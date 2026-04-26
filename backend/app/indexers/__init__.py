from __future__ import annotations

import asyncio
import json

from app.indexers.base import Candidate, Indexer, SourceKind
from app.indexers.free import NyaaIndexer, TorrentsCsvIndexer, X1337Indexer
from app.indexers.newznab import NewznabAggregateIndexer, NewznabIndexer
from app.indexers.torznab import TorznabAggregateIndexer, TorznabIndexer
from app.resolvers.base import ResolvedTrack

__all__ = ["Candidate", "Indexer", "SourceKind", "build_indexers", "search_all"]


def _parse_list(raw: str) -> list[dict]:
    try:
        data = json.loads(raw or "[]")
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _bool(cfg: dict[str, str], key: str, default: bool = True) -> bool:
    v = cfg.get(key)
    if v is None or v == "":
        return default
    return str(v).lower() not in ("0", "false", "no", "off")


def build_indexers(cfg: dict[str, str]) -> list[Indexer]:
    indexers: list[Indexer] = []

    # Newznab (Usenet)
    nzb_cfgs = _parse_list(cfg.get("usenet_indexers", "[]"))
    nzb_inst = [
        NewznabIndexer(c.get("name", "indexer"), c.get("url", ""), c.get("api_key", ""))
        for c in nzb_cfgs
        if c.get("url") and c.get("api_key")
    ]
    if nzb_inst:
        indexers.append(NewznabAggregateIndexer(nzb_inst))

    # Torznab (paid/subscription torrent indexers)
    tor_cfgs = _parse_list(cfg.get("torrent_indexers", "[]"))
    tor_inst = [
        TorznabIndexer(c.get("name", "tracker"), c.get("url", ""), c.get("api_key", ""))
        for c in tor_cfgs
        if c.get("url")
    ]
    if tor_inst:
        indexers.append(TorznabAggregateIndexer(tor_inst))

    # Free public torrent sources — toggleable, default ON since
    # they cost nothing.
    if _bool(cfg, "free_src_torrents_csv", True):
        indexers.append(TorrentsCsvIndexer())
    if _bool(cfg, "free_src_nyaa", True):
        indexers.append(NyaaIndexer())
    if _bool(cfg, "free_src_x1337", True):
        indexers.append(X1337Indexer())

    return indexers


async def search_all(track: ResolvedTrack, cfg: dict[str, str]) -> list[Candidate]:
    """Fan out across every configured indexer in parallel, then dedupe
    by URL/guid keeping the highest-scored copy. Same release on three
    trackers shouldn't show up three times in the candidates panel."""
    indexers = build_indexers(cfg)
    if not indexers:
        return []
    results = await asyncio.gather(
        *(i.search(track) for i in indexers),
        return_exceptions=True,
    )
    seen: dict[str, Candidate] = {}
    for r in results:
        if isinstance(r, Exception):
            continue
        for c in r:
            key = c.url
            if not key:
                continue
            existing = seen.get(key)
            if existing is None or c.score > existing.score:
                seen[key] = c
    return list(seen.values())
