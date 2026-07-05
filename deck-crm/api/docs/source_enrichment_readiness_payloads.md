# Source enrichment readiness payloads

## Purpose

PR #29 persists validated LLM source labels into existing DB fields. This follow-up exposes those labels in the payloads consumed by Smart Deck and processing/status UI.

## Exposed in `get_deck_structure()`

Top-level:

- `sourceWorkspace`
- `sourceEnrichment`

Extraction run:

- `sourceWorkspace`
- `sourceEnrichment`
- `metricsJson`

Slides:

- `semanticSlideType`
- `summary`
- `textHash`
- `sourceVersion`
- `enrichmentSource`

Blocks:

- `text`
- `blockKind`
- `semanticRole`
- `contentHash`
- `extractionStage`
- `extractionSource`
- `sourceVersion`
- `enrichmentSource`
- `semanticConfidence`

## Exposed in processing status

Processing payloads now include:

- `sourceWorkspace`
- `sourceEnrichment`
- `enrichmentSource`
- `llmStatus`

This lets the frontend distinguish:

- deterministic source labels
- LLM-enriched source labels
- disabled enrichment
- missing provider
- invalid LLM output
- LLM failure fallback

## Safety boundary

The LLM still does not write directly to the database. It produces JSON only. Backend services validate and persist labels, then expose the persisted state to downstream payloads.
