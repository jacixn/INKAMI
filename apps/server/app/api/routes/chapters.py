from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status

from app.core.config import settings
from app.models.schemas import ChapterPayload
from app.services.pipeline import chapter_store
from app.workers.tasks import enqueue_chapter_job

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_chapter(
    request: Request,
    files: Annotated[list[UploadFile], File(..., description="Chapter archive/pages")],
) -> dict[str, str]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    chapter_id = str(uuid.uuid4())
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[dict[str, str]] = []
    base_url = str(request.base_url).rstrip("/")
    for index, file in enumerate(files):
        content = await file.read()
        if not content:
            continue
        suffix = Path(file.filename or f"page_{index}.png").suffix or ".png"
        storage_name = f"{chapter_id}_{index}{suffix}"
        file_path = upload_dir / storage_name
        file_path.write_bytes(content)
        public_url = f"{base_url}/uploads/{storage_name}"
        saved_files.append({"filename": storage_name, "image_url": public_url})

    if not saved_files:
        placeholder = f"{base_url}/static/placeholder-page.png"
        saved_files.append({"filename": "placeholder-page.png", "image_url": placeholder})

    job_id = enqueue_chapter_job(chapter_id, saved_files)

    return {"chapter_id": chapter_id, "job_id": job_id}


@router.get("/{chapter_id}", response_model=ChapterPayload)
async def get_chapter(chapter_id: str) -> ChapterPayload:
    chapter = chapter_store.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter

