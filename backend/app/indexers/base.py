from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol

from app.resolvers.base import ResolvedTrack


class SourceKind(str, Enum):
    ytdlp = "ytdlp"
    torrent = "torrent"
    nzb = "nzb"
    spotdl = "spotdl"
    zotify = "zotify"


@dataclass
class Candidate:
    source: SourceKind
    url: str
    title: str
    bitrate_kbps: Optional[int] = None
    format: Optional[str] = None
    duration_s: Optional[int] = None
    score: float = 0.0
    extra: dict = None  # type: ignore[assignment]


class Indexer(Protocol):
    name: str
    kind: SourceKind

    async def search(self, track: ResolvedTrack) -> list[Candidate]: ...
