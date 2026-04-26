from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import Playlist, Track, TrackStatus
from app.db.session import get_session

router = APIRouter(tags=["queue"])


class TrackInQueue(BaseModel):
    id: int
    playlist_id: int
    playlist_name: str
    playlist_source: str
    artist: str
    title: str
    album: Optional[str]
    duration_s: Optional[int]
    status: str
    error: Optional[str]
    track_no: Optional[int] = None
    year: Optional[int] = None
    bytes_done: int = 0
    bytes_total: int = 0
    speed_kbps: int = 0
    quality_format: Optional[str] = None
    quality_bitrate: Optional[int] = None
    quality_lossless: bool = False
    file_path: Optional[str] = None
    updated_at: datetime


_ACTIVE = (
    TrackStatus.pending,
    TrackStatus.resolving,
    TrackStatus.downloading,
    TrackStatus.tagging,
)
_FINISHED = (TrackStatus.done, TrackStatus.failed, TrackStatus.skipped)


def _to_q(t: Track, p: Playlist) -> TrackInQueue:
    return TrackInQueue(
        id=t.id,
        playlist_id=t.playlist_id,
        playlist_name=p.name,
        playlist_source=p.source,
        artist=t.artist,
        title=t.title,
        album=t.album,
        duration_s=t.duration_s,
        status=t.status.value if isinstance(t.status, TrackStatus) else str(t.status),
        error=t.error,
        track_no=t.track_no,
        year=t.year,
        bytes_done=t.bytes_done,
        bytes_total=t.bytes_total,
        speed_kbps=t.speed_kbps,
        quality_format=t.quality_format,
        quality_bitrate=t.quality_bitrate,
        quality_lossless=t.quality_lossless,
        file_path=t.file_path,
        updated_at=t.updated_at,
    )


@router.get("/queue", response_model=list[TrackInQueue])
async def queue(session: AsyncSession = Depends(get_session)) -> list[TrackInQueue]:
    result = await session.exec(
        select(Track, Playlist)
        .join(Playlist, Track.playlist_id == Playlist.id)
        .where(Track.status.in_(_ACTIVE))
        .order_by(Track.updated_at.desc())
    )
    return [_to_q(t, p) for t, p in result.all()]


@router.get("/history", response_model=list[TrackInQueue])
async def history(
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
) -> list[TrackInQueue]:
    result = await session.exec(
        select(Track, Playlist)
        .join(Playlist, Track.playlist_id == Playlist.id)
        .where(Track.status.in_(_FINISHED))
        .order_by(Track.updated_at.desc())
        .limit(limit)
    )
    return [_to_q(t, p) for t, p in result.all()]
