from __future__ import annotations

from pyspark.sql import SparkSession
from sqlalchemy.orm import Session

from app.db.models import Deck
from app.services.llm_parallelization_service import (
    build_llm_parallelization_batches,
    summarize_parallelization_manifest,
    summarize_parallelization_result,
)
from app.services.workflow_job_service import JOB_STATUS_COMPLETED, record_workflow_artifact, set_workflow_job_status


def _spark_session(partition_count: int) -> SparkSession:
    return (
        SparkSession.builder.master(f"local[{max(1, partition_count)}]")
        .appName("deck-llm-parallelization")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", str(max(1, partition_count)))
        .getOrCreate()
    )


def handle_llm_parallelization(db: Session, job, *, worker_id: str) -> None:
    payload = dict(job.input_json or {})
    prompt = str(payload.get("prompt") or "").strip()
    selected_source_slide_ids = list(payload.get("selectedSourceSlideIds") or [])
    partition_count = int(payload.get("partitionCount") or 1)
    batch_size = int(payload.get("batchSize") or 8)

    deck = db.query(Deck).filter(Deck.id == job.deck_id).one_or_none()
    if deck is None:
        raise ValueError("Deck not found")
    if not prompt:
        raise ValueError("LLM parallelization requires a prompt.")
    if not selected_source_slide_ids:
        raise ValueError("LLM parallelization requires at least one selected source slide.")

    plan = build_llm_parallelization_batches(
        db,
        deck=deck,
        selected_source_slide_ids=selected_source_slide_ids,
        prompt=prompt,
        partition_count=partition_count,
        batch_size=batch_size,
    )
    tasks = plan["tasks"]
    if not tasks:
        raise ValueError("LLM parallelization did not build any tasks.")

    spark = _spark_session(plan["partitionCount"])
    try:
        slice_count = min(max(1, plan["partitionCount"]), len(tasks))

        def _execute(task: dict) -> dict:
            return summarize_parallelization_result(task, prompt=plan["prompt"])

        results = spark.sparkContext.parallelize(tasks, slice_count).map(_execute).collect()
    finally:
        spark.stop()

    manifest = summarize_parallelization_manifest(tasks, results)
    artifact_key = f"workflow/llm-parallelization/{job.id}.json"
    record_workflow_artifact(
        db,
        job=job,
        artifact_type="llm_parallelization_manifest",
        storage_key=artifact_key,
        metadata={
            "deckId": deck.id,
            "partitionCount": plan["partitionCount"],
            "batchSize": plan["batchSize"],
            "taskCount": manifest["taskCount"],
            "resultCount": manifest["resultCount"],
        },
    )
    set_workflow_job_status(
        db,
        job=job,
        status=JOB_STATUS_COMPLETED,
        worker_id=worker_id,
        message="LLM parallelization completed.",
        published_phase=None,
        output_payload={
            "phase": "llm_parallelization_ready",
            "parallelization": {
                "deckId": deck.id,
                "deckTitle": deck.title,
                "prompt": plan["prompt"],
                "partitionCount": plan["partitionCount"],
                "batchSize": plan["batchSize"],
                "selectedSourceSlideIds": plan["selectedSourceSlideIds"],
                "taskCount": manifest["taskCount"],
                "resultCount": manifest["resultCount"],
                "artifactStorageKey": artifact_key,
            },
            "tasks": tasks,
            "results": results,
            "summary": manifest,
        },
    )
    db.commit()

