"""observability admin tables

Revision ID: 0003_observability_admin
Revises: 0002_auth_pipeline_keys
Create Date: 2026-07-05 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_observability_admin"
down_revision = "0002_auth_pipeline_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("deck_id", sa.String(length=36), sa.ForeignKey("decks.id"), nullable=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("deck_generation_runs.id"), nullable=True),
        sa.Column("event_name", sa.String(length=120), nullable=False),
        sa.Column("event_level", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "failure_tickets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("route", sa.String(length=255), nullable=True),
        sa.Column("page_url", sa.String(length=512), nullable=True),
        sa.Column("api_path", sa.String(length=255), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("error_name", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("error_stack", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=120), nullable=True),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("failure_tickets")
    op.drop_table("telemetry_events")
