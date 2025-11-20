from __future__ import annotations

import base64
import io
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from app.core.config import settings


@dataclass
class CharacterAnalysis:
    """Analysis of a character and their emotional state."""
    character_type: str  # e.g., "young_female", "tough_male", "wise_mentor"
    emotion: str  # e.g., "confused", "angry", "excited", "sad", "neutral"
    tone: str  # e.g., "questioning", "assertive", "timid", "dramatic"
    voice_suggestion: str  # Which ElevenLabs voice to use
    stability: float  # 0.0-1.0, lower = more expressive
    similarity_boost: float  # 0.0-1.0, higher = more similar to original voice
    style: float = 0.2  # 0.0-1.0 intensity for stylistic delivery


@dataclass
class VisionTextEntry:
    text: str
    speaker_gender: str | None = None
    speaker_age: str | None = None
    emotion: str | None = None
    tone: str | None = None
    bubble_type: str | None = None

    @property
    def has_metadata(self) -> bool:
        return any(
            value
            for value in (
                self.speaker_gender,
                self.speaker_age,
                self.emotion,
                self.tone,
                self.bubble_type,
            )
        )


class VisionService:
    """Service for analyzing manga/manhwa images with AI vision."""

    OPENAI_URL = "https://api.openai.com/v1/responses"
    VISION_MODEL = "gpt-4o-mini"

    VOICE_MAPPING = {
        # Female character archetypes
        "child_female": "voice_child_f",
        "young_female": "voice_young_f",
        "adult_female": "voice_adult_f",
        
        # Male character archetypes
        "child_male": "voice_child_m",
        "young_male": "voice_young_m",
        "adult_male": "voice_adult_m",
        
        # Special
        "narrator": "voice_narrator_f",
        "system": "voice_system",
    }

    def detect_and_read_all_bubbles(self, image_path: Path) -> list[tuple[list[int], str, CharacterAnalysis]]:
        """Use AI vision to find ALL text bubbles and read them in one go."""
        
        if not settings.openai_api_key:
            print("⚠️ OpenAI API key not set")
            return []
        
        try:
            # Load and optionally split the image for long-scroll chapters
            from PIL import Image

            image = Image.open(image_path)
            width, height = image.size
            segments = self._segment_vertical_ranges(height)

            prompt = (
                "You are an expert manga letterer and voice director. "
                "Look at the ENTIRE page and extract EVERY readable text element: speech bubbles, narration boxes, "
                "system/U.I. panels, glowing screens, and sound effects. "
                "Return results in reading order (top-to-bottom, left-to-right) as STRICT JSON (no narration outside JSON). "
                "Each entry must be an object with: "
                '{"text":"..." , "speaker_gender":"male|female|unknown", '
                '"speaker_age":"child|teen|young adult|adult", '
                '"emotion":"happy|sad|angry|scared|serious|neutral", '
                '"tone":"playful|serious|questioning|dramatic|neutral", '
                '"bubble_type":"dialogue|thought|narration|system|sfx" }.'
            )

            print(
                f"🧩 Vision segmentation: {len(segments)} slice(s) for page height {height}px"
            )

            bubbles: list[tuple[list[int], str, CharacterAnalysis]] = []
            seen_signatures: set[tuple[str, int]] = set()
            total_entries = 0

            for seg_index, (start_y, end_y) in enumerate(segments, start=1):
                crop = image.crop((0, start_y, width, end_y))
                img_base64 = self._encode_image(crop)
                segment_height = end_y - start_y
                segment_prompt = prompt
                if len(segments) > 1:
                    segment_prompt += (
                        f" You are looking only at segment {seg_index} of {len(segments)}, "
                        f"covering vertical pixels {start_y} through {end_y}. "
                        "Focus on text inside this slice only."
                    )

                print(
                    f"🤖 Calling GPT-4o-mini for slice {seg_index}/{len(segments)} "
                    f"(height {segment_height}px)"
                )
                content = self._call_openai(segment_prompt, img_base64, max_tokens=700)
                if not content:
                    print(f"⚠️ Vision API returned no text for slice {seg_index}")
                    continue
                print(f"📝 Vision response (slice {seg_index}):\n{content}")

                entries = self._parse_detected_entries(content)
                if not entries:
                    print(f"⚠️ Could not parse text entries for slice {seg_index}")
                    continue

                slice_boxes = self._approximate_bubble_boxes(
                    len(entries), width, segment_height
                )
                for idx, entry in enumerate(entries):
                    text = entry.text.strip()
                    if not text:
                        continue
                    box = (
                        slice_boxes[idx]
                        if idx < len(slice_boxes)
                        else [80, 40, width - 80, segment_height - 40]
                    )
                    adjusted_box = [
                        box[0],
                        box[1] + start_y,
                        box[2],
                        box[3] + start_y,
                    ]
                    signature = self._entry_signature(text, adjusted_box)
                    if signature in seen_signatures:
                        continue
                    seen_signatures.add(signature)

                    analysis = self._analysis_from_entry(
                        entry, text, adjusted_box, height
                    )
                    bubbles.append((adjusted_box, text, analysis))
                    total_entries += 1
                    print(
                        f"✨ Vision detected text #{total_entries}: {text[:60]} "
                        f"(slice {seg_index})"
                    )

            if not bubbles:
                print("⚠️ Vision API did not return any usable text entries")
            else:
                print(
                    f"✨ Vision API found {total_entries} text elements across {len(segments)} slice(s)"
                )

            return bubbles
            
        except Exception as e:
            print(f"❌ Vision API failed: {type(e).__name__}: {str(e)}")
            return []
    
    def read_and_analyze_bubble(
        self,
        image_path: Path,
        bubble_box: list[int],
        page_height: int | float | None = None,
    ) -> tuple[str, CharacterAnalysis]:
        """Use AI vision to read text from a specific bubble region."""
        
        if not settings.openai_api_key:
            print("⚠️ OpenAI API key not set, using fallback")
            return "", self._fallback_analysis()
        
        try:
            # Crop the bubble region
            from PIL import Image
            image = Image.open(image_path)
            crop = image.crop((bubble_box[0], bubble_box[1], bubble_box[2], bubble_box[3]))
            
            img_base64 = self._encode_image(crop)
            
            prompt = (
                "Transcribe this manga speech bubble exactly as written. Preserve punctuation, "
                "question marks, ellipses, shouting, and casing. Return ONLY the text."
            )
            
            print(f"🤖 Calling GPT-4o-mini for bubble at {bubble_box}")
            text = self._call_openai(prompt, img_base64, max_tokens=200)
            if text:
                text = text.replace("\n", " ").replace("  ", " ").strip()
                print(f"✨ Vision API read: {text}")
                analysis = self._analyze_from_text(text, bubble_box, page_height)
                return text, analysis
            
            print("⚠️ Vision API returned no text")
            return "", self._fallback_analysis()
            
        except Exception as e:
            print(f"❌ Vision API failed: {type(e).__name__}: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return "", self._fallback_analysis()
    
    def analyze_bubble(
        self,
        image_path: Path,
        text: str,
        bubble_box: list[int],
        page_height: int | float | None = None,
    ) -> CharacterAnalysis:
        """Analyze a speech bubble and determine character emotion and voice."""
        
        # Use smart text analysis to determine emotion and voice
        return self._analyze_from_text(text, bubble_box, page_height)

    def _analysis_from_entry(
        self,
        entry: VisionTextEntry,
        fallback_text: str,
        bubble_box: list[int],
        page_height: int | float | None,
    ) -> CharacterAnalysis:
        if entry.has_metadata:
            metadata_analysis = self._analysis_from_metadata(entry)
            if metadata_analysis:
                return metadata_analysis
        if self._looks_like_sfx(fallback_text):
            voice_id = self.VOICE_MAPPING.get("sfx", self.VOICE_MAPPING["narrator"])
            return CharacterAnalysis(
                character_type="sfx_autodetect",
                emotion="neutral",
                tone="impact",
                voice_suggestion=voice_id,
                stability=0.3,
                similarity_boost=0.85,
                style=0.7,
            )
        return self._analyze_from_text(fallback_text, bubble_box, page_height)

    def _analysis_from_metadata(self, entry: VisionTextEntry) -> CharacterAnalysis | None:
        gender = (entry.speaker_gender or "unknown").lower()
        age = (entry.speaker_age or "").lower()
        bubble_type = (entry.bubble_type or "").lower()
        emotion = (entry.emotion or "neutral").lower()
        tone = (entry.tone or "normal").lower()

        voice_key = self._map_voice_key(gender, age, bubble_type)
        voice_id = self.VOICE_MAPPING.get(voice_key, self.VOICE_MAPPING["narrator"])
        stability, similarity, style = self._emotion_to_settings(emotion)

        character_label = bubble_type or f"{gender}_{age or 'unknown'}"
        print(
            f"🎭 Vision metadata: type={character_label} gender={gender} age={age} "
            f"emotion={emotion} → {voice_id} (stability={stability})"
        )

        return CharacterAnalysis(
            character_type=character_label,
            emotion=emotion,
            tone=tone,
            voice_suggestion=voice_id,
            stability=stability,
            similarity_boost=similarity,
            style=style,
        )

    def _map_voice_key(self, gender: str, age: str, bubble_type: str) -> str:
        if bubble_type in {"system", "ui", "computer", "hud"}:
            return "system"
        if bubble_type in {"sfx", "fx", "effect", "sound"}:
            return "sfx"
        if bubble_type in {"narration", "narrator"}:
            return "narrator"

        if gender == "male":
            if any(keyword in age for keyword in ("child", "kid", "boy")):
                return "child_male"
            if any(keyword in age for keyword in ("teen", "young", "youth")):
                return "young_male"
            return "adult_male"

        if gender == "female":
            if any(keyword in age for keyword in ("child", "kid", "girl")):
                return "child_female"
            if any(keyword in age for keyword in ("teen", "young", "youth")):
                return "young_female"
            return "adult_female"

        # Unknown gender: infer from bubble type or default to young female
        if bubble_type in {"thought"}:
            return "young_female"
        if bubble_type in {"sfx"}:
            return "narrator"
        return "young_female"

    def _emotion_to_settings(self, emotion: str) -> tuple[float, float, float]:
        emotion = emotion.lower()
        stability = 0.5
        similarity = 0.75
        style = 0.2
        
        if emotion in {"angry", "furious", "excited", "ecstatic"}:
            stability = 0.22
            similarity = 0.68
            style = 0.85
        elif emotion in {"happy", "playful", "amused"}:
            stability = 0.35
            similarity = 0.75
            style = 0.6
        elif emotion in {"sad", "melancholy", "serious", "calm"}:
            stability = 0.65
            similarity = 0.82
            style = 0.35
        elif emotion in {"scared", "nervous", "anxious"}:
            stability = 0.4
            similarity = 0.72
            style = 0.55
        
        return stability, similarity, style

    def _parse_detected_entries(self, content: str) -> list[VisionTextEntry]:
        if not content:
            return []
        
        content = content.strip()
        if not content:
            return []
        
        try:
            normalized = self._strip_code_fences(content)
            parsed = json.loads(normalized)
            entries = self._extract_entries_from_structure(parsed)
            if entries:
                return entries
        except json.JSONDecodeError:
            pass
        
        fallback_texts = self._split_plain_text(content)
        return [VisionTextEntry(text=text) for text in fallback_texts]
    
    def _extract_entries_from_structure(self, data) -> list[VisionTextEntry]:
        if isinstance(data, list):
            entries: list[VisionTextEntry] = []
            for item in data:
                entries.extend(self._extract_entries_from_structure(item))
            return entries
        
        if isinstance(data, dict):
            entry = self._entry_from_dict(data)
            if entry:
                return [entry]
            entries: list[VisionTextEntry] = []
            for value in data.values():
                entries.extend(self._extract_entries_from_structure(value))
            return entries
        
        if isinstance(data, str):
            text = data.strip()
            if text:
                return [VisionTextEntry(text=text)]
        return []
    
    def _entry_from_dict(self, data: dict) -> VisionTextEntry | None:
        text_value = data.get("text") or data.get("content")
        if isinstance(text_value, (str, int, float)):
            text = str(text_value).strip()
            if not text:
                return None
            return VisionTextEntry(
                text=text,
                speaker_gender=self._clean_meta_value(
                    data.get("speaker_gender")
                    or data.get("gender")
                    or data.get("voice_gender")
                ),
                speaker_age=self._clean_meta_value(
                    data.get("speaker_age") or data.get("age")
                ),
                emotion=self._clean_meta_value(data.get("emotion")),
                tone=self._clean_meta_value(data.get("tone")),
                bubble_type=self._clean_meta_value(
                    data.get("bubble_type")
                    or data.get("type")
                    or data.get("speaker_type")
                ),
            )
        return None
    
    def _clean_meta_value(self, value) -> str | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return str(value).strip()
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        return None
    
    def _split_plain_text(self, content: str) -> list[str]:
        lines = content.replace("\r", "\n").split("\n")
        cleaned_lines: list[str] = []
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                cleaned_lines.append("")
                continue
            line = line.strip("-•*> ")
            line = re.sub(r"^\d+[\)\.:-]\s*", "", line)
            line = re.sub(r"(?i)^(bubble|panel|text|speech)\s*\d*\s*[:\-]\s*", "", line).strip()
            line = self._strip_metadata_from_line(line)
            cleaned_lines.append(line)
        
        bubbles: list[str] = []
        buffer: list[str] = []
        
        def _flush_buffer() -> None:
            if buffer:
                joined = " ".join(buffer).strip(" \"“”")
                if joined:
                    bubbles.append(joined)
                buffer.clear()
        
        for line in cleaned_lines:
            if not line:
                _flush_buffer()
                continue
            if line.startswith(("\"", "“")) and line.endswith(("\"", "”")) and len(line) > 1:
                _flush_buffer()
                bubbles.append(line.strip(" \"“”"))
                continue
            buffer.append(line)
            if line.endswith(tuple(".?!…\"”")):
                _flush_buffer()
        _flush_buffer()
        
        if not bubbles and content:
            bubbles = [content.strip()]
        return [text for text in bubbles if len(text) > 1]

    def _strip_metadata_from_line(self, line: str) -> str:
        if not line:
            return ""
        
        text_match = re.search(r"(?i)text\s*[:=]\s*(.+)", line)
        if text_match:
            candidate = text_match.group(1).strip()
            candidate = candidate.strip(" \"“”'")
            return candidate
        
        meta_fields = [
            "speaker gender",
            "speaker_gender",
            "gender",
            "speaker age",
            "speaker_age",
            "age",
            "bubble type",
            "bubble_type",
            "emotion",
            "tone",
        ]
        for field in meta_fields:
            pattern = (
                r"(?i)\b"
                + re.escape(field)
                + r"\b\s*(?:[:=\-]\s*)?(?:\"[^\"]*\"|'[^']*'|[A-Za-z ]+)"
            )
            line = re.sub(pattern, "", line)
        
        line = re.sub(r"\s{2,}", " ", line)
        return line.strip(" ,;:-\"“”'")

    def _strip_code_fences(self, content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 2:
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        return stripped

    def _looks_like_sfx(self, text: str) -> bool:
        if not text:
            return False
        cleaned = text.strip()
        if not cleaned:
            return False
        compact = cleaned.replace(" ", "")
        if len(compact) > 20:
            return False
        letters = [char for char in cleaned if char.isalpha()]
        if not letters:
            return False
        uppercase_ratio = sum(1 for char in letters if char.isupper()) / len(letters)
        keywords = {
            "boom",
            "bang",
            "pow",
            "wham",
            "slam",
            "crash",
            "clang",
            "clank",
            "snap",
            "whoosh",
            "thud",
            "zap",
            "kaboom",
            "zing",
        }
        tokens = [token for token in re.split(r"[^a-zA-Z]+", cleaned.lower()) if token]
        keyword_match = any(token in keywords for token in tokens)
        punctuation_heavy = bool(re.fullmatch(r"[A-Z0-9!?~\\-]+", compact))
        repeated_letters = bool(re.search(r"(.)\1{2,}", compact))
        return uppercase_ratio >= 0.7 and (keyword_match or punctuation_heavy or repeated_letters)

    def _infer_gender_from_text(self, text: str) -> str | None:
        """Heuristic gender detection from pronouns and honorifics."""
        padded = f" {text} "
        male_tokens = [
            " he ",
            " his ",
            " him ",
            " sir ",
            " lord ",
            " mr.",
            " brother ",
            " dad ",
            " father ",
            " king ",
            " dude ",
            " bro ",
            " man ",
        ]
        female_tokens = [
            " she ",
            " her ",
            " hers ",
            " ma'am",
            " lady ",
            " miss ",
            " mrs.",
            " sister ",
            " mom ",
            " mother ",
            " queen ",
            " girl ",
        ]
        if any(token in padded for token in male_tokens):
            return "male"
        if any(token in padded for token in female_tokens):
            return "female"
        return None

    def _encode_image(self, image) -> str:
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()

    def _segment_vertical_ranges(
        self, height: int, max_height: int = 1500, overlap: int = 1000
    ) -> list[tuple[int, int]]:
        """Split tall/scrolling pages into overlapping slices for better OCR.
        
        Very large overlap (1000px) ensures stacked bubbles near slice boundaries
        appear fully in at least one slice. Smaller max_height (1500px) keeps text
        larger and makes bubbles more likely to be fully contained in one segment.
        """
        if height <= max_height:
            return [(0, height)]

        # Ensure overlap doesn't exceed half the max height
        overlap = min(overlap, max_height // 2)
        step = max(400, max_height - overlap)

        ranges: list[tuple[int, int]] = []
        start = 0
        while start < height:
            end = min(height, start + max_height)
            ranges.append((start, end))
            if end >= height:
                break
            start = max(0, end - overlap)
        return ranges

    def _entry_signature(self, text: str, box: list[int]) -> tuple[str, int]:
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        center_y = (box[1] + box[3]) // 2
        bucket = center_y // 60
        return normalized, bucket

    def _approximate_bubble_boxes(
        self, count: int, width: int, height: int
    ) -> list[list[int]]:
        """When vision API doesn't return coordinates, approximate boxes in reading order."""
        if count <= 0:
            return []
        
        left_margin = int(width * 0.08)
        right_margin = int(width * 0.92)
        top_margin = int(height * 0.05)
        bottom_margin = int(height * 0.05)
        available_height = max(100, height - top_margin - bottom_margin)
        slot_height = max(140, int(available_height / max(1, count)))
        
        boxes: list[list[int]] = []
        for idx in range(count):
            top = top_margin + idx * slot_height
            bottom = top + slot_height - int(slot_height * 0.2)
            if bottom > height - bottom_margin:
                bottom = height - bottom_margin
            if bottom - top < 80:
                bottom = top + 80
            boxes.append(
                [
                    left_margin,
                    max(0, top),
                    right_margin,
                    min(height, bottom),
                ]
            )
        return boxes

    def _analyze_from_text(
        self,
        text: str,
        bubble_box: list[int],
        page_height: int | float | None,
    ) -> CharacterAnalysis:
        """Analyze text content to determine character type and emotion."""
        
        text_lower = text.lower()
        alpha_chars = [char for char in text if char.isalpha()]
        upper_ratio = (
            sum(1 for char in alpha_chars if char.isupper()) / max(1, len(alpha_chars))
        )
        
        # Detect emotion from text patterns
        emotion = "neutral"
        tone = "normal"
        stability = 0.5

        text_words = [word.strip("?!.,;:") for word in text_lower.split()]
        alpha_chars = [char for char in text if char.isalpha()]
        upper_ratio = (
            sum(1 for char in alpha_chars if char.isupper()) / max(1, len(alpha_chars))
        )
        
        # Question marks suggest confusion/uncertainty
        if "?" in text:
            if "...?" in text or "??" in text:
                emotion = "confused"
                tone = "questioning"
                stability = 0.3  # More expressive
            else:
                tone = "questioning"
                stability = 0.4
        
        # Exclamation marks suggest excitement/anger
        if "!" in text:
            if "!!" in text or "!!!" in text:
                emotion = "excited" if len(text) < 50 else "angry"
                tone = "dramatic"
                stability = 0.2  # Very expressive
            else:
                emotion = "assertive"
                tone = "emphatic"
                stability = 0.35
        
        # Ellipsis suggests thoughtfulness/uncertainty
        if "..." in text:
            emotion = "thoughtful"
            tone = "contemplative"
            stability = 0.4
        
        # Keyword patterns for voice selection
        system_keywords = ["you are now", "system", "quest", "mission", "objective", "status"]
        warrior_keywords = ["knight", "iron", "blood", "sword", "battle", "fight", "warrior", "soldier"]
        adult_male_keywords = ["sir", "captain", "commander", "master", "lord", "king"]
        young_male_keywords = ["bro", "dude", "hey", "yeah", "whoa"]
        child_keywords = ["mom", "mommy", "dad", "daddy", "scared", "wanna", "gonna"]
        elegant_keywords = ["grace", "beauty", "elegant", "lovely", "delicate"]
        wise_keywords = ["ancient", "wisdom", "elder", "sage", "experience"]

        voice_archetype = "narrator"
        
        # Check for system messages
        has_system_keywords = any(keyword in text_lower for keyword in system_keywords)
        has_warrior_keywords = any(keyword in text_lower for keyword in warrior_keywords)
        has_child_keywords = any(keyword in text_lower for keyword in child_keywords)
        
        # All-caps dialogue is common in manga, so only treat as system if it has system keywords
        is_system_message = has_system_keywords and not has_warrior_keywords

        # Determine age group and gender
        if is_system_message:
            voice_archetype = "system"
            stability = max(stability, 0.65)
        elif has_child_keywords:
            # Child voice - determine gender from other context
            if any(keyword in text_lower for keyword in ["boy", "son", "he", "him", "his"]):
                voice_archetype = "child_male"
            else:
                voice_archetype = "child_female"
            stability = 0.35  # Children are more expressive
        elif has_warrior_keywords or any(keyword in text_lower for keyword in adult_male_keywords):
            # Adult male voice for warriors/authority figures
            voice_archetype = "adult_male"
        elif any(keyword in text_lower for keyword in young_male_keywords):
            # Young male voice
            voice_archetype = "young_male"
        elif any(keyword in text_lower for keyword in wise_keywords + elegant_keywords):
            # Mature female voice for wise/elegant characters
            voice_archetype = "adult_female"
        elif len(text) < 30 and "?" in text:
            # Short questions often from younger characters
            voice_archetype = "young_female"
        else:
            # Default to young adult based on emotion
            if emotion in {"excited", "assertive"}:
                voice_archetype = "young_male"
            else:
                voice_archetype = "young_female"

        gender_hint = self._infer_gender_from_text(text_lower)
        if not is_system_message and gender_hint:
            if gender_hint == "male":
                if has_child_keywords:
                    voice_archetype = "child_male"
                elif has_warrior_keywords or len(text) > 70 or "sir" in text_lower:
                    voice_archetype = "adult_male"
                else:
                    voice_archetype = "young_male"
            elif gender_hint == "female":
                if has_child_keywords:
                    voice_archetype = "child_female"
                elif len(text) > 70 or "lady" in text_lower or "madam" in text_lower:
                    voice_archetype = "adult_female"
                else:
                    voice_archetype = "young_female"

        # If the bubble sits in the top ~15% of the page and looks like UI text, treat as system
        effective_height = (
            page_height
            if page_height and page_height > 0
            else (bubble_box[3] if len(bubble_box) > 3 else bubble_box[1] + 100)
        )
        top_ratio = bubble_box[1] / max(1.0, effective_height)
        if top_ratio <= 0.15 and len(text) > 15 and not has_warrior_keywords:
            voice_archetype = "system"
            stability = max(stability, 0.6)

        base_stability, similarity_boost, style = self._emotion_to_settings(emotion)
        if stability == 0.5:
            stability = base_stability
        else:
            stability = min(stability, base_stability)

        voice_id = self.VOICE_MAPPING.get(voice_archetype, "voice_narrator_f")
        
        print(
            f"🎭 Text Analysis: {emotion} ({tone}) → {voice_id} "
            f"[stability: {stability}, style: {style}]"
        )
        
        return CharacterAnalysis(
            character_type=voice_archetype,
            emotion=emotion,
            tone=tone,
            voice_suggestion=voice_id,
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
        )

    def _is_ocr_gibberish(self, text: str) -> bool:
        """Detect if OCR produced gibberish that needs vision API correction."""
        if not text or len(text) < 5:
            return True
        
        # Count how many characters are NOT letters/numbers/basic punctuation
        total_chars = len(text)
        junk_chars = sum(1 for char in text if char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ?!.,;:-'\"")
        junk_ratio = junk_chars / max(1, total_chars)
        
        # If more than 25% junk characters, it's probably gibberish
        if junk_ratio > 0.25:
            return True
        
        # Check for common OCR mistakes with UI text
        gibberish_patterns = ["\\", "|", "Ny ", "Sy.", "gl ag", "eo y"]
        if any(pattern in text for pattern in gibberish_patterns):
            return True
        
        return False

    def _read_with_vision(self, image_path: Path, bubble_box: list[int]) -> str:
        """Use the vision model to read text from a specific region."""
        if not settings.openai_api_key:
            print("⚠️ OpenAI API key not set, skipping vision API")
            return ""
        
        try:
            # Crop the image to the bubble region
            from PIL import Image
            image = Image.open(image_path)
            crop = image.crop((bubble_box[0], bubble_box[1], bubble_box[2], bubble_box[3]))
            
            # Convert to base64
            import io
            buffered = io.BytesIO()
            crop.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
            
            prompt = (
                "Read ONLY the text visible in this cropped bubble/panel. "
                "Return just the text (single line)."
            )
            text = self._call_openai(prompt, img_base64, max_tokens=150)
            if text:
                return text.replace("\n", " ").replace("  ", " ").strip()
            return ""
            
        except Exception as e:
            print(f"❌ Vision API failed: {type(e).__name__}: {str(e)}")
            return ""

    def _call_openai(self, prompt: str, img_base64: str, max_tokens: int = 500) -> str:
        if not settings.openai_api_key:
            return ""
        
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.VISION_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{img_base64}",
                        },
                    ],
                }
            ],
            "max_output_tokens": max_tokens,
        }

        last_error: Exception | None = None
        for attempt in range(4):
            response = requests.post(
                self.OPENAI_URL, headers=headers, json=payload, timeout=60
            )
            if response.status_code == 429:
                wait_time = 0.75 * (attempt + 1)
                print(
                    f"⚠️ Vision API rate limited (attempt {attempt + 1}/4). "
                    f"Retrying in {wait_time:.2f}s..."
                )
                time.sleep(wait_time)
                last_error = requests.HTTPError(response.text, response=response)
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                body = response.text if response is not None else ""
                print(
                    f"❌ Vision HTTPError "
                    f"{response.status_code if response else '??'}: {body[:500]}"
                )
                last_error = exc
                break

            data = response.json()
            return self._extract_openai_output(data)

        if last_error:
            raise last_error
        return ""

    def _extract_openai_output(self, payload: dict) -> str:
        if not payload:
            return ""
        
        outputs = payload.get("output") or []
        text_chunks: list[str] = []
        for message in outputs:
            contents = message.get("content") or []
            for item in contents:
                if item.get("type") in {"output_text", "text"}:
                    text = item.get("text")
                    if text:
                        text_chunks.append(text)
        # Some responses might nest text differently; fall back to usage field
        if not text_chunks and "usage" in payload:
            text = payload.get("usage", {}).get("output_text")
            if text:
                text_chunks.append(text)
        return "\n".join(chunk.strip() for chunk in text_chunks if chunk).strip()

    def _fallback_analysis(self) -> CharacterAnalysis:
        """Fallback when AI analysis isn't available."""
        return CharacterAnalysis(
            character_type="unknown",
            emotion="neutral",
            tone="normal",
            voice_suggestion="voice_narrator_f",
            stability=0.5,
            similarity_boost=0.75,
            style=0.2,
        )


vision_service = VisionService()

