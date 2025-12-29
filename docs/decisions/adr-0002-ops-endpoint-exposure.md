# ADR-0002: Ops Endpoint Exposure Model

- Status: Accepted
- Date: 2025-12-01

## Context
Ops endpoints expose queue, worker, and vault health. This telemetry is useful
for operators but should not be publicly accessible or reachable without
administrative authorization.

## Decision
- `/api/ops/*` requires authentication and admin allowlisting via
  `OPS_ADMIN_EMAILS`.
- Ops routes are only reachable through the edge proxy (no direct container
  exposure).
- The proxy applies rate limits and host validation to ops routes.
- Production deployments should further restrict ops access (allowlist, private
  network, or mTLS).

## Consequences
- Production configs must set `OPS_ADMIN_EMAILS` (do not leave empty).
- Ops telemetry is guarded by both app-level auth and edge routing controls.

## References
- `../architecture.md`
- `../security/production-hardening.md`
