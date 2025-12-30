"""Add persisted search vectors for media items.

Revision ID: 20250402_000010
Revises: 20250321_000009
Create Date: 2025-04-02 00:00:10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20250402_000010"
down_revision: Union[str, None] = "20250321_000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add stored full-text search vectors and refresh triggers."""
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'english_unaccent') THEN
                CREATE TEXT SEARCH CONFIGURATION english_unaccent ( COPY = english );
                ALTER TEXT SEARCH CONFIGURATION english_unaccent
                    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart, word, hword, hword_part
                    WITH unaccent, english_stem;
            END IF;
        END $$;
        """
    )

    op.add_column("media_items", sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True))

    op.execute(
        """
        CREATE OR REPLACE FUNCTION media_items_search_vector(target_id uuid)
        RETURNS tsvector
        LANGUAGE sql
        STABLE
        AS $$
        SELECT
            setweight(to_tsvector('english_unaccent', coalesce(mi.title, '')), 'A') ||
            setweight(to_tsvector('english_unaccent', coalesce(mi.subtitle, '')), 'B') ||
            setweight(to_tsvector('english_unaccent', coalesce(mi.description, '')), 'C') ||
            setweight(
                (
                    to_tsvector(
                        'english_unaccent',
                        coalesce(
                            array_to_string(
                                ARRAY(SELECT jsonb_array_elements_text(coalesce(b.authors, '[]'::jsonb))),
                                ' '
                            ),
                            ''
                        )
                    ) ||
                    to_tsvector('english_unaccent', coalesce(b.publisher, '')) ||
                    to_tsvector('english_unaccent', coalesce(b.isbn_10, '')) ||
                    to_tsvector('english_unaccent', coalesce(b.isbn_13, '')) ||
                    to_tsvector(
                        'english_unaccent',
                        coalesce(
                            array_to_string(
                                ARRAY(SELECT jsonb_array_elements_text(coalesce(mo.directors, '[]'::jsonb))),
                                ' '
                            ),
                            ''
                        )
                    ) ||
                    to_tsvector(
                        'english_unaccent',
                        coalesce(
                            array_to_string(
                                ARRAY(SELECT jsonb_array_elements_text(coalesce(mo.producers, '[]'::jsonb))),
                                ' '
                            ),
                            ''
                        )
                    ) ||
                    to_tsvector(
                        'english_unaccent',
                        coalesce(
                            array_to_string(
                                ARRAY(SELECT jsonb_array_elements_text(coalesce(g.developers, '[]'::jsonb))),
                                ' '
                            ),
                            ''
                        )
                    ) ||
                    to_tsvector(
                        'english_unaccent',
                        coalesce(
                            array_to_string(
                                ARRAY(SELECT jsonb_array_elements_text(coalesce(g.publishers, '[]'::jsonb))),
                                ' '
                            ),
                            ''
                        )
                    ) ||
                    to_tsvector(
                        'english_unaccent',
                        coalesce(
                            array_to_string(
                                ARRAY(SELECT jsonb_array_elements_text(coalesce(g.genres, '[]'::jsonb))),
                                ' '
                            ),
                            ''
                        )
                    ) ||
                    to_tsvector(
                        'english_unaccent',
                        coalesce(
                            array_to_string(
                                ARRAY(SELECT jsonb_array_elements_text(coalesce(g.platforms, '[]'::jsonb))),
                                ' '
                            ),
                            ''
                        )
                    ) ||
                    to_tsvector('english_unaccent', coalesce(mu.artist_name, '')) ||
                    to_tsvector('english_unaccent', coalesce(mu.album_name, ''))
                ),
                'D'
            )
        FROM media_items mi
        LEFT JOIN book_items b ON b.media_item_id = mi.id
        LEFT JOIN movie_items mo ON mo.media_item_id = mi.id
        LEFT JOIN game_items g ON g.media_item_id = mi.id
        LEFT JOIN music_items mu ON mu.media_item_id = mi.id
        WHERE mi.id = target_id;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION refresh_media_item_search_vector(target_id uuid)
        RETURNS void
        LANGUAGE sql
        AS $$
        UPDATE media_items
        SET search_vector = media_items_search_vector(target_id)
        WHERE id = target_id;
        $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION media_items_search_vector_trigger()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            target_id uuid;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                target_id := OLD.media_item_id;
            ELSIF TG_TABLE_NAME = 'media_items' THEN
                target_id := NEW.id;
            ELSE
                target_id := NEW.media_item_id;
            END IF;
            IF target_id IS NULL THEN
                IF TG_OP = 'DELETE' THEN
                    RETURN OLD;
                END IF;
                RETURN NEW;
            END IF;
            PERFORM refresh_media_item_search_vector(target_id);
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER media_items_search_vector_update
        AFTER INSERT OR UPDATE OF title, subtitle, description
        ON media_items
        FOR EACH ROW EXECUTE FUNCTION media_items_search_vector_trigger();
        """
    )
    op.execute(
        """
        CREATE TRIGGER book_items_search_vector_update
        AFTER INSERT OR UPDATE OR DELETE
        ON book_items
        FOR EACH ROW EXECUTE FUNCTION media_items_search_vector_trigger();
        """
    )
    op.execute(
        """
        CREATE TRIGGER movie_items_search_vector_update
        AFTER INSERT OR UPDATE OR DELETE
        ON movie_items
        FOR EACH ROW EXECUTE FUNCTION media_items_search_vector_trigger();
        """
    )
    op.execute(
        """
        CREATE TRIGGER game_items_search_vector_update
        AFTER INSERT OR UPDATE OR DELETE
        ON game_items
        FOR EACH ROW EXECUTE FUNCTION media_items_search_vector_trigger();
        """
    )
    op.execute(
        """
        CREATE TRIGGER music_items_search_vector_update
        AFTER INSERT OR UPDATE OR DELETE
        ON music_items
        FOR EACH ROW EXECUTE FUNCTION media_items_search_vector_trigger();
        """
    )

    op.execute("UPDATE media_items SET search_vector = media_items_search_vector(id)")
    op.create_index(
        "ix_media_items_search_vector",
        "media_items",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Remove stored search vectors and triggers."""
    op.drop_index("ix_media_items_search_vector", table_name="media_items")
    op.execute("DROP TRIGGER IF EXISTS music_items_search_vector_update ON music_items")
    op.execute("DROP TRIGGER IF EXISTS game_items_search_vector_update ON game_items")
    op.execute("DROP TRIGGER IF EXISTS movie_items_search_vector_update ON movie_items")
    op.execute("DROP TRIGGER IF EXISTS book_items_search_vector_update ON book_items")
    op.execute("DROP TRIGGER IF EXISTS media_items_search_vector_update ON media_items")
    op.execute("DROP FUNCTION IF EXISTS media_items_search_vector_trigger")
    op.execute("DROP FUNCTION IF EXISTS refresh_media_item_search_vector")
    op.execute("DROP FUNCTION IF EXISTS media_items_search_vector")
    op.drop_column("media_items", "search_vector")
    op.execute("DROP TEXT SEARCH CONFIGURATION IF EXISTS english_unaccent")
