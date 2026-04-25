from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings as env_settings
from app.db.settings_store import load_all, merge_with_env, parse_list, patch as patch_settings

router = APIRouter(prefix="/settings", tags=["settings"])


class UsenetIndexer(BaseModel):
    name: str
    url: str
    api_key: str = ""
    api_key_set: bool = False


class UsenetServer(BaseModel):
    name: str
    host: str
    port: int = 563
    ssl: bool = True
    username: str = ""
    password: str = ""
    password_set: bool = False
    connections: int = 10


class TorrentIndexer(BaseModel):
    name: str
    url: str
    api_key: str = ""
    api_key_set: bool = False


class SettingsOut(BaseModel):
    library_path: str
    quality_profile: str
    preferred_sources: list[str]
    anthropic_api_key_set: bool
    spotify_configured: bool
    usenet_indexers: list[UsenetIndexer]
    usenet_servers: list[UsenetServer]
    torrent_indexers: list[TorrentIndexer]


class SettingsPatch(BaseModel):
    library_path: str | None = None
    quality_profile: str | None = None
    preferred_sources: list[str] | None = None
    anthropic_api_key: str | None = None
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    usenet_indexers: list[dict] | None = None
    usenet_servers: list[dict] | None = None
    torrent_indexers: list[dict] | None = None


def _redact_indexer(item: dict, key: str = "api_key") -> dict:
    has = bool(item.get(key))
    out = {k: v for k, v in item.items() if k != key}
    out[f"{key}_set"] = has
    return out


def _redact_server(item: dict) -> dict:
    has = bool(item.get("password"))
    out = {k: v for k, v in item.items() if k != "password"}
    out["password_set"] = has
    return out


def _to_out(cfg: dict[str, str]) -> SettingsOut:
    return SettingsOut(
        library_path=cfg.get("library_path") or env_settings.library_path,
        quality_profile=cfg.get("quality_profile") or "best",
        preferred_sources=[s for s in (cfg.get("preferred_sources") or "").split(",") if s],
        anthropic_api_key_set=bool(cfg.get("anthropic_api_key")),
        spotify_configured=bool(cfg.get("spotify_client_id") and cfg.get("spotify_client_secret")),
        usenet_indexers=[
            UsenetIndexer(**_redact_indexer(i))
            for i in parse_list(cfg.get("usenet_indexers", "[]"))
        ],
        usenet_servers=[
            UsenetServer(**_redact_server(s))
            for s in parse_list(cfg.get("usenet_servers", "[]"))
        ],
        torrent_indexers=[
            TorrentIndexer(**_redact_indexer(i))
            for i in parse_list(cfg.get("torrent_indexers", "[]"))
        ],
    )


def _merge_secret_lists(
    existing: list[dict],
    incoming: list[dict],
    secret_keys: tuple[str, ...],
) -> list[dict]:
    by_name = {(e.get("name") or "").lower(): e for e in existing}
    out: list[dict] = []
    for item in incoming:
        merged = dict(item)
        prior = by_name.get((item.get("name") or "").lower())
        if prior:
            for k in secret_keys:
                if not merged.get(k) and prior.get(k):
                    merged[k] = prior[k]
        for k in list(merged.keys()):
            if k.endswith("_set"):
                merged.pop(k, None)
        out.append(merged)
    return out


@router.get("", response_model=SettingsOut)
async def get_settings() -> SettingsOut:
    cfg = merge_with_env(load_all(), env_settings)
    return _to_out(cfg)


@router.put("", response_model=SettingsOut)
async def update_settings(body: SettingsPatch) -> SettingsOut:
    cfg_db = load_all()
    payload = body.model_dump(exclude_unset=True)
    updates: dict[str, str] = {}

    if "preferred_sources" in payload and payload["preferred_sources"] is not None:
        updates["preferred_sources"] = ",".join(payload.pop("preferred_sources"))

    for k in ("library_path", "quality_profile", "spotify_client_id"):
        if k in payload and payload[k] is not None:
            updates[k] = str(payload[k])

    for k in ("anthropic_api_key", "spotify_client_secret"):
        if k in payload and payload[k]:
            updates[k] = str(payload[k])

    if "usenet_indexers" in payload and payload["usenet_indexers"] is not None:
        existing = parse_list(cfg_db.get("usenet_indexers", "[]"))
        merged = _merge_secret_lists(existing, payload["usenet_indexers"], ("api_key",))
        updates["usenet_indexers"] = json.dumps(merged)

    if "usenet_servers" in payload and payload["usenet_servers"] is not None:
        existing = parse_list(cfg_db.get("usenet_servers", "[]"))
        merged = _merge_secret_lists(existing, payload["usenet_servers"], ("password",))
        updates["usenet_servers"] = json.dumps(merged)

    if "torrent_indexers" in payload and payload["torrent_indexers"] is not None:
        existing = parse_list(cfg_db.get("torrent_indexers", "[]"))
        merged = _merge_secret_lists(existing, payload["torrent_indexers"], ("api_key",))
        updates["torrent_indexers"] = json.dumps(merged)

    if updates:
        patch_settings(updates)

    cfg = merge_with_env(load_all(), env_settings)
    return _to_out(cfg)
