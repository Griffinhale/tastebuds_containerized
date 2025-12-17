# Tastebuds Containerized – Implementation Plan

## 1. Architecture & Stack Choices
- **Backend:** FastAPI with Pydantic v2, SQLAlchemy 2.0 ORM, Alembic for migrations. Provides typed services, dependency-injected repositories, and background ingestion tasks handled synchronously (no Redis jobs initially).
- **Database:** PostgreSQL 15. UUID PKs generated at API layer. JSONB columns where required, B-tree/GiST indexes for search and slugs.
- **Frontend:** React/Next.js single-page app under `web/` (TypeScript + Tailwind) compiled to a static bundle and shipped via its own Node-based container. The UI consumes the `/api` surface, handles auth flows, builds menu/course editors, and exposes public menu pages for anonymous visitors.
- **Containerization:** Docker Compose orchestrates `api`, `web`, `db`, and `pgadmin` (optional helper). API image built from multi-stage Dockerfile using `pip` + `requirements.txt`. The `web` service runs `next build && next start` behind an internal nginx/Traefik reverse proxy that works for local homelab deployments or public hosting.
- **Auth:** Email/password with JWT (access + refresh). Password hashing via `passlib[bcrypt]`. The web client stores tokens in httpOnly cookies and refreshes sessions through a `POST /auth/refresh` endpoint.
- **Search Strategy:** DB-first search (ILIKE + trigram) combined with a search orchestrator that can fan out to connectors (Google Books, TMDB, IGDB, Last.fm) asynchronously. Optional `include_external=true` query parameter triggers on-demand ingestion plus mixed search results from upstream APIs.
- **External Sources:** Google Books, TMDB, IGDB, Last.fm. Each connector: shared `BaseConnector` handles retries/backoff, HTTP session, error handling, logging.

## 2. Data Model Overview
1. `users` – auth credentials, profile metadata.
2. `media_items` – base table with `media_type`, `title`, `subtitle`, `description`, `release_date`, `cover_image_url`, `metadata`.
3. Medium extensions (1:1):
   - `book_items` (authors, page_count, isbn)
   - `movie_items` (tmdb_type, runtime, directors)
   - `game_items` (platforms, developers)
   - `music_items` (artist, album, track_number, duration_ms)
4. `media_sources` – `(media_item_id, source_name, external_id, canonical_url, raw_payload JSONB)` unique per source.
5. Tagging tables: `tags`, `media_item_tags`.
6. User state: `user_item_states` capturing status enum, rating, favorite, notes, timestamps.
7. Curation: `menus`, `courses`, `course_items`.

## 3. Execution Phases
1. **Scaffolding**
   - Bootstrap `api/` as a Python package with `requirements.txt`.
   - Create `docker-compose.yml`, API `Dockerfile`, `.env.example`.
   - Bootstrap FastAPI structure: `app/main.py`, routers package, config loader, logging utilities.
   - Introduce `web/` directory with Next.js boilerplate (`app/`, `components/`, `lib/api.ts`) plus a multi-stage `web/Dockerfile` that builds static assets before copying into a slimmer runtime image.
2. **Database & Migrations**
   - Configure SQLAlchemy models per schema above.
   - Alembic env setup with autogenerate helper but manually reviewed migration.
   - Seed script populating demo user, sample menu, sample media items (mixed types) plus states/tags.
3. **Core Services**
   - Auth router (`/auth/register`, `/auth/login`), `GET /me`.
   - Media search service hitting DB, optionally connectors when `include_external`.
   - CRUD routers for menus/courses/course-items with slug creation and the `/api/public/menus/{slug}` endpoint (slug stability even after title edits, 404 guard when `is_public=false`, ordering enforced by position columns).
   - Tag management endpoints so users can create/list/delete tags and attach them to media items.
4. **Search Orchestrator & External Query Hooks**
   - Build a search orchestrator service class that fans out to DB + connectors concurrently, normalizes each result into a shared DTO, and annotates whether data is persisted vs. external-only.
   - Extend each connector with keyword-search helpers (not just ID ingestion) and enforce provider throttling/backoff windows.
   - Cache upstream search hits for a short TTL (Postgres JSONB cache table now, Redis later) so UI autocomplete does not hammer providers.
   - Expand `/api/search` to accept `sources[]`, `media_type`, pagination tokens for each connector, and a `scope` flag controlling DB vs. external results.
5. **Web UI Delivery**
   - Build shared layout, auth screens, and menu/course editors with optimistic updates mapped to the FastAPI schema (RTK Query/SWR for data fetching).
   - Implement unified search/autocomplete that calls `/api/search` with `include_external` during menu editing and surfaces “import this” actions that trigger `/api/ingest/{source}` under the hood.
   - Add public menu pages and share cards that fetch `/api/public/menus/{slug}` anonymously.
   - Wire JWT refresh/token storage, guard protected routes, and surface account/profile settings.
6. **Container Orchestration & Deployment**
   - Update `docker-compose.yml` with `web` service, reverse proxy (Traefik or nginx), TLS-ready labels/env for homelab + public deployments, volume mounts for static assets/logs, and healthchecks for both services.
   - Provide `docker-compose.homelab.yml` overlay with watchtower/cron-based image pulls, secrets mounts, CDN/cache headers, and optional Tailscale/WireGuard network for private access.
   - Add `scripts/dev.sh web` helper for running the frontend locally (`next dev`) while still relying on containerized API/DB.
7. **Documentation & Tooling**
   - `docs/schema.md` describing tables/relationships.
   - `docs/attribute-mapping.md` capturing field mappings (best-effort lists, expandable).
   - `docs/api.md` enumerating endpoints, auth usage, sample curl flows.
   - `docs/ui.md` capturing frontend architecture, shared components, routing/auth flow diagrams, and deployment notes.
   - README with setup/run instructions and workflows.
8. **Testing**
   - Pytest executed via `pip` virtualenv (see `requirements-dev.txt`).
   - Unit tests: ingestion mapping function ensures normalized structure, menu slug retrieval ensures correct ordering/exposure, tag lifecycle/access control ensures user-owned tagging behaves as expected.
   - Web tests: React Testing Library for components, Cypress/Playwright smoke test covering auth → search → menu publish.

## 4. Ordering & Milestones
1. Finish backend + frontend scaffolding (`api/`, `web/`, compose services, shared env files).
2. Implement models, migrations, and seed scripts so demo data flows end-to-end.
3. Deliver auth/menu/tag/search routers with ingestion connectors wired for ID lookups.
4. Build the search orchestrator + connector keyword search hooks, extending `/api/search` for multi-source support.
5. Stand up the web UI (auth, menus, unified search/import flows, public menu pages) and containerize it alongside the API behind a reverse proxy.
6. Harden homelab/public deployment story (TLS, proxy config, watchtower) and round out docs/tests (backend + frontend suites).

## 5. Frontend Ticket Backlog (Next.js + TypeScript)
1. **FE-001 – Next.js scaffolding & container wiring**
   - Initialize `web/` with `create-next-app` (TypeScript, ESLint, Tailwind).
   - Add shared config: absolute imports, env typing, axios/fetch wrapper pointed at FastAPI base URL.
   - Create `web/Dockerfile` multi-stage build and extend `docker-compose.yml` with `web` + reverse proxy routing to `/api`.
   - Acceptance: `docker compose up web` serves placeholder page, Hot Reload works via `scripts/dev.sh web`.
2. **FE-002 – Auth foundation & API client utilities**
   - Build typed API client module (SWR or RTK Query) handling JWT access/refresh, httpOnly cookie storage, and 401 retries via `/auth/refresh`.
   - Implement login/register forms with validation, success redirects, and error toasts.
   - Add protected route guard (middleware or layout) that checks session state before rendering app shell.
3. **FE-003 – App chrome & navigation**
   - Create responsive layout (sidebar/nav, header with user menu) with dark/light theme toggle.
   - Wire menu links for Dashboard, Menus, Search, Settings.
   - Ensure layout consumes auth context (shows avatar/email, exposes logout).
4. **FE-004 – Unified search UI hooked to orchestrator**
   - Build search page with filters (`media_type`, `sources[]`, `include_external`, pagination tokens).
   - Integrate autocomplete/typeahead that hits `/api/search` and surfaces both DB + external connector results, including provenance badges.
   - Provide CTA to “import” external results -> triggers `/api/ingest/{source}` then refreshes local list.
5. **FE-005 – Menu & course editor**
   - Implement menu list/create forms with slug visibility, public toggle, cover image.
   - Build drag-and-drop course/item editing experience. Integrate search drawer from FE-004 to attach media items inline.
   - Persist optimistic updates via API service, handle ordering/position updates, surface validation errors from FastAPI.
6. **FE-006 – Public menu & share pages**
   - SSR-friendly route `/menus/[slug]` fetching `/api/public/menus/{slug}` without auth, apply open graph tags for social cards.
   - Provide share panel (copy link, embed code placeholder, “Open in Tastebuds” CTA).
   - Handle private menu states (404 display) and loading skeletons.
7. **FE-007 – Account & settings views**
   - Add profile editor (display name, bio), password reset/change flows against API.
   - Surface API key statuses (external connectors) and allow toggling optional privacy settings once backend supports them.
8. **FE-008 – Frontend testing & QA automation**
   - Configure Jest + React Testing Library for components (auth forms, menu editor pieces).
   - Add Cypress/Playwright smoke path: login -> search -> import item -> publish menu -> view public page.
   - Wire tests into CI (GitHub Actions) and document commands in README.
9. **FE-009 – Deployment & homelab polish**
   - Finalize Traefik/nginx config for `web` + `api`, including HTTPS (Let’s Encrypt or homelab certs) and caching headers for static assets.
   - Document watchtower/image update flow, env vars for public URLs, CDN strategy if self-hosted.
   - Provide README section for publishing (ports, DNS, secrets).

## 5. Risks & Mitigations
- **External API schema drift:** capture complete `raw_payload`, isolate mapping functions, document mapping for easy extension.
- **Rate limit/backoff:** tenacity-based retry with jitter, connectors expose `max_results` and chunked ingestion for multi-result.
- **Search performance:** indexes on `title`, `media_type`, `slug`, `tags`; fallback to Postgres trigram extension on compose init.
- **Secrets management:** `.env` + `env_file` in compose, `Settings` reading environment and raising if mandatory values absent in runtime modes.

## 6. Milestone – June 2024
_Historical snapshot kept for reference._
- ✅ **Container & config** – Compose stack (`api`, `db`, `pgadmin`) builds cleanly; `api` image sets `PYTHONPATH=/app` so CLI tools (Alembic, pytest) can import the package.
- ✅ **Database ready** – Initial migration `20240602_000001` (users/media/menus/tags enums) runs successfully; enums are idempotent and `alembic upgrade head` is part of the standard boot flow.
- ✅ **Routers in place** – Auth, menus (incl. nested course/item CRUD), tags, ingest scaffolding, public slug route, and `/health` are wired up and responding (smoke test on `/docs` and `/health` confirmed).
- ✅ **Seed/test coverage** – Seed script now consumes fixture payloads from `app/samples/ingestion/` and pytest reuses the same data for ingestion regression tests.
- ✅ **Ingestion connectors** – Connector classes live under `app/ingestion/`, with automated mapping tests guarding book/movie/game/music coverage per source.
- ✅ **Docs polish** – ASCII schema diagram (`docs/schema.md`), importable Postman collection (`docs/tastebuds.postman_collection.json`), and release QA checklist (`docs/qa-checklist.md`) captured for the notes bundle.
