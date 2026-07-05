from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

os.environ["APP_ROLE"] = "migration"

from app.core.config import settings

DDL = [
    "ALTER TABLE IF EXISTS decks ADD COLUMN IF NOT EXISTS user_id VARCHAR",
    "ALTER TABLE IF EXISTS decks ADD COLUMN IF NOT EXISTS original_filename VARCHAR",
    "ALTER TABLE IF EXISTS decks ADD COLUMN IF NOT EXISTS source_type VARCHAR",
    "ALTER TABLE IF EXISTS decks ADD COLUMN IF NOT EXISTS slide_count INTEGER",
    "ALTER TABLE IF EXISTS decks ADD COLUMN IF NOT EXISTS description TEXT",
    "ALTER TABLE IF EXISTS decks ADD COLUMN IF NOT EXISTS metadata_json JSON",
    "ALTER TABLE IF EXISTS decks ADD COLUMN IF NOT EXISTS summary TEXT DEFAULT ''",
    "ALTER TABLE IF EXISTS decks ADD COLUMN IF NOT EXISTS current_design_version_id VARCHAR",
    "ALTER TABLE IF EXISTS design_versions ADD COLUMN IF NOT EXISTS bucket_manifest_key VARCHAR",
    "ALTER TABLE IF EXISTS generated_slides ADD COLUMN IF NOT EXISTS current_version_id VARCHAR",
    "ALTER TABLE IF EXISTS security_audit_events ADD COLUMN IF NOT EXISTS request_id VARCHAR",
    "ALTER TABLE IF EXISTS security_audit_events ADD COLUMN IF NOT EXISTS source_ip VARCHAR",
    "ALTER TABLE IF EXISTS security_audit_events ADD COLUMN IF NOT EXISTS user_agent TEXT",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS original_filename VARCHAR",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS file_role VARCHAR DEFAULT 'original_upload'",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS file_extension VARCHAR",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS storage_provider VARCHAR DEFAULT 'local'",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS storage_path VARCHAR",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS checksum_sha256 VARCHAR(64)",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS page_count INTEGER",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS metadata_json JSON",
    "ALTER TABLE IF EXISTS deck_files ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP WITHOUT TIME ZONE",
    "ALTER TABLE IF EXISTS workspaces ADD COLUMN IF NOT EXISTS user_id VARCHAR",
    "ALTER TABLE IF EXISTS workspaces ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITHOUT TIME ZONE",
    "ALTER TABLE IF EXISTS workspaces ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE",
    """
    CREATE TABLE IF NOT EXISTS deck_input_sources (
        id VARCHAR PRIMARY KEY,
        deck_id VARCHAR REFERENCES decks(id) ON DELETE CASCADE,
        source_type VARCHAR,
        label VARCHAR,
        original_filename VARCHAR,
        mime_type VARCHAR,
        storage_path VARCHAR,
        external_url VARCHAR,
        text_value TEXT,
        status VARCHAR DEFAULT 'ready',
        created_at TIMESTAMP WITHOUT TIME ZONE,
        updated_at TIMESTAMP WITHOUT TIME ZONE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS deck_product_events (
        id VARCHAR PRIMARY KEY,
        workspace_id VARCHAR,
        user_id VARCHAR,
        deck_id VARCHAR,
        session_id VARCHAR,
        event_name VARCHAR,
        surface VARCHAR,
        route TEXT,
        entity_type VARCHAR,
        entity_id VARCHAR,
        event_version INTEGER DEFAULT 1,
        metadata_json JSON,
        source_ip VARCHAR,
        user_agent TEXT,
        request_id VARCHAR,
        created_at TIMESTAMP WITHOUT TIME ZONE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rate_limit_buckets (
        actor_key VARCHAR PRIMARY KEY,
        window_start TIMESTAMP WITHOUT TIME ZONE NOT NULL,
        request_count INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP WITHOUT TIME ZONE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS failure_tickets (
        id VARCHAR PRIMARY KEY,
        route VARCHAR,
        page_url TEXT,
        api_path VARCHAR,
        status_code INTEGER,
        user_id VARCHAR,
        user_email VARCHAR,
        deck_id VARCHAR,
        error_name VARCHAR,
        error_message TEXT,
        error_stack TEXT,
        context_json JSON,
        severity VARCHAR DEFAULT 'medium',
        source VARCHAR DEFAULT 'frontend',
        status VARCHAR DEFAULT 'new',
        request_id VARCHAR,
        admin_notes TEXT,
        created_at TIMESTAMP WITHOUT TIME ZONE,
        updated_at TIMESTAMP WITHOUT TIME ZONE,
        acknowledged_at TIMESTAMP WITHOUT TIME ZONE,
        fixed_at TIMESTAMP WITHOUT TIME ZONE,
        ignored_at TIMESTAMP WITHOUT TIME ZONE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_jobs (
        id VARCHAR PRIMARY KEY,
        deck_id VARCHAR REFERENCES decks(id) ON DELETE CASCADE,
        workspace_id VARCHAR REFERENCES workspaces(id) ON DELETE SET NULL,
        user_id VARCHAR REFERENCES users(id) ON DELETE SET NULL,
        extraction_run_id VARCHAR REFERENCES deck_extraction_runs(id) ON DELETE SET NULL,
        job_type VARCHAR NOT NULL,
        status VARCHAR NOT NULL DEFAULT 'queued',
        priority INTEGER NOT NULL DEFAULT 50,
        idempotency_key VARCHAR,
        input_json JSON,
        output_json JSON,
        error_code VARCHAR,
        error_message TEXT,
        attempt_count INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 2,
        heartbeat_at TIMESTAMP WITHOUT TIME ZONE,
        locked_by VARCHAR,
        locked_until TIMESTAMP WITHOUT TIME ZONE,
        recovery_count INTEGER NOT NULL DEFAULT 0,
        last_recovered_at TIMESTAMP WITHOUT TIME ZONE,
        last_recovered_by VARCHAR,
        terminal_reason VARCHAR,
        published_phase VARCHAR,
        published_at TIMESTAMP WITHOUT TIME ZONE,
        queued_at TIMESTAMP WITHOUT TIME ZONE,
        started_at TIMESTAMP WITHOUT TIME ZONE,
        completed_at TIMESTAMP WITHOUT TIME ZONE,
        failed_at TIMESTAMP WITHOUT TIME ZONE,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_workflow_jobs_deck_job_type_idempotency UNIQUE (deck_id, job_type, idempotency_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_job_events (
        id VARCHAR PRIMARY KEY,
        job_id VARCHAR REFERENCES workflow_jobs(id) ON DELETE CASCADE,
        event_type VARCHAR NOT NULL,
        from_status VARCHAR,
        to_status VARCHAR,
        message TEXT,
        metadata_json JSON,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_job_artifacts (
        id VARCHAR PRIMARY KEY,
        job_id VARCHAR REFERENCES workflow_jobs(id) ON DELETE CASCADE,
        deck_id VARCHAR REFERENCES decks(id) ON DELETE CASCADE,
        artifact_type VARCHAR NOT NULL,
        storage_key VARCHAR NOT NULL,
        content_hash VARCHAR(64),
        metadata_json JSON,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_workflow_job_artifacts_job_type_storage UNIQUE (job_id, artifact_type, storage_key)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflow_job_dependencies (
        id VARCHAR PRIMARY KEY,
        job_id VARCHAR REFERENCES workflow_jobs(id) ON DELETE CASCADE,
        depends_on_job_id VARCHAR REFERENCES workflow_jobs(id) ON DELETE CASCADE,
        dependency_type VARCHAR NOT NULL DEFAULT 'requires_completion',
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_workflow_job_dependencies_edge UNIQUE (job_id, depends_on_job_id, dependency_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_telemetry_events (
        id VARCHAR PRIMARY KEY,
        workspace_id VARCHAR,
        deck_id VARCHAR,
        user_id VARCHAR,
        run_id VARCHAR,
        run_type VARCHAR NOT NULL,
        step_id VARCHAR,
        event_name VARCHAR NOT NULL,
        event_level VARCHAR NOT NULL,
        status VARCHAR,
        provider VARCHAR,
        model VARCHAR,
        latency_ms INTEGER,
        input_tokens INTEGER,
        output_tokens INTEGER,
        estimated_cost_cents DOUBLE PRECISION,
        error_category VARCHAR,
        error_message_redacted TEXT,
        trace_id VARCHAR,
        span_id VARCHAR,
        request_id VARCHAR,
        metadata_json JSON,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
    )
    """,
    "ALTER TABLE IF EXISTS workflow_jobs ADD COLUMN IF NOT EXISTS recovery_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE IF EXISTS workflow_jobs ADD COLUMN IF NOT EXISTS last_recovered_at TIMESTAMP WITHOUT TIME ZONE",
    "ALTER TABLE IF EXISTS workflow_jobs ADD COLUMN IF NOT EXISTS last_recovered_by VARCHAR",
    "ALTER TABLE IF EXISTS workflow_jobs ADD COLUMN IF NOT EXISTS terminal_reason VARCHAR",
    "ALTER TABLE IF EXISTS workflow_jobs ADD COLUMN IF NOT EXISTS published_phase VARCHAR",
    "ALTER TABLE IF EXISTS workflow_jobs ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITHOUT TIME ZONE",
    "CREATE INDEX IF NOT EXISTS ix_decks_user_id ON decks (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_decks_current_design_version_id ON decks (current_design_version_id)",
    "CREATE INDEX IF NOT EXISTS ix_generated_slides_current_version_id ON generated_slides (current_version_id)",
    "CREATE INDEX IF NOT EXISTS ix_deck_files_file_role ON deck_files (file_role)",
    "CREATE INDEX IF NOT EXISTS ix_deck_input_sources_deck_id ON deck_input_sources (deck_id)",
    "CREATE INDEX IF NOT EXISTS ix_deck_input_sources_source_type ON deck_input_sources (source_type)",
    "CREATE INDEX IF NOT EXISTS ix_deck_product_events_workspace_id ON deck_product_events (workspace_id)",
    "CREATE INDEX IF NOT EXISTS ix_deck_product_events_user_id ON deck_product_events (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_deck_product_events_deck_id ON deck_product_events (deck_id)",
    "CREATE INDEX IF NOT EXISTS ix_deck_product_events_event_name ON deck_product_events (event_name)",
    "CREATE INDEX IF NOT EXISTS ix_deck_product_events_surface ON deck_product_events (surface)",
    "CREATE INDEX IF NOT EXISTS ix_deck_product_events_created_at ON deck_product_events (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_rate_limit_buckets_window_start ON rate_limit_buckets (window_start)",
    "CREATE INDEX IF NOT EXISTS ix_rate_limit_buckets_updated_at ON rate_limit_buckets (updated_at)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_api_path ON failure_tickets (api_path)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_deck_id ON failure_tickets (deck_id)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_request_id ON failure_tickets (request_id)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_status ON failure_tickets (status)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_status_code ON failure_tickets (status_code)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_user_id ON failure_tickets (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_security_audit_events_request_id ON security_audit_events (request_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_deck_id ON workflow_jobs (deck_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_deck_created_at ON workflow_jobs (deck_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_workspace_id ON workflow_jobs (workspace_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_user_id ON workflow_jobs (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_extraction_run_id ON workflow_jobs (extraction_run_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_job_type ON workflow_jobs (job_type)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_status ON workflow_jobs (status)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_idempotency_key ON workflow_jobs (idempotency_key)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_heartbeat_at ON workflow_jobs (heartbeat_at)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_claim ON workflow_jobs (status, job_type, priority, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_recovery_scan ON workflow_jobs (status, heartbeat_at, locked_until)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_recovery_count ON workflow_jobs (recovery_count)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_last_recovered_at ON workflow_jobs (last_recovered_at)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_terminal_reason ON workflow_jobs (terminal_reason)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_jobs_published_phase ON workflow_jobs (published_phase)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_job_events_job_id ON workflow_job_events (job_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_job_events_event_type ON workflow_job_events (event_type)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_job_artifacts_job_id ON workflow_job_artifacts (job_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_job_artifacts_deck_id ON workflow_job_artifacts (deck_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_job_artifacts_artifact_type ON workflow_job_artifacts (artifact_type)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_job_artifacts_storage_key ON workflow_job_artifacts (storage_key)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_job_dependencies_job_id ON workflow_job_dependencies (job_id)",
    "CREATE INDEX IF NOT EXISTS ix_workflow_job_dependencies_depends_on_job_id ON workflow_job_dependencies (depends_on_job_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_workspace_id ON agent_telemetry_events (workspace_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_deck_id ON agent_telemetry_events (deck_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_user_id ON agent_telemetry_events (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_run_id ON agent_telemetry_events (run_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_run_type ON agent_telemetry_events (run_type)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_step_id ON agent_telemetry_events (step_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_event_name ON agent_telemetry_events (event_name)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_event_level ON agent_telemetry_events (event_level)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_status ON agent_telemetry_events (status)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_provider ON agent_telemetry_events (provider)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_error_category ON agent_telemetry_events (error_category)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_trace_id ON agent_telemetry_events (trace_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_span_id ON agent_telemetry_events (span_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_request_id ON agent_telemetry_events (request_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_telemetry_events_created_at ON agent_telemetry_events (created_at)",
]

VERIFY_SQL = [
    "SELECT current_design_version_id FROM decks LIMIT 0",
    "SELECT bucket_manifest_key FROM design_versions LIMIT 0",
    "SELECT current_version_id FROM generated_slides LIMIT 0",
    "SELECT request_id FROM security_audit_events LIMIT 0",
    "SELECT actor_key FROM rate_limit_buckets LIMIT 0",
    "SELECT id FROM failure_tickets LIMIT 0",
    "SELECT storage_path FROM deck_files LIMIT 0",
    "SELECT source_type FROM deck_input_sources LIMIT 0",
    "SELECT event_name FROM deck_product_events LIMIT 0",
    "SELECT job_type FROM workflow_jobs LIMIT 0",
    "SELECT event_type FROM workflow_job_events LIMIT 0",
    "SELECT artifact_type FROM workflow_job_artifacts LIMIT 0",
    "SELECT dependency_type FROM workflow_job_dependencies LIMIT 0",
    "SELECT event_name FROM agent_telemetry_events LIMIT 0",
]


def main() -> int:
    engine = create_engine(settings.database_url)
    with engine.begin() as connection:
        for statement in DDL:
            connection.execute(text(statement))
        for statement in VERIFY_SQL:
            connection.execute(text(statement))
    print("Runtime schema bootstrap completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
