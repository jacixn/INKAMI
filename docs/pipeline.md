# Pipeline Overview

1. **Upload** – chapter archive hits `/api/chapters`. Files are persisted to object storage and a job is queued.
2. **Layout detection** – YOLOv8/Detectron2 finds panels, speech bubbles, narration boxes, thought bubbles, SFX.
3. **OCR** – PaddleOCR (latin, later JP/KR packs) extracts text per bubble, cleaning hyphenation + punctuation.
4. **Classification** – heuristics or lightweight CNN infers bubble type (dialogue/narration/thought/SFX). SFX can be skipped initially.
5. **Speaker linking** – bubble tails + nearest face boxes (RetinaFace/MediaPipe). Maintain short-term embedding memory to keep IDs consistent.
6. **Voice registry** – new speaker IDs grab the next available archetype voice. Narrator defaults to dedicated voice.
7. **TTS + alignment** – call ElevenLabs/Deepsick for neural audio. If provider lacks timestamps, run forced alignment and store word timings.
8. **Playback packaging** – return JSON with ordered bubble metadata + signed audio URLs. Cache in Postgres/S3 for later replays.

## Background Worker Responsibilities

- Handle large images and long-running inference without blocking HTTP threads.
- Batch requests page-by-page to reuse GPU context.
- Prefetch next page audio while current page is playing.
- Persist debug artifacts (panel masks, bubble crops) for correction UI.

## Correction Loop

1. User taps bubble → selects correct speaker/voice.
2. PATCH `/api/bubbles/{speaker_id}` updates registry.
3. Re-run TTS for affected speaker asynchronously; reader gets new signed audio URL.

## Privacy Notes

- Only process chapters users upload & own.
- Expose toggle to delete raw images once audio finishes.
- Keep logs scrubbed of text content unless user opts in for analytics.

