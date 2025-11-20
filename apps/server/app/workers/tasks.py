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
from app.services.tts import TTSResult, tts_service
from app.services.vision import CharacterAnalysis, vision_service


class ChapterFile(TypedDict):
    filename: str
    image_url: str
    width: int | None
    height: int | None
    path: str


def enqueue_chapter_job(
    chapter_id: str,
    files: Iterable[ChapterFile],
    processing_mode: ProcessingMode = "bring_to_life",
    narrator_gender: str = "female",
) -> str:
    job = chapter_store.create_job()
    chapter_store.update_job(
        job.job_id, status="processing", chapter_id=chapter_id, progress=5
    )
    process_chapter(chapter_id, list(files), job.job_id, processing_mode, narrator_gender)
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


def _strip_sfx_prefix(text: str) -> str:
    return re.sub(r"^(?:sfx|fx)\s*[:\-]\s*", "", text, flags=re.IGNORECASE).strip()


SFX_KEYWORDS = {
    "boom",
    "bang",
    "kraa",
    "krak",
    "wham",
    "slam",
    "snap",
    "crash",
    "thud",
    "whoosh",
    "fwoosh",
    "fwip",
    "swoosh",
    "kshh",
    "pow",
    "zap",
}


APOLOGY_PATTERNS = {
    "i'm sorry, i can't transcribe",
    "i'm sorry, i can't assist",
    "i'm sorry, but i cannot",
    "i can't see the speech bubble",
    "i'm sorry, but i can't",
    "i cannot assist with that",
}


def _looks_like_sfx_text(text: str) -> bool:
    trimmed = text.strip()
    if not trimmed:
        return False
    # short, mostly uppercase, or contains classic SFX keywords
    words = trimmed.split()
    letters = [c for c in trimmed if c.isalpha()]
    upper_letters = [c for c in letters if c.isupper()]
    upper_ratio = (len(upper_letters) / len(letters)) if letters else 0

    if len(words) <= 3 and upper_ratio >= 0.8:
        return True
    lowered = trimmed.lower()
    if any(keyword in lowered for keyword in SFX_KEYWORDS):
        return True
    if re.fullmatch(r"[A-Z!?]{2,}", trimmed.upper()):
        return True
    return False


def _build_tone_hint(text: str, analysis: CharacterAnalysis) -> str | None:
    hints: list[str] = []
    trimmed = text.strip()
    lowered = trimmed.lower()

    if trimmed.endswith("?"):
        hints.append("Deliver it as a genuine question with a gentle rise at the end.")
    elif trimmed.endswith("!"):
        hints.append("Deliver it as a forceful exclamation with extra emphasis.")
    elif trimmed.endswith("..."):
        hints.append("Let the ending trail off softly, as if unsure.")

    if "," in trimmed:
        hints.append("Add a brief natural pause at each comma.")
    if "…" in trimmed:
        hints.append("Let the ellipsis trail off softly.")

    tone = (analysis.tone or "").lower()
    tone_map = {
        "questioning": "Sound curious and slightly rising toward the end.",
        "dramatic": "Lean into a dramatic delivery with controlled pacing.",
        "serious": "Keep the delivery measured and grounded.",
        "playful": "Add a light, playful lilt.",
        "neutral": "",
    }
    tone_hint = tone_map.get(tone)
    if tone_hint:
        hints.append(tone_hint)

    emotion = (analysis.emotion or "").lower()
    emotion_map = {
        "angry": "Add intensity as if angry.",
        "excited": "Sound excited and energetic.",
        "sad": "Soften the tone, as if saddened.",
        "scared": "Let a hint of fear or urgency come through.",
    }
    emotion_hint = emotion_map.get(emotion)
    if emotion_hint:
        hints.append(emotion_hint)

    if not hints:
        return None
    return " ".join(hints)


def _build_tts_delivery_text(text: str, analysis: CharacterAnalysis) -> str:
    """Lightly tweak punctuation so OpenAI leans into the intent."""
    trimmed = text.strip()
    emphasized = trimmed

    if trimmed.endswith("?"):
        # Double question mark sometimes helps OpenAI raise pitch
        emphasized = trimmed + "?"
    elif trimmed.endswith(("!", "!!")):
        emphasized = trimmed + "!"
    elif trimmed.endswith(("...", "…")):
        # Ensure it's a single ellipsis character to avoid "dot dot dot"
        emphasized = trimmed.rstrip(".…") + "…"
    else:
        tone = (analysis.tone or "").lower()
        emotion = (analysis.emotion or "").lower()
        if tone in {"questioning", "curious"} and not trimmed.endswith("?"):
            emphasized = trimmed + "?"
        elif tone in {"dramatic", "excited"} or emotion in {"angry", "excited"}:
            if not trimmed.endswith(("!", "!!")):
                emphasized = trimmed + "!"
        elif tone in {"sad", "hesitant"} and not trimmed.endswith(("...", "…")):
            emphasized = trimmed + "…"

    return emphasized


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
    narrator_gender: str = "female",
) -> None:
    if not files:
        return

    pages: list[PagePayload] = []
    total_files = len(files)
    character_voice_memory: dict[str, tuple[str, float, float, float]] = {}
    for index, file_info in enumerate(files):
        page_width = file_info.get("width") or 1080
        page_height = file_info.get("height") or 1920
        image_path = Path(file_info["path"])

        # 🤖 USE DEEPSEEK VISION API TO DETECT AND READ ALL TEXT
        # OCR completely removed - Vision AI does everything!
        print(f"🤖 Using GPT-4o-mini Vision API to read page {index} (mode: {processing_mode})")
        print(f"📁 Image path: {image_path}, exists: {image_path.exists()}")
        
        try:
            vision_bubbles = vision_service.detect_and_read_all_bubbles(image_path)
        except Exception as e:
            print(f"❌ Vision API call failed: {type(e).__name__}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            vision_bubbles = []
        
        if not vision_bubbles:
            print(f"⚠️ Vision API found no bubbles (mode: {processing_mode}), creating fallback")
            from app.services.vision import CharacterAnalysis
            fallback_analysis = CharacterAnalysis(
                character_type="unknown",
                emotion="neutral",
                tone="normal",
                voice_suggestion="voice_narrator_f",
                stability=0.5,
                similarity_boost=0.75,
                style=0.2,
            )
            vision_bubbles = [
                ([100, 200, page_width - 100, 400], "No text detected on this page.", fallback_analysis)
            ]
        
        print(f"✨ Vision API found {len(vision_bubbles)} text elements (mode: {processing_mode})")

        # STEP 1: Collect all candidate bubbles (filter out obvious junk)
        candidates: list[tuple[list[float], str, Any, str]] = []
        for bubble_box, text, analysis in vision_bubbles:
            normalized_text = _normalize_text(text)
            bubble_type = _bubble_kind_from_analysis(analysis)
            if processing_mode == "narrate" and bubble_type != "sfx":
                if _looks_like_sfx_text(normalized_text):
                    bubble_type = "sfx"
            
            # FILTER OUT SFX AND HALLUCINATIONS
            if bubble_type == "sfx":
                continue
            if normalized_text.lower() in {"jason", "json"}:
                continue
            if len(normalized_text) < 2 and not normalized_text.isalnum():
                continue
            
            # FILTER OUT GPT APOLOGY PHRASES
            text_lower = normalized_text.lower()
            if any(pattern in text_lower for pattern in APOLOGY_PATTERNS):
                continue
            
            candidates.append((bubble_box, normalized_text, analysis, text_lower))
        
        # STEP 2: Deduplicate by keeping the LONGEST/MOST COMPLETE version of each sentence
        unique_bubbles: list[tuple[list[float], str, Any]] = []
        used_indices: set[int] = set()
        
        for i, (box_i, text_i, analysis_i, lower_i) in enumerate(candidates):
            if i in used_indices:
                continue
            
            # Find all similar texts (duplicates/substrings) - check ALL candidates
            similar_group = [(i, box_i, text_i, analysis_i, lower_i)]
            for j, (box_j, text_j, analysis_j, lower_j) in enumerate(candidates):
                if j == i or j in used_indices:  # Skip self and already-used
                    continue
                
                # Check if they're substrings of each other
                if lower_i in lower_j or lower_j in lower_i:
                    longer = max(len(lower_i), len(lower_j))
                    shorter = min(len(lower_i), len(lower_j))
                    if shorter / longer > 0.8:  # >80% similar
                        similar_group.append((j, box_j, text_j, analysis_j, lower_j))
            
            # Pick the LONGEST one from the group (most complete sentence)
            best = max(similar_group, key=lambda x: len(x[4]))
            unique_bubbles.append((best[1], best[2], best[3]))
            
            # Mark all in this group as used
            for idx, *_ in similar_group:
                used_indices.add(idx)
        
        print(f"✨ After deduplication: {len(unique_bubbles)} unique bubbles")

        # STEP 3: Generate TTS for unique bubbles
        items: list[BubbleItem] = []
        for bubble_idx, (bubble_box, normalized_text, analysis) in enumerate(unique_bubbles):
            bubble_type = _bubble_kind_from_analysis(analysis)
                
            character_key = (analysis.character_type or "").strip().lower()
            reuse_allowed = (
                processing_mode != "narrate"
                and character_key
                and character_key not in {"unknown", "sfx_autodetect"}
                and bubble_type not in {"sfx", "narration"}
            )
            if processing_mode == "narrate":
                assigned_voice = (
                    "voice_narrator_m" if narrator_gender == "male" else "voice_narrator_f"
                )
                stability = 0.7
                similarity_boost = 0.85
                speaker_label = "Narrator"
                style = 0.25
            else:
                if reuse_allowed and character_key in character_voice_memory:
                    cached_voice, cached_stability, cached_similarity, cached_style = (
                        character_voice_memory[character_key]
                    )
                    assigned_voice = cached_voice
                    stability = cached_stability
                    similarity_boost = cached_similarity
                    style = cached_style
                else:
                    assigned_voice = analysis.voice_suggestion
                    stability = analysis.stability
                    similarity_boost = analysis.similarity_boost
                    style = analysis.style
                    if reuse_allowed and assigned_voice:
                        character_voice_memory[character_key] = (
                            assigned_voice,
                            stability,
                            similarity_boost,
                            style,
                        )
                speaker_label = (
                    analysis.character_type.replace("_", " ").title()
                    if analysis.character_type
                    else None
                )
            
            if bubble_type == "sfx":
                continue # Should be caught above, but safe keeping
            
            # Generate TTS with emotion parameters
            tone_hint = _build_tone_hint(normalized_text, analysis)
            delivery_text = _build_tts_delivery_text(normalized_text, analysis)
            tts_result = tts_service.synthesize(
                delivery_text,
                assigned_voice,
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                tone_hint=tone_hint,
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

