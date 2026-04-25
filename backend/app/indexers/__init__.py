from __future__ import annotations

import asyncio

from app.indexers.base import Candidate, Indexer, SourceKind
from app.indexers.nzbhydra import NzbHydraIndexer
from app.indexers.prowlarr import ProwlarrIndexer
from app.indexers.spotdl import SpotdlIndexer
from app.indexers.ytdlp import YtDlpIndexer
from app.resolvers.base import ResolvedTrack

__all__ = ["Candidate", "Indexer", "SourceKind", "build_indexers", "search_all"]


def build_indexers(cfg: dict[str, str]) -> list[Indexer]:
    indexers: list[Indexer] = [YtDlpIndexer(), SpotdlIndexer()]
    if cfg.get("prowlarr_url") and cfg.get("prowlarr_api_key"):
        indexers.append(
            ProwlarrIndexer(cfg["prowlarr_url"], cfg["prowlarr_api_key"])
        )
    if cfg.get("nzbhydra_url") and cfg.get("nzbhydra_api_key"):
        indexers.append(
            NzbHydraIndexer(cfg["nzbhydra_url"], cfg["nzbhydra_api_key"])
        )
    return indexers


async def search_all(track: ResolvedTrack, cfg: dict[str, str]) -> list[Candidate]:
    indexers = build_indexers(cfg)
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
