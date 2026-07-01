"""Free-tier usage accounting (FR-06).

The monthly count is derived from ``saved_backtests.created_at`` — no separate
counter table to drift out of sync.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SavedBacktest


def month_start_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.now(tz=UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def monthly_count(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(SavedBacktest)
            .where(
                SavedBacktest.user_id == user_id,
                SavedBacktest.created_at >= month_start_utc(),
            )
        )
        or 0
    )
