from __future__ import annotations

import uuid
from typing import Iterable

from app.models.schemas import BubbleItem, ChapterPayload, PagePayload, WordTime
from app.services.pipeline import chapter_store


def enqueue_chapter_job(chapter_id: str, filenames: Iterable[str]) -> str:
    job = chapter_store.create_job()
    chapter_store.update_job(job.job_id, status="processing", chapter_id=chapter_id, progress=10)
    simulate_processing(chapter_id, list(filenames))
    chapter_store.update_job(job.job_id, status="ready", progress=100)
    return job.job_id


def simulate_processing(chapter_id: str, filenames: list[str]) -> None:
    pages: list[PagePayload] = []
    for index, name in enumerate(filenames or ["page_1.png"]):
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
            audio_url=f"https://example.com/audio/{bubble_id}.mp3",
            word_times=word_times,
        )
        page = PagePayload(
            page_index=index,
            image_url=f"/uploads/{name}",
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

