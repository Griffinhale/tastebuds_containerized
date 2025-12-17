# Tastebuds (Containerized)

Tastebuds is a database-first "media diet" curator. Users ingest books, films, games, and tracks into a normalized catalog, then craft shareable menus of chronologically ordered courses.

---

## Current Status (Dec 2025)
- Docker Compose runs FastAPI (`api`), Postgres with a seeded test database (`db`), the optional Next.js app (`web`), and optional PgAdmin.
- Auth now stores refresh tokens server-side, rotates them on every `/api/auth/refresh`, and revokes tokens that are reused or logged out so expired sessions are surfaced cleanly.
- Search is paginated, supports `types` filtering, and can target specific external connectors or internal-only lookups while returning paging/source counts in `metadata`. Merged results are deterministic (internal first, then external by requested order, then title/release), with cross-connector dedupe keyed off canonical URLs or normalized title + release date.
- Initial Alembic migration `20240602_000001` creates the full schema (users, media, menus, tags, user states); `alembic upgrade head` is part of the normal boot path.
- Ingestion connectors for Google Books, TMDB (movie/tv), IGDB, and Last.fm power `/api/ingest/{source}` and `/api/search?include_external=true`; ingestion dedupe is enforced on `(source_name, external_id)` while search-level dedupe additionally suppresses cross-source duplicates.
- Seed script and pytest fixtures share sample ingestion payloads to keep mapping regressions covered.
- Next.js frontend now includes login/register, session status, a home search workspace, a menus dashboard with inline course/item editors plus a search/ingest drawer, and slug-based public menu pages rendered at `/menus/[slug]`.

## Architecture & Data Model
- FastAPI + SQLAlchemy 2 + Alembic, async DB access everywhere.
- Postgres 15 stores canonical media rows plus 1:1 extensions (`book_items`, `movie_items`, `game_items`, `music_items`), ingestion sources, menus/courses/items, tags, and per-user item states.
- Connectors normalize upstream payloads, stash full raw payloads, and populate canonical+metadata+extension fields. Mapping notes live in `docs/attribute-mapping.md` and `mappings/*.yaml`.
- Next.js (app router, Tailwind) lives in `web/` and is wired for `NEXT_PUBLIC_API_BASE` (browser) and `API_INTERNAL_BASE` (server).

## Configure your environment
```bash
cp .env.example .env
```
Set at minimum:
- `DATABASE_URL` / `TEST_DATABASE_URL` (Compose defaults target `db`)
- `JWT_SECRET_KEY` (required for token issuance)
- `NEXT_PUBLIC_API_BASE` and `API_INTERNAL_BASE` (defaults are fine for Compose); `NEXT_PUBLIC_APP_BASE_URL` powers share links/OG metadata for public menus
- `CORS_ORIGINS` (comma-separated list of allowed browser origins)
- External API credentials: `GOOGLE_BOOKS_API_KEY`, `TMDB_API_AUTH_HEADER` (TMDB v4 bearer, preferred) _or_ `TMDB_API_KEY` as a fallback, `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`, `LASTFM_API_KEY`. TMDB credentials are validated at startup.
The Compose stack also reads `.env` for the web service.

## Helper script (Docker & Flatpak friendly)
`./scripts/dev.sh <command>` wraps `docker compose` and auto-prefers `flatpak-spawn --host` when needed.
- `up`: build and start the stack
- `down`: stop services
- `logs [svc]`: tail logs
- `migrate`: `alembic upgrade head` in the `api` container
- `seed`: run the demo seed script
- `test`: run pytest inside the API image against `TEST_DATABASE_URL`
- `web`: build/start the Next.js container

## Run the stack
```bash
./scripts/dev.sh up
./scripts/dev.sh migrate
# optional helpers
./scripts/dev.sh seed   # demo data + menu
./scripts/dev.sh web    # Next.js auth + menus UI on :3000
```
Raw commands if you prefer:
```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed
docker compose up --build -d web
```
API: `http://localhost:8000` (OpenAPI at `/docs`, health at `/health` or `/api/health`)  
Web app: `http://localhost:3000` (uses `NEXT_PUBLIC_API_BASE`)

## Development without Docker
```bash
python -m venv .venv
source .venv/bin/activate  # or Scripts\activate on Windows
pip install -r api/requirements-dev.txt
export DATABASE_URL=postgresql+asyncpg://tastebuds:tastebuds@localhost:5432/tastebuds
export TEST_DATABASE_URL=postgresql+asyncpg://tastebuds:tastebuds@localhost:5432/tastebuds_test
cd api
alembic upgrade head
uvicorn app.main:app --reload
```
Frontend only:
```bash
cd web
npm install
npm run dev -- --hostname 0.0.0.0 --port 3000
```
- Auth pages live at `http://localhost:3000/login` and `/register`, hitting the FastAPI auth endpoints using `NEXT_PUBLIC_API_BASE`. Tokens are issued as httpOnly cookies; no `localStorage` usage.
- After logging in, the home page shows your signed-in status via `/api/me` and now includes a search workspace with prompts/filters that can fan out to external sources. `/menus` lists/creates menus, lets you add/delete courses/items, and includes a per-course search drawer that ingests external matches directly into that course. Use the refresh/log out buttons on the home page as needed.
- Mark a menu public and share `http://localhost:3000/menus/{slug}` for the read-only view backed by `/api/public/menus/{slug}`.

## API quickstart
Authenticated routes accept `Authorization: Bearer <access_token>` and the browser also gets httpOnly cookies (`access_token`, `refresh_token`) from register/login/refresh. Register/login returns both access and refresh tokens; refresh is available at `/api/auth/refresh`.
Refresh tokens rotate on every call and are revoked server-side when they expire or when you log out—reusing an old refresh cookie will yield `401`.
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123","display_name":"Demo"}'
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123"}'
```
Ingest media (deduped by `(source_name, external_id)`):
```bash
curl -X POST http://localhost:8000/api/ingest/google_books \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"zyTCAlFPjgYC"}'
curl -X POST http://localhost:8000/api/ingest/tmdb \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"603"}'  # or "movie:603" / "tv:123"
```
Build and share a menu:
```bash
MENU_ID=$(curl -s -X POST http://localhost:8000/api/menus \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Neo-Noir Night","description":"Books + Movies + Music","is_public":true}' \
  | jq -r '.id')

COURSE_ID=$(curl -s -X POST http://localhost:8000/api/menus/$MENU_ID/courses \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Appetizer","description":"Set the tone","position":1}' \
  | jq -r '.id')

curl -X POST http://localhost:8000/api/menus/$MENU_ID/courses/$COURSE_ID/items \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"media_item_id\":\"$MEDIA_ID\",\"position\":1,\"notes\":\"Read first.\"}"

curl http://localhost:8000/api/public/menus/$(curl -s http://localhost:8000/api/menus/$MENU_ID \
  -H "Authorization: Bearer $TOKEN" | jq -r '.slug')
```
Tags:
```bash
TAG_ID=$(curl -s -X POST http://localhost:8000/api/tags \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Neo-Noir"}' | jq -r '.id')
curl -X POST http://localhost:8000/api/tags/$TAG_ID/media \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"media_item_id\":\"$MEDIA_ID\"}"
```
Search with optional external fan-out (ingests results before returning them):
```bash
curl "http://localhost:8000/api/search?q=blade%20runner&include_external=true" \
  -H "Authorization: Bearer $TOKEN"
# Paginate/filter and request specific connectors (include_external is implicit when sources are supplied):
curl "http://localhost:8000/api/search?q=zelda&types=game&sources=internal&sources=igdb&page=2&per_page=10&external_per_source=3" \
  -H "Authorization: Bearer $TOKEN"
# Response metadata includes paging, per-source counts, cross-source dedupe tallies, and timing per connector under `source_metrics`.
```

## Testing
```bash
./scripts/dev.sh test
# or locally
cd api && TEST_DATABASE_URL=... pytest app/tests
```
Pytest uses async fixtures plus ingestion samples, and now includes API-level coverage for auth/token flows and menu CRUD.

## CI
GitHub Actions run on push/PR:
- Backend: Ruff (`python -m ruff check app`) + `pytest app/tests` with SQLite.
- Compose parity check: `./scripts/dev.sh test`.
- Frontend: `npm ci` then `npm run lint`, `npm run prettier:check`, `npm run typecheck`.

## Troubleshooting
- Database not ready: `docker compose ps` should show `db` healthy; retry `./scripts/dev.sh migrate`.
- Missing env vars or API keys: the API logs list the missing key; ensure `.env` is loaded and rebuild the `api` container.
- TMDB/IGDB/Last.fm/Google Books failures: connectors now emit structured ingestion logs and apply per-source circuit breakers with exponential backoff. If calls get skipped, look for `ingestion_circuit_open`/`ingestion_skip` events and wait for cooldowns to elapse before retrying.
- Compose port conflicts: adjust `docker-compose.yml` published ports if 5432/8000/3000 are busy.

## Reference docs
- `docs/api.md`: endpoint reference and example payloads.
- `docs/schema.md`: tables, relationships, and constraints.
- `docs/attribute-mapping.md`: provider field coverage.
- `docs/qa-checklist.md`: release smoke checklist.
- `docs/tastebuds.postman_collection.json`: importable Postman collection.
