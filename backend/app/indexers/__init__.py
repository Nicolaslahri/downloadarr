from __future__ import annotations

import asyncio
import json

from app.indexers.base import Candidate, Indexer, SourceKind
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


def build_indexers(cfg: dict[str, str]) -> list[Indexer]:
    """HQ-audio sources only. yt-dlp is used elsewhere for playlist
    enumeration but never as an audio source — we chase FLAC/320 here."""
    indexers: list[Indexer] = []

    nzb_cfgs = _parse_list(cfg.get("usenet_indexers", "[]"))
    nzb_inst = [
        NewznabIndexer(c.get("name", "indexer"), c.get("url", ""), c.get("api_key", ""))
        for c in nzb_cfgs
        if c.get("url") and c.get("api_key")
    ]
    if nzb_inst:
        indexers.append(NewznabAggregateIndexer(nzb_inst))

    tor_cfgs = _parse_list(cfg.get("torrent_indexers", "[]"))
    tor_inst = [
        TorznabIndexer(c.get("name", "tracker"), c.get("url", ""), c.get("api_key", ""))
        for c in tor_cfgs
        if c.get("url")
    ]
    if tor_inst:
        indexers.append(TorznabAggregateIndexer(tor_inst))

    return indexers


async def search_all(track: ResolvedTrack, cfg: dict[str, str]) -> list[Candidate]:
    indexers = build_indexers(cfg)
    if not indexers:
        return []
    results = await asyncio.gather(
        *(i.search(track) for i in indexers),
        return_exceptions=True,
    )
    out: list[Candidate] = []
    for r in results:
        if isinstance(r, Exception):
            continue
        out.extend(r)
    return out
