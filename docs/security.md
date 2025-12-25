# Security & Data Risk Notes

Tastebuds locks down most CRUD routes behind auth. The items below capture remaining risks and the status of previously identified gaps.

## 1. External search controls (implemented)
- **Where:** `api/app/api/routes/search.py`, `app/services/search_preview_service.py`
- **Status:** Auth now gates all external fan-out; per-user quotas throttle usage. External hits stay in short-TTL previews with payload/metadata byte caps and GC; full ingest happens only after authenticated interaction.
- **Residual:** Consider tiered quotas and telemetry/alerts for sustained throttling.

## 2. Third-party payload retention
- **Where:** `app/services/media_service.py`
- **Status:** External search results are preview-only with TTL/size caps. Explicit ingest now size-caps payload + metadata at write time and still scrubs `raw_payload` after `INGESTION_PAYLOAD_RETENTION_DAYS` via the maintenance queue job.
- **Plan:** Validate retention/redaction defaults against licensing terms and add optional encryption for long-term storage.

## 3. Public menu surface (implemented)
- **Where:** `api/app/api/routes/public.py`, `app/schema/menu.py`
- **Status:** Public DTO omits `owner_id`; only published menus are served anonymously.
- **Plan:** If author info is desired, add an opt-in sanitized handle.

## 4. Health telemetry (implemented)
- **Where:** `api/app/main.py`
- **Status:** Anonymous callers receive `{status}` only; authenticated or allowlisted hosts (via `HEALTH_ALLOWLIST`) receive connector telemetry.
- **Plan:** Add admin-only diagnostics if deeper logs are needed.

## 5. IGDB access token never refreshes (resolved)
- **Where:** `api/app/ingestion/igdb.py`
- **Status:** Token expiry is now cached with a refresh buffer; 401s clear the cache and force a refresh so searches/ingests recover without restarts.
- **Residual:** Mirror this pattern for other OAuth-backed connectors as they arrive.

## 6. Integration credential handling
- **Where:** `api/app/services/credential_vault.py`, `app/models/credential.py`
- **Status:** Per-user integration secrets are encrypted with Fernet at rest (`user_credentials`), include optional expiries, and clear on failures. Vault health surfaces through `/api/ops/queues`.
- **Residual:** Add provider-specific rotation jobs once connectors (Spotify/Arr/Jellyfin) are wired; consider HSM/KMS when moving beyond dev.

## 7. Ops surface scoping
- **Where:** `docker/proxy/nginx.conf`, `api/app/api/routes/ops.py`
- **Status:** Proxy now rate-limits and IP-allows `/api/ops/`, validates `Host` for localhost-only use, and the API/web services are exposed only through the proxy by default. The API requires an admin email allowlist for diagnostics, and health includes queue + vault status.
- **Residual:** Move to role-based admin claims once user roles exist; consider mutual TLS for production ops endpoints.

---

**Next Steps**
1. Validate payload caps/retention defaults against licensing terms; consider migrating sensitive ingestion payloads to encrypted storage.
2. Mirror IGDB-style token refresh/401 handling for upcoming Spotify/Arr/Jellyfin connectors and move secrets into the vault by default.
3. Tighten ops exposure with role-based admin claims and, for production, mutual TLS or private-network-only access to `/api/ops/*`.
