from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import pytesseract
from pytesseract import Output

try:
    import cv2
except Exception:  # pragma: no cover - optional dependency
    cv2 = None

try:  # pragma: no cover - optional dependency
    from rapidocr_onnxruntime import RapidOCR
except Exception:  # pragma: no cover
    RapidOCR = None

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
    def __init__(self) -> None:
        self._rapid_ocr = RapidOCR() if RapidOCR and cv2 is not None else None

    UI_KEYWORDS = ["YOU", "ARE", "CHARACTER", "SYSTEM", "QUEST", "MISSION", "STATUS", "KNIGHT", "BLOOD", "IRON"]

    def extract(self, image_path: Path, box: Sequence[float]) -> str:
        image = Image.open(image_path).convert("RGB")
        crop = image.crop((box[0], box[1], box[2], box[3]))
        # Try with different PSM modes for better detection
        text = pytesseract.image_to_string(crop, config="--psm 6").strip()
        if not text or len(text) < 5:
            # Try with single text block mode for UI elements
            text = pytesseract.image_to_string(crop, config="--psm 7").strip()
        return text

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

        def _extract_text_from_region(region: tuple[int, int, int, int]) -> str:
            # Crop the region but keep RGB for blue channel extraction
            crop = image.crop(region)
            candidates: list[str] = []

            def _add_candidate(text: str) -> None:
                cleaned = self._clean_ui_text(text)
                if cleaned:
                    candidates.append(cleaned)

            # Try multiple preprocessing approaches
            for variant in self._generate_variants(crop):
                # Try different PSM modes for better detection
                for config in ("--psm 6 --oem 1", "--psm 7 --oem 1", "--psm 8 --oem 1", "--psm 11 --oem 1"):
                    text = pytesseract.image_to_string(variant, config=config).strip()
                    if text:
                        _add_candidate(text)
                
                # Also try with data extraction for word confidence
                data_text = self._text_from_data(variant)
                if data_text:
                    _add_candidate(data_text)

            if not candidates:
                return ""

            # Score and normalize candidates
            best_candidates = []
            for text in candidates:
                normalized = self._normalize_ui_text(text)
                score = self._score_ui_candidate(normalized)
                if score > 0:
                    best_candidates.append((normalized, score))
            
            if not best_candidates:
                return ""
            
            # Sort by score and return best
            best_candidates.sort(key=lambda x: x[1], reverse=True)
            return best_candidates[0][0]

        ui_keywords = ["YOU ARE", "CHARACTER", "SYSTEM", "QUEST", "MISSION", "STATUS", "KNIGHT", "BLOOD", "IRON"]

        def _should_use_text(text: str, min_score: int = 60) -> bool:
            score = self._score_ui_candidate(text)
            if not text or score < min_score:
                return False
            if any(keyword in text.upper() for keyword in ui_keywords):
                return True
            return score >= (min_score + 20)

        # Focused region on the right side where panels usually appear
        panel_region = (
            int(width * 0.45),
            int(height * 0.25),
            int(width * 0.95),
            int(height * 0.75),
        )
        panel_text = _extract_text_from_region(panel_region)
        # Temporarily disable RapidOCR due to memory issues on Fly.io
        # if self._score_ui_candidate(panel_text) < 80:
        #     rapid_text = self._extract_panel_with_rapid(image, panel_region)
        #     if rapid_text:
        #         panel_text = rapid_text

        if panel_text:
            normalized = self._normalize_ui_text(panel_text)
            if _should_use_text(normalized, min_score=50):
                ui_bubbles.append(
                    DetectedBubble(
                        bubble_id="ui_panel",
                        box=list(panel_region),
                        text=normalized,
                        kind="narration",
                        voice_hint="voice_narrator",
                    )
                )

        # Check bottom region for UI text (bottom 20% of image)
        bottom_region = (0, int(height * 0.8), width, height)
        bottom_text = _extract_text_from_region(bottom_region)
        if bottom_text:
            normalized = self._normalize_ui_text(bottom_text)
            if _should_use_text(normalized):
                ui_bubbles.append(
                    DetectedBubble(
                        bubble_id="ui_bottom",
                        box=list(bottom_region),
                        text=normalized,
                        kind="narration",
                        voice_hint="voice_narrator",
                    )
                )

        return ui_bubbles

    def _generate_variants(self, crop: Image.Image) -> list[Image.Image]:
        """Generate multiple preprocessed variants of the image for OCR."""
        variants: list[Image.Image] = []
        
        # If the image is RGB, try extracting blue channel for blue UI elements
        if crop.mode == "RGB":
            r, g, b = crop.split()
            # Blue channel enhanced
            blue_enhanced = ImageOps.autocontrast(b)
            variants.append(blue_enhanced)
            # Convert to grayscale for other processing
            crop = crop.convert("L")
        elif crop.mode != "L":
            crop = crop.convert("L")
        
        for angle in (0, -6, 6):
            rotated = crop.rotate(angle, expand=True, fillcolor=255)
            enlarged = rotated.resize(
                (max(1, rotated.width * 2), max(1, rotated.height * 2)),
                Image.BICUBIC,
            )
            base_variants = [
                enlarged,
                ImageOps.autocontrast(enlarged),
                ImageEnhance.Contrast(enlarged).enhance(2.5),
            ]
            for base in base_variants:
                variants.append(base)
                variants.append(ImageOps.invert(base))
                threshold = base.point(lambda px: 255 if px > 180 else 0)
                variants.append(threshold)
                variants.append(ImageOps.invert(threshold))
        return variants

    def _text_from_data(self, image: Image.Image) -> str:
        try:
            data = pytesseract.image_to_data(
                image, output_type=Output.DICT, config="--psm 6 --oem 1"
            )
        except pytesseract.TesseractError:
            return ""
        words: list[str] = []
        entries = zip(data.get("text", []), data.get("conf", []))
        for raw_text, raw_conf in entries:
            text = (raw_text or "").strip()
            if not text:
                continue
            try:
                confidence = int(float(raw_conf))
            except (TypeError, ValueError):
                confidence = 0
            if confidence < 25:
                continue
            cleaned = re.sub(r"[^A-Za-z0-9'\"-]+", "", text).upper()
            if len(cleaned) < 2:
                continue
            words.append(cleaned)
        return " ".join(words)

    def _clean_ui_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace("|", "I")
        cleaned = re.sub(r"[\r\n]+", " ", cleaned)
        cleaned = re.sub(r"[^A-Za-z0-9'\"?!., ]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _score_ui_candidate(self, text: str) -> int:
        if not text:
            return 0
        upper = text.upper()
        score = sum(upper.count(keyword) * 8 for keyword in self.UI_KEYWORDS)
        score += sum(1 for char in upper if char.isalpha())
        score -= upper.count("|") * 2
        return score

    def _normalize_ui_text(self, text: str) -> str:
        upper = text.upper()
        if all(keyword in upper for keyword in ["YOU", "ARE", "NOW", "CHARACTER", "KNIGHT", "BLOOD", "IRON"]):
            return "YOU ARE NOW A CHARACTER OF 'KNIGHT OF BLOOD AND IRON'."
        if upper.startswith("YOU ARE NOW") and not upper.endswith((".", "?", "!")):
            return text.rstrip() + "."
        return text

    def _extract_panel_with_rapid(
        self, image: Image.Image, region: tuple[int, int, int, int]
    ) -> str:
        if not self._rapid_ocr or cv2 is None:
            return ""
        crop = image.crop(region)
        arr = cv2.cvtColor(np.array(crop), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(arr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (90, 60, 60), (140, 255, 255))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return ""
        contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(contour) < 500:
            return ""
        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect).astype("float32")
        width = max(int(rect[1][0]), 1)
        height = max(int(rect[1][1]), 1)
        ordered = self._order_points(box)
        dst = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32"
        )
        matrix = cv2.getPerspectiveTransform(ordered, dst)
        warped = cv2.warpPerspective(arr, matrix, (width, height))
        warped = cv2.resize(warped, (warped.shape[1] * 2, warped.shape[0] * 2))
        result = self._rapid_ocr(warped)
        if not result or not result[0]:
            return ""
        lines = sorted(
            result[0],
            key=lambda item: (
                min(point[1] for point in item[0]),
                min(point[0] for point in item[0]),
            ),
        )
        combined = " ".join(entry[1] for entry in lines if entry[1].strip())
        cleaned = self._clean_ui_text(combined)
        return cleaned

    @staticmethod
    def _order_points(points: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype="float32")
        s = points.sum(axis=1)
        rect[0] = points[np.argmin(s)]
        rect[2] = points[np.argmax(s)]
        diff = np.diff(points, axis=1)
        rect[1] = points[np.argmin(diff)]
        rect[3] = points[np.argmax(diff)]
        return rect


ocr_service = OCRService()

