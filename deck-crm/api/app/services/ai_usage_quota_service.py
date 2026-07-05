from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import generate_id
from app.db.models import AiUsageBucket, User

DAILY_AI_QUOTA_KEY = "daily_generation"
DAILY_AI_QUOTA_WINDOW_SECONDS = 24 * 60 * 60


def _quota_exceeded() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Daily AI generation quota exceeded. Please try again later.",
    )


def enforce_ai_generation_quota(
    db: Session,
    user: User,
    *,
    units: int = 1,
    quota: int | None = None,
    window_seconds: int = DAILY_AI_QUOTA_WINDOW_SECONDS,
) -> None:
    allowed = quota if quota is not None else settings.ai_daily_generation_quota
    if allowed <= 0:
        raise _quota_exceeded()
    if units <= 0:
        return

    now = datetime.utcnow()
    window_delta = timedelta(seconds=window_seconds)
    try:
        bucket = (
            db.query(AiUsageBucket)
            .filter(AiUsageBucket.user_id == user.id, AiUsageBucket.quota_key == DAILY_AI_QUOTA_KEY)
            .with_for_update()
            .one_or_none()
        )
        if bucket is None:
            if units > allowed:
                raise _quota_exceeded()
            db.add(
                AiUsageBucket(
                    id=generate_id("aiusage"),
                    user_id=user.id,
                    quota_key=DAILY_AI_QUOTA_KEY,
                    window_start=now,
                    usage_count=units,
                    updated_at=now,
                )
            )
            db.commit()
            return

        if now - bucket.window_start >= window_delta:
            if units > allowed:
                raise _quota_exceeded()
            bucket.window_start = now
            bucket.usage_count = units
            bucket.updated_at = now
            db.commit()
            return

        if bucket.usage_count + units > allowed:
            db.rollback()
            raise _quota_exceeded()

        bucket.usage_count += units
        bucket.updated_at = now
        db.commit()
    except IntegrityError:
        db.rollback()
        enforce_ai_generation_quota(db, user, units=units, quota=allowed, window_seconds=window_seconds)
