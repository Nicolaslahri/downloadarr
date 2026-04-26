"""Pre-download filtering of indexer candidates.

Stops the pipeline from picking obvious false positives — audiobooks
named the same as a song, video releases that happen to mention the
artist, album-sized payloads when we know we want a single track from
a different album, etc.
"""
from __future__ import annotations

import re

from app.indexers.base import Candidate
from app.resolvers.base import ResolvedTrack

# Substrings that almost always mean "not a music release for our
# purposes". Matched case-insensitively against the candidate title.
_NON_MUSIC_MARKERS = [
    # Audiobook formats
    "audiobook", ".m4b", " m4b ", "[m4b]", "(m4b)",
    ".aax", " aax ", "[aax]",
    "audible",
    # Video formats / encodes
    ".mkv", "[mkv]", " mkv ",
    ".mp4 ", "[mp4]",
    "1080p", "720p", "2160p", "4k uhd", "bluray", "bdrip",
    "x264", "x265", " h.264", " h.265", "hevc", "av1 ",
    "webrip", "web-dl", "hdrip", "dvdrip",
    # Disc images
    ".iso", "[iso]",
]


def _norm_for_match(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower())


def _non_music_marker(title: str) -> str | None:
    low = title.lower()
    for marker in _NON_MUSIC_MARKERS:
        if marker in low:
            return marker.strip()
    return None


def _album_words(track: ResolvedTrack) -> list[str]:
    if not track.album:
        return []
    raw = re.split(r"\s+", track.album.lower())
    # Skip stop-words that frequently appear in album names but aren't
    # discriminative on their own.
    stop = {"the", "and", "of", "a", "an", "to", "in", "for", "on", "edition"}
    return [w for w in raw if len(w) > 2 and w not in stop]


def _plausible_size_max(track: ResolvedTrack) -> int | None:
    """Return the largest plausible release size in bytes for this track,
    or None if we can't make a guess (no duration known)."""
    if not track.duration_s:
        return None
    minutes = max(1.0, track.duration_s / 60.0)
    # Lossless ceiling: ~12 MB/min. Padding for parity files + metadata.
    per_min = 14 * 1024 * 1024
    if track.album:
        # An album release: assume up to 20 tracks averaging same length.
        return int(per_min * minutes * 20)
    # A standalone single: a few MB to maybe 60 MB tops.
    return int(per_min * minutes * 4)


def filter_candidates(
    candidates: list[Candidate], track: ResolvedTrack
) -> tuple[list[Candidate], list[tuple[Candidate, str]]]:
    """Drop obviously-wrong candidates before we waste bandwidth.

    Returns (kept, rejected_with_reason). Both lists preserve input order.
    """
    kept: list[Candidate] = []
    rejected: list[tuple[Candidate, str]] = []

    album_words = _album_words(track)
    size_cap = _plausible_size_max(track)

    for c in candidates:
        # 1. Format / category blacklist — audiobook / video / disc image.
        marker = _non_music_marker(c.title)
        if marker:
            rejected.append((c, f"non-music release type ({marker})"))
            continue

        title_norm = _norm_for_match(c.title)

        # 2. Album cross-check — when MusicBrainz gave us an album name,
        #    the candidate must contain at least half of its meaningful
        #    words (skipping stop-words). A release that doesn't mention
        #    the album is almost always for a different album by the
        #    same artist.
        if album_words:
            hits = sum(1 for w in album_words if w in title_norm)
            needed = max(1, len(album_words) // 2)
            if hits < needed:
                rejected.append(
                    (c, f"album {track.album!r} not in release title (hit {hits}/{len(album_words)} words)")
                )
                continue

        # 3. Size sanity — reject releases too big to plausibly contain
        #    only the album our track lives on.
        size = int((c.extra or {}).get("size") or 0)
        if size_cap and size and size > size_cap:
            rejected.append(
                (c, f"size {size/1024/1024:.0f}MB > plausible cap {size_cap/1024/1024:.0f}MB")
            )
            continue

        kept.append(c)

    return kept, rejected
