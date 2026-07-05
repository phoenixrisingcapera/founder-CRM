from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)
os.environ.setdefault("APP_ROLE", "migration")

from app.db.session import engine


SCHEMA_REPAIR_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS rate_limit_buckets (
        actor_key VARCHAR PRIMARY KEY,
        window_start TIMESTAMP WITHOUT TIME ZONE NOT NULL,
        request_count INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_rate_limit_buckets_window_start ON rate_limit_buckets (window_start)",
    "CREATE INDEX IF NOT EXISTS ix_rate_limit_buckets_updated_at ON rate_limit_buckets (updated_at)",
    """
    CREATE TABLE IF NOT EXISTS failure_tickets (
        id VARCHAR PRIMARY KEY,
        route VARCHAR NULL,
        page_url TEXT NULL,
        api_path VARCHAR NULL,
        status_code INTEGER NULL,
        user_id VARCHAR NULL,
        user_email VARCHAR NULL,
        deck_id VARCHAR NULL,
        error_name VARCHAR NULL,
        error_message TEXT NULL,
        error_stack TEXT NULL,
        context_json JSON NULL,
        severity VARCHAR NOT NULL DEFAULT 'medium',
        source VARCHAR NOT NULL DEFAULT 'frontend',
        status VARCHAR NOT NULL DEFAULT 'new',
        request_id VARCHAR NULL,
        admin_notes TEXT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        acknowledged_at TIMESTAMP WITHOUT TIME ZONE NULL,
        fixed_at TIMESTAMP WITHOUT TIME ZONE NULL,
        ignored_at TIMESTAMP WITHOUT TIME ZONE NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_route ON failure_tickets (route)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_api_path ON failure_tickets (api_path)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_status_code ON failure_tickets (status_code)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_user_id ON failure_tickets (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_user_email ON failure_tickets (user_email)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_deck_id ON failure_tickets (deck_id)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_severity ON failure_tickets (severity)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_source ON failure_tickets (source)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_status ON failure_tickets (status)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_request_id ON failure_tickets (request_id)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_created_at ON failure_tickets (created_at)",
    "CREATE INDEX IF NOT EXISTS ix_failure_tickets_updated_at ON failure_tickets (updated_at)",
    "ALTER TABLE security_audit_events ADD COLUMN IF NOT EXISTS source_ip VARCHAR NULL",
    "ALTER TABLE security_audit_events ADD COLUMN IF NOT EXISTS request_id VARCHAR NULL",
    "ALTER TABLE security_audit_events ADD COLUMN IF NOT EXISTS user_agent TEXT NULL",
    "CREATE INDEX IF NOT EXISTS ix_security_audit_events_request_id ON security_audit_events (request_id)",
    "ALTER TABLE decks ADD COLUMN IF NOT EXISTS current_design_version_id VARCHAR NULL",
    "CREATE INDEX IF NOT EXISTS ix_decks_current_design_version_id ON decks (current_design_version_id)",
]


def main() -> None:
    with engine.begin() as connection:
        dialect = connection.dialect.name
        if dialect != "postgresql":
            print(f"schema repair skipped for dialect={dialect}")
            return

        for statement in SCHEMA_REPAIR_STATEMENTS:
            connection.execute(text(statement))

    print("production schema repair complete")


if __name__ == "__main__":
    main()
