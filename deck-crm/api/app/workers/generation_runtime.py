from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import DesignVersion, WorkflowJob
from app.schemas.smart_deck import CreateSmartDeckGenerationJobInput
from app.services.deck_processing_worker_service import _dependency_output, _job_payload
from app.services.smart_deck_llm_service import apply_design_version, create_generation_job
from app.services.workflow_job_service import (
    JOB_STATUS_COMPLETED,
    JOB_TYPE_LLM_GENERATION,
    JOB_TYPE_SCHEMA_VALIDATION,
    record_workflow_artifact,
    set_workflow_job_status,
)


def handle_llm_generation(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    payload = CreateSmartDeckGenerationJobInput(**_job_payload(job))
    result = create_generation_job(db, job.deck_id, payload, run_id=job.id)
    if result is None:
        raise ValueError("Deck not found")
    generation_job, design_version, workspace = result
    set_workflow_job_status(
        db,
        job=job,
        status=JOB_STATUS_COMPLETED,
        worker_id=worker_id,
        message="LLM generation completed.",
        output_payload={
            "phase": "generation_running",
            "generationJob": generation_job,
            "designVersionId": design_version.get("id"),
            "generatedVersionCount": len(design_version.get("generatedSlides", [])),
            "workspaceId": workspace.get("workspace", {}).get("id") if isinstance(workspace.get("workspace"), dict) else None,
            "generationStatus": "completed",
        },
    )
    db.commit()


def handle_schema_validation(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    generation_output = _dependency_output(db, job, JOB_TYPE_LLM_GENERATION)
    design_version_id = generation_output.get("designVersionId")
    if not design_version_id:
        raise ValueError("Schema validation cannot run without a generated designVersionId.")
    version = (
        db.query(DesignVersion)
        .filter(DesignVersion.deck_id == job.deck_id, DesignVersion.id == design_version_id)
        .one_or_none()
    )
    if version is None:
        raise ValueError("Schema validation cannot find the generated design version.")
    slides = sorted(version.generated_slides, key=lambda item: item.slide_number)
    if not slides:
        raise ValueError("Schema validation cannot run without generated slides.")
    missing_schema_slide_ids = [slide.id for slide in slides if not slide.render_schema_json]
    if missing_schema_slide_ids:
        raise ValueError("Schema validation found generated slides without render_schema_json.")
    set_workflow_job_status(
        db,
        job=job,
        status=JOB_STATUS_COMPLETED,
        worker_id=worker_id,
        message="Schema validation stage completed.",
        output_payload={
            "phase": "generation_running",
            "designVersionId": design_version_id,
            "workspaceId": generation_output.get("workspaceId"),
            "generationJob": generation_output.get("generationJob"),
            "validationStatus": "passed",
            "validatedSlideCount": len(slides),
        },
    )
    db.commit()


def handle_preview_render(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    schema_output = _dependency_output(db, job, JOB_TYPE_SCHEMA_VALIDATION)
    generation_output = _dependency_output(db, job, JOB_TYPE_LLM_GENERATION)
    design_version_id = schema_output.get("designVersionId") or generation_output.get("designVersionId")
    workspace_id = schema_output.get("workspaceId") or generation_output.get("workspaceId")
    if not design_version_id:
        raise ValueError("Preview render cannot run without a generated designVersionId.")
    version = (
        db.query(DesignVersion)
        .filter(DesignVersion.deck_id == job.deck_id, DesignVersion.id == design_version_id)
        .one_or_none()
    )
    if version is None:
        raise ValueError("Preview render cannot find the generated design version.")
    slides = sorted(version.generated_slides, key=lambda item: item.slide_number)
    if not slides:
        raise ValueError("Preview render cannot run without generated slides.")
    manifest_key = version.bucket_manifest_key or f"workflow/design-version-manifests/{design_version_id}.json"
    record_workflow_artifact(
        db,
        job=job,
        artifact_type="design_version_manifest",
        storage_key=manifest_key,
        metadata={
            "designVersionId": design_version_id,
            "generatedSlideCount": len(slides),
            "hasStoredManifest": bool(version.bucket_manifest_key),
        },
    )
    set_workflow_job_status(
        db,
        job=job,
        status=JOB_STATUS_COMPLETED,
        worker_id=worker_id,
        message="Preview render stage completed.",
        output_payload={
            "phase": "preview_ready",
            "designVersionId": design_version_id,
            "workspaceId": workspace_id,
            "renderStatus": "completed",
            "previewRenderable": bool(design_version_id),
            "generatedSlideCount": len(slides),
            "manifestKey": manifest_key,
        },
    )
    db.commit()


def handle_apply_version(db: Session, job: WorkflowJob, *, worker_id: str) -> None:
    payload = _job_payload(job)
    design_version_id = str(payload.get("designVersionId") or "").strip()
    if not design_version_id:
        raise ValueError("Workflow apply-version job is missing designVersionId.")
    result = apply_design_version(db, job.deck_id, design_version_id)
    if result is None:
        raise ValueError("Design version not found")
    set_workflow_job_status(
        db,
        job=job,
        status=JOB_STATUS_COMPLETED,
        worker_id=worker_id,
        message="Apply version completed.",
        output_payload={
            "phase": "apply_running",
            "designVersionId": design_version_id,
            "applyResult": result,
        },
    )
    db.commit()
