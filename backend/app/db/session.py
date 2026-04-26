from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Columns added in v2 that need ALTER-TABLE for existing databases.
# Mapping: column name → SQL DDL fragment (sqlite-friendly).
_NEW_TRACK_COLUMNS: dict[str, str] = {
    "mb_recording_id": "TEXT",
    "album_mbid": "TEXT",
    "track_no": "INTEGER",
    "year": "INTEGER",
    "bytes_done": "INTEGER NOT NULL DEFAULT 0",
    "bytes_total": "INTEGER NOT NULL DEFAULT 0",
    "speed_kbps": "INTEGER NOT NULL DEFAULT 0",
    "quality_format": "TEXT",
    "quality_bitrate": "INTEGER",
    "quality_lossless": "INTEGER NOT NULL DEFAULT 0",
    "source_url_hint": "TEXT",
}


def _existing_columns(sync_conn, table: str) -> set[str]:
    insp = inspect(sync_conn)
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


async def _migrate_track_columns() -> None:
    async with engine.begin() as conn:
        existing = await conn.run_sync(lambda sc: _existing_columns(sc, "track"))
        if not existing:
            return
        for col, ddl in _NEW_TRACK_COLUMNS.items():
            if col not in existing:
                await conn.execute(text(f"ALTER TABLE track ADD COLUMN {col} {ddl}"))


async def init_db() -> None:
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    await _migrate_track_columns()


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
