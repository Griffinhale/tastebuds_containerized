# API Guide
_Milestone – June 2024 (historical):_ Auth, menus/courses/items, tags, search, ingestion scaffolding, and public menu endpoints are online in the running stack; `/health` and `/docs` were smoke-tested successfully after applying `alembic upgrade head`.

All routes are served under the configured `API_PREFIX` (default `/api`). Authenticated endpoints expect a `Bearer <access_token>` header.

## Auth
### POST /api/auth/register
Registers a user.
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123","display_name":"Demo"}'
```
Returns `{ access_token, refresh_token, user }`.

### POST /api/auth/login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123"}'
```

## User
### GET /api/me
Current profile.
```bash
curl http://localhost:8000/api/me -H "Authorization: Bearer $TOKEN"
```

### GET /api/me/states
List all `UserItemState` rows for the caller.

### PUT /api/me/states/{media_item_id}
Upsert status/rating/favorite for a given media item.
```bash
curl -X PUT http://localhost:8000/api/me/states/$MEDIA_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"status":"consumed","rating":9,"favorite":true}'
```

## Search
### GET /api/search?q=...&types=book&types=movie&include_external=true
- Queries Postgres first.
- When `include_external=true`, the service reaches out to Google Books, TMDB, IGDB, and Last.fm (subject to API keys) and upserts any fresh results before returning them.
Response:
```json
{
  "source": "internal+external",
  "metadata": {"internal_results": 2, "external_ingested": 3},
  "results": [ {"id":"...","media_type":"book", ...} ]
}
```

## Ingestion
### POST /api/ingest/{source}
Supported sources: `google_books`, `tmdb`, `igdb`, `lastfm`.
Body: `{ "external_id": "..." }`, `{ "url": "..." }`, or a connector-specific token (e.g., `artist::track` for Last.fm). Pass `force_refresh=true` to bust the deduplication cache and replay the connector even when a matching `media_sources` row already exists.
```bash
curl -X POST http://localhost:8000/api/ingest/google_books \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"external_id":"zyTCAlFPjgYC"}'
```
Pipeline:
- Connector fetches the upstream payload and emits a `ConnectorResult` containing canonical fields, metadata JSON, medium-specific extensions, and the raw payload blob.
- `media_service.upsert_media` stores the canonical media row, inserts/updates the extension table (`book_items`, `movie_items`, `game_items`, `music_items`), and persists `media_sources.raw_payload`.
- The response contains the fully hydrated media item (metadata + extension + `sources` array), ready to be referenced when creating menus, tags, or user states.

## Menus
### GET /api/menus
List menus owned by the caller.

### POST /api/menus
Create a menu with optional nested courses/items.
```json
{
  "title": "Story Arc",
  "description": "Books → Films → Games",
  "is_public": true,
  "courses": [
    {"title":"Appetizer","position":1,"items":[{"media_item_id":"...","position":1}]}
  ]
}
```

### GET /api/menus/{id}
Fetch a single menu (auth required, owner only).

### PATCH /api/menus/{id}
Update title/description/visibility.

### DELETE /api/menus/{id}
Remove a menu and cascading courses.

### POST /api/menus/{id}/courses
Add a course (also accepts nested items in payload).

### DELETE /api/menus/{id}/courses/{course_id}
Remove a course.

### POST /api/menus/{id}/courses/{course_id}/items
Add a course item referencing an existing media item.

### DELETE /api/menus/{id}/course-items/{item_id}
Remove a course item.

## Tags
### GET /api/tags
List personal tags plus any global tags.

### POST /api/tags
Create a tag scoped to the caller.
```bash
curl -X POST http://localhost:8000/api/tags \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Neo-Noir"}'
```

### DELETE /api/tags/{tag_id}
Remove one of your tags (also removes media links).

### GET /api/tags/media/{media_item_id}
List tags applied to a media item that you can see.

### POST /api/tags/{tag_id}/media
Assign a tag to a media item:
```bash
curl -X POST http://localhost:8000/api/tags/$TAG_ID/media \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"media_item_id":"$MEDIA_ID"}'
```

### DELETE /api/tags/{tag_id}/media/{media_item_id}
Remove a tag from a media item.

## Public Sharing
### GET /api/public/menus/{slug}
Anonymous, read-only access to a published menu by slug. Slugs are generated at menu creation using a slugified title (with numeric suffixes appended for collisions) and remain stable even if the title changes. When `is_public=false` the API returns 404 regardless of slug correctness.

Ordering guarantees:
- Courses are returned sorted by their `position` field.
- Items inside each course are sorted by `position`, preserving the intended chronology.

Example response (truncated):
```json
{
  "id": "6e0f5f2d-a767-4d44-9549-8a5be9e1d5ac",
  "slug": "neo-noir-night",
  "title": "Neo-Noir Night",
  "is_public": true,
  "courses": [
    {
      "id": "d3abbdbe-bcdb-45a1-8378-fb71c5fd3a75",
      "title": "Appetizer",
      "position": 1,
      "items": [
        {
          "id": "f5cce289-8a65-4f74-8232-237c7b8c0cfe",
          "position": 1,
          "media_item": {
            "id": "aabbccdd-0000-0000-0000-111122223333",
            "media_type": "book",
            "title": "Do Androids Dream of Electric Sheep?",
            "cover_image_url": "https://...",
            "metadata": {"categories": ["Sci-Fi"]}
          }
        }
      ]
    }
  ]
}
```

## Example Workflow
1. Register/login to obtain a token.
2. `POST /api/ingest/tmdb` with an external ID to add a film into the catalog.
3. Repeat for Google Books / IGDB / Last.fm sources.
4. `POST /api/menus` to create a curated journey referencing the ingested media IDs.
5. Toggle `is_public` to `true` and share `/api/public/menus/{slug}`.
