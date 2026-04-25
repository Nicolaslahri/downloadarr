"""libtorrent wrapper: add magnet/.torrent → wait for completion → return audio file."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wav"}


@dataclass
class TorrentResult:
    file_path: Path
    bytes: int


def _import_lt():
    try:
        import libtorrent as lt  # type: ignore

        return lt
    except Exception as e:
        raise RuntimeError(
            "libtorrent is not installed in this Python environment. "
            "On Windows, install via conda: `conda install -c conda-forge libtorrent`, "
            "or grab a prebuilt wheel for your Python version. "
            "See README → 'Torrent engine install'. "
            f"({e!r})"
        )


async def download(
    torrent_url_or_magnet: str,
    save_dir: str,
    progress: Callable[[int, int], None] | None = None,
    timeout_s: int = 60 * 60,
) -> TorrentResult:
    lt = _import_lt()

    Path(save_dir).mkdir(parents=True, exist_ok=True)
    settings_pack = {
        "listen_interfaces": "0.0.0.0:6881",
        "user_agent": "MusicDownloadarr/0.1",
        "alert_mask": lt.alert.category_t.all_categories,
    }
    session = lt.session(settings_pack)
    session.add_dht_router("router.bittorrent.com", 6881)
    session.add_dht_router("dht.transmissionbt.com", 6881)
    session.start_dht()

    if torrent_url_or_magnet.startswith("magnet:"):
        params = lt.parse_magnet_uri(torrent_url_or_magnet)
        params.save_path = save_dir
        handle = session.add_torrent(params)
    else:
        # Fetch a .torrent over HTTP first, then add by content
        import httpx

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            r = await client.get(torrent_url_or_magnet)
            r.raise_for_status()
            torrent_bytes = r.content
        info = lt.torrent_info(lt.bdecode(torrent_bytes))
        handle = session.add_torrent({"ti": info, "save_path": save_dir})

    # Wait for metadata if magnet
    deadline = asyncio.get_event_loop().time() + timeout_s
    while not handle.status().has_metadata:
        if asyncio.get_event_loop().time() > deadline:
            raise RuntimeError("torrent metadata timeout")
        await asyncio.sleep(1)

    # Audio-only file priorities
    info = handle.get_torrent_info()
    files = info.files()
    selected_idx: int | None = None
    largest = -1
    for i in range(files.num_files()):
        path = files.file_path(i)
        size = files.file_size(i)
        if Path(path).suffix.lower() in AUDIO_EXTS and size > largest:
            largest = size
            selected_idx = i

    if selected_idx is not None:
        priorities = [0] * files.num_files()
        priorities[selected_idx] = 4
        handle.prioritize_files(priorities)

    # Loop until done (or until our chosen file is fully downloaded)
    while True:
        s = handle.status()
        if progress and s.total_wanted > 0:
            progress(int(s.total_wanted_done), int(s.total_wanted))
        if s.is_seeding or s.progress >= 1.0:
            break
        if asyncio.get_event_loop().time() > deadline:
            raise RuntimeError("torrent download timeout")
        await asyncio.sleep(2)

    save_path = Path(save_dir)
    audio_files = [
        save_path / files.file_path(i)
        for i in range(files.num_files())
        if Path(files.file_path(i)).suffix.lower() in AUDIO_EXTS
    ]
    audio_files = [p for p in audio_files if p.exists()]
    if not audio_files:
        raise RuntimeError("torrent finished but no audio file inside")
    audio_files.sort(key=lambda p: p.stat().st_size, reverse=True)
    chosen = audio_files[0]
    return TorrentResult(file_path=chosen, bytes=chosen.stat().st_size)
