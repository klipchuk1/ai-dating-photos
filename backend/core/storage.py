"""
Synchronous file I/O — safe to call from worker threads.
"""

import uuid
from pathlib import Path
from typing import List

UPLOAD_DIR = Path("storage/uploads")
RESULT_DIR = Path("storage/results")
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES   = 10 * 1024 * 1024  # 10 MB


# ── Directory helpers ──────────────────────────────────────────────────────────

def user_upload_dir(user_id: str) -> Path:
    p = UPLOAD_DIR / user_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def user_result_dir(user_id: str) -> Path:
    p = RESULT_DIR / user_id
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Upload ─────────────────────────────────────────────────────────────────────

def save_file(user_id: str, filename: str, content: bytes) -> str | None:
    """
    Save raw bytes to the user's upload folder.
    Returns the saved path, or None if extension / size is invalid.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXT:
        return None
    if len(content) > MAX_BYTES:
        return None

    dest = user_upload_dir(user_id) / f"{uuid.uuid4().hex}{ext}"
    dest.write_bytes(content)
    return str(dest)


# ── Query ──────────────────────────────────────────────────────────────────────

def list_uploads(user_id: str) -> List[str]:
    d = UPLOAD_DIR / user_id
    if not d.exists():
        return []
    return [str(p) for p in d.iterdir() if p.suffix.lower() in ALLOWED_EXT]


def list_results(user_id: str) -> List[dict]:
    d = RESULT_DIR / user_id
    if not d.exists():
        return []
    out = []
    for p in sorted(d.iterdir()):
        if p.suffix.lower() in ALLOWED_EXT:
            out.append({
                "url":      f"/results/{user_id}/{p.name}",
                "filename": p.name,
                "path":     str(p),
            })
    return out
