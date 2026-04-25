from __future__ import annotations

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack

QUALITY_BIAS: dict[str, dict[SourceKind, float]] = {
    "best": {
        SourceKind.torrent: 0.9,
        SourceKind.nzb: 0.85,
    },
    "lossless_first": {
        SourceKind.torrent: 1.0,
        SourceKind.nzb: 0.95,
    },
    "320_only": {
        SourceKind.torrent: 0.8,
        SourceKind.nzb: 0.75,
    },
}


def rank(
    candidates: list[Candidate],
    track: ResolvedTrack,
    profile: str,
    preferred: list[str],
) -> list[Candidate]:
    bias = QUALITY_BIAS.get(profile, QUALITY_BIAS["best"])
    pref_set = {p.lower() for p in preferred}

    def adjusted(c: Candidate) -> float:
        base = c.score
        base += bias.get(c.source, 0.5)
        if c.source.value in pref_set:
            base += 0.2
        if c.bitrate_kbps:
            base += min(c.bitrate_kbps / 1000, 0.3)
        if track.duration_s and c.duration_s:
            diff = abs(c.duration_s - track.duration_s)
            base += max(0.0, 0.2 - diff / 60)
        return base

    return sorted(candidates, key=adjusted, reverse=True)
