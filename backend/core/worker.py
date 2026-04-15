"""
Thread pool worker.

All Replicate I/O runs in daemon threads via ThreadPoolExecutor.
FastAPI's event loop stays unblocked — it only reads job state.

Thread safety
-------------
Job.update()  → acquires Job._lock  (writer)
Job.snapshot() → acquires Job._lock  (reader)
JobStore.get() → acquires JobStore._lock
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core.jobs import Job, JobStatus, PhotoResult
from core.similarity import compute_similarity
from services.pipeline import PipelineConfig, run_pipeline

logger = logging.getLogger(__name__)

# 4 concurrent generation threads — tune to your Replicate plan limits
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="gen")


# ── Job runner (runs inside a worker thread) ───────────────────────────────────

def _run(job: Job) -> None:
    logger.info("[worker] START  job=%s  user=%s  style=%s",
                job.job_id, job.user_id, job.style_id)
    job.update(status=JobStatus.processing, progress=0)

    try:
        # ── Generation pipeline ────────────────────────────────────────────────
        # run_pipeline selects the best face internally from user's uploads.
        saved_paths = run_pipeline(
            user_id=job.user_id,
            style_id=job.style_id,
            cfg=PipelineConfig(),
            on_progress=lambda p: job.update(progress=p),
        )

        if not saved_paths:
            raise RuntimeError("Pipeline returned no images")

        # ── Similarity scoring ─────────────────────────────────────────────────
        # Re-select the same reference face for scoring.
        from core.face_selector import select_best
        from core.storage import list_uploads
        face_path = select_best(list_uploads(job.user_id)) or ""

        photos: list[PhotoResult] = []
        n = len(saved_paths)

        for i, path in enumerate(saved_paths):
            score = compute_similarity(face_path, path) if face_path else 0.0
            url   = f"/results/{job.user_id}/{Path(path).name}"
            photos.append(PhotoResult(url=url, local_path=path, similarity_score=score))
            job.update(progress=90 + int((i + 1) / n * 9))   # 90 → 99

        top = max(photos, key=lambda p: p.similarity_score)
        job.update(status=JobStatus.done, progress=100, photos=photos, top_photo=top)
        logger.info("[worker] DONE  job=%s  images=%d  top_score=%.3f",
                    job.job_id, len(photos), top.similarity_score)

    except Exception as exc:
        logger.exception("[worker] FAILED  job=%s  error=%s", job.job_id, exc)
        job.update(status=JobStatus.failed, error=str(exc))


# ── Public API ─────────────────────────────────────────────────────────────────

def submit(job: Job) -> None:
    """
    Submit job to thread pool. Returns immediately — non-blocking.
    Face selection and all Replicate I/O happen inside the worker thread.
    """
    _pool.submit(_run, job)
