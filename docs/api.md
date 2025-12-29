# API Usage Guide

This guide explains how to use the API without duplicating the OpenAPI contract.

## Source of Truth
OpenAPI is authoritative. Use `/docs` (Swagger UI) or `/openapi.json` for the
canonical endpoint definitions. This file is a how-to guide only.

## Base URL
- Docker proxy: `https://localhost` (API at `/api`).
- OpenAPI UI: `https://localhost/docs` (proxied to the API service).

## Authentication Overview
- Authenticated routes accept `Authorization: Bearer <access_token>`.
- Browser clients also receive `access_token` + `refresh_token` httpOnly cookies.
- Refresh rotates tokens on every `/api/auth/refresh` and revokes reused tokens.

Example (register + login):
```bash
curl -k -X POST https://localhost/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123","display_name":"Demo"}'

curl -k -X POST https://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"changeme123"}'
```

## Using `/docs`
- Click **Authorize** and paste your bearer token (`Bearer <token>`).
- For cookie-based auth, use the browser in the same session that logged in.

## Common Pitfalls
- External search fan-out requires auth; anonymous requests return 401.
- External results are preview-only until explicit ingest/save actions.
- Ops endpoints (`/api/ops/*`) require admin allowlisting.
- `/health` and `/api/health` return telemetry only to auth/allowlisted callers.

## Example Flow
1. Register/login to obtain an access token.
2. `GET /api/search?q=...` (internal search works anonymously).
3. Authenticated: `GET /api/search?q=...&include_external=true` for previews.
4. `POST /api/ingest/{source}` to fully ingest a previewed item.

## Postman Collection
Import `docs/tastebuds.postman_collection.json` for scripted flows.
