from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable, TypedDict

from app.models.schemas import (
    BubbleItem,
    ChapterPayload,
    PagePayload,
    ProcessingMode,
    WordTime,
)
from app.services.pipeline import chapter_store
from app.services.speaker import speaker_linker
from app.services.tts import tts_service
from app.services.vision import CharacterAnalysis, vision_service


class ChapterFile(TypedDict):
    filename: str
    image_url: str
    width: int | None
    height: int | None
    path: str


def enqueue_chapter_job(
    chapter_id: str, files: Iterable[ChapterFile], processing_mode: ProcessingMode = "bring_to_life"
) -> str:
    job = chapter_store.create_job()
    chapter_store.update_job(
        job.job_id, status="processing", chapter_id=chapter_id, progress=5
    )
    process_chapter(chapter_id, list(files), job.job_id, processing_mode)
    chapter_store.update_job(job.job_id, status="ready", progress=100)
    return job.job_id


def _normalize_text(text: str) -> str:
    # Remove OCR artifacts and normalize spacing
    cleaned = text.replace("|", " ")
    cleaned = cleaned.replace("\n", " ")
    cleaned = cleaned.replace(";", "")  # Remove semicolons (OCR artifacts)
    cleaned = re.sub(r"^['\"]+|['\"]+$", "", cleaned)  # Remove leading/trailing quotes
    cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
    return cleaned.strip()


def _bubble_kind_from_analysis(analysis: CharacterAnalysis) -> str:
    descriptor = (analysis.character_type or "").lower()
    if any(keyword in descriptor for keyword in ("system", "ui", "computer", "panel")):
        return "narration"
    if any(keyword in descriptor for keyword in ("narration", "narrator")):
        return "narration"
    if "thought" in descriptor:
        return "thought"
    if "sfx" in descriptor or "sound" in descriptor or "fx" in descriptor:
        return "sfx"
    return "dialogue"


def process_chapter(
    chapter_id: str,
    files: list[ChapterFile],
    job_id: str | None = None,
    processing_mode: ProcessingMode = "bring_to_life",
) -> None:
    if not files:
        return

    pages: list[PagePayload] = []
    total_files = len(files)
    for index, file_info in enumerate(files):
        page_width = file_info.get("width") or 1080
        page_height = file_info.get("height") or 1920
        image_path = Path(file_info["path"])

        # 🤖 USE DEEPSEEK VISION API TO DETECT AND READ ALL TEXT
        # OCR completely removed - Vision AI does everything!
        print(f"🤖 Using GPT-4o-mini Vision API to read page {index}")
        vision_bubbles = vision_service.detect_and_read_all_bubbles(image_path)
        
        if not vision_bubbles:
            print("⚠️ Vision API found no bubbles, creating fallback")
            from app.services.vision import CharacterAnalysis
            fallback_analysis = CharacterAnalysis(
                character_type="unknown",
                emotion="neutral",
                tone="normal",
                voice_suggestion="voice_narrator",
                stability=0.5,
                similarity_boost=0.75,
                style=0.2,
            )
            vision_bubbles = [
                ([100, 200, page_width - 100, 400], "No text detected on this page.", fallback_analysis)
            ]
        
        print(f"✨ Vision API found {len(vision_bubbles)} text elements")

        items: list[BubbleItem] = []
        for bubble_idx, (bubble_box, text, analysis) in enumerate(vision_bubbles):
            normalized_text = _normalize_text(text)
            bubble_type = _bubble_kind_from_analysis(analysis)
            if processing_mode == "narrate":
                assigned_voice = "voice_narrator"
                stability = 0.7
                similarity_boost = 0.85
                speaker_label = "Narrator"
                style = 0.25
            else:
                assigned_voice = analysis.voice_suggestion
                stability = analysis.stability
                similarity_boost = analysis.similarity_boost
                style = analysis.style
                speaker_label = (
                    analysis.character_type.replace("_", " ").title()
                    if analysis.character_type
                    else None
                )
            
            # Generate TTS with emotion parameters
            tts_result = tts_service.synthesize(
                normalized_text,
                assigned_voice,
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
            )
            
            items.append(
                BubbleItem(
                    bubble_id=f"bubble_{index}_{bubble_idx}",
                    panel_box=[0, 0, page_width, page_height],
                    bubble_box=bubble_box,
                    type=bubble_type,
                    speaker_id=f"{chapter_id[:6]}_speaker_{index}_{bubble_idx}",
                    speaker_name=speaker_label,
                    voice_id=assigned_voice,
                    text=normalized_text,
                    audio_url=tts_result.audio_url,
                    word_times=[WordTime(**word.model_dump()) for word in tts_result.word_times],
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
        processing_mode=processing_mode,
    )
    chapter_store.save_chapter(chapter)

