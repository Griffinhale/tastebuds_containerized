# Release QA Checklist

Tastebuds ships Docker-first. Each release candidate should walk through this checklist to ensure the Compose stack, migrations, ingestion layer, and public surfaces stay healthy.

## 1. Environment & Containers
- [ ] Copy `.env.example` to `.env` and confirm all secrets/API keys are populated.
- [ ] `./scripts/dev.sh up` builds fresh images and all services report `healthy` via `docker compose ps`.
- [ ] `./scripts/dev.sh migrate` succeeds and prints the latest Alembic revision.
- [ ] `./scripts/dev.sh seed` loads demo data without errors (verifies fixtures + ingestion samples).
- [ ] `./scripts/dev.sh logs api` shows FastAPI booting with the expected environment banner (`ENVIRONMENT=production` for release).

## 2. Database Integrity
- [ ] `docker compose exec api alembic check` reports heads in sync (no pending migrations).
- [ ] Unique constraints: attempt to create duplicate menu slugs/courses/items and ensure the API returns 400/409.
- [ ] Spot-check ordering by querying `menus`, `courses`, and `course_items` to confirm `position` columns line up with the seed data.

## 3. Automated Tests & Linters
- [ ] `./scripts/dev.sh test` (pytest) passes using the Compose-provided `tastebuds_test` database.
- [ ] `docker compose exec api mypy app` passes (type coverage for services/schemas).
- [ ] `docker compose exec api ruff check app` passes (style + import hygiene).

## 4. API Smoke Tests
- [ ] Register + login via the curl examples in `README.md` and confirm tokens decode with the correct claims.
- [ ] `GET /api/docs` renders OpenAPI without exceptions and lists all routers.
- [ ] `POST /api/ingest/{source}` for each connector (Google Books, TMDB, IGDB, Last.fm) ingests one fixture item and returns metadata + extension rows.
- [ ] `POST /api/menus` with nested courses/items succeeds and the response slug matches DB state.
- [ ] `GET /api/public/menus/{slug}` for the menu above works when `is_public=true` and returns 404 when toggled off.
- [ ] `GET /api/tags` shows global + user tags; attach/detach tags from a newly ingested media item and verify lookups.

## 5. Observability & Health
- [ ] `GET /health` returns `{"status":"ok"}`.
- [ ] API logs show ingestion retries (tenacity) when simulating upstream 429/500 responses (temporarily tweak credentials or throttle).
- [ ] Confirm structured logging fields (`request_id`, `path`, `status_code`) appear in `api` logs.

## 6. Docs & Distribution
- [ ] `README.md` instructions match the release artifacts (commands, env vars, helper scripts).
- [ ] `docs/api.md` examples reflect the current OpenAPI schema (paths, payloads, query params).
- [ ] `docs/attribute-mapping.md` entries mirror connector behavior (especially new metadata/extension fields).
- [ ] Export/refresh the Postman collection used for demos and attach it to the release notes.

## 7. Final Sign-off
- [ ] Tag the commit, push images, and attach SHA/compose instructions to the release notes.
- [ ] Capture any deviations or flaky steps in `docs/qa-checklist.md` for the next iteration.
