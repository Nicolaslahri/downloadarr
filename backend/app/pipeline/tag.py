from __future__ import annotations

import asyncio
from pathlib import Path

from app.resolvers.base import ResolvedTrack


def _tag_sync(file_path: str, track: ResolvedTrack) -> None:
    p = Path(file_path)
    ext = p.suffix.lower()
    try:
        if ext == ".m4a" or ext == ".mp4":
            from mutagen.mp4 import MP4
            f = MP4(file_path)
            f["\xa9nam"] = [track.title]
            f["\xa9ART"] = [track.artist]
            if track.album:
                f["\xa9alb"] = [track.album]
            f.save()
        elif ext == ".mp3":
            from mutagen.easyid3 import EasyID3
            from mutagen.mp3 import MP3
            try:
                f = EasyID3(file_path)
            except Exception:
                m = MP3(file_path)
                m.add_tags()
                m.save()
                f = EasyID3(file_path)
            f["title"] = track.title
            f["artist"] = track.artist
            if track.album:
                f["album"] = track.album
            f.save()
        elif ext in (".flac", ".ogg", ".opus"):
            from mutagen import File
            f = File(file_path)
            if f is None:
                return
            f["title"] = track.title
            f["artist"] = track.artist
            if track.album:
                f["album"] = track.album
            f.save()
    except Exception:
        # Tagging best-effort; never fail the pipeline over metadata.
        pass


async def tag_file(file_path: str, track: ResolvedTrack) -> None:
    await asyncio.to_thread(_tag_sync, file_path, track)
