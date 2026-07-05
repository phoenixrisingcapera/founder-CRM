from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import DeckFile
from app.services.deck_preview_service import extract_source_previews


def _normalized_source_extension(deck_file: DeckFile) -> str:
    raw_extension = str(deck_file.file_extension or "").strip().lower()
    if raw_extension:
        return raw_extension.removeprefix(".")

    fallback_name = deck_file.original_filename or deck_file.filename or ""
    return Path(fallback_name).suffix.lower().removeprefix(".")


def extract_presentation_miniatures(
    db: Session,
    deck_id: str,
    *,
    publish_ready_state: bool = False,
) -> dict[str, int | str | bool | None]:
    deck_file = db.query(DeckFile).filter(DeckFile.deck_id == deck_id).one_or_none()
    if deck_file is None:
        raise ValueError("Deck source file not found")

    source_extension = _normalized_source_extension(deck_file)
    if source_extension not in {"pdf", "ppt", "pptx"}:
        raise ValueError("Presentation miniatures require a PDF, PPT, or PPTX source file")

    return extract_source_previews(db, deck_id, publish_ready_state=publish_ready_state)
