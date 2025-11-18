from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import bubbles, chapters, jobs, speakers
from app.core.config import settings

app = FastAPI(title="Inkami API", version="0.1.0")

frontend_url = settings.frontend_url.rstrip("/")
parsed = urlparse(frontend_url)
origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else frontend_url
allow_origins = {frontend_url, origin}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allow_origins),
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


app.include_router(chapters.router, prefix="/api/chapters", tags=["chapters"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(bubbles.router, prefix="/api/bubbles", tags=["bubbles"])
app.include_router(speakers.router, prefix="/api/speakers", tags=["speakers"])

