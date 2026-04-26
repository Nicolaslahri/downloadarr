"""Pre-download filtering of indexer candidates.

Stops the pipeline from picking obvious false positives — audiobooks
named the same as a song, video releases that happen to mention the
artist, releases by a different artist whose name happens to share a
substring with ours, album-sized payloads for a single, etc.
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

_STOP = {"the", "and", "of", "a", "an", "to", "in", "for", "on", "edition", "feat", "ft"}


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
    return [w for w in raw if len(w) > 2 and w not in _STOP]


def _artist_words(track: ResolvedTrack) -> list[str]:
    """Words from the *primary* artist. Splits on comma / slash / & /
    feat so 'RAYE, 070 Shake' yields ['raye'] not ['raye', '070', 'shake']."""
    if not track.artist:
        return []
    primary = re.split(
        r"\s*[,/&]\s*|\s+feat\.?\s+|\s+ft\.?\s+",
        track.artist,
        maxsplit=1,
    )[0]
    raw = re.split(r"\s+", primary.lower())
    return [w for w in raw if len(w) > 1 and w not in _STOP]


def _title_words(track: ResolvedTrack) -> list[str]:
    if not track.title:
        return []
    raw = re.split(r"\s+", track.title.lower().rstrip(".!?,;"))
    return [w for w in raw if len(w) > 2 and w not in _STOP]


def _plausible_size_max(track: ResolvedTrack) -> int | None:
    if not track.duration_s:
        return None
    minutes = max(1.0, track.duration_s / 60.0)
    per_min = 14 * 1024 * 1024
    if track.album:
        return int(per_min * minutes * 20)
    return int(per_min * minutes * 4)


def _word_match_count(words: list[str], haystack: str) -> int:
    """Match each word as its own token (so 'ray' doesn't match
    'ray_hawthorne'). Words are matched against tokens in the
    space-normalized haystack."""
    if not words:
        return 0
    tokens = set(haystack.split())
    return sum(1 for w in words if w in tokens)


def filter_candidates(
    candidates: list[Candidate], track: ResolvedTrack
) -> tuple[list[Candidate], list[tuple[Candidate, str]]]:
    """Drop obviously-wrong candidates before we waste bandwidth.

    Returns (kept, rejected_with_reason). Both lists preserve input order.
    """
    kept: list[Candidate] = []
    rejected: list[tuple[Candidate, str]] = []

    artist_words = _artist_words(track)
    album_words = _album_words(track)
    title_words = _title_words(track)
    size_cap = _plausible_size_max(track)

    for c in candidates:
        # 1. Format / category blacklist — audiobook / video / disc image.
        marker = _non_music_marker(c.title)
        if marker:
            rejected.append((c, f"non-music release type ({marker})"))
            continue

        title_norm = _norm_for_match(c.title)

        # 2. ARTIST cross-check — strongest signal when no album info is
        #    available. Token-based match so 'ray' doesn't accidentally
        #    match 'ray_hawthorne' (the actual failure case we saw).
        if artist_words:
            hits = _word_match_count(artist_words, title_norm)
            needed = max(1, (len(artist_words) + 1) // 2)
            if hits < needed:
                rejected.append(
                    (c, f"artist {track.artist!r} not in release (matched {hits}/{len(artist_words)})")
                )
                continue

        # 3. Album cross-check — when MusicBrainz gave us an album name.
        if album_words:
            hits = _word_match_count(album_words, title_norm)
            needed = max(1, len(album_words) // 2)
            if hits < needed:
                rejected.append(
                    (c, f"album {track.album!r} not in release (matched {hits}/{len(album_words)})")
                )
                continue
        elif title_words:
            # 3b. No album → require at least one title word in the release.
            #     Keeps us from grabbing 'RAYE — Some Other Song' for
            #     'Escapism.'.
            hits = _word_match_count(title_words, title_norm)
            if hits == 0:
                rejected.append(
                    (c, f"title {track.title!r} not in release name")
                )
                continue

        # 4. Size sanity.
        size = int((c.extra or {}).get("size") or 0)
        if size_cap and size and size > size_cap:
            rejected.append(
                (c, f"size {size/1024/1024:.0f}MB > plausible cap {size_cap/1024/1024:.0f}MB")
            )
            continue

        kept.append(c)

    return kept, rejected
