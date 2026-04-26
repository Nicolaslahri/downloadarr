from __future__ import annotations

from urllib.parse import quote_plus

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack
from app.services.events import bus


def _build_query(track: ResolvedTrack) -> str:
    if track.album:
        return f"{track.artist} {track.album}"
    return f"{track.artist} {track.title}"


class TorrentsCsvIndexer:
    """torrents-csv.com — DHT-aggregated torrent dataset with a tiny
    JSON search API. No login, no API key, just polite rate."""

    name = "torrents-csv"
    kind = SourceKind.torrent

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        q = _build_query(track)
        try:
            async with httpx.AsyncClient(
                timeout=12,
                headers={"User-Agent": "MusicDownloadarr/0.1"},
                follow_redirects=True,
            ) as client:
                r = await client.get(
                    "https://torrents-csv.com/service/search",
                    params={"q": q, "size": 25},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            bus.emit("log", f"torrents-csv search failed: {e}", level="warn")
            return []

        out: list[Candidate] = []
        for item in data.get("torrents") or []:
            ih = (item.get("infohash") or "").strip()
            name = (item.get("name") or "").strip()
            if not ih or not name:
                continue
            seeders = int(item.get("seeders") or 0)
            size = int(item.get("size_bytes") or 0)
            magnet = f"magnet:?xt=urn:btih:{ih}&dn={quote_plus(name)}"
            out.append(
                Candidate(
                    source=SourceKind.torrent,
                    url=magnet,
                    title=name,
                    score=0.4 + min(seeders / 200, 0.5),
                    extra={
                        "indexer": "torrents-csv",
                        "seeders": seeders,
                        "size": size,
                        "is_magnet": True,
                    },
                )
            )
        return out
