from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack


class NewznabIndexer:
    """One Newznab-compatible indexer (NZBGeek, DrunkenSlug, NZBPlanet, etc.)."""

    kind = SourceKind.nzb

    def __init__(self, name: str, url: str, api_key: str):
        self.name = f"newznab:{name}"
        self.base_url = url.rstrip("/")
        self.api_key = api_key

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        if not self.base_url or not self.api_key:
            return []
        params = {
            "t": "music",
            "q": f"{track.artist} {track.title}",
            "apikey": self.api_key,
            "o": "xml",
            "limit": 25,
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(f"{self.base_url}/api", params=params)
                r.raise_for_status()
                root = ET.fromstring(r.text)
        except Exception:
            return []
        out: list[Candidate] = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if not title or not link:
                continue
            attrs = {a.get("name"): a.get("value") for a in item.findall("{*}attr")}
            size = int(attrs.get("size") or 0)
            grabs = int(attrs.get("grabs") or 0)
            score = 0.5 + min(grabs / 50, 0.4)
            out.append(
                Candidate(
                    source=SourceKind.nzb,
                    url=link,
                    title=title,
                    score=score,
                    extra={
                        "indexer": self.name,
                        "size": size,
                        "grabs": grabs,
                    },
                )
            )
        return out


class NewznabAggregateIndexer:
    """Fan out a single search across all configured Newznab indexers."""

    name = "newznab-aggregate"
    kind = SourceKind.nzb

    def __init__(self, indexers: list[NewznabIndexer]):
        self.indexers = indexers

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        if not self.indexers:
            return []
        results = await asyncio.gather(
            *(idx.search(track) for idx in self.indexers),
            return_exceptions=True,
        )
        out: list[Candidate] = []
        for r in results:
            if isinstance(r, Exception):
                continue
            out.extend(r)
        return out
