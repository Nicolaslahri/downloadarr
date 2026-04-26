from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlmodel import select

from app.config import settings as env_settings
from app.db.models import Track, TrackStatus
from app.db.session import SessionLocal
from app.db.settings_store import load_all, merge_with_env
from app.downloaders import pick as pick_downloader
from app.indexers import search_all
from app.pipeline.organize import organize
from app.pipeline.score import rank
from app.pipeline.tag import tag_file
from app.resolvers.base import ResolvedTrack
from app.services.events import bus
from app.services.musicbrainz import enrich as mb_enrich
from app.services.progress import TrackProgress


async def _set_status(track_id: int, status: TrackStatus, **fields) -> None:
    async with SessionLocal() as session:
        t = await session.get(Track, track_id)
        if not t:
            return
        t.status = status
        for k, v in fields.items():
            setattr(t, k, v)
        t.updated_at = datetime.utcnow()
        session.add(t)
        await session.commit()
    bus.emit(
        "track_update",
        message=f"#{track_id} → {status.value}",
        track_id=track_id,
        status=status.value,
    )


def _is_already_in_library(library_root: str, track: ResolvedTrack) -> str | None:
    """Quick dedupe by Artist/Album/Title path before doing any work."""
    from app.pipeline.organize import _safe

    artist = _safe(track.artist)
    album = _safe(track.album or "Singles")
    title = _safe(track.title)
    folder = Path(library_root) / artist / album
    if not folder.exists():
        return None
    for p in folder.iterdir():
        if p.is_file() and p.stem.lower().startswith(title.lower()):
            return str(p)
    return None


async def process_track(track_id: int) -> None:
    cfg = merge_with_env(load_all(), env_settings)
    library_root = cfg.get("library_path") or env_settings.library_path

    async with SessionLocal() as session:
        t = await session.get(Track, track_id)
        if not t:
            return
        rt = ResolvedTrack(
            artist=t.artist,
            title=t.title,
            album=t.album,
            duration_s=t.duration_s,
            isrc=t.isrc,
            track_no=t.track_no,
            year=t.year,
            mb_recording_id=t.mb_recording_id,
            source_url_hint=t.source_url_hint,
        )
        already_enriched = bool(t.album_mbid or t.mb_recording_id)

    # Pre-search enrichment via MusicBrainz. We always want album info
    # so the indexer query is specific (album-shaped) rather than the
    # broad "artist alone" fallback that returns whatever the artist
    # ever uploaded.
    if not already_enriched:
        enriched = await mb_enrich(rt.artist, rt.title, rt.duration_s)
        if enriched:
            rt.album = enriched.album or rt.album
            rt.track_no = enriched.track_no or rt.track_no
            rt.year = enriched.year or rt.year
            rt.mb_recording_id = enriched.mb_recording_id or rt.mb_recording_id
            if enriched.duration_s and not rt.duration_s:
                rt.duration_s = enriched.duration_s
            async with SessionLocal() as session:
                tt = await session.get(Track, track_id)
                if tt:
                    if enriched.album:
                        tt.album = enriched.album
                    tt.album_mbid = enriched.mb_release_id
                    tt.mb_recording_id = enriched.mb_recording_id
                    tt.track_no = enriched.track_no
                    tt.year = enriched.year
                    if enriched.duration_s and not tt.duration_s:
                        tt.duration_s = enriched.duration_s
                    session.add(tt)
                    await session.commit()
            bus.emit(
                "log",
                f"#{track_id} MB: '{rt.artist} – {rt.title}' → album "
                f"'{enriched.album}' track {enriched.track_no} ({enriched.year})",
            )
        else:
            bus.emit(
                "log",
                f"#{track_id} MB: no confident match for '{rt.artist} – {rt.title}'",
                level="warn",
            )

    existing = _is_already_in_library(library_root, rt)
    if existing:
        await _set_status(track_id, TrackStatus.skipped, file_path=existing, error=None)
        bus.emit("log", f"#{track_id} skipped — already in library: {existing}")
        return

    await _set_status(track_id, TrackStatus.resolving)

    from app.indexers import build_indexers
    if not build_indexers(cfg):
        await _set_status(
            track_id,
            TrackStatus.failed,
            error="No Usenet or torrent indexers configured. Add one in Settings.",
        )
        return

    candidates = await search_all(rt, cfg)
    if not candidates:
        await _set_status(
            track_id,
            TrackStatus.failed,
            error="No matches from any configured indexer for this track.",
        )
        return

    profile = cfg.get("quality_profile") or "best"
    preferred = [s for s in (cfg.get("preferred_sources") or "").split(",") if s]
    ranked = rank(candidates, rt, profile, preferred)

    last_err: str | None = None
    for cand in ranked[:5]:
        downloader = pick_downloader(cand, cfg)
        if not downloader:
            continue
        await _set_status(track_id, TrackStatus.downloading)
        prog = TrackProgress(track_id=track_id)
        try:
            result = await downloader.download(
                cand, env_settings.downloads_path, rt, progress=prog
            )
            await prog.finalize()
        except NotImplementedError as e:
            last_err = str(e)
            continue
        except Exception as e:
            last_err = f"{downloader.name}: {e}"
            bus.emit("log", f"#{track_id} {last_err}", level="warn")
            continue

        await _set_status(track_id, TrackStatus.tagging)
        await tag_file(result.file_path, rt)
        try:
            final = organize(result.file_path, rt, library_root)
        except Exception as e:
            await _set_status(track_id, TrackStatus.failed, error=f"organize: {e}")
            return
        await _set_status(track_id, TrackStatus.done, file_path=final, error=None)
        bus.emit("log", f"#{track_id} done → {final}")
        return

    await _set_status(
        track_id,
        TrackStatus.failed,
        error=last_err or "no compatible downloader for any candidate",
    )
