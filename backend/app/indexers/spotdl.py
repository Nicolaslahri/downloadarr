from __future__ import annotations

from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack


class SpotdlIndexer:
    """Stub — spotdl already does Spotify→YouTube matching internally.

    A future iteration would shell out to the spotdl CLI when a track has
    an ISRC, then convert the resulting audio URL to a Candidate.
    """

    name = "spotdl"
    kind = SourceKind.spotdl

    async def search(self, track: ResolvedTrack) -> list[Candidate]:
        return []
