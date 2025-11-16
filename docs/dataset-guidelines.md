# Dataset Guidelines

## Target
- Vertical webtoon layouts first (mobile-friendly, top-to-bottom flow).
- Label 10–20 pages per update to iterate quickly.

## Classes
1. `panel`
2. `bubble_dialogue`
3. `bubble_narration`
4. `bubble_thought`
5. `bubble_sfx` (optional early on)
6. `character_face`

## Annotation Tips
- Panels: outline rectangular bounds even if gutters overlap.
- Bubbles: follow text area; include tails if needed for speaker linking.
- Narration boxes: rectangular boxes without tails.
- Thoughts: cloud shapes; label as separate class for softer voices.
- SFX: label but you can exclude from playback initially.

## File Format
- Store in COCO JSON or YOLO txt for YOLOv8 compatibility.
- Keep source page image paths relative to `datasets/bubble_samples/images`.

## QA Checklist
- Ensure every bubble has readable text (crop if blurry).
- Avoid mixing left-to-right manga for the first sprint.
- Balance male/female/neutral speaker bubbles for better voice mapping.
- Document tricky cases (vertical text, ruby annotations) for future heuristics.

