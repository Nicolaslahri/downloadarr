"""Workspace housekeeping.

NNTP and torrent downloads land in `downloads_path` (usually mapped to
`./downloads` on the host). On a happy path, each downloader cleans
its own temp work_dir. On failure / cancellation, those dirs linger.
This module sweeps them on startup and on demand.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

from app.services.events import bus

_TEMP_PREFIX = "musicdl_nzb_"


def sweep_workspace(downloads_path: str, max_age_hours: float = 24) -> dict:
    """Remove orphaned temp dirs and files. Returns counts."""
    root = Path(downloads_path)
    if not root.exists():
        return {"removed_dirs": 0, "removed_files": 0, "freed_bytes": 0}

    cutoff = time.time() - max_age_hours * 3600
    removed_dirs = 0
    removed_files = 0
    freed_bytes = 0

    for child in root.iterdir():
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime > cutoff:
            continue
        try:
            if child.is_dir() and child.name.startswith(_TEMP_PREFIX):
                size = sum(p.stat().st_size for p in child.rglob("*") if p.is_file())
                shutil.rmtree(child, ignore_errors=True)
                removed_dirs += 1
                freed_bytes += size
            elif child.is_file() and child.suffix in {".tmp", ".part", ".aria2"}:
                size = child.stat().st_size
                child.unlink(missing_ok=True)
                removed_files += 1
                freed_bytes += size
        except OSError:
            continue

    return {
        "removed_dirs": removed_dirs,
        "removed_files": removed_files,
        "freed_bytes": freed_bytes,
    }


def workspace_size(downloads_path: str) -> int:
    """Total bytes currently sitting in the workspace (excluding library)."""
    root = Path(downloads_path)
    if not root.exists():
        return 0
    total = 0
    for p in root.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            pass
    return total


async def startup_sweep(downloads_path: str) -> None:
    """Called from the FastAPI lifespan."""
    try:
        result = sweep_workspace(downloads_path, max_age_hours=24)
        if result["removed_dirs"] or result["removed_files"]:
            mb = result["freed_bytes"] / 1024 / 1024
            bus.emit(
                "log",
                f"workspace sweep: freed {mb:.1f} MB across "
                f"{result['removed_dirs']} dirs and {result['removed_files']} files",
            )
    except Exception as e:
        bus.emit("log", f"workspace sweep failed: {e}", level="warn")
