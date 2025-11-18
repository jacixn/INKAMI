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

    def analyze_bubble(self, image_path: Path, text: str, bubble_box: list[int]) -> CharacterAnalysis:
        """Analyze a speech bubble and determine character emotion and voice."""
        
        # For now, use smart text analysis to determine emotion and voice
        # This is a temporary solution until we get vision API working properly
        return self._analyze_from_text(text, bubble_box)

    def _analyze_from_text(self, text: str, bubble_box: list[int]) -> CharacterAnalysis:
        """Analyze text content to determine character type and emotion."""
        
        text_lower = text.lower()
        
        # Detect emotion from text patterns
        emotion = "neutral"
        tone = "normal"
        stability = 0.5
        
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
        
        # Detect character type from speech patterns
        voice_archetype = "narrator"
        
        # Short, questioning text often suggests younger character
        if len(text) < 100 and "?" in text:
            voice_archetype = "young_female_warm"
        # Authoritative statements suggest confident character
        elif any(word in text_lower for word in ["must", "will", "shall", "command"]):
            voice_archetype = "male_confident"
        # Gentle or emotional words suggest warm character
        elif any(word in text_lower for word in ["please", "sorry", "hope", "wish", "feel"]):
            voice_archetype = "young_female_warm"
        # Cool analytical words
        elif any(word in text_lower for word in ["analyze", "observe", "calculate", "precisely"]):
            voice_archetype = "young_female_cool"
        
        # Position can hint at character type (top = narrator, middle = dialogue)
        if bubble_box[1] < 200:  # Near top
            voice_archetype = "narrator"
            stability = 0.6  # More stable for narration
        
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

