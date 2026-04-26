"""MusicBrainz lookups for enriching track metadata before indexer search.

Pre-search enrichment is the biggest single accuracy win — instead of
asking Usenet/torrent indexers for "Chris Brown Under The Influence"
and praying, we first ask MusicBrainz "what album is this song on" and
then the indexer query becomes "Chris Brown Indigo" — which actually
exists as a release.

Free, no API key. Just polite User-Agent and ~1 req/sec.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Optional

import httpx

from app.services.events import bus

USER_AGENT = "MusicDownloadarr/0.1 (https://github.com/Nicolaslahri/downloadarr)"
MB_BASE = "https://musicbrainz.org/ws/2"

# MusicBrainz asks for max 1 req/sec from anonymous clients. We serialize
# globally — the cost is negligible vs the time saved on better matches.
_RATE_LOCK = asyncio.Lock()


@dataclass
class EnrichedTrack:
    artist: str
    title: str
    album: Optional[str] = None
    track_no: Optional[int] = None
    year: Optional[int] = None
    duration_s: Optional[int] = None
    isrc: Optional[str] = None
    mb_recording_id: Optional[str] = None
    mb_release_id: Optional[str] = None


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _lucene_escape(s: str) -> str:
    # Bare-minimum escape for the MB query DSL.
    s = s.replace("\\", "")
    return s.replace('"', '\\"')


def _release_score(rel: dict) -> float:
    """Higher is better. Prefer official Album, penalize compilations,
    nudge toward earlier original releases."""
    s = 0.0
    group = rel.get("release-group") or {}
    primary = (group.get("primary-type") or "").lower()
    secondary = [t.lower() for t in (group.get("secondary-types") or [])]
    if primary == "album":
        s += 2.0
    elif primary == "single":
        s += 1.0
    elif primary == "ep":
        s += 1.5
    if "compilation" in secondary:
        s -= 0.8
    if "live" in secondary:
        s -= 0.4
    if "remix" in secondary:
        s -= 0.3
    if "soundtrack" in secondary:
        s -= 0.2
    date = rel.get("date") or ""
    try:
        year = int(date[:4]) if date else 9999
    except ValueError:
        year = 9999
    s -= year / 100000.0  # tiny preference for earlier originals
    if rel.get("status", "").lower() == "official":
        s += 0.3
    return s


def _track_no_for(rec_id: str, rec_title: str, release: dict) -> Optional[int]:
    target_title = _norm(rec_title)
    for medium in release.get("media") or []:
        for trk in medium.get("track") or []:
            same_id = trk.get("recording", {}).get("id") == rec_id
            if same_id or _norm(trk.get("title") or "") == target_title:
                num = trk.get("number") or trk.get("position")
                if num is not None:
                    try:
                        return int(num)
                    except (ValueError, TypeError):
                        return None
    return None


def _artist_variants(artist: str) -> list[str]:
    """Yield candidate artist strings to try in order of preference.

    For 'RAYE, 070 Shake' we try the full string first, then 'RAYE'
    alone; multi-artist tracks are common and MB sometimes credits
    only the lead artist on the recording."""
    out = [artist.strip()]
    parts = re.split(r"\s*[,/&]\s*|\s+feat\.?\s+|\s+ft\.?\s+", artist, maxsplit=1)
    if len(parts) > 1 and parts[0].strip() and parts[0].strip() not in out:
        out.append(parts[0].strip())
    return out


def _clean_title(title: str) -> str:
    """Strip trailing punctuation/parentheticals that confuse MB scoring."""
    cleaned = title.strip()
    # Drop trailing periods/exclaim/question
    cleaned = re.sub(r"[.!?]+$", "", cleaned)
    # Drop a single trailing parenthetical that looks like an annotation
    cleaned = re.sub(
        r"\s*[\(\[][^\)\]]{0,40}(official|video|audio|lyric[s]?|hd|hq|4k|mv|remix)[^\)\]]{0,40}[\)\]]\s*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


async def _mb_search(client: httpx.AsyncClient, artist: str, title: str) -> list[dict]:
    query = f'recording:"{_lucene_escape(title)}" AND artist:"{_lucene_escape(artist)}"'
    try:
        r = await client.get(
            f"{MB_BASE}/recording/",
            params={"query": query, "fmt": "json", "limit": 10},
        )
        r.raise_for_status()
        return (r.json() or {}).get("recordings") or []
    except Exception:
        return []


async def enrich(
    artist: str, title: str, duration_s: Optional[int] = None
) -> Optional[EnrichedTrack]:
    """Best-effort lookup. Returns None when MB has no confident match."""
    if not artist or not title:
        return None

    title_clean = _clean_title(title)
    artist_attempts = _artist_variants(artist)

    recordings: list[dict] = []
    async with _RATE_LOCK:
        async with httpx.AsyncClient(
            timeout=15,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        ) as client:
            for attempt_artist in artist_attempts:
                recordings = await _mb_search(client, attempt_artist, title_clean)
                if recordings:
                    bus.emit(
                        "log",
                        f"MB: {len(recordings)} recordings for {attempt_artist!r} – {title_clean!r}",
                    )
                    break
                await asyncio.sleep(1.0)
        await asyncio.sleep(1.0)

    if not recordings:
        return None

    # Score each recording.
    target_artist = _norm(artist)
    target_title = _norm(title_clean)
    best, best_score = None, -1.0
    for rec in recordings:
        score = float(rec.get("score") or 0) / 100.0
        rec_artist = " ".join(c.get("name", "") for c in (rec.get("artist-credit") or []))
        if _norm(rec_artist) == target_artist:
            score += 0.3
        elif target_artist in _norm(rec_artist):
            score += 0.1
        if _norm(rec.get("title") or "") == target_title:
            score += 0.2
        if duration_s and rec.get("length"):
            diff = abs(rec["length"] / 1000 - duration_s)
            if diff < 5:
                score += 0.3
            elif diff < 15:
                score += 0.1
        if score > best_score:
            best, best_score = rec, score

    if not best or best_score < 0.7:
        return None

    # Now we need release info — sometimes /recording results don't
    # include releases or media. Re-fetch with release expansion.
    rec_id = best.get("id")
    if not rec_id:
        return None

    async with _RATE_LOCK:
        try:
            async with httpx.AsyncClient(
                timeout=15,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            ) as client:
                r2 = await client.get(
                    f"{MB_BASE}/recording/{rec_id}",
                    params={"inc": "releases+release-groups+media", "fmt": "json"},
                )
                r2.raise_for_status()
                detail = r2.json()
        except Exception as e:
            bus.emit("log", f"MusicBrainz recording detail failed: {e}", level="warn")
            await asyncio.sleep(1.0)
            detail = best
        await asyncio.sleep(1.0)

    releases = detail.get("releases") or best.get("releases") or []
    best_release = max(releases, key=_release_score) if releases else {}

    album = best_release.get("title")
    year = None
    date = best_release.get("date")
    if date:
        try:
            year = int(date[:4])
        except ValueError:
            year = None

    track_no = _track_no_for(rec_id, detail.get("title") or title, best_release) if best_release else None
    length_ms = detail.get("length") or best.get("length")

    return EnrichedTrack(
        artist=artist,
        title=detail.get("title") or best.get("title") or title,
        album=album,
        track_no=track_no,
        year=year,
        duration_s=int(length_ms / 1000) if length_ms else duration_s,
        mb_recording_id=rec_id,
        mb_release_id=best_release.get("id") if best_release else None,
    )
