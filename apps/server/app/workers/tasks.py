from __future__ import annotations

import uuid
from pathlib import Path
import re
from typing import Iterable, TypedDict

from app.models.schemas import BubbleItem, ChapterPayload, PagePayload, WordTime
from app.services.ocr import DetectedBubble, ocr_service
from app.services.pipeline import chapter_store
from app.services.speaker import speaker_linker
from app.services.tts import tts_service
from app.services.vision import vision_service

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


def _normalize_text(text: str) -> str:
    cleaned = text.replace("|", " ")
    cleaned = cleaned.replace("\n", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _bubble_to_item(
    chapter_id: str,
    page_index: int,
    bubble_index: int,
    page_width: int,
    page_height: int,
    bubble: DetectedBubble,
    image_path: Path,
) -> BubbleItem:
    speaker_id = f"{chapter_id[:6]}_speaker_{page_index}_{bubble_index}"
    
    # Use AI vision to analyze the bubble and determine voice/emotion
    analysis = vision_service.analyze_bubble(
        image_path=image_path,
        text=bubble.text,
        bubble_box=list(bubble.box),
        page_height=page_height,
    )
    assigned_voice = analysis.voice_suggestion
    normalized_text = _normalize_text(bubble.text)
    
    # Generate TTS with emotion parameters from AI analysis
    tts_result = tts_service.synthesize(
        normalized_text,
        assigned_voice,
        stability=analysis.stability,
        similarity_boost=analysis.similarity_boost,
    )
    
    return BubbleItem(
        bubble_id=f"bubble_{page_index}_{bubble_index}",
        panel_box=[0, 0, page_width, page_height],
        bubble_box=list(bubble.box),
        type=bubble.kind,
        speaker_id=speaker_id,
        speaker_name=bubble.speaker_name,
        voice_id=assigned_voice,
        text=normalized_text,
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
        # Perform a second pass with a lower threshold to capture UI/system text blocks.
        if detected:
            existing = {bubble.text.strip().lower() for bubble in detected if bubble.text}
        else:
            existing = set()
        secondary = ocr_service.detect_bubbles(image_path, conf_threshold=35)
        for bubble in secondary:
            normalized = bubble.text.strip().lower()
            if not normalized:
                continue
            if normalized in existing:
                continue
            detected.append(bubble)
            existing.add(normalized)
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

        print(f"🧠 OCR initial bubbles ({len(detected)}): {[bubble.text for bubble in detected]}")

        # Refine each detected bubble text using a targeted OCR pass over its bounds.
        for bubble in detected:
            # Expand the box slightly to capture edge text
            expanded_box = [
                max(0, bubble.box[0] - 20),
                max(0, bubble.box[1] - 20),
                min(page_width, bubble.box[2] + 60),
                min(page_height, bubble.box[3] + 60),
            ]
            refined = ocr_service.extract(image_path, expanded_box).strip()
            if not refined:
                continue
            current = bubble.text.strip()
            # Always use refined if it contains more content or punctuation
            if len(refined) > len(current) or ("?" in refined and "?" not in current) or ("..." in refined and "..." not in current):
                bubble.text = refined

        print(f"🧠 OCR refined bubbles ({len(detected)}): {[bubble.text for bubble in detected]}")

        # Try to detect UI elements that might have been missed
        ui_elements = ocr_service.detect_ui_elements(image_path)
        print(f"🖼️ UI detection found {len(ui_elements)} elements: {[elem.text for elem in ui_elements]}")
        if ui_elements:
            # Filter out UI elements that overlap with already detected bubbles
            for ui_elem in ui_elements:
                overlaps = False
                ui_text_lower = ui_elem.text.lower()
                for bubble in detected:
                    # Check if the UI text is already included in a detected bubble
                    if any(word in bubble.text.lower() for word in ui_text_lower.split() if len(word) > 3):
                        overlaps = True
                        break
                if not overlaps:
                    detected.append(ui_elem)
            print(f"🧠 OCR with UI elements ({len(detected)}): {[bubble.text for bubble in detected]}")

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
                    image_path=image_path,
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

