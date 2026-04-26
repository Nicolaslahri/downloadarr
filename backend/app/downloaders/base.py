from dataclasses import dataclass
from typing import Optional, Protocol

from app.indexers.base import Candidate
from app.resolvers.base import ResolvedTrack
from app.services.progress import TrackProgress


@dataclass
class DownloadResult:
    file_path: str
    bytes: int
    bitrate_kbps: int | None = None
    format: str | None = None


class Downloader(Protocol):
    name: str

    def supports(self, candidate: Candidate) -> bool: ...

    async def download(
        self,
        candidate: Candidate,
        dest_dir: str,
        track: ResolvedTrack,
        progress: Optional[TrackProgress] = None,
    ) -> DownloadResult: ...
