"""
services/pipeline.py
--------------------
Full generation pipeline: best-face selection → InstantID → SDXL → CodeFormer → Real-ESRGAN.

Design decisions
────────────────
• Fully synchronous — designed to run inside a worker thread (see core/worker.py).
• InstantID is called in batches of batch_size (4–8).  Because the Replicate model
  caps num_outputs at 4, any batch_size > 4 is split into sub-batches of 4 automatically.
• CodeFormer and Real-ESRGAN process one image at a time (APIs don't support multi-image
  input), but run sequentially inside their own retry loops.
• Every Replicate call is wrapped in _call_with_retry():  exponential back-off, full
  exception logging, configurable max_retries.
• Progress is reported via a callback(int 0–100) so the caller can update job state
  without touching pipeline internals.

Progress milestones
───────────────────
  5   – face selected, encoding done
  5→50 – InstantID batches (evenly distributed)
  50→75 – CodeFormer pass   (per image)
  75→90 – Real-ESRGAN pass  (per image)
  90→99 – download to disk  (per image)
  100  – done (set by caller after all phases)
"""

import base64
import logging
import math
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

import requests
import replicate

from core.face_selector import select_best
from core.storage import list_uploads, user_result_dir
from services.styles import get_prompt
from services.face_check import filter_by_similarity, THRESHOLD_DEFAULT

logger = logging.getLogger(__name__)


# ── Pinned Replicate model versions ───────────────────────────────────────────
# Update these when new stable checkpoints are released.
_MODEL_INSTANTID  = "zsxkib/instant-id:2e4785a4d80dadf580077b2244c8d7c05d8e3faac04a04c02d8e099dd2876789"
_MODEL_CODEFORMER = "sczhou/codeformer:cc4956dd26fa5a7185d5660cc9100fab1b8070a1d1654a8bb5eb6d443b020bb2"
_MODEL_REALESRGAN = "nightmareai/real-esrgan:b3ef194191d13140337468c916c2c5b96dd0cb06dffc032a022a31807f6a5ea8"

# InstantID hard cap on num_outputs per single call
_INSTANTID_MAX_OUTPUTS = 4


# ── Pipeline configuration ─────────────────────────────────────────────────────

@dataclass
class PipelineConfig:
    """
    All tunable generation parameters.  Defaults are the recommended starting point.
    Pass a custom instance to run_pipeline() to override.
    """
    # Generation volume
    total_images: int   = 20      # 20–40 final images requested
    batch_size:   int   = 4       # images per InstantID call (4–8; capped at 4 by model)

    # Diffusion quality
    guidance_scale: float = 6.0   # 5–7  (lower = more creative, higher = more prompt-adherent)
    num_steps:      int   = 30    # 25–35 (more steps = higher quality, slower)

    # Resolution
    width:  int = 1024
    height: int = 1024

    # InstantID identity control
    ip_adapter_scale:              float = 0.75  # identity strength (lower = looser style)
    controlnet_conditioning_scale: float = 0.80  # face structure adherence
    enhance_nonface_region:        bool  = True

    # CodeFormer
    codeformer_fidelity: float = 0.70  # 0 = max enhance / 1 = max fidelity; 0.7 = identity-safe
    codeformer_upscale:  int   = 1     # upscale handled separately by ESRGAN

    # Real-ESRGAN
    esrgan_scale: int = 2   # 2× faster; use 4 for maximum quality

    # Retry
    max_retries:    int   = 3
    retry_base_sec: float = 2.0   # back-off multiplier: 2^attempt × base

    # Face similarity filter (step 6)
    # Set to None to disable filtering entirely
    face_check_threshold: Optional[float] = THRESHOLD_DEFAULT


# ── Progress callback type ─────────────────────────────────────────────────────

ProgressFn = Optional[Callable[[int], None]]


# ── Internal helpers ───────────────────────────────────────────────────────────

def _emit(fn: ProgressFn, value: int) -> None:
    """Fire progress callback; silently swallow any exceptions in the callback."""
    if fn is not None:
        try:
            fn(max(0, min(100, value)))
        except Exception:
            pass


def _encode_b64(path: str) -> str:
    """Encode a local image file as a base64 data URI."""
    ext  = Path(path).suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return f"data:image/{mime};base64,{data}"


def _download(url: str, dest: Path) -> str:
    """Download a URL to dest; returns the local path as str."""
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    logger.debug("Downloaded %s → %s", url, dest)
    return str(dest)


def _to_list(output) -> List[str]:
    """Normalise Replicate output to a plain list of URL strings."""
    if isinstance(output, (list, tuple)):
        return [str(u) for u in output]
    return [str(output)]


# ── Retry wrapper ──────────────────────────────────────────────────────────────

def _call_with_retry(
    label: str,
    fn: Callable,
    max_retries: int,
    base_sec: float,
) -> any:
    """
    Call fn(); on failure sleep and retry up to max_retries times.
    Raises the last exception if all attempts fail.

    Back-off schedule (base_sec=2): 2s, 4s, 8s, …
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            t0     = time.monotonic()
            result = fn()
            elapsed = time.monotonic() - t0
            logger.info("[%s] OK  attempt=%d  elapsed=%.1fs", label, attempt, elapsed)
            return result

        except Exception as exc:
            last_exc = exc
            wait = base_sec ** (attempt - 1)
            logger.warning(
                "[%s] FAIL attempt=%d/%d  error=%s  retrying in %.0fs",
                label, attempt, max_retries, exc, wait,
            )
            if attempt < max_retries:
                time.sleep(wait)

    logger.error("[%s] EXHAUSTED after %d attempts: %s", label, max_retries, last_exc)
    raise last_exc


# ── Step 1: face reference selection ──────────────────────────────────────────

def _select_face(user_id: str) -> str:
    """
    Load all uploads for user_id, score them with OpenCV, return the best path.
    Raises RuntimeError if no uploads are found.
    """
    uploads = list_uploads(user_id)
    if not uploads:
        raise RuntimeError(f"No uploaded photos found for user_id='{user_id}'")

    best = select_best(uploads)
    if not best:
        raise RuntimeError("Face selection returned no candidate")

    logger.info("[face] Selected reference: %s  (from %d uploads)", best, len(uploads))
    return best


# ── Step 2: InstantID + SDXL (batched) ────────────────────────────────────────

def _run_instantid_batch(
    face_b64: str,
    prompt: str,
    negative_prompt: str,
    num_outputs: int,
    cfg: PipelineConfig,
    batch_label: str,
) -> List[str]:
    """
    One InstantID call for num_outputs images.
    num_outputs is capped at _INSTANTID_MAX_OUTPUTS by the caller.
    """
    def _call():
        return replicate.run(
            _MODEL_INSTANTID,
            input={
                "image":                         face_b64,
                "prompt":                        prompt,
                "negative_prompt":               negative_prompt,
                "ip_adapter_scale":              cfg.ip_adapter_scale,
                "controlnet_conditioning_scale": cfg.controlnet_conditioning_scale,
                "num_inference_steps":           cfg.num_steps,
                "guidance_scale":                cfg.guidance_scale,
                "num_outputs":                   num_outputs,
                "width":                         cfg.width,
                "height":                        cfg.height,
                "enhance_nonface_region":        cfg.enhance_nonface_region,
            },
        )

    output = _call_with_retry(batch_label, _call, cfg.max_retries, cfg.retry_base_sec)
    urls   = _to_list(output)
    logger.info("[instantid] %s  got %d URL(s)", batch_label, len(urls))
    return urls


def _run_all_batches(
    face_b64: str,
    prompt: str,
    negative_prompt: str,
    cfg: PipelineConfig,
    on_progress: ProgressFn,
) -> List[str]:
    """
    Split total_images into batches and call InstantID repeatedly.
    Progress window: 5 → 50.
    """
    effective_batch = min(cfg.batch_size, _INSTANTID_MAX_OUTPUTS)
    n_batches       = math.ceil(cfg.total_images / effective_batch)
    remaining       = cfg.total_images
    all_urls:  List[str] = []

    logger.info(
        "[instantid] target=%d images  batch_size=%d  n_batches=%d  "
        "guidance=%.1f  steps=%d",
        cfg.total_images, effective_batch, n_batches,
        cfg.guidance_scale, cfg.num_steps,
    )

    for batch_idx in range(n_batches):
        this_batch = min(effective_batch, remaining)
        label      = f"instantid batch {batch_idx + 1}/{n_batches}"

        urls = _run_instantid_batch(
            face_b64, prompt, negative_prompt,
            this_batch, cfg, label,
        )
        all_urls.extend(urls)
        remaining -= this_batch

        # Progress 5 → 50 spread evenly across batches
        progress = 5 + int((batch_idx + 1) / n_batches * 45)
        _emit(on_progress, progress)

    logger.info("[instantid] DONE  total raw URLs: %d", len(all_urls))
    return all_urls


# ── Step 3: CodeFormer ─────────────────────────────────────────────────────────

def _run_codeformer(image_url: str, cfg: PipelineConfig, label: str) -> str:
    def _call():
        return replicate.run(
            _MODEL_CODEFORMER,
            input={
                "image":               image_url,
                "codeformer_fidelity": cfg.codeformer_fidelity,
                "upscale":             cfg.codeformer_upscale,
                "face_upsample":       True,
                "background_enhance":  False,
            },
        )

    output = _call_with_retry(label, _call, cfg.max_retries, cfg.retry_base_sec)
    url    = _to_list(output)[0]
    logger.debug("[codeformer] %s → %s", label, url)
    return url


# ── Step 4: Real-ESRGAN ────────────────────────────────────────────────────────

def _run_realesrgan(image_url: str, cfg: PipelineConfig, label: str) -> str:
    def _call():
        return replicate.run(
            _MODEL_REALESRGAN,
            input={
                "image":        image_url,
                "scale":        cfg.esrgan_scale,
                "face_enhance": False,   # already done by CodeFormer
            },
        )

    output = _call_with_retry(label, _call, cfg.max_retries, cfg.retry_base_sec)
    url    = _to_list(output)[0]
    logger.debug("[realesrgan] %s → %s", label, url)
    return url


# ── Step 5: post-process all raw images ───────────────────────────────────────

def _post_process(
    raw_urls:   List[str],
    user_id:    str,
    style_id:   str,
    cfg:        PipelineConfig,
    on_progress: ProgressFn,
) -> List[str]:
    """
    For each raw URL: CodeFormer → ESRGAN → download.
    Progress windows:
        CodeFormer : 50 → 75
        ESRGAN     : 75 → 90
        Download   : 90 → 99
    """
    result_dir  = user_result_dir(user_id)
    n           = len(raw_urls)
    saved_paths: List[str] = []

    logger.info("[post-process] %d images  codeformer_fidelity=%.2f  esrgan_scale=%dx",
                n, cfg.codeformer_fidelity, cfg.esrgan_scale)

    for i, raw_url in enumerate(raw_urls):
        img_label = f"img {i + 1}/{n}"

        # ── CodeFormer ──────────────────────────────────────────────────────────
        restored_url = _run_codeformer(raw_url, cfg, f"codeformer {img_label}")
        _emit(on_progress, 50 + int((i + 1) / n * 25))   # 50 → 75

        # ── Real-ESRGAN ─────────────────────────────────────────────────────────
        upscaled_url = _run_realesrgan(restored_url, cfg, f"realesrgan {img_label}")
        _emit(on_progress, 75 + int((i + 1) / n * 15))   # 75 → 90

        # ── Download ────────────────────────────────────────────────────────────
        dest = result_dir / f"{style_id}_{uuid.uuid4().hex[:8]}_{i:02d}.jpg"
        try:
            _download(upscaled_url, dest)
            saved_paths.append(str(dest))
        except Exception as exc:
            logger.error("[download] %s FAILED: %s — skipping", img_label, exc)

        _emit(on_progress, 90 + int((i + 1) / n * 9))    # 90 → 99

    logger.info("[post-process] DONE  saved=%d/%d", len(saved_paths), n)
    return saved_paths


# ── Public entry point ─────────────────────────────────────────────────────────

def run_pipeline(
    user_id:     str,
    style_id:    str,
    cfg:         PipelineConfig   = None,
    on_progress: ProgressFn       = None,
) -> List[str]:
    """
    Execute the full generation pipeline for one user + style.

    Steps
    ─────
    1. Select best reference face from user's uploads.
    2. InstantID + SDXL: generate cfg.total_images raw images in batches.
    3. CodeFormer: restore / sharpen face on every image.
    4. Real-ESRGAN: upscale every image by cfg.esrgan_scale.
    5. Download all final images to storage/results/{user_id}/.

    Parameters
    ──────────
    user_id     : user session identifier (from POST /upload)
    style_id    : one of the IDs from services/styles.py
    cfg         : PipelineConfig (uses defaults if None)
    on_progress : optional callback(int 0–100) for real-time progress updates

    Returns
    ───────
    List of absolute local file paths to the saved final images.

    Raises
    ──────
    RuntimeError  – no uploads found, no face detected
    ValueError    – unknown style_id
    Exception     – propagated from Replicate after all retries exhausted
    """
    if cfg is None:
        cfg = PipelineConfig()

    # Validate inputs
    try:
        prompt, negative_prompt = get_prompt(style_id)
    except KeyError:
        raise ValueError(f"Unknown style_id: {style_id!r}")

    logger.info(
        "[pipeline] START  user=%s  style=%s  total_images=%d  "
        "batch=%d  steps=%d  guidance=%.1f",
        user_id, style_id, cfg.total_images,
        cfg.batch_size, cfg.num_steps, cfg.guidance_scale,
    )
    t_start = time.monotonic()

    # ── Phase 1: face reference ────────────────────────────────────────────────
    face_path = _select_face(user_id)
    face_b64  = _encode_b64(face_path)
    _emit(on_progress, 5)

    # ── Phase 2: InstantID + SDXL batches ─────────────────────────────────────
    raw_urls = _run_all_batches(
        face_b64, prompt, negative_prompt, cfg, on_progress
    )

    if not raw_urls:
        raise RuntimeError("InstantID returned no images after all retries")

    # ── Phases 3–5: CodeFormer → ESRGAN → download ────────────────────────────
    saved_paths = _post_process(raw_urls, user_id, style_id, cfg, on_progress)

    # ── Phase 6: face similarity filter ───────────────────────────────────────
    if cfg.face_check_threshold is not None and saved_paths:
        logger.info(
            "[pipeline] Running face_check  images=%d  threshold=%.2f",
            len(saved_paths), cfg.face_check_threshold,
        )
        _emit(on_progress, 96)
        try:
            filter_result = filter_by_similarity(
                reference_path=face_path,
                generated_paths=saved_paths,
                threshold=cfg.face_check_threshold,
                delete_rejected=True,
            )
            saved_paths = [p.path for p in filter_result.passed]
            logger.info(
                "[pipeline] face_check  passed=%d  rejected=%d  pass_rate=%.0f%%",
                len(filter_result.passed),
                len(filter_result.rejected),
                filter_result.pass_rate * 100,
            )
        except RuntimeError as exc:
            # Reference face not detectable — skip filter, keep all images
            logger.warning("[pipeline] face_check skipped: %s", exc)
        _emit(on_progress, 99)

    elapsed = time.monotonic() - t_start
    logger.info(
        "[pipeline] DONE  user=%s  style=%s  images=%d  elapsed=%.1fs",
        user_id, style_id, len(saved_paths), elapsed,
    )

    return saved_paths
