"""Indicator helpers used by strategies via ``Strategy.I(...)``.

Each returns a NumPy array aligned to the input series (leading NaNs where the
window is not yet full).
"""

import numpy as np
import pandas as pd


def sma(values, n: int):
    """Simple moving average."""
    return pd.Series(values).rolling(int(n)).mean().to_numpy()


def rsi(values, n: int):
    """Relative Strength Index (Wilder-style simple-mean approximation)."""
    series = pd.Series(values).astype(float)
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(int(n)).mean()
    loss = (-delta.clip(upper=0)).rolling(int(n)).mean()
    rs = gain / loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.to_numpy()
