from __future__ import annotations

from app.downloaders.base import DownloadResult, Downloader
from app.downloaders.nntp import NntpDownloader
from app.downloaders.torrent import TorrentDownloader
from app.downloaders.ytdlp import YtDlpDownloader
from app.indexers.base import Candidate

__all__ = ["DownloadResult", "Downloader", "build_downloaders", "pick"]


def build_downloaders(cfg: dict[str, str]) -> list[Downloader]:
    return [
        YtDlpDownloader(),
        NntpDownloader(server_cfgs_json=cfg.get("usenet_servers", "[]")),
        TorrentDownloader(),
    ]


def pick(candidate: Candidate, cfg: dict[str, str]) -> Downloader | None:
    for d in build_downloaders(cfg):
        if d.supports(candidate):
            return d
    return None
