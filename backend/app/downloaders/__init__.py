from __future__ import annotations

from app.downloaders.base import DownloadResult, Downloader
from app.downloaders.qbittorrent import QbittorrentDownloader
from app.downloaders.sabnzbd import SabnzbdDownloader
from app.downloaders.ytdlp import YtDlpDownloader
from app.indexers.base import Candidate

__all__ = ["DownloadResult", "Downloader", "build_downloaders", "pick"]


def build_downloaders(cfg: dict[str, str]) -> list[Downloader]:
    return [
        YtDlpDownloader(),
        QbittorrentDownloader(
            url=cfg.get("qbt_url", ""),
            user=cfg.get("qbt_user", ""),
            password=cfg.get("qbt_pass", ""),
        ),
        SabnzbdDownloader(
            url=cfg.get("sab_url", ""),
            api_key=cfg.get("sab_api_key", ""),
        ),
    ]


def pick(candidate: Candidate, cfg: dict[str, str]) -> Downloader | None:
    for d in build_downloaders(cfg):
        if d.supports(candidate):
            return d
    return None
