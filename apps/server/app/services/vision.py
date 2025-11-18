from __future__ import annotations

import base64
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
        
        if not settings.deepseek_api_key:
            print("⚠️ DeepSeek API key not set, using default voice selection")
            return self._fallback_analysis()

        try:
            # Read and encode the image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            # Create the prompt for DeepSeek
            prompt = f"""Analyze this manga/manhwa panel and the speech bubble containing: "{text}"

The speech bubble is located at coordinates: {bubble_box}

Provide a JSON response with:
1. character_type: Describe the character (e.g., "young_female", "tough_male", "wise_elder", "child", "villain")
2. emotion: Current emotion (e.g., "confused", "angry", "excited", "sad", "scared", "happy", "neutral", "worried")
3. tone: How they're speaking (e.g., "questioning", "assertive", "timid", "dramatic", "sarcastic", "whisper", "shout")
4. voice_archetype: Best voice match (choose from: "young_female_warm", "young_female_cool", "male_confident", "male_stoic", "androgynous_mysterious", "narrator")
5. expressiveness: How expressive should the voice be? (0.0-1.0, where 0.0 is very expressive/emotional, 1.0 is monotone/flat)

Only respond with valid JSON, no other text."""

            # Call DeepSeek API
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_data}"
                                    }
                                },
                                {
                                    "type": "text",
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30,
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Parse the AI response
            content = result["choices"][0]["message"]["content"]
            import json
            analysis = json.loads(content)
            
            # Map to our voice system
            voice_archetype = analysis.get("voice_archetype", "narrator")
            voice_id = self.VOICE_MAPPING.get(voice_archetype, "voice_narrator")
            
            # Convert expressiveness to stability (inverse relationship)
            expressiveness = float(analysis.get("expressiveness", 0.5))
            stability = expressiveness  # More expressive = lower stability
            
            print(f"🎭 AI Analysis: {analysis['character_type']} - {analysis['emotion']} ({analysis['tone']}) → {voice_id}")
            
            return CharacterAnalysis(
                character_type=analysis.get("character_type", "unknown"),
                emotion=analysis.get("emotion", "neutral"),
                tone=analysis.get("tone", "normal"),
                voice_suggestion=voice_id,
                stability=stability,
                similarity_boost=0.75,  # Default good value
            )

        except Exception as e:
            print(f"❌ Vision analysis failed: {type(e).__name__}: {str(e)}")
            return self._fallback_analysis()

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

