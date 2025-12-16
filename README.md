# Tastebuds (Containerized)

Tastebuds is a database-first "media diet" curator. Users ingest books, films, games, and tracks into a normalized catalog, then craft shareable Menus composed of chronologically ordered Courses that walk a friend through a cross-medium experience.

---

## Current Progress (June 2024)
- Docker Compose stack (`api`, `db`, optional `pgadmin`) builds/runs cleanly; `api` container now exports `PYTHONPATH=/app` so CLI tooling (Alembic, pytest) works both inside and outside Docker.
- Initial Alembic migration `20240602_000001` succeeds end-to-end (enums are created idempotently) and is part of `docker compose exec api alembic upgrade head`.
- Core routes (auth, menus/courses/items, tags, ingestion scaffolding, `/public/menus/{slug}`, `/health`, `/docs`) are live—recent smoke tests hit `/health` and `/docs` successfully.
- Next focus areas: seed script + fixtures, automated ingestion mapping tests, and expanding docs (`docs/schema.md`, Postman collection).

## Concept: Menus, Courses & the Media Diet
- **Menus** are curated journeys owned by a user. Each menu implies an order of consumption and exposes a stable public slug that can be shared without authentication.
- **Courses** sit inside a menu and group items into beats ("Appetizer", "Feature", "Encore"). Ordering happens at both the course level and inside each course through `position` columns—so the chronology is always explicit.
- **Course Items** reference normalized `media_items` rows, meaning a menu can mix formats. A course can start with a book, progress to a movie, and end with a track without duplicating metadata.
- **User state & annotations** are tracked separately through `user_item_states` (status enum: `consumed`, `currently_consuming`, `want_to_consume`, `paused`, `dropped` + rating/favorite flags, timestamps, and notes). Tags sit on `media_items` via `media_item_tags` to power personal taxonomies.
- This is more than a watchlist: Menus preserve intent + commentary, highlight what was consumed vs. what's aspirational, and produce a permalink slug for sharing the finished tasting menu.

### Slugs & static sharing
- Slugs are generated when menus are created (`slugify(title)` plus a numeric suffix when needed). They do **not** change automatically if the title changes, so existing links stay valid.
- `is_public=false` keeps a menu private (returns 404 from `/api/public/menus/{slug}`). Toggling `is_public=true` exposes the immutable slug.
- Ordering is enforced via unique `(menu_id, position)` constraints for courses and `(course_id, position)` for items, so public responses always reflect a deterministic chronology.

---

## Architecture & Data Model
Tastebuds treats the database schema as the product contract. FastAPI, SQLAlchemy, and Alembic orchestrate the API and migrations, but Postgres owns ordering, deduplication, and sharing semantics.

### Tables at a glance
- `media_items` holds shape-agnostic metadata (title, description, release_date, media_type discriminator, JSONB metadata) plus relationships to tags, sources, and user states.
- Medium extensions (`book_items`, `movie_items`, `game_items`, `music_items`) are 1:1 tables keyed by `media_item_id` so each medium only stores the attributes it needs.
- `media_sources` deduplicates ingestion via a unique `(source_name, external_id)` constraint and stores the raw provider payload for lossless reprocessing.
- `user_item_states` stores per-user status/rating/favorite/notes with timestamps, enabling personal views that don't pollute canonical metadata.
- `menus → courses → course_items` capture ordering with uniqueness constraints on `(menu_id, position)` and `(course_id, position)` to guarantee chronological integrity.
- `tags` + `media_item_tags` allow global or user-scoped annotations that travel with menu exports.

```text
users ──┐
        ├─ menus ── courses ── course_items ── media_items
        └─ user_item_states ──┘                ├─ book_items / movie_items / game_items / music_items
media_items ── media_sources (source_name, external_id, raw_payload)
media_items ── media_item_tags ── tags
```

See `docs/schema.md` for diagrams, entity notes, and index/constraint commentary.

### Canonical vs metadata vs raw payloads
- **Canonical columns** live directly on `media_items` (title, subtitle, release_date, cover_image_url, canonical_url) or extension tables. They are typed fields indexed for filtering/search.
- **Metadata JSONB** (`media_items.metadata`) stores semi-structured data like categories, listener counts, languages, and platforms when we still need queryable JSON operators but not a dedicated column yet.
- **Raw payloads** are stored verbatim per source inside `media_sources.raw_payload`. They are write-only until a developer promotes a field via the mapping workflow below.

---

## Ingestion & Attribute Mapping Strategy
- Async connectors for Google Books, TMDB (movie + TV), IGDB, and Last.fm normalize upstream payloads into `ConnectorResult` objects before they touch the DB. The connectors decide the media_type, populate shared + extension columns, and always stash the upstream response in `media_sources.raw_payload`.
- Attribute coverage for each provider lives in `docs/attribute-mapping.md` and structured YAML manifests under `mappings/{google_books,tmdb,igdb,lastfm}.yaml`. When the live docs for a provider aren't reachable we lean on **mapping files + captured `raw_payload` samples + iterative expansion**.
- Extending mappings safely:
  1. Update the relevant `mappings/<source>.yaml` entry to document whether the field should be canonical, metadata, or raw-only.
  2. Model the new attribute (JSON key in `metadata` or Alembic migration for a new column/extension field).
  3. Update the connector under `api/app/ingestion/` to populate it and capture tests in `api/app/tests`.
  4. Refresh `docs/attribute-mapping.md` so downstream consumers know what to expect.

---

## Getting Started
### Prerequisites
- Docker + Docker Compose
- Python 3.11+ (optional but useful for running scripts/tests without containers)

### Configure your environment
```bash
cp .env.example .env
```
Update the following at minimum:
- `DATABASE_URL=postgresql+asyncpg://tastebuds:tastebuds@db:5432/tastebuds`
- `TEST_DATABASE_URL=postgresql+asyncpg://tastebuds:tastebuds@db:5432/tastebuds_test` (create the `tastebuds_test` DB once via `docker compose exec db psql -U tastebuds -c 'CREATE DATABASE tastebuds_test;'`).
- JWT secrets and every external API key listed in the next section.

### Run the stack
```bash
# Build images + start services in the background
docker compose up --build -d

# Apply migrations against the running DB
docker compose exec api alembic upgrade head

# (Optional) seed demo content (user + mixed menu)
docker compose exec api python -m app.scripts.seed
```
The API lives at `http://localhost:8000` with docs at `/docs` (Swagger) and `/redoc`.

### Development without Docker
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r api/requirements-dev.txt
export DATABASE_URL=postgresql+asyncpg://tastebuds:tastebuds@localhost:5432/tastebuds
export TEST_DATABASE_URL=postgresql+asyncpg://tastebuds:tastebuds@localhost:5432/tastebuds_test
cd api
alembic upgrade head
uvicorn app.main:app --reload
```

### Running tests
Tastebuds ships with async pytest coverage that exercises ingestion mappings, menu slug behavior, and the public menu lookup path.

**Inside Docker (recommended):**
```bash
docker compose run --rm api sh -c "pip install -r requirements-dev.txt && TEST_DATABASE_URL=postgresql+asyncpg://tastebuds:tastebuds@db:5432/tastebuds_test pytest app/tests"
```

**Locally:**
```bash
cd api
pytest app/tests
```
Ensure `TEST_DATABASE_URL` points at an isolated database; the pytest fixture automatically creates/drops schemas per test run.

---

## Getting API Keys
- **Google Books** – enable the Books API inside Google Cloud Console and create an API key. Set `GOOGLE_BOOKS_API_KEY`.
- **TMDB** – create an account at themoviedb.org, request an API key (v3), and place it in `TMDB_API_KEY`.
- **IGDB** – register an application in the Twitch Developer Console to get a client ID + secret. Tastebuds exchanges these for an OAuth token at runtime (`IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`). Tokens are fetched and refreshed automatically; no manual access token env var is required.
- **Last.fm** – register for an API account at https://www.last.fm/api/account/create and use the key inside `LASTFM_API_KEY`.

---

## Example API Flow
All routes live under `/api`. Authenticated requests expect `Authorization: Bearer $TOKEN`.

### Register & Login
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123","display_name":"Demo"}'

curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123"}'
```

### Ingest media items
```bash
# Google Books (volume ID or URL)
curl -X POST http://localhost:8000/api/ingest/google_books \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"zyTCAlFPjgYC"}'

# TMDB (movie or tv). Prefix the ID with the resource type when possible
curl -X POST http://localhost:8000/api/ingest/tmdb \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"movie:603"}'

# IGDB (numeric game ID)
curl -X POST http://localhost:8000/api/ingest/igdb \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"7346"}'

# Last.fm (MBID or artist::track string)
curl -X POST http://localhost:8000/api/ingest/lastfm \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"Daft Punk::Harder Better Faster Stronger"}'
```

### Build and share a menu
```bash
# Create a menu with the desired slug generated automatically
MENU_ID=$(curl -s -X POST http://localhost:8000/api/menus \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Neo-Noir Night","description":"Books → Movies → Music","is_public":true}' \
  | jq -r '.id')

# Add a course
COURSE_ID=$(curl -s -X POST http://localhost:8000/api/menus/$MENU_ID/courses \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Appetizer","description":"Set the tone","position":1}' \
  | jq -r '.id')

# Add a course item (MEDIA_ID is returned from ingestion)
curl -X POST http://localhost:8000/api/menus/$MENU_ID/courses/$COURSE_ID/items \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"media_item_id":"$MEDIA_ID","position":1,"notes":"Read first."}'

# Fetch the public slug (share this URL)
curl http://localhost:8000/api/public/menus/$(curl -s http://localhost:8000/api/menus/$MENU_ID \
  -H "Authorization: Bearer $TOKEN" | jq -r '.slug')
```

### Tag media items
```bash
TAG_ID=$(curl -s -X POST http://localhost:8000/api/tags \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Neo-Noir"}' | jq -r '.id')

curl -X POST http://localhost:8000/api/tags/$TAG_ID/media \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"media_item_id\":\"$MEDIA_ID\"}"

curl http://localhost:8000/api/tags/media/$MEDIA_ID -H "Authorization: Bearer $TOKEN"
```

Need more endpoints? See `docs/api.md` for the full surface area plus additional examples (search, states, tagging, etc.).

---

## Database Migrations & Seeding
- **Upgrade**: `docker compose exec api alembic upgrade head`
- **Downgrade**: `docker compose exec api alembic downgrade -1`
- **Create a revision**: `docker compose exec api alembic revision --autogenerate -m "add music fields"`
- **Seed demo data**: `docker compose exec api python -m app.scripts.seed`

When changing schema, always update `docs/schema.md` and re-run any ingestion tests touched by the new columns.

---

## Flatpak VS Code Notes
- **Recommended workflow:** run Docker or Podman commands from a regular host terminal (outside VS Code). The API code can still be edited inside Flatpak VS Code while `docker compose` runs elsewhere.
- **Inside Flatpak terminal (optional):** if the host has Docker installed, prefix commands with `flatpak-spawn --host`:
  ```sh
  flatpak-spawn --host docker compose up -d
  flatpak-spawn --host docker compose exec api alembic upgrade head
  flatpak-spawn --host docker compose logs -f api
  ```
- Sudo/apt/apk/yum are unavailable inside the Flatpak sandbox; install dependencies on the host OS instead.

---

## Troubleshooting
- **Database not ready**: `docker compose ps` should show the `db` service as healthy. If API boot loops, restart with `docker compose restart api` after Postgres passes its health check.
- **Missing env vars**: the API logs will state which credential is missing. Cross-check `.env` with `.env.example` and make sure compose picked up your changes (`docker compose up -d --build api`).
- **Invalid external API keys**: 401/403 responses during ingestion contain the connector name. Reissue the key and update `.env`.
- **IGDB auth failures**: verify `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET`. The service auto-fetches tokens from Twitch; clear the API container to drop cached tokens if credentials change.
- **Rate limits**: connectors retry idempotently, but persistent 429s mean you should slow ingestion, reduce search fan-out, or schedule replays later. Because every `raw_payload` is stored, failed mappings can be reprocessed without re-hitting the provider once the rate limit resets.
- **Compose networking quirks**: ensure nothing else is bound to `5432`/`8000` on the host or adjust the published ports inside `docker-compose.yml`.

---

## Further Reading
- `docs/schema.md` – detailed ERD + migration notes.
- `docs/attribute-mapping.md` – provider field coverage and fallback strategy.
- `docs/api.md` – endpoint-by-endpoint reference.
