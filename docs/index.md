# Documentation Index

Tastebuds is a Docker-first FastAPI + Postgres + Redis + Next.js stack for
curating cross-media "tasting menus" and ingesting external media sources into
a normalized catalog.

## Quickstart
Docker (recommended):
- `cp example.env .env`
- `./scripts/dev.sh up`
- `./scripts/dev.sh migrate`
- Optional demo data: `./scripts/dev.sh seed`

Local API dev (no Docker):
- `python -m venv .venv && source .venv/bin/activate`
- `pip install -r api/requirements-dev.txt`
- `cd api && alembic upgrade head`
- `uvicorn app.main:app --reload`

Tests:
- Docker: `./scripts/dev.sh test`
- Local: `cd api && TEST_DATABASE_URL=... pytest app/tests`

## Start here
- Prioritized TODO list for new contributors: `docs/todo.md`

## Trust Boundaries (high level)
- Edge proxy (Nginx): TLS termination, host validation, and rate limits before
  routing to API or web.
- Auth/session: access + refresh JWTs with rotation and server-side tracking.
- External fan-out: authenticated-only, quota gated, preview-only cache until
  explicit ingest.
- Ingestion pipeline: connector payloads are size-capped and subject to
  retention/scrubbing policies.

## API Contract Source of Truth
OpenAPI is authoritative. Use `/docs` (Swagger UI) or `/openapi.json` for the
canonical contract; `docs/api.md` is a usage guide, not an endpoint catalog.

## Concepts
- `docs/architecture.md`

## Reference
- `docs/schema.md`
- `docs/config.md`
- `docs/data-lifecycle.md`
- `docs/api.md`
- `docs/tests.md`
- `docs/attribute-mapping.md`
- `docs/qa-checklist.md`
- `docs/tastebuds.postman_collection.json`

## How-to
- `docs/ops-runbook.md`
- `docs/migrations.md`
- `docs/integrations/connector-guide.md`

## Security
- `docs/security.md`
- `docs/security/threat-model.md`
- `docs/security/production-hardening.md`
- `docs/security/backlog.md`

## Decisions
- `docs/decisions/README.md` (ADR directory; file an ADR for cross-cutting policy changes)

## Product
- `docs/product/roadmap.md`
