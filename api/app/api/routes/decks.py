from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.core.config import settings
from app.db.models import User
from app.db.models import AudienceProfile, Deck, DeckArtifact, DeckGenerationRun, DeckSlide, TelemetryEvent
from app.schemas.crm import DeleteResponse
from app.schemas.deck import (
    AudienceProfileResponse,
    DeckArtifactResponse,
    DeckGenerationRequest,
    DeckGenerationResponse,
    DeckGenerationRunResponse,
    DeckArtifactDetailResponse,
    DeckResponse,
    DeckSlideResponse,
)
from app.services.ai import generate_deck_improvement
from app.services.deck_parser import parse_deck_file
from app.services.observability import create_telemetry_event
from app.services.settings import resolve_user_api_key

router = APIRouter(tags=["decks"])


@router.get("/audiences", response_model=list[AudienceProfileResponse])
def list_audiences(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[AudienceProfileResponse]:
    records = db.query(AudienceProfile).filter(AudienceProfile.workspace_id == workspace.id).order_by(AudienceProfile.label.asc()).all()
    return [AudienceProfileResponse(id=item.id, code=item.code, label=item.label, description=item.description) for item in records]


@router.get("/decks", response_model=list[DeckResponse])
def list_decks(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[DeckResponse]:
    decks = db.query(Deck).filter(Deck.workspace_id == workspace.id).order_by(Deck.created_at.desc()).all()
    return [_serialize_deck(db, deck) for deck in decks]


@router.post("/decks/upload", response_model=DeckResponse)
async def upload_deck(
    title: str = Form(...),
    audience: str = Form("angel"),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> DeckResponse:
    content = await file.read()
    slides = parse_deck_file(file.filename or "deck.txt", content)

    settings.uploads_root_path.mkdir(parents=True, exist_ok=True)
    storage_path = settings.uploads_root_path / f"{workspace.id}_{file.filename or 'deck.txt'}"
    storage_path.write_bytes(content)

    deck = Deck(
        workspace_id=workspace.id,
        title=title,
        audience=audience,
        status="uploaded",
        source_file_name=file.filename,
        source_storage_path=str(storage_path),
    )
    db.add(deck)
    db.flush()

    for index, slide in enumerate(slides, start=1):
        db.add(
            DeckSlide(
                workspace_id=workspace.id,
                deck_id=deck.id,
                slide_order=index,
                title=slide["title"],
                content=slide["content"],
            )
        )

    db.commit()
    db.refresh(deck)
    create_telemetry_event(
        db,
        event_name="deck.upload.completed",
        status="uploaded",
        user_id=user.id,
        workspace_id=workspace.id,
        deck_id=deck.id,
        metadata={"title": deck.title, "audience": audience, "slide_count": len(slides)},
    )
    return _serialize_deck(db, deck)


@router.post("/decks/{deck_id}/generation-runs", response_model=DeckGenerationResponse)
async def create_generation_run(
    deck_id: str,
    payload: DeckGenerationRequest,
    user: User = Depends(get_current_user),
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> DeckGenerationResponse:
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.workspace_id == workspace.id).one_or_none()
    if deck is None:
        raise HTTPException(status_code=404, detail="Deck not found")

    audience = (
        db.query(AudienceProfile)
        .filter(AudienceProfile.workspace_id == workspace.id, AudienceProfile.code == payload.audience_code)
        .one_or_none()
    )
    if audience is None:
        raise HTTPException(status_code=404, detail="Audience profile not found")

    slides = db.query(DeckSlide).filter(DeckSlide.deck_id == deck.id).order_by(DeckSlide.slide_order.asc()).all()
    slide_text = "\n\n".join(f"{item.slide_order}. {item.title}\n{item.content}" for item in slides)

    stored_provider, stored_api_key = resolve_user_api_key(db, user, payload.provider)
    run_api_key = payload.api_key or stored_api_key
    run_provider = payload.provider or stored_provider

    try:
        provider, model, markdown = await generate_deck_improvement(
            audience_label=audience.label,
            instruction=payload.instruction,
            slide_text=slide_text,
            api_key=run_api_key,
            provider=run_provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run = DeckGenerationRun(
        workspace_id=workspace.id,
        deck_id=deck.id,
        audience_profile_id=audience.id,
        provider=provider,
        model=model,
        status="completed",
        prompt_summary=payload.instruction,
    )
    db.add(run)
    db.flush()

    artifact = DeckArtifact(
        workspace_id=workspace.id,
        deck_id=deck.id,
        generation_run_id=run.id,
        artifact_type="deck_improvement",
        artifact_status="draft",
        title=f"{deck.title} improvement for {audience.label}",
        content_markdown=markdown,
        export_enabled=settings.exports_enabled,
    )
    db.add(artifact)
    deck.status = "improved"
    db.commit()
    db.refresh(artifact)
    create_telemetry_event(
        db,
        event_name="deck.generation.completed",
        status="completed",
        provider=provider,
        model=model,
        user_id=user.id,
        workspace_id=workspace.id,
        deck_id=deck.id,
        run_id=run.id,
        metadata={"artifact_id": artifact.id, "audience_code": payload.audience_code},
    )

    return DeckGenerationResponse(
        run_id=run.id,
        artifact=_serialize_artifact(artifact),
    )


@router.get("/artifacts", response_model=list[DeckArtifactResponse])
def list_artifacts(workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[DeckArtifactResponse]:
    artifacts = (
        db.query(DeckArtifact)
        .filter(DeckArtifact.workspace_id == workspace.id)
        .order_by(DeckArtifact.created_at.desc())
        .all()
    )
    return [_serialize_artifact(item) for item in artifacts]


@router.get("/decks/{deck_id}/generation-runs", response_model=list[DeckGenerationRunResponse])
def list_generation_runs(deck_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> list[DeckGenerationRunResponse]:
    rows = (
        db.query(DeckGenerationRun)
        .filter(DeckGenerationRun.deck_id == deck_id, DeckGenerationRun.workspace_id == workspace.id)
        .order_by(DeckGenerationRun.created_at.desc())
        .all()
    )
    return [_serialize_run(db, item) for item in rows]


@router.get("/generation-runs/{run_id}", response_model=DeckGenerationRunResponse)
def get_generation_run(run_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeckGenerationRunResponse:
    row = db.query(DeckGenerationRun).filter(DeckGenerationRun.id == run_id, DeckGenerationRun.workspace_id == workspace.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Generation run not found")
    return _serialize_run(db, row)


@router.get("/artifacts/{artifact_id}", response_model=DeckArtifactDetailResponse)
def get_artifact(artifact_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeckArtifactDetailResponse:
    artifact = db.query(DeckArtifact).filter(DeckArtifact.id == artifact_id, DeckArtifact.workspace_id == workspace.id).one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    deck = db.query(Deck).filter(Deck.id == artifact.deck_id).one_or_none()
    run = db.query(DeckGenerationRun).filter(DeckGenerationRun.id == artifact.generation_run_id).one_or_none()
    audience = db.query(AudienceProfile).filter(AudienceProfile.id == run.audience_profile_id).one_or_none() if run and run.audience_profile_id else None
    return DeckArtifactDetailResponse(
        **_serialize_artifact(artifact).model_dump(),
        deck_title=deck.title if deck else None,
        audience_label=audience.label if audience else None,
        run=_serialize_run(db, run) if run else None,
    )


@router.patch("/artifacts/{artifact_id}/status", response_model=DeckArtifactDetailResponse)
def update_artifact_status(artifact_id: str, status: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeckArtifactDetailResponse:
    artifact = db.query(DeckArtifact).filter(DeckArtifact.id == artifact_id, DeckArtifact.workspace_id == workspace.id).one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    artifact.artifact_status = status
    db.commit()
    db.refresh(artifact)
    return DeckArtifactDetailResponse(**_serialize_artifact(artifact).model_dump(), deck_title=None, audience_label=None, run=None)


@router.delete("/artifacts/{artifact_id}", response_model=DeleteResponse)
def delete_artifact(artifact_id: str, workspace=Depends(get_current_workspace), db: Session = Depends(get_db)) -> DeleteResponse:
    artifact = db.query(DeckArtifact).filter(DeckArtifact.id == artifact_id, DeckArtifact.workspace_id == workspace.id).one_or_none()
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    db.delete(artifact)
    db.commit()
    return DeleteResponse(status="deleted")


def _serialize_deck(db: Session, deck: Deck) -> DeckResponse:
    slides = db.query(DeckSlide).filter(DeckSlide.deck_id == deck.id).order_by(DeckSlide.slide_order.asc()).all()
    return DeckResponse(
        id=deck.id,
        title=deck.title,
        audience=deck.audience,
        status=deck.status,
        source_file_name=Path(deck.source_storage_path).name if deck.source_storage_path else deck.source_file_name,
        slides=[DeckSlideResponse(id=item.id, slide_order=item.slide_order, title=item.title, content=item.content) for item in slides],
    )


def _serialize_artifact(artifact: DeckArtifact) -> DeckArtifactResponse:
    return DeckArtifactResponse(
        id=artifact.id,
        deck_id=artifact.deck_id,
        generation_run_id=artifact.generation_run_id,
        artifact_type=artifact.artifact_type,
        artifact_status=artifact.artifact_status,
        title=artifact.title,
        content_markdown=artifact.content_markdown,
        export_enabled=artifact.export_enabled,
        created_at=artifact.created_at.isoformat(),
    )


def _serialize_run(db: Session, run: DeckGenerationRun) -> DeckGenerationRunResponse:
    deck = db.query(Deck).filter(Deck.id == run.deck_id).one_or_none()
    audience = db.query(AudienceProfile).filter(AudienceProfile.id == run.audience_profile_id).one_or_none() if run.audience_profile_id else None
    artifacts = db.query(DeckArtifact).filter(DeckArtifact.generation_run_id == run.id).order_by(DeckArtifact.created_at.asc()).all()
    telemetry_event_count = db.query(TelemetryEvent).filter(TelemetryEvent.run_id == run.id).count()
    return DeckGenerationRunResponse(
        id=run.id,
        deck_id=run.deck_id,
        deck_title=deck.title if deck else None,
        audience_profile_id=run.audience_profile_id,
        audience_label=audience.label if audience else None,
        provider=run.provider,
        model=run.model,
        status=run.status,
        prompt_summary=run.prompt_summary,
        created_at=run.created_at.isoformat(),
        artifacts=[_serialize_artifact(item) for item in artifacts],
        telemetry_event_count=telemetry_event_count,
    )
