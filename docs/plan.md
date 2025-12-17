# Tastebuds Containerized - Implementation Plan

## Current Snapshot
- Compose stands up `api` (FastAPI), `db` (Postgres with test DB bootstrap), optional `web` (Next.js app), and optional `pgadmin`.
- Backend delivers auth (register/login/refresh/logout with JWT), search with optional external ingestion, connectors for Google Books/TMDB/IGDB/Last.fm, menus with slugs and ordered courses/items, tags, and user item states.
- Alembic migration `20240602_000001` installs the full schema; seed + pytest reuse ingestion samples for regression coverage.
- Next.js frontend now includes login/register, a signed-in status widget with refresh/logout, and a `/menus` dashboard that lists menus, supports inline course/item editors, and provides catalog search + ingestion.

## Near-Term Priorities
1. **Frontend flows:** keep polishing the `/menus` search/ingest drawer and ship read-only public menu pages. _Search + ingestion is live (catalog browsing with external fan-out), so the next milestone is slug-based public views and richer course editors._
2. **Auth polish:** add refresh-token rotation/revocation tracking and surface session-expiry UX in the web app. _Refresh + cookies shipped; continue monitoring expiry handling and add revocation storage before exposing sessions broadly._
3. **Search/ingestion hardening:** paginate `/api/search`, add source filters, promote more metadata fields, and add regressions for TV + multi-result connectors. _Connectors are stable but coverage for TV seasons/multi-source merges is still light._
4. **Quality & ops:** add formatting/linting for API + web code, tighten ingestion failure logging, and ensure the QA checklist reflects the live frontend flows. _Docs now describe login/register/menus; testing/linting automation is still TODO._
5. **Deployment polish:** introduce a reverse proxy/TLS overlay and document homelab/public hosting once search/public pages are feature-complete.

## Stack at a Glance
- **Backend:** FastAPI, SQLAlchemy 2, Alembic, async sessions everywhere.
- **Database:** Postgres 15 with JSONB metadata, UUID PKs, ordering constraints on menus/courses/items.
- **Ingestion:** connectors in `api/app/ingestion/` normalize upstream payloads and store raw payloads for replay.
- **Frontend:** Next.js 14 + Tailwind app (`web/`), wired to `NEXT_PUBLIC_API_BASE` and `API_INTERNAL_BASE`.
- **Tooling:** `./scripts/dev.sh` for Compose tasks, pytest for backend regression coverage, Postman collection for manual testing.
