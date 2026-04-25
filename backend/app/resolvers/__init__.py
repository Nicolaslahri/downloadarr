from __future__ import annotations

from app.resolvers.ai_video import AIVideoResolver
from app.resolvers.apple_music import AppleMusicResolver
from app.resolvers.base import ResolvedPlaylist, ResolvedTrack, Resolver
from app.resolvers.soundcloud import SoundCloudResolver
from app.resolvers.spotify import SpotifyResolver
from app.resolvers.youtube import YouTubeResolver

__all__ = ["ResolvedPlaylist", "ResolvedTrack", "Resolver", "build_resolvers", "dispatch"]


def build_resolvers(cfg: dict[str, str]) -> list[Resolver]:
    return [
        YouTubeResolver(),  # playlists/lists
        AIVideoResolver(anthropic_api_key=cfg.get("anthropic_api_key", "")),  # single video
        SpotifyResolver(
            client_id=cfg.get("spotify_client_id", ""),
            client_secret=cfg.get("spotify_client_secret", ""),
        ),
        AppleMusicResolver(),
        SoundCloudResolver(),
    ]


async def dispatch(url: str, cfg: dict[str, str]) -> ResolvedPlaylist:
    for r in build_resolvers(cfg):
        if r.detect(url):
            return await r.resolve(url)
    raise ValueError(f"No resolver matched: {url}")
