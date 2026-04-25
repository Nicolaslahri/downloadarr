from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack


class TorznabIndexer:
    """Single Torznab-compatible torrent indexer."""

    kind = SourceKind.torrent

    def __init__(self, name: str, url: str, api_key: str = ""):
        self.name = f"torznab:{name}"
        self.base_url = url.rstrip("/")
        self.api_key = api_key

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        if not self.base_url:
            return []
        params: dict[str, str | int] = {
            "t": "music",
            "q": f"{track.artist} {track.title}",
            "limit": 25,
        }
        if self.api_key:
            params["apikey"] = self.api_key
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
            seeders = int(attrs.get("seeders") or 0)
            magnet = attrs.get("magneturl") or ""
            url = magnet or link
            out.append(
                Candidate(
                    source=SourceKind.torrent,
                    url=url,
                    title=title,
                    score=0.4 + min(seeders / 200, 0.5),
                    extra={
                        "indexer": self.name,
                        "seeders": seeders,
                        "size": int(attrs.get("size") or 0),
                        "is_magnet": bool(magnet),
                    },
                )
            )
        return out


class TorznabAggregateIndexer:
    name = "torznab-aggregate"
    kind = SourceKind.torrent

    def __init__(self, indexers: list[TorznabIndexer]):
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
