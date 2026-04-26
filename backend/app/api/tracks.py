from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import Track, TrackStatus
from app.db.session import get_session
from app.pipeline.run import process_track, process_with_candidate
from app.services.runner import submit

router = APIRouter(prefix="/tracks", tags=["tracks"])


class CandidateOut(BaseModel):
    source: str
    url: str
    title: str
    score: float
    size: int = 0
    indexer: str = ""
    seeders: int = 0
    format: str = ""
    bitrate_kbps: int = 0


class UseCandidateRequest(BaseModel):
    source: str
    url: str
    title: str = ""
    indexer: str = ""
    size: int = 0
    score: float = 0.0


@router.post("/{track_id}/retry")
async def retry_track(track_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    t = await session.get(Track, track_id)
    if not t:
        raise HTTPException(404, "Track not found")
    t.status = TrackStatus.pending
    t.error = None
    t.bytes_done = 0
    t.bytes_total = 0
    t.speed_kbps = 0
    session.add(t)
    await session.commit()
    submit(
        f"process_track:{track_id}",
        lambda: process_track(track_id),
        playlist_id=t.playlist_id,
    )
    return {"ok": True}


@router.get("/{track_id}/candidates", response_model=list[CandidateOut])
async def get_candidates(
    track_id: int, session: AsyncSession = Depends(get_session)
) -> list[CandidateOut]:
    t = await session.get(Track, track_id)
    if not t:
        raise HTTPException(404, "Track not found")
    raw = t.candidates_json or "[]"
    try:
        data = json.loads(raw)
    except Exception:
        data = []
    out: list[CandidateOut] = []
    for c in data if isinstance(data, list) else []:
        try:
            out.append(CandidateOut(**c))
        except Exception:
            continue
    return out


@router.delete("/{track_id}")
async def delete_track(track_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    t = await session.get(Track, track_id)
    if not t:
        raise HTTPException(404, "Track not found")
    await session.delete(t)
    await session.commit()
    return {"ok": True}


@router.post("/{track_id}/use-candidate")
async def use_candidate(
    track_id: int,
    body: UseCandidateRequest,
    session: AsyncSession = Depends(get_session),
) -> dict:
    t = await session.get(Track, track_id)
    if not t:
        raise HTTPException(404, "Track not found")
    t.status = TrackStatus.pending
    t.error = None
    t.bytes_done = 0
    t.bytes_total = 0
    t.speed_kbps = 0
    session.add(t)
    await session.commit()
    payload = body.model_dump()
    submit(
        f"manual_candidate:{track_id}",
        lambda: process_with_candidate(track_id, payload),
        playlist_id=t.playlist_id,
    )
    return {"ok": True}
