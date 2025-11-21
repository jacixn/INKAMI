from __future__ import annotations

import tempfile
from difflib import SequenceMatcher
from pathlib import Path
import re
from typing import Any, Iterable, TypedDict

import requests
from PIL import Image

from app.core.config import settings
from app.models.schemas import (
    BubbleItem,
    ChapterPayload,
    PagePayload,
    ProcessingMode,
    WordTime,
)
from app.services.pipeline import chapter_store
from app.services.tts import tts_service
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
    placeholder = ChapterPayload(
        chapter_id=chapter_id,
        title=None,
        status="processing",
        progress=5,
        pages=[],
        processing_mode=processing_mode,
    )
    chapter_store.save_chapter(placeholder)

    files_snapshot = [dict(item) for item in files]

    chapter_store.queue.enqueue_call(
        func=process_chapter,
        args=(chapter_id, files_snapshot, job.job_id, processing_mode, narrator_gender),
        job_id=f"chapter-{chapter_id}",
        result_ttl=0,
        failure_ttl=86400,
        timeout=settings.job_timeout_seconds,
    )

    return job.job_id


def _normalize_text(text: str) -> str:
    # Remove OCR artifacts and normalize spacing
    cleaned = text.replace("|", " ")
    cleaned = cleaned.replace("\n", " ")
    cleaned = cleaned.replace(";", "")  # Remove semicolons (OCR artifacts)
    cleaned = re.sub(r"^['\"]+|['\"]+$", "", cleaned)  # Remove leading/trailing quotes
    cleaned = re.sub(r"\s+", " ", cleaned)  # Normalize whitespace
    return cleaned.strip()


def _clean_redundant_phrases(text: str) -> str:
    """
    Collapse repeated words/phrases like
    "Turn an entire world turned an tire world upside down upside down".
    """
    lowered = text.lower()
    if len(lowered) < 5:
        return text

    segments = re.split(r"([,.;!?])", text)
    cleaned_segments: list[str] = []

    for i in range(0, len(segments), 2):
        segment = segments[i].strip()
        punctuation = segments[i + 1] if i + 1 < len(segments) else ""
        if not segment:
            continue

        words = segment.split()
        deduped_words: list[str] = []
        window = max(1, min(4, len(words) // 2))
        last_phrases: set[str] = set()
        buffer: list[str] = []

        for word in words:
            buffer.append(word)
            if len(buffer) > window:
                buffer.pop(0)
            phrase = " ".join(buffer).lower()
            if phrase in last_phrases:
                # Skip repeating phrase
                buffer.pop()
                continue
            last_phrases.add(phrase)
            deduped_words.append(word)

        cleaned = " ".join(deduped_words)
        cleaned_segments.append(cleaned + punctuation)

    final_text = " ".join(segment.strip() for segment in cleaned_segments if segment.strip())
    return final_text or text


def _humanize_caps_for_tts(text: str) -> str:
    tokens = re.split(r"(\s+)", text)
    transformed: list[str] = []

    def should_soften(token: str) -> bool:
        letters = [c for c in token if c.isalpha()]
        if not letters:
            return False
        if any(c.islower() for c in token):
            return False
        if "." in token:
            return False
        # treat long all-caps or repeated letters as SFX words
        return True

    for token in tokens:
        if should_soften(token):
            transformed.append(token.lower())
        else:
            transformed.append(token)
    return "".join(transformed)
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

MIN_GAP_HEIGHT = 380
MAX_GAP_REGIONS = 5


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


def _recover_missing_bubbles(
    image_path: Path,
    page_width: int | None,
    page_height: int | None,
    bubbles: list[tuple[list[float], str, CharacterAnalysis]],
) -> list[tuple[list[float], str, CharacterAnalysis]]:
    if not bubbles:
        return bubbles

    try:
        with Image.open(image_path) as image:
            image_width = int(page_width or image.width)
            total_height = int(page_height or image.height)

            sorted_bubbles = sorted(bubbles, key=lambda entry: entry[0][1])
            gaps: list[tuple[int, int]] = []
            prev_bottom = 0

            for bubble_box, _, _ in sorted_bubbles:
                top = max(0, int(bubble_box[1]))
                if top - prev_bottom >= MIN_GAP_HEIGHT:
                    gaps.append((prev_bottom, min(top, total_height)))
                prev_bottom = max(prev_bottom, int(bubble_box[3]))

            if total_height - prev_bottom >= MIN_GAP_HEIGHT:
                gaps.append((prev_bottom, total_height))

            if not gaps:
                return bubbles

            recovered: list[tuple[list[float], str, CharacterAnalysis]] = []
            for gap_start, gap_end in gaps[:MAX_GAP_REGIONS]:
                if gap_end - gap_start < MIN_GAP_HEIGHT:
                    continue

                crop = image.crop((0, gap_start, image_width, gap_end))
                if crop.height < 80:
                    continue

                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    temp_path = Path(tmp.name)
                    crop.save(temp_path)
                try:
                    extra = vision_service.detect_and_read_all_bubbles(temp_path)
                finally:
                    temp_path.unlink(missing_ok=True)

                for box, text, analysis in extra:
                    adjusted_box = [
                        box[0],
                        box[1] + gap_start,
                        box[2],
                        box[3] + gap_start,
                    ]
                    recovered.append((adjusted_box, text, analysis))

            if recovered:
                print(f"✨ Gap recovery added {len(recovered)} bubble(s)")
                return bubbles + recovered
    except (FileNotFoundError, OSError) as exc:
        print(f"⚠️ Gap recovery skipped: {exc}")

    return bubbles


def _build_tone_hint(text: str, analysis: CharacterAnalysis) -> str | None:
    hints: list[str] = []
    trimmed = text.strip()

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
        image_path = _ensure_local_image(file_info, chapter_id, index)

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
            print(
                f"⚠️ Vision API returned no bubbles for page {index}; "
                "keeping artwork but skipping audio."
            )
        else:
            print(
                f"✨ Vision API found {len(vision_bubbles)} text elements (mode: {processing_mode})"
            )

        # STEP 1: Collect all candidate bubbles (filter out obvious junk)
        candidates: list[tuple[list[float], str, Any, str]] = []
        # Attempt to recover bubbles in large gaps that the main pass missed
        vision_bubbles = _recover_missing_bubbles(
            image_path,
            page_width,
            page_height,
            vision_bubbles,
        )

        for bubble_box, text, analysis in vision_bubbles:
            normalized_text = _normalize_text(text)
            bubble_type = _bubble_kind_from_analysis(analysis)
            if processing_mode == "narrate" and bubble_type != "sfx":
                if _looks_like_sfx_text(normalized_text):
                    bubble_type = "sfx"
            
            # FILTER OUT HALLUCINATIONS
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
        def normalize_for_comparison(text: str) -> str:
            """Remove spaces, hyphens, and extra whitespace for accurate duplicate detection."""
            return text.replace(" ", "").replace("-", "").replace("\n", "").replace("\r", "")
        
        unique_bubbles: list[tuple[list[float], str, Any]] = []
        used_indices: set[int] = set()
        
        for i, (box_i, text_i, analysis_i, lower_i) in enumerate(candidates):
            if i in used_indices:
                continue
            
            # Normalize for comparison (remove spaces/hyphens)
            normalized_i = normalize_for_comparison(lower_i)
            
            # Find all similar texts (duplicates/substrings) - check ALL candidates
            similar_group = [(i, box_i, text_i, analysis_i, lower_i, normalized_i)]
            for j, (box_j, text_j, analysis_j, lower_j) in enumerate(candidates):
                if j == i or j in used_indices:  # Skip self and already-used
                    continue
                
                normalized_j = normalize_for_comparison(lower_j)
                
                longer = max(len(normalized_i), len(normalized_j))
                shorter = min(len(normalized_i), len(normalized_j))
                substring_match = (
                    normalized_i in normalized_j or normalized_j in normalized_i
                )
                length_ratio = shorter / longer if longer else 1.0
                similarity = SequenceMatcher(None, normalized_i, normalized_j).ratio()

                if substring_match and length_ratio > 0.7:
                    similar_group.append((j, box_j, text_j, analysis_j, lower_j, normalized_j))
                elif similarity >= 0.88:
                    similar_group.append((j, box_j, text_j, analysis_j, lower_j, normalized_j))
            
            # Pick the LONGEST one from the group (most complete sentence)
            # Use the normalized length for comparison
            best = max(similar_group, key=lambda x: len(x[5]))
            unique_bubbles.append((best[1], best[2], best[3]))
            
            # Mark all in this group as used
            for idx, *_ in similar_group:
                used_indices.add(idx)
        
        print(f"✨ After deduplication: {len(unique_bubbles)} unique bubbles")

        # STEP 3: Generate TTS for unique bubbles
        items: list[BubbleItem] = []
        for bubble_idx, (bubble_box, normalized_text, analysis) in enumerate(unique_bubbles):
            cleaned_text = _clean_redundant_phrases(normalized_text)
            tts_ready_text = _humanize_caps_for_tts(cleaned_text)
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
            
            # Generate TTS with emotion parameters
            tone_hint = _build_tone_hint(cleaned_text, analysis)
            delivery_text = _build_tts_delivery_text(tts_ready_text, analysis)
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
                    text=cleaned_text,
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
    if job_id:
        chapter_store.update_job(job_id, status="ready", progress=100)


def _ensure_local_image(file_info: ChapterFile, chapter_id: str, index: int) -> Path:
    path = Path(file_info["path"])
    if path.exists():
        return path

    image_url = file_info.get("image_url")
    if not image_url:
        raise FileNotFoundError(
            f"Unable to locate file for chapter {chapter_id} page {index}: {path}"
        )

    cache_dir = Path(settings.upload_dir) / "worker-cache" / chapter_id
    cache_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file_info.get("filename") or "").suffix or ".png"
    local_path = cache_dir / f"{chapter_id}_{index:04d}{suffix}"

    print(f"📥 Downloading page {index} for chapter {chapter_id} from {image_url}")
    response = requests.get(image_url, timeout=60)
    response.raise_for_status()
    local_path.write_bytes(response.content)
    return local_path

