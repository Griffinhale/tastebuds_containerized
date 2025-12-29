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

## Deep Docs
- Architecture + flows: `architecture.md`
- API usage guide: `api.md`
- Schema overview: `schema.md`
- Security: `security/threat-model.md`
- Production hardening checklist: `security/production-hardening.md`
- Security backlog: `security/backlog.md`
- Attribute mapping + manifests: `attribute-mapping.md`
- Tests + suites: `tests.md`
- Release QA checklist: `qa-checklist.md`
- ADRs (decisions): `decisions/README.md`
- Product plan: `plan.md`

## Decision Records
Any cross-cutting policy change requires an ADR.
