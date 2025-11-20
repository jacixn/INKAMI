# Project Brief

## Vision
Create **INKAMI**, a voice-driven manga/manhwa reader where users upload chapter bundles and get an automatically narrated, karaoke-style reading experience accessible on the web.

## Scope
- Accept image/PDF/ZIP uploads of chapters.
- Detect panels/bubbles, extract text, associate speakers, and synthesize dialogue audio.
- Provide a frontend to upload, monitor processing, and read/listen to completed chapters with synchronized highlighting.
- Offer corrective loops for manual speaker/voice adjustments.

## Success Criteria
- Smooth end-to-end flow from upload to playback for typical chapters.
- Responsive reader UI that works statically (GitHub Pages) but can call remote APIs.
- Modular backend pipeline ready for GPU-heavy inference and async workers.
- Clear telemetry/status so users trust the automation.

