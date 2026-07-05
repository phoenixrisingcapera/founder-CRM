"""active venture goal + intro path dispatch linking

Revision ID: 0008_active_goal_intro_linking
Revises: 0007_people_unification
Create Date: 2026-07-05 04:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_active_goal_intro_linking"
down_revision = "0007_people_unification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("founder_workspaces", sa.Column("active_project_id", sa.String(length=36),
                  sa.ForeignKey("projects.id"), nullable=True))
    op.add_column("dispatches", sa.Column("intro_path_id", sa.String(length=36),
                  sa.ForeignKey("intro_paths.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("dispatches", "intro_path_id")
    op.drop_column("founder_workspaces", "active_project_id")
