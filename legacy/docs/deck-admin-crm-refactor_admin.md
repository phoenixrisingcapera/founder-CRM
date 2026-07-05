# Deck Admin Failure Tickets Refactor Plan

Date: 2026-06-21  
Scope: `/home/phoenix/Documents/andrea-projects-workspace/my_portafolio/Deck/deck-admin`

## Goal

Copy the failure-ticket admin surfaces into `deck-admin` so the feature can be verified in the standalone admin console without changing the main Svelte frontend.

## Boundary

- Do not modify `Production-deck-aistack-codes/Frontend-clean`.
- Reuse the existing backend API:
  - `GET /api/admin/failure-tickets`
  - `GET /api/admin/failure-tickets/{id}`
  - `PATCH /api/admin/failure-tickets/{id}`
- Keep the current dashboard and login flow working.
- Add the new failure-ticket pages as local `deck-admin` routes.

## Phases

### Phase 1 - Inventory and route mapping
- Confirm the backend ticket payload shape.
- Confirm the admin console already authenticates against the backend.
- Map the local console pages that should receive the new tab link.
- Keep the current dashboard feed intact.

### Phase 2 - Local page copy
- Add `/admin/failure-tickets` to `deck-admin`.
- Add `/admin/failure-tickets/{ticket_id}` to `deck-admin`.
- Copy the list/table presentation from the existing admin UI into the console style.
- Copy the detail view, including:
  - status
  - severity
  - source
  - route/page URL
  - stack trace in an expandable section
  - admin notes and status update form

### Phase 3 - Persistence and wiring
- Store the backend bearer token in the admin console session after backend sign-in.
- Reuse that token for the new failure-ticket pages.
- Add a visible console tab so the page is discoverable.
- Keep redirects and error handling local to the admin console.

### Phase 4 - Verification
- Open `/admin/failure-tickets` from the deck-admin console.
- Verify list filters work.
- Verify a ticket detail page loads.
- Verify status updates persist to the backend.
- Confirm the main Svelte frontend still serves the original admin routes unchanged.
- Run `scripts/smoke_failure_tickets.py` with `DECK_API_URL` and `DECK_ADMIN_BEARER_TOKEN` set.

## Acceptance Criteria

- The failure-ticket page is visible in `deck-admin`.
- The ticket detail page is visible in `deck-admin`.
- Status changes can be saved back to the backend.
- The existing Deck frontend does not need to be edited for this verification path.
- The current console dashboard and login flow continue to work.
