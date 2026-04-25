from __future__ import annotations

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack


class ProwlarrIndexer:
    name = "prowlarr"
    kind = SourceKind.torrent

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        if not self.base_url or not self.api_key:
            return []
        params = {
            "query": f"{track.artist} {track.title}",
            "categories": "3000,3010,3020",  # Audio/MP3/FLAC
            "type": "search",
            "apikey": self.api_key,
            "limit": 20,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{self.base_url}/api/v1/search", params=params)
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []
        out: list[Candidate] = []
        for item in data or []:
            url = item.get("downloadUrl") or item.get("magnetUrl") or item.get("guid")
            if not url:
                continue
            seeders = item.get("seeders") or 0
            score = min(0.9, 0.3 + seeders / 100)
            out.append(
                Candidate(
                    source=SourceKind.torrent,
                    url=url,
                    title=item.get("title") or "",
                    score=score,
                    extra={"seeders": seeders, "size": item.get("size")},
                )
            )
        return out
