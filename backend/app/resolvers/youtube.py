from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from app.resolvers.base import ResolvedPlaylist, ResolvedTrack


def _is_yt(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    host = host.replace("www.", "")
    return host in {
        "youtube.com",
        "music.youtube.com",
        "m.youtube.com",
        "youtu.be",
    }


def _is_playlist(url: str) -> bool:
    if not _is_yt(url):
        return False
    p = urlparse(url)
    return "list=" in (p.query or "") or "/playlist" in p.path


def _extract_sync(url: str) -> ResolvedPlaylist:
    from yt_dlp import YoutubeDL

    opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        raise RuntimeError("yt-dlp returned no info")
    entries = info.get("entries") or []
    name = info.get("title") or "YouTube Playlist"
    tracks: list[ResolvedTrack] = []
    for e in entries:
        if not e:
            continue
        title = (e.get("title") or "").strip()
        if not title:
            continue
        artist = (e.get("uploader") or e.get("channel") or "Unknown").strip()
        # Many YT music titles are "Artist - Title" — split if so.
        if " - " in title:
            maybe_artist, _, maybe_title = title.partition(" - ")
            if len(maybe_artist) < 80:
                artist = maybe_artist.strip()
                title = maybe_title.strip()
        duration = e.get("duration")
        video_id = e.get("id")
        url_hint = f"https://www.youtube.com/watch?v={video_id}" if video_id else None
        tracks.append(
            ResolvedTrack(
                artist=artist,
                title=title,
                duration_s=int(duration) if duration else None,
                source_url_hint=url_hint,
            )
        )
    source = "youtube_music" if "music.youtube.com" in url else "youtube"
    return ResolvedPlaylist(source=source, source_url=url, name=name, tracks=tracks)


class YouTubeResolver:
    name = "youtube"

    def detect(self, url: str) -> bool:
        return _is_playlist(url)

    async def resolve(self, url: str) -> ResolvedPlaylist:
        return await asyncio.to_thread(_extract_sync, url)
