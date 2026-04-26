import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import jobs, library, playlists, queue as queue_api, settings as settings_api, tracks
from app.config import settings as env_settings
from app.db.session import init_db
from app.services.events import bus
from app.services.runner import shutdown as shutdown_runner
from app.services.tools import ensure_all as ensure_tools


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    bus.emit("log", "MusicDownloadarr started")
    # Don't block startup on tool downloads — fire and forget.
    asyncio.create_task(ensure_tools())
    try:
        yield
    finally:
        await shutdown_runner()


app = FastAPI(title="MusicDownloadarr", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=env_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(playlists.router)
app.include_router(tracks.router)
app.include_router(jobs.router)
app.include_router(library.router)
app.include_router(queue_api.router)
app.include_router(settings_api.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
