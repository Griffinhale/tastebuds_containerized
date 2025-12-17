# Attribute Mapping

Tastebuds ingests upstream payloads with an "always keep the source" policy: every response is stored in `media_sources.raw_payload` while high-signal attributes hydrate normalized columns. When live provider docs are unreachable, rely on mapping files plus captured payloads so new fields can be promoted safely.

Structured manifests live under `mappings/{google_books,tmdb,igdb,lastfm}.yaml`, and captured samples live in `api/app/samples/ingestion/*.json`. The seed script and pytest fixtures reuse those samples.

## Google Books
- **Mapped:** `title`, `description`, `publishedDate` -> `release_date`, `imageLinks.thumbnail` -> `cover_image_url`, `infoLink` -> `canonical_url`. Metadata stores `categories`, `language`, `pageCount`. Extension `book_items` stores `authors`, `page_count`, `publisher`, `language`, `isbn_10`, `isbn_13`.
- **Raw-only:** `searchInfo`, `panelizationSummary`, `accessInfo`, and other untouched keys stay in `raw_payload`.

## TMDB (Movies & TV)
- **Mapped:** `title`/`name` -> `title`; `overview` -> `description`; `poster_path` -> `cover_image_url` (prefixed with `https://image.tmdb.org/t/p/original`); `release_date`/`first_air_date` -> `release_date`; metadata includes `genres`, `spoken_languages`, `status`. Extension `movie_items` stores `runtime_minutes`, `directors` (crew job `Director` or showrunners for TV), `producers` (crew job `Producer`), and `tmdb_type` (`movie` or `tv`).
- **Raw-only:** `production_companies`, `production_countries`, `videos`, `watch/providers`, and other nested blobs remain in `raw_payload`.

## IGDB (Games)
- **Mapped:** `name` -> `title`; `summary` -> `description`; `first_release_date` (UNIX) -> `release_date`; `cover.url` -> `cover_image_url`; metadata includes `genres` and `platforms`. Extension `game_items` stores `platforms`, `developers`, `publishers`, and `genres`.
- **Raw-only:** `age_ratings`, `screenshots`, `multiplayer_modes`, DLC/expansions, and other nested fields remain raw.

## Last.fm (Music)
- **Mapped:** `track.name` -> `title`; `artist.name`, `album.title`, `album.@attr.position` -> `music_items.artist_name`, `album_name`, `track_number`; `wiki.summary` -> `description`; `album.image[..]` (largest) -> `cover_image_url`; `track.url` -> `canonical_url`; `track.duration` -> `music_items.duration_ms`. Metadata captures listeners, playcount, and top tags.
- **Raw-only:** `streamable`, `userplaycount`, comments, and unused album/artist fields stay in `raw_payload`.

## Adding a new attribute
1. Update `mappings/<provider>.yaml` to document whether the field should be canonical, metadata, or raw-only.
2. Add or adjust columns (Alembic migration) or metadata keys, plus `ConnectorResult.extensions` entries if an extension table owns the field.
3. Update the connector under `api/app/ingestion/` to populate it and extend tests in `api/app/tests`.
4. Refresh this file and `README.md` so API consumers know which fields are queryable.
