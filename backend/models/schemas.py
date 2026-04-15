from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field
from core.jobs import JobStatus


# ── POST /upload ───────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    user_id:        str
    uploaded_count: int
    message:        str


# ── GET /styles ────────────────────────────────────────────────────────────────

class StyleOption(BaseModel):
    id:              str
    name:            str
    description:     str
    preview_url:     str
    style_strength:  float = Field(ge=0.0, le=1.0)


# ── POST /generate ─────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    user_id:  str
    style_id: str


class GenerateResponse(BaseModel):
    job_id:   str
    user_id:  str
    style_id: str
    status:   JobStatus


# ── GET /status/{job_id} ───────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    job_id:   str
    user_id:  str
    style_id: str
    status:   JobStatus
    progress: int = Field(ge=0, le=100)
    error:    Optional[str] = None


# ── GET /result/{job_id} ───────────────────────────────────────────────────────

class PhotoOut(BaseModel):
    url:              str
    similarity_score: float


class ResultResponse(BaseModel):
    job_id:    str
    user_id:   str
    style_id:  str
    photos:    List[PhotoOut]
    top_photo: Optional[PhotoOut]
