"""Health check endpoint — Phase 0 done-gate and deployment liveness probe."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import __version__
from app.db import get_db
from app.models import Candle

router = APIRouter(tags=["health"])


def _data_freshness(db: Session) -> list[dict]:
    """Newest-candle age per (symbol, interval) — catches a broken backfill
    before users do. Best-effort: failures degrade to an empty list."""
    try:
        rows = db.execute(
            select(
                Candle.symbol, Candle.interval, func.max(Candle.open_time)
            ).group_by(Candle.symbol, Candle.interval)
        ).all()
    except Exception:  # noqa: BLE001 - freshness is advisory, never break the probe
        return []
    now = datetime.now(tz=UTC)
    out = []
    for symbol, interval, newest in rows:
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=UTC)
        out.append(
            {
                "symbol": symbol,
                "interval": interval,
                "newest": newest.isoformat(),
                "age_hours": round((now - newest).total_seconds() / 3600, 1),
            }
        )
    return sorted(out, key=lambda r: (r["symbol"], r["interval"]))


@router.get("/health")
def health(db: Session = Depends(get_db)) -> JSONResponse:
    """Return service status and verify the DB connection is live.

    Degraded returns 503 so the platform health check (render.yaml sets
    ``healthCheckPath: /health``) actually marks the instance unhealthy
    instead of routing traffic to an API that can't reach its database.
    """
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - report DB down rather than crash the probe
        db_ok = False

    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={
            "status": "ok" if db_ok else "degraded",
            "version": __version__,
            "database": "up" if db_ok else "down",
            "data": _data_freshness(db) if db_ok else [],
        },
    )
