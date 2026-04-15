from fastapi import APIRouter, HTTPException
from models.schemas import GalleryResponse
from services.storage import get_session_results

router = APIRouter(prefix="/gallery", tags=["gallery"])


@router.get("/{session_id}", response_model=GalleryResponse)
async def get_gallery(session_id: str):
    images = get_session_results(session_id)
    if not images:
        raise HTTPException(404, f"No results for session {session_id} yet")
    return GalleryResponse(session_id=session_id, images=images)
