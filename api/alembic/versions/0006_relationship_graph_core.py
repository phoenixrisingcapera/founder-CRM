"""relationship graph core

Revision ID: 0006_relationship_graph_core
Revises: 0005_venture_workflow_core
Create Date: 2026-07-05 02:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_relationship_graph_core"
down_revision = "0005_venture_workflow_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "relationship_edges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("source_contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("target_contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("target_company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("strength", sa.String(length=40), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "intro_paths",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("from_contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=False),
        sa.Column("to_investor_id", sa.String(length=36), sa.ForeignKey("investors.id"), nullable=True),
        sa.Column("to_contact_id", sa.String(length=36), sa.ForeignKey("contacts.id"), nullable=True),
        sa.Column("path_label", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("intro_paths")
    op.drop_table("relationship_edges")
