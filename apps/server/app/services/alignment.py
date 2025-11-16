from __future__ import annotations

from typing import List


class AlignmentService:
    def align(self, text: str, audio_path: str) -> List[dict[str, float | str]]:
        # TODO: integrate MFA or gentle aligner when provider lacks timings
        return []


alignment_service = AlignmentService()

