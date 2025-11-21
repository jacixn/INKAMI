from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
import os
from io import BytesIO
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse, urlunparse
import zipfile

import fitz
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.models.schemas import ChapterPayload
from app.services.pipeline import chapter_store
from app.workers.tasks import enqueue_chapter_job

router = APIRouter()

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
ARCHIVE_EXTENSIONS = {".zip", ".cbz"}
PDF_EXTENSIONS = {".pdf"}


def _get_image_size(content: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(BytesIO(content)) as img:
            return img.size
    except UnidentifiedImageError:
        return None, None


def _persist_image_bytes(
    chapter_id: str,
    index: int,
    suffix: str,
    content: bytes,
    upload_dir: Path,
    base_url: str,
) -> dict[str, str | int | None] | None:
    width, height = _get_image_size(content)
    if width is None or height is None:
        return None

    safe_suffix = suffix if suffix in IMAGE_EXTENSIONS else ".png"
    filename = f"{chapter_id}_{index:04d}{safe_suffix}"
    file_path = upload_dir / filename
    file_path.write_bytes(content)

    return {
        "filename": filename,
        "image_url": f"{base_url}/uploads/{filename}",
        "width": width,
        "height": height,
        "path": str(file_path),
    }


def _extract_archive_images(
    chapter_id: str,
    start_index: int,
    content: bytes,
    upload_dir: Path,
    base_url: str,
) -> list[dict[str, str | int | None]]:
    extracted: list[dict[str, str | int | None]] = []
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            members = sorted(
                (name for name in archive.namelist() if not name.endswith("/")),
                key=str.lower,
            )
            for member in members:
                suffix = Path(member).suffix.lower()
                if suffix not in IMAGE_EXTENSIONS:
                    continue
                data = archive.read(member)
                saved = _persist_image_bytes(
                    chapter_id,
                    start_index + len(extracted),
                    suffix,
                    data,
                    upload_dir,
                    base_url,
                )
                if saved:
                    extracted.append(saved)
    except zipfile.BadZipFile as exc:  # pragma: no cover - user input error
        raise HTTPException(status_code=400, detail="Invalid archive uploaded.") from exc

    return extracted


def _effective_dpi_for_page(page: fitz.Page, base_dpi: int) -> int:
    height_points = page.rect.height
    # Very tall scroll pages become huge bitmaps at 220 DPI.
    if height_points >= 1200:  # ~16.5 inches
        return max(160, base_dpi - 40)
    if height_points >= 900:
        return max(170, base_dpi - 20)
    return base_dpi


def _render_pdf_page(content: bytes, page_number: int, base_dpi: int) -> bytes:
    with fitz.open(stream=content, filetype="pdf") as document:
        page = document.load_page(page_number)
        dpi = _effective_dpi_for_page(page, base_dpi)
        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
        return pix.tobytes("png")


def _extract_pdf_images(
    chapter_id: str,
    start_index: int,
    content: bytes,
    upload_dir: Path,
    base_url: str,
    base_dpi: int = 210,
) -> list[dict[str, str | int | None]]:
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            page_count = document.page_count
    except fitz.FileDataError as exc:  # pragma: no cover - user input error
        raise HTTPException(status_code=400, detail="Invalid PDF uploaded.") from exc

    extracted: list[dict[str, str | int | None]] = []
    results: list[tuple[int, bytes]] = []
    cpu_count = os.cpu_count() or 4
    max_workers = max(2, min(8, cpu_count, page_count))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_render_pdf_page, content, page_number, base_dpi)
            for page_number in range(page_count)
        ]
        for page_number, future in enumerate(futures):
            try:
                image_bytes = future.result()
            except Exception as exc:  # pragma: no cover - safety
                raise HTTPException(
                    status_code=500, detail=f"Failed to render PDF page {page_number + 1}: {exc}"
                ) from exc
            results.append((page_number, image_bytes))

    results.sort(key=lambda item: item[0])
    for offset, (_, image_bytes) in enumerate(results):
        saved = _persist_image_bytes(
            chapter_id,
            start_index + offset,
            ".png",
            image_bytes,
            upload_dir,
            base_url,
        )
        if saved:
            extracted.append(saved)

    return extracted


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_chapter(
    request: Request,
    files: Annotated[list[UploadFile], File(..., description="Chapter archive/pages")],
    processing_mode: str = Form("bring_to_life"),
    narrator_gender: str = Form("female"),
) -> dict[str, str]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    chapter_id = str(uuid.uuid4())
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_files: list[dict[str, str | int | None]] = []
    base_url = str(request.base_url).rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme == "http":
        base_url = urlunparse(parsed._replace(scheme="https"))

    page_index = 0
    for index, file in enumerate(files):
        content = await file.read()
        if not content:
            continue
        suffix = Path(file.filename or f"page_{index}.png").suffix.lower() or ".png"

        if suffix in ARCHIVE_EXTENSIONS:
            extracted = _extract_archive_images(
                chapter_id,
                page_index,
                content,
                upload_dir,
                base_url,
            )
            saved_files.extend(extracted)
            page_index += len(extracted)
            continue

        if suffix in PDF_EXTENSIONS:
            extracted = _extract_pdf_images(
                chapter_id,
                page_index,
                content,
                upload_dir,
                base_url,
            )
            saved_files.extend(extracted)
            page_index += len(extracted)
            continue

        saved = _persist_image_bytes(
            chapter_id,
            page_index,
            suffix,
            content,
            upload_dir,
            base_url,
        )
        if saved:
            saved_files.append(saved)
            page_index += 1

    if not saved_files:
        placeholder = f"{base_url}/static/placeholder-page.png"
        placeholder_path = Path(__file__).resolve().parent.parent / "static" / "placeholder-page.png"
        saved_files.append(
            {
                "filename": "placeholder-page.png",
                "image_url": placeholder,
                "width": 1080,
                "height": 1920,
                "path": str(placeholder_path),
            }
        )

    mode = (processing_mode or "bring_to_life").strip().lower()
    if mode not in {"bring_to_life", "narrate"}:
        raise HTTPException(status_code=400, detail="Invalid processing mode.")

    gender = (narrator_gender or "female").strip().lower()
    job_id = enqueue_chapter_job(chapter_id, saved_files, mode, gender)  # type: ignore[arg-type]

    return {"chapter_id": chapter_id, "job_id": job_id}


@router.get("/{chapter_id}", response_model=ChapterPayload)
async def get_chapter(chapter_id: str) -> ChapterPayload:
    chapter = chapter_store.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter

