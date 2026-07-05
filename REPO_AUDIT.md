# CRM Repo Audit

## Active Product

- `apps/crm/web`
- `apps/crm/api`

## Current Product Memory

The active product direction is:
- AiStack
- founder relationship mapping
- venture workflow intelligence
- controlled backend integration

The app should move toward these canonical surfaces:
- Projects
- Dispatches
- People
- Companies
- Opportunities
- Relationship Graph
- Goal-Based Fit Scoring
- Deck Assistant

## Reference Surfaces Worth Mining

### `apps/crm/deck-crm`

Best reusable areas:
- admin telemetry contracts
- failure ticket reporting
- upload validation and workflow proxy patterns
- provider health and quota visibility
- deck upload and artifact workflow concepts

### `apps/crm/deck-admin-crm`

Best reusable areas:
- operator-console framing
- backend health and endpoint inventory ideas
- temporary audit/ops visibility concepts

## Legacy / Non-Canonical

- DDDecks-specific route structure
- old admin planning docs
- unrelated QA baggage
- duplicate layout/component systems
- duplicated token/theme namespaces
- old auth aliases and typo routes

## Refactor Target

### Keep active
- `web/`
- `api/`

### Keep as reference only
- `deck-crm/`
- `deck-admin-crm/`

### Legacy archive material
- moved docs under `legacy/docs/`

## Next Extraction Priorities

1. Failure ticket reporting into Founder CRM backend and web shell
2. Admin telemetry schema normalization for CRM runs and artifacts
3. Provider health and quota visibility for Founder CRM settings/admin
4. PPTX handling parity in active `api/` deck upload flow
