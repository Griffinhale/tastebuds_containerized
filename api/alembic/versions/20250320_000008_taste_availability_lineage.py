"""Add taste profiles, availability, menu lineage, pairings, and share tokens.

Revision ID: 20250320_000008
Revises: 20250316_000007
Create Date: 2025-03-20 00:00:08
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20250320_000008"
down_revision: Union[str, None] = "20250316_000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


availability_status_enum = postgresql.ENUM(
    "available",
    "unavailable",
    "unknown",
    name="availability_status",
    create_type=False,
)


def upgrade() -> None:
    """Create tables for taste profiles, availability, lineage, pairings, and share tokens."""
    availability_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_taste_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_user_taste_profile"),
    )

    op.create_table(
        "media_item_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "media_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("media_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("region", sa.String(length=32), nullable=False),
        sa.Column("format", sa.String(length=64), nullable=False),
        sa.Column("status", availability_status_enum, nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("deeplink_url", sa.String(length=1024), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "media_item_id",
            "provider",
            "region",
            "format",
            name="uq_media_availability",
        ),
    )
    op.create_index("ix_media_item_availability_media_item_id", "media_item_availability", ["media_item_id"])

    op.create_table(
        "menu_lineage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "source_menu_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("menus.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "forked_menu_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("menus.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_menu_id", "forked_menu_id", name="uq_menu_lineage"),
    )
    op.create_index("ix_menu_lineage_source_menu_id", "menu_lineage", ["source_menu_id"])
    op.create_index("ix_menu_lineage_forked_menu_id", "menu_lineage", ["forked_menu_id"])

    op.create_table(
        "menu_item_pairings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "menu_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("menus.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "primary_course_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("course_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "paired_course_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("course_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "menu_id",
            "primary_course_item_id",
            "paired_course_item_id",
            name="uq_menu_pairing",
        ),
    )
    op.create_index("ix_menu_item_pairings_menu_id", "menu_item_pairings", ["menu_id"])

    op.create_table(
        "menu_share_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "menu_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("menus.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("token", name="uq_menu_share_token"),
    )
    op.create_index("ix_menu_share_tokens_menu_id", "menu_share_tokens", ["menu_id"])
    op.create_index("ix_menu_share_tokens_token", "menu_share_tokens", ["token"], unique=True)


def downgrade() -> None:
    """Drop taste profiles, availability, lineage, pairings, and share tokens."""
    op.drop_index("ix_menu_share_tokens_token", table_name="menu_share_tokens")
    op.drop_index("ix_menu_share_tokens_menu_id", table_name="menu_share_tokens")
    op.drop_table("menu_share_tokens")

    op.drop_index("ix_menu_item_pairings_menu_id", table_name="menu_item_pairings")
    op.drop_table("menu_item_pairings")

    op.drop_index("ix_menu_lineage_forked_menu_id", table_name="menu_lineage")
    op.drop_index("ix_menu_lineage_source_menu_id", table_name="menu_lineage")
    op.drop_table("menu_lineage")

    op.drop_index("ix_media_item_availability_media_item_id", table_name="media_item_availability")
    op.drop_table("media_item_availability")

    op.drop_table("user_taste_profiles")

    availability_status_enum.drop(op.get_bind(), checkfirst=True)
