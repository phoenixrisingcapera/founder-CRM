# Stuck Smart Deck Diagnosis

## What the user sees

The intake screen stays on:

- `Checking Smart Deck readiness`
- `Reading your uploaded slides`
- `Creating slide previews`
- `Preparing your Smart Deck workspace`

The message `Blocking reason: slides not read` is a backend readiness projection, not a frontend crash.

## What is actually happening

The frontend is polling backend workflow state correctly.

The blocker is that the workflow never reaches the source-read complete state that would let the readiness contract mark the deck openable.

## Live Railway evidence

Current production topology shows:

- `worker-source-extraction`: online and healthy
- `worker-miniatures`: online and healthy
- `worker-preview-render`: online and healthy
- `worker-stale-job-rescuer`: online and healthy
- `deck-processing-worker`: failed deployment

The backend API deployment is now healthy again. I hardened the `0033_smart_deck_bucket_keys` and `0035_failure_tickets` migrations so the duplicate-column / duplicate-table startup warnings no longer recur when those objects already exist.

That means the dedicated PDF-reading worker exists, but the legacy generic worker path is still present and disconnected.

## Pipeline boundary for PDF reading

The PDF read/extract path is the backend source pipeline:

- `worker-source-ingestion`
- `worker-source-extraction`
- `worker-miniatures`
- `worker-preview-render`

`worker-source-extraction` is the service that should actually read the uploaded PDF/PPTX, persist slides, and make `workflow-state.source.slideCount` / `source.extractionReady` true.

## Why the loader stalls

`workflow-state` only returns `canOpenSmartDeck=true` when the backend has enough source and preview evidence.

If slide extraction never completes, the readiness service reports:

- `currentStep = reading_uploaded_slides`
- `blockingReason = slides_not_read`

That is the state currently shown in the UI.

The live browser session was also still hitting the legacy `smart-deck-readiness` route. That is a compatibility path and should not be the primary source of truth, but it can make stale tabs look noisier than they are.

## Recovery action taken

I normalized worker role inference so Railway service names can select the correct worker kind without brittle manual env setup.

The legacy `deck-processing-worker` service is now treated as recovery-only by default instead of trying to act like a general-purpose worker.

The frontend processing page now auto-retries stalled decks once when the deck has been sitting in a stalled queued/processing state long enough, so older decks can re-enter the canonical source pipeline without a manual click.

## Next checks

- confirm `worker-source-extraction` keeps claiming jobs on Railway
- inspect `/api/admin/decks/{deckId}/workflow-state` for the stuck deck
- inspect `/api/admin/workers/heartbeat`
- verify the extraction job writes slide rows and thumbnail artifacts
- verify `workflow-state.source.slideCount > 0` and `source.extractionReady=true`
