# AiStack Founder CRM

This folder is the canonical local workspace for the founder-facing venture workflow product.

## Canonical Product Direction

AiStack is:
- a founder relationship mapping and venture workflow CRM
- a relationship graph and workflow intelligence product first
- a fundraising and venture execution operating system second
- a founder deck preparation product as a connected module
- a single-workspace, single-founder MVP

It is not:
- a DDDecks clone
- a generic CRM
- a collaborative presentation editor
- a Canva replacement

## Canonical Active Surfaces

- `web/`: active founder-facing frontend
- `api/`: active founder-facing backend
- `decisions/`: architectural decisions for the founder CRM direction
- `legacy/`: archived planning material and explicitly non-canonical source material

## Source Material Surfaces

These are not the canonical product, but they contain useful implementation material to mine deliberately:

- `deck-crm/`
  - best source for telemetry, admin visibility, failure tickets, and deck workflow proxy ideas
- `deck-admin-crm/`
  - best source for temporary operator-console concepts

These should be treated as reference repos inside the workspace, not as the active Founder CRM product.

## High-Value Reuse Targets

- telemetry and failure visibility patterns
- admin and audit concepts
- deck upload validation
- artifact and generation workflow concepts
- provider health and quota visibility

## Do Not Reintroduce

- DDDecks naming and route assumptions
- VC deck app IA as the core product
- duplicate auth paths
- duplicate layout systems
- generic super-admin baggage in founder-facing flows

## Product Truth

The Founder CRM Grill in `FOUNDER_CRM_GRILL.md` is the product source of truth for intent.

The active working memory for the corrected product direction is in `PRODUCT_MEMORY.md`.

## Deployment

Railway deployment notes live in `RAILWAY_DEPLOY.md`.
