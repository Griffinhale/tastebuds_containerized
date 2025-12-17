# Release QA Checklist

Tastebuds ships Docker-first. Use this checklist for release candidates to confirm the Compose stack, migrations, ingestion layer, and public surfaces stay healthy.

## 1) Environment & Containers
- [ ] Copy `.env.example` to `.env` and populate secrets/API keys (Google Books, TMDB via `TMDB_API_AUTH_HEADER` or `TMDB_API_KEY`, IGDB, Last.fm) plus `JWT_SECRET_KEY`.
- [ ] `./scripts/dev.sh up` builds/starts services; `docker compose ps` shows `db` as healthy.
- [ ] `./scripts/dev.sh migrate` succeeds and reports the latest Alembic revision.
- [ ] (Optional) `./scripts/dev.sh seed` loads demo data without errors.
- [ ] `./scripts/dev.sh logs api` shows FastAPI booted with the expected environment.

## 2) Database Integrity
- [ ] `docker compose exec api alembic history --verbose | tail -n 1` shows the head revision.
- [ ] Creating duplicate menu slugs/courses/items returns 400/409 (ordering constraints hold).
- [ ] Spot-check ordering: `GET /api/menus/{id}` returns courses/items sorted by `position`.

## 3) Automated Tests
- [ ] `./scripts/dev.sh test` (pytest) passes against the Compose-provided `tastebuds_test` database.
- [ ] If running locally, `TEST_DATABASE_URL=postgresql+asyncpg://... pytest app/tests` passes.

## 4) API Smoke Tests
- [ ] Register + login via `README.md` examples; decode `access_token` to confirm subject and type.
- [ ] `GET /api/docs` renders OpenAPI successfully.
- [ ] `POST /api/ingest/{source}` succeeds for each configured connector (requires valid API keys).
- [ ] `POST /api/menus` with nested courses/items works; slug matches DB state.
- [ ] `GET /api/public/menus/{slug}` returns the published menu when `is_public=true` and 404 when toggled off.
- [ ] `GET /api/search?q=demo&include_external=true` returns paging/source metadata and ingests external hits.
- [ ] `GET /api/search?q=demo&types=book&sources=internal&sources=google_books&page=2&per_page=5&external_per_source=2` paginates internal results and only fans out to the requested connectors.
- [ ] Cross-connector dedupe: ingest a movie internally, run `/api/search` with `sources=tmdb&sources=google_books&include_external=true`, and confirm the internal hit is first, external duplicates are counted in `metadata.counts.external_deduped`, and per-source timings appear under `metadata.source_metrics`.
- [ ] `/api/auth/refresh` rotates the refresh cookie and rejects the previous cookie (expect 401 if you reuse it); `/api/auth/logout` revokes the most recent refresh token.
- [ ] Tags lifecycle: create tag -> assign to ingested media -> list media tags -> delete assignment and tag.
- [ ] User state lifecycle: `PUT /api/me/states/{media_item_id}` upserts status/rating/favorite and returns updated data.

## 5) Frontend App
- [ ] `./scripts/dev.sh web` builds/serves the Next.js app on `:3000` and reads `.env`.
- [ ] Home page cards show API status plus the signed-in widget; refresh/log out buttons work (cookies survive reloads).
- [ ] The home search workspace accepts queries/prompts, respects media-type filters and the include-external toggle, and renders result cards with source context.
- [ ] `/login` and `/register` submit successfully against the FastAPI auth endpoints and set httpOnly cookies.
- [ ] `/menus` lists existing menus, supports drag-to-reorder course items with optimistic updates, and still allows creating/deleting courses/items. The search/ingest drawer should surface empty/error states gracefully and add catalog hits directly into a course.
- [ ] Course search fan-out: toggle `Include external sources`, run a query, and confirm the results are ingested (metadata counts increment) and selectable.
- [ ] Publish a menu and load `http://localhost:3000/menus/{slug}` to confirm the share-ready preview renders, skeleton states display on reload, and the copy/share controls produce a usable link with the new SEO metadata.
- [ ] Let a session expire and hit the `Refresh` button on the Signed-in widget; the UI should show "Session expired. Please log in again." once rotation fails.

## 6) Docs & Artifacts
- [ ] `README.md` and `docs/*.md` match the shipped commands/endpoints.
- [ ] Postman collection (`docs/tastebuds.postman_collection.json`) is importable and points at the correct origin.
- [ ] Note any deviations or flaky steps in `docs/qa-checklist.md` for the next iteration.
