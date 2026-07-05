from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.deps import get_db
from app.db.models import WorkflowJob
from app.services.workflow_job_service import JOB_STATUS_FAILED_RETRYABLE, JOB_STATUS_QUEUED, JOB_STATUS_RUNNING
from app.services.upload_storage import get_upload_storage

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "deck-aistack-codes-backend"}


@router.get("/health/storage")
def storage_health(db: Session = Depends(get_db)) -> dict:
    required: dict[str, bool] = {}
    if settings.upload_storage_backend == "s3":
        required = {
            "bucket": bool(settings.upload_storage_s3_bucket),
            "region": bool(settings.upload_storage_s3_region),
            "accessKey": bool(settings.railway_bucket_access_key),
            "secretKey": bool(settings.railway_bucket_secret_key),
        }
    elif settings.upload_storage_backend == "supabase":
        required = {
            "url": bool(settings.supabase_url),
            "serviceRoleKey": bool(settings.supabase_service_role_key),
            "bucket": bool(settings.supabase_storage_bucket),
        }

    config_ok = all(required.values()) if required else settings.upload_storage_backend == "local"
    runtime_error = None
    try:
        storage = get_upload_storage()
        provider = storage.provider
    except Exception as exc:
        provider = settings.upload_storage_backend
        config_ok = False
        runtime_error = exc.__class__.__name__

    queue_counts = db.query(WorkflowJob.status, WorkflowJob.id).all()
    actionable_statuses = {JOB_STATUS_QUEUED, JOB_STATUS_FAILED_RETRYABLE}
    active_statuses = actionable_statuses | {JOB_STATUS_RUNNING}
    queue_depth = sum(1 for status, _job_id in queue_counts if str(status) in active_statuses)
    queued_count = sum(1 for status, _job_id in queue_counts if str(status) in actionable_statuses)

    return {
        "status": "ok" if config_ok else "degraded",
        "provider": provider,
        "queue": {
            "active": queue_depth,
            "queued": queued_count,
        },
        "config": {
            "requiredValuesPresent": required,
            "hasEndpoint": bool(settings.upload_storage_s3_endpoint_url),
            "hasPrefix": bool(settings.upload_storage_s3_prefix),
        },
        "runtimeError": runtime_error,
    }


@router.get("/health/worker")
def worker_health(db: Session = Depends(get_db)) -> dict:
    actionable_statuses = {JOB_STATUS_QUEUED, JOB_STATUS_FAILED_RETRYABLE}
    active_statuses = actionable_statuses | {JOB_STATUS_RUNNING}
    queued_jobs = (
        db.query(WorkflowJob)
        .filter(WorkflowJob.status.in_(tuple(active_statuses)))
        .order_by(WorkflowJob.queued_at.asc().nullsfirst(), WorkflowJob.created_at.asc())
        .all()
    )
    queued_count = sum(1 for job in queued_jobs if str(job.status) in actionable_statuses)
    active_count = len(queued_jobs)
    oldest_queued = next((job for job in queued_jobs if str(job.status) in active_statuses), None)
    oldest_queued_age_seconds = None
    if oldest_queued is not None:
        anchor = oldest_queued.queued_at or oldest_queued.updated_at or oldest_queued.created_at
        if anchor is not None:
            if anchor.tzinfo is None:
                anchor = anchor.replace(tzinfo=timezone.utc)
            oldest_queued_age_seconds = max(0, int((datetime.now(timezone.utc) - anchor).total_seconds()))

    worker_required = active_count > 0 or queued_count > 0
    blocked = bool(oldest_queued_age_seconds is not None and oldest_queued_age_seconds > 300)

    return {
        "status": "degraded" if blocked else "ok",
        "workerRequired": worker_required,
        "blocked": blocked,
        "queue": {
            "active": active_count,
            "queued": queued_count,
            "oldestQueuedAgeSeconds": oldest_queued_age_seconds,
        },
        "recommendation": (
            "Queued workflow jobs exist but have not been drained recently."
            if blocked
            else "Workflow job queue is healthy or idle."
        ),
        "appRole": settings.app_role,
    }
