# Inkami Server

FastAPI application + background worker that processes manga/manhwa chapters, runs OCR + speaker detection, and generates realistic TTS audio per bubble.

## Local Setup

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

Start worker:
```bash
poetry run rq worker inkami
```

Environment configuration lives in `.env` (see `.env.example`).

## Key Modules

- `app/api/routes`: HTTP endpoints used by the web client.
- `app/services`: detection, OCR, speaker linking, voice selection, TTS.
- `app/workers/tasks.py`: background job orchestration.
- `app/core`: config, storage helpers for S3/Supabase.

See `docs/pipeline.md` for the full flow and `docs/api-contract.md` for payloads.

