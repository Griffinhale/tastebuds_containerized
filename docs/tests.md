# Tests

This document summarizes the current test suites and what each test checks.

## How to run
- `./scripts/dev.sh test` runs backend pytest in Docker.
- Local: `cd api && TEST_DATABASE_URL=... pytest app/tests`.
- Frontend checks: `npm run lint`, `npm run prettier:check`, `npm run typecheck` in `web/`.

## Fixtures and harness
### `api/app/tests/conftest.py`
- `_use_plaintext_passwords`: forces plaintext hashing for faster auth tests.
- `session`: creates an isolated async database schema per test, creates tables, and drops everything on teardown.
- `client`: overrides `get_db` and provides an async HTTP client bound to the FastAPI app.

### `api/app/tests/utils.py`
- `register_and_login`: helper for creating an authenticated session with a fresh user.

## Backend suites (pytest)
### `api/app/tests/test_availability_routes.py`
- `test_availability_upsert_and_summary`: availability CRUD + summary aggregation.

### `api/app/tests/test_auth_routes.py`
- `test_register_and_login_flow`: register returns user + tokens and sets cookies; login returns user + access token cookie.
- `test_refresh_and_logout_flow`: refresh rotates the refresh cookie, old refresh tokens fail, logout clears cookies and revokes tokens.

### `api/app/tests/test_auth_sessions.py`
- `test_session_inventory_and_revoke`: sessions list returns current session; revoke marks it inactive with `revoked_at`.
- `test_session_revoke_is_scoped_to_owner`: users cannot revoke another user's session (404).

### `api/app/tests/test_automations_routes.py`
- `test_automation_rule_lifecycle`: create/list/update/run/delete automation rules and validate ingest execution output.
- `test_automation_rule_sync_action`: sync action adapter returns a completed run with action results.

### `api/app/tests/test_credential_vault.py`
- `test_credential_vault_store_and_read`: secrets can be stored and retrieved for a provider.
- `test_credential_vault_respects_expiry_and_clear`: expired secrets return None and are cleared on failure.

### `api/app/tests/test_health.py`
- `test_health_reports_ok_without_auth`: unauthenticated `/api/health` returns `{status: ok}` without ingestion telemetry.
- `test_health_reports_ok_for_authenticated_users`: authenticated callers see ingestion telemetry with empty sources/issues.
- `test_health_degrades_for_authenticated_users`: degraded status includes last error and issue reason in telemetry.
- `test_health_allows_allowlisted_clients_without_auth`: allowlisted hosts receive ingestion telemetry without auth.
- `test_health_flags_repeated_failures`: repeated failures mark sources degraded and emit issue reasons.

### `api/app/tests/test_igdb_connector.py`
- `test_igdb_token_cached_until_expiry`: token fetched once and reused until expiry.
- `test_igdb_token_refreshes_when_expired`: expired token triggers a refresh.
- `test_igdb_fetch_retries_after_401`: 401 triggers token refresh and a retry for the game fetch.

### `api/app/tests/test_ingestion_mapping.py`
- `test_book_ingestion_populates_extension`: book extension fields and metadata categories persist on upsert.
- `test_movie_ingestion_populates_extension`: movie extension fields and metadata status persist on upsert.
- `test_game_ingestion_populates_extension`: game extension fields and metadata platforms persist on upsert.
- `test_music_ingestion_populates_extension`: music extension fields and metadata tags persist on upsert.

### `api/app/tests/test_ingestion_observability.py`
- `test_ingestion_monitor_opens_circuit_after_repeated_failures`: repeated failures open the circuit and record skips/metrics.
- `test_ingestion_monitor_recovers_after_cooldown_and_success`: cooldown + success resets failure streak and tracks success.

### `api/app/tests/test_integrations_routes.py`
- `test_integration_status_and_webhook_token`: credentials + webhook token lifecycle reflected in status.

### `api/app/tests/test_maintenance_jobs.py`
- `test_prune_media_source_payloads_strips_old_rows`: old raw payloads are redacted with a retention reason.
- `test_prune_media_source_payloads_can_be_disabled`: retention disabled leaves payloads untouched.

### `api/app/tests/test_media_service.py`
- `test_upsert_media_truncates_payloads`: oversized metadata and raw payloads are truncated with a reason flag.

### `api/app/tests/test_menu_routes_api.py`
- `test_menu_course_item_flow`: menu/course/item create, list, delete, and final empty-course state.
- `test_reorder_course_items`: reorder endpoint returns items in the requested order.

### `api/app/tests/test_menu_collaboration.py`
- `test_menu_share_tokens_and_public_draft`: draft share token creation and public access lifecycle.
- `test_menu_pairings_and_lineage`: pairings CRUD plus fork lineage summaries.

### `api/app/tests/test_menu_service.py`
- `test_menu_slug_uniqueness`: duplicate titles yield unique slugs with numeric suffixes.
- `test_menu_slug_stable_on_update`: menu slug does not change when updating the title.

### `api/app/tests/test_library_logs.py`
- `test_log_flow_updates_library`: log creation syncs library summary, next-up queue, and state status.
- `test_log_filters_and_update`: log filters and patch updates work as expected.

### `api/app/tests/test_log_redaction.py`
- `test_task_queue_redacts_redis_url_in_logs`: secrets are scrubbed from queue failure logs.

### `api/app/tests/test_ops.py`
- `test_ops_requires_auth`: unauthenticated requests to `/api/ops/queues` are rejected.
- `test_ops_snapshot_with_auth`: admin allowlisted user receives status, queues, and vault in the snapshot.
- `test_ops_requires_admin_allowlist`: non-admins are rejected when allowlist is configured.

### `api/app/tests/test_previews.py`
- `test_preview_detail_scoped_and_expires`: preview details enforce ownership + TTL.

### `api/app/tests/test_public_menu.py`
- `test_public_menu_lookup`: only public menus resolve by slug.
- `test_public_menu_respects_ordering`: course and item positions are returned in sorted order.
- `test_public_menu_route_hides_owner_id`: public menu route omits `owner_id`.

### `api/app/tests/test_search_routes.py`
Note: CI runs these tests against SQLite, so internal search uses the normalized substring fallback instead of Postgres FTS.
- `test_search_pagination_produces_metadata`: paging metadata and counts align with internal results.
- `test_external_search_requires_auth`: external fan-out without auth returns 401.
- `test_search_ranking_prioritizes_title_over_metadata`: title matches rank above metadata-only matches.
- `test_search_handles_diacritics_and_punctuation`: diacritic folding + malformed punctuation remain safe.
- `test_search_vector_refreshes_after_extension_update`: extension updates refresh the stored search vector.
- `test_search_external_ingests_multi_source`: external sources ingest and report per-source counts.
- `test_search_sources_filter_limits_external_only`: filtering to sources limits fan-out and metadata to those sources.
- `test_search_types_filter_drops_incompatible_sources`: type filters prevent incompatible connectors from running.
- `test_search_external_per_source_limits_counts`: per-source limits cap external ingestion counts.
- `test_search_external_dedupes_against_internal_and_tracks_metrics`: internal matches dedupe externals and track metrics.
- `test_search_merge_order_follows_source_order`: result ordering follows requested source order.
- `test_search_external_previews_cached`: external previews are stored with a future expiry.
- `test_search_external_quota_enforced`: external search quota returns 429 once exceeded.

### `api/app/tests/test_security_regressions.py`
- `test_external_fanout_not_triggered_without_auth`: unauthenticated external fan-out is blocked even when requested.

### `api/app/tests/test_seed_script.py`
- `test_seed_populates_demo_menu`: seed creates the demo menu with ordered courses/items and demo payloads.
- `test_seed_is_idempotent`: running the seed twice does not duplicate menus or sources.

### `api/app/tests/test_smoke_flows.py`
- `test_login_menu_crud_and_search_ingest_flow`: end-to-end flow for auth, menus, external search ingest, and cleanup.

### `api/app/tests/test_tags.py`
- `test_tag_lifecycle`: tag create/list/attach/remove/delete flows work.
- `test_tag_access_control`: non-owners cannot tag media they do not own.

### `api/app/tests/test_taste_profile.py`
- `test_taste_profile_builds_from_logs_tags_and_menus`: taste profile aggregates menus, logs, and tags.

### `api/app/tests/test_tmdb_connector.py`
- `test_tmdb_auth_prefers_bearer`: bearer auth header takes precedence over API key.
- `test_tmdb_auth_uses_api_key_when_header_missing`: API key is used when bearer is absent.
- `test_tmdb_auth_errors_without_credentials`: missing credentials raises an error.

### `api/app/tests/test_user_states.py`
- `test_user_state_upsert_and_list`: upserts state and lists updated values.

### `api/app/tests/test_mapping_manifest_validation.py`
- `test_mapping_manifests_are_valid`: mapping YAMLs pass schema validation.
