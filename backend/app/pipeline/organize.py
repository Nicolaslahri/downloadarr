from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.resolvers.base import ResolvedTrack

_SAFE_CHAR = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe(name: str) -> str:
    name = _SAFE_CHAR.sub("_", name).strip().rstrip(".")
    return name[:120] or "Unknown"


def organize(file_path: str, track: ResolvedTrack, library_root: str) -> str:
    src = Path(file_path)
    artist = _safe(track.artist or "Unknown Artist")
    album = _safe(track.album or "Singles")
    title = _safe(track.title or src.stem)
    dest_dir = Path(library_root) / artist / album
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{title}{src.suffix}"
    if dest.exists() and dest.resolve() == src.resolve():
        return str(dest)
    if dest.exists():
        # uniqueify
        for i in range(2, 50):
            cand = dest_dir / f"{title} ({i}){src.suffix}"
            if not cand.exists():
                dest = cand
                break
    shutil.move(str(src), str(dest))
    return str(dest)
