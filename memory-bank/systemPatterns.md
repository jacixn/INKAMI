# System Patterns

## Architecture
- **Monorepo** with `apps/web` (Next.js App Router) and `apps/server` (FastAPI + RQ workers).
- Frontend is mostly static-exportable; dynamic data fetched from `PUBLIC_API_URL`.
- Backend exposes REST endpoints for chapters, jobs, bubbles; heavy lifting delegated to workers.

## Data Flow
1. Upload hits FastAPI, stored via object storage abstraction.
2. Worker pipeline performs layout detection → OCR → classification → speaker linking → TTS.
3. Processed metadata/audio URLs stored in Postgres/S3 and surfaced through `/api/chapters` responses.
4. Frontend polls job status, then renders pages with audio playback + highlighting controlled by hooks like `usePlaybackController`.

## UI Patterns
- Reusable shell (`AppShell` + persistent `BottomNav`) coordinates navigation states; the previous breadcrumb-style `TopBar` has been removed per UX update.
- Tailwind CSS for styling; gradient/aurora backgrounds for immersive feel.
- Playback components (e.g., `ImmersiveReader`, `PlaybackControls`) consume typed data from `apps/web/lib/types.ts`.

## Backend Patterns
- Services organized under `apps/server/app/services/*` for modular vision/OCR/TTS steps.
- Worker tasks defined in `workers/tasks.py`, triggered via job queue.
- Schemas maintained in both Python (Pydantic) and TS (shared types) for parity.

