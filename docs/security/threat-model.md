# Threat Model

This model captures current assets, entry points, and invariants so security work
tracks the system that actually ships.

## Assets
- Access + refresh tokens and session inventory.
- Integration credentials (encrypted) and webhook tokens.
- User data: menus, logs, library state, tags, taste profiles.
- Cached previews + raw ingestion payloads.
- Ops diagnostics + health telemetry.
- Queue state and job metadata (Redis/RQ).

## Entry Points
- Public API routes (`/api`, `/api/public/*`, `/api/auth/*`).
- Share links (`/api/public/menus/{slug}`, `/api/public/menus/draft/{token}`).
- Ops + health (`/api/ops/*`, `/health`, `/api/health`).
- Webhooks + sync (`/api/integrations/*/webhook`, `/api/integrations/*/sync`).
- External connector fan-out (Google Books, TMDB, IGDB, Last.fm).
- OpenAPI UI + spec (`/docs`, `/openapi.json`).

## Attacker Model
- Unauthenticated internet traffic probing public endpoints.
- Compromised client tokens (access or refresh leakage).
- Authenticated but malicious users attempting cross-tenant access.
- Internal misuse or over-privileged ops access.

## Trust Boundaries
- Edge proxy enforces TLS, host validation, and rate limits before routing.
- API <-> Postgres/Redis boundaries for data + queue state.
- API/worker <-> external providers via connector fan-out.
- Browser clients rely on httpOnly cookies for session tokens.
- Public share endpoints expose read-only DTOs without auth.

## Key Invariants
- External fan-out requires authentication and per-user quota enforcement.
- External search results are preview-only (TTL + size caps) until explicit ingest.
- Public menu DTOs omit owner identifiers and respect visibility flags.
- Ops endpoints require auth + admin allowlist and are proxy-gated.
- Health telemetry is limited to authenticated or allowlisted callers.
- Secrets/tokens are never logged; sensitive payloads follow retention policy.
