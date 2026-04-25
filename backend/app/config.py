from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://musicdl:musicdl@postgres:5432/musicdl"
    redis_url: str = "redis://redis:6379/0"
    library_path: str = "/library"
    downloads_path: str = "/downloads"

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


settings = Settings()
