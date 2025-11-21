from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import bubbles, chapters, jobs, speakers
from app.core.config import settings

app = FastAPI(title="Inkami API", version="0.1.0")

def _add_origin_variants(raw: str, bucket: set[str]) -> None:
    cleaned = raw.strip().rstrip("/")
    if not cleaned:
        return
    bucket.add(cleaned)
    parsed = urlparse(cleaned)
    if parsed.scheme and parsed.netloc:
        bucket.add(f"{parsed.scheme}://{parsed.netloc}")


allow_origins: set[str] = set()
_add_origin_variants(settings.frontend_url, allow_origins)

default_dev_origins = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "http://localhost:5173",
}
for origin in default_dev_origins:
    _add_origin_variants(origin, allow_origins)

extra_origins = [
    origin
    for origin in (settings.extra_cors_origins or "").split(",")
    if origin.strip()
]
for origin in extra_origins:
    _add_origin_variants(origin, allow_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allow_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

uploads_path = Path(settings.upload_dir)
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

static_path = Path(__file__).resolve().parent / "static"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/voices", tags=["meta"])
async def get_voices() -> dict[str, str]:
    """Get available voice IDs and their display names."""
    from app.services.tts import tts_service
    return tts_service.VOICE_DISPLAY_NAMES


app.include_router(chapters.router, prefix="/api/chapters", tags=["chapters"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(bubbles.router, prefix="/api/bubbles", tags=["bubbles"])
app.include_router(speakers.router, prefix="/api/speakers", tags=["speakers"])

