from __future__ import annotations

import json
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.models import SettingsRow

DEFAULTS: dict[str, str] = {
    "library_path": "",
    "quality_profile": "best",
    "preferred_sources": "nzb,torrent",
    "anthropic_api_key": "",
    "spotify_client_id": "",
    "spotify_client_secret": "",
    # JSON-encoded lists of source configs; UI manages via list editors.
    "usenet_indexers": "[]",
    "usenet_servers": "[]",
    "torrent_indexers": "[]",
}

LIST_KEYS = {"usenet_indexers", "usenet_servers", "torrent_indexers"}


async def load_all(session: AsyncSession) -> dict[str, str]:
    result = await session.exec(select(SettingsRow))
    rows = result.all()
    out = dict(DEFAULTS)
    for r in rows:
        out[r.key] = r.value
    return out


async def get(session: AsyncSession, key: str) -> str:
    row = await session.get(SettingsRow, key)
    return row.value if row else DEFAULTS.get(key, "")


async def set_value(session: AsyncSession, key: str, value: str) -> None:
    row = await session.get(SettingsRow, key)
    if row is None:
        session.add(SettingsRow(key=key, value=value))
    else:
        row.value = value
        session.add(row)
    await session.commit()


async def patch(session: AsyncSession, updates: dict[str, str]) -> None:
    for k, v in updates.items():
        await set_value(session, k, v)


def parse_list(raw: str) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def merge_with_env(stored: dict[str, str], env_settings) -> dict[str, str]:
    out = dict(stored)
    fallbacks = {
        "library_path": env_settings.library_path,
        "anthropic_api_key": env_settings.anthropic_api_key,
        "spotify_client_id": env_settings.spotify_client_id,
        "spotify_client_secret": env_settings.spotify_client_secret,
    }
    for k, v in fallbacks.items():
        if not out.get(k):
            out[k] = v
    return out
