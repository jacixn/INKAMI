from fastapi import APIRouter, HTTPException, Path

from app.models.schemas import SpeakerUpdate
from app.services.pipeline import chapter_store

router = APIRouter()


@router.patch("/{speaker_id}")
async def update_speaker(
    speaker_id: str = Path(..., description="Detected speaker id"),
    payload: SpeakerUpdate | None = None,
) -> dict[str, str]:
    if payload is None:
        raise HTTPException(status_code=400, detail="Missing payload")
    chapter_store.update_speaker(speaker_id, payload)
    return {"status": "ok"}

