"""Health check endpoint — Phase 0 done-gate and deployment liveness probe."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Return service status and verify the DB connection is live."""
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - report DB down rather than crash the probe
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "version": __version__,
        "database": "up" if db_ok else "down",
    }
