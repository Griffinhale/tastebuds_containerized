# Database Schema

## Overview
- **users**: Authenticated accounts (email + hashed password). Own menus and user-level media states.
- **media_items**: Core catalog table shared across media types. Columns: `media_type`, `title`, `subtitle`, `description`, `release_date`, `cover_image_url`, `canonical_url`, JSONB `metadata`, timestamps. Acts as the canonical, queryable layer for ingestion.
- **book_items / movie_items / game_items / music_items**: One-to-one extension tables keyed by `media_item_id` for medium-specific attributes (authors/page counts, runtimes, platforms, album metadata, etc.).
- **media_sources**: Records external origin per item (`source_name`, `external_id`, `canonical_url`, `raw_payload`). Enforces unique `(source_name, external_id)`.
- **tags / media_item_tags**: Free-form tagging with optional owner scope.
- **user_item_states**: Each user's relationship to a media item (status, rating, favorite, notes, timestamps).
- **menus**: Curated collections owned by a user, with slug for public sharing.
- **courses**: Ordered stages inside a menu.
- **course_items**: Ordered items inside a course referencing `media_items`.

## Key Relationships
- `users (1) -> (N) menus`
- `users (1) -> (N) user_item_states`
- `media_items (1) -> (1) {book_items|movie_items|game_items|music_items}`
- `media_items (1) -> (N) media_sources`
- `media_items (N) <-> (N) tags` through `media_item_tags`
- `menus (1) -> (N) courses -> (N) course_items`
- `course_items (N) -> (1) media_items`

## Entity Diagram
```text
users
  ├─< menus
  │     └─< courses
  │            └─< course_items >─ media_items >─ media_sources
  │                                      │
  │                                      └─< media_item_tags >─ tags
  └─< user_item_states

media_items
  ├─ book_items
  ├─ movie_items
  ├─ game_items
  └─ music_items
```

## Important Constraints & Indexes
- All primary keys are UUIDs generated in the API layer.
- `menus.slug` unique + indexed for public lookups. Slugs are generated when a menu is created and never auto-regenerated, even if the title changes, and `/api/public/menus/{slug}` returns 404 unless `is_public=true`.
- `media_sources`: `(source_name, external_id)` unique to prevent duplicates; index on `media_item_id` + `source_name` for ingestion lookups.
- `user_item_states`: `(user_id, media_item_id)` unique + rating check constraint (0–10).
- `courses`: `(menu_id, position)` unique; `course_items`: `(course_id, position)` unique to enforce ordering so `/api/public/menus/{slug}` and owner views both respect deterministic chronology.
- `tags`: `(owner_id, name)` unique to keep user-specific tag namespaces.

## Canonical vs Metadata vs Raw
- **Canonical columns** (`media_items.title`, `media_items.cover_image_url`, extension table columns, etc.) are indexed/typed fields we guarantee are queryable via filters/search.
- **Metadata JSONB** (`media_items.metadata`) holds medium-agnostic attributes that still need to be queryable via JSON operators (e.g., categories, listeners, maturity ratings) but do not deserve individual columns yet.
- **Raw payload** (`media_sources.raw_payload`) stores verbatim upstream responses for replaying ingestion when APIs evolve or when new mappings are added. These blobs should never be queried directly in user-facing flows; instead, new fields graduate to metadata or canonical columns via the mapping workflow described in `README.md` and `docs/attribute-mapping.md`.

## Table Details
### users
- Columns: `email` (unique, indexed), `hashed_password`, optional `display_name`, timestamps.
- Relationships: owns `menus` (cascade delete) and `user_item_states`.

### media_items
- Columns: `media_type` enum (`book`, `movie`, `tv`, `game`, `music`), canonical text fields, `metadata` JSONB, timestamps.
- Indexes: title index for search, FK lookups via extensions/sources/tags/states.
- Relationships: one-to-one to each extension, one-to-many to `media_sources`, `media_item_tags`, `course_items`, and `user_item_states`.

### book_items / movie_items / game_items / music_items
- Shared shape: PK/FK to `media_items.id` with `ON DELETE CASCADE`.
- Each table stores medium-specific payloads (e.g., book authors + ISBNs, movie runtimes/directors, game platforms + genres, music artist/album/duration).

### media_sources
- Columns: `(media_item_id, source_name, external_id)` with unique constraint, canonical URL, raw JSON payload, fetched timestamp.
- Acts as dedupe + replay anchor for ingestion connectors.

### user_item_states
- Columns: `(user_id, media_item_id)` unique pair, `status` enum, optional `rating` (0–10 check), `favorite` flag, timestamps.
- Foreign keys cascade deletes when either the user or media item vanishes.

### menus
- Columns: `owner_id`, `title`, `description`, slug (unique/indexed), `is_public`, timestamps.
- Cascade deletes propagate to `courses`/`course_items`.

### courses
- Columns: `menu_id`, `title`, optional `description`, integer `position` (unique per menu).
- Ordered relationship to `course_items`.

### course_items
- Columns: `course_id`, `media_item_id`, optional `notes`, integer `position` (unique per course).
- Links curated chronology back to normalized `media_items`.

### tags & media_item_tags
- `tags`: `(owner_id, name)` unique so users can reuse global tags or create private namespaces.
- `media_item_tags`: `(media_item_id, tag_id)` unique, cascades when media or tag is deleted.
