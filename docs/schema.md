# Database Schema

## Overview
- **users**: auth accounts (email + hashed password), own menus and user-level media states.
- **media_items**: canonical catalog table with `media_type`, `title`, `description`, `release_date`, `cover_image_url`, `canonical_url`, JSONB `metadata`, timestamps.
- **book_items / movie_items / game_items / music_items**: one-to-one extension tables keyed by `media_item_id` for medium-specific attributes.
- **media_sources**: ingestion provenance per item (`source_name`, `external_id`, `canonical_url`, `raw_payload`, `fetched_at`), unique on `(source_name, external_id)`.
- **tags / media_item_tags**: free-form tagging with optional owner scope.
- **user_item_states**: per-user status/rating/favorite/notes with timestamps and a rating check constraint.
- **user_item_logs**: per-user timeline entries (started/finished/progress/notes/goals) with optional minutes, progress %, and goal targets.
- **menus / courses / course_items**: ordered menu structure with public slug on `menus` plus narrative intent on courses and item annotations.
- **menu_item_pairings**: narrative links between course items for story mode.
- **menu_lineage**: fork/lineage attribution between menus.
- **menu_share_tokens**: temporary tokens for draft share links.
- **media_item_availability**: provider/region/format availability entries with status + last checked.
- **user_taste_profiles**: cached preference summaries derived from logs/tags/menus.

## Relationships
```
users --> menus --> courses --> course_items --> media_items
      \-> user_item_states -------------/
      \-> user_item_logs ---------------/
      \-> user_taste_profiles

media_items --> media_sources
media_items --> book_items | movie_items | game_items | music_items
media_items <--> media_item_tags <--> tags
media_items --> media_item_availability
menus --> menu_share_tokens
menus --> menu_lineage
course_items --> menu_item_pairings
```

## Constraints & Indexes
- UUID primary keys generated in the API.
- `menus.slug` is unique/indexed; slugs are generated at creation and stay stable even if the title changes.
- Ordering: `(menu_id, position)` unique on `courses`, `(course_id, position)` unique on `course_items`.
- `media_sources` unique `(source_name, external_id)`; `media_item_id` indexed for lookups.
- `user_item_states` unique `(user_id, media_item_id)` with rating range check (0-10).
- `tags` unique `(owner_id, name)` to prevent duplicates per user namespace.

## Canonical vs Metadata vs Raw
- **Canonical columns**: typed fields on `media_items` or extension tables (e.g., `runtime_minutes`, `authors`).
- **Metadata JSONB**: semi-structured attributes that are queryable but do not yet need dedicated columns (genres, languages, counts).
- **Raw payload**: verbatim upstream responses stored in `media_sources.raw_payload` for replaying ingestion and future promotion of new fields.
