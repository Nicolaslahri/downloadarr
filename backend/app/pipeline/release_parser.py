"""Parse a raw release title (e.g. 'Bad.Bunny-El.Ultimo.Tour.Del.Mundo-WEB-FLAC-2020-PERFECT')
into structured fields. Ported from Lidarr's Parser/* in spirit, simplified.

Used by specs that need to know 'is this release name actually for our album'.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class ParsedRelease:
    artist: str | None = None
    album: str | None = None
    year: int | None = None
    source: str | None = None
    codec: str | None = None
    quality_hint: str | None = None
    group: str | None = None
    is_discography: bool = False
    is_compilation: bool = False
    is_live: bool = False
    is_remix: bool = False


# Strip scene tracker tags like [rartv], (rartv) — these confuse the patterns.
_TRACKER_TAG = re.compile(r"\[(?:[a-z0-9.\-]+)\]|\((?:[a-z0-9.\-]+)\)$", re.IGNORECASE)

_DISCO = re.compile(r"\bdiscograph(?:y|ie)\b", re.IGNORECASE)
_VA = re.compile(r"\b(?:various\.?artists|v\.?a\.?|VA)\b", re.IGNORECASE)
_LIVE = re.compile(r"\b(?:live\.from|live\.in|live\.at|\(live\)|\.live\.)\b", re.IGNORECASE)
_REMIX = re.compile(r"\b(?:remix|remixes|remixed|rmx)\b", re.IGNORECASE)


# Ordered patterns — first match wins. Add more as we hit edge cases.
_PATTERNS = [
    # 1) Dot/underscore scene: Artist.Name-Album.Name-(Year)?-SOURCE-CODEC-GROUP
    re.compile(
        r"""^
        (?P<artist>[\w.()&]+?)
        [-._]
        (?P<album>[\w.()&'!,]+?)
        [-._]
        (?:\(?(?P<year>(?:19|20)\d{2})\)?[-._])?
        (?:(?P<source>WEB|CD|VINYL|SACD|DSD|DVD|HDCD|TAPE)[-._])?
        (?P<codec>FLAC|MP3|AAC|OGG|OPUS|ALAC|WAV)
        (?:[-._](?P<quality>320|256|224|192|160|128|V0|V1|V2|24-?BIT|24B))?
        [-._]
        (?P<group>[\w.]+?)
        $""",
        re.IGNORECASE | re.VERBOSE,
    ),
    # 2) Spaced human form: Artist - Album (Year) [Source] [Codec] [Group]
    re.compile(
        r"""^
        (?P<artist>[\w\s&'.,!]+?)
        \s*-\s*
        (?P<album>[\w\s&'.,!()]+?)
        \s*\(?(?P<year>(?:19|20)\d{2})\)?
        (?:[\s\-\[\]_.]*?(?P<source>WEB|CD|VINYL|SACD|DSD|DVD|HDCD|TAPE))?
        (?:[\s\-\[\]_.]*?(?P<codec>FLAC|MP3|AAC|OGG|OPUS|ALAC|WAV))
        (?:[\s\-\[\]_.]*?(?P<quality>320|256|224|192|V0|V2|24-?BIT))?
        (?:[\s\-_]+(?P<group>[\w.]+))?
        \s*$""",
        re.IGNORECASE | re.VERBOSE,
    ),
    # 3) Loose "Artist - Album (Year)" with nothing else
    re.compile(
        r"""^
        (?P<artist>[\w\s&'.,!]+?)
        \s*[-_]\s*
        (?P<album>[\w\s&'.,!()]+?)
        \s*\(?(?P<year>(?:19|20)\d{2})\)?
        \s*$""",
        re.IGNORECASE | re.VERBOSE,
    ),
    # 4) Bare "Artist - Album" no year, no codec
    re.compile(
        r"""^
        (?P<artist>[\w\s&'.,!]+?)
        \s*-\s*
        (?P<album>[\w\s&'.,!()]+?)
        \s*$""",
        re.IGNORECASE | re.VERBOSE,
    ),
]


_ARTICLES = {"the", "a", "an"}
_NORMALIZE_PUNCT = re.compile(r"[^\w\s&]")


def _humanize(s: str | None) -> str | None:
    if s is None:
        return None
    out = re.sub(r"[._]+", " ", s).strip()
    return out or None


def parse_release_title(title: str) -> ParsedRelease:
    raw = (title or "").strip()
    cleaned = _TRACKER_TAG.sub("", raw).strip()

    flags = ParsedRelease(
        is_discography=bool(_DISCO.search(cleaned)),
        is_compilation=bool(_VA.search(cleaned)),
        is_live=bool(_LIVE.search(cleaned)),
        is_remix=bool(_REMIX.search(cleaned)),
    )

    for pat in _PATTERNS:
        m = pat.match(cleaned)
        if not m:
            continue
        d = m.groupdict()
        return ParsedRelease(
            artist=_humanize(d.get("artist")),
            album=_humanize(d.get("album")),
            year=int(d["year"]) if d.get("year") else None,
            source=(d.get("source") or "").upper() or None,
            codec=(d.get("codec") or "").upper() or None,
            quality_hint=(d.get("quality") or "").upper() or None,
            group=d.get("group"),
            is_discography=flags.is_discography,
            is_compilation=flags.is_compilation,
            is_live=flags.is_live,
            is_remix=flags.is_remix,
        )
    return flags


def clean_name(s: str | None) -> str:
    """Lowercase, strip diacritics, strip leading article, drop punctuation,
    collapse whitespace. Used for token-based comparison.

    'The Beatles' → 'beatles'   (article stripped)
    'Beyoncé'     → 'beyonce'   (NFD-normalized, marks dropped)
    'AC/DC'      → 'ac dc'      (slash → space)
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = _NORMALIZE_PUNCT.sub(" ", s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    # Strip a single leading article so "The Beatles" matches "Beatles"
    parts = s.split(" ", 1)
    if len(parts) == 2 and parts[0] in _ARTICLES:
        s = parts[1]
    return s


def tokens(s: str | None) -> set[str]:
    """clean_name + drop articles + drop 1-char tokens."""
    if not s:
        return set()
    return {
        t
        for t in clean_name(s).split()
        if t and t not in _ARTICLES and len(t) > 1
    }


def fuzzy_match(target: str | None, haystack: str | None) -> float:
    """Symmetric 0–1 score for 'does the haystack contain enough of target'.

    Token-based first (avoids 'ray fuzzy-matches raye' false positives);
    falls back to rapidfuzz token_set_ratio for diacritic / punctuation
    edge cases the tokenizer might miss.
    """
    if not target or not haystack:
        return 0.0
    target_tokens = tokens(target)
    haystack_tokens = tokens(haystack)
    if not target_tokens:
        return 0.0

    # Strong signal: every meaningful target token is present.
    if target_tokens.issubset(haystack_tokens):
        return 1.0

    overlap = len(target_tokens & haystack_tokens)
    if overlap:
        return 0.5 + 0.5 * (overlap / len(target_tokens))

    # No token overlap. Try rapidfuzz on the cleaned strings — catches
    # things tokens miss (e.g. 'AC/DC' vs 'ACDC' if normalisation differs).
    try:
        from rapidfuzz import fuzz  # type: ignore

        score = fuzz.token_set_ratio(clean_name(target), clean_name(haystack)) / 100.0
        # Penalise heavily — if tokens didn't overlap, we're being generous.
        return max(0.0, score - 0.4)
    except Exception:
        return 0.0
