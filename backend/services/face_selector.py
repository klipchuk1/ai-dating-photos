"""
Select the best reference face from uploaded photos.
Priority: frontal > high resolution > sharp > well-lit.
Uses OpenCV for basic checks; falls back to first image if CV not available.
"""

import os
from pathlib import Path
from typing import List, Optional

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


def _score_image(path: str) -> float:
    """
    Score a photo as a face reference candidate.
    Higher = better. Returns 0.0 on failure.
    """
    try:
        img = cv2.imread(path)
        if img is None:
            return 0.0

        h, w = img.shape[:2]
        resolution_score = min(h, w) / 1000.0  # prefer >= 1000px short side

        # Sharpness via Laplacian variance
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness_score = min(sharpness / 500.0, 1.0)

        # Face detection with Haar cascade
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        if len(faces) == 0:
            return 0.0
        if len(faces) > 1:
            # Multiple faces — penalize heavily
            return 0.1

        # Face size relative to image — bigger is better
        x, y, fw, fh = faces[0]
        face_ratio = (fw * fh) / (w * h)
        face_score = min(face_ratio * 3, 1.0)

        return (resolution_score * 0.3) + (sharpness_score * 0.4) + (face_score * 0.3)

    except Exception:
        return 0.0


def select_best_face(image_paths: List[str]) -> Optional[str]:
    """
    Return the path of the best face reference photo.
    Falls back to first image if scoring fails entirely.
    """
    if not image_paths:
        return None

    if not CV2_AVAILABLE:
        return image_paths[0]

    scored = [(path, _score_image(path)) for path in image_paths]
    scored.sort(key=lambda x: x[1], reverse=True)

    # If best score is 0 (no faces detected) return first upload
    if scored[0][1] == 0.0:
        return image_paths[0]

    return scored[0][0]
