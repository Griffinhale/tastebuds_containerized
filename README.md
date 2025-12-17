# Tastebuds (Containerized)

Tastebuds is a database-first "media diet" curator. Users ingest books, films, games, and tracks into a normalized catalog, then craft shareable menus of chronologically ordered courses.

---

## Current Status (Dec 2025)
- Docker Compose runs FastAPI (`api`), Postgres with a seeded test database (`db`), the optional Next.js app (`web`), and optional PgAdmin.
- Initial Alembic migration `20240602_000001` creates the full schema (users, media, menus, tags, user states); `alembic upgrade head` is part of the normal boot path.
- Ingestion connectors for Google Books, TMDB (movie/tv), IGDB, and Last.fm power `/api/ingest/{source}` and `/api/search?include_external=true`; dedupe happens via `media_sources (source_name, external_id)`.
- Seed script and pytest fixtures share sample ingestion payloads to keep mapping regressions covered.
- Next.js frontend now includes login/register, session status, and a menus dashboard with inline course/item editors plus a search/ingest drawer.

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
- `NEXT_PUBLIC_API_BASE` and `API_INTERNAL_BASE` (defaults are fine for Compose)
- `CORS_ORIGINS` (comma-separated list of allowed browser origins)
- External API keys: `GOOGLE_BOOKS_API_KEY`, `TMDB_API_KEY`, `IGDB_CLIENT_ID`, `IGDB_CLIENT_SECRET`, `LASTFM_API_KEY`
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
- After logging in, the home page shows your signed-in status via `/api/me`, and `/menus` lists/creates menus, lets you add/delete courses/items, and includes a search drawer that can ingest external matches. Use the refresh/log out buttons on the home page as needed.

## API quickstart
Authenticated routes accept `Authorization: Bearer <access_token>` and the browser also gets httpOnly cookies (`access_token`, `refresh_token`) from register/login/refresh. Register/login returns both access and refresh tokens; refresh is available at `/api/auth/refresh`.
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
  -d '{"external_id":"movie:603"}'
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
```

## Testing
```bash
./scripts/dev.sh test
# or locally
cd api && TEST_DATABASE_URL=... pytest app/tests
```
Pytest uses async fixtures plus ingestion samples, and now includes API-level coverage for auth/token flows and menu CRUD.

## Troubleshooting
- Database not ready: `docker compose ps` should show `db` healthy; retry `./scripts/dev.sh migrate`.
- Missing env vars or API keys: the API logs list the missing key; ensure `.env` is loaded and rebuild the `api` container.
- TMDB/IGDB/Last.fm/Google Books failures: check credentials and rate limits; every ingestion stores `raw_payload` so you can replay without refetching.
- Compose port conflicts: adjust `docker-compose.yml` published ports if 5432/8000/3000 are busy.

## Reference docs
- `docs/api.md`: endpoint reference and example payloads.
- `docs/schema.md`: tables, relationships, and constraints.
- `docs/attribute-mapping.md`: provider field coverage.
- `docs/qa-checklist.md`: release smoke checklist.
- `docs/tastebuds.postman_collection.json`: importable Postman collection.
