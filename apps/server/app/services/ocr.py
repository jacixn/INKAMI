from __future__ import annotations

from pathlib import Path
from typing import Sequence


class OCRService:
    def extract(self, image_path: Path, box: Sequence[float]) -> str:
        # TODO: crop bubble + call PaddleOCR
        return "Placeholder bubble transcription."


ocr_service = OCRService()

