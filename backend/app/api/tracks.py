from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Track, TrackStatus
from app.db.session import get_session
from app.pipeline.run import process_track
from app.services.runner import submit

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.post("/{track_id}/retry")
async def retry_track(track_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    t = await session.get(Track, track_id)
    if not t:
        raise HTTPException(404, "Track not found")
    t.status = TrackStatus.pending
    t.error = None
    session.add(t)
    await session.commit()
    submit(f"process_track:{track_id}", lambda: process_track(track_id))
    return {"ok": True}
