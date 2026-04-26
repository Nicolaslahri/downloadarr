"""Concrete specifications that run on every indexer candidate.

Priority groups (lower runs first; same-priority specs all run together,
short-circuit on any reject):

    5 — parse (no-op spec; populates cache for downstream specs)
   10 — format blacklist (audiobook/video/disc image)
   20 — artist match (must reference our artist)
   25 — album OR title match (when album known, else title)
   30 — size sanity (release size plausible for track duration)
"""
from __future__ import annotations

import re

from app.indexers.base import Candidate
from app.pipeline.release_parser import clean_name, tokens
from app.pipeline.specs import Reject, SearchCtx


class ParseSpec:
    name = "parse"
    priority = 5

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        ctx.parse(c)  # cache for downstream
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
    """The candidate's parsed artist (or full title) must contain at
    least one token of our primary artist."""
    name = "artist-match"
    priority = 20

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        track = ctx.track
        if not track.artist:
            return None
        primary = re.split(
            r"\s*[,/&]\s*|\s+feat\.?\s+|\s+ft\.?\s+", track.artist, maxsplit=1
        )[0]
        target = {t for t in tokens(primary) if len(t) > 1}
        if not target:
            return None
        parsed = ctx.parse(c)
        haystack = tokens(parsed.artist) | tokens(c.title)
        if not (target & haystack):
            return Reject(
                self.name,
                f"artist {primary!r} not found in release",
            )
        return None


class AlbumMatchesSpec:
    """When MusicBrainz gave us an album, the candidate must reference
    enough of its meaningful words. Stops 'right artist, wrong album'."""
    name = "album-match"
    priority = 25

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        track = ctx.track
        if not track.album:
            return None
        target = {t for t in tokens(track.album) if len(t) > 2}
        if not target:
            return None
        parsed = ctx.parse(c)
        haystack = tokens(parsed.album) | tokens(c.title)
        hits = len(target & haystack)
        needed = max(1, len(target) // 2)
        if hits < needed:
            return Reject(
                self.name,
                f"album {track.album!r} not in release ({hits}/{len(target)} words)",
            )
        return None


class TitleInReleaseSpec:
    """Fallback when no album info — require at least one title word."""
    name = "title-match"
    priority = 25  # same group as AlbumMatches; only fires when album unknown

    def check(self, c: Candidate, ctx: SearchCtx) -> Reject | None:
        track = ctx.track
        if track.album:
            return None  # album spec handles it
        if not track.title:
            return None
        target = {t for t in tokens(track.title) if len(t) > 2}
        if not target:
            return None
        haystack = tokens(c.title)
        if not (target & haystack):
            return Reject(
                self.name,
                f"title {track.title!r} not in release",
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
