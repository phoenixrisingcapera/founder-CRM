# DeckAiStack failure-ticket system status

Completed on 2026-06-20.

## Backend

- [x] Added `failure_tickets` SQLAlchemy model.
- [x] Added Alembic migration `0035_failure_tickets.py`.
- [x] Added `FailureTicketService` for report creation, listing, detail, and admin status updates.
- [x] Added `POST /api/admin/failure-tickets/report` for frontend and server-side reporting.
- [x] Added admin-only `GET /api/admin/failure-tickets`.
- [x] Added admin-only `GET /api/admin/failure-tickets/{id}`.
- [x] Added admin-only `PATCH /api/admin/failure-tickets/{id}`.
- [x] Added global backend exception recording for unhandled 500 errors.
- [x] Stores route, page URL, API path, status code, user id/email, deck id, error name/message/stack, context JSON, severity, source, status, request id, and admin notes.

## Frontend

- [x] Added central browser error reporting helper.
- [x] Added browser `apiFetch` wrapper that reports failed API calls.
- [x] Added SvelteKit server report proxy at `/api/admin/failure-tickets/report`.
- [x] Updated backend API proxy handling to report failed backend calls.
- [x] Added `handleError` reporting for SvelteKit loader/page failures.
- [x] Added root `+error.svelte` with friendly copy, safe reporting, and safe redirect.
- [x] Added admin route `/admin/failure-tickets` with table, filters, status badges, and detail action.
- [x] Added ticket detail page with expandable technical context and admin notes.
- [x] Normal users see friendly fallback copy and no stack traces.
- [x] Backend jargon is kept to admin pages.

## Acceptance criteria

- [x] If `/smart-deck` fails, the user is moved to a stable page and a ticket is reported through the error page/server error path.
- [x] If an API request returns 500, the backend proxy reports a ticket for admin review.
- [x] If the backend raises an unhandled exception, middleware records a ticket.
- [x] Admin can mark tickets acknowledged, investigating, fixed, or ignored.
- [x] Normal users never see raw internal errors.

## Verification

- [x] Backend compile check: `python3 -m compileall app`.
- [x] Frontend check: `npm run check`.

## Brand URL loader audit status

- [x] Frontend URL-brand entry flow exists (`/welcome -> /decks/new?firstBatch=url_branding`).
- [x] Backend first-batch URL flow exists (`source_type=url_branding`, `website_url` persistence).
- [x] URL is passed to `POST /brand/extract` and `DeckBrandProfile` stores color fields.
- [x] URL colors are sampled from live website content/assets:
  - HTML parsing extracts theme colors, style blocks, `og/twitter` images and icons.
  - Assets/favicons are raster/SVG sampled when available.
  - CSS files are parsed for color candidates.
- [x] URL extraction evidence is persisted in `raw_evidence_json` (`paletteEvidence`, `paletteSource`, sample URLs, color counts).
- [ ] Persisted evidence/UX still does not explicitly surface live vs seeded source in the brand picker UI (copy remains generic today).
