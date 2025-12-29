# ADR-0001: External Fan-Out Gating and Preview-Only Caching

- Status: Accepted
- Date: 2025-12-01

## Context
External connectors provide discovery value but introduce cost, licensing, and
privacy risks. The system needs to allow authenticated discovery without storing
third-party payloads indefinitely or exposing fan-out to anonymous callers.

## Decision
- External search fan-out requires authentication and enforces per-user quotas.
- External results are stored only as short-lived previews with TTL + size caps.
- Full ingestion into canonical tables happens only after explicit user action.
- Preview detail views are read-only and expire with the preview cache.

## Consequences
- Anonymous users cannot trigger external fan-out.
- Preview retention and scrubbing must run reliably.
- UI/clients must handle preview expiry and explicit ingest flows.

## References
- `../architecture.md`
- `../security/threat-model.md`
