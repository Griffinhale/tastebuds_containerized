# Tastebuds TODO (Prioritized)

This is the first stop for new contributors. It consolidates open work from the
architecture gaps, security backlog, and product roadmap into a single
prioritized list. Each item links back to the source doc for depth.

## How to use this list
1. Pick a priority band (P0 to P3).
2. Read the linked doc(s) to understand constraints and context.
3. For cross-cutting changes, open an ADR per `docs/decisions/README.md`.

## P0 - Production hardening and safety
- Production TLS and cert management (ACME or managed certs). Source:
  `docs/architecture.md`, `docs/security/production-hardening.md`.
- Lock down `/api/ops/*` beyond email allowlists (RBAC or network controls).
  Source: `docs/security/backlog.md`.
- Validate retention defaults against licensing requirements. Source:
  `docs/data-lifecycle.md`, `docs/architecture.md`.
- Provider credential rotation jobs (Spotify/Arr/Jellyfin/Plex). Source:
  `docs/security/backlog.md`.
- Tiered external-search quotas and sustained-throttle alerting. Source:
  `docs/security/backlog.md`.

## P1 - Integration burst
- Expand webhook and sync adapters beyond the current scaffolding (Arr,
  Jellyfin, Plex) and document adapter coverage. Source:
  `docs/architecture.md`, `docs/product/roadmap.md` (7.3).
- Spotify export and pullback (playlist + track metadata) with polished UX.
  Source: `docs/product/roadmap.md` (6.1, 7.3).
- Availability provider connectors and freshness policy. Source:
  `docs/product/roadmap.md`, `docs/data-lifecycle.md`.

## P2 - Ecosystem and community
- ActivityPub/RSS outbox for public menus. Source: `docs/product/roadmap.md` (7.4).
- Moderation and trust & safety plan for public sharing. Source:
  `docs/product/roadmap.md` (8).
- Offline/low-connectivity exports (printable or offline-ready menus). Source:
  `docs/product/roadmap.md` (8).
- Public author handles (sanitized, opt-in). Source: `docs/security/backlog.md`.
- Media detail views UI (helpers already exist). Source: `web/lib/media.ts`.

## P3 - Developer experience and docs
- Keep proxy TLS settings discoverable: align `docs/config.md` and
  `docker/proxy/entrypoint.sh` defaults. Source: `docs/config.md`.
- Draft RFCs for Library + Log, story mode, taste profile refinements,
  availability providers, and community exchange governance. Source:
  `docs/product/roadmap.md` (7.2).
- Add a contributor "good first issue" list once issue tracking is in place.

## Where to start building (by focus)
- **Infra/Ops:** P0 items around TLS, ops endpoint hardening, and quotas.
- **Data/Connectors:** P1 adapter expansions and availability providers.
- **UX/Product:** P1 Spotify flow polish, P2 community and sharing features.
