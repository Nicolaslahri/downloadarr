"""Per-track download progress: bytes done/total + rolling speed.

Updates the Track row in the DB at most ~once every 2s, and emits an
SSE event at most ~once every 1s. Both rates are tunable via the class
constants below; the goal is to keep the UI lively without spamming
the DB or browser with thousands of tiny updates.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.db.models import Track
from app.db.session import SessionLocal
from app.services.events import bus

DB_FLUSH_INTERVAL_S = 2.0
SSE_EMIT_INTERVAL_S = 1.0


@dataclass
class TrackProgress:
    track_id: int
    bytes_done: int = 0
    bytes_total: int = 0
    speed_bps: float = 0.0

    _last_db: float = field(default_factory=time.time)
    _last_emit: float = field(default_factory=time.time)
    _last_speed_at: float = field(default_factory=time.time)
    _last_bytes_for_speed: int = 0

    async def update(self, done: int, total: int) -> None:
        now = time.time()
        self.bytes_done = max(self.bytes_done, done)
        if total:
            self.bytes_total = total

        elapsed = now - self._last_speed_at
        if elapsed >= 0.75:
            delta = done - self._last_bytes_for_speed
            self.speed_bps = max(0.0, delta / elapsed) if delta > 0 else self.speed_bps * 0.5
            self._last_bytes_for_speed = done
            self._last_speed_at = now

        if now - self._last_db >= DB_FLUSH_INTERVAL_S:
            self._last_db = now
            try:
                async with SessionLocal() as session:
                    t = await session.get(Track, self.track_id)
                    if t:
                        t.bytes_done = int(self.bytes_done)
                        t.bytes_total = int(self.bytes_total)
                        t.speed_kbps = int(self.speed_bps / 1024)
                        session.add(t)
                        await session.commit()
            except Exception:
                pass  # progress writes are best-effort

        if now - self._last_emit >= SSE_EMIT_INTERVAL_S:
            self._last_emit = now
            bus.emit(
                "track_progress",
                track_id=self.track_id,
                bytes_done=int(self.bytes_done),
                bytes_total=int(self.bytes_total),
                speed_kbps=int(self.speed_bps / 1024),
            )

    async def finalize(self) -> None:
        """Flush a final state when the download completes (so the UI
        doesn't sit at 99% from a missed rate-limited tick)."""
        try:
            async with SessionLocal() as session:
                t = await session.get(Track, self.track_id)
                if t:
                    t.bytes_done = int(self.bytes_total or self.bytes_done)
                    t.bytes_total = int(self.bytes_total or self.bytes_done)
                    t.speed_kbps = 0
                    session.add(t)
                    await session.commit()
        except Exception:
            pass
        bus.emit(
            "track_progress",
            track_id=self.track_id,
            bytes_done=int(self.bytes_total or self.bytes_done),
            bytes_total=int(self.bytes_total or self.bytes_done),
            speed_kbps=0,
        )
