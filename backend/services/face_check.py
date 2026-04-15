"""
services/face_check.py
──────────────────────
Face identity verification for generated photos.

Flow
────
1. Extract 512-dim ArcFace embedding from the reference photo.
2. Extract 512-dim ArcFace embedding from each generated photo.
3. Compute cosine similarity between reference and each generated image.
4. Filter: keep photos whose similarity ≥ threshold; delete the rest from disk.
5. Return CheckedPhoto records for every image (passed + rejected).

Backend priority
────────────────
PRIMARY   → InsightFace buffalo_l  (ArcFace, most accurate)
FALLBACK  → DeepFace ArcFace       (if insightface not installed)
LAST      → no embeddings available; log a warning and pass all photos through

Similarity scale (ArcFace cosine, both backends)
─────────────────────────────────────────────────
≥ 0.50   high identity match   — same person, different style ✓
0.35–0.50 moderate match       — acceptable for most use-cases
0.20–0.35 weak match           — face may have drifted
< 0.20   different person      — reject

Recommended thresholds
───────────────────────
THRESHOLD_PERMISSIVE = 0.25  (keep almost everything)
THRESHOLD_DEFAULT    = 0.35  (balanced — handles style variation well)
THRESHOLD_STRICT     = 0.50  (only near-identical results pass)
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Public threshold constants ─────────────────────────────────────────────────
THRESHOLD_PERMISSIVE: float = 0.25
THRESHOLD_DEFAULT:    float = 0.35
THRESHOLD_STRICT:     float = 0.50


# ── InsightFace (primary backend) ──────────────────────────────────────────────
try:
    from insightface.app import FaceAnalysis as _FaceAnalysis
    import cv2 as _cv2_if
    _INSIGHTFACE = True
except ImportError:
    _INSIGHTFACE = False
    logger.info("[face_check] insightface not installed — will try DeepFace fallback")

# ── DeepFace (fallback backend) ────────────────────────────────────────────────
try:
    from deepface import DeepFace as _DeepFace
    _DEEPFACE = True
except ImportError:
    _DEEPFACE = False
    logger.info("[face_check] deepface not installed — no embedding backend available")


# ── Result types ───────────────────────────────────────────────────────────────

class RejectReason(str, Enum):
    no_face_reference  = "no_face_reference"   # couldn't extract from reference
    no_face_generated  = "no_face_generated"   # couldn't extract from this image
    low_similarity     = "low_similarity"       # score < threshold
    file_error         = "file_error"           # image could not be read


@dataclass
class CheckedPhoto:
    path:       str
    similarity: float        # 0.0–1.0; -1.0 means "could not compute"
    passed:     bool
    reason:     Optional[RejectReason] = None  # None when passed=True


@dataclass
class FilterResult:
    reference_path: str
    threshold:      float
    passed:         List[CheckedPhoto] = field(default_factory=list)
    rejected:       List[CheckedPhoto] = field(default_factory=list)

    @property
    def all_photos(self) -> List[CheckedPhoto]:
        return self.passed + self.rejected

    @property
    def pass_rate(self) -> float:
        total = len(self.all_photos)
        return round(len(self.passed) / total, 3) if total else 0.0


# ── InsightFace singleton ──────────────────────────────────────────────────────

class _InsightFaceEmbedder:
    """
    Lazy-initialised InsightFace FaceAnalysis wrapper.
    Model is downloaded on first use (~300 MB, buffalo_l).
    Uses GPU if CUDA is available, otherwise CPU.
    """
    _app = None

    @classmethod
    def _load(cls):
        if cls._app is not None:
            return cls._app
        logger.info("[face_check] Loading InsightFace buffalo_l model …")
        app = _FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        app.prepare(ctx_id=0, det_size=(640, 640))
        cls._app = app
        logger.info("[face_check] InsightFace ready")
        return cls._app

    @classmethod
    def get_embedding(cls, image_path: str) -> Optional[np.ndarray]:
        """
        Return the ArcFace embedding (512-d float32) for the largest detected face.
        Returns None if no face is detected or the file cannot be read.
        """
        try:
            img = _cv2_if.imread(image_path)
            if img is None:
                logger.warning("[insightface] Cannot read image: %s", image_path)
                return None

            app   = cls._load()
            faces = app.get(img)

            if not faces:
                logger.debug("[insightface] No face detected in %s", image_path)
                return None

            # Use the face with the largest bounding-box area
            best = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            emb  = best.embedding.astype(np.float32)
            logger.debug("[insightface] Embedding OK  path=%s  norm=%.3f",
                         Path(image_path).name, float(np.linalg.norm(emb)))
            return emb

        except Exception as exc:
            logger.error("[insightface] Embedding failed for %s: %s", image_path, exc)
            return None


# ── DeepFace fallback embedder ─────────────────────────────────────────────────

def _deepface_embedding(image_path: str) -> Optional[np.ndarray]:
    """Return ArcFace embedding via DeepFace. Returns None on failure."""
    try:
        result = _DeepFace.represent(
            img_path=image_path,
            model_name="ArcFace",
            detector_backend="retinaface",
            enforce_detection=False,
        )
        if not result:
            return None
        # DeepFace returns a list of dicts; take the first (largest) face
        vec = np.array(result[0]["embedding"], dtype=np.float32)
        logger.debug("[deepface] Embedding OK  path=%s  dim=%d",
                     Path(image_path).name, len(vec))
        return vec
    except Exception as exc:
        logger.error("[deepface] Embedding failed for %s: %s", image_path, exc)
        return None


# ── Embedding dispatcher ───────────────────────────────────────────────────────

def _get_embedding(image_path: str) -> Optional[np.ndarray]:
    """Try InsightFace first, then DeepFace."""
    if _INSIGHTFACE:
        emb = _InsightFaceEmbedder.get_embedding(image_path)
        if emb is not None:
            return emb

    if _DEEPFACE:
        return _deepface_embedding(image_path)

    return None


# ── Cosine similarity ──────────────────────────────────────────────────────────

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity between two L2-normalised embedding vectors.
    Returns a value in [-1.0, 1.0]; for face embeddings expect [0.0, 1.0].
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    sim = float(np.dot(a, b) / (norm_a * norm_b))
    return round(float(np.clip(sim, -1.0, 1.0)), 4)


# ── Core filter logic ──────────────────────────────────────────────────────────

def _process_one(
    generated_path: str,
    ref_embedding:  np.ndarray,
    threshold:      float,
    delete_rejected: bool,
) -> CheckedPhoto:
    """Score one generated image and decide pass / reject."""

    if not Path(generated_path).exists():
        return CheckedPhoto(
            path=generated_path,
            similarity=-1.0,
            passed=False,
            reason=RejectReason.file_error,
        )

    gen_embedding = _get_embedding(generated_path)

    if gen_embedding is None:
        logger.info("[face_check] No face  path=%s → rejected", Path(generated_path).name)
        if delete_rejected:
            _safe_delete(generated_path)
        return CheckedPhoto(
            path=generated_path,
            similarity=-1.0,
            passed=False,
            reason=RejectReason.no_face_generated,
        )

    sim    = cosine_similarity(ref_embedding, gen_embedding)
    passed = sim >= threshold

    logger.info(
        "[face_check] %s  sim=%.4f  threshold=%.2f  → %s",
        Path(generated_path).name, sim, threshold, "PASS" if passed else "REJECT",
    )

    if not passed and delete_rejected:
        _safe_delete(generated_path)

    return CheckedPhoto(
        path=generated_path,
        similarity=sim,
        passed=passed,
        reason=None if passed else RejectReason.low_similarity,
    )


def _safe_delete(path: str) -> None:
    try:
        os.remove(path)
        logger.debug("[face_check] Deleted rejected image: %s", path)
    except OSError as exc:
        logger.warning("[face_check] Could not delete %s: %s", path, exc)


# ── Public API ─────────────────────────────────────────────────────────────────

def filter_by_similarity(
    reference_path:  str,
    generated_paths: List[str],
    threshold:       float = THRESHOLD_DEFAULT,
    delete_rejected: bool  = True,
) -> FilterResult:
    """
    Check every generated photo against the reference face.

    Parameters
    ──────────
    reference_path   : path to the best reference upload (from face_selector)
    generated_paths  : list of paths produced by the pipeline
    threshold        : minimum cosine similarity to pass (default 0.35)
    delete_rejected  : if True, rejected files are removed from disk

    Returns
    ───────
    FilterResult with .passed and .rejected lists of CheckedPhoto.
    Each CheckedPhoto has:
        .path        – original file path
        .similarity  – cosine score 0–1 (-1 if embedding failed)
        .passed      – bool
        .reason      – None | RejectReason enum

    Raises
    ──────
    RuntimeError  – if the reference photo has no detectable face
                    (pipeline should abort rather than filter against nothing)
    """
    result = FilterResult(reference_path=reference_path, threshold=threshold)

    if not generated_paths:
        logger.warning("[face_check] No generated paths provided — nothing to filter")
        return result

    # ── Extract reference embedding ────────────────────────────────────────────
    if not _INSIGHTFACE and not _DEEPFACE:
        # No backend available — pass all through with a warning
        logger.warning(
            "[face_check] No embedding backend (insightface / deepface) installed. "
            "Skipping similarity filter — all %d images pass.",
            len(generated_paths),
        )
        result.passed = [
            CheckedPhoto(path=p, similarity=-1.0, passed=True) for p in generated_paths
        ]
        return result

    logger.info("[face_check] Extracting reference embedding: %s", reference_path)
    ref_embedding = _get_embedding(reference_path)

    if ref_embedding is None:
        raise RuntimeError(
            f"Could not extract face embedding from reference photo: {reference_path}. "
            "Ensure the photo contains a clearly visible face."
        )

    # ── Score and filter each generated image ──────────────────────────────────
    logger.info(
        "[face_check] Checking %d images  threshold=%.2f  delete_rejected=%s",
        len(generated_paths), threshold, delete_rejected,
    )

    for path in generated_paths:
        checked = _process_one(path, ref_embedding, threshold, delete_rejected)
        if checked.passed:
            result.passed.append(checked)
        else:
            result.rejected.append(checked)

    logger.info(
        "[face_check] DONE  passed=%d  rejected=%d  pass_rate=%.0f%%",
        len(result.passed), len(result.rejected), result.pass_rate * 100,
    )
    return result


def score_photo(reference_path: str, generated_path: str) -> float:
    """
    Single-image convenience wrapper.
    Returns cosine similarity 0–1, or -1.0 if embedding fails.
    """
    ref_emb = _get_embedding(reference_path)
    gen_emb = _get_embedding(generated_path)

    if ref_emb is None or gen_emb is None:
        return -1.0
    return cosine_similarity(ref_emb, gen_emb)
