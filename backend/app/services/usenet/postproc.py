"""PAR2 repair + RAR extraction. Both shell out — bin should be on PATH."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from app.services.events import bus

AUDIO_EXTS = {
    ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wav",
    ".mka", ".ape", ".wv", ".alac", ".tta", ".dsf", ".dff", ".tak",
}


def _which(name: str) -> str | None:
    return shutil.which(name)


async def _run(*args: str, cwd: Path) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    out, _ = await proc.communicate()
    return proc.returncode or 0, out.decode("utf-8", "replace")


async def par2_repair(work_dir: Path) -> bool:
    par2_files = sorted(work_dir.glob("*.par2"))
    if not par2_files:
        return True
    par2_bin = _which("par2") or _which("par2cmdline") or _which("par2j64")
    if not par2_bin:
        bus.emit(
            "log",
            "par2 binary not on PATH — skipping repair",
            level="warn",
        )
        return True
    main_par2 = next(
        (p for p in par2_files if not p.name.lower().endswith(".vol00.par2")),
        par2_files[0],
    )
    code, _out = await _run(par2_bin, "r", main_par2.name, cwd=work_dir)
    if code != 0:
        bus.emit("log", f"par2 returned exit {code} — files may be incomplete", level="warn")
        return False
    return True


async def unrar(work_dir: Path) -> bool:
    rars = sorted(work_dir.glob("*.rar"))
    if not rars:
        return True

    existing_audio = find_audio_files(work_dir)
    audio_outside_rar = [p for p in existing_audio if p.suffix.lower() != ".rar"]

    unrar_bin = _which("unrar") or _which("unrar.exe") or _which("UnRAR.exe")
    if not unrar_bin:
        if audio_outside_rar:
            bus.emit(
                "log",
                "unrar not on PATH — using audio files outside the RAR set",
                level="warn",
            )
            return True
        raise RuntimeError(
            "Release is RAR-archived and no unrar binary is on PATH. "
            "Install unrar (apt install unrar / Settings → Tools)."
        )

    first = rars[0]
    for r in rars:
        if "part01.rar" in r.name.lower() or "part1.rar" in r.name.lower():
            first = r
            break
    code, _out = await _run(unrar_bin, "x", "-o+", "-y", first.name, cwd=work_dir)
    return code == 0


def find_audio_files(work_dir: Path) -> list[Path]:
    out: list[Path] = []
    for p in work_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
            out.append(p)
    return out


def _summarize_dir(work_dir: Path, max_lines: int = 12) -> str:
    if not work_dir.exists():
        return "<work dir gone>"
    rows: list[str] = []
    by_ext: dict[str, list[Path]] = {}
    for p in work_dir.rglob("*"):
        if p.is_file():
            by_ext.setdefault(p.suffix.lower() or "<no ext>", []).append(p)
    for ext, files in sorted(by_ext.items(), key=lambda kv: -sum(f.stat().st_size for f in kv[1])):
        total = sum(f.stat().st_size for f in files)
        rows.append(f"{ext}: {len(files)} files, {total / 1024 / 1024:.1f} MB")
        if len(rows) >= max_lines:
            rows.append("…")
            break
    return "; ".join(rows) or "<empty>"


async def post_process(work_dir: Path) -> list[Path]:
    """Run par2 → unrar → return ALL audio files found.

    Caller (track_picker) chooses which one is the target track. Raises
    if no audio at all turns up.
    """
    await par2_repair(work_dir)
    await unrar(work_dir)
    audio = find_audio_files(work_dir)
    if not audio:
        summary = _summarize_dir(work_dir)
        raise RuntimeError(
            f"no audio file in extracted set — release contents: [{summary}]. "
            "This release probably isn't what we wanted (video/disc image, or unrelated)."
        )
    return audio
