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

    def detect_bubbles(self, image_path: Path, conf_threshold: int = 45) -> List[DetectedBubble]:
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

        # First pass: create bubbles from OCR groups
        raw_bubbles: List[DetectedBubble] = []
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
            raw_bubbles.append(
                DetectedBubble(
                    bubble_id=f"ocr_{group_index}",
                    box=[left, top, right, bottom],
                    text=assembled,
                    kind="dialogue",
                )
            )
        
        # Second pass: merge nearby bubbles that likely belong together
        bubbles: List[DetectedBubble] = []
        merged_indices = set()
        
        for i, bubble1 in enumerate(raw_bubbles):
            if i in merged_indices:
                continue
                
            # Try to find bubbles that should be merged with this one
            merged_text = bubble1.text
            merged_box = list(bubble1.box)
            
            for j, bubble2 in enumerate(raw_bubbles[i+1:], i+1):
                if j in merged_indices:
                    continue
                    
                # Check if bubbles are close enough to merge (within 50 pixels vertically)
                vertical_distance = abs(bubble2.box[1] - bubble1.box[3])
                horizontal_overlap = min(bubble1.box[2], bubble2.box[2]) - max(bubble1.box[0], bubble2.box[0])
                
                if vertical_distance < 50 and horizontal_overlap > 0:
                    # Merge the bubbles
                    merged_text += " " + bubble2.text
                    merged_box[0] = min(merged_box[0], bubble2.box[0])
                    merged_box[1] = min(merged_box[1], bubble2.box[1])
                    merged_box[2] = max(merged_box[2], bubble2.box[2])
                    merged_box[3] = max(merged_box[3], bubble2.box[3])
                    merged_indices.add(j)
            
            bubbles.append(
                DetectedBubble(
                    bubble_id=f"ocr_{i}",
                    box=merged_box,
                    text=merged_text,
                    kind="dialogue",
                )
            )

        bubbles.sort(key=lambda bubble: (bubble.box[1], bubble.box[0]))
        return bubbles

    def detect_ui_elements(self, image_path: Path) -> List[DetectedBubble]:
        """Detect UI/system text elements that might be missed by regular bubble detection."""
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        ui_bubbles: List[DetectedBubble] = []
        
        # Check bottom region for UI text (bottom 20% of image)
        bottom_region = (0, int(height * 0.8), width, height)
        bottom_text = self.extract(image_path, bottom_region).strip()
        if bottom_text and len(bottom_text) > 10:  # Increased minimum length
            ui_bubbles.append(
                DetectedBubble(
                    bubble_id="ui_bottom",
                    box=list(bottom_region),
                    text=bottom_text,
                    kind="narration",
                )
            )
        
        return ui_bubbles


ocr_service = OCRService()

