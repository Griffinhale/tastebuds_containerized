# Tastebuds Architecture Overview

This snapshot ties the running Compose stack to the data model, request flows, and delivery dependencies so feature work and hardening stay aligned.

## Runtime Topology
- **Services (docker-compose.yml):** `api` (FastAPI + SQLAlchemy/Alembic), `db` (Postgres 15), `web` (Next.js), optional `pgadmin`. No reverse proxy or worker service is currently defined.
- **State:** Postgres owns canonical media (`media_items` + extensions), provenance (`media_sources`), menus/courses/items, tags, and per-user states. UUIDs generated in the API.
- **Env & secrets:** `.env` is consumed by API and web; external API keys (Google Books, TMDB v4 bearer, IGDB client/secret, Last.fm) are required for live ingestion.
- **Not yet present:** Background queue/broker (for retries, webhooks, scheduled sync) and reverse proxy/TLS/rate-limits (Traefik/Caddy) mentioned in the delivery plan are not provisioned in Compose.

## Request & Data Flows
- **Auth:** JWT access/refresh tokens issued at login/register; refresh rotates server-side tokens. Cookies are httpOnly; most CRUD routes depend on `get_current_user`.
- **Ingestion:** `POST /api/ingest/{source}` normalizes upstream payloads into canonical columns + metadata JSONB + extension tables, while persisting the full `raw_payload` in `media_sources`. Dedupe uses `(source_name, external_id)`.
- **Search:** `GET /api/search` queries Postgres first, optionally fans out to external connectors, and now requires auth for any external sources. External results should be stored in a short-TTL preview cache; full ingest occurs when an authenticated user opens details or saves to a menu/library.
- **Menus & sharing:** Authenticated owners manage menus/courses/items; `GET /api/public/menus/{slug}` serves published menus anonymously. Current schema exposes `owner_id` on the public DTO (see security notes).
- **Health/telemetry:** `/health` and `/api/health` expose connector status and last errors without auth; intended for observability but currently public.

## Delivery & Ops Dependencies
- **Migrations:** `alembic upgrade head` is part of boot; initial revision `20240602_000001` creates the full schema.
- **Tests/fixtures:** Pytest uses async fixtures and sample ingestion payloads; CI runs Ruff + pytest (SQLite) + frontend lint/typecheck.
- **Background work:** Retryable ingestion, webhook listeners (Arr/Jellyfin), and scheduled syncs require a queue (RQ/Celery) and worker containers plus durable storage (e.g., Redis); none are wired yet.
- **Security controls:** Rate limiting, session inventory/audit APIs, and data-retention/TTL for external payloads are planned but unimplemented; see `docs/security.md` for current risks.

## Known Gaps to Align With Delivery Plan
- Add reverse proxy + TLS + rate-limit profile ahead of public exposure.
- Lock down `/api/search` external fan-out, `/health`, and public menu DTO to satisfy privacy-first goals.
- Introduce a worker/broker and queue-backed ingestion retry model before shipping webhook-driven integrations (Arr/Jellyfin/Spotify).
- Define retention/GC for unused ingested media/raw payloads to avoid unbounded growth and licensing concerns.
