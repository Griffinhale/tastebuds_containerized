# Ops Runbook

This runbook covers common operational checks for the local Docker stack.

## Runtime topology & order
See `architecture.md` to understand the runtime topology and the recommended startup order. Use `./scripts/dev.sh up` to start the full stack; it handles service ordering and dependencies.

## Shutdown order
Stop in reverse order to avoid dropping dependencies:
proxy -> web -> scheduler -> worker -> api -> redis -> db. See `architecture.md` for the full runtime layout when you need to adjust this sequence.

## Health endpoints
- `/health` and `/api/health` return a status payload.
- Unauthenticated callers get `{status: ok}` only.
- Authenticated or allowlisted callers see ingestion telemetry.
- Allowlist is configured with `HEALTH_ALLOWLIST` (CSV or JSON array).

Triage tips:
- `status: degraded` means ingestion issues are present.
- `ingestion.issues` lists source, operation, reason, and last_error.
- `ingestion.sources.*` shows circuit state and remaining cooldown.

## Queue triage (`/api/ops/queues`)
- Requires auth; if `OPS_ADMIN_EMAILS` is set, the user must be allowlisted.
- `status` is `online`, `degraded`, or `offline`.
- `queues` shows per-queue sizes, deferred, scheduled, started, and failed counts.
- `workers` shows worker state, queues, and current job id.
- `scheduler.scheduled_jobs` should be non-zero when healthy.
- `vault` reports credential vault health.

## Queue drain and resume
Drain:
- Stop scheduling new jobs where possible (pause ingest or automation flows).
- Keep the worker running until `/api/ops/queues` shows queue sizes at 0.
- If you need to pause processing, stop worker and scheduler containers.

Pause/resume (Docker):
- `docker compose stop worker scheduler`
- `docker compose start worker scheduler`

## Connector failure triage
1. Check `/api/health` (auth required) for degraded sources and last_error.
2. Confirm worker and scheduler health via `/api/ops/queues`.
3. Validate connector credentials in `.env` (TMDB, IGDB, Last.fm, Google Books).
4. Look for `ingestion_failure` or `ingestion_circuit_open` log events.
5. If a circuit is open, wait for cooldown or fix the root cause; restarting the
   API clears in-memory circuit state but should not be the first response.

## Verify retention jobs
- Preview cleanup and payload scrubbing are scheduled on API startup.
- Check `/api/ops/queues` for `scheduler.scheduled_jobs` and a `maintenance` queue.
- Look for log lines:
  - "Pruned X expired external search previews"
  - "Scrubbed X ingestion payloads older than N days"
- If scheduled jobs are missing, restart the API and ensure scheduler + worker
  are running.
