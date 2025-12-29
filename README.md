# Tastebuds (Containerized)

Tastebuds is a Docker-first FastAPI + Postgres + Redis + Next.js stack for
curating cross-media "tasting menus" and ingesting external media into a
normalized catalog.

Start here: `docs/index.md` (canonical docs map, architecture, security, tests).

## Quickstart
See `docs/index.md` for Docker and local setup steps.
UI: `https://localhost` (proxy)  
API: `https://localhost/api` (OpenAPI at `/docs`)

## Tests
```bash
./scripts/dev.sh test
# local
cd api && TEST_DATABASE_URL=... pytest app/tests
```

## API Contract Source of Truth
OpenAPI is authoritative; use `/docs` or `/openapi.json`. `docs/api.md` is a
usage guide, not an endpoint catalog.

## Docs
- `docs/index.md` (start here)
- `docs/architecture.md`
- `docs/security/threat-model.md`
- `docs/security/production-hardening.md`
- `docs/tests.md`
- `docs/qa-checklist.md`
