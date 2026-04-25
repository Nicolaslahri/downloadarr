from arq.connections import RedisSettings

from app.config import settings


def _redis_settings() -> RedisSettings:
    url = settings.redis_url
    return RedisSettings.from_dsn(url)


async def ping(ctx: dict) -> str:
    return "pong"


class WorkerSettings:
    functions = [ping]
    redis_settings = _redis_settings()
