"""PAR2 repair + RAR extraction. Both shell out — bin should be on PATH."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from app.services.events import bus

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
    """Run par2 verify+repair on any *.par2 in work_dir. Best-effort: if
    no par2 binary is on PATH we log a warning and skip — the release is
    almost always intact (par2 is for *recovering* missing/corrupt blocks),
    and downstream steps will surface real corruption when they hit it."""
    par2_files = sorted(work_dir.glob("*.par2"))
    if not par2_files:
        return True
    par2_bin = _which("par2") or _which("par2cmdline") or _which("par2j64")
    if not par2_bin:
        bus.emit(
            "log",
            "par2 binary not on PATH — skipping repair. Install par2cmdline-turbo "
            "for guaranteed integrity: github.com/animetosho/par2cmdline-turbo/releases",
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
    """Extract any .rar archives found in work_dir. Hard-required when
    RARs are the only carriers of the audio — without it we have no way
    to get the content out."""
    rars = sorted(work_dir.glob("*.rar"))
    if not rars:
        return True

    # If audio files already exist outside the RARs, treat unrar as optional.
    existing_audio = find_audio_files(work_dir)
    audio_outside_rar = [p for p in existing_audio if p.suffix.lower() != ".rar"]

    unrar_bin = _which("unrar") or _which("unrar.exe") or _which("UnRAR.exe")
    if not unrar_bin:
        if audio_outside_rar:
            bus.emit(
                "log",
                "unrar not on PATH — using audio files outside the RAR set. Install "
                "unrar (rarlab.com) to also extract archived content.",
                level="warn",
            )
            return True
        raise RuntimeError(
            "This release is RAR-archived and no unrar binary is on PATH. "
            "Install unrar from rarlab.com (UnRAR.exe → place on PATH) and retry."
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
