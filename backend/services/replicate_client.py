"""
Replicate API wrappers for each model in the pipeline.
All calls are async-compatible via asyncio.to_thread.
"""

import asyncio
import base64
import os
from pathlib import Path
from typing import Optional
import httpx
import replicate

# ─── Model versions ────────────────────────────────────────────────────────────
# Pin versions for reproducibility — update when new stable versions release.

INSTANTID_VERSION = "491ddf5be6b827f8931f088ef10c6d015f6d99d5"
# InstantID: face conditioning → outputs conditioned latent fed into SDXL

SDXL_VERSION = "7762fd07cf82c948538e41f63f77d685e02b063e"
# SDXL: base generation guided by InstantID face embedding

CODEFORMER_VERSION = "7de2ea26c616d5bf2245ad0d5e24f0ff9a6204578"
# CodeFormer: face restoration — sharpens identity details post-generation

REALESRGAN_VERSION = "42fed1c4974146d4d2414e2be2c5277c7fcf05faf03a2905d4c5b5b4a4b8b49b"
# Real-ESRGAN: 2x / 4x upscale preserving texture


async def _run_async(model_id: str, **inputs) -> list:
    """Run a Replicate model, return list of output URLs."""
    output = await asyncio.to_thread(
        replicate.run, model_id, input=inputs
    )
    if isinstance(output, list):
        return output
    return [output]


def _encode_image_b64(path: str) -> str:
    """Encode local image to base64 data URI."""
    suffix = Path(path).suffix.lower().lstrip(".")
    mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{data}"


async def run_instantid_sdxl(
    face_image_path: str,
    prompt: str,
    negative_prompt: str,
    style_strength: float = 0.75,
    num_outputs: int = 2,
) -> list[str]:
    """
    InstantID + SDXL combined: generate images with preserved face identity.
    Returns list of output image URLs.
    """
    face_b64 = _encode_image_b64(face_image_path)

    return await _run_async(
        f"zsxkib/instant-id:{INSTANTID_VERSION}",
        image=face_b64,
        prompt=prompt,
        negative_prompt=negative_prompt,
        ip_adapter_scale=style_strength,        # controls identity vs style balance
        controlnet_conditioning_scale=0.8,       # face structure adherence
        num_inference_steps=30,
        guidance_scale=7.5,
        num_outputs=num_outputs,
        width=1024,
        height=1024,
        scheduler="EulerDiscreteScheduler",
        enhance_nonface_region=True,            # keeps non-face areas natural
    )


async def run_codeformer(image_url: str, fidelity: float = 0.7) -> str:
    """
    CodeFormer face restoration.
    fidelity: 0.0 = max enhancement, 1.0 = max fidelity to input.
    0.7 = good balance: restores detail without drifting from identity.
    """
    outputs = await _run_async(
        f"sczhou/codeformer:{CODEFORMER_VERSION}",
        image=image_url,
        codeformer_fidelity=fidelity,
        upscale=1,              # we upscale separately with ESRGAN
        face_upsample=True,
        background_enhance=False,
    )
    return outputs[0] if outputs else image_url


async def run_realesrgan(image_url: str, scale: int = 2) -> str:
    """
    Real-ESRGAN upscale. scale=2 for fast, scale=4 for max quality.
    """
    outputs = await _run_async(
        f"nightmareai/real-esrgan:{REALESRGAN_VERSION}",
        image=image_url,
        scale=scale,
        face_enhance=False,     # already done by CodeFormer
    )
    return outputs[0] if outputs else image_url


async def download_image(url: str, dest_path: str) -> str:
    """Download image from URL to local path, return path."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    with open(dest_path, "wb") as f:
        f.write(resp.content)
    return dest_path
