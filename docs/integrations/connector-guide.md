# Connector Guide

This guide describes connector invariants, mapping rules, and test expectations.

## Invariants
- External fan-out requires auth and is quota gated.
- External results are preview-only until a user explicitly ingests them.
- Dedupe is deterministic (canonical URL first, then title/date keys).
- Connector payloads are size-capped and subject to retention scrubbing.
- Connector failures are circuit-breaker guarded to protect upstream APIs.

## Auth and quotas
- Google Books: `GOOGLE_BOOKS_API_KEY` is optional (unauthenticated allowed).
- TMDB: `TMDB_API_AUTH_HEADER` (preferred bearer token) or `TMDB_API_KEY`.
- IGDB: `IGDB_CLIENT_ID` and `IGDB_CLIENT_SECRET` required for API calls.
- Last.fm: `LASTFM_API_KEY` required for API calls.
- Spotify (integration only): `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`,
  `SPOTIFY_REDIRECT_URI`, `SPOTIFY_SCOPES`.
- Global quota: `EXTERNAL_SEARCH_QUOTA_MAX_REQUESTS` per
  `EXTERNAL_SEARCH_QUOTA_WINDOW_SECONDS`.

## Preview policy
- External search results are cached in `external_search_previews` with TTL from
  `EXTERNAL_SEARCH_PREVIEW_TTL_SECONDS`.
- Preview payloads and metadata are truncated to the preview max byte limits.
- Preview detail is read-only and owner-scoped; ingest writes to canonical
  tables and `media_sources`.

## Mapping rules
- Source of truth: `../attribute-mapping.md` and `../../mappings/*.yaml`.
- Canonical fields map to typed columns on `media_items` or extension tables.
- Metadata stays under `media_items.metadata.*`.
- Raw-only fields remain in `media_sources.raw_payload`.
- Validate manifests from `api/`: `python -m app.scripts.validate_mappings`.
- Sample payloads live in `../../api/app/samples/ingestion/*.json`.

## Connector implementation expectations
- Set stable `source_name`, `source_id`, and `source_url` for provenance.
- Populate extension keys that match extension tables (`book`, `movie`, `game`,
  `music`).
- Support URL identifiers in `parse_identifier` where providers expose them.
- Do not log raw payloads or secrets.

## Test expectations
- Mapping manifests: `api/app/tests/test_mapping_manifest_validation.py`.
- Ingestion mapping: `api/app/tests/test_ingestion_mapping.py`.
- Connector auth behavior: `api/app/tests/test_tmdb_connector.py` and
  `api/app/tests/test_igdb_connector.py`.
- Preview and quota behavior: `api/app/tests/test_previews.py` and
  `api/app/tests/test_search_routes.py`.
