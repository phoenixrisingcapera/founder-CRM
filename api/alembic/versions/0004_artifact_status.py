"""artifact status column

Revision ID: 0004_artifact_status
Revises: 0003_observability_admin
Create Date: 2026-07-05 01:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_artifact_status"
down_revision = "0003_observability_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deck_artifacts", sa.Column("artifact_status", sa.String(length=40), nullable=True))
    op.execute("UPDATE deck_artifacts SET artifact_status = 'draft' WHERE artifact_status IS NULL")
    op.alter_column("deck_artifacts", "artifact_status", nullable=False)


def downgrade() -> None:
    op.drop_column("deck_artifacts", "artifact_status")
