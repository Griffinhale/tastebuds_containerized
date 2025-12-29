# Data Lifecycle

This doc summarizes what data we store, how long it lives, and how it is
bounded. For full schemas, see `schema.md`.

## Data inventory (from `schema.md`)
- `users`: auth accounts (email, password hash), owners for menus and states.
- `media_items`: canonical catalog entries with typed fields and JSONB metadata.
- `book_items` / `movie_items` / `game_items` / `music_items`: per-medium
  extensions keyed by `media_item_id`.
- `media_sources`: ingestion provenance with `source_name`, `external_id`,
  `canonical_url`, `raw_payload`, and `fetched_at`.
- `tags` / `media_item_tags`: owner-scoped tagging.
- `user_item_states`: per-user status, rating, favorite, notes.
- `user_item_logs`: timeline entries with progress, minutes, goals.
- `menus` / `courses` / `course_items`: ordered menu structure and annotations.
- `menu_item_pairings`: narrative links between course items.
- `menu_lineage`: fork and lineage attribution.
- `menu_share_tokens`: temporary tokens for draft share links.
- `media_item_availability`: provider, region, and format availability snapshots.
- `user_taste_profiles`: cached preference summaries derived from usage.
- `integration_webhook_tokens`: hashed webhook tokens for inbound events.
- `integration_ingest_events`: queued webhook events ready for ingestion.
- `automation_rules`: user-defined automation rule definitions.

## Operational and ephemeral data
- `external_search_previews`: short-lived previews for external search results.
- `user_external_search_quotas`: per-user quota windows for external fan-out.

## Retention and caps (settings defaults)
- `EXTERNAL_SEARCH_QUOTA_MAX_REQUESTS` (10) and
  `EXTERNAL_SEARCH_QUOTA_WINDOW_SECONDS` (60): per-user external search quota.
- `EXTERNAL_SEARCH_PREVIEW_TTL_SECONDS` (300): preview cache TTL.
- `EXTERNAL_SEARCH_PREVIEW_MAX_PAYLOAD_BYTES` (50000) and
  `EXTERNAL_SEARCH_PREVIEW_MAX_METADATA_BYTES` (20000): preview payload caps.
- `INGESTION_PAYLOAD_RETENTION_DAYS` (90): raw payload retention window.
- `INGESTION_PAYLOAD_MAX_BYTES` (250000) and `INGESTION_METADATA_MAX_BYTES`
  (50000): ingestion payload caps.
- `AVAILABILITY_REFRESH_DAYS` (7): refresh cadence for availability jobs.
- `TASTE_PROFILE_REFRESH_HOURS` (24): refresh cadence for taste profiles.
- `DRAFT_SHARE_TOKEN_TTL_DAYS` (7): draft share token lifetime.
- `ACCESS_TOKEN_EXPIRES_MINUTES` (30) and `REFRESH_TOKEN_EXPIRES_MINUTES`
  (10080): auth session TTLs.

See `../example.env` for the full list of configuration values.

## Preview TTL and cleanup
- External fan-out results are cached in `external_search_previews` with TTL
  from `EXTERNAL_SEARCH_PREVIEW_TTL_SECONDS`.
- Preview payloads and metadata are truncated to the preview max byte limits.
- A scheduled maintenance job prunes expired previews regularly.
- Preview detail responses are owner-scoped and read-only.

## Raw payload scrubbing and redaction policy
- Ingestion writes `media_sources.raw_payload` but truncates large payloads to
  `INGESTION_PAYLOAD_MAX_BYTES` and `INGESTION_METADATA_MAX_BYTES` first.
- Retention jobs replace stale `raw_payload` values with a redacted marker:
  `{redacted: true, reason: retention_expired, ...}`.
- Log redaction removes common secret patterns before emitting queue errors.
- Raw payloads are never exposed on public endpoints; preview detail is
  restricted to the owning user.
