from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, status

WINDOW_SECONDS = 60.0
MAX_REQUESTS_PER_WINDOW = 12

_requests: dict[str, deque[float]] = defaultdict(deque)


def enforce_smart_edit_quota(actor_key: str) -> None:
    now = monotonic()
    window_start = now - WINDOW_SECONDS
    bucket = _requests[actor_key]

    while bucket and bucket[0] < window_start:
        bucket.popleft()

    if len(bucket) >= MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Smart Edit generation quota exceeded. Try again in a minute.",
        )

    bucket.append(now)
