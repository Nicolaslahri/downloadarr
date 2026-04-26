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
from app.services.runner import active_count, cancel_playlist, submit

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
    pending_count: int
    active_count: int


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
    track_no: Optional[int] = None
    year: Optional[int] = None
    bytes_done: int = 0
    bytes_total: int = 0
    speed_kbps: int = 0
    quality_format: Optional[str] = None
    quality_bitrate: Optional[int] = None
    quality_lossless: bool = False
    created_at: datetime
    updated_at: datetime


class PlaylistDetail(PlaylistOut):
    tracks: list[TrackOut]


def _track_out(t: Track) -> TrackOut:
    data = t.model_dump()
    data["status"] = t.status.value if isinstance(t.status, TrackStatus) else str(t.status)
    return TrackOut(**data)


async def _stats(session: AsyncSession, playlist_id: int) -> tuple[int, int, int]:
    total = await session.scalar(
        select(func.count()).select_from(Track).where(Track.playlist_id == playlist_id)
    )
    done = await session.scalar(
        select(func.count())
        .select_from(Track)
        .where(Track.playlist_id == playlist_id, Track.status == TrackStatus.done)
    )
    pending = await session.scalar(
        select(func.count())
        .select_from(Track)
        .where(Track.playlist_id == playlist_id, Track.status == TrackStatus.pending)
    )
    return int(total or 0), int(done or 0), int(pending or 0)


@router.get("", response_model=list[PlaylistOut])
async def list_playlists(session: AsyncSession = Depends(get_session)) -> list[PlaylistOut]:
    result = await session.exec(select(Playlist).order_by(Playlist.created_at.desc()))
    playlists = result.all()
    out: list[PlaylistOut] = []
    for p in playlists:
        total, done, pending = await _stats(session, p.id)
        out.append(
            PlaylistOut(
                id=p.id,
                source=p.source,
                source_url=p.source_url,
                name=p.name,
                created_at=p.created_at,
                track_count=total,
                done_count=done,
                pending_count=pending,
                active_count=active_count(p.id),
            )
        )
    return out


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
    total, done, pending = await _stats(session, playlist_id)
    return PlaylistDetail(
        id=p.id,
        source=p.source,
        source_url=p.source_url,
        name=p.name,
        created_at=p.created_at,
        track_count=total,
        done_count=done,
        pending_count=pending,
        active_count=active_count(playlist_id),
        tracks=[_track_out(t) for t in tracks],
    )


@router.post("/import")
async def import_playlist(
    req: ImportRequest, session: AsyncSession = Depends(get_session)
) -> dict:
    """Resolve the URL and persist tracks as `pending` only.

    Downloads do NOT start automatically — the user previews the tracklist
    on the playlist detail page and explicitly clicks Start.
    """
    cfg = merge_with_env(load_all(), env_settings)

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
        message=f"resolved '{rp.name}' from {rp.source} ({len(rp.tracks)} tracks) — preview only",
        playlist_id=p.id,
    )

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

    return {
        "playlist": {
            "id": p.id,
            "source": p.source,
            "source_url": p.source_url,
            "name": p.name,
            "created_at": p.created_at.isoformat(),
        },
        "track_count": len(rp.tracks),
    }


class StartRequest(BaseModel):
    limit: int | None = None


@router.post("/{playlist_id}/start")
async def start_playlist(
    playlist_id: int,
    body: StartRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    p = await session.get(Playlist, playlist_id)
    if not p:
        raise HTTPException(404, "Playlist not found")
    q = select(Track.id).where(
        Track.playlist_id == playlist_id, Track.status == TrackStatus.pending
    )
    if body and body.limit:
        q = q.limit(body.limit)
    result = await session.exec(q)
    track_ids = list(result.all())
    if not track_ids:
        return {"queued": 0, "message": "Nothing pending to start."}
    for tid in track_ids:
        submit(
            f"process_track:{tid}",
            lambda tid=tid: process_track(tid),
            playlist_id=playlist_id,
        )
    bus.emit(
        "playlist_update",
        message=f"started downloads for '{p.name}' — {len(track_ids)} tracks queued",
        playlist_id=playlist_id,
    )
    return {"queued": len(track_ids)}


@router.post("/{playlist_id}/stop")
async def stop_playlist(
    playlist_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    p = await session.get(Playlist, playlist_id)
    if not p:
        raise HTTPException(404, "Playlist not found")
    cancelled = cancel_playlist(playlist_id)
    bus.emit(
        "playlist_update",
        message=f"stopped '{p.name}' — {cancelled} task(s) cancelled",
        playlist_id=playlist_id,
        level="warn",
    )
    return {"cancelled": cancelled}


@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    p = await session.get(Playlist, playlist_id)
    if not p:
        raise HTTPException(404, "Playlist not found")
    cancel_playlist(playlist_id)
    result = await session.exec(select(Track).where(Track.playlist_id == playlist_id))
    for t in result.all():
        await session.delete(t)
    await session.delete(p)
    await session.commit()
    return {"ok": True}
