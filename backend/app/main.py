"""FastAPI application entrypoint.

Run locally:  uvicorn app.main:app --reload  (from the backend/ directory)
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api import backtest, backtests, billing, health
from app.config import get_settings

settings = get_settings()

# Route the app's own loggers (backtestlab.billing, .backfill, .freshness, …)
# to stdout at the configured level so they show up in platform logs.
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# API payloads here are small JSON bodies (a backtest config, a saved label).
# Reject anything larger up front so a huge body can't tie up the worker. The
# billing webhook is exempt — event payloads can legitimately be larger.
_MAX_BODY_BYTES = 64 * 1024

app = FastAPI(
    title="BacktestLab API",
    version=__version__,
    description="AI-assisted crypto strategy backtesting — no custody, no signals.",
)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    if not request.url.path.startswith("/billing/webhook"):
        content_length = request.headers.get("content-length")
        if content_length is not None and content_length.isdigit():
            if int(content_length) > _MAX_BODY_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request body too large."})
    return await call_next(request)

# The frontend runs on a different origin; allow the configured origins
# (CORS_ORIGINS env var — defaults to local Vite/CRA in dev).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(backtest.router)
app.include_router(backtests.router)
app.include_router(billing.router)


@app.get("/")
def root() -> dict:
    return {
        "name": "BacktestLab API",
        "version": __version__,
        "docs": "/docs",
        "disclaimer": (
            "For research only. Not financial advice. "
            "Past performance does not guarantee future results."
        ),
    }
