from __future__ import annotations

import asyncio
from typing import AsyncIterator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.services.events import bus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/stream")
async def stream() -> EventSourceResponse:
    queue = await bus.subscribe()

    async def gen() -> AsyncIterator[dict]:
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                    yield {"data": item}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            await bus.unsubscribe(queue)

    return EventSourceResponse(gen())
