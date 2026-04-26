from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack
from app.services.events import bus

_NYAA_NS = "{https://nyaa.si/xmlns/nyaa}"


_SIZE_RE = re.compile(r"([\d.]+)\s*([KMGT]i?B)", re.IGNORECASE)


def _parse_size(text: str) -> int:
    if not text:
        return 0
    m = _SIZE_RE.search(text)
    if not m:
        return 0
    value = float(m.group(1))
    unit = m.group(2).upper()
    multipliers = {
        "B": 1, "KB": 1000, "MB": 1_000_000, "GB": 1_000_000_000, "TB": 1_000_000_000_000,
        "KIB": 1024, "MIB": 1024 ** 2, "GIB": 1024 ** 3, "TIB": 1024 ** 4,
    }
    return int(value * multipliers.get(unit, 1))


class NyaaIndexer:
    """Nyaa.si RSS feed — best for OST / anime / Asian music. Stable
    XML format, no auth."""

    name = "nyaa"
    kind = SourceKind.torrent

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        # Category 2_0 = Audio (all).
        q = f"{track.artist} {track.album or track.title}"
        try:
            async with httpx.AsyncClient(
                timeout=12,
                headers={"User-Agent": "MusicDownloadarr/0.1"},
                follow_redirects=True,
            ) as client:
                r = await client.get(
                    "https://nyaa.si/",
                    params={"page": "rss", "q": q, "c": "2_0"},
                )
                r.raise_for_status()
                root = ET.fromstring(r.text)
        except Exception as e:
            bus.emit("log", f"nyaa search failed: {e}", level="warn")
            return []

        out: list[Candidate] = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            torrent_url = (item.findtext("link") or "").strip()
            ih = (item.findtext(f"{_NYAA_NS}infoHash") or "").strip()
            seeders = int(item.findtext(f"{_NYAA_NS}seeders") or "0")
            size = _parse_size(item.findtext(f"{_NYAA_NS}size") or "")
            if not title or (not torrent_url and not ih):
                continue
            url = (
                f"magnet:?xt=urn:btih:{ih}&dn={quote_plus(title)}" if ih else torrent_url
            )
            out.append(
                Candidate(
                    source=SourceKind.torrent,
                    url=url,
                    title=title,
                    score=0.4 + min(seeders / 100, 0.5),
                    extra={
                        "indexer": "nyaa",
                        "seeders": seeders,
                        "size": size,
                        "is_magnet": bool(ih),
                    },
                )
            )
        return out
