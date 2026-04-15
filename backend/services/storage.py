import os
import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from typing import List

UPLOAD_DIR = Path("storage/uploads")
RESULT_DIR = Path("storage/results")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def session_upload_dir(session_id: str) -> Path:
    p = UPLOAD_DIR / session_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def session_result_dir(session_id: str) -> Path:
    p = RESULT_DIR / session_id
    p.mkdir(parents=True, exist_ok=True)
    return p


async def save_uploads(session_id: str, files: List[UploadFile]) -> List[str]:
    """Save uploaded photos, return list of saved file paths."""
    upload_dir = session_upload_dir(session_id)
    saved_paths = []

    for file in files:
        ext = Path(file.filename or "photo.jpg").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue

        file_id = uuid.uuid4().hex
        dest = upload_dir / f"{file_id}{ext}"

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            continue

        async with aiofiles.open(dest, "wb") as f:
            await f.write(content)

        saved_paths.append(str(dest))

    return saved_paths


def get_session_uploads(session_id: str) -> List[str]:
    upload_dir = UPLOAD_DIR / session_id
    if not upload_dir.exists():
        return []
    return [
        str(p) for p in upload_dir.iterdir()
        if p.suffix.lower() in ALLOWED_EXTENSIONS
    ]


def get_session_results(session_id: str) -> List[dict]:
    result_dir = RESULT_DIR / session_id
    if not result_dir.exists():
        return []
    results = []
    for p in sorted(result_dir.iterdir()):
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            results.append({
                "url": f"/results/{session_id}/{p.name}",
                "filename": p.name,
                "style_id": p.stem.split("_")[0] if "_" in p.stem else "unknown",
            })
    return results
