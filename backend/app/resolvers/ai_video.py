from __future__ import annotations

import asyncio
import json
import re
from urllib.parse import urlparse

from app.resolvers.base import ResolvedPlaylist, ResolvedTrack
from app.services.events import bus


def _is_yt_video(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").replace("www.", "")
    except Exception:
        return False
    if host not in {"youtube.com", "youtu.be", "m.youtube.com"}:
        return False
    p = urlparse(url)
    return "list=" not in (p.query or "") and "/playlist" not in p.path


def _fetch_metadata_sync(url: str) -> dict:
    from yt_dlp import YoutubeDL

    with YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    return info or {}


_TRACKLIST_LINE = re.compile(
    r"""
    ^\s*
    (?:\d+[.)\]:]?\s*)?            # leading index
    (?:\(?\d{1,2}:\d{2}(?::\d{2})?\)?\s*[-–—:]?\s*)?  # timestamp
    ([^—–\-:]{2,80}?)              # artist
    \s*[—–\-:]\s*
    ([^—–\-:][^\n]{1,120}?)        # title
    \s*$
    """,
    re.MULTILINE | re.VERBOSE,
)


def _heuristic_extract(description: str) -> list[ResolvedTrack]:
    out: list[ResolvedTrack] = []
    for m in _TRACKLIST_LINE.finditer(description):
        artist = m.group(1).strip().strip("'\"")
        title = m.group(2).strip().strip("'\"")
        if len(artist) < 2 or len(title) < 2:
            continue
        if any(skip in artist.lower() for skip in ["http", "www", "subscribe"]):
            continue
        out.append(ResolvedTrack(artist=artist, title=title))
    return out


def _chapters_to_tracks(chapters: list[dict]) -> list[ResolvedTrack]:
    out: list[ResolvedTrack] = []
    for ch in chapters or []:
        title = (ch.get("title") or "").strip()
        if not title:
            continue
        artist = "Unknown"
        if " - " in title:
            artist, _, title = title.partition(" - ")
            artist = artist.strip()
            title = title.strip()
        out.append(ResolvedTrack(artist=artist, title=title))
    return out


SYSTEM_PROMPT = """\
You extract a structured tracklist from a YouTube video's metadata.
Return ONLY JSON of the form:
{"tracks": [{"artist": "...", "title": "...", "start_ts": 123 | null}]}

Rules:
- One entry per song; do NOT include intros, outros, or non-music chatter.
- "artist" is the performer of the recording. If the video is a DJ set or
  a "Top X" compilation, each row is a different artist.
- "title" is the song title without the artist prefix.
- Skip lines with URLs, social handles, or sponsorship mentions.
- If you cannot find any songs, return {"tracks": []}.
- Output JSON only — no prose, no markdown fences.
"""


async def _llm_extract(text: str, api_key: str) -> list[ResolvedTrack]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    msg = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    try:
        data = json.loads(raw)
    except Exception:
        return []
    tracks_data = data.get("tracks") or []
    out: list[ResolvedTrack] = []
    for t in tracks_data:
        if not isinstance(t, dict):
            continue
        artist = (t.get("artist") or "").strip()
        title = (t.get("title") or "").strip()
        if not artist or not title:
            continue
        out.append(ResolvedTrack(artist=artist, title=title))
    return out


class AIVideoResolver:
    name = "ai_video"

    def __init__(self, anthropic_api_key: str = ""):
        self.api_key = anthropic_api_key

    def detect(self, url: str) -> bool:
        return _is_yt_video(url)

    async def resolve(self, url: str) -> ResolvedPlaylist:
        info = await asyncio.to_thread(_fetch_metadata_sync, url)
        title = info.get("title") or "YouTube Video"
        description = info.get("description") or ""
        chapters = info.get("chapters") or []
        bus.emit(
            "log",
            f"AI extract: title='{title}', chapters={len(chapters)}, desc={len(description)}ch",
        )

        tracks: list[ResolvedTrack] = []

        if chapters:
            tracks = _chapters_to_tracks(chapters)
            bus.emit("log", f"AI extract: {len(tracks)} tracks from chapters")

        if len(tracks) < 5:
            heur = _heuristic_extract(description)
            if len(heur) >= 5:
                tracks = heur
                bus.emit("log", f"AI extract: {len(tracks)} tracks via regex")

        if len(tracks) < 5 and self.api_key and description:
            llm = await _llm_extract(
                f"Video title: {title}\n\nDescription:\n{description}",
                self.api_key,
            )
            if llm:
                tracks = llm
                bus.emit("log", f"AI extract: {len(tracks)} tracks via Claude")

        if not tracks:
            raise RuntimeError(
                "Couldn't find any tracks in the video. "
                "Set ANTHROPIC_API_KEY in Settings for the AI fallback, "
                "or paste a video that has a tracklist in its description/chapters."
            )

        return ResolvedPlaylist(
            source="ai_video", source_url=url, name=title, tracks=tracks
        )
