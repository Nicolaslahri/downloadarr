"""1337x.to scraper.

Two-step: search-results page → list of torrent detail URLs → fetch
each detail page in parallel for the magnet link. We limit to top-N
hits so we don't fan out 25 detail-page requests at once.
"""
from __future__ import annotations

import asyncio
import re

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack
from app.services.events import bus

_BASE = "https://1337x.to"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 MusicDownloadarr/0.1",
    "Accept": "text/html",
}

# Two-link rows: name link is /torrent/<id>/<slug>/ ; same row has
# seeders, leechers, size in subsequent <td>s.
_RESULT_RE = re.compile(
    r'<td class="coll-1 name">.*?<a href="(?P<href>/torrent/\d+/[^"]+/)"[^>]*>(?P<name>[^<]+)</a>'
    r'.*?<td class="coll-2 seeds">(?P<seeders>\d+)</td>'
    r'.*?<td class="coll-3 leeches">\d+</td>'
    r'.*?<td class="coll-date">[^<]+</td>'
    r'.*?<td class="coll-4 size[^"]*">(?P<size>[^<]+?)<',
    re.DOTALL | re.IGNORECASE,
)
_MAGNET_RE = re.compile(r'href="(magnet:\?xt=urn:btih:[^"]+)"', re.IGNORECASE)
_SIZE_RE = re.compile(r"([\d.]+)\s*([KMGT]B)", re.IGNORECASE)


def _parse_size(text: str) -> int:
    text = text.strip()
    m = _SIZE_RE.search(text)
    if not m:
        return 0
    value = float(m.group(1))
    unit = m.group(2).upper()
    mults = {"B": 1, "KB": 1000, "MB": 1_000_000, "GB": 1_000_000_000, "TB": 1_000_000_000_000}
    return int(value * mults.get(unit, 1))


async def _fetch_magnet(client: httpx.AsyncClient, href: str) -> str | None:
    try:
        r = await client.get(_BASE + href)
        r.raise_for_status()
    except Exception:
        return None
    m = _MAGNET_RE.search(r.text)
    return m.group(1) if m else None


class X1337Indexer:
    name = "1337x"
    kind = SourceKind.torrent

    async def search(self, track: ResolvedTrack, limit: int = 8) -> list[Candidate]:
        q = (f"{track.artist} {track.album or track.title}").strip()
        url = f"{_BASE}/sort-category-search/{q.replace(' ', '+')}/Music/seeders/desc/1/"
        try:
            async with httpx.AsyncClient(
                timeout=15,
                headers=_HEADERS,
                follow_redirects=True,
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                listing = r.text

                hits = list(_RESULT_RE.finditer(listing))[:limit]
                if not hits:
                    return []

                # Resolve magnets in parallel.
                magnets = await asyncio.gather(
                    *(_fetch_magnet(client, m.group("href")) for m in hits),
                    return_exceptions=True,
                )
        except Exception as e:
            bus.emit("log", f"1337x search failed: {e}", level="warn")
            return []

        out: list[Candidate] = []
        for hit, magnet in zip(hits, magnets):
            if isinstance(magnet, Exception) or not magnet:
                continue
            seeders = int(hit.group("seeders") or 0)
            size = _parse_size(hit.group("size") or "")
            out.append(
                Candidate(
                    source=SourceKind.torrent,
                    url=magnet,
                    title=hit.group("name").strip(),
                    score=0.4 + min(seeders / 200, 0.5),
                    extra={
                        "indexer": "1337x",
                        "seeders": seeders,
                        "size": size,
                        "is_magnet": True,
                    },
                )
            )
        return out
