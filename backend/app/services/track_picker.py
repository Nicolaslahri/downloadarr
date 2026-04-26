"""Pick the right audio file out of an album-shaped release.

When NZBGeek hands us 'Chris Brown - Indigo (2019) [FLAC]' for a track
that's just one song on that album, the work dir ends up with 19
.flac files. We need exactly one of them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.resolvers.base import ResolvedTrack


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


@dataclass
class PickResult:
    path: Path
    score: float
    reasons: list[str]


def _read_tags(path: Path) -> tuple[str, float | None, str | None]:
    """Return (title, length_s, mb_recording_id)."""
    try:
        from mutagen import File as MutaFile  # type: ignore

        audio = MutaFile(str(path))
    except Exception:
        return "", None, None
    if audio is None:
        return "", None, None
    title = ""
    mbid = None
    tags = getattr(audio, "tags", None)
    if tags:
        for key in ("TIT2", "title", "\xa9nam", "Title", "TITLE"):
            val = None
            try:
                val = tags.get(key)
            except Exception:
                continue
            if val:
                if isinstance(val, list):
                    title = str(val[0]).strip()
                else:
                    title = str(val).strip()
                break
        for key in ("UFID:http://musicbrainz.org", "musicbrainz_trackid", "MUSICBRAINZ_TRACKID"):
            try:
                val = tags.get(key)
            except Exception:
                continue
            if val:
                mbid = str(val[0] if isinstance(val, list) else val).strip()
                break
    length = None
    info = getattr(audio, "info", None)
    if info is not None:
        length = getattr(info, "length", None)
    return title, length, mbid


def _score_file(p: Path, track: ResolvedTrack) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    name = p.stem
    name_norm = _norm(name)
    title_norm = _norm(track.title)

    # Filename heuristics
    if track.track_no:
        m = re.match(r"^\s*0*(\d{1,3})[\s\.\-_]", name)
        if m:
            try:
                if int(m.group(1)) == track.track_no:
                    score += 1.5
                    reasons.append(f"track no {track.track_no} prefix")
            except ValueError:
                pass

    if title_norm and title_norm in name_norm:
        score += 2.0
        reasons.append("title in filename")
    elif title_norm and len(title_norm) > 4:
        # Partial token match
        title_words = [w for w in re.split(r"\s+", track.title.lower()) if len(w) > 2]
        hits = sum(1 for w in title_words if _norm(w) in name_norm)
        if title_words and hits == len(title_words):
            score += 1.5
            reasons.append("all title words in filename")
        elif hits >= max(1, len(title_words) // 2):
            score += 0.5

    # Mutagen probe — tags + duration
    tag_title, length, mbid = _read_tags(p)
    if track.mb_recording_id and mbid and mbid == track.mb_recording_id:
        score += 5.0
        reasons.append("MB recording id")
    if tag_title:
        if _norm(tag_title) == title_norm:
            score += 2.0
            reasons.append("tag title exact")
        elif title_norm in _norm(tag_title):
            score += 0.8
            reasons.append("tag title contains")

    if track.duration_s and length:
        diff = abs(length - track.duration_s)
        if diff < 3:
            score += 1.0
            reasons.append(f"duration ±{diff:.0f}s")
        elif diff < 10:
            score += 0.3

    return score, reasons


def pick_track_file(
    audio_files: list[Path],
    track: ResolvedTrack,
) -> Optional[PickResult]:
    if not audio_files:
        return None
    if len(audio_files) == 1:
        return PickResult(path=audio_files[0], score=10.0, reasons=["only audio file"])

    scored: list[tuple[float, list[str], Path]] = []
    for p in audio_files:
        s, reasons = _score_file(p, track)
        scored.append((s, reasons, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_reasons, best_path = scored[0]
    if best_score >= 1.0:
        return PickResult(path=best_path, score=best_score, reasons=best_reasons)

    # No clear winner — refuse to guess randomly.
    return None
