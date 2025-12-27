# Tastebuds Architecture Overview

This snapshot ties the running Compose stack to the data model, request flows, and delivery dependencies so feature work and hardening stay aligned.

## Runtime Topology
- **Services (docker-compose.yml):** `api` (FastAPI + SQLAlchemy/Alembic), `db` (Postgres 15), `redis` (RQ broker), `worker` (`python -m app.worker`), `scheduler` (`rqscheduler`), `web` (Next.js), optional `pgadmin`, and `proxy` (local Nginx front door that routes `/api` to the backend and serves Next.js at the root).
- **Edge routing:** The `proxy` service listens on 80/443 with a generated dev certificate, redirects HTTP to HTTPS, auto-rotates self-signed certs via `docker/proxy/entrypoint.sh`, validates `Host` for localhost-only dev use, applies per-route rate limits (auth, ingest, search, public), funnels `/api`/`/docs`/`/health` to `api:8000`, and hands the remaining traffic to `web:3000`.
- **State:** Postgres owns canonical media (`media_items` + extensions), provenance (`media_sources`), menus/courses/items, tags, per-user states + logs, refresh tokens for session inventory, and encrypted integration secrets in `user_credentials`. Redis now holds the queue state for ingestion retries, webhook/sync jobs, integrations, and scheduled maintenance while UUIDs remain generated in the API.
- **Env & secrets:** `.env` is consumed by API, worker, and web; external API keys (Google Books, TMDB v4 bearer, IGDB client/secret, Last.fm) are required for live ingestion.
- **Not yet present:** ACME/production cert issuance and webhook payload persistence beyond the current stateless handlers.

## Request & Data Flows
- **Auth:** JWT access/refresh tokens issued at login/register; refresh rotates server-side tokens. Cookies are httpOnly; most CRUD routes depend on `get_current_user`. Session inventory lives at `/api/auth/sessions` with per-session revoke.
- **Ingestion:** `POST /api/ingest/{source}` normalizes upstream payloads into canonical columns + metadata JSONB + extension tables, while persisting the full `raw_payload` in `media_sources`. Dedupe uses `(source_name, external_id)`.
- **Search:** `GET /api/search` queries Postgres first, optionally fans out to external connectors, and requires auth for any external sources. External results are stored in a short-TTL preview cache (with payload/metadata caps) and fully ingested only when an authenticated user opens details or saves to a menu/library.
- **Menus & sharing:** Authenticated owners manage menus/courses/items; `GET /api/public/menus/{slug}` serves published menus anonymously using a public DTO that omits `owner_id`.
- **Library + Log:** `/api/me/library` aggregates user states + log events into a status snapshot, while `/api/me/logs` captures timeline entries (progress, minutes, goals) without mutating menu data.
- **Menu narrative (in progress):** course intents + item annotations are now stored on `courses`/`course_items`; pairings remain pending with minimal additional joins.
- **Taste Profile (planned):** TODO: define aggregation pipeline and caching for preference insights derived from logs/tags/menus.
- **Availability awareness (planned):** TODO: ingest provider data, schedule refresh jobs, and map region-specific availability to items.
- **Community exchange (planned):** TODO: model menu lineage, attribution, and fork/remix notifications.
- **Health/telemetry:** `/health` and `/api/health` return only `{status}` to anonymous callers; authenticated or allowlisted callers also see connector status, repeated failure alerts, and open circuits for ingestion/search fan-out.
- **Ops/queues:** `/api/ops/queues` (auth + admin allowlist) surfaces Redis/RQ queue sizes, worker presence, scheduler health, and vault encryption status for quick triage; the Next.js home page now renders a queue health card for the same snapshot.

## Delivery & Ops Dependencies
- **Migrations:** `alembic upgrade head` is part of boot; initial revision `20240602_000001` creates the full schema.
- **Tests/fixtures:** Pytest uses async fixtures and sample ingestion payloads; CI runs Ruff + pytest (SQLite) + frontend lint/typecheck plus proxy routing smokes.
- **Background work:** Retryable ingestion/search fan-out now enqueues into Redis-backed RQ queues, with rq-scheduler keeping preview cache cleanup running. Webhook listeners and long-running sync jobs now have dedicated RQ jobs + queues (`webhooks`, `sync`) and share the same worker pool.
- **Security controls:** Route-specific rate limits live at the proxy, session inventory/audit APIs are present, and external payloads now have retention/TTL enforcement (preview cache TTL + raw payload GC); see `docs/security.md` for current risks.

## Known Gaps to Align With Delivery Plan
- Finalize production TLS (ACME/managed certs) and continue tuning rate-limit profiles before any public exposure.
- Wire the Arr/Jellyfin/Spotify webhook listeners and scheduled sync adapters into the Redis/RQ worker queue before those integrations go live, including retries and campaign scheduling.
- Validate data-retention defaults (preview TTL + raw payload GC) against licensing policies once external payload sizes are better understood.
