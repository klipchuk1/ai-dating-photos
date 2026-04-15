"""
In-memory async job queue.
MVP: no Redis needed — jobs stored in dict, worker runs as asyncio task.
Upgrade path: swap state dict for Redis + Celery when scaling.
"""

import asyncio
import uuid
from typing import Dict
from models.schemas import JobStatus


class Job:
    def __init__(self, job_id: str, session_id: str, style_ids: list):
        self.job_id = job_id
        self.session_id = session_id
        self.style_ids = style_ids
        self.status: JobStatus = JobStatus.pending
        self.progress: int = 0
        self.total_images: int = len(style_ids) * 2  # 2 images per style
        self.done_images: int = 0
        self.result_urls: list = []
        self.error: str | None = None


# Global in-memory store — replace with Redis for multi-process deployments
_jobs: Dict[str, Job] = {}


def create_job(session_id: str, style_ids: list) -> Job:
    job_id = uuid.uuid4().hex
    job = Job(job_id=job_id, session_id=session_id, style_ids=style_ids)
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


async def run_job(job: Job, face_image_path: str) -> None:
    """Execute pipeline for a job, updating status as it progresses."""
    from services.pipeline import run_full_pipeline
    from services.storage import get_session_results

    job.status = JobStatus.processing

    def on_progress(done: int, total: int) -> None:
        job.done_images = done * 2  # 2 images per style
        job.progress = int((done / total) * 100)

    try:
        await run_full_pipeline(
            session_id=job.session_id,
            face_image_path=face_image_path,
            style_ids=job.style_ids,
            on_progress=on_progress,
        )
        # Build result URLs from saved files
        results = get_session_results(job.session_id)
        job.result_urls = [r["url"] for r in results]
        job.progress = 100
        job.status = JobStatus.done

    except Exception as e:
        job.error = str(e)
        job.status = JobStatus.failed


def enqueue_job(job: Job, face_image_path: str) -> None:
    """Fire-and-forget: launch job as background asyncio task."""
    asyncio.create_task(run_job(job, face_image_path))
