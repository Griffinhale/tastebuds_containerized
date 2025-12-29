# Production Hardening Checklist

Use this checklist for production readiness. Each item should be verified
explicitly before exposure beyond local development.

## Edge Controls
- [ ] TLS is terminated with trusted certs (no self-signed/dev certs).
- [ ] Host validation is enabled at the proxy (no wildcard/unknown hosts).
- [ ] Route-specific rate limits are configured for auth, ingest, search, public.
- [ ] HTTP -> HTTPS redirect is enforced.
- [ ] Proxy only exposes API + web; no direct container ports.

## Auth / Session Controls
- [ ] `JWT_SECRET_KEY` is unique per environment and rotated when compromised.
- [ ] Refresh tokens rotate on every `/api/auth/refresh` and revoke on reuse.
- [ ] Access + refresh TTLs are configured for the environment.
- [ ] Cookie flags are secure (`HttpOnly`, `Secure`, `SameSite`).
- [ ] `OPS_ADMIN_EMAILS` is set for ops endpoints (do not leave empty in prod).

## Ops Endpoint Exposure
- [ ] `/api/ops/*` is reachable only through the proxy and requires admin allowlist.
- [ ] Ops endpoints are allowlisted at the edge (IP allowlist, private network, or mTLS).
- [ ] `/health` and `/api/health` expose telemetry only to auth/allowlisted hosts.

## Logging / Redaction
- [ ] Logs never emit tokens, secrets, or raw third-party payloads.
- [ ] Errors from connector/auth flows are redacted before logging.
- [ ] Log storage access is restricted to operators with least-privilege needs.

## Data Retention + Scrubbing
- [ ] External preview TTLs are set (`EXTERNAL_SEARCH_PREVIEW_TTL_SECONDS`).
- [ ] Raw payload retention is configured (`INGESTION_PAYLOAD_RETENTION_DAYS`).
- [ ] Payload/metadata caps are set (`INGESTION_PAYLOAD_MAX_BYTES`, `INGESTION_METADATA_MAX_BYTES`).
- [ ] Retention/scrubbing jobs are scheduled and verified in the worker queue.

## External Fan-Out + Connectors
- [ ] External search requires auth and enforces per-user quotas.
- [ ] Connector circuit breakers are enabled and visible in health telemetry.
- [ ] Webhook tokens are treated as secrets and never logged.
