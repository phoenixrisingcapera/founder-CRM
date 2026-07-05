# Deck Admin Console

Reference-only surface for Founder CRM migration work.

This is not the canonical Founder CRM product. It is older operational/admin source material that may still inform:
- ops console framing
- backend health visibility
- endpoint inventory
- admin navigation ideas

New Founder CRM product work should land in `../web` and `../api`.

Railway-hosted admin UI for watching the production backend visually during user testing.

This service does not connect directly to Postgres from the browser. It calls the production backend:

- `POST /api/auth/sign-in`
- `GET /api/health`
- `GET /openapi.json`
- `GET /api/admin/users`
- `GET /api/admin/users/analytics`
- `PATCH /api/admin/users/{user_id}/role`
- `POST /api/admin/users/bootstrap-role`
- `GET /api/decks`

## What The Console Shows

- backend health
- endpoint and API inventory from OpenAPI
- total users, workspaces, decks, auth sessions, AI-provider configurations, and audit events
- user role distribution
- deck status distribution
- API/action result counts
- top backend actions
- recent user testing activity from `security_audit_events`
- recent decks
- signed-up users with role assignment controls

## Railway Service

Create a new Railway service from this folder:

```txt
Production/admin
```

Required variables:

```env
ADMIN_CONSOLE_PASSWORD="long-private-console-password"
ADMIN_CONSOLE_SECRET="long-random-cookie-signing-secret"
DECK_API_URL="https://api.deck.aistack.codes"
SUPERADMIN_AISTACK_URL="https://superadmin.aistack.codes"  # optional external control-room UI
```

Temporary first-admin variable:

```env
USER_ADMIN_BOOTSTRAP_TOKEN="same-temporary-token-set-on-dddecks-backend"
```

Use `USER_ADMIN_BOOTSTRAP_TOKEN` only to promote your first signed-up account to `super_admin`, then rotate or remove it from both this admin service and the backend.

## Super-admin service (separate repo)

For full operational controls, deploy a dedicated service from:

```txt
git@github.com:phoenixrisingcapera/superadmin-aistack.git
```

Set `SUPERADMIN_AISTACK_URL` on this service to the deployed URL. A "Super Admin Service" tab will then show in the feature section and open that app in a new tab.

Keep this service read/write on operations that must run outside Deck runtime; Deck admin routes (`/admin/*`) remain production-safe and contain operational views for normal ticketing/incident workflows.

Expected local repository layout for the super-admin control plane in this workspace:

`/home/phoenix/Documents/andrea-projects-workspace/my_portafolio/Deck/super-admin/super-admin`

Current quick-link tabs in this console:

- Overview
- Users
- Agents
- Agent Teams
- Telemetry
- Learning
- Failure Tickets
- Safety Controls
- Audit
- Provider Health
- Quotas
- Super Admin Service, when `SUPERADMIN_AISTACK_URL` is set

## Workflow

1. User signs up on `https://deck.aistack.codes/auth/sign-up`.
2. User is stored in Railway Postgres as `general`.
3. Open this admin console.
4. Unlock the console with `ADMIN_CONSOLE_PASSWORD`.
5. For the first admin, use the bootstrap form.
6. Sign in as a backend `super_admin`.
7. Review users, decks, API activity, and endpoint inventory.
8. Assign roles as needed.

Users need to sign out and sign back in after their role changes so their session token contains the new role.
