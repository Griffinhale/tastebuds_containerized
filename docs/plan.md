# Tastebuds Containerized - Implementation Plan

## Current Snapshot
- Compose stands up `api` (FastAPI), `db` (Postgres with test DB bootstrap), optional `web` (Next.js app), and optional `pgadmin`.
- Backend delivers auth (register/login/refresh/logout with JWT), paginated search with `types`/`sources` filters plus optional external ingestion, connectors for Google Books/TMDB/IGDB/Last.fm, menus with slugs and ordered courses/items, tags, and user item states.
- Alembic migration `20240602_000001` installs the full schema; seed + pytest reuse ingestion samples for regression coverage.
- Next.js frontend now includes login/register, a signed-in status widget with refresh/logout, a `/menus` dashboard with inline course/item editors plus drag-to-reorder, catalog search + ingestion with paging/source counts, and shareable public menu pages at `/menus/[slug]`.

## Near-Term Priorities
1. **Connector reliability & observability:** add structured logging/metrics for ingestion attempts (per-source success/skip/fail), bubble credential/quotas errors into response metadata, and add circuit-breaker/backoff to external fan-out so rate-limit spikes do not slow the API.
2. **Search relevance & dedupe:** enforce deterministic ordering for merged internal+external results, add cross-connector dedupe (e.g., TMDB vs internal duplicates), and expose source-level timing/counts for debugging queries.
3. **Auth/session transparency:** surface per-device session listings with revoke controls and basic audit trails in both API and web. _Refresh rotation/revocation works, but there is no visibility into active sessions._
4. **Deployment polish:** add a reverse proxy/TLS overlay and document homelab/public hosting paths once connector/auth hardening lands.
5. **Frontend UX fit-and-finish:** add loading/empty/error states to the ingest drawer, tighten accessibility (focus order/ARIA), and add smoke tests for the critical flows (login, menu CRUD, search/ingest).

## Stack at a Glance
- **Backend:** FastAPI, SQLAlchemy 2, Alembic, async sessions everywhere.
- **Database:** Postgres 15 with JSONB metadata, UUID PKs, ordering constraints on menus/courses/items.
- **Ingestion:** connectors in `api/app/ingestion/` normalize upstream payloads and store raw payloads for replay.
- **Frontend:** Next.js 14 + Tailwind app (`web/`), wired to `NEXT_PUBLIC_API_BASE` and `API_INTERNAL_BASE`.
- **Tooling:** `./scripts/dev.sh` for Compose tasks, pytest for backend regression coverage, Postman collection for manual testing.
