"""User-mutable settings live in a JSON file at .data/settings.json.

Kept out of the SQLite DB on purpose: track/playlist data and config have
different lifecycles (you may legitimately want to wipe the DB to clear
test data without nuking your Usenet/torrent credentials).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, str] = {
    "library_path": "",
    "quality_profile": "best",
    "preferred_sources": "nzb,torrent",
    "anthropic_api_key": "",
    "spotify_client_id": "",
    "spotify_client_secret": "",
    "usenet_indexers": "[]",
    "usenet_servers": "[]",
    "torrent_indexers": "[]",
    # Free public torrent sources — default ON, no API keys needed.
    "free_src_torrents_csv": "true",
    "free_src_nyaa": "true",
    "free_src_x1337": "true",
    # Quality chain: ordered preference list, top-of-list first.
    # Floor: minimum acceptable tier; below this = failed track.
    "quality_chain": "lossless,320,256,192",
    "quality_floor": "192",
}

LIST_KEYS = {"usenet_indexers", "usenet_servers", "torrent_indexers"}


def _settings_path() -> Path:
    p = Path.cwd() / ".data" / "settings.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_all() -> dict[str, str]:
    p = _settings_path()
    if not p.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULTS)
    if not isinstance(data, dict):
        return dict(DEFAULTS)
    out = dict(DEFAULTS)
    for k, v in data.items():
        if v is None:
            out[k] = ""
        elif isinstance(v, str):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def save_all(cfg: dict[str, str]) -> None:
    p = _settings_path()
    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def patch(updates: dict[str, str]) -> None:
    cfg = load_all()
    cfg.update(updates)
    save_all(cfg)


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
