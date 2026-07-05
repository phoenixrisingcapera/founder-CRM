from __future__ import annotations

from collections.abc import Callable
from app.services.workflow_job_service import (
    JOB_TYPE_APPLY_VERSION,
    JOB_TYPE_BRAND_EXTRACTION,
    JOB_TYPE_DB_PUBLISHER,
    JOB_TYPE_EXPORT,
    JOB_TYPE_LLM_GENERATION,
    JOB_TYPE_LLM_PARALLELIZATION,
    JOB_TYPE_MINIATURES,
    JOB_TYPE_PREVIEW_RENDER,
    JOB_TYPE_SCHEMA_VALIDATION,
    JOB_TYPE_SMART_DECK_CONTEXT,
    JOB_TYPE_SOURCE_EXTRACTION,
    JOB_TYPE_SOURCE_INGESTION,
)

def get_workflow_job_handler(job_type: str) -> Callable[..., None] | None:
    if job_type == JOB_TYPE_SOURCE_INGESTION:
        from app.workers.source_pipeline_runtime import handle_source_ingestion

        return handle_source_ingestion
    if job_type == JOB_TYPE_SOURCE_EXTRACTION:
        from app.workers.source_pipeline_runtime import handle_source_extraction

        return handle_source_extraction
    if job_type == JOB_TYPE_MINIATURES:
        from app.workers.source_pipeline_runtime import handle_miniatures

        return handle_miniatures
    if job_type == JOB_TYPE_BRAND_EXTRACTION:
        from app.workers.source_pipeline_runtime import handle_brand_extraction

        return handle_brand_extraction
    if job_type == JOB_TYPE_SMART_DECK_CONTEXT:
        from app.workers.source_pipeline_runtime import handle_smart_deck_context

        return handle_smart_deck_context
    if job_type == JOB_TYPE_LLM_GENERATION:
        from app.workers.generation_runtime import handle_llm_generation

        return handle_llm_generation
    if job_type == JOB_TYPE_LLM_PARALLELIZATION:
        from app.workers.llm_parallelization_runtime import handle_llm_parallelization

        return handle_llm_parallelization
    if job_type == JOB_TYPE_SCHEMA_VALIDATION:
        from app.workers.generation_runtime import handle_schema_validation

        return handle_schema_validation
    if job_type == JOB_TYPE_PREVIEW_RENDER:
        from app.workers.generation_runtime import handle_preview_render

        return handle_preview_render
    if job_type == JOB_TYPE_APPLY_VERSION:
        from app.workers.generation_runtime import handle_apply_version

        return handle_apply_version
    if job_type == JOB_TYPE_DB_PUBLISHER:
        from app.workers.publisher_runtime import handle_db_publisher

        return handle_db_publisher
    if job_type == JOB_TYPE_EXPORT:
        from app.workers.publisher_runtime import handle_export

        return handle_export
    return None
