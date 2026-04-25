from __future__ import annotations

import asyncio

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack


def _search_sync(query: str, limit: int = 5) -> list[dict]:
    from yt_dlp import YoutubeDL

    opts = {"quiet": True, "skip_download": True, "default_search": f"ytsearch{limit}"}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
    return (info or {}).get("entries") or []


class YtDlpIndexer:
    name = "ytdlp"
    kind = SourceKind.ytdlp

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        if track.source_url_hint:
            return [
                Candidate(
                    source=SourceKind.ytdlp,
                    url=track.source_url_hint,
                    title=f"{track.artist} - {track.title}",
                    duration_s=track.duration_s,
                    score=1.0,
                )
            ]
        query = f"{track.artist} {track.title} audio"
        results = await asyncio.to_thread(_search_sync, query, 5)
        out: list[Candidate] = []
        for r in results:
            if not r:
                continue
            url = r.get("webpage_url") or (
                f"https://www.youtube.com/watch?v={r['id']}" if r.get("id") else None
            )
            if not url:
                continue
            duration = r.get("duration")
            score = 0.5
            if track.duration_s and duration:
                # Reward duration similarity
                diff = abs(duration - track.duration_s)
                score += max(0.0, 0.5 - diff / 60)
            out.append(
                Candidate(
                    source=SourceKind.ytdlp,
                    url=url,
                    title=r.get("title") or query,
                    duration_s=int(duration) if duration else None,
                    score=score,
                )
            )
        return out
