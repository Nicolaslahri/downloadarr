"""Lightweight in-process task runner.

For dev / single-node use we don't need Redis+Arq — we just spawn coroutines
and let asyncio handle them. A small concurrency cap keeps yt-dlp from
hammering the network.

Tasks can be tagged with a playlist_id so the API can cancel a whole
playlist's worth of work at once.
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Awaitable, Callable

from app.services.events import bus

_sem = asyncio.Semaphore(4)
_tasks: set[asyncio.Task] = set()
_tasks_by_playlist: dict[int, set[asyncio.Task]] = {}


def submit(
    name: str,
    coro_factory: Callable[[], Awaitable[None]],
    *,
    playlist_id: int | None = None,
) -> None:
    async def _run() -> None:
        async with _sem:
            try:
                await coro_factory()
            except asyncio.CancelledError:
                bus.emit("log", f"task {name} cancelled")
                raise
            except Exception as e:
                bus.emit("log", f"task {name} failed: {e}", level="error")

    task = asyncio.create_task(_run(), name=name)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    if playlist_id is not None:
        bucket = _tasks_by_playlist.setdefault(playlist_id, set())
        bucket.add(task)
        task.add_done_callback(bucket.discard)


def cancel_playlist(playlist_id: int) -> int:
    bucket = _tasks_by_playlist.get(playlist_id, set())
    n = 0
    for t in list(bucket):
        if not t.done():
            t.cancel()
            n += 1
    return n


def active_count(playlist_id: int | None = None) -> int:
    if playlist_id is None:
        return sum(1 for t in _tasks if not t.done())
    bucket = _tasks_by_playlist.get(playlist_id, set())
    return sum(1 for t in bucket if not t.done())


async def shutdown() -> None:
    for t in list(_tasks):
        t.cancel()
        with contextlib.suppress(Exception):
            await t
