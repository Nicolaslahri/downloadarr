from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from app.resolvers.base import ResolvedPlaylist, ResolvedTrack


def _resolve_sync(url: str) -> ResolvedPlaylist:
    from yt_dlp import YoutubeDL

    with YoutubeDL({"quiet": True, "skip_download": True, "extract_flat": "in_playlist"}) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise RuntimeError("yt-dlp returned no info")
    entries = info.get("entries") or [info]
    tracks: list[ResolvedTrack] = []
    for e in entries:
        if not e:
            continue
        title = e.get("title") or ""
        artist = e.get("uploader") or "Unknown"
        if " - " in title:
            artist, _, title = title.partition(" - ")
        url_hint = e.get("webpage_url") or e.get("url")
        tracks.append(
            ResolvedTrack(
                artist=artist.strip(),
                title=title.strip(),
                duration_s=int(e.get("duration") or 0) or None,
                source_url_hint=url_hint,
            )
        )
    return ResolvedPlaylist(
        source="soundcloud",
        source_url=url,
        name=info.get("title") or "SoundCloud",
        tracks=tracks,
    )


class SoundCloudResolver:
    name = "soundcloud"

    def detect(self, url: str) -> bool:
        try:
            return (urlparse(url).hostname or "").endswith("soundcloud.com")
        except Exception:
            return False

    async def resolve(self, url: str) -> ResolvedPlaylist:
        return await asyncio.to_thread(_resolve_sync, url)
