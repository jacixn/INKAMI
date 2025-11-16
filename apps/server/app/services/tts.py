from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Sequence

from app.core.config import settings
from app.core.storage import storage_client


@dataclass
class TTSResult:
    audio_url: str
    word_times: List[dict[str, float | str]]


class TTSService:
    def synthesize(self, text: str, voice_id: str) -> TTSResult:
        provider_chain = settings.tts_provider_priority.split(",")
        provider = provider_chain[0]
        # TODO: integrate real TTS providers (11Labs/Deepsick/Azure/Google)
        fake_audio = text.encode("utf-8")[:8]
        key = f"tts/{voice_id}/{random.randint(1000,9999)}.mp3"
        audio_url = storage_client.put_bytes(key, fake_audio, "audio/mpeg")
        words = text.split()
        word_times = []
        cursor = 0.0
        for word in words:
            duration = max(0.2, len(word) * 0.03)
            word_times.append({"word": word, "start": cursor, "end": cursor + duration})
            cursor += duration
        return TTSResult(audio_url=audio_url, word_times=word_times)


tts_service = TTSService()

