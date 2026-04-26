"""Augment magnet links with the curated public-tracker list from
ngosang/trackerslist.

Magnet links from public DHT-aggregated sources (torrents-csv, Nyaa,
1337x scrapes) often carry only 2-3 trackers, many of which go stale.
Appending the ~80 known-good public trackers from the trackerslist
project dramatically improves peer discovery and download success on
otherwise low-seeder music torrents.

Refreshed every 24h in the background. Falls back to disk cache when
the network is unreachable.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from app.services.events import bus

# `trackers_best.txt` is the curated subset (highest uptime). Other
# variants exist (`trackers_all.txt`, `trackers_all_https.txt`); best
# is the right default — quality over quantity.
TRACKERS_URL = (
    "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt"
)
_CACHE_FILE = Path.cwd() / ".data" / "trackers_cache.txt"
_REFRESH_HOURS = 24

_cache: list[str] = []
_last_fetched: float = 0.0
_lock = asyncio.Lock()


def _load_disk_cache() -> list[str]:
    if not _CACHE_FILE.exists():
        return []
    try:
        return [
            line.strip()
            for line in _CACHE_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    except OSError:
        return []


def _save_disk_cache(trackers: list[str]) -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text("\n".join(trackers), encoding="utf-8")
    except OSError:
        pass


async def fetch() -> list[str]:
    """Fetch the latest list from GitHub. Updates in-memory + disk cache."""
    global _cache, _last_fetched
    async with _lock:
        try:
            async with httpx.AsyncClient(
                timeout=15,
                headers={"User-Agent": "MusicDownloadarr/0.1"},
            ) as client:
                r = await client.get(TRACKERS_URL)
                r.raise_for_status()
                text = r.text
        except Exception as e:
            bus.emit(
                "log",
                f"trackerslist refresh failed ({e}); using cached copy",
                level="warn",
            )
            if not _cache:
                _cache = _load_disk_cache()
            return _cache

        trackers = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        if trackers:
            _cache = trackers
            _last_fetched = time.time()
            _save_disk_cache(trackers)
            bus.emit("log", f"trackerslist: {len(trackers)} public trackers loaded")
        return _cache


def cached() -> list[str]:
    """Return the in-memory list, falling back to disk on first call."""
    global _cache
    if not _cache:
        _cache = _load_disk_cache()
    return _cache


def enhance_magnet(magnet: str) -> str:
    """Append cached public trackers to a magnet URI, deduping against
    the trackers it already declares."""
    if not magnet or not magnet.startswith("magnet:"):
        return magnet
    pool = cached()
    if not pool:
        return magnet

    parts = urlparse(magnet)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    existing_trackers = {v for k, v in pairs if k == "tr"}

    additions = [t for t in pool if t not in existing_trackers]
    if not additions:
        return magnet

    pairs.extend(("tr", t) for t in additions)
    new_query = urlencode(pairs)
    return urlunparse(parts._replace(query=new_query))


async def background_refresher() -> None:
    """Refresh forever in the background. Fetches once on start so the
    first download has trackers; then sleeps REFRESH_HOURS between
    refreshes."""
    while True:
        await fetch()
        await asyncio.sleep(_REFRESH_HOURS * 3600)


def info() -> dict:
    """Lightweight status for the Tools / Settings panel."""
    return {
        "trackers_loaded": len(cached()),
        "last_fetched": _last_fetched,
        "source": TRACKERS_URL,
    }
