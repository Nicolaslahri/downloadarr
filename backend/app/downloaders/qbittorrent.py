from __future__ import annotations

from app.downloaders.base import DownloadResult
from app.indexers.base import Candidate, SourceKind


class QbittorrentDownloader:
    """Placeholder — wires to qBittorrent's WebUI API to add a torrent
    and poll for completion. Returns the downloaded audio file path
    after move-on-complete.
    """

    name = "qbittorrent"

    def __init__(self, url: str = "", user: str = "", password: str = ""):
        self.url = url
        self.user = user
        self.password = password

    def supports(self, candidate: Candidate) -> bool:
        return candidate.source == SourceKind.torrent and bool(self.url)

    async def download(self, candidate: Candidate, dest_dir: str) -> DownloadResult:
        raise NotImplementedError(
            "qBittorrent downloader is wired only for stubbed candidates yet — "
            "configure qBittorrent in Settings and we'll add an audio torrent and poll."
        )
