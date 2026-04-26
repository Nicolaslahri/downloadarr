from __future__ import annotations

import asyncio
import json
import xml.etree.ElementTree as ET

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import settings as env_settings
from app.db.settings_store import load_all, merge_with_env, parse_list, patch as patch_settings
from app.services.tools import (
    ensure_all as ensure_tools,
    save_uploaded_tool,
    status as tools_status,
)
from app.services.usenet.nntp import NntpConfig, _Conn

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


class FreeTorrentSources(BaseModel):
    torrents_csv: bool = True
    nyaa: bool = True
    x1337: bool = True


class QualityConfig(BaseModel):
    chain: list[str] = ["lossless", "320", "256", "192"]
    floor: str = "192"


class SettingsOut(BaseModel):
    library_path: str
    quality_profile: str
    preferred_sources: list[str]
    anthropic_api_key_set: bool
    spotify_configured: bool
    usenet_indexers: list[UsenetIndexer]
    usenet_servers: list[UsenetServer]
    torrent_indexers: list[TorrentIndexer]
    free_torrents: FreeTorrentSources
    quality: QualityConfig


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
    free_torrents: FreeTorrentSources | None = None
    quality: QualityConfig | None = None


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


def _bool_setting(cfg: dict[str, str], key: str, default: bool = True) -> bool:
    v = cfg.get(key)
    if v is None or v == "":
        return default
    return str(v).lower() not in ("0", "false", "no", "off")


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
        free_torrents=FreeTorrentSources(
            torrents_csv=_bool_setting(cfg, "free_src_torrents_csv", True),
            nyaa=_bool_setting(cfg, "free_src_nyaa", True),
            x1337=_bool_setting(cfg, "free_src_x1337", True),
        ),
        quality=QualityConfig(
            chain=[t for t in (cfg.get("quality_chain") or "lossless,320,256,192").split(",") if t],
            floor=(cfg.get("quality_floor") or "192").strip(),
        ),
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

    if "free_torrents" in payload and payload["free_torrents"] is not None:
        ft = payload["free_torrents"]
        if isinstance(ft, dict):
            updates["free_src_torrents_csv"] = "true" if ft.get("torrents_csv", True) else "false"
            updates["free_src_nyaa"] = "true" if ft.get("nyaa", True) else "false"
            updates["free_src_x1337"] = "true" if ft.get("x1337", True) else "false"

    if "quality" in payload and payload["quality"] is not None:
        q = payload["quality"]
        if isinstance(q, dict):
            chain = q.get("chain")
            if isinstance(chain, list):
                updates["quality_chain"] = ",".join(str(t) for t in chain)
            floor = q.get("floor")
            if floor:
                updates["quality_floor"] = str(floor)

    if updates:
        patch_settings(updates)

    cfg = merge_with_env(load_all(), env_settings)
    return _to_out(cfg)


# ---------------------------------------------------------------------------
# Test-connection endpoints
# ---------------------------------------------------------------------------


class TestResult(BaseModel):
    ok: bool
    message: str
    detail: dict | None = None


def _resolve_secret(list_key: str, name: str, secret_field: str) -> str:
    """If the UI submits a row with a blank secret but a name that matches
    a previously-saved row, use the stored secret for the test."""
    if not name:
        return ""
    for e in parse_list(load_all().get(list_key, "[]")):
        if (e.get("name") or "").lower() == name.lower():
            return e.get(secret_field) or ""
    return ""


class NewznabTest(BaseModel):
    name: str = ""
    url: str
    api_key: str = ""


async def _newznab_caps(url: str, api_key: str) -> TestResult:
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            r = await client.get(
                f"{url.rstrip('/')}/api",
                params={"t": "caps", "apikey": api_key} if api_key else {"t": "caps"},
            )
    except Exception as e:
        return TestResult(ok=False, message=f"Connection failed: {e}")
    if r.status_code == 401:
        return TestResult(ok=False, message="API key rejected (HTTP 401)")
    if r.status_code != 200:
        return TestResult(ok=False, message=f"HTTP {r.status_code}: {r.text[:160]}")
    try:
        root = ET.fromstring(r.text)
    except Exception:
        return TestResult(ok=False, message="Response is not valid Newznab/Torznab XML")
    if root.tag.lower() == "error":
        msg = root.get("description") or "Indexer returned an error"
        return TestResult(ok=False, message=msg)
    server_name = ""
    for child in root:
        tag = child.tag.split("}", 1)[-1].lower()
        if tag == "server":
            server_name = child.get("title") or child.get("appversion") or ""
            break
    cats = sum(1 for c in root.iter() if c.tag.split("}", 1)[-1].lower() == "category")
    return TestResult(
        ok=True,
        message=f"Connected{' to ' + server_name if server_name else ''} — {cats} categories",
        detail={"server": server_name, "categories": cats},
    )


@router.post("/test/usenet-indexer", response_model=TestResult)
async def test_usenet_indexer(body: NewznabTest) -> TestResult:
    if not body.url:
        return TestResult(ok=False, message="URL required")
    api_key = body.api_key or _resolve_secret("usenet_indexers", body.name, "api_key")
    if not api_key:
        return TestResult(ok=False, message="API key required")
    return await _newznab_caps(body.url, api_key)


@router.post("/test/torrent-indexer", response_model=TestResult)
async def test_torrent_indexer(body: NewznabTest) -> TestResult:
    if not body.url:
        return TestResult(ok=False, message="URL required")
    api_key = body.api_key or _resolve_secret("torrent_indexers", body.name, "api_key")
    return await _newznab_caps(body.url, api_key)


class NntpTest(BaseModel):
    name: str = ""
    host: str
    port: int = 563
    ssl: bool = True
    username: str = ""
    password: str = ""


@router.post("/test/usenet-server", response_model=TestResult)
async def test_usenet_server(body: NntpTest) -> TestResult:
    if not body.host:
        return TestResult(ok=False, message="Host required")
    pwd = body.password or _resolve_secret("usenet_servers", body.name, "password")
    cfg = NntpConfig(
        host=body.host,
        port=body.port,
        ssl=body.ssl,
        username=body.username,
        password=pwd,
        connections=1,
    )
    conn = _Conn(cfg)
    try:
        await asyncio.wait_for(conn.connect(), timeout=15)
    except asyncio.TimeoutError:
        return TestResult(ok=False, message="Timeout connecting to NNTP server")
    except Exception as e:
        return TestResult(ok=False, message=f"NNTP error: {e}")
    finally:
        try:
            await conn.close()
        except Exception:
            pass
    auth_state = "authenticated" if cfg.username else "anonymous"
    return TestResult(
        ok=True,
        message=f"Connected to {cfg.host}:{cfg.port} ({auth_state})",
    )


class AnthropicTest(BaseModel):
    api_key: str = ""


@router.post("/test/anthropic", response_model=TestResult)
async def test_anthropic(body: AnthropicTest) -> TestResult:
    api_key = body.api_key or load_all().get("anthropic_api_key", "")
    if not api_key:
        return TestResult(ok=False, message="API key required")
    try:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=api_key)
        msg = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4,
            messages=[{"role": "user", "content": "ping"}],
        )
        usage = getattr(msg, "usage", None)
        in_tok = getattr(usage, "input_tokens", None) if usage else None
        return TestResult(
            ok=True,
            message=f"Authenticated with Claude (model={msg.model})",
            detail={"input_tokens": in_tok},
        )
    except Exception as e:
        return TestResult(ok=False, message=f"Anthropic error: {e}")


class SpotifyTest(BaseModel):
    client_id: str = ""
    client_secret: str = ""


@router.get("/tools")
async def get_tools() -> dict:
    return await tools_status()


@router.post("/tools/install")
async def install_tools(force: bool = False) -> dict:
    return await ensure_tools(force=force)


@router.post("/tools/upload")
async def upload_tool(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    if len(content) > 50_000_000:
        raise HTTPException(413, "File too large (max 50 MB)")
    if len(content) < 10_000:
        raise HTTPException(400, "File too small to be a real binary")
    result = save_uploaded_tool(file.filename or "", content)
    if not result.get("ok"):
        raise HTTPException(400, result.get("error", "Upload rejected"))
    return result


@router.post("/test/spotify", response_model=TestResult)
async def test_spotify(body: SpotifyTest) -> TestResult:
    cid = body.client_id or load_all().get("spotify_client_id", "")
    sec = body.client_secret or load_all().get("spotify_client_secret", "")
    if not cid or not sec:
        return TestResult(ok=False, message="Client ID and secret required")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                "https://accounts.spotify.com/api/token",
                data={"grant_type": "client_credentials"},
                auth=(cid, sec),
            )
        if r.status_code == 200:
            return TestResult(ok=True, message="Spotify credentials valid")
        return TestResult(
            ok=False,
            message=f"Spotify rejected credentials (HTTP {r.status_code})",
            detail={"body": r.text[:200]},
        )
    except Exception as e:
        return TestResult(ok=False, message=f"Spotify error: {e}")
