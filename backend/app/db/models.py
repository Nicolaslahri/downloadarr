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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SettingsRow(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str = ""
