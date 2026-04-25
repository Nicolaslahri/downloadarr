"""In-process pub/sub for SSE clients. One asyncio.Queue per subscriber."""
from __future__ import annotations

import asyncio
import json
from collections import deque
from datetime import datetime
from typing import Any


class EventBus:
    def __init__(self, history: int = 200) -> None:
        self._subs: set[asyncio.Queue[str]] = set()
        self._history: deque[str] = deque(maxlen=history)
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=512)
        async with self._lock:
            for past in self._history:
                q.put_nowait(past)
            self._subs.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subs.discard(q)

    def emit(
        self,
        kind: str,
        message: str | None = None,
        *,
        level: str = "info",
        playlist_id: int | None = None,
        track_id: int | None = None,
        status: str | None = None,
        **extra: Any,
    ) -> None:
        payload: dict[str, Any] = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "kind": kind,
            "level": level,
        }
        if message is not None:
            payload["message"] = message
        if playlist_id is not None:
            payload["playlist_id"] = playlist_id
        if track_id is not None:
            payload["track_id"] = track_id
        if status is not None:
            payload["status"] = status
        if extra:
            payload.update(extra)
        encoded = json.dumps(payload)
        self._history.append(encoded)
        for q in list(self._subs):
            try:
                q.put_nowait(encoded)
            except asyncio.QueueFull:
                pass


bus = EventBus()
