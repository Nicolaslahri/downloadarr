from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings as env_settings
from app.db.models import Playlist, Track, TrackStatus
from app.db.session import get_session
from app.db.settings_store import load_all, merge_with_env
from app.pipeline.run import process_track
from app.resolvers import dispatch
from app.services.events import bus
from app.services.runner import submit

router = APIRouter(prefix="/playlists", tags=["playlists"])


class ImportRequest(BaseModel):
    url: str


class PlaylistOut(BaseModel):
    id: int
    source: str
    source_url: str
    name: str
    created_at: datetime
    track_count: int
    done_count: int


class TrackOut(BaseModel):
    id: int
    playlist_id: int
    artist: str
    title: str
    album: Optional[str]
    duration_s: Optional[int]
    isrc: Optional[str]
    status: str
    file_path: Optional[str]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime


class PlaylistDetail(PlaylistOut):
    tracks: list[TrackOut]


@router.get("", response_model=list[PlaylistOut])
async def list_playlists(session: AsyncSession = Depends(get_session)) -> list[PlaylistOut]:
    result = await session.exec(select(Playlist).order_by(Playlist.created_at.desc()))
    playlists = result.all()
    out: list[PlaylistOut] = []
    for p in playlists:
        total = await session.scalar(
            select(func.count()).select_from(Track).where(Track.playlist_id == p.id)
        )
        done = await session.scalar(
            select(func.count())
            .select_from(Track)
            .where(Track.playlist_id == p.id, Track.status == TrackStatus.done)
        )
        out.append(
            PlaylistOut(
                id=p.id,
                source=p.source,
                source_url=p.source_url,
                name=p.name,
                created_at=p.created_at,
                track_count=int(total or 0),
                done_count=int(done or 0),
            )
        )
    return out


def _track_out(t: Track) -> TrackOut:
    data = t.model_dump()
    data["status"] = t.status.value if isinstance(t.status, TrackStatus) else str(t.status)
    return TrackOut(**data)


@router.get("/{playlist_id}", response_model=PlaylistDetail)
async def get_playlist(
    playlist_id: int, session: AsyncSession = Depends(get_session)
) -> PlaylistDetail:
    p = await session.get(Playlist, playlist_id)
    if not p:
        raise HTTPException(404, "Playlist not found")
    result = await session.exec(
        select(Track).where(Track.playlist_id == playlist_id).order_by(Track.id)
    )
    tracks = result.all()
    done = sum(1 for t in tracks if t.status == TrackStatus.done)
    return PlaylistDetail(
        id=p.id,
        source=p.source,
        source_url=p.source_url,
        name=p.name,
        created_at=p.created_at,
        track_count=len(tracks),
        done_count=done,
        tracks=[_track_out(t) for t in tracks],
    )


@router.post("/import")
async def import_playlist(
    req: ImportRequest, session: AsyncSession = Depends(get_session)
) -> dict:
    cfg_db = await load_all(session)
    cfg = merge_with_env(cfg_db, env_settings)

    bus.emit("log", f"resolving {req.url}")
    try:
        rp = await dispatch(req.url, cfg)
    except Exception as e:
        bus.emit("log", f"resolve failed: {e}", level="error")
        raise HTTPException(400, str(e))

    p = Playlist(source=rp.source, source_url=rp.source_url, name=rp.name)
    session.add(p)
    await session.commit()
    await session.refresh(p)
    bus.emit(
        "playlist_update",
        message=f"imported '{rp.name}' from {rp.source} ({len(rp.tracks)} tracks)",
        playlist_id=p.id,
    )

    track_ids: list[int] = []
    for rt in rp.tracks:
        t = Track(
            playlist_id=p.id,
            artist=rt.artist,
            title=rt.title,
            album=rt.album,
            duration_s=rt.duration_s,
            isrc=rt.isrc,
            source_url_hint=rt.source_url_hint,
        )
        session.add(t)
        await session.commit()
        await session.refresh(t)
        track_ids.append(t.id)

    for tid in track_ids:
        submit(f"process_track:{tid}", lambda tid=tid: process_track(tid))

    return {
        "playlist": {
            "id": p.id,
            "source": p.source,
            "source_url": p.source_url,
            "name": p.name,
            "created_at": p.created_at.isoformat(),
        },
        "queued": len(track_ids),
    }
