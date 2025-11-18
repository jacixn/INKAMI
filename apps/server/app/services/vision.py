from __future__ import annotations

import base64
import json
import random
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

    VOICE_MAPPING = {
        "young_female_warm": "voice_friendly_f",
        "young_female_cool": "voice_cool_f",
        "male_confident": "voice_brash_m",
        "male_stoic": "voice_stoic_m",
        "androgynous_mysterious": "voice_androgynous",
        "narrator": "voice_narrator",
    }

    def analyze_bubble(
        self,
        image_path: Path,
        text: str,
        bubble_box: list[int],
        page_height: int | float | None = None,
    ) -> CharacterAnalysis:
        """Analyze a speech bubble and determine character emotion and voice."""
        
        # For now, use smart text analysis to determine emotion and voice
        # This is a temporary solution until we get vision API working properly
        return self._analyze_from_text(text, bubble_box, page_height)

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
        
        system_keywords = ["you are now", "system", "quest", "mission", "objective", "status"]
        male_keywords = ["knight", "iron", "blood", "sword", "bro", "dude", "sir", "captain", "hero"]
        calm_keywords = ["calculate", "observe", "analysis", "strategy", "precisely"]
        warm_keywords = ["please", "sorry", "hope", "wish", "feel", "thank"]

        voice_archetype = "narrator"
        # Check for system messages - but male keywords override system detection
        has_system_keywords = any(keyword in text_lower for keyword in system_keywords)
        has_male_keywords = any(keyword in text_lower for keyword in male_keywords)
        
        # All-caps dialogue is common in manga, so check for actual system keywords
        is_system_message = has_system_keywords or (upper_ratio > 0.85 and not has_male_keywords and len(text) < 50)

        if has_male_keywords:
            # Male character dialogue takes priority
            # Use male_stoic for questioning/thoughtful, male_confident for assertions
            voice_archetype = "male_stoic" if emotion in {"thoughtful", "confused"} else "male_confident"
        elif is_system_message:
            voice_archetype = "narrator"
            stability = max(stability, 0.65)
        elif any(keyword in text_lower for keyword in calm_keywords):
            voice_archetype = "young_female_cool"
        elif any(keyword in text_lower for keyword in warm_keywords):
            voice_archetype = "young_female_warm"
        else:
            # Alternate based on punctuation: questions lean warm heroine, otherwise stoic mentor.
            voice_archetype = "young_female_warm" if "?" in text else "male_stoic"

        # If the bubble sits in the top ~15% of the page and looks like UI text, treat as narrator/system.
        effective_height = page_height if page_height and page_height > 0 else (bubble_box[3] if len(bubble_box) > 3 else bubble_box[1] + 100)
        top_ratio = bubble_box[1] / max(1.0, effective_height)
        if top_ratio <= 0.15 and len(text) > 15:
            voice_archetype = "narrator"
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

