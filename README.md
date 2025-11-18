# INKAMI

Voice-driven manga & manhwa reader that processes uploaded chapters, understands speakers, and narrates each bubble with realistic voices.

## Monorepo Layout

- `apps/web`: Next.js web client (upload wizard, processing status, reader UI)
- `apps/server`: FastAPI backend + worker pipeline
- `packages/layout-model`: training assets for panel/bubble detector
- `packages/shared-schemas`: shared TypeScript/Pydantic contracts
- `packages/datasets/bubble_samples`: starter labelled dataset description
- `docs`: architecture notes, API contracts, dataset guidelines
- `infrastructure`: local docker-compose + future infra configs
- `supabase`: SQL migrations for metadata store

## Quickstart

1. **Frontend**
   ```bash
   cd apps/web
   npm install
   npm run dev
   ```
2. **Backend**
   ```bash
   cd apps/server
   poetry install
   poetry run uvicorn app.main:app --reload
   ```
3. **Workers + Infra**
   ```bash
   cd infrastructure/dev
   docker compose up
   ```

## High-Level Flow

1. User uploads a chapter (ZIP/PDF/jpg bundle).
2. Backend splits pages, detects panels/bubbles, runs OCR, classifies bubble type.
3. Bubble is linked to a speaker and assigned a voice archetype.
4. Neural TTS (11Labs, Azure, or fallback) generates per-bubble audio + word timings.
5. Frontend polls processing status, then renders reader canvas with karaoke highlighting.

See `docs/pipeline.md` and `docs/api-contract.md` for deeper details.

## Deploying the Web App on GitHub Pages

1. Create a GitHub repo under your account (e.g. `jacixn/inkami`) and push this workspace.
2. In the repo settings → Pages, choose “GitHub Actions” as the source.
3. Add a repository secret named `PUBLIC_API_URL` pointing to your deployed FastAPI backend (Render/Fly/etc). Without a backend, the reader and status views will stay in their placeholder states because no real chapters exist to stream.
4. The included workflow `.github/workflows/deploy-web.yml` runs on every push to `main`, builds `apps/web` with `next export`, and deploys the static files to Pages.
5. Your site will be available at `https://<username>.github.io/<repo>/` (or `https://<username>.github.io` if the repo itself is `<username>.github.io`).

For local previews, run `npm run dev:web`. For the production static build the workflow automatically injects the correct base path so assets resolve on GitHub Pages.

## Deploying the FastAPI backend on Fly.io

1. **Install Fly tooling**
   ```bash
   curl -L https://fly.io/install.sh | sh
   fly auth login
   ```
2. **Launch from `apps/server`**
   ```bash
   cd apps/server
   fly launch --no-deploy
   ```
   The generated app name should match the `app` field in `fly.toml` (default `inkami-api`). Adjust `primary_region` if needed.
3. **Provision backing services**
   ```bash
   fly postgres create --name inkami-db
   fly redis create --name inkami-redis
   ```
   Capture the connection strings and inject them as secrets:
   ```bash
   fly secrets set \
     DATABASE_URL="postgresql+asyncpg://..." \
     REDIS_URL="redis://..." \
     S3_ENDPOINT="https://<your-storage>" \
     S3_BUCKET="inkami" \
     S3_ACCESS_KEY="..." \
     S3_SECRET_KEY="..." \
     ELEVENLABS_API_KEY="..." \
     DEEPSICK_API_KEY="..." \
     FRONTEND_URL="https://jacixn.github.io/INKAMI"
   ```
   (Add any other env vars from `apps/server/.env.example`.)
4. **Deploy**
   ```bash
   fly deploy
   ```
   This uses the included `Dockerfile` and runs both the API (`processes.web`) and the RQ worker (`processes.worker`).
5. **Update the frontend**
   - Copy the Fly app URL (e.g., `https://inkami-api.fly.dev`) into the GitHub secret `PUBLIC_API_URL`.
   - Re-run the “Deploy Web to GitHub Pages” workflow so the static site points at the new backend.

Fly automatically exposes the API over HTTPS, restarts machines if they crash, and can scale horizontally later via `fly scale count`.

