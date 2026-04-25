from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack
from app.services.events import bus


# Audio categories (Newznab standard): 3000 = Audio (parent), 3010 MP3,
# 3040 Lossless/FLAC. Most indexers treat 3000 as "all audio subcats".
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
        size = int(attrs.get("size") or 0)
        grabs = int(attrs.get("grabs") or 0)
        out.append(
            Candidate(
                source=SourceKind.nzb,
                url=link,
                title=title,
                score=0.5 + min(grabs / 50, 0.4),
                extra={"indexer": indexer_name, "size": size, "grabs": grabs},
            )
        )
    return out


class NewznabIndexer:
    """One Newznab-compatible indexer (NZBGeek, DrunkenSlug, etc.)."""

    kind = SourceKind.nzb

    def __init__(self, name: str, url: str, api_key: str):
        self.name = f"newznab:{name}"
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
        if not self.base_url or not self.api_key:
            return []

        # Build a sequence of progressively broader queries. Music on Usenet
        # is overwhelmingly album-shaped, so artist+album wins when we have
        # an album; raw artist alone is the last resort.
        attempts: list[dict] = []
        common = {
            "apikey": self.api_key,
            "o": "xml",
            "limit": 50,
            "cat": _AUDIO_CATS,
        }
        # 1. Structured music search (t=music) with artist/album.
        if track.album:
            attempts.append({**common, "t": "music", "artist": track.artist, "album": track.album})
        # 2. Structured music with artist only (returns whole discography).
        attempts.append({**common, "t": "music", "artist": track.artist})
        # 3. Plain text search Artist + Album.
        if track.album:
            attempts.append({**common, "t": "search", "q": f"{track.artist} {track.album}"})
        # 4. Plain text search Artist + Title (long shot — singles only).
        attempts.append({**common, "t": "search", "q": f"{track.artist} {track.title}"})

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for params in attempts:
                results = await self._query(client, params)
                if results:
                    label = (
                        params.get("q")
                        or f"{params.get('artist', '')} / {params.get('album', '') or '*'}"
                    )
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
