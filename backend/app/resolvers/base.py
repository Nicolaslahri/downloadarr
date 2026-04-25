from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class ResolvedTrack:
    artist: str
    title: str
    album: Optional[str] = None
    duration_s: Optional[int] = None
    isrc: Optional[str] = None
    source_url_hint: Optional[str] = None


@dataclass
class ResolvedPlaylist:
    source: str
    source_url: str
    name: str
    tracks: list[ResolvedTrack]


class Resolver(Protocol):
    name: str

    def detect(self, url: str) -> bool: ...

    async def resolve(self, url: str) -> ResolvedPlaylist: ...
