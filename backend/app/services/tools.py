"""Auto-install external binaries (par2, unrar) into .data/tools/.

Augments the running process's PATH so subprocess.run / shutil.which see
them. Works on Windows; on macOS/Linux we expect the binaries to come
from the system package manager (apt/brew install par2 unrar).
"""
from __future__ import annotations

import asyncio
import io
import os
import platform
import shutil
import zipfile
from pathlib import Path
from typing import Any

import httpx

from app.services.events import bus

TOOLS_DIR = Path.cwd() / ".data" / "tools"


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def _augment_path(p: Path) -> None:
    s = str(p.resolve())
    paths = os.environ.get("PATH", "")
    if s not in paths.split(os.pathsep):
        os.environ["PATH"] = s + os.pathsep + paths


def _which(name: str) -> str | None:
    return shutil.which(name)


async def _download(url: str, timeout: int = 60) -> bytes:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


def _status(name: str, *, available: bool, path: str | None,
            auto: bool, error: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "name": name,
        "available": available,
        "path": path,
        "auto_managed": auto,
    }
    if error:
        out["error"] = error
    return out


async def ensure_par2(force: bool = False) -> dict[str, Any]:
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    _augment_path(TOOLS_DIR)

    target = TOOLS_DIR / ("par2.exe" if _is_windows() else "par2")
    if target.exists() and not force:
        return _status("par2", available=True, path=str(target), auto=True)

    system_par2 = _which("par2") or _which("par2cmdline") or _which("par2j64")
    if system_par2 and not force:
        return _status("par2", available=True, path=system_par2, auto=False)

    if not _is_windows():
        return _status(
            "par2",
            available=False,
            path=None,
            auto=False,
            error="par2 not found. Install via your package manager: `apt install par2` or `brew install par2cmdline`.",
        )

    bus.emit("log", "par2: auto-installing par2cmdline-turbo (one-time download)")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(
                "https://api.github.com/repos/animetosho/par2cmdline-turbo/releases/latest"
            )
            r.raise_for_status()
            data = r.json()
        asset_url = None
        for asset in data.get("assets", []):
            n = (asset.get("name") or "").lower()
            if ("win-x64" in n or "win64" in n) and n.endswith(".zip"):
                asset_url = asset["browser_download_url"]
                break
        if not asset_url:
            return _status("par2", available=False, path=None, auto=True,
                           error="no win-x64 asset found in latest release")
        zip_bytes = await _download(asset_url)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            for name in z.namelist():
                if name.lower().endswith("par2.exe"):
                    target.write_bytes(z.read(name))
                    break
        if not target.exists():
            return _status("par2", available=False, path=None, auto=True,
                           error="par2.exe not present in downloaded archive")
        bus.emit("log", f"par2 installed → {target}")
        return _status("par2", available=True, path=str(target), auto=True)
    except Exception as e:
        return _status("par2", available=False, path=None, auto=True, error=str(e))


async def _extract_sfx_with_7z(sfx_path: Path, target_dir: Path) -> Path | None:
    """7-Zip can read rarlab's SFX (it's a RAR archive with an exe prefix).
    No UAC required, no installer side-effects. Returns the extracted
    UnRAR.exe path if it succeeded, else None."""
    sevenz = _which("7z") or _which("7za") or _which("7zr")
    if not sevenz:
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            sevenz, "x", str(sfx_path), f"-o{target_dir}", "-y", "-bso0", "-bsp0",
            cwd=str(target_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            await asyncio.wait_for(proc.communicate(), timeout=60)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
    except Exception:
        return None
    for name in ("UnRAR.exe", "unrar.exe"):
        cand = target_dir / name
        if cand.exists() and cand.stat().st_size > 50_000:
            return cand
    return None


async def ensure_unrar(force: bool = False) -> dict[str, Any]:
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    _augment_path(TOOLS_DIR)

    target = TOOLS_DIR / ("UnRAR.exe" if _is_windows() else "unrar")
    if target.exists() and not force:
        return _status("unrar", available=True, path=str(target), auto=True)

    system = _which("unrar") or _which("UnRAR")
    if system and not force:
        return _status("unrar", available=True, path=system, auto=False)

    if not _is_windows():
        return _status(
            "unrar",
            available=False,
            path=None,
            auto=False,
            error="unrar not found. Install via your package manager: `apt install unrar` or `brew install unrar`.",
        )

    bus.emit("log", "unrar: downloading rarlab SFX")
    sfx_path = TOOLS_DIR / "_unrar_sfx.exe"
    try:
        sfx_bytes = await _download("https://www.rarlab.com/rar/unrarw64.exe")
        sfx_path.write_bytes(sfx_bytes)

        # 1) Best path: extract the embedded RAR archive with 7-Zip if it's
        #    on the PATH. No UAC, no installer side-effects.
        bus.emit("log", "unrar: trying 7-Zip extraction")
        extracted = await _extract_sfx_with_7z(sfx_path, TOOLS_DIR)
        if extracted:
            if extracted != target:
                target.write_bytes(extracted.read_bytes())
                if extracted != target:
                    extracted.unlink(missing_ok=True)
            sfx_path.unlink(missing_ok=True)
            bus.emit("log", f"unrar installed via 7-Zip → {target}")
            return _status("unrar", available=True, path=str(target), auto=True)

        # 2) Fallback: try silent flags. rarlab's SFX rarely respects these
        #    without elevation, but cheap to try.
        for args in [
            [str(sfx_path), "-s", f"-d{TOOLS_DIR}"],
            [str(sfx_path), "/S", f"/D={TOOLS_DIR}"],
            [str(sfx_path), "-s"],
        ]:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=str(TOOLS_DIR),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                )
                try:
                    await asyncio.wait_for(proc.communicate(), timeout=20)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.communicate()
            except Exception:
                continue
            for cand in (
                target,
                TOOLS_DIR / "UnRAR.exe",
                Path("C:/Program Files/UnRAR/UnRAR.exe"),
                Path("C:/Program Files (x86)/UnRAR/UnRAR.exe"),
            ):
                if cand.exists() and cand.stat().st_size > 50_000:
                    if cand != target:
                        target.write_bytes(cand.read_bytes())
                    sfx_path.unlink(missing_ok=True)
                    bus.emit("log", f"unrar installed via SFX → {target}")
                    return _status("unrar", available=True, path=str(target), auto=True)

        sfx_path.unlink(missing_ok=True)
        return _status(
            "unrar",
            available=False,
            path=None,
            auto=True,
            error=(
                "Auto-install failed (no 7-Zip on PATH and the rarlab SFX needs UAC). "
                "Click the Upload button and pick UnRAR.exe from rarlab.com — no admin needed."
            ),
        )
    except Exception as e:
        sfx_path.unlink(missing_ok=True)
        return _status("unrar", available=False, path=None, auto=True, error=str(e))


def save_uploaded_tool(filename: str, content: bytes) -> dict[str, Any]:
    """Whitelist + persist a user-uploaded tool binary."""
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    stem = filename.lower().rsplit(".", 1)[0].rstrip(" _-")
    name_map = {
        "unrar": "UnRAR.exe" if _is_windows() else "unrar",
        "par2": "par2.exe" if _is_windows() else "par2",
        "par2cmdline": "par2.exe" if _is_windows() else "par2",
        "par2j64": "par2.exe" if _is_windows() else "par2",
    }
    if stem not in name_map:
        return {
            "ok": False,
            "error": f"Filename '{filename}' isn't on the allow-list. Pick UnRAR.exe or par2.exe.",
        }
    target = TOOLS_DIR / name_map[stem]
    target.write_bytes(content)
    _augment_path(TOOLS_DIR)
    bus.emit("log", f"uploaded tool installed → {target}")
    return {"ok": True, "name": name_map[stem], "path": str(target), "size": len(content)}


async def ensure_all(force: bool = False) -> dict[str, dict[str, Any]]:
    par2 = await ensure_par2(force=force)
    unrar = await ensure_unrar(force=force)
    return {"par2": par2, "unrar": unrar}


async def status() -> dict[str, dict[str, Any]]:
    """Read-only — checks PATH + .data/tools/ without downloading anything."""
    _augment_path(TOOLS_DIR)
    out: dict[str, dict[str, Any]] = {}
    for tool, exe in (("par2", "par2"), ("unrar", "unrar")):
        candidate = TOOLS_DIR / (f"{exe}.exe" if _is_windows() else exe)
        managed = candidate.exists()
        if managed:
            out[tool] = _status(tool, available=True, path=str(candidate), auto=True)
            continue
        sys_path = _which(exe) or _which(exe.capitalize())
        out[tool] = _status(tool, available=bool(sys_path), path=sys_path, auto=False)
    return out
