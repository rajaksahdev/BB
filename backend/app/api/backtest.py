"""Backtest API: list strategies and run a backtest (FR-02, FR-03)."""

from fastapi import APIRouter, Depends, HTTPException

from app.backtesting.engine import run_backtest
from app.backtesting.schemas import BacktestRequest
from app.backtesting.strategies import STRATEGIES
from app.config import get_settings
from app.ratelimit import RateLimiter

router = APIRouter(tags=["backtest"])

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


@router.post("/backtest", dependencies=[Depends(_backtest_limiter)])
def post_backtest(req: BacktestRequest) -> dict:
    """Run a backtest synchronously and return stats + equity curve."""
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
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
