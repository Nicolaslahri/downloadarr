"""Lightweight in-process task runner.

For dev / single-node use we don't need Redis+Arq — we just spawn coroutines
and let asyncio handle them. A small concurrency cap keeps yt-dlp from
hammering the network.
"""
from __future__ import annotations

import asyncio
import contextlib
from typing import Awaitable, Callable

from app.services.events import bus

_sem = asyncio.Semaphore(4)
_tasks: set[asyncio.Task] = set()


def submit(name: str, coro_factory: Callable[[], Awaitable[None]]) -> None:
    async def _run() -> None:
        async with _sem:
            try:
                await coro_factory()
            except Exception as e:  # surface to clients
                bus.emit("log", f"task {name} failed: {e}", level="error")

    task = asyncio.create_task(_run(), name=name)
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def shutdown() -> None:
    for t in list(_tasks):
        t.cancel()
        with contextlib.suppress(Exception):
            await t
