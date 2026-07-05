from __future__ import annotations

import os

os.environ.setdefault("WORKER_KIND", "llm_generation")
os.environ.setdefault("DECK_WORKER_JOB_TYPES", "llm_generation")

from app.workers.deck_queue_worker import main


if __name__ == "__main__":
    main()
