from __future__ import annotations

import asyncio
import re
import xml.etree.ElementTree as ET

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack
from app.services.events import bus

# Audio categories (Newznab standard)
_AUDIO_CATS = "3000,3010,3040,3050"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _title_score_boost(track: ResolvedTrack, candidate_title: str) -> float:
    """Reward candidates whose release name actually mentions the track
    title. Stops the indexer from happily handing back a random release
    by the same artist that doesn't contain the song we want."""
    cand = _norm(candidate_title)
    title_words = [w for w in _norm(track.title).split() if len(w) > 2]
    if not title_words:
        return 0.0
    hits = sum(1 for w in title_words if w in cand)
    if hits == len(title_words):
        return 0.6  # full match
    if hits >= max(1, len(title_words) // 2):
        return 0.25  # most words match
    return 0.0


def _parse(xml_text: str, indexer_name: str, track: ResolvedTrack) -> list[Candidate]:
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
        score = 0.5 + min(grabs / 50, 0.3) + _title_score_boost(track, title)
        out.append(
            Candidate(
                source=SourceKind.nzb,
                url=link,
                title=title,
                score=score,
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

    async def _query(self, client: httpx.AsyncClient, params: dict, track: ResolvedTrack) -> list[Candidate]:
        try:
            r = await client.get(f"{self.base_url}/api", params=params)
        except Exception as e:
            bus.emit("log", f"{self.name} request failed: {e}", level="warn")
            return []
        if r.status_code != 200:
            return []
        return _parse(r.text, self.name, track)

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        if not self.base_url or not self.api_key:
            return []

        common = {
            "apikey": self.api_key,
            "o": "xml",
            "limit": 50,
            "cat": _AUDIO_CATS,
        }

        # Build a query ladder. Specific queries first; broad artist-only
        # is the LAST resort because it returns whatever the artist has
        # ever uploaded, which is usually not what we want.
        attempts: list[dict] = []
        if track.album:
            # Track has known album — this is the gold path.
            attempts.append({**common, "t": "music", "artist": track.artist, "album": track.album})
            attempts.append({**common, "t": "search", "q": f"{track.artist} {track.album}"})
        # Specific artist+title text search (works for singles, OSTs, comps).
        attempts.append({**common, "t": "search", "q": f"{track.artist} {track.title}"})
        # Some indexers honor the `track` param under t=music.
        attempts.append({**common, "t": "music", "artist": track.artist, "track": track.title})
        # Last resort: whole-artist search (will return the discography).
        attempts.append({**common, "t": "music", "artist": track.artist})

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for params in attempts:
                results = await self._query(client, params, track)
                if results:
                    label = (
                        params.get("q")
                        or f"{params.get('artist', '')} / {params.get('album', '*')} / {params.get('track', '*')}"
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
