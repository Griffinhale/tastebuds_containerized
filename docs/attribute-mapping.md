# Attribute Mapping

Tastebuds ingests upstream payloads with an \"always keep the source\" policy: every response is saved in `media_sources.raw_payload` while high-signal attributes hydrate normalized columns. When official docs aren't reachable at runtime we fall back to **mapping files + raw_payload capture + iterative expansion**—meaning we document the field, store the entire payload, and expose it once demand warrants a new column.

Each connector lists the primary normalized fields and the attributes that currently stay inside `raw_payload`. The same information is stored in structured YAML manifests under `mappings/google_books.yaml`, `mappings/tmdb.yaml`, `mappings/igdb.yaml`, and `mappings/lastfm.yaml` to keep the source of truth alongside the code. Captured sample payloads live in `app/samples/ingestion/*.json` so tests and the seed script can replay realistic responses without calling upstream services.

## Google Books
- **Fields captured**
  - `volumeInfo.title`, `subtitle` → `media_items.title` / `media_items.subtitle`.
  - `authors` → `book_items.authors` (JSON array).
  - `description` → `media_items.description`.
  - `publishedDate` → `media_items.release_date` (parsed to `DATE`).
  - `imageLinks.thumbnail` → `media_items.cover_image_url`.
  - `infoLink` → `media_items.canonical_url`.
  - `industryIdentifiers.ISBN_10/ISBN_13` → `book_items.isbn_10` / `isbn_13`.
  - `pageCount`, `language`, `publisher` → corresponding columns in `book_items`.
  - `categories`, `maturityRating` → stored inside `media_items.metadata`.
- **Raw-only fields**: `searchInfo`, `panelizationSummary`, `accessInfo` (persisted verbatim inside `media_sources.raw_payload`).

## TMDB (Movies & TV)
- **Fields captured**
  - `title` / `name` → `media_items.title` (media_type detects movie/tv).
  - `overview` → `media_items.description`.
  - `poster_path` → `media_items.cover_image_url` (prefixed with `image.tmdb.org`).
  - `release_date` / `first_air_date` → `media_items.release_date`.
  - `genres`, `spoken_languages`, `status` → `media_items.metadata`.
  - `runtime` or `episode_run_time` → `movie_items.runtime_minutes`.
  - `credits.crew` filtered by job → `movie_items.directors`, `movie_items.producers`.
  - `created_by` → stored as directors for TV to surface showrunners.
  - Resource URL → `media_items.canonical_url` & `media_sources.canonical_url`.
- **Raw-only fields**: `production_companies`, `production_countries`, `videos`, `watch/providers` etc.

## IGDB (Games)
- **Fields captured**
  - `name` → `media_items.title`.
  - `summary` → `media_items.description`.
  - `first_release_date` (UNIX) → `media_items.release_date`.
  - `cover.url` → `media_items.cover_image_url`.
  - `genres`, `platforms` → stored both in `media_items.metadata` and `game_items.genres/platforms` for queryable arrays.
  - `involved_companies` split by flags → `game_items.developers` / `publishers`.
- **Raw-only fields**: `age_ratings`, `multiplayer_modes`, `screenshots`, `dlcs`, etc. Entire payload persisted for reprocessing.

## Last.fm (Music)
- **Fields captured**
  - `track.name` → `media_items.title`.
  - `artist.name`, `album.title`, `album.@attr.position` → `music_items.artist_name`, `album_name`, `track_number`.
  - `wiki.summary` → `media_items.description`.
  - `album.image[..]` highest size → `media_items.cover_image_url`.
  - `track.url` → `media_items.canonical_url`.
  - `track.duration` → `music_items.duration_ms` (integer).
  - Listener counts, playcounts, top tags → `media_items.metadata`.
- **Raw-only fields**: `streamable`, `userplaycount`, `comments`, plus any nested album artist info beyond the commonly used keys.

## Raw Payload Policy
Every ingestion stores the unmodified upstream response in `media_sources.raw_payload` (JSONB). This guarantees forward-compatible migrations when APIs add attributes. Mapping adjustments live in `app/ingestion/*` modules; new fields can be surfaced by updating `ConnectorResult.extensions` and/or `MediaItem.metadata` alongside Alembic migrations if new columns are required.

## How to add a new attribute
1. Update the relevant `mappings/<provider>.yaml` file to describe whether the field belongs in canonical columns, `metadata`, or `raw_payload` only.
2. If the field requires a new column, create an Alembic migration and extend the appropriate SQLAlchemy model/`ConnectorResult.extensions` entry. Otherwise, route it into the shared metadata JSON.
3. Update the connector parser under `api/app/ingestion/` to populate the new field and add/refresh tests in `api/app/tests`.
4. Document the change here (and in `README.md` if it affects ingestion behavior) so API consumers know it is queryable.
