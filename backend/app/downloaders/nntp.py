from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import httpx

from app.downloaders.base import DownloadResult
from app.indexers.base import Candidate, SourceKind
from app.resolvers.base import ResolvedTrack
from app.services.events import bus
from app.services.track_picker import pick_track_file
from app.services.usenet.nntp import NntpConfig, NntpPool
from app.services.usenet.nntp import download_files as nntp_download_files
from app.services.usenet.nzb import parse as parse_nzb
from app.services.usenet.postproc import post_process


def _server_configs(raw: str) -> list[NntpConfig]:
    try:
        data = json.loads(raw or "[]")
    except Exception:
        return []
    out: list[NntpConfig] = []
    for c in data if isinstance(data, list) else []:
        host = (c.get("host") or "").strip()
        if not host:
            continue
        out.append(
            NntpConfig(
                host=host,
                port=int(c.get("port") or 563),
                ssl=bool(c.get("ssl", True)),
                username=c.get("username") or "",
                password=c.get("password") or "",
                connections=int(c.get("connections") or 10),
            )
        )
    return out


class NntpDownloader:
    name = "nntp"

    def __init__(self, server_cfgs_json: str = "[]"):
        self.servers = _server_configs(server_cfgs_json)

    def supports(self, candidate: Candidate) -> bool:
        return candidate.source == SourceKind.nzb and bool(self.servers)

    async def download(
        self, candidate: Candidate, dest_dir: str, track: ResolvedTrack
    ) -> DownloadResult:
        if not self.servers:
            raise RuntimeError("No NNTP servers configured. Add one in Settings → Usenet.")
        cfg = self.servers[0]

        # 1. Fetch the NZB itself
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(candidate.url)
            r.raise_for_status()
            nzb_bytes = r.content

        nzb = parse_nzb(nzb_bytes)
        if not nzb.files:
            raise RuntimeError("NZB had no files")
        bus.emit("log", f"NZB: {len(nzb.files)} files, ~{nzb.total_bytes / 1024 / 1024:.1f} MB")

        # 2. Download everything into a temp work dir
        work_dir = Path(tempfile.mkdtemp(prefix="musicdl_nzb_", dir=dest_dir))
        pool = NntpPool(cfg)

        last_pct = -1

        def on_progress(done: int, total: int) -> None:
            nonlocal last_pct
            pct = int(done * 100 / max(total, 1))
            if pct != last_pct and pct % 10 == 0:
                bus.emit("log", f"NNTP {cfg.host}: {done}/{total} segments ({pct}%)")
                last_pct = pct

        try:
            await nntp_download_files(pool, nzb.files, work_dir, progress=on_progress)
        finally:
            await pool.shutdown()

        # 3. par2 → unrar → list of audio files
        audio_files = await post_process(work_dir)

        # 4. Pick the right one for this track
        pick = pick_track_file(audio_files, track)
        if pick is None:
            shown = ", ".join(p.name for p in audio_files[:8])
            extra = f" (+{len(audio_files) - 8} more)" if len(audio_files) > 8 else ""
            raise RuntimeError(
                f"track-picker: couldn't confidently identify '{track.title}' among "
                f"{len(audio_files)} audio files: [{shown}{extra}]"
            )
        bus.emit(
            "log",
            f"track-picker: chose {pick.path.name} (score={pick.score:.2f} — {', '.join(pick.reasons)})",
        )

        # 5. Move chosen file out of the work dir; clean the rest up
        final = Path(dest_dir) / pick.path.name
        if final.exists():
            final.unlink()
        os.rename(pick.path, final)
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass

        size = final.stat().st_size
        return DownloadResult(
            file_path=str(final),
            bytes=size,
            format=final.suffix.lstrip(".").lower(),
        )
