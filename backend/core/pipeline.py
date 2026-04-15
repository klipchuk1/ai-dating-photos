"""
Fully synchronous Replicate pipeline.
Designed to be executed inside a worker thread — never called from async code directly.

Flow per style:
  InstantID + SDXL  →  CodeFormer (face restore)  →  Real-ESRGAN (2× upscale)  →  save locally
"""

import base64
import uuid
from pathlib import Path
from typing import Callable, List, Optional

import requests
import replicate

from models.styles import STYLES
from core.storage import user_result_dir

# ── Pinned model versions ──────────────────────────────────────────────────────
_INSTANTID  = "zsxkib/instant-id:491ddf5be6b827f8931f088ef10c6d015f6d99d5"
_CODEFORMER = "sczhou/codeformer:7de2ea26c616d5bf2245ad0d5e24f0ff9a6204578"
_REALESRGAN = "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05faf03a2905d4c5b5b4a4b8b49b"

IMAGES_PER_STYLE = 2

ProgressFn = Optional[Callable[[int], None]]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _b64(path: str) -> str:
    """Encode local file as data URI for Replicate input."""
    ext  = Path(path).suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:image/{mime};base64,{data}"


def _download(url: str, dest: Path) -> str:
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return str(dest)


def _first(output) -> str:
    """Replicate outputs can be a list or a single value."""
    if isinstance(output, (list, tuple)):
        return str(output[0])
    return str(output)


# ── Pipeline steps ─────────────────────────────────────────────────────────────

def _step_instantid(face_b64: str, style: dict) -> List[str]:
    output = replicate.run(
        _INSTANTID,
        input={
            "image":                         face_b64,
            "prompt":                        style["prompt"],
            "negative_prompt":               style["negative_prompt"],
            "ip_adapter_scale":              style["style_strength"],
            "controlnet_conditioning_scale": 0.8,
            "num_inference_steps":           30,
            "guidance_scale":                7.5,
            "num_outputs":                   IMAGES_PER_STYLE,
            "width":                         1024,
            "height":                        1024,
            "enhance_nonface_region":        True,
        },
    )
    return list(output) if isinstance(output, (list, tuple)) else [str(output)]


def _step_codeformer(image_url: str) -> str:
    output = replicate.run(
        _CODEFORMER,
        input={
            "image":               image_url,
            "codeformer_fidelity": 0.7,   # 0 = max enhance, 1 = max fidelity; 0.7 = identity-safe
            "upscale":             1,
            "face_upsample":       True,
            "background_enhance":  False,
        },
    )
    return _first(output)


def _step_realesrgan(image_url: str) -> str:
    output = replicate.run(
        _REALESRGAN,
        input={
            "image":        image_url,
            "scale":        2,
            "face_enhance": False,   # already handled by CodeFormer
        },
    )
    return _first(output)


# ── Public entry point ─────────────────────────────────────────────────────────

def run_pipeline(
    user_id:         str,
    face_image_path: str,
    style_id:        str,
    on_progress:     ProgressFn = None,
) -> List[str]:
    """
    Run the full generation pipeline for one style.
    Returns a list of absolute local file paths to the final images.

    Progress milestones emitted via on_progress(0-100):
        10  – encoding done, InstantID starting
        50  – InstantID done
        55–75 – CodeFormer per image
        76–90 – ESRGAN per image
        91–99 – download per image
    """
    if style_id not in STYLES:
        raise ValueError(f"Unknown style_id: {style_id!r}")

    style      = STYLES[style_id]
    result_dir = user_result_dir(user_id)
    _emit(on_progress, 10)

    # ── Step 1: InstantID + SDXL ───────────────────────────────────────────────
    face_b64  = _b64(face_image_path)
    raw_urls  = _step_instantid(face_b64, style)
    _emit(on_progress, 50)

    saved_paths: List[str] = []
    n = len(raw_urls)

    for i, raw_url in enumerate(raw_urls):
        base_pct = 50 + i * (40 // n)   # spread remaining 40 pts across images

        # ── Step 2: CodeFormer ─────────────────────────────────────────────────
        restored_url = _step_codeformer(raw_url)
        _emit(on_progress, base_pct + (10 // n))

        # ── Step 3: Real-ESRGAN ────────────────────────────────────────────────
        upscaled_url = _step_realesrgan(restored_url)
        _emit(on_progress, base_pct + (20 // n))

        # ── Download ───────────────────────────────────────────────────────────
        dest = result_dir / f"{style_id}_{uuid.uuid4().hex[:8]}_{i}.jpg"
        _download(upscaled_url, dest)
        saved_paths.append(str(dest))
        _emit(on_progress, base_pct + (30 // n))

    return saved_paths


def _emit(fn: ProgressFn, value: int) -> None:
    if fn is not None:
        try:
            fn(value)
        except Exception:
            pass
