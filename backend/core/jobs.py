"""
Thread-safe job store.

All writes to Job fields go through Job.update() which holds a Lock,
so worker threads and FastAPI handler threads never race.
"""

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class JobStatus(str, Enum):
    pending    = "pending"
    processing = "processing"
    done       = "done"
    failed     = "failed"


@dataclass
class PhotoResult:
    url: str
    local_path: str
    similarity_score: float = 0.0


@dataclass
class Job:
    job_id:    str
    user_id:   str
    style_id:  str
    status:    JobStatus       = JobStatus.pending
    progress:  int             = 0          # 0–100
    photos:    list            = field(default_factory=list)   # List[PhotoResult]
    top_photo: Optional[PhotoResult] = None
    error:     Optional[str]   = None
    _lock:     threading.Lock  = field(default_factory=threading.Lock, repr=False, compare=False)

    def update(self, **kwargs) -> None:
        """Thread-safe bulk field update."""
        with self._lock:
            for key, val in kwargs.items():
                setattr(self, key, val)

    def snapshot(self) -> dict:
        """Return a thread-safe copy of mutable state for serialisation."""
        with self._lock:
            return {
                "job_id":    self.job_id,
                "user_id":   self.user_id,
                "style_id":  self.style_id,
                "status":    self.status,
                "progress":  self.progress,
                "photos":    list(self.photos),
                "top_photo": self.top_photo,
                "error":     self.error,
            }


class JobStore:
    """Global in-memory job registry. Replace with Redis for multi-process."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, user_id: str, style_id: str) -> Job:
        job = Job(job_id=uuid.uuid4().hex, user_id=user_id, style_id=style_id)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)


# Module-level singleton
store = JobStore()
