"""goal scores and ai artifacts

Revision ID: 0009_goal_scores_ai_artifacts
Revises: 0008_active_goal_intro_linking
Create Date: 2026-07-05 16:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_goal_scores_ai_artifacts"
down_revision = "0008_active_goal_intro_linking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "goal_scores",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("opportunity_id", sa.String(length=36), sa.ForeignKey("opportunities.id"), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("relationship_strength_score", sa.Integer(), nullable=False),
        sa.Column("warm_path_score", sa.Integer(), nullable=False),
        sa.Column("sector_fit_score", sa.Integer(), nullable=False),
        sa.Column("stage_fit_score", sa.Integer(), nullable=False),
        sa.Column("recency_score", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("reasons_json", sa.Text(), nullable=True),
        sa.Column("missing_data_json", sa.Text(), nullable=True),
        sa.Column("recommended_next_action", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ai_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True),
        sa.Column("company_id", sa.String(length=36), sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("opportunity_id", sa.String(length=36), sa.ForeignKey("opportunities.id"), nullable=True),
        sa.Column("goal_score_id", sa.String(length=36), sa.ForeignKey("goal_scores.id"), nullable=True),
        sa.Column("artifact_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_artifacts")
    op.drop_table("goal_scores")
