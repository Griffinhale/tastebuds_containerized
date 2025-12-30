# Configuration

This document explains how configuration is grouped and coordinated across the stack; `example.env` is the canonical source for app-level variable names, defaults, and sample values, while proxy-only TLS defaults live in `docker/proxy/entrypoint.sh`.

## Canonical list

Copy `example.env` to `.env` and use it as the single source of truth for new variables or when editing defaults. Changes to the documented variables should happen there first, then propagate to the services that consume them.

## API and worker (shared)

The API and worker share the database URL, JWT secrets, and queue wiring. The same file holds the connectors (TMDB, IGDB, Last.fm, Google Books, Spotify) plus ingestion quotas, preview caps, and raw payload retention limits that keep the services within their expected bounds. Session TTLs, refresh windows, and queue names are documented in `example.env` so you can tune them without chasing multiple docs.

## Web (Next.js)

Next.js primarily needs the API base URLs (`NEXT_PUBLIC_API_BASE`, `API_INTERNAL_BASE`) and the public app base URL for share links; the sample values in `example.env` demonstrate how to target either a local Compose stack or a deployed environment.

## Proxy (nginx)

The proxy reads certificate paths, rotation intervals, and subject details from environment variables with defaults defined in `docker/proxy/entrypoint.sh`. Override `CERT_DIR`, `CERT_PATH`, `KEY_PATH`, or the TLS rotation windows via the proxy service environment (or `.env`) when you need to change local TLS behavior.

## Security-sensitive settings

Treat the database URLs, Redis hostname, JWT secret, credential vault key, and connector credentials (TMDB, IGDB, Last.fm, Google Books, Spotify) as secrets—`example.env` highlights them in one place. Allowlist variables like `OPS_ADMIN_EMAILS` and `HEALTH_ALLOWLIST` also grant elevated access and should be managed carefully.

## List parsing

Fields such as `CORS_ORIGINS`, `OPS_ADMIN_EMAILS`, `WORKER_QUEUE_NAMES`, `HEALTH_ALLOWLIST`, and `SPOTIFY_SCOPES` accept CSV or JSON arrays; the sample values in `example.env` show both formats.
