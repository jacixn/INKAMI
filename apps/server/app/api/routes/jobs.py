from fastapi import APIRouter, HTTPException

from app.models.schemas import JobStatus
from app.services.pipeline import chapter_store

router = APIRouter()


@router.get("/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    job = chapter_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

