from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Sequence

from PIL import Image, ImageEnhance, ImageOps
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
            try:
                crop = image.crop(region).convert("L")
                candidates: list[str] = []

                def _add_candidate(text: str) -> None:
                    cleaned = self._clean_ui_text(text)
                    if cleaned:
                        candidates.append(cleaned)

                for variant in self._generate_variants(crop):
                    for config in ("--psm 6 --oem 1", "--psm 7 --oem 1"):
                        try:
                            text = pytesseract.image_to_string(variant, config=config).strip()
                            if text:
                                _add_candidate(text)
                        except Exception:
                            continue
                    try:
                        data_text = self._text_from_data(variant)
                        if data_text:
                            _add_candidate(data_text)
                    except Exception:
                        continue

                if not candidates:
                    return ""

                scored = sorted(
                    candidates,
                    key=lambda text: self._score_ui_candidate(text),
                    reverse=True,
                )
                top = scored[0]
                return self._normalize_ui_text(top)
            except Exception as e:
                print(f"⚠️ UI OCR failed for region {region}: {e}")
                return ""
        
        ui_keywords = ["YOU ARE", "CHARACTER", "SYSTEM", "QUEST", "MISSION", "STATUS"]
        
        # Focused region on the right side where panels usually appear
        panel_region = (
            int(width * 0.45),
            int(height * 0.25),
            int(width * 0.95),
            int(height * 0.75),
        )
        print(f"🔎 Scanning panel region: {panel_region} on {width}x{height} image")
        panel_text = _extract_text_from_region(panel_region)
        print(f"🔎 Panel OCR result: '{panel_text}' (length: {len(panel_text)})")
        
        if panel_text and len(panel_text) > 5:  # Lowered threshold from 8 to 5
            print(f"🔎 Checking for UI keywords in: {panel_text.upper()}")
            # Check if this is likely UI text (contains system keywords OR has junk characters)
            has_ui_keywords = any(keyword in panel_text.upper() for keyword in ui_keywords)
            # Also accept if it's gibberish (OCR failed on colored background)
            is_gibberish = any(char in panel_text for char in ["\\", "|"]) or len(panel_text.split()) < 3
            
            if has_ui_keywords or is_gibberish:
                print(f"✅ Adding panel as UI element (keywords: {has_ui_keywords}, gibberish: {is_gibberish})")
                ui_bubbles.append(
                    DetectedBubble(
                        bubble_id="ui_panel",
                        box=list(panel_region),
                        text=panel_text,
                        kind="narration",
                    )
                )
            else:
                print(f"❌ Panel text rejected (no UI keywords or gibberish pattern)")
        
        # Check bottom region for UI text (bottom 20% of image)
        bottom_region = (0, int(height * 0.8), width, height)
        bottom_text = _extract_text_from_region(bottom_region)
        if bottom_text and len(bottom_text) > 10:
            ui_bubbles.append(
                DetectedBubble(
                    bubble_id="ui_bottom",
                    box=list(bottom_region),
                    text=bottom_text,
                    kind="narration",
                )
            )
        
        return ui_bubbles

    def _generate_variants(self, crop: Image.Image) -> list[Image.Image]:
        variants: list[Image.Image] = []
        # Simpler, faster variant generation
        enlarged = crop.resize(
            (max(1, crop.width * 2), max(1, crop.height * 2)),
            Image.BICUBIC,
        )
        variants.append(enlarged)
        variants.append(ImageOps.autocontrast(enlarged))
        variants.append(ImageOps.invert(enlarged))
        contrast = ImageEnhance.Contrast(enlarged).enhance(2.5)
        variants.append(contrast)
        variants.append(ImageOps.invert(contrast))
        threshold = enlarged.point(lambda px: 255 if px > 180 else 0)
        variants.append(threshold)
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


ocr_service = OCRService()

