from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict

from app.models.schemas import ChapterPayload, JobStatus, SpeakerUpdate


@dataclass
class ChapterStore:
    chapters: Dict[str, ChapterPayload] = field(default_factory=dict)
    jobs: Dict[str, JobStatus] = field(default_factory=dict)

    def create_job(self) -> JobStatus:
        job = JobStatus(
            job_id=str(uuid.uuid4()),
            status="queued",
            progress=0,
        )
        self.jobs[job.job_id] = job
        return job

    def update_job(self, job_id: str, **updates) -> JobStatus:
        job = self.jobs[job_id]
        for key, value in updates.items():
            setattr(job, key, value)
        self.jobs[job_id] = job
        return job

    def save_chapter(self, chapter: ChapterPayload) -> ChapterPayload:
        self.chapters[chapter.chapter_id] = chapter
        return chapter

    def get_chapter(self, chapter_id: str) -> ChapterPayload | None:
        return self.chapters.get(chapter_id)

    def get_job(self, job_id: str) -> JobStatus | None:
        return self.jobs.get(job_id)

    def update_speaker(self, speaker_id: str, patch: SpeakerUpdate) -> None:
        for chapter in self.chapters.values():
            for page in chapter.pages:
                for bubble in page.items:
                    if bubble.speaker_id == speaker_id:
                        if patch.display_name is not None:
                            bubble.speaker_name = patch.display_name
                        if patch.voice_id is not None:
                            bubble.voice_id = patch.voice_id


chapter_store = ChapterStore()

