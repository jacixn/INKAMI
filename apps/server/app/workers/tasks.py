from __future__ import annotations

import uuid
from pathlib import Path
from typing import Iterable, TypedDict

from app.models.schemas import BubbleItem, ChapterPayload, PagePayload, WordTime
from app.services.ocr import DetectedBubble, ocr_service
from app.services.pipeline import chapter_store
from app.services.speaker import speaker_linker
from app.services.tts import tts_service

DEFAULT_VOICE = "voice_friendly_f"


class ChapterFile(TypedDict):
    filename: str
    image_url: str
    width: int | None
    height: int | None
    path: str


def enqueue_chapter_job(chapter_id: str, files: Iterable[ChapterFile]) -> str:
    job = chapter_store.create_job()
    chapter_store.update_job(
        job.job_id, status="processing", chapter_id=chapter_id, progress=5
    )
    process_chapter(chapter_id, list(files), job.job_id)
    chapter_store.update_job(job.job_id, status="ready", progress=100)
    return job.job_id


def _voice_for_bubble(index: int) -> str:
    palette = [
        "voice_friendly_f",
        "voice_cool_f",
        "voice_brash_m",
        "voice_stoic_m",
        "voice_androgynous",
        "voice_narrator",
    ]
    return palette[index % len(palette)]


def _bubble_to_item(
    chapter_id: str,
    page_index: int,
    bubble_index: int,
    page_width: int,
    page_height: int,
    bubble: DetectedBubble,
) -> BubbleItem:
    speaker_id = f"{chapter_id[:6]}_speaker_{page_index}_{bubble_index}"
    assigned_voice = bubble.voice_hint or _voice_for_bubble(bubble_index)
    tts_result = tts_service.synthesize(bubble.text, assigned_voice)
    return BubbleItem(
        bubble_id=f"bubble_{page_index}_{bubble_index}",
        panel_box=[0, 0, page_width, page_height],
        bubble_box=list(bubble.box),
        type=bubble.kind,
        speaker_id=speaker_id,
        speaker_name=bubble.speaker_name,
        voice_id=assigned_voice,
        text=bubble.text,
        audio_url=tts_result.audio_url,
        word_times=[WordTime(**word.model_dump()) for word in tts_result.word_times],
    )


def _fallback_bubble(page_width: int, page_height: int) -> DetectedBubble:
    text = "We couldn't transcribe this bubble yet, but playback is ready."
    return DetectedBubble(
        bubble_id=str(uuid.uuid4()),
        box=[40, 40, page_width - 40, int(page_height * 0.3)],
        text=text,
        kind="dialogue",
        speaker_name=None,
        voice_hint=DEFAULT_VOICE,
    )


def process_chapter(chapter_id: str, files: list[ChapterFile], job_id: str | None = None) -> None:
    if not files:
        return

    pages: list[PagePayload] = []
    total_files = len(files)
    for index, file_info in enumerate(files):
        page_width = file_info.get("width") or 1080
        page_height = file_info.get("height") or 1920
        image_path = Path(file_info["path"])

        detected = ocr_service.detect_bubbles(image_path)
        if not detected:
            fallback_text = ocr_service.extract(image_path, [0, 0, page_width, page_height])
            if fallback_text.strip():
                detected = [
                    DetectedBubble(
                        bubble_id=str(uuid.uuid4()),
                        box=[40, 40, page_width - 40, int(page_height * 0.4)],
                        text=fallback_text.strip(),
                        kind="dialogue",
                        speaker_name=None,
                        voice_hint=DEFAULT_VOICE,
                    )
                ]
            else:
                detected = [_fallback_bubble(page_width, page_height)]

        items: list[BubbleItem] = []
        for bubble_idx, bubble in enumerate(detected):
            items.append(
                _bubble_to_item(
                    chapter_id=chapter_id,
                    page_index=index,
                    bubble_index=bubble_idx,
                    page_width=page_width,
                    page_height=page_height,
                    bubble=bubble,
                )
            )

        items.sort(key=lambda item: item.bubble_box[1])
        reading_order = [item.bubble_id for item in items]
        page = PagePayload(
            page_index=index,
            image_url=file_info.get("image_url") or "",
            width=page_width,
            height=page_height,
            items=items,
            reading_order=reading_order,
        )
        pages.append(page)

        if job_id:
            progress = 10 + int(((index + 1) / total_files) * 80)
            chapter_store.update_job(job_id, progress=progress)

    chapter = ChapterPayload(
        chapter_id=chapter_id,
        title=f"Chapter {chapter_id[:8]}",
        status="ready",
        progress=100,
        pages=pages,
    )
    chapter_store.save_chapter(chapter)

