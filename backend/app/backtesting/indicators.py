"""Indicator helpers used by strategies via ``Strategy.I(...)``.

Each returns a NumPy array aligned to the input series (leading NaNs where the
window is not yet full).
"""

import numpy as np
import pandas as pd


def sma(values, n: int):
    """Simple moving average."""
    return pd.Series(values).rolling(int(n)).mean().to_numpy()


def ema(values, n: int):
    """Exponential moving average (span-based, NaN until the window fills)."""
    return (
        pd.Series(values)
        .astype(float)
        .ewm(span=int(n), adjust=False, min_periods=int(n))
        .mean()
        .to_numpy()
    )


def rsi(values, n: int):
    """Relative Strength Index with Wilder's smoothing (matches TradingView)."""
    n = int(n)
    series = pd.Series(values).astype(float)
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = gain / loss
        out = 100 - (100 / (1 + rs))
    # loss == 0 -> rs is inf (all gains, RSI 100) or NaN (flat window).
    out = out.where(loss != 0, 100.0).where(~((gain == 0) & (loss == 0)), 50.0)
    return out.to_numpy()


def rolling_std(values, n: int):
    """Rolling standard deviation (population of the window, ddof=0)."""
    return pd.Series(values).astype(float).rolling(int(n)).std(ddof=0).to_numpy()
