from __future__ import annotations

import uuid
from typing import Iterable, TypedDict

from app.models.schemas import BubbleItem, ChapterPayload, PagePayload, WordTime
from app.services.pipeline import chapter_store

DEMO_AUDIO_DATA_URL = (
    "data:audio/wav;base64,"
    "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"
)


class ChapterFile(TypedDict):
    filename: str
    image_url: str


def enqueue_chapter_job(chapter_id: str, files: Iterable[ChapterFile]) -> str:
    job = chapter_store.create_job()
    chapter_store.update_job(job.job_id, status="processing", chapter_id=chapter_id, progress=10)
    simulate_processing(chapter_id, list(files))
    chapter_store.update_job(job.job_id, status="ready", progress=100)
    return job.job_id


def simulate_processing(chapter_id: str, files: list[ChapterFile]) -> None:
    if not files:
        files = [{"filename": "placeholder.png", "image_url": ""}]

    pages: list[PagePayload] = []
    for index, file_info in enumerate(files):
        bubble_id = f"bubble_{index}_1"
        words = ["Hello", "from", "Inkami"]
        word_times = [
            WordTime(word=w, start=i * 0.4, end=(i + 1) * 0.4) for i, w in enumerate(words)
        ]
        bubble = BubbleItem(
            bubble_id=bubble_id,
            panel_box=[0, 0, 1080, 1920],
            bubble_box=[120, 240, 420, 420],
            type="dialogue",
            speaker_id="char_default",
            speaker_name="Placeholder",
            voice_id="voice_friendly_f",
            text=" ".join(words),
            audio_url=DEMO_AUDIO_DATA_URL,
            word_times=word_times,
        )
        image_url = file_info.get("image_url") or ""
        page = PagePayload(
            page_index=index,
            image_url=image_url,
            items=[bubble],
            reading_order=[bubble_id],
        )
        pages.append(page)

    chapter = ChapterPayload(
        chapter_id=chapter_id,
        title=f"Chapter {chapter_id[:8]}",
        status="ready",
        progress=100,
        pages=pages,
    )
    chapter_store.save_chapter(chapter)

