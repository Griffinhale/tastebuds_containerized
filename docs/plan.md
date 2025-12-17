# Tastebuds Containerized - Implementation Plan

## Current Snapshot
- Compose stands up `api` (FastAPI), `db` (Postgres with test DB bootstrap), optional `web` (Next.js app), and optional `pgadmin`.
- Backend delivers auth (register/login/refresh/logout with JWT), paginated search with `types`/`sources` filters plus optional external ingestion, connectors for Google Books/TMDB/IGDB/Last.fm, menus with slugs and ordered courses/items, tags, and user item states.
- Alembic migration `20240602_000001` installs the full schema; seed + pytest reuse ingestion samples for regression coverage.
- Next.js frontend now includes login/register, a signed-in status widget with refresh/logout, a `/menus` dashboard with inline course/item editors plus drag-to-reorder, catalog search + ingestion with paging/source counts, and shareable public menu pages at `/menus/[slug]`.

## Near-Term Priorities
1. **Connector reliability & credentials:** align TMDB on the v4 bearer token (and add fallback or clear errors), tighten logging for missing keys, and add ingestion/search tests that assert per-source counts. _External fan-out works but will silently skip when env vars are wrong; TMDB still references API keys in old docs._
2. **Search correctness & coverage:** add API-level tests for pagination, `sources`/`types` filters, and mixed internal/external merges, plus guardrails against duplicate IDs when connectors return overlapping results. _Metadata now includes paging and source counts but lacks regression coverage._
3. **Quality & automation:** introduce lint/format + test pipelines (Ruff/pytest for API, ESLint/Prettier/TypeScript checks for web) and wire CI to `./scripts/dev.sh test` so regressions surface automatically. _Currently all checks are manual._
4. **Auth/session transparency:** surface per-device session listings with revoke controls and basic audit trails in both API and web. _Refresh rotation/revocation works, but there is no visibility into active sessions._
5. **Deployment polish:** add a reverse proxy/TLS overlay and document homelab/public hosting paths once connector/auth hardening lands.

## Stack at a Glance
- **Backend:** FastAPI, SQLAlchemy 2, Alembic, async sessions everywhere.
- **Database:** Postgres 15 with JSONB metadata, UUID PKs, ordering constraints on menus/courses/items.
- **Ingestion:** connectors in `api/app/ingestion/` normalize upstream payloads and store raw payloads for replay.
- **Frontend:** Next.js 14 + Tailwind app (`web/`), wired to `NEXT_PUBLIC_API_BASE` and `API_INTERNAL_BASE`.
- **Tooling:** `./scripts/dev.sh` for Compose tasks, pytest for backend regression coverage, Postman collection for manual testing.
