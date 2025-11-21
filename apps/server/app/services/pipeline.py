from __future__ import annotations

import uuid
from redis import Redis

from app.core.config import settings
from app.models.schemas import ChapterPayload, JobStatus, SpeakerUpdate
from rq import Queue

from app.services.tts import tts_service


def _redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


class ChapterStore:
    def __init__(self) -> None:
        self.redis = _redis_client()
        self.chapter_key = "chapters"
        self.job_key = "jobs"
        self.queue = Queue(settings.job_queue_name, connection=self.redis)

    def create_job(self) -> JobStatus:
        job = JobStatus(job_id=str(uuid.uuid4()), status="queued", progress=0)
        self.redis.hset(self.job_key, job.job_id, job.model_dump_json())
        return job

    def update_job(self, job_id: str, **updates) -> JobStatus:
        payload = self.redis.hget(self.job_key, job_id)
        if payload is None:
            job = JobStatus(job_id=job_id, status="queued", progress=0)
        else:
            job = JobStatus.model_validate_json(payload)

        for key, value in updates.items():
            setattr(job, key, value)

        self.redis.hset(self.job_key, job.job_id, job.model_dump_json())
        return job

    def save_chapter(self, chapter: ChapterPayload) -> ChapterPayload:
        self.redis.hset(self.chapter_key, chapter.chapter_id, chapter.model_dump_json())
        return chapter

    def get_chapter(self, chapter_id: str) -> ChapterPayload | None:
        payload = self.redis.hget(self.chapter_key, chapter_id)
        if payload is None:
            return None
        return ChapterPayload.model_validate_json(payload)

    def get_job(self, job_id: str) -> JobStatus | None:
        payload = self.redis.hget(self.job_key, job_id)
        if payload is None:
            return None
        return JobStatus.model_validate_json(payload)

    def update_speaker(self, speaker_id: str, patch: SpeakerUpdate) -> None:
        for chapter_id, payload in self.redis.hscan_iter(self.chapter_key):
            chapter = ChapterPayload.model_validate_json(payload)
            updated = False
            for page in chapter.pages:
                for bubble in page.items:
                    if bubble.speaker_id != speaker_id:
                        continue
                    if patch.display_name is not None:
                        bubble.speaker_name = patch.display_name
                        updated = True
                    if patch.voice_id is not None:
                        bubble.voice_id = patch.voice_id
                        tts_result = tts_service.synthesize(bubble.text, bubble.voice_id)
                        bubble.audio_url = tts_result.audio_url
                        bubble.word_times = tts_result.word_times
                        updated = True
            if updated:
                self.redis.hset(self.chapter_key, chapter_id, chapter.model_dump_json())


chapter_store = ChapterStore()

