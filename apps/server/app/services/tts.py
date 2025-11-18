from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List
from uuid import uuid4

import requests
import time

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
        
        # Narrators
        "voice_narrator_f": "EXAVITQu4vr4xnSDxMaL",  # Sarah - cinematic female narrator
        "voice_narrator_m": "VR6AewLTigWG4xSOukaG",  # Tom - rich male narrator

        # Backwards compatibility alias (legacy narrator id)
        "voice_narrator": "EXAVITQu4vr4xnSDxMaL",
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
        "voice_narrator_f": "Narrator • Female",
        "voice_narrator_m": "Narrator • Male",
        "voice_narrator": "Narrator • Legacy",
        "voice_system": "System Voice",
        "voice_sfx": "FX Voice",
    }
    
    ELEVEN_MODEL = "eleven_multilingual_v2"
    OPENAI_TTS_MODEL = "gpt-4o-mini-tts"

    OPENAI_VOICE_MAP = {
        "voice_child_f": "luna",
        "voice_young_f": "sol",
        "voice_adult_f": "verse",
        "voice_child_m": "ember",
        "voice_young_m": "alloy",
        "voice_adult_m": "sage",
        "voice_narrator_f": "verse",
        "voice_narrator_m": "sage",
        "voice_narrator": "verse",
        "voice_system": "ash",
        "voice_sfx": "ballad",
    }

    VOICE_SETTINGS_OVERRIDES = {
        "voice_narrator_f": {
            "stability": 0.72,
            "similarity_boost": 0.8,
            "style": 0.35,
            "use_speaker_boost": True,
        },
        "voice_narrator_m": {
            "stability": 0.75,
            "similarity_boost": 0.82,
            "style": 0.3,
            "use_speaker_boost": True,
        },
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
            if provider == "openai" and settings.openai_api_key:
                try:
                    print("🎤 Attempting OpenAI TTS synthesis...")
                    result = self._synthesize_openai(text, voice_id)
                    print(f"✅ OpenAI TTS SUCCESS! Audio URL: {result.audio_url[:100]}")
                    return result
                except Exception as e:
                    print(f"❌ OpenAI TTS failed: {type(e).__name__}: {str(e)}")
                    continue
        if settings.openai_api_key:
            print(
                f"⚠️ Provider chain exhausted; forcing OpenAI TTS for: {text[:50]}..."
            )
            try:
                result = self._synthesize_openai(text, voice_id)
                print(
                    f"✅ OpenAI forced fallback SUCCESS! Audio URL: {result.audio_url[:100]}"
                )
                return result
            except Exception as e:
                print(f"❌ OpenAI forced fallback failed: {type(e).__name__}: {str(e)}")
                raise
        print(
            f"❌ No TTS providers succeeded and no OpenAI key configured for: {text[:50]}..."
        )
        raise RuntimeError("No TTS providers available")

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
        resolved_voice = self.ELEVEN_VOICE_MAP.get(voice_id, self.ELEVEN_VOICE_MAP["voice_narrator_f"])
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{resolved_voice}"
        api_key = (settings.elevenlabs_api_key or "").strip()
        headers = {
            "xi-api-key": api_key,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        if not api_key:
            raise RuntimeError("ElevenLabs API key missing")
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
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = response.text if response is not None else ""
            print(
                f"❌ ElevenLabs HTTPError "
                f"{response.status_code if response else '??'}: {body[:500]}"
            )
            raise exc
        audio_bytes = response.content
        key = f"tts/{voice_id}/{uuid4().hex}.mp3"
        audio_url = storage_client.put_bytes(key, audio_bytes, "audio/mpeg")
        return TTSResult(audio_url=audio_url, word_times=self._approximate_word_times(text))

    def _synthesize_openai(self, text: str, voice_id: str) -> TTSResult:
        api_key = (settings.openai_api_key or "").strip()
        if not api_key:
            raise RuntimeError("OpenAI API key missing")
        voice = self.OPENAI_VOICE_MAP.get(voice_id, "alloy")
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.OPENAI_TTS_MODEL,
            "voice": voice,
            "input": text,
            "format": "mp3",
        }
        last_error: Exception | None = None
        for attempt in range(5):
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 429:
                wait_time = min(2.0, 0.4 * (attempt + 1))
                body = response.text if response is not None else ""
                print(
                    f"⚠️ OpenAI TTS rate limited (attempt {attempt + 1}/5). "
                    f"Waiting {wait_time:.2f}s. Response: {body[:160]}"
                )
                last_error = requests.HTTPError(body, response=response)
                time.sleep(wait_time)
                continue
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                body = response.text if response is not None else ""
                print(
                    f"❌ OpenAI HTTPError "
                    f"{response.status_code if response else '??'}: {body[:500]}"
                )
                last_error = exc
                break

            audio_bytes = response.content
            break
        else:
            if last_error:
                raise last_error
            raise RuntimeError("OpenAI TTS gave no response")

        key = f"tts_openai/{voice_id}/{uuid4().hex}.mp3"
        audio_url = storage_client.put_bytes(key, audio_bytes, "audio/mpeg")
        return TTSResult(audio_url=audio_url, word_times=self._approximate_word_times(text))

    def _fallback_tts(self, text: str, voice_id: str) -> TTSResult:
        # Return an empty audio URL so the frontend falls back to Web Speech API with the actual text
        return TTSResult(audio_url="", word_times=self._approximate_word_times(text))


tts_service = TTSService()

