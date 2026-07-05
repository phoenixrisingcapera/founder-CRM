from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session, selectinload

from app.core.security import generate_id
from app.db.models import (
    AdaptationSuggestion,
    AnalysisFinding,
    AnalysisRun,
    Asset,
    BlockClassification,
    Deck,
    DeckExtractionRun,
    DeckFile,
    DeckLlmArtifact,
    DeckSlide,
    DeckSlideAsset,
    DeckSlideBlock,
    DeckSlideRevision,
    DesignToken,
    DesignVersion,
    DesignBatch,
    DeckGenerationWorkspace,
    GeneratedSlide,
    GeneratedSlideCodeVersion,
    GenerationJob,
    SmartDeckMessage,
    SmartDeckPreference,
    SmartDeckWorkspace,
    SmartEditRun,
    SmartEditSuggestion,
    WorkflowJob,
)
from app.services.deck_file_service import ensure_pdf_source, get_stored_file_path
from app.services.deck_llm_artifact_service import rebuild_deck_llm_artifacts
from app.services.deck_state_machine_service import DeckState, canonical_deck_state
from app.services.pdf_deck_extraction_service import extract_pdf_deck_structure
from app.services.smart_deck_job_service import prepare_smart_deck_source_workspace
from app.services.deck_workflow_service import get_deck_workflow_state
from app.services.workflow_job_service import list_workflow_jobs_for_deck


SMART_DECK_GENERATION_ARTIFACT_TYPES = {
    "smart_deck_generation_context",
    "smart_deck_design_version_manifest",
    "generated_slide_render_schema",
    "generated_slide_code_version",
}
WORKFLOW_FAILED_STATUSES = {"failed_retryable", "failed_final", "blocked", "timed_out"}
WORKFLOW_READY_PHASES = {"smart_deck_ready", "preview_ready", "applied", "export_ready"}


def _load_deck(db: Session, deck_id: str) -> Deck | None:
    return (
        db.query(Deck)
        .options(
            selectinload(Deck.file),
            selectinload(Deck.slides).selectinload(DeckSlide.blocks),
            selectinload(Deck.slides).selectinload(DeckSlide.assets),
        )
        .filter(Deck.id == deck_id)
        .first()
    )


def _clear_existing_structure(db: Session, deck: Deck) -> None:
    slide_ids = [slide.id for slide in deck.slides]
    block_ids = [block.id for slide in deck.slides for block in slide.blocks]
    db.query(DeckGenerationWorkspace).filter(DeckGenerationWorkspace.deck_id == deck.id).delete(synchronize_session=False)
    db.query(DeckLlmArtifact).filter(
        DeckLlmArtifact.deck_id == deck.id,
        DeckLlmArtifact.artifact_type.in_(SMART_DECK_GENERATION_ARTIFACT_TYPES),
    ).delete(synchronize_session=False)
    generated_slide_ids = [
        item.id for item in db.query(GeneratedSlide.id).filter(GeneratedSlide.deck_id == deck.id).all()
    ]
    db.query(Asset).filter(Asset.deck_id == deck.id).delete(synchronize_session=False)
    if generated_slide_ids:
        db.query(GeneratedSlideCodeVersion).filter(
            GeneratedSlideCodeVersion.generated_slide_id.in_(generated_slide_ids)
        ).delete(synchronize_session=False)
    db.query(SmartDeckMessage).filter(SmartDeckMessage.deck_id == deck.id).delete(synchronize_session=False)
    db.query(SmartDeckPreference).filter(SmartDeckPreference.deck_id == deck.id).delete(synchronize_session=False)
    db.query(SmartDeckWorkspace).filter(SmartDeckWorkspace.deck_id == deck.id).delete(synchronize_session=False)
    db.query(DesignToken).filter(DesignToken.deck_id == deck.id).delete(synchronize_session=False)
    db.query(GeneratedSlide).filter(GeneratedSlide.deck_id == deck.id).delete(synchronize_session=False)
    db.query(DesignVersion).filter(DesignVersion.deck_id == deck.id).delete(synchronize_session=False)
    db.query(GenerationJob).filter(GenerationJob.deck_id == deck.id).delete(synchronize_session=False)
    db.query(DesignBatch).filter(DesignBatch.deck_id == deck.id).delete(synchronize_session=False)
    db.query(AnalysisRun).filter(AnalysisRun.deck_id == deck.id).delete(synchronize_session=False)
    db.query(AnalysisFinding).filter(AnalysisFinding.deck_id == deck.id).delete(synchronize_session=False)
    db.query(AdaptationSuggestion).filter(AdaptationSuggestion.deck_id == deck.id).delete(synchronize_session=False)
    db.query(SmartEditSuggestion).filter(SmartEditSuggestion.deck_id == deck.id).delete(synchronize_session=False)
    db.query(SmartEditRun).filter(SmartEditRun.deck_id == deck.id).delete(synchronize_session=False)
    db.query(DeckSlideRevision).filter(DeckSlideRevision.deck_id == deck.id).delete(synchronize_session=False)
    if block_ids:
        db.query(BlockClassification).filter(BlockClassification.block_id.in_(block_ids)).delete(synchronize_session=False)
    if slide_ids:
        db.query(DeckSlideAsset).filter(DeckSlideAsset.slide_id.in_(slide_ids)).delete(synchronize_session=False)
        db.query(DeckSlideBlock).filter(DeckSlideBlock.slide_id.in_(slide_ids)).delete(synchronize_session=False)
    db.query(DeckSlide).filter(DeckSlide.deck_id == deck.id).delete(synchronize_session=False)


def _json_object(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _job_output(job: WorkflowJob | None) -> dict | None:
    if job is None or not isinstance(job.output_json, dict):
        return None
    return dict(job.output_json)


def _workflow_backed_deck_state(db: Session, deck: Deck, workflow: dict | None = None) -> str:
    workflow = workflow or get_deck_workflow_state(db, deck.id)
    if workflow is None:
        return canonical_deck_state(deck.status).value

    workflow_status = str(workflow.get("status") or "")
    workflow_phase = str(workflow.get("phase") or "")

    if workflow.get("canOpenSmartDeck") or workflow_phase in WORKFLOW_READY_PHASES:
        return DeckState.READY.value
    if workflow_status in WORKFLOW_FAILED_STATUSES:
        return DeckState.FAILED.value
    if workflow_phase in {"upload_accepted", "source_file_saved"}:
        return DeckState.UPLOADED.value
    if workflow.get("activeJob") or workflow.get("latestJobs"):
        return DeckState.PROCESSING.value
    return canonical_deck_state(deck.status).value


def _source_workspace_from_run(run: DeckExtractionRun | None) -> dict | None:
    if run is None:
        return None
    metrics = _json_object(run.metrics_json)
    source_workspace = metrics.get("sourceWorkspace")
    return source_workspace if isinstance(source_workspace, dict) else None


def _latest_source_pipeline_job(db: Session, deck_id: str) -> WorkflowJob | None:
    job_types = {
        "source_ingestion",
        "source_extraction",
        "miniatures",
        "brand_extraction",
        "smart_deck_context",
        "db_publisher",
    }
    for job in list_workflow_jobs_for_deck(db, deck_id):
        if job.job_type in job_types:
            return job
    return None


def _source_workspace_from_workflow_jobs(db: Session, deck_id: str) -> dict | None:
    preferred_job_types = [
        "smart_deck_context",
        "source_extraction",
        "brand_extraction",
        "miniatures",
        "db_publisher",
    ]
    jobs = list_workflow_jobs_for_deck(db, deck_id)
    for job_type in preferred_job_types:
        for job in jobs:
            if job.job_type != job_type:
                continue
            output = _job_output(job) or {}
            source_workspace = output.get("sourceWorkspace")
            if isinstance(source_workspace, dict):
                return source_workspace
    return None


def _legacy_extraction_run_from_workflow_jobs(db: Session, deck_id: str) -> dict | None:
    job = _latest_source_pipeline_job(db, deck_id)
    if job is None:
        return None
    output = _job_output(job) or {}
    source_workspace = output.get("sourceWorkspace")
    source_enrichment = _source_enrichment_from_workspace(source_workspace if isinstance(source_workspace, dict) else None)
    phase = output.get("publishedPhase") or output.get("phase")
    return {
        "id": job.id,
        "workflowId": f"deckwf_{deck_id}",
        "workflowJobId": job.id,
        "workflowJobType": job.job_type,
        "workflowJobStatus": job.status,
        "workflowPhase": phase if isinstance(phase, str) else None,
        "status": job.status,
        "sourceFormat": output.get("sourceFormat"),
        "slideCount": output.get("slideCount"),
        "blockCount": output.get("blockCount"),
        "assetCount": output.get("assetCount"),
        "errorMessage": job.error_message,
        "sourceWorkspace": source_workspace if isinstance(source_workspace, dict) else None,
        "sourceEnrichment": source_enrichment,
        "metricsJson": output or None,
        "startedAt": job.started_at.isoformat() if job.started_at else None,
        "completedAt": job.completed_at.isoformat() if job.completed_at else None,
    }


def _workflow_job_refs_by_extraction_run(
    db: Session,
    extraction_run_ids: list[str],
) -> dict[str, dict[str, str | None]]:
    run_ids = [run_id for run_id in extraction_run_ids if isinstance(run_id, str) and run_id]
    if not run_ids:
        return {}

    mapping: dict[str, dict[str, str | None]] = {}
    query_jobs = (
        db.query(WorkflowJob)
        .filter(WorkflowJob.extraction_run_id.in_(run_ids))
        .order_by(WorkflowJob.created_at.desc())
        .all()
    )
    for job in query_jobs:
        if job.extraction_run_id and job.extraction_run_id not in mapping:
            mapping[job.extraction_run_id] = {
                "workflowJobId": job.id,
                "workflowJobType": job.job_type,
            }
    return mapping


def _source_enrichment_from_workspace(source_workspace: dict | None) -> dict | None:
    if not source_workspace:
        return None
    return {
        "source": source_workspace.get("enrichmentSource"),
        "llmStatus": source_workspace.get("llmStatus"),
        "provider": source_workspace.get("llmProvider"),
        "model": source_workspace.get("llmModel"),
    }


def _slide_enrichment_metadata(slide: DeckSlide) -> dict:
    metadata = _json_object(slide.metadata_json)
    return {
        "sourceVersion": metadata.get("sourceVersion"),
        "enrichmentSource": metadata.get("semanticEnrichment"),
    }


def _block_enrichment_metadata(block: DeckSlideBlock) -> dict:
    metadata = _json_object(block.metadata_json)
    return {
        "sourceVersion": metadata.get("sourceVersion"),
        "enrichmentSource": metadata.get("semanticEnrichment"),
        "semanticConfidence": metadata.get("semanticConfidence"),
    }


def extract_and_persist_deck_structure(
    db: Session,
    deck_id: str,
    *,
    publish_ready_state: bool = False,
) -> dict:
    deck = _load_deck(db, deck_id)
    if deck is None or deck.file is None:
        raise ValueError("Deck or deck source file not found")

    source_path = get_stored_file_path(deck.file)
    extraction_run = DeckExtractionRun(
        id=generate_id("extract"),
        deck_id=deck.id,
        source_file_id=deck.file.id,
        extractor_name="deterministic_v1",
        source_format=source_path.suffix.lower().removeprefix(".") or None,
        status="running",
        started_at=datetime.utcnow(),
        metadata_json={"sourceFilename": deck.file.original_filename or deck.file.filename},
    )
    db.add(extraction_run)
    db.flush()

    try:
        pdf_path, converted = ensure_pdf_source(deck.file)
        extracted = extract_pdf_deck_structure(pdf_path)

        _clear_existing_structure(db, deck)

        block_count = 0
        asset_count = 0
        partial_error_count = 0
        slides_with_partial_errors = 0
        text_source_counts: dict[str, int] = {}
        asset_type_counts: dict[str, int] = {}
        for slide_payload in extracted["slides"]:
            slide_block_count = len(slide_payload["blocks"])
            slide_asset_count = len(slide_payload["assets"])
            slide_metadata = slide_payload.get("metadataJson") if isinstance(slide_payload.get("metadataJson"), dict) else {}
            extraction_errors = slide_metadata.get("extractionErrors")
            if isinstance(extraction_errors, list) and extraction_errors:
                slides_with_partial_errors += 1
                partial_error_count += len([error for error in extraction_errors if error])
            text_source = str(slide_metadata.get("textSource") or "pdf_text")
            text_source_counts[text_source] = text_source_counts.get(text_source, 0) + 1
            slide = DeckSlide(
                id=generate_id("slide"),
                deck_id=deck.id,
                extraction_run_id=extraction_run.id,
                slide_index=int(slide_payload["slideIndex"]),
                title=str(slide_payload["title"]),
                role=str(slide_payload["role"]),
                raw_text=str(slide_payload["rawText"]),
                narrative_notes=str(slide_payload["narrativeNotes"]),
                source_file_id=deck.file.id,
                source_page_number=int(slide_payload["sourcePageNumber"]),
                thumbnail_path=slide_payload["thumbnailPath"],
                thumbnail_mime_type=slide_payload["thumbnailMimeType"],
                width_points=slide_payload["widthPoints"],
                height_points=slide_payload["heightPoints"],
                block_count=slide_block_count,
                asset_count=slide_asset_count,
                metadata_json=slide_metadata,
            )
            db.add(slide)
            db.flush()

            for block_payload in slide_payload["blocks"]:
                db.add(
                    DeckSlideBlock(
                        id=generate_id("block"),
                        deck_id=deck.id,
                        slide_id=slide.id,
                        extraction_run_id=extraction_run.id,
                        block_index=int(block_payload["blockIndex"]),
                        raw_text=str(block_payload["rawText"]),
                        normalized_text=str(block_payload["normalizedText"]),
                        block_type=str(block_payload["blockType"]),
                        source_kind=block_payload.get("sourceKind"),
                        metadata_json=block_payload.get("metadataJson"),
                    )
                )
                block_count += 1

            for asset_payload in slide_payload["assets"]:
                asset_type = str(asset_payload["assetType"])
                asset_type_counts[asset_type] = asset_type_counts.get(asset_type, 0) + 1
                db.add(
                    DeckSlideAsset(
                        id=generate_id("asset"),
                        deck_id=deck.id,
                        slide_id=slide.id,
                        extraction_run_id=extraction_run.id,
                        asset_type=asset_type,
                        label=asset_payload.get("label"),
                        mime_type=asset_payload.get("mimeType"),
                        storage_provider=str(asset_payload.get("storageProvider") or "local"),
                        storage_path=asset_payload.get("storagePath"),
                        page_number=asset_payload.get("pageNumber"),
                        width=asset_payload.get("width"),
                        height=asset_payload.get("height"),
                        metadata_json=asset_payload.get("metadataJson"),
                    )
                )
                asset_count += 1

        db.flush()
        db.expire(deck, ["slides"])
        artifact_rows = rebuild_deck_llm_artifacts(db, deck, extraction_run.id)
        source_workspace = prepare_smart_deck_source_workspace(
            db,
            deck.id,
            publish_ready_state=publish_ready_state,
        )

        deck.file.page_count = int(extracted["slideCount"])
        summary = f"Structured {extracted['slideCount']} slides from {deck.file.original_filename or deck.file.filename}."

        extraction_run.source_format = extracted["sourceFormat"]
        extraction_run.status = "completed"
        extraction_run.slide_count = int(extracted["slideCount"])
        extraction_run.block_count = block_count
        extraction_run.asset_count = asset_count
        extraction_run.completed_at = datetime.utcnow()
        extraction_run.metadata_json = {
            **(extraction_run.metadata_json or {}),
            "convertedToPdf": converted,
            "convertedPdf": (deck.file.metadata_json or {}).get("convertedPdf"),
        }
        extraction_run.metrics_json = {
            **(extraction_run.metrics_json or {}),
            "artifactCount": len(artifact_rows),
            "artifactTypes": [artifact.artifact_type for artifact in artifact_rows],
            "partialErrorCount": partial_error_count,
            "slidesWithPartialErrors": slides_with_partial_errors,
            "textSourceCounts": text_source_counts,
            "assetTypeCounts": asset_type_counts,
            "sourceWorkspace": source_workspace,
            "sourceEnrichment": _source_enrichment_from_workspace(source_workspace),
        }
        db.flush()
    except Exception as exc:
        extraction_run.status = "failed"
        extraction_run.error_message = str(exc)
        extraction_run.completed_at = datetime.utcnow()
        db.flush()
        raise

    return get_deck_structure(db, deck.id)


def get_deck_structure(db: Session, deck_id: str) -> dict:
    deck = _load_deck(db, deck_id)
    if deck is None:
        raise ValueError("Deck not found")

    workflow = get_deck_workflow_state(db, deck.id) or {}
    source_workspace = _source_workspace_from_workflow_jobs(db, deck.id)
    source_enrichment = _source_enrichment_from_workspace(source_workspace)
    slides = sorted(deck.slides, key=lambda item: item.slide_index)
    deck_state = _workflow_backed_deck_state(db, deck, workflow)
    extraction_run_ids = [
        run_id
        for run_id in {
            *[slide.extraction_run_id for slide in slides if slide.extraction_run_id],
            *[
                asset.extraction_run_id
                for slide in slides
                for asset in slide.assets
                if asset.extraction_run_id
            ],
        }
    ]
    workflow_refs = _workflow_job_refs_by_extraction_run(db, extraction_run_ids)
    return {
        "deckId": deck.id,
        "title": deck.title,
        "workflowId": workflow.get("workflowId"),
        "workflowPhase": workflow.get("phase"),
        "workflowStatus": workflow.get("status"),
        "status": deck_state,
        "state": deck_state,
        "deckStatus": deck_state,
        "sourceWorkspace": source_workspace,
        "sourceEnrichment": source_enrichment,
        "sourceFile": {
            "id": deck.file.id if deck.file else None,
            "filename": deck.file.original_filename or deck.file.filename if deck.file else None,
            "mimeType": deck.file.mime_type if deck.file else None,
            "pageCount": deck.file.page_count if deck.file else None,
        },
        "extractionRun": _legacy_extraction_run_from_workflow_jobs(db, deck.id),
        "slides": [
            {
                "id": slide.id,
                "extractionRunId": slide.extraction_run_id,
                "workflowJobId": (workflow_refs.get(slide.extraction_run_id or "") or {}).get("workflowJobId"),
                "workflowJobType": (workflow_refs.get(slide.extraction_run_id or "") or {}).get("workflowJobType"),
                "slideIndex": slide.slide_index,
                "sourcePageNumber": slide.source_page_number,
                "title": slide.title,
                "role": slide.role,
                "semanticSlideType": slide.semantic_slide_type,
                "summary": slide.summary,
                "textHash": slide.text_hash,
                "rawText": slide.raw_text,
                "thumbnailPath": slide.thumbnail_path,
                "thumbnailMimeType": slide.thumbnail_mime_type,
                "widthPoints": slide.width_points,
                "heightPoints": slide.height_points,
                "sourceVersion": _slide_enrichment_metadata(slide).get("sourceVersion"),
                "enrichmentSource": _slide_enrichment_metadata(slide).get("enrichmentSource"),
                "metadataJson": slide.metadata_json,
                "blocks": [
                    {
                        "id": block.id,
                        "blockIndex": block.block_index,
                        "rawText": block.raw_text,
                        "normalizedText": block.normalized_text,
                        "text": block.text,
                        "blockType": block.block_type,
                        "blockKind": block.block_kind,
                        "semanticRole": block.semantic_role,
                        "contentHash": block.content_hash,
                        "extractionStage": block.extraction_stage,
                        "extractionSource": block.extraction_source,
                        "sourceKind": block.source_kind,
                        "sourceVersion": _block_enrichment_metadata(block).get("sourceVersion"),
                        "enrichmentSource": _block_enrichment_metadata(block).get("enrichmentSource"),
                        "semanticConfidence": _block_enrichment_metadata(block).get("semanticConfidence"),
                        "metadataJson": block.metadata_json,
                    }
                    for block in sorted(slide.blocks, key=lambda item: item.block_index)
                ],
                "assets": [
                    {
                        "id": asset.id,
                        "extractionRunId": asset.extraction_run_id,
                        "workflowJobId": (workflow_refs.get(asset.extraction_run_id or "") or {}).get("workflowJobId"),
                        "workflowJobType": (workflow_refs.get(asset.extraction_run_id or "") or {}).get("workflowJobType"),
                        "assetType": asset.asset_type,
                        "label": asset.label,
                        "mimeType": asset.mime_type,
                        "storageProvider": asset.storage_provider,
                        "storagePath": asset.storage_path,
                        "assetUrl": (
                            f"/api/decks/{deck.id}/slides/{slide.id}/assets/{asset.id}" if asset.storage_path else None
                        ),
                        "pageNumber": asset.page_number,
                        "width": asset.width,
                        "height": asset.height,
                        "metadataJson": asset.metadata_json,
                    }
                    for asset in slide.assets
                ],
            }
            for slide in slides
        ],
    }
