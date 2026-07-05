# Brand loader source-aware palette

Date: 2026-06-25

## Goal

Make the brand loader reliable as the first intelligent view in Deck AIStack.

The user may provide any combination of:

```text
deck file
company URL
logo
brand guide
```

The app must produce visible colour swatches and clearly explain where those colours came from.

## Current fix in this PR

### 1. Intake-created swatches

`app/services/brand_loader_service.py` now creates safe default swatches during intake when a brand profile has context but no colours yet.

This prevents a brand context from looking empty before full extraction runs.

The profile now records:

```text
primary_color
secondary_color
accent_color
background_color
text_color
palette_json
source_mode=context_seed
raw_evidence_json.paletteSource
raw_evidence_json.fallbackReason
warnings_json
```

### 2. Idempotent brand-first creation

`app/services/first_batch_rescue_service.py` now reuses an existing brand-first deck for the same workspace, user, source type, and URL instead of creating a new pseudo-deck every click.

This stops the `/decks/new` page from accumulating many duplicate URL-branding decks.

### 3. Source-context distinction

Brand-first decks now explicitly report:

```json
{
  "hasSourceFile": false,
  "reused": true
}
```

This allows the frontend to avoid presenting URL-only brand context as a normal uploaded source deck.

## Intended extraction priority

The production order should be:

```text
1. Logo-derived palette
2. Live URL assets / CSS / theme colours
3. Deck visual palette from thumbnails / slide previews
4. Brand guide palette
5. Context/default fallback palette
```

This PR improves the fallback and state behaviour. Follow-up work should add true deck visual sampling from slide thumbnails and brand-guide documents.

## Backend files touched

```text
app/services/brand_loader_service.py
app/services/first_batch_rescue_service.py
docs/brand-loader-source-aware-palette.md
```

## Acceptance criteria

```text
URL-only first batch produces visible swatches.
Repeated URL first-batch does not create duplicate decks for the same URL.
Fallback swatches are marked as fallback/context defaults.
Backend persists palette provenance in raw_evidence_json.
Backend response distinguishes source-context decks from source-file uploads.
```

## Follow-up

```text
Add SVG logo whitelist consistently with frontend.
Add deck visual palette extraction from slide thumbnails.
Add tests for URL idempotency and fallback swatch persistence.
```
