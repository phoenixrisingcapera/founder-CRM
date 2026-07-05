# Railway deck worker

Deck processing now runs as two Railway services from the same backend repo.

## API service

Start command:

```bash
python scripts/start_railway.py
```

Role:

```bash
APP_ROLE=api
```

The API accepts uploads and enqueues deck processing runs.

## Worker service

Create a second Railway service from the same repo and Dockerfile.

Start command:

```bash
APP_ROLE=worker python scripts/start_railway.py
```

The worker service must share the same production database and upload storage configuration as the API service.

Useful variables:

```bash
DECK_WORKER_POLL_INTERVAL_SECONDS=10
DECK_WORKER_STALE_AFTER_SECONDS=900
DECK_WORKER_STALE_RECOVERY_LIMIT=10
DECK_PROCESSING_MAX_ATTEMPTS=3
```

The worker claims queued work, recovers stale running work, and moves exhausted work to manual review.
