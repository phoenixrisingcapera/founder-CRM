# Frontend Worker Boundary

This document translates the problematic frontend responsibilities from `/docs/jun26/problematic_front_end.md` into backend-owned workflow jobs.

The goal is that frontend pages only call:

- `GET /api/products/deck-aistack-codes/decks/{deck_id}/workflow-state`
- `POST /api/products/deck-aistack-codes/decks/{deck_id}/workflow-command`

The frontend should render state, show retry/manual-review actions, and open Smart Deck only when the backend says it is ready. It should not call low-level extraction, start, brand, miniature, or polling endpoints directly.

## Workers Created In This Branch

Dedicated worker entrypoints now exist under `app/workers/`:

- `source_extraction_worker.py`
- `miniatures_worker.py`
- `brand_extraction_worker.py`
- `smart_deck_context_worker.py`
- `db_publisher_worker.py`
- `llm_generation_worker.py`
- `schema_validation_worker.py`
- `preview_render_worker.py`
- `apply_version_worker.py`
- `export_worker.py`

Each entrypoint sets one `DECK_WORKER_JOB_TYPES` value and then runs the shared durable queue loop from `deck_queue_worker.py`.

### 1. source_ingestion

Status: created as a completed workflow job during upload.

Owner: `app/services/upload_service.py`

Purpose:

- Records that the source file is saved and belongs to a deck.
- Stores source file metadata, checksum, MIME type, size, and storage key.
- Records a `deck_source_file` workflow artifact.
- Gives workflow-state a durable upload/source baseline before any extraction worker runs.

Frontend responsibility removed:

- The frontend no longer needs to infer whether a file is saved from deck-list refreshes or multiple status payloads.

### 2. source_extraction

Status: created and executable.

Owner:

- Queue creation: `app/services/deck_processing_queue_service.py`
- Worker execution: `app/services/deck_processing_worker_service.py`
- Workflow state: `app/services/deck_workflow_service.py`

Purpose:

- Runs persisted deck structure extraction through `extract_and_persist_deck_structure`.
- Persists slides, blocks, assets, source enrichment details, and extraction metrics.
- Updates the linked `DeckExtractionRun` metadata with stage, worker id, heartbeat, counts, and next action.
- Emits workflow output including slide count, block count, asset count, source workspace, source enrichment, and structure status.

Frontend responsibility removed:

- The frontend should stop calling `POST /extract-structure`.
- The frontend should stop polling `/status` just to decide whether extraction is ready.
- Readiness is exposed through `workflow-state.source.extractionReady`, `workflow-state.source.slideCount`, and job phases.

### 3. miniatures

Status: created and executable.

Owner: `app/services/deck_processing_worker_service.py`

Purpose:

- Runs `extract_source_previews` after source extraction completes.
- Persists thumbnail/preview readiness as workflow job output.
- Updates the extraction run stage from `preview_generation_running` to `preview_generation_completed`.
- Feeds `workflow-state.source.thumbnailCount`.

Frontend responsibility removed:

- Upload save no longer generates miniatures inline.
- The frontend should not decide miniature readiness by repeatedly refreshing deck lists.
- The frontend should render thumbnail readiness from workflow-state only.

### 4. brand_extraction

Status: created and executable.

Owner: `app/services/deck_processing_worker_service.py`

Purpose:

- Creates or reuses the workspace `CompanyProfile`.
- Reads deck input sources and brand assets.
- Runs `upsert_brand_profile`.
- Runs `enrich_brand_profile_after_extract`.
- Persists profile id, processing status, palette, and logo URL into job output.

Frontend responsibility removed:

- The frontend should stop treating brand extraction as a UI-triggered job.
- The frontend should stop calling `POST /brand/extract` as part of the intake process.
- The frontend can still read/update a brand profile for review, but extraction state must come from workflow-state and brand profile provenance.

### 5. smart_deck_context

Status: created and executable.

Owner: `app/services/deck_processing_worker_service.py`

Purpose:

- Runs `prepare_smart_deck_source_workspace`.
- Persists Smart Deck source workspace readiness.
- Captures source run id, workspace id, slide count, artifact count, enrichment source, LLM status, provider, and model.

Frontend responsibility removed:

- The frontend should stop guessing whether Smart Deck can open from local status normalization.
- Smart Deck opens only when workflow-state says `nextAction=open_smart_deck` and `canOpenSmartDeck=true`.

### 6. db_publisher

Status: created and executable.

Owner: `app/services/deck_processing_worker_service.py`

Purpose:

- Publishes terminal workflow phases after upstream jobs complete.
- Marks source pipeline completion as `smart_deck_ready`.
- Transitions the deck state to `ready`.
- Updates the processing run to completed with `nextAction=open_smart_deck`.

Frontend responsibility removed:

- The frontend should stop independently deciding final readiness from slide counts, generated slides, or inferred worker state.

### 7. llm_generation

Status: created and executable.

Owner:

- Queue creation: `app/services/deck_workflow_service.py`
- Worker execution: `app/services/deck_processing_worker_service.py`

Purpose:

- Runs Smart Deck generation through `create_generation_job`.
- Stores the generation job result, design version id, generated slide count, and workspace id.
- Chains to `db_publisher` with `publishTarget=preview_ready`.

Frontend responsibility removed:

- The frontend should send one `workflow-command` with `command=generate_preview`.
- The frontend should not manage generation polling separately from workflow-state.

### 8. apply_version

Status: created and executable.

Owner:

- Queue creation: `app/services/deck_workflow_service.py`
- Worker execution: `app/services/deck_processing_worker_service.py`

Purpose:

- Applies a selected design version through `apply_design_version`.
- Chains to `db_publisher` with `publishTarget=applied`.

Frontend responsibility removed:

- The frontend should not assemble apply state from design-version, generated-slide, and Smart Deck workspace calls.

### 9. workflow-state

Status: created.

Owner:

- Route: `app/api/routes/deck_workflow.py`
- Schema: `app/schemas/deck_workflow.py`
- State assembly: `app/services/deck_workflow_service.py`

Purpose:

- Provides one canonical deck workflow object.
- Exposes active job, latest jobs, source readiness, Smart Deck readiness, provider readiness, links, retry state, and blocking reason.

Frontend responsibility removed:

- The frontend should stop reading `/processing`, `/status`, `/structure`, `/artifacts`, and brand endpoints to assemble one page state.

### 10. workflow-command

Status: created in this branch.

Owner:

- Route: `app/api/routes/deck_workflow.py`
- Schema: `app/schemas/deck_workflow.py`

Supported commands:

- `start_source_extraction`
- `start_source_processing`
- `create_smart_deck`
- `retry`
- `generate_preview`
- `apply_design_version`

Purpose:

- Gives the frontend a single mutation endpoint.
- Queues the correct workflow job.
- Starts background execution when the command accepts a queued job.
- Keeps detailed legacy workflow routes available for compatibility.

Frontend responsibility removed:

- The frontend should stop calling `POST /extract-structure`, `POST /smart-deck/start`, and `POST /retry` directly.
- The canonical frontend command is now `POST /workflows/source-extraction`; the
  older start/retry routes remain compatibility aliases only.

## Workers Still Needed

### 1. schema_validation

Status: worker implemented.

Current behavior:

- Validates that generated slides exist and carry persisted
  `render_schema_json` before downstream preview publication.
- Persists failure through the workflow-job lifecycle when validation cannot
  complete.

Needed:

- Broaden validation depth if stricter schema/runtime guarantees are needed.
- Keep validation failures workflow-job-native.

### 2. preview_render

Status: worker implemented.

Current behavior:

- Persists preview-stage completion from the generated design version.
- Records a concrete `design_version_manifest` workflow artifact for the job.

Needed:

- If visual raster previews become mandatory, add concrete rendered-image
  artifacts in this stage rather than republishing from another service.
- Keep preview artifact visibility workflow-job-native.

### 3. export

Status: worker implemented.

Current behavior:

- Calls the export service through the workflow stage.
- Persists a concrete `deck_export` workflow artifact with the resulting
  export id and download URL.

Needed:

- Harden artifact hashing/storage metadata further if stricter provenance is
  required.
- Keep export publication owned by `db_publisher`.

### 4. brand provenance hardening

Status: partial.

Current behavior:

- Brand extraction runs in the worker.
- Job output includes profile id, processing status, palette, and logo URL.

Needed:

- Add explicit `paletteSource`, `sourceQuality`, and `isFallbackPalette`.
- Make fallback palettes visually and contractually distinct from real extracted brand signals.
- Ensure frontend brand components render provenance from backend fields only.

### 5. root workflow-command adoption by frontend

Status: backend route created, frontend refactor still needed.

Needed:

- Refactor `/decks/new` to read only workflow-state after upload.
- Refactor `/decks/{deck_id}/processing` to read only workflow-state.
- Remove frontend helper exports for low-level extraction/start/status calls.
- Make deck-list refresh independent from workflow polling.

## Operational Notes

- `DECK_WORKER_JOB_TYPES` can restrict a worker process to specific job types.
- Empty `DECK_WORKER_JOB_TYPES` means the worker can claim all workflow job types.
- Stale workflow jobs are recovered through `recover_stale_workflow_jobs`.
- Running jobs time out to `timed_out` after max attempts and stale heartbeat.
- Dependency failures block downstream jobs and surface `needs_manual_review`.

## Verification

Run:

```bash
.venv/bin/python -m pytest tests/test_workflow_frontend_worker_boundary.py tests/test_durable_worker_contract.py -q
```
