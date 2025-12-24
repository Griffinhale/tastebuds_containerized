# Tastebuds Architecture Overview

This snapshot ties the running Compose stack to the data model, request flows, and delivery dependencies so feature work and hardening stay aligned.

## Runtime Topology
- **Services (docker-compose.yml):** `api` (FastAPI + SQLAlchemy/Alembic), `db` (Postgres 15), `redis` (RQ broker), `worker` (`python -m app.worker`), `scheduler` (`rqscheduler`), `web` (Next.js), optional `pgadmin`, and `proxy` (local Nginx front door that routes `/api` to the backend and serves Next.js at the root).
- **Edge routing:** The `proxy` service now listens on 80/443 with a bundled dev certificate, redirects HTTP to HTTPS, applies basic rate limits per route family, funnels `/api` to `api:8000`, and hands the remaining traffic to `web:3000`.
- **State:** Postgres owns canonical media (`media_items` + extensions), provenance (`media_sources`), menus/courses/items, tags, per-user states, and refresh tokens for session inventory. Redis now holds the queue state for ingestion retries, webhook/sync jobs, and scheduled maintenance while UUIDs remain generated in the API.
- **Env & secrets:** `.env` is consumed by API, worker, and web; external API keys (Google Books, TMDB v4 bearer, IGDB client/secret, Last.fm) are required for live ingestion.
- **Not yet present:** Automated cert rotation/ACME, refined rate-limit profiles, and the production-grade webhook/sync job wiring that will ride the new queue.

## Request & Data Flows
- **Auth:** JWT access/refresh tokens issued at login/register; refresh rotates server-side tokens. Cookies are httpOnly; most CRUD routes depend on `get_current_user`. Session inventory lives at `/api/auth/sessions` with per-session revoke.
- **Ingestion:** `POST /api/ingest/{source}` normalizes upstream payloads into canonical columns + metadata JSONB + extension tables, while persisting the full `raw_payload` in `media_sources`. Dedupe uses `(source_name, external_id)`.
- **Search:** `GET /api/search` queries Postgres first, optionally fans out to external connectors, and requires auth for any external sources. External results are stored in a short-TTL preview cache (with payload/metadata caps) and fully ingested only when an authenticated user opens details or saves to a menu/library.
- **Menus & sharing:** Authenticated owners manage menus/courses/items; `GET /api/public/menus/{slug}` serves published menus anonymously using a public DTO that omits `owner_id`.
- **Health/telemetry:** `/health` and `/api/health` return only `{status}` to anonymous callers; authenticated or allowlisted callers also see connector status and last errors.
- **Ops/queues:** `/api/ops/queues` (auth required) surfaces Redis/RQ queue sizes, worker presence, and scheduler health for quick triage.

## Delivery & Ops Dependencies
- **Migrations:** `alembic upgrade head` is part of boot; initial revision `20240602_000001` creates the full schema.
- **Tests/fixtures:** Pytest uses async fixtures and sample ingestion payloads; CI runs Ruff + pytest (SQLite) + frontend lint/typecheck plus proxy routing smokes.
- **Background work:** Retryable ingestion/search fan-out now enqueues into Redis-backed RQ queues, with rq-scheduler keeping preview cache cleanup running. Webhook listeners and long-running sync jobs should reuse the same queues.
- **Security controls:** Rate limiting, session inventory/audit APIs, and data-retention/TTL for external payloads are planned but unimplemented; see `docs/security.md` for current risks.

## Known Gaps to Align With Delivery Plan
- Harden the TLS story (rotate certs, OCSP/ACME automation) and keep refining the rate-limit profiles before any public exposure.
- Wire the Arr/Jellyfin/Spotify webhook listeners and scheduled sync adapters into the Redis/RQ worker queue before those integrations go live, including retries and campaign scheduling.
- Define retention/GC for unused ingested media/raw payloads to avoid unbounded growth and licensing concerns.
