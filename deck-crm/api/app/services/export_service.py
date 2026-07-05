from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.security import generate_id
from app.db.models import AnalysisFinding, CompiledDeck, Deck, DeckExport, DeckSlide


def _map_export(deck_export: DeckExport) -> dict[str, str]:
    return {
        "id": deck_export.id,
        "deck_id": deck_export.deck_id,
        "deckId": deck_export.deck_id,
        "type": deck_export.type,
        "content": deck_export.content,
        "created_at": deck_export.created_at.isoformat() if deck_export.created_at else "",
        "createdAt": deck_export.created_at.isoformat() if deck_export.created_at else "",
        "download_url": f"/api/decks/{deck_export.deck_id}/exports/{deck_export.id}/download",
        "downloadUrl": f"/api/decks/{deck_export.deck_id}/exports/{deck_export.id}/download",
    }


def _latest_compiled_deck(db: Session, deck_id: str) -> CompiledDeck | None:
    return (
        db.query(CompiledDeck)
        .filter(CompiledDeck.source_deck_id == deck_id, CompiledDeck.status == "ready")
        .order_by(CompiledDeck.finalized_at.desc())
        .first()
    )


def _build_compiled_deck_export_content(compiled_deck: CompiledDeck, export_type: str) -> str:
    manifest = compiled_deck.manifest_json or {}
    slides = manifest.get("slides", [])
    if export_type == "adapted_outline" and isinstance(slides, list):
        return "\n".join(
            (
                f"{slide.get('slideIndex', index)}. "
                f"{slide.get('title', 'Untitled slide')} "
                f"({slide.get('choice', 'original')})"
            )
            for index, slide in enumerate(slides, start=1)
            if isinstance(slide, dict)
        )

    return json.dumps(
        {
            "exportType": export_type,
            "deckId": compiled_deck.source_deck_id,
            "compiledDeckId": compiled_deck.id,
            "title": compiled_deck.title,
            "status": compiled_deck.status,
            "finalizedAt": compiled_deck.finalized_at.isoformat() if compiled_deck.finalized_at else None,
            "manifest": manifest,
        },
        sort_keys=True,
    )


def _build_legacy_export_content(db: Session, deck_id: str, export_type: str) -> str:
    slides = (
        db.query(DeckSlide)
        .filter(DeckSlide.deck_id == deck_id)
        .order_by(DeckSlide.slide_index.asc())
        .all()
    )
    findings = (
        db.query(AnalysisFinding)
        .filter(AnalysisFinding.deck_id == deck_id)
        .order_by(AnalysisFinding.severity.desc(), AnalysisFinding.title.asc())
        .all()
    )

    if export_type == "adapted_outline":
        return "\n".join(f"{slide.slide_index}. {slide.title} ({slide.role})" for slide in slides)

    return "\n".join(f"- {finding.title}: {finding.detail}" for finding in findings)


def _build_export_content(db: Session, deck_id: str, export_type: str) -> str:
    if export_type != "findings":
        compiled_deck = _latest_compiled_deck(db, deck_id)
        if compiled_deck is not None:
            return _build_compiled_deck_export_content(compiled_deck, export_type)

    return _build_legacy_export_content(db, deck_id, export_type)


def create_export(db: Session, deck_id: str, export_type: str) -> dict[str, str] | None:
    deck = db.query(Deck).filter(Deck.id == deck_id).one_or_none()
    if deck is None:
        return None

    deck_export = DeckExport(
        id=generate_id("export"),
        deck_id=deck.id,
        type=export_type,
        content=_build_export_content(db, deck.id, export_type),
    )
    db.add(deck_export)
    db.commit()
    db.refresh(deck_export)
    return _map_export(deck_export)


def list_exports(db: Session, deck_id: str) -> list[dict[str, str]]:
    exports = (
        db.query(DeckExport)
        .filter(DeckExport.deck_id == deck_id)
        .order_by(DeckExport.created_at.desc())
        .all()
    )
    return [_map_export(deck_export) for deck_export in exports]


def get_export(db: Session, deck_id: str, export_id: str) -> dict[str, str] | None:
    deck_export = (
        db.query(DeckExport)
        .filter(DeckExport.deck_id == deck_id, DeckExport.id == export_id)
        .one_or_none()
    )
    return _map_export(deck_export) if deck_export is not None else None


def export_download_payload(db: Session, deck_id: str, export_id: str) -> tuple[str, str, str] | None:
    deck_export = (
        db.query(DeckExport)
        .filter(DeckExport.deck_id == deck_id, DeckExport.id == export_id)
        .one_or_none()
    )
    if deck_export is None:
        return None

    if deck_export.type == "final_deck":
        media_type = "application/json"
        extension = "json"
    else:
        media_type = "text/plain; charset=utf-8"
        extension = "txt"
    filename = f"deck-aistack-codes-{deck_id}-{deck_export.type}-{deck_export.id}.{extension}"
    return deck_export.content, media_type, filename
