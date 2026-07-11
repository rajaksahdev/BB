"""Health check endpoint — Phase 0 done-gate and deployment liveness probe."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.db import get_db

router = APIRouter(tags=["health"])


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
        },
    )
