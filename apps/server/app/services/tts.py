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
        "voice_child_m": "FGY2WhTYpPnrIDTdsKH5",  # Daniel - young boy
        "voice_young_m": "yoZ06aMxZJJ28mfd3POQ",  # Adam - realistic heroic lead
        "voice_adult_m": "TxGEqnHWrfWFTfGW9XjX",  # Josh - mature deep voice
        
        # Special voices
        "voice_narrator": "EXAVITQu4vr4xnSDxMaL",  # Sarah - clear narrator
        "voice_system": "ErXwobaYiN019PkySvjV",  # Domi - neutral system voice
    }
    
    VOICE_DISPLAY_NAMES = {
        "voice_child_f": "Young Girl",
        "voice_young_f": "Young Woman",
        "voice_adult_f": "Mature Woman",
        "voice_child_m": "Young Boy",
        "voice_young_m": "Young Man",
        "voice_adult_m": "Mature Man",
        "voice_narrator": "Narrator",
        "voice_system": "System Voice",
    }
    
    ELEVEN_MODEL = "eleven_multilingual_v2"

    def synthesize(self, text: str, voice_id: str, stability: float = 0.5, similarity_boost: float = 0.75) -> TTSResult:
        print(f"🔊 TTS Request: text='{text[:50]}...' voice={voice_id} stability={stability}")
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
                    result = self._synthesize_elevenlabs(text, voice_id, stability, similarity_boost)
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

