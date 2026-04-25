from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.downloaders.base import DownloadResult
from app.indexers.base import Candidate, SourceKind


def _download_sync(url: str, dest_dir: str) -> DownloadResult:
    from yt_dlp import YoutubeDL

    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    outtmpl = os.path.join(dest_dir, "%(id)s.%(ext)s")
    opts = {
        "quiet": True,
        "noprogress": True,
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }
        ],
        "noplaylist": True,
        "extractor_args": {"youtube": {"skip": ["dash"]}},
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    if not info:
        raise RuntimeError("yt-dlp returned no info")
    file_path = ydl.prepare_filename(info)
    # postprocessor changes extension to m4a
    final_path = os.path.splitext(file_path)[0] + ".m4a"
    if not os.path.exists(final_path):
        # fall back to whatever extension landed
        for ext in ("opus", "webm", "mp3", "m4a", "ogg"):
            cand = os.path.splitext(file_path)[0] + "." + ext
            if os.path.exists(cand):
                final_path = cand
                break
    size = os.path.getsize(final_path)
    return DownloadResult(
        file_path=final_path,
        bytes=size,
        bitrate_kbps=int(info.get("abr") or 0) or None,
        format=os.path.splitext(final_path)[1].lstrip("."),
    )


class YtDlpDownloader:
    name = "ytdlp"

    def supports(self, candidate: Candidate) -> bool:
        return candidate.source == SourceKind.ytdlp

    async def download(self, candidate: Candidate, dest_dir: str) -> DownloadResult:
        return await asyncio.to_thread(_download_sync, candidate.url, dest_dir)
