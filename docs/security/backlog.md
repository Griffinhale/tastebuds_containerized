# Security Backlog

Items tracked for future hardening work. Keep the production checklist
(`docs/security/production-hardening.md`) crisp by parking future work here.

- Tiered external-search quotas and sustained-throttle alerting.
- Validate payload retention defaults against licensing requirements.
- Optional encryption for long-lived raw payload storage.
- Role-based admin claims (beyond email allowlists) for ops diagnostics.
- Mutual TLS or private-network-only access for `/api/ops/*` in production.
- Provider-specific credential rotation jobs for Spotify/Arr/Jellyfin/Plex.
- Optional public author handles for menus (sanitized, opt-in).
