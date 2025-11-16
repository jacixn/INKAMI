from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass
class SpeakerGuess:
    speaker_id: str
    confidence: float
    character_name: str | None = None


class SpeakerLinker:
    def link(
        self,
        bubble_box: Sequence[float],
        panel_faces: list[tuple[str, Sequence[float]]],
    ) -> SpeakerGuess:
        if panel_faces:
            face_id, _ = panel_faces[0]
            return SpeakerGuess(speaker_id=face_id, confidence=0.7)
        return SpeakerGuess(speaker_id="narrator", confidence=0.3)


speaker_linker = SpeakerLinker()

