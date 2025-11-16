# Bubble Samples

Starter set of labelled webtoon pages to bootstrap the detector.

- `images/` – add raw PNG/JPEG pages here.
- `labels/` – YOLO txt annotations with the same file names.
- `metadata.json` – optional manifest describing source, language, notes.

Use this directory as the seed dataset when iterating on the YOLOv8 layout model. Fill it with at least 10 curated pages (varied bubble types, multiple speakers). Document edge cases in `metadata.json` so future contributors understand special formatting in that chapter.

