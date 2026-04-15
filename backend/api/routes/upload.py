import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from models.schemas import UploadResponse
from services.storage import save_uploads

router = APIRouter(prefix="/upload", tags=["upload"])

MIN_PHOTOS = 3
MAX_PHOTOS = 10


@router.post("", response_model=UploadResponse)
async def upload_photos(
    files: List[UploadFile] = File(..., description="5-10 face photos"),
):
    if len(files) < MIN_PHOTOS:
        raise HTTPException(400, f"Upload at least {MIN_PHOTOS} photos for best results")
    if len(files) > MAX_PHOTOS:
        raise HTTPException(400, f"Maximum {MAX_PHOTOS} photos allowed")

    session_id = uuid.uuid4().hex
    saved = await save_uploads(session_id, files)

    if len(saved) < 1:
        raise HTTPException(400, "No valid images were saved. Use JPG/PNG, max 10 MB each.")

    return UploadResponse(
        session_id=session_id,
        uploaded_count=len(saved),
        message=f"Uploaded {len(saved)} photos. Session ready.",
    )
