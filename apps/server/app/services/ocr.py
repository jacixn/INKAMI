from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

from PIL import Image
import pytesseract
from pytesseract import Output

from app.models.schemas import BubbleType


@dataclass
class DetectedBubble:
    bubble_id: str
    box: Sequence[float]
    text: str
    kind: BubbleType
    speaker_name: str | None = None
    voice_hint: str | None = None


class OCRService:
    def extract(self, image_path: Path, box: Sequence[float]) -> str:
        image = Image.open(image_path).convert("RGB")
        crop = image.crop((box[0], box[1], box[2], box[3]))
        return pytesseract.image_to_string(crop, config="--psm 6").strip()

    def detect_bubbles(self, image_path: Path, conf_threshold: int = 55) -> List[DetectedBubble]:
        image = Image.open(image_path).convert("RGB")
        data = pytesseract.image_to_data(image, output_type=Output.DICT)
        groups: dict[tuple[int, int], list[dict[str, int | str]]] = defaultdict(list)
        count = len(data["text"])
        for idx in range(count):
            text = (data["text"][idx] or "").strip()
            if not text:
                continue
            try:
                confidence = int(float(data["conf"][idx]))
            except (ValueError, TypeError):
                confidence = 0
            if confidence < conf_threshold:
                continue
            key = (data["block_num"][idx], data["par_num"][idx])
            groups[key].append(
                {
                    "text": text,
                    "left": int(data["left"][idx]),
                    "top": int(data["top"][idx]),
                    "width": int(data["width"][idx]),
                    "height": int(data["height"][idx]),
                    "line_num": int(data["line_num"][idx]),
                    "word_num": int(data["word_num"][idx]),
                }
            )

        bubbles: List[DetectedBubble] = []
        for group_index, words in enumerate(groups.values()):
            if not words:
                continue
            words_sorted = sorted(words, key=lambda w: (w["line_num"], w["word_num"], w["left"]))
            assembled = " ".join(word["text"] for word in words_sorted).strip()
            if not assembled:
                continue
            left = min(word["left"] for word in words_sorted)
            top = min(word["top"] for word in words_sorted)
            right = max(word["left"] + word["width"] for word in words_sorted)
            bottom = max(word["top"] + word["height"] for word in words_sorted)
            bubbles.append(
                DetectedBubble(
                    bubble_id=f"ocr_{group_index}",
                    box=[left, top, right, bottom],
                    text=assembled,
                    kind="dialogue",
                )
            )

        bubbles.sort(key=lambda bubble: (bubble.box[1], bubble.box[0]))
        return bubbles


ocr_service = OCRService()

