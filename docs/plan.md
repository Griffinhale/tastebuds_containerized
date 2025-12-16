# Tastebuds Containerized – Implementation Plan

## 1. Architecture & Stack Choices
- **Backend:** FastAPI with Pydantic v2, SQLAlchemy 2.0 ORM, Alembic for migrations. Provides typed services, dependency-injected repositories, and background ingestion tasks handled synchronously (no Redis jobs initially).
- **Database:** PostgreSQL 15. UUID PKs generated at API layer. JSONB columns where required, B-tree/GiST indexes for search and slugs.
- **Containerization:** Docker Compose orchestrates `api`, `db`, and `pgadmin` (optional helper). API image built from multi-stage Dockerfile using `pip` + `requirements.txt`.
- **Auth:** Email/password with JWT (access + refresh). Password hashing via `passlib[bcrypt]`.
- **Search Strategy:** DB-first search (ILIKE + trigram). Optional `include_external=true` query parameter triggers on-demand ingestion from external APIs.
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
2. **Database & Migrations**
   - Configure SQLAlchemy models per schema above.
   - Alembic env setup with autogenerate helper but manually reviewed migration.
   - Seed script populating demo user, sample menu, sample media items (mixed types) plus states/tags.
3. **Core Services**
   - Auth router (`/auth/register`, `/auth/login`), `GET /me`.
   - Media search service hitting DB, optionally connectors when `include_external`.
   - CRUD routers for menus/courses/course-items with slug creation and the `/api/public/menus/{slug}` endpoint (slug stability even after title edits, 404 guard when `is_public=false`, ordering enforced by position columns).
   - Tag management endpoints so users can create/list/delete tags and attach them to media items.
4. **Ingestion Layer**
   - Shared HTTP client with exponential backoff (tenacity).
   - Individual connector classes for Google Books, TMDB, IGDB, Last.fm.
   - `/ingest/{source}` endpoint orchestrating fetch, parse, upsert.
   - Store normalized fields + `raw_payload`.
5. **Documentation & Tooling**
   - `docs/schema.md` describing tables/relationships.
   - `docs/attribute-mapping.md` capturing field mappings (best-effort lists, expandable).
   - `docs/api.md` enumerating endpoints, auth usage, sample curl flows.
   - README with setup/run instructions and workflows.
6. **Testing**
   - Pytest executed via `pip` virtualenv (see `requirements-dev.txt`).
   - Unit tests: ingestion mapping function ensures normalized structure, menu slug retrieval ensures correct ordering/exposure, tag lifecycle/access control ensures user-owned tagging behaves as expected.

## 4. Ordering & Milestones
1. Finish scaffolding + configs.
2. Implement models + migrations.
3. Seed script + sample data verification.
4. Implement auth & base routers (users, search).
5. Implement ingestion connectors + endpoint.
6. Implement menu/courses CRUD + public slug endpoint.
7. Final docs/tests polish.

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
- 🟡 **Seed/test coverage** – Base pytest scaffolding exists but still needs fixtures + sample data script to be wired into CI.
- 🟡 **Ingestion connectors** – Connector classes live under `app/ingestion/`, but automated mapping tests plus attribute coverage documentation are still being expanded per source.
- 🔜 **Polish** – Need to add schema diagrams (`docs/schema.md`), sample Postman collection, and QA checklist once ingestion layer is finalized.
