from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session, selectinload

from app.db.models import Deck, DeckSlide, DesignBatch, User, Workspace
from app.services.deck_workflow_service import get_deck_workflow_state


def _deck_status(status: str) -> str:
    if status in {"pending", "uploaded", "extracting", "parsing", "structuring", "extracting_blocks", "classifying_blocks", "analysing", "adapting"}:
        return "preparing"
    if status == "ready":
        return "ready_to_review"
    if status == "reviewed":
        return "reviewed"
    if status == "exported":
        return "exported"
    return "preparing"


def _dashboard_deck_status(db: Session, deck: Deck | None) -> str:
    if deck is None:
        return "preparing"
    workflow = get_deck_workflow_state(db, deck.id)
    if workflow is None:
        return _deck_status(deck.status)
    phase = str(workflow.get("phase") or "")
    status = str(workflow.get("status") or "")
    if workflow.get("canOpenSmartDeck") or phase in {"smart_deck_ready", "preview_ready", "applied", "export_ready"}:
        return "ready_to_review"
    if status in {"failed_retryable", "failed_final", "blocked", "timed_out"}:
        return "failed"
    if phase in {"upload_accepted", "source_file_saved"}:
        return "preparing"
    if workflow.get("activeJob") or workflow.get("latestJobs"):
        return "preparing"
    return _deck_status(deck.status)


def _iteration_status(status: str) -> str:
    if status == "completed":
        return "ready_for_review"
    if status == "reviewed":
        return "accepted"
    if status == "compiled":
        return "compiled"
    if status == "running":
        return "draft"
    if status == "failed":
        return "failed"
    return "draft"


def _iteration_title(batch: DesignBatch) -> str:
    if batch.batch_name:
        return batch.batch_name.replace("IC", "Investment committee", 1) if batch.batch_name.startswith("IC") else batch.batch_name
    if batch.audience_label:
        return f"{batch.audience_label} iteration"
    if batch.scope_type == "selected_slides":
        return "Selected slide iteration"
    return "Whole deck iteration"


def _slide_thumbnail(slide: DeckSlide | None) -> str | None:
    if slide is None:
        return None
    if not (slide.rendered_image_path or slide.thumbnail_path):
        return None
    return f"/api/decks/{slide.deck_id}/slides/{slide.id}/preview"


def _serialize_deck(db: Session, deck: Deck) -> dict:
    sorted_slides = sorted(deck.slides, key=lambda slide: slide.slide_index)
    return {
        "id": deck.id,
        "title": deck.title,
        "description": deck.description or deck.summary or "",
        "audience": deck.audience or "",
        "purpose": deck.purpose or "",
        "status": _dashboard_deck_status(db, deck),
        "slideCount": deck.slide_count or len(sorted_slides),
        "thumbnailUrl": _slide_thumbnail(sorted_slides[0] if sorted_slides else None),
        "updatedAt": deck.updated_at.isoformat(),
    }


def _serialize_slide(slide: DeckSlide) -> dict:
    return {
        "id": slide.id,
        "deckId": slide.deck_id,
        "slideNumber": slide.slide_number or slide.slide_index,
        "title": slide.title,
        "thumbnailUrl": _slide_thumbnail(slide),
        "previewImageUrl": _slide_thumbnail(slide),
        "status": "original",
        "updatedAt": slide.updated_at.isoformat(),
    }


def _serialize_iteration(batch: DesignBatch) -> dict:
    sorted_slides = sorted(batch.deck.slides, key=lambda slide: slide.slide_index) if batch.deck is not None else []
    return {
        "id": batch.id,
        "deckId": batch.deck_id,
        "deckTitle": batch.deck.title if batch.deck is not None else "",
        "iterationNumber": batch.batch_number,
        "title": _iteration_title(batch),
        "scope": batch.scope_type,
        "status": _iteration_status(batch.status),
        "thumbnailUrl": _slide_thumbnail(sorted_slides[0] if sorted_slides else None),
        "updatedAt": (batch.updated_at or batch.created_at).isoformat(),
    }


def _scope_deck_query(db: Session, user: User):
    query = db.query(Deck)
    if user.role != "super_admin":
        query = query.join(Workspace, Workspace.id == Deck.workspace_id).filter(
            (Deck.user_id == user.id) | (Workspace.user_id == user.id)
        )
    return query


def get_workspace_dashboard(db: Session, user: User) -> dict:
    decks = _scope_deck_query(db, user).options(selectinload(Deck.file), selectinload(Deck.slides)).order_by(
        Deck.updated_at.desc()
    ).limit(6).all()
    latest_deck = decks[0] if decks else None
    recent_slides = (
        db.query(DeckSlide)
        .filter(DeckSlide.deck_id == latest_deck.id)
        .order_by(DeckSlide.slide_index.asc())
        .limit(6)
        .all()
        if latest_deck is not None
        else []
    )
    latest_iterations_query = db.query(DesignBatch).join(Deck, Deck.id == DesignBatch.deck_id)
    if user.role != "super_admin":
        latest_iterations_query = latest_iterations_query.join(Workspace, Workspace.id == Deck.workspace_id).filter(
            (Deck.user_id == user.id) | (Workspace.user_id == user.id)
        )
    latest_iterations = latest_iterations_query.options(selectinload(DesignBatch.deck).selectinload(Deck.slides)).order_by(
        DesignBatch.updated_at.desc()
    ).limit(5).all()
    week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
    scoped_deck_ids = [deck.id for deck in decks]
    uploaded_count = _scope_deck_query(db, user).count()
    slides_count = db.query(DeckSlide).filter(DeckSlide.deck_id.in_(scoped_deck_ids)).count() if scoped_deck_ids else 0
    iterations_this_week = (
        latest_iterations_query.filter(DesignBatch.created_at >= week_start).count()
    )

    return {
        "user": {
            "id": user.id,
            "handle": user.email.split("@", 1)[0],
            "role": user.role,
            "plan": "Pro plan",
        },
        "stats": {
            "uploadedDecks": uploaded_count,
            "iterationsThisWeek": iterations_this_week,
            "slidesInLibrary": slides_count,
            "teamMembers": 1 if user.role != "super_admin" else max(db.query(User).count(), 1),
        },
        "latestDeck": _serialize_deck(db, latest_deck) if latest_deck is not None else None,
        "decks": [_serialize_deck(db, deck) for deck in decks],
        "recentSlides": [_serialize_slide(slide) for slide in recent_slides],
        "latestIterations": [_serialize_iteration(batch) for batch in latest_iterations],
    }
