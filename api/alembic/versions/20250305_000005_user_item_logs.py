"""Add user item logs for library tracking.

Revision ID: 20250305_000005
Revises: 20250215_000004
Create Date: 2025-03-05 00:00:05
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20250305_000005"
down_revision: Union[str, None] = "20250215_000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_item_log_type_enum = postgresql.ENUM(
    "started",
    "progress",
    "finished",
    "note",
    "goal",
    name="user_item_log_type",
    create_type=False,
)


def upgrade() -> None:
    """Add user item log table and enum type."""
    user_item_log_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_item_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "media_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("media_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("log_type", user_item_log_type_enum, nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("minutes_spent", sa.Integer(), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=True),
        sa.Column("goal_target", sa.String(length=255), nullable=True),
        sa.Column("goal_due_on", sa.Date(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("minutes_spent >= 0", name="ck_log_minutes_spent_nonnegative"),
        sa.CheckConstraint("progress_percent >= 0 AND progress_percent <= 100", name="ck_log_progress_range"),
    )
    op.create_index(op.f("ix_user_item_logs_user_id"), "user_item_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_item_logs_media_item_id"), "user_item_logs", ["media_item_id"], unique=False)
    op.create_index(op.f("ix_user_item_logs_logged_at"), "user_item_logs", ["logged_at"], unique=False)


def downgrade() -> None:
    """Drop user item log table and enum type."""
    op.drop_index(op.f("ix_user_item_logs_logged_at"), table_name="user_item_logs")
    op.drop_index(op.f("ix_user_item_logs_media_item_id"), table_name="user_item_logs")
    op.drop_index(op.f("ix_user_item_logs_user_id"), table_name="user_item_logs")
    op.drop_table("user_item_logs")
    user_item_log_type_enum.drop(op.get_bind(), checkfirst=True)
