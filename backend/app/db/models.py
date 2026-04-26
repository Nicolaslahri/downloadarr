from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TrackStatus(str, Enum):
    pending = "pending"
    resolving = "resolving"
    downloading = "downloading"
    tagging = "tagging"
    done = "done"
    failed = "failed"
    skipped = "skipped"


class Playlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source: str
    source_url: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Track(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    playlist_id: int = Field(foreign_key="playlist.id", index=True)
    artist: str
    title: str
    album: Optional[str] = None
    duration_s: Optional[int] = None
    isrc: Optional[str] = Field(default=None, index=True)
    status: TrackStatus = Field(default=TrackStatus.pending, index=True)
    file_path: Optional[str] = None
    error: Optional[str] = None
    source_url_hint: Optional[str] = None

    # v2: MusicBrainz enrichment
    mb_recording_id: Optional[str] = None
    album_mbid: Optional[str] = None
    track_no: Optional[int] = None
    year: Optional[int] = None

    # v2: live download progress
    bytes_done: int = Field(default=0)
    bytes_total: int = Field(default=0)
    speed_kbps: int = Field(default=0)

    # v2: resolved quality of the file we landed
    quality_format: Optional[str] = None
    quality_bitrate: Optional[int] = None
    quality_lossless: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# NOTE: Settings used to live in a SettingsRow table here. They've been
# moved to .data/settings.json so they survive any DB wipe — see
# app/db/settings_store.py. The table is intentionally gone.
