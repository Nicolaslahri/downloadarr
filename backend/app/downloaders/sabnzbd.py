from __future__ import annotations

from app.downloaders.base import DownloadResult
from app.indexers.base import Candidate, SourceKind


class SabnzbdDownloader:
    name = "sabnzbd"

    def __init__(self, url: str = "", api_key: str = ""):
        self.url = url
        self.api_key = api_key

    def supports(self, candidate: Candidate) -> bool:
        return candidate.source == SourceKind.nzb and bool(self.url)

    async def download(self, candidate: Candidate, dest_dir: str) -> DownloadResult:
        raise NotImplementedError(
            "SABnzbd downloader stub — configure SAB in Settings and we'll POST the NZB and poll."
        )
