"""
Face similarity scoring between a reference photo and a generated image.

Primary:  DeepFace + ArcFace (cosine distance → 0–1 score)
Fallback: OpenCV histogram correlation (when DeepFace is not installed)
Final:    Returns 0.0 on any failure — never crashes the pipeline.

Score semantics
---------------
1.0  = faces are virtually identical
0.8+ = high similarity (good generation)
0.5–0.8 = moderate
< 0.5 = low similarity (face may have drifted)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── DeepFace (primary) ─────────────────────────────────────────────────────────
try:
    from deepface import DeepFace as _DF
    _DEEPFACE = True
except ImportError:
    _DEEPFACE = False

# ── OpenCV (fallback) ──────────────────────────────────────────────────────────
try:
    import cv2 as _cv2
    import numpy as _np
    _CV2 = True
except ImportError:
    _CV2 = False


# ── ArcFace cosine threshold (per DeepFace docs) ───────────────────────────────
_ARCFACE_THRESHOLD = 0.68


def compute_similarity(reference_path: str, generated_path: str) -> float:
    """
    Return face similarity score in [0.0, 1.0].
    Tries DeepFace first, falls back to histogram correlation.
    """
    if _DEEPFACE:
        score = _deepface_score(reference_path, generated_path)
        if score >= 0.0:
            return score

    if _CV2:
        return _histogram_score(reference_path, generated_path)

    return 0.0


# ── DeepFace scorer ────────────────────────────────────────────────────────────

def _deepface_score(ref: str, gen: str) -> float:
    try:
        result = _DF.verify(
            img1_path=ref,
            img2_path=gen,
            model_name="ArcFace",
            detector_backend="retinaface",
            distance_metric="cosine",
            enforce_detection=False,   # don't crash if face not found
        )
        distance = float(result["distance"])
        # Normalise: distance=0 → score=1.0, distance=threshold → score=0.0
        score = max(0.0, 1.0 - distance / _ARCFACE_THRESHOLD)
        return round(min(1.0, score), 3)
    except Exception as e:
        logger.debug("DeepFace similarity failed: %s", e)
        return -1.0   # signal: try fallback


# ── Histogram fallback ─────────────────────────────────────────────────────────

def _histogram_score(ref: str, gen: str) -> float:
    """
    HSV histogram correlation — fast, no ML required.
    Correlates colour distribution of detected face regions.
    Less precise than ArcFace but never crashes.
    """
    try:
        img1 = _cv2.imread(ref)
        img2 = _cv2.imread(gen)
        if img1 is None or img2 is None:
            return 0.0

        # Crop face region if detectable; otherwise use centre crop
        region1 = _face_crop(img1)
        region2 = _face_crop(img2)

        h1 = _hsv_hist(region1)
        h2 = _hsv_hist(region2)

        # HISTCMP_CORREL → [-1, 1]; shift to [0, 1]
        corr = _cv2.compareHist(h1, h2, _cv2.HISTCMP_CORREL)
        return round(max(0.0, float(corr)), 3)
    except Exception as e:
        logger.debug("Histogram similarity failed: %s", e)
        return 0.0


def _face_crop(img):
    """Return face region from image, or centre 50 % crop as fallback."""
    try:
        gray    = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
        cascade = _cv2.CascadeClassifier(
            _cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(gray, 1.1, 5)
        if len(faces) == 1:
            x, y, w, h = faces[0]
            return img[y:y+h, x:x+w]
    except Exception:
        pass

    # Centre crop fallback
    h, w = img.shape[:2]
    y0, y1 = h // 4, 3 * h // 4
    x0, x1 = w // 4, 3 * w // 4
    return img[y0:y1, x0:x1]


def _hsv_hist(region) -> "_np.ndarray":
    hsv = _cv2.cvtColor(region, _cv2.COLOR_BGR2HSV)
    hist = _cv2.calcHist(
        [hsv], [0, 1], None, [50, 60], [0, 180, 0, 256]
    )
    _cv2.normalize(hist, hist)
    return hist
