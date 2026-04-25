from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> Path:
    p = Path.cwd() / ".data"
    p.mkdir(exist_ok=True)
    return p


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = f"sqlite+aiosqlite:///{_default_data_dir() / 'musicdl.db'}"
    redis_url: str = ""

    library_path: str = str(_default_data_dir() / "library")
    downloads_path: str = str(_default_data_dir() / "downloads")

    anthropic_api_key: str = ""

    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    prowlarr_url: str = ""
    prowlarr_api_key: str = ""

    nzbhydra_url: str = ""
    nzbhydra_api_key: str = ""

    qbt_url: str = ""
    qbt_user: str = ""
    qbt_pass: str = ""

    sab_url: str = ""
    sab_api_key: str = ""

    cors_origins: list[str] = ["*"]


settings = Settings()

Path(settings.library_path).mkdir(parents=True, exist_ok=True)
Path(settings.downloads_path).mkdir(parents=True, exist_ok=True)
