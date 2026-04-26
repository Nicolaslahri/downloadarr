"""Decision-engine pattern ported from Lidarr.

Each `Specification` decides whether a single candidate should be
rejected, returning a `Reject` with a reason. Specs are grouped by
`priority` (lower runs first); within a group every spec runs, but if
*any* spec in a group rejects, evaluation short-circuits and later
priority groups are skipped. This gives clean, explainable filtering.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import groupby
from typing import Protocol

from app.indexers.base import Candidate
from app.pipeline.release_parser import ParsedRelease, parse_release_title
from app.resolvers.base import ResolvedTrack


@dataclass(frozen=True)
class Reject:
    spec: str
    reason: str


@dataclass
class SearchCtx:
    track: ResolvedTrack
    parsed: dict[str, ParsedRelease] = field(default_factory=dict)

    def parse(self, c: Candidate) -> ParsedRelease:
        cached = self.parsed.get(c.url)
        if cached is None:
            cached = parse_release_title(c.title)
            self.parsed[c.url] = cached
        return cached


class Spec(Protocol):
    name: str
    priority: int

    def check(self, candidate: Candidate, ctx: SearchCtx) -> Reject | None: ...


@dataclass
class Decision:
    candidate: Candidate
    accepted: bool
    rejects: list[Reject] = field(default_factory=list)


def evaluate(
    candidates: list[Candidate],
    track: ResolvedTrack,
    specs: list[Spec],
) -> list[Decision]:
    """Run each candidate through the spec ladder. Returns a Decision per
    candidate (in input order) so callers can see both accepted and
    rejected sets."""
    ctx = SearchCtx(track=track)
    sorted_specs = sorted(specs, key=lambda s: s.priority)

    out: list[Decision] = []
    for c in candidates:
        rejects: list[Reject] = []
        for _prio, group_iter in groupby(sorted_specs, key=lambda s: s.priority):
            group_specs = list(group_iter)
            group_rejects: list[Reject] = []
            for spec in group_specs:
                r = spec.check(c, ctx)
                if r is not None:
                    group_rejects.append(r)
            if group_rejects:
                rejects = group_rejects
                break  # short-circuit later priority groups
        out.append(Decision(candidate=c, accepted=not rejects, rejects=rejects))
    return out
