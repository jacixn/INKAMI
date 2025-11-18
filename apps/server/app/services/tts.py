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
        "voice_friendly_f": "21m00Tcm4TlvDq8ikWAM",  # Rachel
        "voice_cool_f": "AZnzlk1XvdvUeBnXmlld",  # Bella
        "voice_brash_m": "pNInz6obpgDQGcFmaJgB",  # Antoni
        "voice_stoic_m": "TxGEqnHWrfWFTfGW9XjX",  # Josh
        "voice_androgynous": "ErXwobaYiN019PkySvjV",  # Domi
        "voice_narrator": "EXAVITQu4vr4xnSDxMaL",  # Sarah
    }
    ELEVEN_MODEL = "eleven_multilingual_v2"

    def synthesize(self, text: str, voice_id: str, stability: float = 0.5, similarity_boost: float = 0.75) -> TTSResult:
        provider_chain = [
            provider.strip()
            for provider in settings.tts_provider_priority.split(",")
            if provider.strip()
        ]
        for provider in provider_chain:
            if provider == "elevenlabs" and settings.elevenlabs_api_key:
                try:
                    return self._synthesize_elevenlabs(text, voice_id, stability, similarity_boost)
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

    def _synthesize_elevenlabs(self, text: str, voice_id: str, stability: float = 0.5, similarity_boost: float = 0.75) -> TTSResult:
        resolved_voice = self.ELEVEN_VOICE_MAP.get(voice_id, self.ELEVEN_VOICE_MAP["voice_narrator"])
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{resolved_voice}"
        headers = {
            "xi-api-key": settings.elevenlabs_api_key or "",
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self.ELEVEN_MODEL,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": 0.0,  # Use default style
                "use_speaker_boost": True  # Enhance voice clarity
            },
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

