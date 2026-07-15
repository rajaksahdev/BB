"""Backtest engine: (pair, strategy, params, range) -> stats + equity curve.

Honest by design (spec guardrail): every run models trading **fees** (via
commission) and **slippage** (via spread), and the response echoes those
assumptions plus a disclaimer.

Note on sizing: backtesting.py trades whole units, so a small cash base against
an expensive asset (e.g. $10k vs $60k BTC) would round to zero trades. We run
the simulation on a large internal cash base (quantization negligible) and scale
all monetary outputs back to the user's chosen starting cash. Percentage metrics
(return, drawdown, win rate, Sharpe) are scale-invariant and unaffected.
"""

import math
import threading
from datetime import datetime

import pandas as pd
from backtesting import Backtest

from app.backtesting.data import load_ohlcv
from app.backtesting.strategies import STRATEGIES
from app.config import get_settings
from app.db import SessionLocal


class EngineBusy(RuntimeError):
    """All engine slots are running simulations; the caller should retry."""


# Simulations are CPU-bound and GIL-contending: unbounded concurrency stalls
# every request on the instance (including /health). A short acquire wait
# absorbs bursts; beyond it the API answers 429 instead of piling up.
_run_slots = threading.BoundedSemaphore(get_settings().backtest_max_concurrency)
_ACQUIRE_WAIT_SECONDS = 2.0

DISCLAIMER = (
    "For research and educational use only. This is NOT financial advice. "
    "Past performance does not guarantee future results. Results model "
    "estimated fees and slippage and may differ from live trading."
)

_MIN_CANDLES = 50


def _clean(value) -> float | None:
    """Convert to float, mapping NaN/inf to None for JSON safety."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _resolve_params(strategy_key: str, raw: dict) -> dict:
    """Validate + coerce user params against the strategy's declared schema."""
    spec = STRATEGIES[strategy_key]["meta"]["params"]
    merged = {k: v["default"] for k, v in spec.items()}
    for key, val in (raw or {}).items():
        if key not in spec:
            raise ValueError(
                f"Unknown parameter '{key}' for strategy '{strategy_key}'. "
                f"Allowed: {', '.join(spec)}"
            )
        coerced = int(val) if spec[key]["type"] == "int" else float(val)
        lo, hi = spec[key].get("min"), spec[key].get("max")
        if lo is not None and coerced < lo:
            raise ValueError(f"'{key}' must be >= {lo}")
        if hi is not None and coerced > hi:
            raise ValueError(f"'{key}' must be <= {hi}")
        merged[key] = coerced
    validate = STRATEGIES[strategy_key].get("validate")
    if validate is not None:
        validate(merged)
    return merged


def run_backtest(
    symbol: str,
    interval: str,
    strategy: str,
    params: dict | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    cash: float = 10_000.0,
    fee_pct: float = 0.001,
    slippage_pct: float = 0.0005,
    max_curve_points: int = 1000,
    max_trades: int = 500,
) -> dict:
    """Run a single backtest and return a JSON-serializable result.

    Raises ``EngineBusy`` when all concurrency slots are taken.
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"Unknown strategy '{strategy}'. Available: {', '.join(STRATEGIES)}"
        )
    resolved = _resolve_params(strategy, params)

    if not _run_slots.acquire(timeout=_ACQUIRE_WAIT_SECONDS):
        raise EngineBusy(
            "The server is running its maximum number of simultaneous "
            "backtests. Please retry in a few seconds."
        )
    try:
        return _run(symbol, interval, strategy, resolved, start, end, cash,
                    fee_pct, slippage_pct, max_curve_points, max_trades)
    finally:
        _run_slots.release()


def _run(
    symbol: str,
    interval: str,
    strategy: str,
    resolved: dict,
    start: datetime | None,
    end: datetime | None,
    cash: float,
    fee_pct: float,
    slippage_pct: float,
    max_curve_points: int,
    max_trades: int,
) -> dict:

    with SessionLocal() as db:
        df = load_ohlcv(db, symbol, interval, start, end)

    if len(df) < _MIN_CANDLES:
        raise ValueError(
            f"Not enough data for {symbol} {interval} in the requested range "
            f"(got {len(df)} candles, need >= {_MIN_CANDLES}). "
            f"Run the data backfill first."
        )

    # Large internal cash base so whole-unit rounding is negligible.
    first_close = float(df["Close"].iloc[0])
    internal_cash = max(float(cash), first_close * 10_000)
    scale = float(cash) / internal_cash

    bt = Backtest(
        df,
        STRATEGIES[strategy]["class"],
        cash=internal_cash,
        commission=float(fee_pct),   # trading fee per transaction
        spread=float(slippage_pct),  # slippage / bid-ask spread
        finalize_trades=True,
    )
    stats = bt.run(**resolved)

    return_pct = _clean(stats.get("Return [%]"))

    # Equity curve, scaled to user's cash and downsampled for the chart. The
    # final point is always kept so the curve's end matches the final equity.
    equity_series = stats["_equity_curve"]["Equity"]
    step = max(1, len(equity_series) // max_curve_points)
    sampled = equity_series.iloc[::step]
    if sampled.index[-1] != equity_series.index[-1]:
        sampled = pd.concat([sampled, equity_series.iloc[[-1]]])
    equity_curve = [
        {"time": ts.isoformat(), "equity": round(float(val) * scale, 2)}
        for ts, val in sampled.items()
    ]

    # Trade list (most recent first), scaled. Positions still open at the end
    # of the data are force-closed by finalize_trades on the final bar; those
    # exits are artifacts of where the window ends, not strategy decisions, so
    # they are labeled and excluded from trade-quality stats below (a DCA run,
    # for example, would otherwise report a meaningless 0%/100% win rate).
    trades_df = stats["_trades"]
    last_bar_time = df.index[-1]
    forced_mask = trades_df["ExitTime"] == last_bar_time
    forced_exit_count = int(forced_mask.sum())
    trades = []
    for row in trades_df.tail(max_trades).itertuples():
        trades.append(
            {
                "entry_time": row.EntryTime.isoformat(),
                "exit_time": row.ExitTime.isoformat(),
                "entry_price": _clean(row.EntryPrice),
                "exit_price": _clean(row.ExitPrice),
                "pnl": round((_clean(row.PnL) or 0.0) * scale, 2),
                "return_pct": round((_clean(row.ReturnPct) or 0.0) * 100, 4),
                "exit_reason": "end_of_data" if row.ExitTime == last_bar_time else "signal",
            }
        )
    trades.reverse()

    # Trade-quality stats over strategy-decided exits only.
    closed = trades_df[~forced_mask]
    if len(closed):
        pnl = closed["PnL"]
        ret = closed["ReturnPct"]
        gross_profit = float(pnl[pnl > 0].sum())
        gross_loss = float(-pnl[pnl < 0].sum())
        win_rate_pct = _clean((pnl > 0).mean() * 100)
        profit_factor = _clean(gross_profit / gross_loss) if gross_loss > 0 else None
        avg_trade_pct = _clean(ret.mean() * 100)
        best_trade_pct = _clean(ret.max() * 100)
        worst_trade_pct = _clean(ret.min() * 100)
    else:
        win_rate_pct = profit_factor = None
        avg_trade_pct = best_trade_pct = worst_trade_pct = None

    return {
        "request": {
            "symbol": symbol,
            "interval": interval,
            "strategy": strategy,
            "params": resolved,
            "start": equity_series.index[0].isoformat(),
            "end": equity_series.index[-1].isoformat(),
        },
        "stats": {
            "return_pct": return_pct,
            "buy_hold_return_pct": _clean(stats.get("Buy & Hold Return [%]")),
            "win_rate_pct": win_rate_pct,
            "max_drawdown_pct": _clean(stats.get("Max. Drawdown [%]")),
            "sharpe_ratio": _clean(stats.get("Sharpe Ratio")),
            "sortino_ratio": _clean(stats.get("Sortino Ratio")),
            "calmar_ratio": _clean(stats.get("Calmar Ratio")),
            "cagr_pct": _clean(stats.get("CAGR [%]")),
            "volatility_ann_pct": _clean(stats.get("Volatility (Ann.) [%]")),
            "profit_factor": profit_factor,
            "avg_trade_pct": avg_trade_pct,
            "best_trade_pct": best_trade_pct,
            "worst_trade_pct": worst_trade_pct,
            "trade_count": int(stats.get("# Trades", 0)),
            "forced_exit_count": forced_exit_count,
            "exposure_time_pct": _clean(stats.get("Exposure Time [%]")),
            "starting_cash": round(float(cash), 2),
            "final_equity": round(float(cash) * (1 + (return_pct or 0) / 100), 2),
        },
        "equity_curve": equity_curve,
        "trades": trades,
        "assumptions": {
            "fee_pct": float(fee_pct),
            "slippage_pct": float(slippage_pct),
            "position": "long-only",
            "note": "Fees applied per transaction; slippage modeled as spread.",
        },
        "disclaimer": DISCLAIMER,
    }
