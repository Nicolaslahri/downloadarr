from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as env_settings
from app.db.session import get_session
from app.db.settings_store import load_all, merge_with_env

router = APIRouter(prefix="/library", tags=["library"])

AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wav"}


def _scan_sync(root: str) -> list[dict]:
    p = Path(root)
    if not p.exists():
        return []
    out: list[dict] = []
    for f in p.rglob("*"):
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
            try:
                size = f.stat().st_size
            except Exception:
                size = 0
            parts = list(f.relative_to(p).parts)
            artist = parts[0] if len(parts) >= 3 else "Unknown"
            album = parts[1] if len(parts) >= 3 else None
            title = f.stem
            out.append(
                {
                    "path": str(f),
                    "artist": artist,
                    "album": album,
                    "title": title,
                    "size_bytes": size,
                    "format": f.suffix.lstrip(".").lower(),
                }
            )
    out.sort(key=lambda d: (d["artist"].lower(), d["album"] or "", d["title"].lower()))
    return out


@router.get("")
async def list_library(session: AsyncSession = Depends(get_session)) -> list[dict]:
    cfg_db = await load_all(session)
    cfg = merge_with_env(cfg_db, env_settings)
    root = cfg.get("library_path") or env_settings.library_path
    return await asyncio.to_thread(_scan_sync, root)
