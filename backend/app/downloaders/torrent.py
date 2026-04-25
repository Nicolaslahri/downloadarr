from __future__ import annotations

from app.downloaders.base import DownloadResult
from app.indexers.base import Candidate, SourceKind
from app.services.events import bus
from app.services.torrents.engine import download as lt_download


class TorrentDownloader:
    name = "torrent"

    def supports(self, candidate: Candidate) -> bool:
        return candidate.source == SourceKind.torrent

    async def download(self, candidate: Candidate, dest_dir: str) -> DownloadResult:
        last_pct = -1

        def on_progress(done: int, total: int) -> None:
            nonlocal last_pct
            pct = int(done * 100 / max(total, 1))
            if pct != last_pct and pct % 10 == 0:
                bus.emit("log", f"torrent {candidate.title}: {pct}%")
                last_pct = pct

        result = await lt_download(candidate.url, dest_dir, progress=on_progress)
        return DownloadResult(
            file_path=str(result.file_path),
            bytes=result.bytes,
            format=result.file_path.suffix.lstrip(".").lower(),
        )
