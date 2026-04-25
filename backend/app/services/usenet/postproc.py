"""PAR2 repair + RAR extraction. Both shell out — bin must be on PATH."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wav"}


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
    """Run par2 verify+repair on any *.par2 in work_dir. Returns True if no
    par2 present OR repair succeeded; False if it failed."""
    par2_files = sorted(work_dir.glob("*.par2"))
    if not par2_files:
        return True
    par2_bin = _which("par2") or _which("par2cmdline") or _which("par2j64")
    if not par2_bin:
        raise RuntimeError(
            "par2 binary not found on PATH. Install par2cmdline (or par2cmdline-turbo) "
            "to enable repair, or skip releases that ship PAR2 sets."
        )
    main_par2 = next((p for p in par2_files if not p.name.lower().endswith(".vol00.par2")), par2_files[0])
    code, _out = await _run(par2_bin, "r", main_par2.name, cwd=work_dir)
    return code == 0


async def unrar(work_dir: Path) -> bool:
    """Extract any .rar archives found in work_dir. Returns True if no RARs OR all extracted."""
    rars = sorted(work_dir.glob("*.rar"))
    if not rars:
        return True
    unrar_bin = _which("unrar") or _which("unrar.exe") or _which("UnRAR.exe")
    if not unrar_bin:
        raise RuntimeError(
            "unrar binary not found on PATH. Install unrar (rarlab.com) to enable extraction."
        )
    # Pick the first volume (e.g. *.part01.rar OR *.rar). unrar handles the rest.
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


async def post_process(work_dir: Path) -> Path:
    """Run par2 → unrar → return the largest audio file found.

    Raises if no audio file results.
    """
    await par2_repair(work_dir)
    await unrar(work_dir)
    audio = find_audio_files(work_dir)
    if not audio:
        raise RuntimeError("post-process: no audio file in extracted set")
    audio.sort(key=lambda p: p.stat().st_size, reverse=True)
    return audio[0]
