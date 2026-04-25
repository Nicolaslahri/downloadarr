from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from app.resolvers.base import ResolvedPlaylist, ResolvedTrack


def _is_spotify(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return host.endswith("spotify.com")


def _resolve_sync(url: str, client_id: str, client_secret: str) -> ResolvedPlaylist:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    sp = spotipy.Spotify(auth_manager=auth, requests_timeout=20)

    path = urlparse(url).path
    parts = [p for p in path.split("/") if p]
    if "playlist" in parts:
        pid = parts[parts.index("playlist") + 1].split("?")[0]
        meta = sp.playlist(pid, fields="name")
        name = meta.get("name", "Spotify Playlist")
        items: list = []
        offset = 0
        while True:
            page = sp.playlist_items(
                pid,
                offset=offset,
                fields="items(track(name,artists,album(name),duration_ms,external_ids)),next",
                additional_types=("track",),
                limit=100,
            )
            items.extend(page.get("items") or [])
            if not page.get("next"):
                break
            offset += 100
        tracks: list[ResolvedTrack] = []
        for it in items:
            t = (it or {}).get("track")
            if not t:
                continue
            artists = ", ".join(a.get("name", "") for a in (t.get("artists") or []))
            tracks.append(
                ResolvedTrack(
                    artist=artists or "Unknown",
                    title=t.get("name") or "",
                    album=(t.get("album") or {}).get("name"),
                    duration_s=int((t.get("duration_ms") or 0) / 1000) or None,
                    isrc=(t.get("external_ids") or {}).get("isrc"),
                )
            )
        return ResolvedPlaylist(source="spotify", source_url=url, name=name, tracks=tracks)
    if "album" in parts:
        aid = parts[parts.index("album") + 1].split("?")[0]
        album = sp.album(aid)
        tracks = [
            ResolvedTrack(
                artist=", ".join(a.get("name", "") for a in (t.get("artists") or [])),
                title=t.get("name") or "",
                album=album.get("name"),
                duration_s=int((t.get("duration_ms") or 0) / 1000) or None,
            )
            for t in (album.get("tracks") or {}).get("items") or []
        ]
        return ResolvedPlaylist(
            source="spotify",
            source_url=url,
            name=album.get("name") or "Spotify Album",
            tracks=tracks,
        )
    raise ValueError("Unrecognized Spotify URL — paste a playlist or album link.")


class SpotifyResolver:
    name = "spotify"

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret

    def detect(self, url: str) -> bool:
        return _is_spotify(url)

    async def resolve(self, url: str) -> ResolvedPlaylist:
        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Spotify credentials not configured — add them in Settings → Streaming."
            )
        return await asyncio.to_thread(
            _resolve_sync, url, self.client_id, self.client_secret
        )
