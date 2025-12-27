"""initial schema

Revision ID: 20240602_000001
Revises: 
Create Date: 2024-06-02 00:00:01.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20240602_000001"
down_revision = None
branch_labels = None
depends_on = None


media_type_enum = postgresql.ENUM(
    "book", "movie", "tv", "game", "music", name="media_type", create_type=False
)
user_item_status_enum = postgresql.ENUM(
    "consumed",
    "currently_consuming",
    "want_to_consume",
    "paused",
    "dropped",
    name="user_item_status",
    create_type=False,
)


def upgrade() -> None:
    """Create initial schema and enum types."""
    media_type_enum.create(op.get_bind(), checkfirst=True)
    user_item_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "media_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("media_type", media_type_enum, nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("subtitle", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("cover_image_url", sa.String(length=1024), nullable=True),
        sa.Column("canonical_url", sa.String(length=1024), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_media_items_title", "media_items", ["title"], unique=False)

    op.create_table(
        "book_items",
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("authors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=True),
        sa.Column("isbn_10", sa.String(length=32), nullable=True),
        sa.Column("isbn_13", sa.String(length=32), nullable=True),
    )

    op.create_table(
        "movie_items",
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("runtime_minutes", sa.Integer(), nullable=True),
        sa.Column("directors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("producers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tmdb_type", sa.String(length=32), nullable=True),
    )

    op.create_table(
        "game_items",
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("platforms", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("developers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("publishers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("genres", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "music_items",
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("artist_name", sa.String(length=255), nullable=True),
        sa.Column("album_name", sa.String(length=255), nullable=True),
        sa.Column("track_number", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )

    op.create_table(
        "menus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", name="uq_menu_slug"),
    )
    op.create_index("ix_menus_slug", "menus", ["slug"], unique=True)

    op.create_table(
        "media_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="CASCADE")),
        sa.Column("source_name", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("canonical_url", sa.String(length=1024), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source_name", "external_id", name="uq_source_external"),
    )
    op.create_index("ix_media_sources_media_item", "media_sources", ["media_item_id"], unique=False)
    op.create_index("ix_media_sources_source", "media_sources", ["source_name"], unique=False)

    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("menu_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("menus.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("menu_id", "position", name="uq_course_position"),
    )

    op.create_table(
        "course_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("courses.id", ondelete="CASCADE")),
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="CASCADE")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("course_id", "position", name="uq_course_items_position"),
    )

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("owner_id", "name", name="uq_owner_tag"),
    )

    op.create_table(
        "media_item_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="CASCADE")),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tags.id", ondelete="CASCADE")),
        sa.UniqueConstraint("media_item_id", "tag_id", name="uq_media_tag"),
    )

    op.create_table(
        "user_item_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("media_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("media_items.id", ondelete="CASCADE")),
        sa.Column("status", user_item_status_enum, nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("favorite", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("rating >= 0 AND rating <= 10", name="ck_rating_range"),
        sa.UniqueConstraint("user_id", "media_item_id", name="uq_user_item"),
    )


def downgrade() -> None:
    """Drop initial schema and enum types."""
    op.drop_table("user_item_states")
    op.drop_table("media_item_tags")
    op.drop_table("tags")
    op.drop_table("course_items")
    op.drop_table("courses")
    op.drop_index("ix_media_sources_source", table_name="media_sources")
    op.drop_index("ix_media_sources_media_item", table_name="media_sources")
    op.drop_table("media_sources")
    op.drop_table("menus")
    op.drop_table("music_items")
    op.drop_table("game_items")
    op.drop_table("movie_items")
    op.drop_table("book_items")
    op.drop_index("ix_media_items_title", table_name="media_items")
    op.drop_table("media_items")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    user_item_status_enum.drop(op.get_bind(), checkfirst=True)
    media_type_enum.drop(op.get_bind(), checkfirst=True)
