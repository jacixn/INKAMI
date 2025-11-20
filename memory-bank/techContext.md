# Tech Context

## Frontend
- Next.js 14 App Router (React 18, TypeScript).
- Tailwind CSS + custom gradients/background components.
- Audio playback managed via custom hooks (`usePlaybackController`) and `<audio>` elements.
- Deployed statically to GitHub Pages via workflow `.github/workflows/deploy-web.yml`.

## Backend
- FastAPI with Pydantic schemas, served via Uvicorn.
- Worker pipeline uses Redis/RQ (or compatible) for async jobs.
- Computer vision stack leverages YOLO/Detectron2, PaddleOCR, ElevenLabs/Deepsick TTS (see `apps/server/app/services`).
- Deployed to Fly.io with `fly.toml` orchestrating API + worker processes.

## Storage & Infra
- Object storage abstraction (`app/core/storage.py`) for chapters + audio assets.
- Postgres for metadata, Redis for queues/cache.
- Docker Compose under `infrastructure/dev` for local stack.

## Tooling
- Node/npm for frontend, Poetry for backend dependencies.
- Shared schema package to keep TS/Python contracts synchronized.

