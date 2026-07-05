# Decision 0001: Canonical Founder CRM Direction

## Status

Accepted

## Decision

`apps/crm/web` and `apps/crm/api` are the canonical AiStack product surfaces.

`apps/crm/deck-crm` and `apps/crm/deck-admin-crm` are source-material surfaces, not the active product.

## Why

- The filled Founder CRM Grill plus subsequent product memory define a product that is relationship-mapping-first and workflow-intelligence-first, not deck-first.
- The new `web/` and `api/` apps already express the correct product ownership boundaries.
- The older `deck-*` surfaces contain useful infrastructure but are structurally and semantically tied to DDDecks.

## Consequences

- New feature work should land in `web/` and `api/`.
- Old `deck-*` paths should only be mined intentionally.
- When old code is copied forward, it must be renamed into AiStack venture workflow language and contracts.
