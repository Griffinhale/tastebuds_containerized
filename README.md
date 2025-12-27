# Tastebuds (Containerized)

Tastebuds is a database-first "media diet" curator. Users ingest books, films, games, and tracks into a normalized catalog, then craft shareable menus of chronologically ordered courses.

---

## Current Status (Dec 2025)
- Docker Compose runs FastAPI (`api`), Postgres with a seeded test database (`db`), Redis plus an RQ worker and scheduler (`redis`/`worker`/`scheduler`), the optional Next.js app (`web`), optional PgAdmin, and a local Nginx proxy that fronts the API and UI on port 80/443.
- The local proxy terminates TLS with a generated dev certificate (auto-rotated via `docker/proxy/entrypoint.sh`, swap for a real cert in prod), enforces route-specific rate limits, redirects HTTP to HTTPS, and surfaces queue/redis health via `/api/ops/queues` (auth required).
- Auth now stores refresh tokens server-side, rotates them on every `/api/auth/refresh`, and revokes tokens that are reused or logged out so expired sessions are surfaced cleanly.
- Session inventory: `/api/auth/sessions` lists active/expired refresh tokens for the current user and supports revocation per session; cookies continue to mirror new tokens on rotate/login.
- Search is paginated, supports `types` filtering, and can target specific external connectors or internal-only lookups while returning paging/source counts in `metadata`. Merged results are deterministic (internal first, then external by requested order, then title/release), with cross-connector dedupe keyed off canonical URLs or normalized title + release date.
- External search is auth-only; per-user quotas guard external traffic. External hits stay in short-TTL previews with payload/metadata byte caps and GC, and full ingest happens only after user interaction or explicit ingest.
- Initial Alembic migration `20240602_000001` creates the full schema (users, media, menus, tags, user states); `alembic upgrade head` is part of the normal boot path.
- Ingestion connectors for Google Books, TMDB (movie/tv), IGDB, and Last.fm power `/api/ingest/{source}` and `/api/search?include_external=true`; ingestion dedupe is enforced on `(source_name, external_id)` while search-level dedupe additionally suppresses cross-source duplicates.
- Seed script and pytest fixtures share sample ingestion payloads to keep mapping regressions covered.
- Next.js frontend now includes login/register, session status, a home search workspace, a menus dashboard with inline course/item editors (course intents + item annotations) plus a search/ingest drawer, a Library + Log hub for status tracking and timeline entries, and slug-based public menu pages rendered at `/menus/[slug]`.
- Known security gaps: review `docs/security.md` for remaining risks (production ACME/cert pipeline, connector credential refresh). Public menu DTO is now owner-safe, external search is auth+quota gated with preview caching + payload caps, and `/health` hides telemetry unless the caller is authenticated or allowlisted.
- Search/auth policy: anonymous search returns internal results only. External fan-out requires auth and uses per-user quotas; external hits live in a short-TTL preview cache with payload caps until a signed-in user opens details or saves to a menu/library, which then triggers full ingest.

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
- `REDIS_URL` (defaults to `redis://redis:6379/0`) for the queue broker that backs the worker service
- `WORKER_QUEUE_NAMES` (defaults to `default,ingestion,integrations,maintenance,webhooks,sync`) if you want to tune which queues the worker listens to
- `JWT_SECRET_KEY` (required for token issuance)
- `NEXT_PUBLIC_API_BASE` and `API_INTERNAL_BASE` (defaults are fine for Compose); `NEXT_PUBLIC_APP_BASE_URL` powers share links/OG metadata for public menus
- `CORS_ORIGINS` (comma-separated list of allowed browser origins)
- `INGESTION_PAYLOAD_MAX_BYTES` / `INGESTION_METADATA_MAX_BYTES` to cap stored upstream payloads and `CREDENTIAL_VAULT_KEY` for encrypting integration secrets at rest (falls back to `JWT_SECRET_KEY` in dev).
- `OPS_ADMIN_EMAILS` to restrict `/api/ops/*` diagnostics to a specific set of users.
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
- `web`: build/start the Next.js container plus the proxy

## Run the stack
```bash
./scripts/dev.sh up
./scripts/dev.sh migrate
# optional helpers
./scripts/dev.sh seed   # demo data + menu
./scripts/dev.sh web    # Next.js auth + menus UI on https://localhost

```

`./scripts/dev.sh up` also brings up the `redis` broker, `worker`, and Nginx proxy so you can access the UI at `https://localhost` and the API at `https://localhost/api`.
The proxy listens on HTTPS via a generated dev certificate; use `https://localhost` (self-signed) if you want to test TLS and rate limits. API/web container ports are not published by default; use the proxy for local access.

Raw commands if you prefer:
```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed
docker compose up --build -d proxy
```
API: `https://localhost/api` (OpenAPI at `https://localhost/docs`, health at `/api/health`; telemetry is included only for authenticated or allowlisted callers)  
Web app: `https://localhost` (uses `NEXT_PUBLIC_API_BASE`)

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
curl -k -X POST https://localhost/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123","display_name":"Demo"}'
# Login
curl -k -X POST https://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123"}'
```
Ingest media (deduped by `(source_name, external_id)`):
```bash
curl -k -X POST https://localhost/api/ingest/google_books \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"zyTCAlFPjgYC"}'
curl -k -X POST https://localhost/api/ingest/tmdb \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"603"}'  # or "movie:603" / "tv:123"
```
Build and share a menu:
```bash
MENU_ID=$(curl -sk -X POST https://localhost/api/menus \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Neo-Noir Night","description":"Books + Movies + Music","is_public":true}' \
  | jq -r '.id')

COURSE_ID=$(curl -sk -X POST https://localhost/api/menus/$MENU_ID/courses \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"Appetizer","description":"Set the tone","position":1}' \
  | jq -r '.id')

curl -k -X POST https://localhost/api/menus/$MENU_ID/courses/$COURSE_ID/items \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"media_item_id\":\"$MEDIA_ID\",\"position\":1,\"notes\":\"Read first.\"}"

curl -k https://localhost/api/public/menus/$(curl -sk https://localhost/api/menus/$MENU_ID \
  -H "Authorization: Bearer $TOKEN" | jq -r '.slug')
```
Tags:
```bash
TAG_ID=$(curl -sk -X POST https://localhost/api/tags \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Neo-Noir"}' | jq -r '.id')
curl -k -X POST https://localhost/api/tags/$TAG_ID/media \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"media_item_id\":\"$MEDIA_ID\"}"
```
Search with optional external fan-out (ingests results before returning them):
```bash
curl -k "https://localhost/api/search?q=blade%20runner&include_external=true" \
  -H "Authorization: Bearer $TOKEN"
# Paginate/filter and request specific connectors (include_external is implicit when sources are supplied):
curl -k "https://localhost/api/search?q=zelda&types=game&sources=internal&sources=igdb&page=2&per_page=10&external_per_source=3" \
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

## Security status
- External search fan-out is auth-only with per-user quotas and preview-only persistence; cached payload/metadata are size-capped and GC’d. Full ingest requires user interaction.
- Public menus use a safe DTO with no `owner_id`.
- `/health` and `/api/health` return only `{status}` for anonymous callers; telemetry is returned to authenticated or allowlisted hosts defined via `HEALTH_ALLOWLIST`.
- Full list of remaining risks and fixes: `docs/security.md`.

## Troubleshooting
- Database not ready: `docker compose ps` should show `db` healthy; retry `./scripts/dev.sh migrate`.
- Missing env vars or API keys: the API logs list the missing key; ensure `.env` is loaded and rebuild the `api` container.
- TMDB/IGDB/Last.fm/Google Books failures: connectors now emit structured ingestion logs and apply per-source circuit breakers with exponential backoff. If calls get skipped, look for `ingestion_circuit_open`/`ingestion_skip` events and wait for cooldowns to elapse before retrying.
- Compose port conflicts: adjust `docker-compose.yml` published ports if 80/443/5432/5050 are busy.

## Reference docs
- `docs/architecture.md`: current services, data flows, and delivery dependencies.
- `docs/api.md`: endpoint reference and example payloads.
- `docs/schema.md`: tables, relationships, and constraints.
- `docs/attribute-mapping.md`: provider field coverage.
- `docs/qa-checklist.md`: release smoke checklist.
- `docs/tastebuds.postman_collection.json`: importable Postman collection.
