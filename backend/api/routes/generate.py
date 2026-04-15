from fastapi import APIRouter, HTTPException
from models.schemas import GenerateRequest, GenerateResponse, JobStatusResponse, JobStatus
from models.styles import STYLES
from services.storage import get_session_uploads
from services.face_selector import select_best_face
from workers.job_queue import create_job, get_job, enqueue_job

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenerateResponse)
async def start_generation(req: GenerateRequest):
    # Validate styles
    unknown = [s for s in req.style_ids if s not in STYLES]
    if unknown:
        raise HTTPException(400, f"Unknown style IDs: {unknown}")

    # Validate session has uploads
    uploads = get_session_uploads(req.session_id)
    if not uploads:
        raise HTTPException(404, f"No uploads found for session {req.session_id}")

    # Pick best face reference
    best_face = select_best_face(uploads)
    if not best_face:
        raise HTTPException(400, "Could not find a usable face photo")

    # Create and enqueue job
    job = create_job(session_id=req.session_id, style_ids=req.style_ids)
    enqueue_job(job, face_image_path=best_face)

    return GenerateResponse(
        job_id=job.job_id,
        session_id=req.session_id,
        status=JobStatus.pending,
        message="Generation started. Poll /generate/status/{job_id} for progress.",
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=job.job_id,
        session_id=job.session_id,
        status=job.status,
        progress=job.progress,
        total_images=job.total_images,
        done_images=job.done_images,
        error=job.error,
        result_urls=job.result_urls,
    )
