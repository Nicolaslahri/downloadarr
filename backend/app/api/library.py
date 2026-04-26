from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings as env_settings
from app.db.settings_store import load_all, merge_with_env
from app.services.cleanup import sweep_workspace, workspace_size

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
async def list_library() -> list[dict]:
    cfg = merge_with_env(load_all(), env_settings)
    root = cfg.get("library_path") or env_settings.library_path
    return await asyncio.to_thread(_scan_sync, root)


class LibraryInfo(BaseModel):
    library_path: str
    library_exists: bool
    library_writable: bool
    library_track_count: int
    library_size_bytes: int
    downloads_path: str
    downloads_exists: bool
    downloads_size_bytes: int
    free_bytes: int


def _check_writable(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".musicdl_write_test"
        test.write_bytes(b"ok")
        test.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _free_bytes(p: Path) -> int:
    try:
        usage = shutil.disk_usage(p if p.exists() else p.parent)
        return int(usage.free)
    except OSError:
        return 0


def _info_sync() -> LibraryInfo:
    cfg = merge_with_env(load_all(), env_settings)
    lib = Path(cfg.get("library_path") or env_settings.library_path)
    dl = Path(env_settings.downloads_path)
    audio_count = 0
    audio_size = 0
    if lib.exists():
        for p in lib.rglob("*"):
            if p.is_file() and p.suffix.lower() in AUDIO_EXTS:
                audio_count += 1
                try:
                    audio_size += p.stat().st_size
                except OSError:
                    pass
    return LibraryInfo(
        library_path=str(lib),
        library_exists=lib.exists(),
        library_writable=_check_writable(lib) if lib.exists() or lib.parent.exists() else False,
        library_track_count=audio_count,
        library_size_bytes=audio_size,
        downloads_path=str(dl),
        downloads_exists=dl.exists(),
        downloads_size_bytes=workspace_size(str(dl)),
        free_bytes=_free_bytes(lib),
    )


@router.get("/info", response_model=LibraryInfo)
async def library_info() -> LibraryInfo:
    return await asyncio.to_thread(_info_sync)


@router.post("/cleanup")
async def cleanup_workspace() -> dict:
    """Force-sweep the downloads/ workspace, removing orphan temp dirs."""
    cfg = merge_with_env(load_all(), env_settings)
    dl = cfg.get("downloads_path") or env_settings.downloads_path
    return await asyncio.to_thread(sweep_workspace, dl, 0)  # max_age_hours=0 = nuke all old
