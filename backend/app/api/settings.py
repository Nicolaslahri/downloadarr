from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as env_settings
from app.db.session import get_session
from app.db.settings_store import load_all, merge_with_env, patch as patch_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsOut(BaseModel):
    library_path: str
    quality_profile: str
    preferred_sources: list[str]
    anthropic_api_key_set: bool
    spotify_configured: bool
    prowlarr_configured: bool
    nzbhydra_configured: bool
    qbt_configured: bool
    sab_configured: bool


class SettingsPatch(BaseModel):
    library_path: str | None = None
    quality_profile: str | None = None
    preferred_sources: list[str] | None = None
    anthropic_api_key: str | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    prowlarr_url: str | None = None
    prowlarr_api_key: str | None = None
    nzbhydra_url: str | None = None
    nzbhydra_api_key: str | None = None
    qbt_url: str | None = None
    qbt_user: str | None = None
    qbt_pass: str | None = None
    sab_url: str | None = None
    sab_api_key: str | None = None


def _to_out(cfg: dict[str, str]) -> SettingsOut:
    return SettingsOut(
        library_path=cfg.get("library_path") or env_settings.library_path,
        quality_profile=cfg.get("quality_profile") or "best",
        preferred_sources=[s for s in (cfg.get("preferred_sources") or "").split(",") if s],
        anthropic_api_key_set=bool(cfg.get("anthropic_api_key")),
        spotify_configured=bool(cfg.get("spotify_client_id") and cfg.get("spotify_client_secret")),
        prowlarr_configured=bool(cfg.get("prowlarr_url") and cfg.get("prowlarr_api_key")),
        nzbhydra_configured=bool(cfg.get("nzbhydra_url") and cfg.get("nzbhydra_api_key")),
        qbt_configured=bool(cfg.get("qbt_url")),
        sab_configured=bool(cfg.get("sab_url") and cfg.get("sab_api_key")),
    )


@router.get("", response_model=SettingsOut)
async def get_settings(session: AsyncSession = Depends(get_session)) -> SettingsOut:
    cfg_db = await load_all(session)
    cfg = merge_with_env(cfg_db, env_settings)
    return _to_out(cfg)


@router.put("", response_model=SettingsOut)
async def update_settings(
    body: SettingsPatch, session: AsyncSession = Depends(get_session)
) -> SettingsOut:
    updates: dict[str, str] = {}
    payload = body.model_dump(exclude_unset=True)
    if "preferred_sources" in payload and payload["preferred_sources"] is not None:
        updates["preferred_sources"] = ",".join(payload.pop("preferred_sources"))
    for k, v in payload.items():
        if v is None:
            continue
        # Empty string for secrets means "leave as-is"
        if k in {
            "anthropic_api_key",
            "spotify_client_secret",
            "prowlarr_api_key",
            "nzbhydra_api_key",
            "qbt_pass",
            "sab_api_key",
        } and v == "":
            continue
        updates[k] = str(v)
    if updates:
        await patch_settings(session, updates)
    cfg_db = await load_all(session)
    cfg = merge_with_env(cfg_db, env_settings)
    return _to_out(cfg)
