from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass
class PanelBox:
    panel_id: str
    box: Sequence[float]


@dataclass
class BubbleBox:
    bubble_id: str
    box: Sequence[float]
    mask_path: Path | None = None


class LayoutDetector:
    """
    Thin placeholder around YOLOv8/Detectron2 inference.
    Swap with a proper model once dataset is collected.
    """

    def detect(self, image_path: Path) -> tuple[List[PanelBox], List[BubbleBox]]:
        # TODO: integrate ultralytics model inference
        panels = [PanelBox(panel_id="panel_1", box=[40, 40, 1000, 1800])]
        bubbles = [
            BubbleBox(bubble_id="bubble_1", box=[100, 200, 420, 420]),
            BubbleBox(bubble_id="bubble_2", box=[500, 600, 900, 820]),
        ]
        return panels, bubbles


layout_detector = LayoutDetector()

