from __future__ import annotations

import os
from pathlib import Path

from typing import Optional

from app.downloaders.base import DownloadResult
from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack
from app.services.events import bus
from app.services.progress import TrackProgress
from app.services.torrents.engine import download as lt_download
from app.services.track_picker import pick_track_file
from app.services.usenet.postproc import find_audio_files


class TorrentDownloader:
    name = "torrent"

    def supports(self, candidate: Candidate) -> bool:
        return candidate.source == SourceKind.torrent

    async def download(
        self,
        candidate: Candidate,
        dest_dir: str,
        track: ResolvedTrack,
        progress: Optional[TrackProgress] = None,
    ) -> DownloadResult:
        last_pct = -1

        def on_progress(done: int, total: int) -> None:
            nonlocal last_pct
            pct = int(done * 100 / max(total, 1))
            if pct != last_pct and pct % 10 == 0:
                bus.emit("log", f"torrent {candidate.title}: {pct}%")
                last_pct = pct

        async def on_bytes(done: int, total: int) -> None:
            if progress is not None:
                await progress.update(done, total)

        result = await lt_download(
            candidate.url, dest_dir,
            progress=on_progress,
            bytes_progress=on_bytes,
        )

        # libtorrent already returns the largest audio file, but if the
        # torrent is an album we want a specific track. Re-scan the save
        # path for all audio files and pass through the picker.
        save_path = Path(dest_dir)
        all_audio = find_audio_files(save_path)
        # Restrict to files inside the torrent's content tree if possible.
        if result.file_path.parent.exists():
            inside = [p for p in all_audio if str(p).startswith(str(result.file_path.parent))]
            if inside:
                all_audio = inside

        pick = pick_track_file(all_audio, track)
        if pick is None:
            # If picker can't decide, fall back to libtorrent's choice.
            chosen = result.file_path
            bus.emit(
                "log",
                f"track-picker: no confident match in torrent; falling back to {chosen.name}",
                level="warn",
            )
        else:
            chosen = pick.path
            bus.emit(
                "log",
                f"track-picker: chose {chosen.name} (score={pick.score:.2f} — {', '.join(pick.reasons)})",
            )

        return DownloadResult(
            file_path=str(chosen),
            bytes=chosen.stat().st_size,
            format=chosen.suffix.lstrip(".").lower(),
        )
