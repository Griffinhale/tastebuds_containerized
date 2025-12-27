"""Add narrative intent to courses.

Revision ID: 20250315_000006
Revises: 20250305_000005
Create Date: 2025-03-15 00:00:06
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20250315_000006"
down_revision: Union[str, None] = "20250305_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add narrative intent to menu courses."""
    op.add_column("courses", sa.Column("intent", sa.Text(), nullable=True))


def downgrade() -> None:
    """Drop narrative intent from menu courses."""
    op.drop_column("courses", "intent")
