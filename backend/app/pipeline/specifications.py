"""Concrete specifications that run on every indexer candidate.

Priority groups (lower runs first; same-priority specs all run together,
short-circuit on any reject):

    5  — parse  (no-op spec; populates parsed-release cache)
    10 — format-blacklist (audiobook/video/disc image)
    20 — artist-match (parsed artist must reference our artist)
    25 — album-match OR title-match (album when known, title fallback)
    30 — size-sanity (release size plausible for track duration)
"""
from __future__ import annotations

import re

from app.indexers.base import Candidate
from app.pipeline.release_parser import (
    clean_name,
    fuzzy_match,
    tokens,
)
from app.pipeline.specs import Reject, SearchCtx


# Lidarr's thresholds: 0.8 for artist, 0.7 for album, with stricter gap
# enforcement. We don't have a "runner-up" set so the gap doesn't apply;
# instead we use fuzzy_match's token-issubset signal as the primary
# gate and rely on the score for tie-breaking later.
_ARTIST_THRESHOLD = 0.7
_ALBUM_THRESHOLD = 0.6
_TITLE_THRESHOLD = 0.5


class ParseSpec:
    name = "parse"
    priority = 5

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        ctx.parse(c)
        return None


class FormatBlacklistSpec:
    name = "format-blacklist"
    priority = 10
    _MARKERS = (
        "audiobook", ".m4b", " m4b ", "[m4b]", "(m4b)",
        ".aax", "[aax]", "audible",
        ".mkv", "[mkv]",
        "1080p", "720p", "2160p", "4k uhd", "bluray", "bdrip",
        "x264", "x265", " h.264", " h.265", "hevc", "av1 ",
        "webrip", "web-dl", "hdrip", "dvdrip",
        ".iso", "[iso]",
    )

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        low = c.title.lower()
        for m in self._MARKERS:
            if m in low:
                return Reject(self.name, f"non-music format ({m.strip() or m!r})")
        return None


class ArtistMatchesSpec:
    """The parsed artist (or full release title as fallback) must
    fuzzy-match our primary artist. Token-based to stop 'ray' from
    fake-matching 'ray_hawthorne'."""

    name = "artist-match"
    priority = 20

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        track = ctx.track
        if not track.artist:
            return None
        primary = re.split(
            r"\s*[,/&]\s*|\s+feat\.?\s+|\s+ft\.?\s+", track.artist, maxsplit=1
        )[0].strip()
        if not primary:
            return None

        parsed = ctx.parse(c)
        # Try the parsed artist first (most precise), then fall back to the
        # full release title in case parsing didn't isolate it.
        score_parsed = fuzzy_match(primary, parsed.artist) if parsed.artist else 0.0
        score_title = fuzzy_match(primary, c.title)
        score = max(score_parsed, score_title)

        if score < _ARTIST_THRESHOLD:
            return Reject(
                self.name,
                f"artist {primary!r} doesn't match (score {score:.2f})",
            )
        return None


class AlbumMatchesSpec:
    """When MusicBrainz gave us an album, the candidate's parsed album
    (or release title fallback) must fuzzy-match it."""

    name = "album-match"
    priority = 25

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        track = ctx.track
        if not track.album:
            return None
        parsed = ctx.parse(c)
        score_parsed = fuzzy_match(track.album, parsed.album) if parsed.album else 0.0
        score_title = fuzzy_match(track.album, c.title)
        score = max(score_parsed, score_title)
        if score < _ALBUM_THRESHOLD:
            return Reject(
                self.name,
                f"album {track.album!r} not in release (score {score:.2f})",
            )
        return None


class TitleInReleaseSpec:
    """Fallback when no album info — require the track title in the release."""

    name = "title-match"
    priority = 25

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        track = ctx.track
        if track.album:
            return None  # AlbumMatchesSpec handles it instead
        if not track.title:
            return None
        score = fuzzy_match(track.title, c.title)
        parsed = ctx.parse(c)
        if parsed.album:
            score = max(score, fuzzy_match(track.title, parsed.album))
        if score < _TITLE_THRESHOLD:
            return Reject(
                self.name,
                f"title {track.title!r} not in release (score {score:.2f})",
            )
        return None


class SizeReasonableSpec:
    """Reject releases too big to plausibly contain only the album our
    track lives on. Lossless ceiling ~14 MB/min × 20-track album."""

    name = "size-sanity"
    priority = 30

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        track = ctx.track
        size = int((c.extra or {}).get("size") or 0)
        if not size or not track.duration_s:
            return None
        minutes = max(1.0, track.duration_s / 60.0)
        per_min = 14 * 1024 * 1024
        max_size = int(per_min * minutes * (20 if track.album else 4))
        if size > max_size:
            return Reject(
                self.name,
                f"size {size/1024/1024:.0f}MB > cap {max_size/1024/1024:.0f}MB",
            )
        return None


def default_specs():
    return [
        ParseSpec(),
        FormatBlacklistSpec(),
        ArtistMatchesSpec(),
        AlbumMatchesSpec(),
        TitleInReleaseSpec(),
        SizeReasonableSpec(),
    ]
