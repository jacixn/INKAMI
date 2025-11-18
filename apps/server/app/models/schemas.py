from __future__ import annotations

from typing import Literal, Sequence

from pydantic import BaseModel, Field

BubbleType = Literal["dialogue", "narration", "thought", "sfx"]


class WordTime(BaseModel):
    word: str
    start: float
    end: float


class BubbleItem(BaseModel):
    bubble_id: str
    panel_box: Sequence[float]
    bubble_box: Sequence[float]
    type: BubbleType
    speaker_id: str
    speaker_name: str | None = None
    voice_id: str
    text: str
    audio_url: str
    word_times: list[WordTime] = Field(default_factory=list)


class PagePayload(BaseModel):
    page_index: int
    image_url: str
    width: int | None = None
    height: int | None = None
    items: list[BubbleItem]
    reading_order: list[str]


class ChapterPayload(BaseModel):
    chapter_id: str
    title: str | None = None
    status: Literal["processing", "ready", "failed"]
    progress: int = 0
    pages: list[PagePayload] = Field(default_factory=list)


class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "ready", "failed"]
    progress: int = 0
    chapter_id: str | None = None
    error: str | None = None


class SpeakerUpdate(BaseModel):
    speaker_id: str | None = None
    display_name: str | None = None
    voice_id: str | None = None

