from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import bubbles, chapters, jobs
from app.core.config import settings

app = FastAPI(title="Inkami API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(chapters.router, prefix="/api/chapters", tags=["chapters"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(bubbles.router, prefix="/api/bubbles", tags=["bubbles"])

