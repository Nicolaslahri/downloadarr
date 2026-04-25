from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from app.resolvers.base import ResolvedPlaylist, ResolvedTrack


def _is_apple(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return False
    return host.endswith("music.apple.com")


_NAME_RE = re.compile(
    r'<meta property="(?:og:title|twitter:title)" content="([^"]+)"', re.I
)
_LD_RE = re.compile(
    r'<script type="application/ld\+json"[^>]*>([\s\S]*?)</script>', re.I
)


class AppleMusicResolver:
    """
    Best-effort scrape of Apple Music's public HTML. Apple's official
    catalog API needs a developer token; for self-hosted single-user we
    parse the embedded JSON-LD instead. Works for most public playlists
    and albums.
    """

    name = "apple_music"

    def detect(self, url: str) -> bool:
        return _is_apple(url)

    async def resolve(self, url: str) -> ResolvedPlaylist:
        import json

        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 MusicDownloadarr/0.1"},
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            html = r.text

        name_match = _NAME_RE.search(html)
        name = (name_match.group(1) if name_match else "Apple Music").split(" - ")[0]
        tracks: list[ResolvedTrack] = []
        for blob in _LD_RE.findall(html):
            try:
                data = json.loads(blob)
            except Exception:
                continue
            candidates = data if isinstance(data, list) else [data]
            for d in candidates:
                if not isinstance(d, dict):
                    continue
                track_blocks = d.get("track") or d.get("itemListElement")
                if not track_blocks:
                    if d.get("@type") == "MusicRecording":
                        track_blocks = [d]
                if not track_blocks:
                    continue
                for tb in track_blocks if isinstance(track_blocks, list) else [track_blocks]:
                    if isinstance(tb, dict) and tb.get("item"):
                        tb = tb["item"]
                    if not isinstance(tb, dict):
                        continue
                    title = tb.get("name")
                    if not title:
                        continue
                    by = tb.get("byArtist") or {}
                    artist = (
                        by.get("name") if isinstance(by, dict)
                        else ", ".join(a.get("name", "") for a in by) if isinstance(by, list)
                        else "Unknown"
                    )
                    tracks.append(
                        ResolvedTrack(artist=artist or "Unknown", title=title)
                    )
        if not tracks:
            raise RuntimeError(
                "Couldn't parse this Apple Music page. The HTML may have changed; "
                "Apple Music public scraping is a best-effort path."
            )
        return ResolvedPlaylist(
            source="apple_music", source_url=url, name=name, tracks=tracks
        )
