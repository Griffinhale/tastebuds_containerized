"""preview cache and quota tables

Revision ID: 20250107_000003
Revises: 20240620_000002
Create Date: 2025-01-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20250107_000003"
down_revision = "20240620_000002"
branch_labels = None
depends_on = None

media_type_enum = postgresql.ENUM(
    "book",
    "movie",
    "tv",
    "game",
    "music",
    name="media_type",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "external_search_previews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_name", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("media_type", media_type_enum, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("cover_image_url", sa.String(length=1024), nullable=True),
        sa.Column("canonical_url", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "source_name", "external_id", name="uq_preview_per_user"),
    )
    op.create_index("ix_external_search_previews_user_id", "external_search_previews", ["user_id"], unique=False)
    op.create_index(
        "ix_external_search_previews_expires_at", "external_search_previews", ["expires_at"], unique=False
    )

    op.create_table(
        "user_external_search_quotas",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("user_external_search_quotas")
    op.drop_index("ix_external_search_previews_expires_at", table_name="external_search_previews")
    op.drop_index("ix_external_search_previews_user_id", table_name="external_search_previews")
    op.drop_table("external_search_previews")
