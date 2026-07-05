"""auth pipeline and key storage

Revision ID: 0002_auth_pipeline_keys
Revises: 0001_init_founder_crm
Create Date: 2026-07-05 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_auth_pipeline_keys"
down_revision = "0001_init_founder_crm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.execute("UPDATE users SET password_hash = 'demo$reset-required' WHERE password_hash IS NULL")
    op.alter_column("users", "password_hash", nullable=False)
    op.create_table(
        "user_api_keys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_api_keys")
    op.drop_column("users", "password_hash")
