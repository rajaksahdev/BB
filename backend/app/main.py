"""FastAPI application entrypoint.

Run locally:  uvicorn app.main:app --reload  (from the backend/ directory)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import backtest, backtests, billing, health
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="BacktestLab API",
    version=__version__,
    description="AI-assisted crypto strategy backtesting — no custody, no signals.",
)

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
