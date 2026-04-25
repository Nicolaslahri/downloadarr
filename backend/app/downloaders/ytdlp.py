from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from app.downloaders.base import DownloadResult
from app.indexers.base import Candidate, SourceKind


def _download_sync(url: str, dest_dir: str) -> DownloadResult:
    from yt_dlp import YoutubeDL

    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    outtmpl = os.path.join(dest_dir, "%(id)s.%(ext)s")

    has_ffmpeg = bool(shutil.which("ffmpeg"))

    # Prefer YouTube's native audio formats so we don't need ffmpeg to
    # transcode. m4a is best for tagging; opus/webm work too. Only fall
    # back to "bestaudio" (which may need transcoding) when ffmpeg exists.
    fmt = (
        "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=opus]/bestaudio[ext=ogg]/bestaudio"
        if not has_ffmpeg
        else "bestaudio/best"
    )

    opts: dict = {
        "quiet": True,
        "noprogress": True,
        "format": fmt,
        "outtmpl": outtmpl,
        "noplaylist": True,
        "ignoreerrors": False,
    }

    # Only add the FFmpegExtractAudio postprocessor when ffmpeg is around;
    # without it, yt-dlp errors after the download.
    if has_ffmpeg:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",
            }
        ]

    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    if not info:
        raise RuntimeError("yt-dlp returned no info")

    file_path = ydl.prepare_filename(info)
    if has_ffmpeg:
        # postprocessor changes ext to m4a
        file_path = os.path.splitext(file_path)[0] + ".m4a"

    if not os.path.exists(file_path):
        stem = os.path.splitext(file_path)[0]
        for ext in ("m4a", "opus", "webm", "ogg", "mp3", "aac"):
            cand = f"{stem}.{ext}"
            if os.path.exists(cand):
                file_path = cand
                break

    size = os.path.getsize(file_path)
    return DownloadResult(
        file_path=file_path,
        bytes=size,
        bitrate_kbps=int(info.get("abr") or 0) or None,
        format=os.path.splitext(file_path)[1].lstrip("."),
    )


class YtDlpDownloader:
    name = "ytdlp"

    def supports(self, candidate: Candidate) -> bool:
        return candidate.source == SourceKind.ytdlp

    async def download(self, candidate: Candidate, dest_dir: str) -> DownloadResult:
        return await asyncio.to_thread(_download_sync, candidate.url, dest_dir)
