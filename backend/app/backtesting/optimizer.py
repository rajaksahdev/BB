"""Parameter-sweep optimizer: grid-search a strategy's params on one dataset.

Design constraints (same honesty + availability guardrails as the engine):
- Fees and slippage are modeled on every combo; the response echoes them.
- The whole sweep runs synchronously under ONE engine concurrency slot and a
  server-side combo cap, so a sweep can never stall interactive backtests or
  turn into an unbounded job. No queues, by design (see EXECUTION_PLAN Phase 7).
- Only percentage/ratio metrics are reported per combo (scale-invariant), so
  the sweep runs on the engine's large internal cash base without rescaling.
"""

import itertools
import math
import time
from datetime import datetime

from backtesting import Backtest

from app.backtesting.data import load_ohlcv
from app.backtesting.engine import (
    DISCLAIMER,
    _clean,
    _MIN_CANDLES,
    coerce_param,
    engine_slot,
)
from app.backtesting.strategies import STRATEGIES
from app.db import SessionLocal

# Metrics a sweep can rank by. All are "higher is better" (max_drawdown_pct is
# negative, so the least-bad drawdown correctly sorts first).
METRICS = ("return_pct", "sharpe_ratio", "win_rate_pct", "max_drawdown_pct")

# A sweep is a UI over sliders — 1 or 2 swept params is the product surface
# (table / heatmap). 3+ explodes the grid and has no visualization.
MAX_SWEPT_PARAMS = 2

_MAX_VALUES_PER_PARAM = 50


def _grid_values(name: str, spec: dict, rng: dict) -> list[float]:
    """Expand one param's {min,max,step} range against its declared bounds."""
    is_int = spec["type"] == "int"
    lo = rng.get("min", spec.get("min"))
    hi = rng.get("max", spec.get("max"))
    if lo is None or hi is None:
        raise ValueError(f"Parameter '{name}' needs an explicit min and max to sweep.")
    lo = int(lo) if is_int else float(lo)
    hi = int(hi) if is_int else float(hi)
    if hi < lo:
        raise ValueError(f"Sweep range for '{name}' has max < min.")
    b_lo, b_hi = spec.get("min"), spec.get("max")
    if (b_lo is not None and lo < b_lo) or (b_hi is not None and hi > b_hi):
        raise ValueError(
            f"Sweep range for '{name}' must stay within [{b_lo}, {b_hi}]."
        )
    default_step = (hi - lo) / 10 if not is_int else max(1, round((hi - lo) / 10))
    step = rng.get("step") or default_step
    step = int(step) if is_int else float(step)
    if step <= 0:
        raise ValueError(f"Sweep step for '{name}' must be > 0.")
    n_values = math.floor((hi - lo) / step) + 1
    if n_values > _MAX_VALUES_PER_PARAM:
        raise ValueError(
            f"Sweep for '{name}' yields {n_values} values (max "
            f"{_MAX_VALUES_PER_PARAM}). Increase the step or narrow the range."
        )
    values = [lo + i * step for i in range(n_values)]
    # Include the range's far edge so min/max are always tested even when the
    # step doesn't land on it exactly.
    if values[-1] < hi:
        values.append(hi)
    if not is_int:
        values = [round(v, 6) for v in values]
    return values


def run_optimization(
    symbol: str,
    interval: str,
    strategy: str,
    param_ranges: dict[str, dict],
    fixed_params: dict | None = None,
    metric: str = "return_pct",
    start: datetime | None = None,
    end: datetime | None = None,
    fee_pct: float = 0.001,
    slippage_pct: float = 0.0005,
    max_combos: int = 200,
) -> dict:
    """Grid-search ``param_ranges``, rank combos by ``metric``, return them all.

    Raises ``ValueError`` for invalid input and ``EngineBusy`` when the engine
    has no free slot.
    """
    if strategy not in STRATEGIES:
        raise ValueError(
            f"Unknown strategy '{strategy}'. Available: {', '.join(STRATEGIES)}"
        )
    if metric not in METRICS:
        raise ValueError(f"Unknown metric '{metric}'. Available: {', '.join(METRICS)}")
    if not param_ranges:
        raise ValueError("Provide at least one parameter range to sweep.")
    if len(param_ranges) > MAX_SWEPT_PARAMS:
        raise ValueError(f"Sweep at most {MAX_SWEPT_PARAMS} parameters at a time.")

    spec = STRATEGIES[strategy]["meta"]["params"]
    for name in param_ranges:
        if name not in spec:
            raise ValueError(
                f"Unknown parameter '{name}' for strategy '{strategy}'. "
                f"Allowed: {', '.join(spec)}"
            )
    swept = list(param_ranges)
    grid = {name: _grid_values(name, spec[name], param_ranges[name]) for name in swept}

    total = math.prod(len(v) for v in grid.values())
    if total > max_combos:
        raise ValueError(
            f"This sweep is {total} combinations (max {max_combos}). "
            f"Increase the step or narrow the ranges."
        )

    # Non-swept params: strategy defaults overridden by any fixed values, each
    # validated against its declared bounds (same rules as a single run).
    base = {k: v["default"] for k, v in spec.items()}
    for key, val in (fixed_params or {}).items():
        if key not in spec:
            raise ValueError(
                f"Unknown parameter '{key}' for strategy '{strategy}'. "
                f"Allowed: {', '.join(spec)}"
            )
        if key in param_ranges:
            continue  # the sweep owns this param
        base[key] = coerce_param(key, spec[key], val)

    validate = STRATEGIES[strategy].get("validate")

    with engine_slot():
        with SessionLocal() as db:
            df = load_ohlcv(db, symbol, interval, start, end)
        if len(df) < _MIN_CANDLES:
            raise ValueError(
                f"Not enough data for {symbol} {interval} in the requested range "
                f"(got {len(df)} candles, need >= {_MIN_CANDLES}). "
                f"Run the data backfill first."
            )

        first_close = float(df["Close"].iloc[0])
        bt = Backtest(
            df,
            STRATEGIES[strategy]["class"],
            cash=first_close * 10_000,  # large base: whole-unit rounding negligible
            commission=float(fee_pct),
            spread=float(slippage_pct),
            finalize_trades=True,
        )

        started = time.perf_counter()
        results: list[dict] = []
        skipped = 0
        for combo_values in itertools.product(*(grid[name] for name in swept)):
            combo = dict(base)
            combo.update(zip(swept, combo_values))
            if validate is not None:
                try:
                    validate(combo)
                except ValueError:
                    skipped += 1  # e.g. fast >= slow — a hole in the grid, not an error
                    continue
            stats = bt.run(**combo)
            results.append(
                {
                    "params": {name: combo[name] for name in swept},
                    "return_pct": _clean(stats.get("Return [%]")),
                    "sharpe_ratio": _clean(stats.get("Sharpe Ratio")),
                    "max_drawdown_pct": _clean(stats.get("Max. Drawdown [%]")),
                    "win_rate_pct": _clean(stats.get("Win Rate [%]")),
                    "trade_count": int(stats.get("# Trades", 0)),
                }
            )
        elapsed_ms = round((time.perf_counter() - started) * 1000)

    if not results:
        raise ValueError(
            "Every combination in this sweep is invalid for the strategy "
            "(e.g. fast >= slow across the whole grid). Adjust the ranges."
        )

    # Rank best-first; combos where the metric is undefined (e.g. Sharpe with
    # no trades) sink to the bottom.
    results.sort(key=lambda r: (r[metric] is None, -(r[metric] or 0)))
    best = results[0]

    return {
        "request": {
            "symbol": symbol,
            "interval": interval,
            "strategy": strategy,
            "metric": metric,
            "start": df.index[0].isoformat(),
            "end": df.index[-1].isoformat(),
            "fixed_params": {k: v for k, v in base.items() if k not in param_ranges},
        },
        "swept": swept,
        "grid": grid,
        "results": results,
        "best": {**best, "full_params": {**base, **best["params"]}},
        "combos_run": len(results),
        "combos_skipped": skipped,
        "elapsed_ms": elapsed_ms,
        "assumptions": {
            "fee_pct": float(fee_pct),
            "slippage_pct": float(slippage_pct),
            "position": "long-only",
            "note": (
                "Fees applied per transaction; slippage modeled as spread. "
                "Optimized parameters are fit to this exact period — expect "
                "worse out-of-sample performance (overfitting risk)."
            ),
        },
        "disclaimer": DISCLAIMER,
    }
