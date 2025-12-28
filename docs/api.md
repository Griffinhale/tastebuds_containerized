# API Guide

Base path is `API_PREFIX` (default `/api`). Authenticated routes expect `Authorization: Bearer <access_token>`. Register/login/refresh return both access and refresh tokens and also set httpOnly cookies for browser clients. When using the proxy, base URL is `https://localhost` and the dev cert is self-signed (use `curl -k` or trust the cert).

## Health & Docs
- `GET /health` and `GET /api/health` return `{"status":"ok","ingestion":{"sources":{},"issues":[]}}`. When a connector circuit is open or a connector's last call failed, `status` flips to `degraded` and `ingestion.issues` lists the affected sources/operations along with the last error or remaining cooldown.
- `GET /api/ops/queues` (auth required) reports Redis/RQ health: queue sizes, worker presence, scheduler counts, and Redis server info. Useful for spotting stalled jobs or empty workers.
- OpenAPI/Swagger UI: `/docs` (proxied to the API service).

## Auth
Browser clients receive httpOnly cookies (`access_token`, `refresh_token`) on login/register/refresh; tokens are also returned in the JSON response for non-browser callers.

### POST /api/auth/register
Create a user and return tokens.
```bash
curl -k -X POST https://localhost/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123","display_name":"Demo"}'
```

### POST /api/auth/login
Exchange credentials for a token pair.
```bash
curl -k -X POST https://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123"}'
```

Response for both: `{ access_token, refresh_token, token_type, user }` and sets cookies.

### POST /api/auth/refresh
Issue a new token pair from a refresh token. Supply the refresh token either in the request body or rely on the `refresh_token` cookie.
```bash
curl -k -X POST https://localhost/api/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<refresh>"}'
```
Response matches login/register and sets fresh cookies.

### POST /api/auth/logout
Clears auth cookies. Returns `204 No Content`.

### GET /api/auth/sessions
List refresh-token sessions for the current user.
- Query params: `include_expired` (default false), `include_revoked` (default false).
- Response items include: `id`, `created_at`, `expires_at`, `revoked_at`, `revoked_reason`, `replaced_by_token_id`, `is_active`, `is_current`.

### POST /api/auth/sessions/{token_id}/revoke
Revoke a specific session by ID. Returns `204 No Content` or `404` if the session does not belong to the caller.

## Users & States
- `GET /api/me` - current profile.
- `GET /api/me/states` - all of your `user_item_states` rows.
- `PUT /api/me/states/{media_item_id}` - upsert status/rating/favorite/notes/timestamps for a media item.
  ```bash
  curl -k -X PUT https://localhost/api/me/states/$MEDIA_ID \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"status":"consumed","rating":9,"favorite":true}'
  ```
- `GET /api/me/taste-profile` - aggregated taste profile (use `?refresh=true` to rebuild).
- `POST /api/me/taste-profile/refresh` - force a taste profile refresh.

## Library + Logs
### GET /api/me/library
Returns a library snapshot with status counts, full item list, and a next-up queue.

### GET /api/me/logs
List log entries for the current user.
- Query params: `media_item_id`, `log_type` (`started`, `progress`, `finished`, `note`, `goal`), `limit`, `offset`.

### POST /api/me/logs
Create a log entry (also syncs the related `user_item_state` when appropriate).
```bash
curl -k -X POST https://localhost/api/me/logs \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"media_item_id":"'$MEDIA_ID'","log_type":"progress","minutes_spent":30,"progress_percent":40,"notes":"Good pacing."}'
```

### PATCH /api/me/logs/{log_id}
Update a log entry.

### DELETE /api/me/logs/{log_id}
Remove a log entry.

## Search
`GET /api/search?q=...&types=book&types=movie&include_external=true`
- Always searches Postgres first. Accepts `types` to filter media types and `page`/`per_page` for internal pagination.
- External fan-out is opt-in via `include_external=true` or explicitly enumerating `sources` (e.g., `sources=igdb&sources=tmdb`). `external_per_source` limits per-connector ingestion; defaults to 1 (max 5).
- Auth policy: anonymous callers only receive internal results. When unauthenticated, `include_external=true` or external `sources` are rejected (401/403) or ignored per deployment policy. Authenticated callers may request external sources subject to per-user quotas/rate limits (see `external_search_quota_max_requests` / `external_search_quota_window_seconds`).
- Persistence policy: external search responses stay in a short-TTL preview cache (`external_search_preview_ttl_seconds`) and are fully ingested into `media_items`/`media_sources` only after an authenticated user explicitly ingests or interacts (opens details or saves to a menu/library). Cached payloads should be size-capped and garbage-collected.
- Allowed `sources`: `internal`, `external`, `google_books`, `tmdb`, `igdb`, `lastfm`. Explicit external sources still include internal results when `include_external=true`; omit both `include_external` and `internal` to skip internal search.
- Dedupe and ordering: merged results are deterministic—internal first, then external in the order requested (`sources`), then normalized title and release date. Cross-connector duplicates are suppressed using canonical URL or normalized title + release date keys.
- Response: `{ source: "internal"|"external"|"internal+external", metadata: { paging: {page, per_page, offset, total_internal}, counts: { internal, external_ingested?, external_returned?, external_deduped? }, source_counts: { internal, external?, google_books?, tmdb?, igdb?, lastfm? }, source_metrics: { internal: { returned }, tmdb?: { returned, ingested, deduped, search_ms, fetch_ms, dedupe_reasons? }, ... }, dedupe_reasons?: { canonical_url?, title_release_date?, title_only? } }, results: [{ ...media_item, source_name?, source_id?, preview_id?, preview_expires_at?, in_collection?, availability_summary? }, ...] }`.

## Availability
- `GET /api/media/{media_item_id}/availability` - list availability entries by provider/region/format.
- `PUT /api/media/{media_item_id}/availability` - upsert availability entries (auth required).
- `POST /api/media/availability/summary` - return summary rows for a list of media IDs (public).

## Ingestion
`POST /api/ingest/{source}` - Supported sources: `google_books`, `tmdb`, `igdb`, `lastfm`.
- Body: `{ "external_id": "...", "url": "...", "force_refresh": false }` (either `external_id` or `url` is required).
- Identifier hints: Google Books volume ID or URL; TMDB accepts `603`/`movie:603`/`tv:123` or a TMDB URL; IGDB expects a numeric ID; Last.fm accepts `Artist::Track`, MBID, or a track URL.
- TMDB prefers a v4 bearer token via `TMDB_API_AUTH_HEADER` (full `Authorization` header value); `TMDB_API_KEY` is accepted as a fallback. Credentials are validated at startup.
- Dedupe: unique `(source_name, external_id)` in `media_sources`; `force_refresh=true` replays the connector and overwrites stored payloads.
- Response: `{ media_item: { ...sources[] }, source_name }`.

## Menus
- `GET /api/menus` - menus owned by the caller.
- `POST /api/menus` - create a menu (supports nested courses/items). Slug is generated from the title and remains stable even if the title changes.
- `GET /api/menus/{id}` - fetch one menu (owner only).
- `PATCH /api/menus/{id}` - update title/description/visibility.
- `DELETE /api/menus/{id}` - delete a menu and cascade children.
- `POST /api/menus/{id}/fork` - fork a menu into a new draft (public menus or owner only).
- `GET /api/menus/{id}/lineage` - lineage summary for a menu.
- `POST /api/menus/{id}/courses` - add a course (optionally with items).
- `PATCH /api/menus/{id}/courses/{course_id}` - update a course title/description/intent (optional `expected_updated_at` for conflict detection).
- `DELETE /api/menus/{id}/courses/{course_id}` - remove a course.
- `POST /api/menus/{id}/courses/{course_id}/items` - add a course item pointing to an existing media item.
- `PATCH /api/menus/{id}/course-items/{item_id}` - update course item annotations (optional `expected_updated_at` for conflict detection).
- `DELETE /api/menus/{id}/course-items/{item_id}` - remove a course item.
- `POST /api/menus/{id}/courses/{course_id}/reorder-items` - persist a new item order via an array of course item IDs.
- `GET /api/menus/{id}/pairings` - list narrative pairings.
- `POST /api/menus/{id}/pairings` - create a pairing between two course items.
- `DELETE /api/menus/{id}/pairings/{pairing_id}` - delete a pairing.
- `GET /api/menus/{id}/share-tokens` - list draft share tokens for a menu.
- `POST /api/menus/{id}/share-tokens` - create a draft share token.
- `DELETE /api/menus/{id}/share-tokens/{token_id}` - revoke a draft share token.

Ordering is enforced via unique `(menu_id, position)` for courses and `(course_id, position)` for items, so responses always reflect the intended chronology. Courses now return `updated_at` for conflict-aware edits, support an optional `intent` field, and course items accept `notes` as narrative annotations with their own `updated_at`.
When `expected_updated_at` is supplied and stale, the API responds with `409 Conflict` and includes `current_updated_at` in the error detail payload so clients can resolve the mismatch.

## Tags
- `GET /api/tags` - list your tags plus global ones.
- `POST /api/tags` - create a tag scoped to the caller.
- `DELETE /api/tags/{tag_id}` - delete one of your tags (also removes assignments).
- `GET /api/tags/media/{media_item_id}` - tags applied to a media item visible to you.
- `POST /api/tags/{tag_id}/media` - attach a tag to a media item.
- `DELETE /api/tags/{tag_id}/media/{media_item_id}` - remove a tag from a media item.

## Public Sharing
`GET /api/public/menus/{slug}` - anonymous read-only access to a published menu. Returns 404 when `is_public=false`, even if the slug exists. Courses and items are returned sorted by their `position` fields to preserve chronology.
`GET /api/public/menus/draft/{token}` - anonymous access to a draft menu by share token (expires/revocable).
`GET /api/public/menus/{slug}/lineage` - public lineage summary (public forks + visible source menu).

## Short Example Flow
1. Register/login to obtain `access_token`.
2. `POST /api/ingest/tmdb` with `{"external_id":"603"}` (or `movie:603`) to ingest a film.
3. `POST /api/menus` with a course that references the ingested media ID.
4. `GET /api/public/menus/{slug}` to share the published menu.
