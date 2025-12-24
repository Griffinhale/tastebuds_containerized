# Security & Data Risk Notes

Tastebuds already locks down most CRUD routes behind auth, but a few surfaces can be abused or leak information if deployed as-is. Track and remediate the issues below before opening the stack to the public internet.

## 1. Unauthenticated external search fan-out
- **Where:** `api/app/api/routes/search.py`
- **Problem:** `/api/search` does not require authentication yet still honors `include_external=true` / `sources=` parameters. Anyone can proxy unlimited TMDB/IGDB/Google Books/Last.fm traffic through our backend.
- **Impact:** Connector API quotas are exhausted, and unwanted catalog items + raw payloads get saved (see issue #2). Attackers can also harvest our telemetry response to gauge connector availability.
- **Fix direction:** Allow anonymous search only for internal results; require `get_current_user` when `include_external=true` or any external `sources=` are present. Enforce per-user rate limits/quotas on external calls and optionally return 401/403 if an unauthenticated request asks for external sources instead of silently ignoring it.
- **Implementation note:** External hits are now cached in `external_search_previews` (TTL governed by `external_search_preview_ttl_seconds`) and per-user traffic is throttled via `user_external_search_quotas` (controlled by `external_search_quota_max_requests` / `external_search_quota_window_seconds`).

## 2. Automatic persistence of third-party payloads
- **Where:** `api/app/services/media_service.py` (`search_external_sources` + `upsert_media`)
- **Problem:** Every external search hit is written to `media_items`/`media_sources`, including full `raw_payload`. Users do not need to add the item to a menu for it to stick around.
- **Impact:** Storage bloat and easy abuse when combined with #1 (anyone can flood the DB with arbitrary media); quota and bandwidth waste.
- **Fix direction:** Treat external search as read-only by default and store results in a short-TTL cache. Fully ingest only when a signed-in user interacts (opens details, saves to menu/library, or explicit ingest call). Enforce size caps and optional truncation/encryption on cached payloads, and garbage-collect unreferenced previews after TTL expiry.

## 3. Owner IDs leaked on public menu endpoint
- **Where:** `api/app/api/routes/public.py` + `MenuRead` schema (`app/schema/menu.py`)
- **Problem:** `/api/public/menus/{slug}` returns the full `MenuRead`, which exposes the owner’s UUID for every public menu.
- **Impact:** Anonymous callers can map user IDs, correlate menus by owner, and use the UUID as a pivot for future API guessing or auth attacks.
- **Fix direction:** Add a dedicated DTO for public menus that omits `owner_id` (and any future private fields). If public author info is desired, expose a sanitized handle instead.

## 4. Verbose unauthenticated health telemetry
- **Where:** `api/app/main.py` (`/health`, `/api/health`)
- **Problem:** Health endpoints are publicly readable and include connector names, last errors, and circuit cooldowns.
- **Impact:** Attackers learn which external services we depend on, current failure modes, and can time attacks around open circuits. Error payloads could also leak upstream response details.
- **Fix direction:** Require auth/IP allowlists for detailed telemetry or restrict the public response to a minimal `{ status: "ok" }`. Move full diagnostics behind admin-only routes.

## 5. IGDB access token never refreshes
- **Where:** `api/app/ingestion/igdb.py`
- **Problem:** `_ensure_token` caches the Twitch OAuth token indefinitely and never checks `expires_in`. After the token expires, all IGDB searches/fetches fail until the API container restarts.
- **Impact:** Game ingestion silently dies, connector circuit breakers flap, and users cannot ingest or search for games.
- **Fix direction:** Persist the token expiry timestamp, refresh before it lapses, and invalidate the cache on 401 responses.

---

**Next Steps**
1. Prioritize auth/rate-limiting for `/api/search` and split public/private menu schemas.
2. Draft an ingestion data-retention policy so we only store external payloads with user intent.
3. Harden health endpoints and connector credential refresh logic as part of the next deployment cycle.
