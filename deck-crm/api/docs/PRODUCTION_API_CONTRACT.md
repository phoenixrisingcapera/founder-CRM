# Production API Contract

## Runtime surface

- Frontend origin: `https://deck.aistack.codes`
- Backend origin: `https://api.deck.aistack.codes`
- API prefix: `/api`

## Canonical production endpoints

### Health
- `GET /api/health`
- `GET /api/health/storage`

### Auth
- `POST /api/auth/sign-in`
- `POST /api/auth/sign-up` (compat alias kept as optional compatibility)
- `GET  /api/auth/me`

### Workspace summary
- `GET /api/products/deck-aistack-codes/welcome-state`
- `GET /api/products/deck-aistack-codes/workspace-summary`
- `GET /api/products/deck-aistack-codes/decks`

### Workspace AI provider
- `GET    /api/settings/workspace/ai-provider`
- `POST   /api/settings/workspace/ai-provider`
- `DELETE /api/settings/workspace/ai-provider`

### Deck loading
- `GET  /api/products/deck-aistack-codes/decks/{deck_id}/status`
- `GET  /api/products/deck-aistack-codes/decks/{deck_id}/structure`
- `GET  /api/products/deck-aistack-codes/decks/{deck_id}/editable-fields`
- `GET  /api/products/deck-aistack-codes/decks/{deck_id}/fields/{field_key:path}`
- `POST /api/products/deck-aistack-codes/decks/{deck_id}/changes/preview`
- `POST /api/products/deck-aistack-codes/decks/{deck_id}/changes/apply`
- `GET  /api/products/deck-aistack-codes/decks/{deck_id}/smart-deck`
- `POST /api/products/deck-aistack-codes/decks/{deck_id}/smart-deck/generation-jobs`
- `GET  /api/products/deck-aistack-codes/decks/{deck_id}/smart-deck/generation-jobs/{job_id}`

### Exports
- `GET  /api/products/deck-aistack-codes/decks/{deck_id}/exports`
- `POST /api/products/deck-aistack-codes/decks/{deck_id}/export`

### Non-goal
- No production logic should depend on frontend rewrite/proxy/canonical wrappers.
- No `/api/v1` route paths are part of this product runtime contract.
