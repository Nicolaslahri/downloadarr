from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import httpx

from app.downloaders.base import DownloadResult
from app.indexers.base import Candidate, SourceKind
from app.services.events import bus
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

    async def download(self, candidate: Candidate, dest_dir: str) -> DownloadResult:
        if not self.servers:
            raise RuntimeError("No NNTP servers configured. Add one in Settings → Usenet.")
        # First server only for v1; multi-server fanout is a follow-up.
        cfg = self.servers[0]

        # 1. Fetch the NZB from the indexer URL
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(candidate.url)
            r.raise_for_status()
            nzb_bytes = r.content

        nzb = parse_nzb(nzb_bytes)
        if not nzb.files:
            raise RuntimeError("NZB had no files")
        bus.emit("log", f"NZB: {len(nzb.files)} files, ~{nzb.total_bytes / 1024 / 1024:.1f} MB")

        # 2. Spin up a pool, download all files into a temp work dir
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

        # 3. Post-process: par2 repair → unrar → pick the largest audio file
        audio_path = await post_process(work_dir)
        size = audio_path.stat().st_size
        # Move the chosen file out of the work dir so the caller can move/tag it
        final = Path(dest_dir) / audio_path.name
        if final.exists():
            final.unlink()
        os.rename(audio_path, final)
        return DownloadResult(
            file_path=str(final),
            bytes=size,
            format=audio_path.suffix.lstrip(".").lower(),
        )
