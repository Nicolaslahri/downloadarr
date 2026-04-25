from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack
from app.services.events import bus

_AUDIO_CATS = "3000,3010,3040,3050"


def _parse(xml_text: str, indexer_name: str) -> list[Candidate]:
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return []
    if root.tag.lower() == "error":
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
                    "indexer": indexer_name,
                    "seeders": seeders,
                    "size": int(attrs.get("size") or 0),
                    "is_magnet": bool(magnet),
                },
            )
        )
    return out


class TorznabIndexer:
    """Single Torznab-compatible torrent indexer."""

    kind = SourceKind.torrent

    def __init__(self, name: str, url: str, api_key: str = ""):
        self.name = f"torznab:{name}"
        self.base_url = url.rstrip("/")
        self.api_key = api_key

    async def _query(self, client: httpx.AsyncClient, params: dict) -> list[Candidate]:
        try:
            r = await client.get(f"{self.base_url}/api", params=params)
        except Exception as e:
            bus.emit("log", f"{self.name} request failed: {e}", level="warn")
            return []
        if r.status_code != 200:
            return []
        return _parse(r.text, self.name)

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        if not self.base_url:
            return []
        common: dict = {"o": "xml", "limit": 50, "cat": _AUDIO_CATS}
        if self.api_key:
            common["apikey"] = self.api_key
        attempts: list[dict] = []
        if track.album:
            attempts.append({**common, "t": "music", "artist": track.artist, "album": track.album})
        attempts.append({**common, "t": "music", "artist": track.artist})
        if track.album:
            attempts.append({**common, "t": "search", "q": f"{track.artist} {track.album}"})
        attempts.append({**common, "t": "search", "q": f"{track.artist} {track.title}"})

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for params in attempts:
                results = await self._query(client, params)
                if results:
                    label = params.get("q") or f"{params.get('artist', '')} / {params.get('album', '*')}"
                    bus.emit(
                        "log",
                        f"{self.name}: {len(results)} hits for {label!r} (t={params.get('t')})",
                    )
                    return results
        bus.emit(
            "log",
            f"{self.name}: no hits for '{track.artist} – {track.title}' across {len(attempts)} queries",
        )
        return []


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
