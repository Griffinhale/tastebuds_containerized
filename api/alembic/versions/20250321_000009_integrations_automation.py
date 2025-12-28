"""Add integration webhooks, ingest queue, and automation rules.

Revision ID: 20250321_000009
Revises: 20250320_000008
Create Date: 2025-03-21 00:00:09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20250321_000009"
down_revision: Union[str, None] = "20250320_000008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add integration webhook tokens, ingest events, and automation rules."""
    op.create_table(
        "integration_webhook_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_integration_webhook_token_hash"),
    )
    op.create_index(
        op.f("ix_integration_webhook_tokens_provider"),
        "integration_webhook_tokens",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_integration_webhook_tokens_user_id"),
        "integration_webhook_tokens",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "integration_ingest_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=True),
        sa.Column("source_name", sa.String(length=64), nullable=True),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "ingested",
                "skipped",
                "failed",
                name="integration_ingest_status",
            ),
            nullable=False,
        ),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_integration_ingest_events_provider"),
        "integration_ingest_events",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_integration_ingest_events_user_id"),
        "integration_ingest_events",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "automation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("trigger_type", sa.String(length=64), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("action_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_automation_rules_user_id"), "automation_rules", ["user_id"], unique=False)


def downgrade() -> None:
    """Drop integration webhook tokens, ingest events, and automation rules."""
    op.drop_index(op.f("ix_automation_rules_user_id"), table_name="automation_rules")
    op.drop_table("automation_rules")
    op.drop_index(op.f("ix_integration_ingest_events_user_id"), table_name="integration_ingest_events")
    op.drop_index(op.f("ix_integration_ingest_events_provider"), table_name="integration_ingest_events")
    op.drop_table("integration_ingest_events")
    op.drop_index(op.f("ix_integration_webhook_tokens_user_id"), table_name="integration_webhook_tokens")
    op.drop_index(op.f("ix_integration_webhook_tokens_provider"), table_name="integration_webhook_tokens")
    op.drop_table("integration_webhook_tokens")
    op.execute("DROP TYPE IF EXISTS integration_ingest_status")
