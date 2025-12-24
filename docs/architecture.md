# Tastebuds Architecture Overview

This snapshot ties the running Compose stack to the data model, request flows, and delivery dependencies so feature work and hardening stay aligned.

## Runtime Topology
- **Services (docker-compose.yml):** `api` (FastAPI + SQLAlchemy/Alembic), `db` (Postgres 15), `redis` (RQ broker), `worker` (`python -m app.worker`), `web` (Next.js), optional `pgadmin`, and `proxy` (local Nginx front door that routes `/api` to the backend and serves Next.js at the root).
- **Edge routing:** The `proxy` service listens on port 80, funnels `/api` to `api:8000`, and hands the remaining traffic to `web:3000`, so the stack can be exposed without an external router.
- **State:** Postgres owns canonical media (`media_items` + extensions), provenance (`media_sources`), menus/courses/items, tags, and per-user states. Redis now holds the queue state for ingestion retries and future webhook/sync jobs while UUIDs remain generated in the API.
- **Env & secrets:** `.env` is consumed by API, worker, and web; external API keys (Google Books, TMDB v4 bearer, IGDB client/secret, Last.fm) are required for live ingestion.
- **Not yet present:** TLS termination, rate limits, audit-friendly session controls, and the automation flows that enqueue retries/webhooks/syncs are still pending; the HTTP proxy is bare-bones and the queue still needs its connector wiring.

## Request & Data Flows
- **Auth:** JWT access/refresh tokens issued at login/register; refresh rotates server-side tokens. Cookies are httpOnly; most CRUD routes depend on `get_current_user`.
- **Ingestion:** `POST /api/ingest/{source}` normalizes upstream payloads into canonical columns + metadata JSONB + extension tables, while persisting the full `raw_payload` in `media_sources`. Dedupe uses `(source_name, external_id)`.
- **Search:** `GET /api/search` queries Postgres first, optionally fans out to external connectors, and now requires auth for any external sources. External results should be stored in a short-TTL preview cache; full ingest occurs when an authenticated user opens details or saves to a menu/library.
- **Menus & sharing:** Authenticated owners manage menus/courses/items; `GET /api/public/menus/{slug}` serves published menus anonymously. Current schema exposes `owner_id` on the public DTO (see security notes).
- **Health/telemetry:** `/health` and `/api/health` expose connector status and last errors without auth; intended for observability but currently public.

## Delivery & Ops Dependencies
- **Migrations:** `alembic upgrade head` is part of boot; initial revision `20240602_000001` creates the full schema.
- **Tests/fixtures:** Pytest uses async fixtures and sample ingestion payloads; CI runs Ruff + pytest (SQLite) + frontend lint/typecheck.
- **Background work:** Retryable ingestion, webhook listeners (Arr/Jellyfin), and scheduled syncs now funnel through the Redis-backed RQ worker (`python -m app.worker`), but the connector-specific jobs and retry logic that enqueue work are still pending and the preview cache cleanup jobs need implementing.
- **Security controls:** Rate limiting, session inventory/audit APIs, and data-retention/TTL for external payloads are planned but unimplemented; see `docs/security.md` for current risks.

## Known Gaps to Align With Delivery Plan
- Harden the local proxy with TLS, certificates, and rate-limit profiles (or replace it with Traefik/Caddy) before public exposure.
- Lock down `/api/search` external fan-out, `/health`, and public menu DTO to satisfy privacy-first goals.
- Wire the Arr/Jellyfin/Spotify webhook listeners and scheduled sync adapters into the Redis/RQ worker queue before those integrations go live, including retries and campaign scheduling.
- Define retention/GC for unused ingested media/raw payloads to avoid unbounded growth and licensing concerns.
