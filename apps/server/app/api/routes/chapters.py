from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.models.schemas import ChapterPayload
from app.services.pipeline import chapter_store
from app.workers.tasks import enqueue_chapter_job

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_chapter(
    files: Annotated[list[UploadFile], File(..., description="Chapter archive/pages")],
) -> dict[str, str]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    chapter_id = str(uuid.uuid4())
    filenames = [file.filename or f"page_{idx}.png" for idx, file in enumerate(files)]
    job_id = enqueue_chapter_job(chapter_id, filenames)

    return {"chapter_id": chapter_id, "job_id": job_id}


@router.get("/{chapter_id}", response_model=ChapterPayload)
async def get_chapter(chapter_id: str) -> ChapterPayload:
    chapter = chapter_store.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter

