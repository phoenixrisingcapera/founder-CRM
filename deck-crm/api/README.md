# Deck AI Stack Backend

FastAPI backend for the Deck AI Stack production service behind `deck.aistack.codes`.

## Runtime

- App entrypoint: `app.main:app`
- Local command: `uvicorn app.main:app --reload --port 8080`
- Railway start command: `python scripts/start_railway.py`
- Railway API role: default `APP_ROLE=api`
- Railway worker role: set `APP_ROLE=worker` on a separate service using the same Docker image/repo
- Railway pre-deploy command: `python scripts/railway_predeploy_noop.py`
- Runtime schema bootstrap: `scripts/start_railway.py` runs migrations/bootstrap for the API service
- Health checks: `/health` and `/api/health`

## Spark runtime

- Dedicated PySpark image: `Dockerfile.pyspark`
- Build command: `docker build -f Dockerfile.pyspark -t deck-backend-pyspark .`
- Default worker command: `docker run --rm deck-backend-pyspark`
- Interactive Spark shell override: `docker run --rm -it deck-backend-pyspark python -m pyspark.shell`
- This image includes `pyspark`, `pandas`, `pyarrow`, and Java 17 so it can run Spark-based LLM parallelization jobs without bloating the main API image.

## Repository Layout

- `app/api/routes/` - FastAPI route modules
- `app/services/` - product and workflow service logic
- `app/db/models/` - SQLAlchemy models
- `app/schemas/` - Pydantic request and response schemas
- `alembic/versions/` - database migrations
- `scripts/` - database backup, restore, startup, and worker helpers

## Workflow orchestration rule

Deck source processing and Smart Deck generation are moving to an orchestrated
pipeline. Treat this as the default backend architecture for new work.

- API routes should accept commands, validate input, create or enqueue durable
  job state, and return quickly.
- Heavy work should run in focused workers with one objective per worker.
- Final deck readiness and publication state should be advanced by an
  orchestrator or publisher stage, not by scattered route helpers.
- Source and generation data should be persisted as durable pipeline state, not
  inferred from mixed frontend polling heuristics.

Current durable pipeline job types now tracked in the database:

- `source_ingestion`
- `source_extraction`
- `miniatures`
- `brand_extraction`
- `smart_deck_context`
- `db_publisher`
- `llm_parallelization`

Current implementation note:

- The codebase now persists durable `workflow_jobs`, `workflow_job_events`,
  `workflow_job_artifacts`, and `workflow_job_dependencies`.
- Worker claims and stale-job recovery now operate on `workflow_jobs`.
- Worker execution can be limited to specific job types with
  `DECK_WORKER_JOB_TYPES`.
- Compatibility payload fields such as `processing_status_url` should now point
  callers back to canonical `workflow-state`, even when the field name remains
  for backward compatibility.
- Source extraction and Smart Deck context builders support publisher-safe mode
  so they do not publish final deck readiness by themselves when executed from
  workflow workers.
- Source preview extraction now also supports publisher-safe mode, so the
  `miniatures` worker does not mark the deck ready by itself.
- Publisher-safe mode is now the default for source extraction, preview
  extraction, and Smart Deck source-workspace preparation. Callers must opt in
  explicitly if they really intend to publish deck readiness outside the
  workflow publisher path.
- `db_publisher` is responsible for publishing final workflow phases such as
  `smart_deck_ready`, `preview_ready`, and `applied`.
- Non-pipeline helper domains such as due-diligence analysis should persist
  their own run/result state without stamping deck `READY`; final workflow
  publication remains owned by `db_publisher`.
- Legacy shell/final-deck compilation helpers should also avoid writing
  `Deck.status = "reviewed"` because that canonicalizes to `READY` and creates
  a second readiness publisher outside the workflow graph.
- Smart Deck generation now queues through
  `llm_generation -> schema_validation -> preview_render -> db_publisher`
  rather than jumping directly from generation to publisher.
- `schema_validation` now checks that generated slides exist and carry
  `render_schema_json`, and `preview_render` now records a concrete design
  version manifest artifact for the workflow job.
- `export` is now queueable through the workflow contract and records a
  concrete `deck_export` workflow artifact backed by the existing export
  service.
- Legacy `/decks/{deck_id}/export` routes now enqueue workflow export jobs
  instead of creating exports inline in the request thread.
- The source file save step is now also persisted as a durable
  `source_ingestion` workflow job row so every source pipeline stage has a job.
- The source pipeline now reuses that one checksum-scoped `source_ingestion`
  job as the dependency head for source extraction instead of minting a second
  run-scoped ingestion job.
- Source pipeline stages after ingestion are now also checksum-scoped durable
  jobs first, with `DeckExtractionRun` retained as compatibility provenance
  rather than the primary idempotency authority.
- The workflow source path no longer falls back to the latest compatibility
  processing run when deciding reuse. It reuses the run linked from the
  durable workflow graph or creates a fresh compatibility run.
- Source-pipeline workers can now also self-heal a missing compatibility run
  for provenance when a workflow job exists, instead of treating the
  compatibility run as a hard execution prerequisite.
- That self-healed compatibility run now derives its `source_file_id` and
  source-format provenance from `DeckFile`, matching the actual foreign-key
  model used by `DeckExtractionRun`.
- Structure extraction, preview extraction, and Smart Deck source-workspace
  helpers no longer publish deck `READY` or failure state themselves. They
  persist stage results only; final readiness publication stays with
  `db_publisher`.
- Canonical workflow-state readiness booleans such as Smart Deck openability
  now derive from completed publisher output, not merely from upstream context
  builders finishing their work.
- Canonical workflow-state readiness booleans for source extraction and brand
  extraction now derive from completed `workflow_jobs` by stage, with slide,
  asset, and thumbnail counts retained only as informational summaries.
- The legacy `DeckExtractionRun` compatibility wrapper now delegates to the
  head workflow job for the run (`source_ingestion`, `source_extraction`, and
  later stages) instead of assuming `source_extraction` is always first.
- The old coarse source-processing execution helpers have now been removed from
  that compatibility module, leaving it closer to a queue/run adapter than a
  second pipeline implementation.
- The legacy intake `/status` payload is now derived from canonical
  `workflow-state` instead of maintaining a separate readiness heuristic over
  `Deck.status` and extraction-run fields.
- New route work should prefer async queued responses over inline long-running
  helper execution when touching Smart Deck or source-processing paths.
- Legacy-compatible Smart Deck and assistant wrapper routes now enqueue
  workflow jobs instead of launching separate inline background helper flows.
- Those generation-start compatibility wrappers should also return queue-first
  accepted payloads only; they should not reload Smart Deck workspace state in
  the same request after enqueue.
- The legacy apply-version wrapper may keep the design-version envelope for
  compatibility, but it should still expose workflow-job metadata and return
  `202 Accepted` so callers do not mistake queueing for synchronous apply.
- Admin generation retry now also re-enters through a durable
  `llm_generation` workflow job instead of creating a replacement generation
  run inline from the admin service.
- Legacy `/processing` visibility is now a compatibility projection over the
  canonical `workflow-state` payload rather than an independent source of truth.
- Legacy `/processing`, `/status`, and upload/intake compatibility payloads
  should surface `workflowId`, `workflowPhase`, `workflowStatus`,
  `workflowJobId`, `workflowJobType`, and `workflowJobStatus` whenever the
  durable workflow graph already knows them.

## Railway service split

The explicit Railway service matrix lives in [docs/jun26/services.md](docs/jun26/services.md).
Use that document when creating separate Railway services for:

- the backend API
- each durable worker role
- the frontend web app
- Workspace summary, welcome-state, and similar dashboard read models should
  also classify deck readiness from canonical workflow-state where available,
  instead of relying only on the persisted `Deck.status` snapshot.
- Structure and artifact read endpoints should also surface `workflowId`,
  `workflowPhase`, and `workflowStatus` directly when possible, with
  `extractionRun` retained only as legacy provenance rather than primary
  pipeline authority.
- Admin/observability read models should likewise prefer canonical
  workflow-state and workflow visibility payloads over `DeckExtractionRun`
  snapshots when reporting current phase, queueing, or readiness.
- Workspace dashboard cards and similar marketing-style overview surfaces should
  also derive visible deck readiness from workflow-state where possible,
  instead of mapping raw `Deck.status` values like `reviewed` or `ready`
  independently.
- When a compatibility visibility payload still includes `deckStatus`, it
  should reflect the workflow-derived lifecycle being shown to the caller. If
  the raw persisted `Deck.status` snapshot is useful for debugging, expose it
  separately rather than mixing the two signals into one field.
- Legacy `POST /products/deck-aistack-codes/decks/{deck_id}/extract-structure`
  now enqueues source extraction instead of running inline extraction work.
- The API background helper now processes only the accepted workflow job; it
  does not walk the entire dependency chain. Downstream stages are expected to
  be claimed by worker processes through the shared durable queue.
- The old in-process workflow background helper has now been removed from the
  public execution path entirely. Durable workflow execution is worker-owned.
- Public API routes and compatibility wrappers now stop at durable enqueue.
  They no longer call workflow execution helpers directly from the request
  process after returning an accepted workflow job.
- The canonical workflow command routes no longer keep a no-op
  `BackgroundTasks` bridge. They are pure enqueue/accept surfaces now.
- Queue-first compatibility aliases such as retry, slide-redesign, and export
  should follow the same rule: no request-thread worker bridge, only durable
  enqueue plus accepted/projection responses.
- The legacy compatibility queue adapter also no longer runs the workflow
  worker inline after creating a durable job. Queue ownership stays with the
  worker fleet.
- The workflow schema now carries DB-level uniqueness for idempotency,
  dependency edges, and artifacts, plus a stable job-status check constraint.
- The public workflow response schema now treats workflow `jobType` and job
  `status` as explicit API enums rather than loose strings.
- The durable workflow tables also persist the operational lifecycle needed by
  workers and the orchestrator: `queued_at`, `started_at`, `completed_at`,
  `failed_at`, `heartbeat_at`, `locked_by`, `locked_until`, structured
  `error_code`, structured `output_json`, artifacts, and dependency edges.
- Alembic revision `0020_workflow_job_lifecycle_columns` adds first-class
  lifecycle columns for orchestrator-grade operations:
  `recovery_count`, `last_recovered_at`, `last_recovered_by`,
  `terminal_reason`, `published_phase`, and `published_at`.
- Stale running jobs are recovered from `workflow_jobs` by heartbeat age,
  requeued when attempts remain, and marked `timed_out` when the retry budget
  is exhausted.
- Stale recovery now also respects the worker lease itself via `locked_until`,
  so a dead worker can be reclaimed even when a stale heartbeat payload still
  exists.
- Worker runtime now refreshes `heartbeat_at` and `locked_until` while a job is
  still executing, so stale-job recovery does not race long PDF extraction,
  Smart Deck generation, or export work.
- Terminal workflow outcomes are durable and queryable as `completed`,
  `failed_final`, `blocked`, and `timed_out`.

Dedicated worker entrypoints now available under `app/workers/`:

- `source_ingestion_worker.py`
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
- `stale_job_rescuer_worker.py`

Each entrypoint sets `DECK_WORKER_JOB_TYPES` for one job type and then runs the
shared queue loop. This allows deployment to run separate worker processes by
responsibility while still using one durable `workflow_jobs` claim/recovery
implementation.

The Railway/manual worker bootstrap scripts now also run the durable
`workflow_jobs` loop and honor `DECK_WORKER_JOB_TYPES`, so deployment can keep a
health-check wrapper while still claiming only the intended job types.

Deployment can now select dedicated workers by `APP_ROLE` as well:

- `worker-source-ingestion`
- `worker-source-extraction`
- `worker-miniatures`
- `worker-brand-extraction`
- `worker-smart-deck-context`
- `worker-db-publisher`
- `worker-llm-generation`
- `worker-schema-validation`
- `worker-preview-render`
- `worker-apply-version`
- `worker-export`
- `worker-stale-job-rescuer`

If one of those roles is used and `DECK_WORKER_JOB_TYPES` is unset, the worker
bootstrap maps the role to the matching job type automatically.
The rescuer role sets `DECK_WORKER_RECOVERY_ONLY=true` so it only runs stale
workflow-job recovery and never claims normal stage work.

Best-practice deployment rule:

- Production should run dedicated `worker-*` roles so each process claims one
  workflow `job_type`.
- The generic `worker` role remains a development or break-glass fallback, not
  the preferred production topology.

## Configuration

Copy `.env.example` to `.env` for local development. Production deployments must provide real values through the platform environment.

Required production settings include:

- `APP_ENV=production`
- `DATABASE_URL`
- `AUTH_SECRET_KEY`
- `AUTH_SECRET_KEY_ID`
- `WORKSPACE_AI_FERNET_KEY`
- `WORKSPACE_AI_FERNET_KEY_VERSION`
- `ALLOWED_ORIGINS` or `CORS_ORIGIN`
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
- `UPLOAD_SECURITY_SCAN_COMMAND`

For durable production uploads, connect the backend service to the bucket using Railway's `AWS SDK (Generic)` connector. The backend accepts the AWS-style variables that connector injects, plus the older Railway aliases:

- `S3_BUCKET_NAME`, `AWS_S3_BUCKET_NAME`, `UPLOAD_STORAGE_S3_BUCKET`, or `RAILWAY_BUCKET_NAME`
- `AWS_DEFAULT_REGION`, `UPLOAD_STORAGE_S3_REGION`, or `RAILWAY_BUCKET_REGION`
- `AWS_ENDPOINT_URL`, `UPLOAD_STORAGE_S3_ENDPOINT`, or `RAILWAY_BUCKET_ENDPOINT`
- `AWS_ACCESS_KEY_ID`, `UPLOAD_STORAGE_S3_ACCESS_KEY`, or `RAILWAY_BUCKET_ACCESS_KEY`
- `AWS_SECRET_ACCESS_KEY`, `UPLOAD_STORAGE_S3_SECRET_KEY`, or `RAILWAY_BUCKET_SECRET_KEY`

If Railway injects `AWS_*` names through the bucket connector, that is the preferred path for this FastAPI/boto3 backend.

## Deck processing worker

Smart Deck extraction requires a separate long-running worker service in production.

Create a second Railway service from the same backend repository/image and set:

```bash
APP_ROLE=worker
RUN_MIGRATIONS_ON_STARTUP=false
RUN_WORKER_MIGRATIONS_ON_STARTUP=false
```

Use the same database, storage, auth, and AI provider environment values as the API service. The role-aware startup script runs `scripts/deck_processing_worker.py`, which claims queued deck-processing jobs, records worker heartbeat telemetry, recovers stale runs, and exposes `/api/health` for Railway health checks.

See `docs/deck-processing-worker-service.md` for the full deployment checklist.

## Public interest bot protection

Public interest bot protection is controlled separately from the public lead form:

- `TURNSTILE_SECRET_KEY` stores the Cloudflare Turnstile secret.
- `PUBLIC_INTEREST_TURNSTILE_REQUIRED=true` requires a browser token on `/api/public/interest`.
- Leave `PUBLIC_INTEREST_TURNSTILE_REQUIRED=false` until the frontend widget is configured, otherwise public lead submissions without a token will be blocked.

## Verification

```bash
python3 -m compileall -q app alembic scripts
```

```bash
DATABASE_URL=sqlite:// python scripts/verify_production_contract.py
```

```bash
DATABASE_URL=sqlite:// python -m pytest tests/test_railway_deploy_config.py tests/test_tester_readiness_smoke.py tests/test_production_route_contract.py tests/test_public_interest_route.py -q
```

```bash
DATABASE_URL=sqlite:// python -m pytest tests/test_workspace_ai_provider_service.py tests/test_auth_route_security.py tests/test_smart_deck_route_security.py tests/test_deck_intake_route_security.py -q
```

Run migrations before deployment:

```bash
alembic upgrade head
```
