# Deck Super-Admin Integration Plan

Date: 2026-06-20  
Owner path: `/home/phoenix/Documents/andrea-projects-workspace/my_portafolio/Deck`

## Current state audit (what already exists)

### 1) Super-admin access and role boundary
- Backend exposes `super_admin`-protected routes and role model already includes `super_admin`.
- `app/api/routes/admin_users.py` implements:
  - `GET /api/admin/users`
  - `GET /api/admin/users/analytics`
  - `POST /api/admin/users`
  - `PATCH /api/admin/users/{id}/role`
  - `POST /api/admin/users/bootstrap-role`
- `app/api/routes/admin_operations.py` implements:
  - overview, agents, telemetry, learning, provider-health, quotas, audit, deck processing, elements, etc.
- `app/api/routes/failure_tickets.py` already has:
  - `POST /api/admin/failure-tickets/report`
  - `GET /api/admin/failure-tickets`
  - `GET /api/admin/failure-tickets/{id}`
  - `PATCH /api/admin/failure-tickets/{id}`
- `app/main.py` currently applies global exception middleware and reports unhandled errors as `FAILURE_TICKET`s.

### 2) Super-admin UI already present in Deck frontend
- Deck has full admin route tree at:
  - `src/routes/(app)/admin`
  - `+layout.server.ts` gatekeeps access to `super_admin` role.
- Implemented sections:
  - Overview: `/admin`
  - Agents: `/admin/agents`, `/admin/agents/[runId]`
  - Learning: `/admin/learning`
  - Telemetry: `/admin/telemetry`
  - Elements: `/admin/elements`
  - Audit: `/admin/audit`
  - Quotas: `/admin/quotas`
  - Provider health: `/admin/provider-health`
  - Failure tickets: `/admin/failure-tickets`, `/admin/failure-tickets/[ticketId]`
  - Processing + slides detail: `/admin/processing/[deckId]`, `/admin/slides/[deckId]`
  - Agent teams: `/admin/agent-teams`
- API client for those surfaces is in:
  - `src/lib/server/adminApi.ts`
  - `src/lib/types/admin.ts`
- Error-safe user-facing behavior is already part of admin data model:
  - technical fields are redacted in list views
  - stack/context shown only where needed

### 3) Existing lightweight admin service (separate from SvelteKit app)
- `deck-admin/app/main.py` currently runs a minimal hard-coded admin console with:
  - backend sign-in
  - bootstrap role promotion (using `USER_ADMIN_BOOTSTRAP_TOKEN`)
  - endpoint inventory and dashboard metrics from backend.
- It links to Deck frontend admin pages via `ADMIN_FEATURE_TABS` and `ADMIN_APP_URL`.

### 4) AI Stack "super-admin" now a standalone repo
- Operational control-plane work is in:
  - `git@github.com:phoenixrisingcapera/superadmin-aistack.git`
- In this workspace we place that service under:
  - `/home/phoenix/Documents/andrea-projects-workspace/my_portafolio/Deck/super-admin/super-admin`
- Local repo root for control-plane: `super-admin/super-admin`
- Remote repo URL for deployments: `git@github.com:phoenixrisingcapera/superadmin-aistack.git`
- This repo is MailTrace-oriented and should remain a separate deployed service for now.
- Reusable components are still valuable as companion services:
  - Guardrail service: `superadmin-aistack/guardrails/backend/`
  - Feature audit/diags service: `superadmin-aistack/backend/`
  - Static diagnostic UIs: `superadmin-aistack/frontend/`

### Practical deployment split
- Deck admin API + `Deck`-native admin routes stay in this repo.
- Super-admin controls that are not deck-native stay in `superadmin-aistack` and are deployed as their own Railway service.

## Fastest path decision (recommended)

**Use split-repo deployment now:**

1. Keep deck-native operations in `Production-deck-aistack-codes/Frontend-clean` + backend admin APIs.
2. Deploy `superadmin-aistack` as a separate Railway service for:
   - `/guardrails/*` and policy/intent controls
   - operational diagnostic/read-only inspection UIs
3. Keep API boundaries explicit; do not import superadmin packages into Deck runtime.

Why this is fastest:
- Most critical surfaces already exist and are authenticated with `super_admin`.
- Most work now is governance/visibility, not re-architecture.
- Minimal blast radius: backend APIs already exist; frontend pages already mapped.

## Why split-repo now
This is now the preferred path, not an optional future step:
- keeps Deck auth/session semantics untouched
- gives each service independent deploy/release cycles
- allows super-admin tooling to be updated without touching deck core.

## Phased implementation plan

### Phase 1 — Operational super-admin (2–4 days)
- [x] Confirm role gate and backend route protection (`super_admin`) end-to-end.
- [x] Confirm all current `/admin/*` pages load for `super_admin` users.
- [x] Confirm failure ticket lifecycle already covers: report, list, detail, status update.
- [x] Add “Users & Access” page in Deck admin UI (if needed) using:
  - `GET /api/admin/users`
  - `PATCH /api/admin/users/{id}/role`
  - keep bootstrap in admin service for emergency use only.
- [x] Add security hardening to bootstrap path:
  - prevent second use in same admin service session after first success,
  - show explicit token-consumed status in dashboard,
  - keep `USER_ADMIN_BOOTSTRAP_TOKEN` usage read-only and short-lived operationally.

### Implementation notes (delivered)
- Deck admin users page added at:
  - `Production-deck-aistack-codes/Frontend-clean/src/routes/(app)/admin/users/+page.server.ts`
  - `Production-deck-aistack-codes/Frontend-clean/src/routes/(app)/admin/users/+page.svelte`
- Admin API support in:
  - `Production-deck-aistack-codes/Frontend-clean/src/lib/types/admin.ts`
  - `Production-deck-aistack-codes/Frontend-clean/src/lib/server/adminApi.ts`
- Sidebar admin access now includes quick links to:
  - `/admin/failure-tickets`
  - `/admin/users`
  - `Production-deck-aistack-codes/Frontend-clean/src/lib/components/Sidebar.svelte`
- Bootstrap hardening implemented in:
  - `deck-admin/app/main.py`

### Phase 2 — Guardrails integration (1–2 weeks)
- [x] Stand up `superadmin-aistack/guardrails/backend` service contract on Deck:
  - `/api/v1/guardrails/health`
  - `/api/v1/guardrails/evaluate`
  - `/api/v1/guardrails/audits`
  - `/api/v1/guardrails/policy-registry`
  - `/api/v1/guardrails/operator/summary`
- [x] Add Deck backend interception point before LLM/pipeline execution:
  - call guardrail service with request/intent/evidence.
  - block/allow according to policy.
- [x] Add admin read-only panel in Deck `/admin` for guardrail health + summaries + audit tail.
- [x] Persist guardrail audit decisions in DB or durable store (not ephemeral file-only).
- [ ] Deploy `super-admin/super-admin/guardrails/backend` to Railway and wire `SUPERADMIN_GUARDRAILS_*` envs in production.

### Phase 3 — Consolidation and staging control (2–3 weeks)
- [x] Add super-admin “safety and controls” panel in `/admin`:
  - incident backlog from failure tickets,
  - guardrail risk hot spots,
  - exception trends by route/api/deck,
  - audit + approval history.
- [ ] Add route-level controls for “investigation actions”:
  - mark/deprioritize provider keys,
  - suspend risky deck source actions,
  - annotate incidents with operator notes.
- [ ] Add deployment-time checks:
  - env validation for guardrail keys,
  - admin pages smoke checks (authenticated),
  - alerting on repeated ticket spikes and blocked guardrail events.

### Phased close-out (current status)
- Phase 1: ✅ Complete
- Phase 2: ⚙️  Core in code, final Railway deploy/config still required
- Phase 3: ⚠️ Partial (safety panel/live metrics done; action controls and ops checks still pending)

### Phase 4 — Optional full AI-stack super-admin extension (if required)
- [ ] Bring in selected read-only AI-stack diagnostic modules from `superadmin-aistack/backend`:
  - feature audit endpoints (`frontend-api`/`backend-routes` inventories),
  - diagnostics views.
- [ ] Keep as separate service (recommended) and integrate only via read APIs into Deck admin.
- [ ] Avoid full `superadmin-aistack` UI merge unless long-term governance platform is required.

## Feature matrix: Deck-native vs AI-Stack

### Keep in Deck-first stack (recommended default)
- super-admin authentication, role management, and user updates
- deck/agent telemetry, telemetry failures, regression promotion
- failure ticket reporting + triage states
- quotas/provider health/audit
- deck processing + slide inspection

### Add from AI Stack (as companion service)
- guardrail decision + policy registry + operator summaries
- route/API/feature inventory scans for architectural drift
- static diagnostic pages for non-production operations visibility

### Avoid importing directly as-is
- MailTrace-specific diagnostics
- product-specific connectors and mailbox workflow introspection not relevant to Deck’s domain

## Acceptance checklist to close each phase

- [x] Super-admin users can triage incidents and assign statuses (`new`, `acknowledged`, `investigating`, `fixed`, `ignored`) in Deck.
- [x] Normal users still never see internal stack traces.
- [x] Guardrail service contract includes:
  - [x] health endpoint
  - [x] policy read endpoint
  - [x] operator summary endpoint
  - [x] audit endpoint
- [x] Admin can navigate from `/admin` to operational controls without leaving the Deck domain.
- [x] Standalone services are deployment-isolated and do not block Deck user journeys.
