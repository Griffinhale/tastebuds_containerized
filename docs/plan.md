# Tastebuds Containerized — Product & Delivery Plan

Tastebuds helps people compose “media tasting menus” that bridge books, film, games, and music. The containerized stack already stands up FastAPI, Postgres, and the Next.js workspace; this document keeps the project oriented toward customer value, ecosystem leverage, and the systems-level guardrails that make future integrations low-risk.

## 1. Vision Snapshot (2025—2026)
- **Curated cross-media journeys:** Tastebuds should feel like hosting a dinner party for your media diet—menus are story-driven, not just playlists.
- **Portable media graph:** Every ingestion normalizes into a canonical catalog so other services (Spotify, Arr suite, Jellyfin/Plex, Letterboxd/StoryGraph exports) can subscribe or push updates without format drift.
- **Composable automations:** Anything you can do manually should be automatable via API/webhooks, enabling “if Jellyfin imports new film, stage a suggested pairing course”.
- **Privacy-first collaboration:** Logged-in collaboration works without forcing public sharing; revocable session awareness and per-menu visibility are mandatory.

## 2. Experience Principles
1. **Menus over media dumps:** Every workflow reinforces curation—courses, pacing, annotations, share cards.
2. **Context-rich ingestion:** Show provenance, raw metadata, connector health, and dedupe explanations so trust remains high.
3. **Link out, don’t lock in:** Integrations (Spotify playlists, Overseerr/Radarr/Sonarr, Jellyfin collections, Notion databases) are first-class exports instead of gated premium features.
4. **Instant feedback:** Health pings, pagination, background ingestion, and optimistic UI states keep the app responsive even when third-party APIs throttle.
5. **Accessible everywhere:** Keyboard-first editing, screen-reader safe drawers, and shareable public pages that degrade gracefully without JS.
6. **Diet visibility:** The Library + Log makes progress, pacing, and reflection visible so users understand their actual consumption, not just plans.
7. **Availability-aware curation:** Always surface where items can be watched/read/listened to, with alternatives when access is limited.
8. **Community exchange with lineage:** Sharing supports forks/remixes with provenance and attribution without drowning users in noise.

## 3. Differentiation vs Incumbents
- **Letterboxd / Goodreads:** Single-medium focus, tagging is social but cross-medium storytelling is missing. Tastebuds differentiates by blending media types in one sequence and by supporting data egress (JSON, ActivityPub, RSS).
- **Spotify / Apple Music:** Excellent playlist UX but no native bridge to books/games/film. Tastebuds can pipe curated music courses into Spotify while referencing related media and annotations.
- **The Arr suite (Radarr/Sonarr/Lidarr/Readarr):** Fantastic automation for downloads, yet no human-friendly way to present “what to experience next.” Tastebuds can subscribe to Arr webhooks to automatically add ready-to-watch items into draft menus.
- **Jellyfin / Plex / Emby libraries:** Rich metadata but limited share/vibe-building. Tastebuds can ingest watch history, highlight-lists, and publish back curated “Collections” with course ordering.

## 4. Personas & Jobs To Be Done
- **The Host (community organizer, podcaster):** Needs to craft themed nights or discussion guides. Jobs: build a shareable flow, coordinate cross-platform availability, update menus collaboratively.
- **The Researcher (critics, librarians, teachers):** Needs canonical metadata, provenance, and bulk imports/exports. Jobs: ensure accuracy, cite sources, publish to catalogs like StoryGraph or LMS.
- **The Enthusiast (friends swapping recs):** Needs lightweight search + ingest, delightful share cards, Spotify/Jellyfin hand-offs, and safety around private drafts.

## 5. Product Surface Map
- **APIs:** `/api/search`, `/api/ingest/{source}`, `/api/menus`, `/api/menus/{id}/fork`, `/api/menus/{id}/pairings`, `/api/menus/{id}/share-tokens`, `/api/public/menus/{slug}`, `/api/public/menus/draft/{token}`, `/api/public/menus/{slug}/lineage`, `/api/media/availability/*`, `/api/me/taste-profile`, `/api/health`, `/api/auth/*`, `/api/auth/sessions`, `/api/me/library`, `/api/me/logs`. Forthcoming: `/api/automations`, `/api/integrations/*`.
- **Connectors (shipping):** Google Books, TMDB, IGDB, Last.fm.
- **Connectors (planned):** Spotify (playlist + track metadata), Discogs, MusicBrainz, StoryGraph export/import, Arr suite webhooks, Jellyfin/Plex library sync, Notion two-way sync, RSS/ActivityPub feeds.
- **Interfaces:** Next.js workspace (auth, search, menu editor, share view, Library + Log hub, Taste Profile dashboard, availability overlays, community exchange), CLI/automation scripts, optional mobile-friendly PWA.
- **Architecture source of truth:** `docs/architecture.md` captures current services, data flows, and delivery dependencies (queue, reverse proxy, retention). Keep this plan and the architecture doc in lockstep.

## 6. Integration & Ecosystem Roadmap
| Phase | Target | Why it matters | Notes |
| --- | --- | --- | --- |
| **6.1 Spotify pairing** | Export a menu’s music courses into Spotify playlists; optionally pull artists/tracks back into Tastebuds. | Unlocks instant playback, differentiates from static lists. | Needs OAuth/device linking and per-user credential storage. |
| **6.2 Arr suite bridge** | Listen for Radarr/Sonarr/Lidarr webhooks, surface “ready to ingest” queue, auto-tag menus once downloaded. | Taps into existing automation communities. | Map Arr quality IDs into metadata for provenance. |
| **6.3 Jellyfin/Plex ingestion** | Pull watch/listen history + custom collections, convert into backlog suggestions. | Lets Tastebuds stay accurate without manual ingestion. | Requires token-scoped background sync workers. |
| **6.4 Media library exports** | Push menus as Jellyfin Collections, Notion databases, Obsidian markdown vaults, or ActivityPub feeds. | Keeps Tastebuds as the curator brain while other apps stay the playback surface. | Build export adapters over the canonical graph. |

## 7. Implementation Roadmap
_Phase gates: 7.1 shipped; 7.3 depends on the queue/broker, rate limits, and the credential vault from 7.1._

### 7.1 Security & Foundation (complete)
- External search is auth+quota gated; anonymous callers only search internal. External hits live in short-TTL previews with payload/metadata caps and GC; full ingest follows user interaction.
- Public surfaces: public menu DTO omits `owner_id`; `/health` returns telemetry only for authenticated/allowlisted callers; session inventory/revoke lives at `/api/auth/sessions` (UI pending).
- Delivery plumbing: the local proxy now runs TLS with auto dev-cert rotation, enforces per-route rate limits, and fronts ingestion/search fan-out enqueued through Redis-backed RQ queues. Webhook + sync jobs have dedicated queues ready.
- Connector observability: `/health` now reports circuits, repeated failures, and last errors; the ingest/search UI surfaces connector badges when degraded.
- Ops: `/api/ops/queues` surfaces Redis/RQ health for authenticated users and feeds the web dashboard card; keep tightening guardrails around who can see it.
- Retention: external preview GC stays scheduled, and raw ingestion payloads are scrubbed after `INGESTION_PAYLOAD_RETENTION_DAYS` to keep data bounded.
- Hardening updates: ingested payloads are now size-capped at write time and redacted on expiry; IGDB tokens refresh ahead of expiry and clear cached secrets on 401s; proxy profiles tightened with admin-only diagnostics; credential vault + integrations queue are online so Spotify/Arr/Jellyfin work can land without backtracking.

### 7.2 Experience Fit & Finish (after 7.1)
- Menu editor improvements (implemented): inline note formatting, drag handles with keyboard moves, and autosave with conflict detection.
- Search workspace trust signals (implemented): “in collection” badges, surfaced dedupe reasons, and connector health callouts.
- Public menu page upgrades: OG-rich cards, embed mode, call-to-action for copying into Spotify/Jellyfin.
- Collaboration preview: draft share links now ship with temporary tokens before full multi-user editing.
- Library + Log hub (implemented): status tracking, timeline view, goals, quick log capture, and an auto-built "Next up" queue.
- Narrative menus: course intents + item annotations are now stored and editable; pairings across media types now ship in the menu payloads.
- Taste Profile: initial preference view powered by logs, tags, and menu signals.
- Availability awareness: provider/format/region entries now surface in UI summaries with refresh jobs marking stale data.
- Community exchange: fork/remix menus now track lineage and attribution notes.
TODO: draft RFCs for Library + Log, deeper narrative menus (story mode), taste profile refinements, availability providers, and community exchange governance.

### 7.3 Integration Burst (requires queue + credential vault from 7.1)
- Spotify linking screen + backend credential vault (per-user encrypted store and token rotation).
- Arr suite integration kit: sample docker-compose w/ webhook forwarding, event schemas, automation recipes backed by the worker queue.
- Jellyfin/Plex connectors with selective sync (e.g., only import “Favorites” libraries) and token-scoped background sync workers.
- Automation hooks: webhooks + scheduled rules (“When IGDB releases follow list, propose menu update”).

### 7.4 Ecosystem & Monetization Experiments (after moderation/abuse controls are defined)
- ActivityPub/RSS outbox for public menus (Mastodon/WriteFreely friendly).
- Shared “menu marketplaces” or featured lists curated with partners (labels, bookstores).
- Optional paid tier experiments around team workspaces or concierge ingestion quotas—documented but disabled until community feedback lands.

## 8. Open Problem Statements
- **Ranking heuristics:** Need ML-light approach (signals from Arr/Jellyfin usage, Spotify popularity, personal history) without storing sensitive listening data.
- **Connector credential UX:** Balance OAuth flows (Spotify) with headless token inputs (Jellyfin, Arr) while surfacing expiry/health states.
- **Offline/low-connectivity workflows:** Provide printable or offline-ready menu exports for classrooms/events.
- **Moderation:** For public menus, spam and IP management is an unsolved path; plan for trust & safety tooling before wide launch.
- **Availability sourcing:** Decide on data providers, region handling, and cache policies for availability overlays.
- **Taste profile privacy:** Define how preference insights are derived without exposing sensitive listening history.
- **Community exchange governance:** Define controls for forks, attribution disputes, and abuse reporting at scale.

## 9. Success Metrics & Telemetry
- **Curation success:** % of menus with ≥3 media types, average annotations per course, publish-to-view ratio.
- **Integration depth:** Count of connected services (Spotify, Arr, Jellyfin) per active curator, latency from external event to Tastebuds ingestion.
- **Reliability:** Ingestion pass rate, connector circuit-breaker uptime, session refresh failures, P95 search latency.
- **Delight:** Net satisfaction from feedback prompts on share pages, copy-to-clipboard/Spotify-export conversions.
- **Diet engagement:** Weekly active loggers, completion rate per status, and goal adherence.
- **Sharing velocity:** Forks/remixes per public menu and follow-through from shared menus to started items.

## 10. Next Planning Cadence
- Revisit this document monthly; track roadmap progress in issues tied to the sections above.
- Each connector/integration gets its own spec (RFC) capturing auth model, schemas, and UX entry points before build.
- Keep README high-level; route product decisions and unbuilt component rationale here for long-lived focus.
