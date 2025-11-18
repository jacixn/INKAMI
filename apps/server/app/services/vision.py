from __future__ import annotations

import base64
import json
import re
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
        "narrator": "voice_narrator",
        "system": "voice_system",
    }

    def detect_and_read_all_bubbles(self, image_path: Path) -> list[tuple[list[int], str, CharacterAnalysis]]:
        """Use AI vision to find ALL text bubbles and read them in one go."""
        
        if not settings.openai_api_key:
            print("⚠️ OpenAI API key not set")
            return []
        
        try:
            # Load and encode the FULL image
            from PIL import Image
            image = Image.open(image_path)
            
            import io
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
            
            prompt = (
                "Extract EVERY readable text from this entire manga page. "
                "Include speech bubbles, narration boxes, UI panels, glowing screens, "
                "sound effects, and any stylized text. Return the text in reading order "
                "(top-to-bottom, left-to-right). Use either JSON "
                '([{\"text\":\"...\"}, ...]) or bullet lines starting with TEXT:. '
                "Do not add commentary."
            )
            
            print("🤖 Calling GPT-4o-mini to detect and read ALL bubbles")
            content = self._call_openai(prompt, img_base64, max_tokens=700)
            if not content:
                print("⚠️ Vision API returned no text")
                return []
            print(f"📝 Vision API response:\n{content}")
            
            texts = self._parse_detected_texts(content)
            if not texts:
                print("⚠️ Could not parse any text entries from vision response")
                return []
            
            width, height = image.size
            boxes = self._approximate_bubble_boxes(len(texts), width, height)
            
            bubbles: list[tuple[list[int], str, CharacterAnalysis]] = []
            for idx, text in enumerate(texts):
                bubble_box = boxes[idx] if idx < len(boxes) else [80, 80, width - 80, height - 80]
                analysis = self._analyze_from_text(text, bubble_box, height)
                bubbles.append((bubble_box, text, analysis))
                print(f"✨ Vision detected text #{idx + 1}: {text[:60]}")
            
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
            
            # Convert to base64
            import io
            buffered = io.BytesIO()
            crop.save(buffered, format="PNG")
            img_bytes = buffered.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
            
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

    def _parse_detected_texts(self, content: str) -> list[str]:
        """Parse multi-bubble output from the vision API into clean text strings."""
        if not content:
            return []
        
        content = content.strip()
        if not content:
            return []
        
        # Try JSON decoding first (if the model followed instructions)
        try:
            parsed = json.loads(content)
            json_texts = self._extract_texts_from_structure(parsed)
            if json_texts:
                return json_texts
        except json.JSONDecodeError:
            pass
        
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

    def _extract_texts_from_structure(self, data) -> list[str]:
        """Recursively extract text fields from a JSON-like structure."""
        texts: list[str] = []
        if isinstance(data, str):
            cleaned = data.strip()
            if cleaned:
                texts.append(cleaned)
        elif isinstance(data, dict):
            if "text" in data:
                value = data["text"]
                if isinstance(value, (str, int, float)):
                    cleaned = str(value).strip()
                    if cleaned:
                        texts.append(cleaned)
            # Support keys like "bubbles" or "items"
            for value in data.values():
                texts.extend(self._extract_texts_from_structure(value))
        elif isinstance(data, list):
            for item in data:
                texts.extend(self._extract_texts_from_structure(item))
        return texts

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

        # If the bubble sits in the top ~15% of the page and looks like UI text, treat as system
        effective_height = page_height if page_height and page_height > 0 else (bubble_box[3] if len(bubble_box) > 3 else bubble_box[1] + 100)
        top_ratio = bubble_box[1] / max(1.0, effective_height)
        if top_ratio <= 0.15 and len(text) > 15 and not has_warrior_keywords:
            voice_archetype = "system"
            stability = max(stability, 0.6)

        voice_id = self.VOICE_MAPPING.get(voice_archetype, "voice_narrator")
        
        print(f"🎭 Text Analysis: {emotion} ({tone}) → {voice_id} [stability: {stability}]")
        
        return CharacterAnalysis(
            character_type="analyzed_from_text",
            emotion=emotion,
            tone=tone,
            voice_suggestion=voice_id,
            stability=stability,
            similarity_boost=0.75,
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
        
        response = requests.post(self.OPENAI_URL, headers=headers, json=payload, timeout=60)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = response.text if response is not None else ""
            print(f"❌ Vision HTTPError {response.status_code if response else '??'}: {body[:500]}")
            raise exc
        
        data = response.json()
        return self._extract_openai_output(data)

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
            voice_suggestion="voice_narrator",
            stability=0.5,
            similarity_boost=0.75,
        )


vision_service = VisionService()

