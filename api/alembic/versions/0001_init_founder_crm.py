"""initial founder crm schema

Revision ID: 0001_init_founder_crm
Revises:
Create Date: 2026-07-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_init_founder_crm"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "founder_workspaces",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column("active_raise_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "funds",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("stage_focus", sa.String(length=80), nullable=True),
        sa.Column("sector_focus", sa.String(length=255), nullable=True),
        sa.Column("check_size", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "contacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("contact_type", sa.String(length=80), nullable=False),
        sa.Column("relationship_status", sa.String(length=80), nullable=False),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "investors",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("fund_id", sa.String(length=36), sa.ForeignKey("funds.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("investor_type", sa.String(length=80), nullable=False),
        sa.Column("preferred_stage", sa.String(length=80), nullable=True),
        sa.Column("sector_relevance", sa.String(length=255), nullable=True),
        sa.Column("thesis", sa.Text(), nullable=True),
        sa.Column("check_fit_notes", sa.Text(), nullable=True),
        sa.Column("portfolio_overlap", sa.Text(), nullable=True),
        sa.Column("warm_intro_path", sa.Text(), nullable=True),
        sa.Column("risk_flags", sa.Text(), nullable=True),
        sa.Column("pipeline_stage", sa.String(length=80), nullable=False),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "pipeline_deals",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("investor_id", sa.String(length=36), sa.ForeignKey("investors.id"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("stage", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("target_raise_amount", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "interaction_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("investor_id", sa.String(length=36), sa.ForeignKey("investors.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "follow_up_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("investor_id", sa.String(length=36), sa.ForeignKey("investors.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "decks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("audience", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("source_file_name", sa.String(length=255), nullable=True),
        sa.Column("source_storage_path", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "deck_slides",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("deck_id", sa.String(length=36), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("slide_order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
    )

    op.create_table(
        "audience_profiles",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )

    op.create_table(
        "deck_generation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("deck_id", sa.String(length=36), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("audience_profile_id", sa.String(length=36), sa.ForeignKey("audience_profiles.id"), nullable=True),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("prompt_summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "deck_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("deck_id", sa.String(length=36), sa.ForeignKey("decks.id"), nullable=False),
        sa.Column("generation_run_id", sa.String(length=36), sa.ForeignKey("deck_generation_runs.id"), nullable=False),
        sa.Column("artifact_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("export_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("deck_artifacts")
    op.drop_table("deck_generation_runs")
    op.drop_table("audience_profiles")
    op.drop_table("deck_slides")
    op.drop_table("decks")
    op.drop_table("follow_up_tasks")
    op.drop_table("interaction_notes")
    op.drop_table("pipeline_deals")
    op.drop_table("investors")
    op.drop_table("contacts")
    op.drop_table("funds")
    op.drop_table("founder_workspaces")
    op.drop_table("users")
