"""Backtest API: list strategies/symbols and run a backtest (FR-02, FR-03)."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.backtesting.engine import EngineBusy, run_backtest
from app.backtesting.schemas import BacktestRequest
from app.backtesting.strategies import STRATEGIES
from app.config import get_settings
from app.data.freshness import ensure_fresh
from app.db import get_db
from app.models import Candle
from app.ratelimit import RateLimiter

router = APIRouter(tags=["backtest"])
logger = logging.getLogger("backtestlab.runs")

# The backtest runs a full simulation synchronously and is unauthenticated, so
# cap how often any single IP can trigger it to protect CPU/availability.
_settings = get_settings()
_backtest_limiter = RateLimiter(
    limit=_settings.backtest_rate_limit, window=_settings.backtest_rate_window
)


@router.get("/strategies")
def list_strategies() -> list[dict]:
    """Strategy catalog + tunable params (powers the UI config form)."""
    return [
        {
            "key": key,
            "name": entry["meta"]["name"],
            "description": entry["meta"]["description"],
            "params": entry["meta"]["params"],
        }
        for key, entry in STRATEGIES.items()
    ]


@router.get("/symbols")
def list_symbols(db: Session = Depends(get_db)) -> dict:
    """Pairs/intervals that actually have candle data (powers the UI selects).

    Derived from the candles table so adding a coin is a backfill run — no
    frontend deploy needed.
    """
    symbols = db.scalars(select(Candle.symbol).distinct().order_by(Candle.symbol)).all()
    intervals = db.scalars(
        select(Candle.interval).distinct().order_by(Candle.interval)
    ).all()
    return {"symbols": list(symbols), "intervals": list(intervals)}


@router.post("/backtest", dependencies=[Depends(_backtest_limiter)])
def post_backtest(req: BacktestRequest) -> dict:
    """Run a backtest synchronously and return stats + equity curve."""
    if _settings.data_auto_refresh:
        ensure_fresh(req.symbol, req.interval)
    # Product-analytics signal (config only, never IPs/PII): which strategies,
    # pairs and params people actually run drives what gets built next.
    logger.info(
        "run strategy=%s symbol=%s interval=%s params=%s ranged=%s",
        req.strategy,
        req.symbol,
        req.interval,
        req.params,
        bool(req.start or req.end),
    )
    try:
        return run_backtest(
            symbol=req.symbol,
            interval=req.interval,
            strategy=req.strategy,
            params=req.params,
            start=req.start,
            end=req.end,
            cash=req.cash,
            fee_pct=req.fee_pct,
            slippage_pct=req.slippage_pct,
        )
    except EngineBusy as exc:
        raise HTTPException(
            status_code=429, detail=str(exc), headers={"Retry-After": "5"}
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
