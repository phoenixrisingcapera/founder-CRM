# Legacy Status

## Archived Already

- old deck admin planning docs moved into `legacy/docs/`
- typo route/planning note `deck-crm/fornten.md` moved into `legacy/docs/`

## Reference-Only Code Surfaces Still Outside `legacy/`

### `deck-crm/`

Keep outside `legacy/` for now because it still contains extractable runtime value:
- telemetry contracts
- failure reporting patterns
- provider health and quota views
- upload and generation workflow proxy logic

### `deck-admin-crm/`

Keep outside `legacy/` for now because it still contains extractable ops-console patterns.

## Explicitly Non-Canonical Subtrees

These should be treated as legacy even if they remain physically in place for reference:

- `deck-admin-crm/qa/`
- old DDDecks auth aliases and DDDecks route variants inside `deck-crm/`
- duplicate layouts/components/themes inside `deck-crm/`

## Future Archive Candidates

1. `deck-admin-crm/qa/`
2. DDDecks-only route aliases in `deck-crm/src/routes/`
3. duplicate component and theme systems in `deck-crm/src/lib/`
