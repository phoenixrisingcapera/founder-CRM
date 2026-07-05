"""venture workflow core models

Revision ID: 0005_venture_workflow_core
Revises: 0004_artifact_status
Create Date: 2026-07-05 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_venture_workflow_core"
down_revision = "0004_artifact_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("company_type", sa.String(length=80), nullable=False),
        sa.Column("sector", sa.String(length=120), nullable=True),
        sa.Column("geography", sa.String(length=120), nullable=True),
        sa.Column("relationship_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("goal_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "dispatches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("person_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("next_step", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("investor_id", sa.String(length=36), sa.ForeignKey("investors.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("opportunity_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("value_label", sa.String(length=120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("opportunities")
    op.drop_table("dispatches")
    op.drop_table("projects")
    op.drop_table("companies")
