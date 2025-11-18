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

