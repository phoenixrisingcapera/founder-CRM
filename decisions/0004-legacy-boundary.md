# Decision 0004: Legacy Boundary

## Status

Accepted

## Decision

Any source material that is:
- DDDecks-specific,
- duplicated,
- planning-only,
- typo-ridden or abandoned,
- unrelated guardrails QA baggage,
- or structurally incompatible with the Founder CRM direction,

belongs under `legacy/` conceptually and should not be treated as active product code.

## Immediate Legacy Examples

- old admin planning docs from `deck-admin-crm`
- `deck-crm/fornten.md`
- old route aliases tied to DDDecks semantics
- QA folders unrelated to the founder CRM product runtime

## Rule

Legacy material may inform migration work, but must not block simplification.
