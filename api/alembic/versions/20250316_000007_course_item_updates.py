"""Add updated timestamps to courses and course items.

Revision ID: 20250316_000007
Revises: 20250315_000006
Create Date: 2025-03-16 00:00:07
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250316_000007"
down_revision: Union[str, None] = "20250315_000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add updated_at timestamps to courses and course items."""
    op.add_column(
        "courses",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "course_items",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    """Drop updated_at timestamps from courses and course items."""
    op.drop_column("course_items", "updated_at")
    op.drop_column("courses", "updated_at")
