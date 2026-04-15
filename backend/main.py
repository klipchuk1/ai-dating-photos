"""
AI Dating Photos — FastAPI backend

Endpoints
---------
POST /upload                   Upload photos → user_id
GET  /styles                   List available styles
POST /generate                 Start generation → job_id
GET  /status/{job_id}          Poll progress 0-100
GET  /result/{job_id}          Final photos + similarity scores + top pick

Threading model
---------------
Replicate API calls are synchronous and blocking.
Each generation job runs in a dedicated OS thread via ThreadPoolExecutor (core/worker.py).
FastAPI's async event loop is never blocked — routes only read job state via thread-safe
Job.snapshot() / JobStore.get().
"""

import logging
import os
import uuid
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.jobs import JobStatus, store
from core.storage import list_uploads, save_file
from core.worker import submit
from models.schemas import (
    GenerateRequest,
    GenerateResponse,
    PhotoOut,
    ResultResponse,
    StatusResponse,
    StyleOption,
    UploadResponse,
)
from models.styles import STYLES

load_dotenv()
logging.basicConfig(level=logging.INFO)

# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Dating Photos",
    version="1.0.0",
    description="Identity-preserving dating photo generation via InstantID + SDXL",
)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated images as static files
for folder in ("storage/uploads", "storage/results", "storage/previews"):
    Path(folder).mkdir(parents=True, exist_ok=True)

app.mount("/results",  StaticFiles(directory="storage/results"),  name="results")
app.mount("/previews", StaticFiles(directory="storage/previews"), name="previews")


# ── POST /upload ───────────────────────────────────────────────────────────────

MIN_PHOTOS = 3
MAX_PHOTOS = 10

@app.post("/upload", response_model=UploadResponse, summary="Upload face photos")
async def upload(
    files: List[UploadFile] = File(..., description="3–10 face photos (JPG/PNG/WebP, ≤10 MB each)"),
):
    """
    Accept 3–10 photos, save them, and return a `user_id` that identifies this session.
    Pass `user_id` to `POST /generate`.
    """
    if len(files) < MIN_PHOTOS:
        raise HTTPException(400, f"Upload at least {MIN_PHOTOS} photos for best results.")
    if len(files) > MAX_PHOTOS:
        raise HTTPException(400, f"Maximum {MAX_PHOTOS} photos per session.")

    user_id = uuid.uuid4().hex
    saved   = 0

    for f in files:
        content = await f.read()
        path    = save_file(user_id, f.filename or "photo.jpg", content)
        if path:
            saved += 1

    if saved == 0:
        raise HTTPException(400, "No valid images saved. Use JPG/PNG/WebP, max 10 MB each.")

    return UploadResponse(
        user_id=user_id,
        uploaded_count=saved,
        message=f"{saved} photo(s) uploaded. Use user_id to start generation.",
    )


# ── GET /styles ────────────────────────────────────────────────────────────────

@app.get("/styles", response_model=List[StyleOption], summary="List available styles")
async def get_styles():
    """Return all available photo styles. Show these in the swipe UI."""
    return [
        StyleOption(
            id=s["id"],
            name=s["name"],
            description=s["description"],
            preview_url=s["preview_url"],
            style_strength=s["style_strength"],
        )
        for s in STYLES.values()
    ]


# ── POST /generate ─────────────────────────────────────────────────────────────

@app.post("/generate", response_model=GenerateResponse, summary="Start generation job")
async def generate(req: GenerateRequest):
    """
    Kick off a generation job for the given user and style.
    Returns a `job_id` — poll `GET /status/{job_id}` to track progress.

    The job runs in a background thread; this endpoint returns immediately.
    """
    # Validate style
    if req.style_id not in STYLES:
        raise HTTPException(400, f"Unknown style_id '{req.style_id}'. Call GET /styles for valid IDs.")

    # Validate uploads exist — face selection happens inside the worker thread
    if not list_uploads(req.user_id):
        raise HTTPException(404, f"No uploads found for user_id '{req.user_id}'. Call POST /upload first.")

    # Create job and dispatch to thread pool
    job = store.create(user_id=req.user_id, style_id=req.style_id)
    submit(job)

    return GenerateResponse(
        job_id=job.job_id,
        user_id=job.user_id,
        style_id=job.style_id,
        status=JobStatus.pending,
    )


# ── GET /status/{job_id} ───────────────────────────────────────────────────────

@app.get("/status/{job_id}", response_model=StatusResponse, summary="Poll job progress")
async def get_status(job_id: str):
    """
    Returns current job status and progress (0–100).

    Statuses:
    - `pending`    — queued, not started yet
    - `processing` — running (check `progress` field)
    - `done`       — completed, call GET /result/{job_id}
    - `failed`     — check `error` field
    """
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found.")

    snap = job.snapshot()
    return StatusResponse(
        job_id=snap["job_id"],
        user_id=snap["user_id"],
        style_id=snap["style_id"],
        status=snap["status"],
        progress=snap["progress"],
        error=snap["error"],
    )


# ── GET /result/{job_id} ───────────────────────────────────────────────────────

@app.get("/result/{job_id}", response_model=ResultResponse, summary="Get generation results")
async def get_result(job_id: str):
    """
    Returns generated photos with per-image similarity scores and the top pick.

    - `photos`    — all generated images, each with URL and similarity_score (0–1)
    - `top_photo` — image with the highest similarity score (best identity match)
    - `similarity_score` — ArcFace cosine similarity; 1.0 = identical, 0.8+ = great

    Only available when status == `done`.
    """
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found.")

    snap = job.snapshot()

    if snap["status"] == JobStatus.failed:
        raise HTTPException(500, f"Job failed: {snap['error']}")

    if snap["status"] != JobStatus.done:
        raise HTTPException(
            409,
            f"Job is not done yet (status={snap['status']}, progress={snap['progress']}%). "
            "Poll GET /status/{job_id} first.",
        )

    photos = [
        PhotoOut(url=p.url, similarity_score=p.similarity_score)
        for p in snap["photos"]
    ]
    top = (
        PhotoOut(url=snap["top_photo"].url, similarity_score=snap["top_photo"].similarity_score)
        if snap["top_photo"]
        else None
    )

    return ResultResponse(
        job_id=snap["job_id"],
        user_id=snap["user_id"],
        style_id=snap["style_id"],
        photos=photos,
        top_photo=top,
    )


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health", include_in_schema=False)
async def health():
    return {
        "status": "ok",
        "replicate_configured": bool(os.getenv("REPLICATE_API_TOKEN")),
    }
