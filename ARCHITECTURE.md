# AI Dating Photos — Architecture

## Directory Structure

```
ai-dating-photos/
├── backend/
│   ├── main.py                    # FastAPI app, CORS, static mounts
│   ├── api/routes/
│   │   ├── upload.py              # POST /api/upload
│   │   ├── generate.py            # POST /api/generate, GET /api/generate/status/{job_id}
│   │   ├── styles.py              # GET /api/styles
│   │   └── gallery.py             # GET /api/gallery/{session_id}
│   ├── services/
│   │   ├── replicate_client.py    # Replicate wrappers (InstantID, CodeFormer, ESRGAN)
│   │   ├── pipeline.py            # Orchestrates per-style generation
│   │   ├── face_selector.py       # Picks best face reference from uploads
│   │   └── storage.py             # File I/O helpers
│   ├── workers/
│   │   └── job_queue.py           # Async in-memory job queue
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── styles.py              # 8 style definitions with prompts
│   └── storage/
│       ├── uploads/{session_id}/  # Raw user photos
│       └── results/{session_id}/  # Generated images
│
└── frontend/
    └── src/
        ├── pages/
        │   ├── UploadPage.tsx     # Step 1: drag & drop upload
        │   ├── StylesPage.tsx     # Step 2: Tinder swipe style select
        │   ├── GeneratingPage.tsx # Step 3: progress + tips
        │   └── GalleryPage.tsx    # Step 4: results grid + download
        ├── components/
        │   ├── UploadZone.tsx     # Dropzone with preview grid
        │   ├── StyleSwipe.tsx     # Swipe card stack (framer-motion)
        │   ├── Gallery.tsx        # Image grid + lightbox
        │   └── ProgressBar.tsx    # Animated progress bar
        ├── hooks/
        │   └── useJobPoller.ts    # Polls /generate/status every 3s
        └── lib/
            └── api.ts             # Axios API client
```

## Generation Pipeline

```
User uploads 5-10 photos
        ↓
face_selector.py — OpenCV scores each photo
  - Resolution (short side ≥ 1000px preferred)
  - Sharpness (Laplacian variance)
  - Face detection (Haar cascade, 1 face preferred)
        ↓
Best face reference selected
        ↓
For each selected style (sequential, avoid rate limits):
  ┌─────────────────────────────────────────────┐
  │  1. InstantID + SDXL                        │
  │     - ip_adapter_scale = style_strength     │
  │     - controlnet_conditioning_scale = 0.8   │
  │     - 2 outputs per style                   │
  │     → Raw generated images (1024×1024)      │
  │                                             │
  │  2. CodeFormer (parallel per image)         │
  │     - fidelity = 0.7 (identity priority)    │
  │     → Face-restored images                  │
  │                                             │
  │  3. Real-ESRGAN (parallel per image)        │
  │     - scale = 2x                            │
  │     → Final 2048×2048 images                │
  └─────────────────────────────────────────────┘
        ↓
Saved to storage/results/{session_id}/
        ↓
Gallery served via /results/{session_id}/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/upload` | Upload 3-10 photos, returns `session_id` |
| GET | `/api/styles` | List all available styles |
| POST | `/api/generate` | Start generation job, returns `job_id` |
| GET | `/api/generate/status/{job_id}` | Poll job progress |
| GET | `/api/gallery/{session_id}` | Get result image URLs |
| GET | `/api/health` | Health check |

## Identity Preservation Strategy

1. **InstantID** — embeds face into CLIP space via IP-Adapter
   - `ip_adapter_scale` < 1.0: style influence allowed, identity preserved
   - `controlnet_conditioning_scale = 0.8`: structure adherence
   - `enhance_nonface_region = True`: naturalness outside face

2. **Prompts** — describe only environment/lighting, never facial features
   - No "brown eyes", "sharp jawline" etc. — those come from InstantID
   - Negative prompts explicitly block deformed/cartoon faces

3. **CodeFormer fidelity = 0.7** — closer to 1.0 = more original identity kept
   - 0.5-0.6 = better quality but may drift; 0.7 = safe default

4. **No face in negative prompt** — avoid fighting InstantID conditioning

## Scaling Path

| Now (MVP) | Production |
|-----------|------------|
| asyncio in-memory queue | Celery + Redis |
| Local file storage | S3 / GCS |
| No auth | Session tokens / OAuth |
| Sequential styles | Parallel with rate limit handling |
| 1 server | Horizontal scaling behind load balancer |
