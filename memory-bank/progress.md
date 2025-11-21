# Progress

## Working
- Upload wizard, processing status view, and immersive reader exist with placeholder/demo data.
- Backend pipeline files implemented (vision, OCR, TTS, workers) though may need infra resources to run.
- Shared types/hooks keep playback in sync.
- Bottom navigation now ordered `Home → Upload → Status → Listen`; breadcrumb header removed.
- Fly backend now whitelists the GitHub Pages origin + dev hosts so uploads no longer fail CORS preflight.

## Outstanding
- Future: correction UI, richer analytics, deletion toggles per pipeline notes.
- Need consistent deployment of backend services + secrets.

## Risks
- Audio pipeline depends on external APIs (11Labs, Deepsick) and GPU inference; ensure fallbacks in dev.
- Static deployment (GitHub Pages) means all API URLs must be absolute + CORS-friendly.

