"""
Pick the best face-reference image from a list of uploads.
Score = resolution × sharpness × face-quality.
Falls back to the first image when OpenCV is unavailable.
"""

from typing import List, Optional

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False


def _score(path: str) -> float:
    try:
        img = cv2.imread(path)
        if img is None:
            return 0.0

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Sharpness: Laplacian variance (higher → sharper)
        sharpness = min(cv2.Laplacian(gray, cv2.CV_64F).var() / 500.0, 1.0)

        # Resolution: normalise on 1000 px short-side
        resolution = min(min(h, w) / 1000.0, 1.0)

        # Face detection
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        if len(faces) == 0:
            return 0.0
        if len(faces) > 1:
            return 0.1  # multiple faces — penalise

        _, _, fw, fh = faces[0]
        face_ratio = min((fw * fh) / (w * h) * 3, 1.0)

        return resolution * 0.3 + sharpness * 0.4 + face_ratio * 0.3

    except Exception:
        return 0.0


def select_best(paths: List[str]) -> Optional[str]:
    if not paths:
        return None
    if not _CV2:
        return paths[0]

    scored = sorted(paths, key=_score, reverse=True)
    return scored[0]
