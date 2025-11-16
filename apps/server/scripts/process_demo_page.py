"""Run the pipeline on a single demo page for debugging."""

from pathlib import Path

from app.services.detection import layout_detector
from app.services.ocr import ocr_service
from app.services.speaker import speaker_linker
from app.services.tts import tts_service


def main(image_path: str) -> None:
    path = Path(image_path)
    panels, bubbles = layout_detector.detect(path)
    print(f"Detected {len(panels)} panels, {len(bubbles)} bubbles")

    for bubble in bubbles:
        text = ocr_service.extract(path, bubble.box)
        speaker = speaker_linker.link(bubble.box, [])
        tts = tts_service.synthesize(text, voice_id="voice_friendly_f")
        print(
            f"{bubble.bubble_id}: speaker={speaker.speaker_id} chars={len(text)} audio={tts.audio_url}"
        )


if __name__ == "__main__":
    main("samples/demo_page.png")

