# Tastebuds Agent Guide

This repository is a Docker-first FastAPI + Postgres + Redis + Next.js stack.
Use this guide to keep changes consistent with project and community standards.

## Project snapshot
- Backend: FastAPI (async) + SQLAlchemy 2 + Alembic
- Data: Postgres 15, Redis + RQ worker/scheduler
- Frontend: Next.js (app router) + Tailwind
- Edge: Nginx proxy at https://localhost routing /api and the web UI

## Repo layout
- `api/`: FastAPI app, ingestion connectors, services, schemas, tests
- `web/`: Next.js app
- `docker/`: proxy config and container assets
- `docs/`: architecture, API, schema, QA, security notes
- `scripts/dev.sh`: preferred wrapper for docker compose
- `mappings/`: ingestion attribute mappings

## Local setup (preferred)
1. Copy `example.env` to `.env` and set required secrets/API keys.
2. Use `./scripts/dev.sh up` to start the stack.
3. Run `./scripts/dev.sh migrate` after schema changes.
4. Optional: `./scripts/dev.sh seed` for demo data.

## Development workflow
- Prefer Docker-first workflows unless explicitly working locally.
- Keep changes scoped and backwards compatible where possible.
- Update Alembic migrations for schema changes and ensure migrations run on boot.
- Preserve ingestion/search invariants:
  - External fan-out requires auth and per-user quotas.
  - External results stay in short-TTL previews until a user action ingests them.
  - Dedupe rules remain deterministic.
- Public menu DTOs must stay owner-safe and non-sensitive.

## Tests and QA
- Backend: `./scripts/dev.sh test` (pytest). CI also runs Ruff and pytest.
- Frontend: `npm run lint`, `npm run prettier:check`, `npm run typecheck`.
- Release checks: see `docs/qa-checklist.md`.
- Suite coverage details: see `docs/tests.md`.
- If you cannot run a test, call it out clearly.

## Commenting standards
- Prefer self-documenting names; add comments when logic is non-obvious, policy-driven, or has tricky edge cases.
- Write comments for the "why" (constraints, invariants, tradeoffs) and the approach when the implementation is non-trivial.
- Module/file level: add a short docstring header when a file has multiple responsibilities, external integrations, or security-sensitive logic. Include purpose + key invariants.
- Function/class level: include a one-line purpose summary; for complex logic add a brief "Implementation notes" section that outlines the method or ordering rules.
- Public APIs, jobs, and connectors should note side effects, auth/quotas, or retention policies in docstrings.
- Keep comments close to the code they describe and update/remove stale comments in the same change.
- Use `TODO(name): ...` only with clear follow-up context.

## Comment examples (copy/paste patterns)
Module header:
```python
"""Search service for internal/external catalog queries.

Invariants:
- External fan-out requires auth + quota and returns previews until explicit ingest.
"""
```

Backend (FastAPI / services):
```python
@router.get("/api/search")
async def search(...):
    """Search internal items and optionally fan out to external sources.

    Implementation notes:
    - Internal results are returned first, then external by requested source order.
    - External results are stored as short-lived previews until user action ingests.
    """
    # External fan-out is auth+quota gated; previews are short-lived until a user action ingests.
    ...
```

```python
def _merge_results(...):
    # Deterministic order: internal first, then external by requested source order.
    ...
```

Ingestion connector:
```python
class TMDBConnector(BaseConnector):
    def _auth(self) -> tuple[dict[str, str], dict[str, str]]:
        # Prefer bearer tokens to avoid TMDB v3 key leakage in logs and caches.
        ...
```

Worker / maintenance:
```python
async def prune_media_source_payloads(...):
    # Retention policy: redact raw payloads after N days to reduce licensing exposure.
    ...
```

Frontend (Next.js / app router):
```tsx
export async function GET() {
  // Use server-side API base to keep cookies httpOnly and avoid client leakage.
  ...
}
```

```tsx
function MenuCard(...) {
  // Keep optimistic updates local to avoid refetch churn on drag reorder.
  ...
}
```

Proxy / infra:
```nginx
# Rate-limit auth routes separately to protect token issuance endpoints.
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/s;
```

Scripts:
```bash
# Use dev.sh to keep docker-compose flags consistent across platforms.
./scripts/dev.sh up
```

## Security and ops
- Follow `docs/security.md` for known risks and constraints.
- Do not log secrets, tokens, or raw third-party payloads.
- Respect payload caps and retention policies for external sources.
- Keep `/api/ops/*` and `/health` protections intact.

## Documentation expectations
- Update `README.md` and relevant `docs/*.md` when behavior, commands,
  endpoints, or data models change.
- Keep `docs/attribute-mapping.md` and `mappings/*.yaml` aligned when
  ingestion mappings change.
- Keep `docs/tests.md` in sync when adding, removing, or changing test suites.

## AI-specific collaboration standards
- Be explicit about assumptions and cite relevant files.
- Prefer minimal, reversible diffs; avoid sweeping refactors.
- Leave a short note on tests run or skipped.
- Ask for clarification when requirements are ambiguous.
