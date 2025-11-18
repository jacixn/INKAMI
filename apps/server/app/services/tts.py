from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List
from uuid import uuid4

import requests

from app.core.config import settings
from app.core.storage import storage_client
from app.models.schemas import WordTime


@dataclass
class TTSResult:
    audio_url: str
    word_times: List[WordTime]


class TTSService:
    ELEVEN_VOICE_MAP = {
        # Female voices (child → young → adult)
        "voice_child_f": "jBpfuIE2acCO8z3wKNLl",  # Charlotte - child/young girl
        "voice_young_f": "21m00Tcm4TlvDq8ikWAM",  # Rachel - friendly young woman
        "voice_adult_f": "AZnzlk1XvdvUeBnXmlld",  # Bella - mature woman
        
        # Male voices (child → young → adult)
        "voice_child_m": "SOYHLrjzK2X1ezoPC6cr",  # Harry - natural middle-school boy
        "voice_young_m": "yoZ06aMxZJJ28mfd3POQ",  # Adam - realistic heroic lead
        "voice_adult_m": "TxGEqnHWrfWFTfGW9XjX",  # Josh - mature deep voice
        
        # Special voices
        "voice_narrator": "EXAVITQu4vr4xnSDxMaL",  # Sarah - clear narrator (female)
        "voice_narrator_male": "ErXwobaYiN019PkySvjV",  # Antoni - friendly male narrator
        "voice_system": "CwhRBWXzGAHq8TQ4Fs17",  # Roger - calm, precise system tone
        "voice_sfx": "N2lVS1w4EtoT3dr4eOWO",  # Callum - punchy FX cues
    }
    
    VOICE_DISPLAY_NAMES = {
        "voice_child_f": "Young Girl",
        "voice_young_f": "Young Woman",
        "voice_adult_f": "Mature Woman",
        "voice_child_m": "Young Boy",
        "voice_young_m": "Young Man",
        "voice_adult_m": "Mature Man",
        "voice_narrator": "Narrator (Female)",
        "voice_narrator_male": "Narrator (Male)",
        "voice_system": "System Voice",
        "voice_sfx": "FX Voice",
    }
    
    ELEVEN_MODEL = "eleven_multilingual_v2"
    
    VOICE_SETTINGS_OVERRIDES = {
        "voice_system": {
            "stability": 0.92,
            "similarity_boost": 0.25,
            "style": 0.4,
            "use_speaker_boost": False,
        },
        "voice_sfx": {
            "stability": 0.3,
            "similarity_boost": 0.9,
            "style": 0.75,
            "use_speaker_boost": True,
        },
    }

    def synthesize(
        self,
        text: str,
        voice_id: str,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float | None = None,
    ) -> TTSResult:
        print(
            f"🔊 TTS Request: text='{text[:50]}...' voice={voice_id} "
            f"stability={stability} style={style if style is not None else 'default'}"
        )
        provider_chain = [
            provider.strip()
            for provider in settings.tts_provider_priority.split(",")
            if provider.strip()
        ]
        print(f"📋 Provider chain: {provider_chain}, ElevenLabs key set: {bool(settings.elevenlabs_api_key)}")
        
        for provider in provider_chain:
            if provider == "elevenlabs" and settings.elevenlabs_api_key:
                try:
                    print(f"🎤 Attempting ElevenLabs synthesis...")
                    result = self._synthesize_elevenlabs(
                        text, voice_id, stability, similarity_boost, style
                    )
                    print(f"✅ ElevenLabs SUCCESS! Audio URL: {result.audio_url[:100]}")
                    return result
                except Exception as e:
                    print(f"❌ ElevenLabs TTS failed: {type(e).__name__}: {str(e)}")
                    continue
        print(f"⚠️ All TTS providers failed, using fallback for: {text[:50]}...")
        return self._fallback_tts(text, voice_id)

    def _approximate_word_times(self, text: str) -> List[WordTime]:
        words = text.split()
        cursor = 0.0
        payload: List[WordTime] = []
        for word in words:
            duration = max(0.25, len(word) * 0.04)
            payload.append(WordTime(word=word, start=cursor, end=cursor + duration))
            cursor += duration
        return payload

    def _synthesize_elevenlabs(
        self,
        text: str,
        voice_id: str,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float | None = None,
    ) -> TTSResult:
        resolved_voice = self.ELEVEN_VOICE_MAP.get(voice_id, self.ELEVEN_VOICE_MAP["voice_narrator"])
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{resolved_voice}"
        headers = {
            "xi-api-key": settings.elevenlabs_api_key or "",
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        voice_settings = {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": 0.0,
            "use_speaker_boost": True,
        }
        override = self.VOICE_SETTINGS_OVERRIDES.get(voice_id)
        if override:
            voice_settings.update(override)
        if style is not None and voice_id not in self.VOICE_SETTINGS_OVERRIDES:
            voice_settings["style"] = max(0.0, min(1.0, style))
        
        payload = {
            "text": text,
            "model_id": self.ELEVEN_MODEL,
            "voice_settings": voice_settings,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        audio_bytes = response.content
        key = f"tts/{voice_id}/{uuid4().hex}.mp3"
        audio_url = storage_client.put_bytes(key, audio_bytes, "audio/mpeg")
        return TTSResult(audio_url=audio_url, word_times=self._approximate_word_times(text))

    def _fallback_tts(self, text: str, voice_id: str) -> TTSResult:
        # Return an empty audio URL so the frontend falls back to Web Speech API with the actual text
        return TTSResult(audio_url="", word_times=self._approximate_word_times(text))


tts_service = TTSService()

