# Architecture Decision Records (ADRs)

ADRs capture cross-cutting decisions so policies do not drift across code, docs,
and operations.

## When to write an ADR
Create an ADR for any decision that changes:
- Security or data retention policy.
- External fan-out or ingestion gating.
- Auth/session behavior or ops exposure rules.
- Data model invariants that affect multiple services.

## How to name
Use `adr-XXXX-short-title.md` with a zero-padded sequence number.

## Process
1. Copy `adr-template.md`.
2. Summarize context, decision, and consequences.
3. Link to relevant code/docs and PRs if available.
