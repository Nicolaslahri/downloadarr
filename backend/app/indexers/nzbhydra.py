from __future__ import annotations

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack


class NzbHydraIndexer:
    name = "nzbhydra"
    kind = SourceKind.nzb

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        if not self.base_url or not self.api_key:
            return []
        params = {
            "t": "search",
            "q": f"{track.artist} {track.title}",
            "cat": "3000",
            "apikey": self.api_key,
            "o": "json",
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{self.base_url}/api", params=params)
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []
        items = ((data or {}).get("channel") or {}).get("item") or []
        out: list[Candidate] = []
        for it in items:
            url = it.get("link") or (it.get("enclosure") or {}).get("@attributes", {}).get("url")
            if not url:
                continue
            out.append(
                Candidate(
                    source=SourceKind.nzb,
                    url=url,
                    title=it.get("title") or "",
                    score=0.6,
                )
            )
        return out
