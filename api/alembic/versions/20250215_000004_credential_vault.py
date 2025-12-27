"""Add user credential vault table

Revision ID: 20250215_000004
Revises: 20250107_000003_preview_cache
Create Date: 2025-02-15 00:00:04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20250215_000004"
down_revision: Union[str, None] = "20250107_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user credential vault table and indexes."""
    op.create_table(
        "user_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("encrypted_secret", sa.String(length=4096), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )
    op.create_index(op.f("ix_user_credentials_expires_at"), "user_credentials", ["expires_at"], unique=False)
    op.create_index(op.f("ix_user_credentials_provider"), "user_credentials", ["provider"], unique=False)
    op.create_index(op.f("ix_user_credentials_user_id"), "user_credentials", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop user credential vault table and indexes."""
    op.drop_index(op.f("ix_user_credentials_user_id"), table_name="user_credentials")
    op.drop_index(op.f("ix_user_credentials_provider"), table_name="user_credentials")
    op.drop_index(op.f("ix_user_credentials_expires_at"), table_name="user_credentials")
    op.drop_table("user_credentials")
