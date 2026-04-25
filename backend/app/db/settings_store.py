from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models import SettingsRow

DEFAULTS: dict[str, str] = {
    "library_path": "",
    "quality_profile": "best",
    "preferred_sources": "ytdlp,spotdl,torrent,nzb",
    "anthropic_api_key": "",
    "spotify_client_id": "",
    "spotify_client_secret": "",
    "prowlarr_url": "",
    "prowlarr_api_key": "",
    "nzbhydra_url": "",
    "nzbhydra_api_key": "",
    "qbt_url": "",
    "qbt_user": "",
    "qbt_pass": "",
    "sab_url": "",
    "sab_api_key": "",
}


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


def merge_with_env(stored: dict[str, str], env_settings) -> dict[str, str]:
    """DB settings take precedence; fall back to env if DB value is empty."""
    out = dict(stored)
    fallbacks = {
        "library_path": env_settings.library_path,
        "anthropic_api_key": env_settings.anthropic_api_key,
        "spotify_client_id": env_settings.spotify_client_id,
        "spotify_client_secret": env_settings.spotify_client_secret,
        "prowlarr_url": env_settings.prowlarr_url,
        "prowlarr_api_key": env_settings.prowlarr_api_key,
        "nzbhydra_url": env_settings.nzbhydra_url,
        "nzbhydra_api_key": env_settings.nzbhydra_api_key,
        "qbt_url": env_settings.qbt_url,
        "qbt_user": env_settings.qbt_user,
        "qbt_pass": env_settings.qbt_pass,
        "sab_url": env_settings.sab_url,
        "sab_api_key": env_settings.sab_api_key,
    }
    for k, v in fallbacks.items():
        if not out.get(k):
            out[k] = v
    return out
