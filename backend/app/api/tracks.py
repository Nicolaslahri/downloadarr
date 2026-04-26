from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings as env_settings
from app.db.models import Track, TrackStatus
from app.db.session import get_session
from app.db.settings_store import load_all, merge_with_env
from app.indexers import search_all
from app.indexers.base import Candidate
from app.pipeline.run import process_track, process_with_candidate
from app.resolvers.base import ResolvedTrack
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


class ManualSearchRequest(BaseModel):
    query: str


@router.post("/{track_id}/manual-search", response_model=list[CandidateOut])
async def manual_search(
    track_id: int,
    body: ManualSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> list[CandidateOut]:
    t = await session.get(Track, track_id)
    if not t:
        raise HTTPException(404, "Track not found")
    query = (body.query or "").strip()
    if not query:
        raise HTTPException(400, "Query is required")

    rt = ResolvedTrack(
        artist=t.artist or "",
        title=query,
        album=None,  # manual = trust the user's query exactly, no album cross-check
        duration_s=t.duration_s,
        track_no=t.track_no,
        mb_recording_id=t.mb_recording_id,
    )

    cfg = merge_with_env(load_all(), env_settings)
    raw: list[Candidate] = await search_all(rt, cfg)
    raw.sort(key=lambda c: c.score, reverse=True)

    payload = [
        {
            "source": c.source.value,
            "url": c.url,
            "title": c.title,
            "score": round(c.score, 3),
            "size": int((c.extra or {}).get("size") or 0),
            "indexer": (c.extra or {}).get("indexer") or "",
            "seeders": int((c.extra or {}).get("seeders") or 0),
            "format": c.format or "",
            "bitrate_kbps": c.bitrate_kbps or 0,
        }
        for c in raw[:25]
    ]

    t.candidates_json = json.dumps(payload)
    session.add(t)
    await session.commit()

    return [CandidateOut(**p) for p in payload]


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
