# Security & Data Risk Notes

Tastebuds locks down most CRUD routes behind auth. The items below capture remaining risks and the status of previously identified gaps.

## 1. External search controls (implemented)
- **Where:** `api/app/api/routes/search.py`, `app/services/search_preview_service.py`
- **Status:** Auth now gates all external fan-out; per-user quotas throttle usage. External hits stay in short-TTL previews with payload/metadata byte caps and GC; full ingest happens only after authenticated interaction.
- **Residual:** Consider tiered quotas and telemetry/alerts for sustained throttling.

## 2. Third-party payload retention
- **Where:** `app/services/media_service.py`
- **Status:** External search results are preview-only with TTL/size caps. Explicit ingest still writes full `raw_payload` to `media_sources`, but those payloads are now scrubbed after `INGESTION_PAYLOAD_RETENTION_DAYS` via the maintenance queue job.
- **Plan:** Validate retention/redaction defaults against licensing terms and add optional encryption/truncation for long-term storage.

## 3. Public menu surface (implemented)
- **Where:** `api/app/api/routes/public.py`, `app/schema/menu.py`
- **Status:** Public DTO omits `owner_id`; only published menus are served anonymously.
- **Plan:** If author info is desired, add an opt-in sanitized handle.

## 4. Health telemetry (implemented)
- **Where:** `api/app/main.py`
- **Status:** Anonymous callers receive `{status}` only; authenticated or allowlisted hosts (via `HEALTH_ALLOWLIST`) receive connector telemetry.
- **Plan:** Add admin-only diagnostics if deeper logs are needed.

## 5. IGDB access token never refreshes
- **Where:** `api/app/ingestion/igdb.py`
- **Problem:** `_ensure_token` caches the Twitch OAuth token indefinitely and never checks `expires_in`. After the token expires, all IGDB searches/fetches fail until the API container restarts.
- **Impact:** Game ingestion silently dies, connector circuit breakers flap, and users cannot ingest or search for games.
- **Fix direction:** Persist the token expiry timestamp, refresh before it lapses, and invalidate the cache on 401 responses.

---

**Next Steps**
1. Add retention/GC for long-lived ingested payloads (post-ingest, not just previews); consider truncation/encryption options.
2. Finalize IGDB token refresh logic and add similar expiry handling for other OAuth-based connectors.
3. Introduce rate-limit profiles at the proxy and admin-grade health diagnostics once TLS is in place.
