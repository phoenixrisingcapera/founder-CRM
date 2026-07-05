# Decision 0002: Admin Observability And Visibility Extraction

## Status

Accepted

## Decision

Admin telemetry, failure visibility, provider health, quota visibility, and audit ideas are worth extracting from `deck-crm`, but the old admin IA should not be adopted wholesale.

## Keep As Patterns

- failure ticket reporting
- server-side error capture hooks
- admin telemetry event models
- provider health surfaces
- quota and run visibility
- audit and learning-memory concepts

## Do Not Keep As Product Shape

- DDDecks route tree
- deck-only admin vocabulary
- duplicated component/layout systems
- old auth and path aliases

## Implementation Direction

- founder-facing founder CRM stays clean and minimal
- operator/admin visibility becomes a separate CRM admin surface later
- extracted observability contracts should be normalized around:
  - workspace
  - user
  - investor
  - pipeline deal
  - deck generation run
  - artifact
