# Tastebuds Containerized - Implementation Plan

## Current Snapshot
- Compose stands up `api` (FastAPI), `db` (Postgres with test DB bootstrap), optional `web` (Next.js stub), and optional `pgadmin`.
- Backend delivers auth (register/login with JWT), search with optional external ingestion, connectors for Google Books/TMDB/IGDB/Last.fm, menus with slugs and ordered courses/items, tags, and user item states.
- Alembic migration `20240602_000001` installs the full schema; seed + pytest reuse ingestion samples for regression coverage.
- Next.js frontend is currently a health-check placeholder; no auth/menu UI is implemented yet.

## Near-Term Priorities
1. **Frontend flows:** build login/register, session storage, menu/course editors, search/ingest drawer, and public menu pages on Next.js using the existing API.
2. **Auth polish:** add a refresh endpoint that uses the issued `refresh_token`, align token lifetimes, and wire browser-safe storage (httpOnly cookies).
3. **Search/ingestion hardening:** pagination and source filters for `/api/search`, richer metadata coverage in connectors, and additional tests for TV/multi-result cases.
4. **Quality & ops:** add linting/type checks, tighten logging around ingestion failures, and expand the QA checklist to cover the web UI once it exists.
5. **Deployment polish:** introduce a reverse proxy/TLS overlay and document homelab/public hosting once the UI is feature-complete.

## Stack at a Glance
- **Backend:** FastAPI, SQLAlchemy 2, Alembic, async sessions everywhere.
- **Database:** Postgres 15 with JSONB metadata, UUID PKs, ordering constraints on menus/courses/items.
- **Ingestion:** connectors in `api/app/ingestion/` normalize upstream payloads and store raw payloads for replay.
- **Frontend:** Next.js 14 + Tailwind stub (`web/`), wired to `NEXT_PUBLIC_API_BASE` and `API_INTERNAL_BASE`.
- **Tooling:** `./scripts/dev.sh` for Compose tasks, pytest for backend regression coverage, Postman collection for manual testing.
