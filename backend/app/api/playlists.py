from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/playlists", tags=["playlists"])


class ImportRequest(BaseModel):
    url: str


class ImportResponse(BaseModel):
    accepted: bool
    url: str
    detail: str


@router.post("/import", response_model=ImportResponse)
async def import_playlist(req: ImportRequest) -> ImportResponse:
    return ImportResponse(
        accepted=True,
        url=req.url,
        detail="Resolver dispatch not wired yet — skeleton only.",
    )
