from dataclasses import dataclass
from typing import Protocol

from app.indexers.base import Candidate


@dataclass
class DownloadResult:
    file_path: str
    bytes: int


class Downloader(Protocol):
    name: str

    def supports(self, candidate: Candidate) -> bool: ...

    async def download(self, candidate: Candidate, dest_dir: str) -> DownloadResult: ...
