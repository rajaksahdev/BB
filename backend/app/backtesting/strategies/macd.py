"""MACD Crossover (momentum trend-following, long-only)."""

from backtesting import Strategy
from backtesting.lib import crossover

from app.backtesting.indicators import ema


def macd_line(values, fast: int, slow: int):
    return ema(values, fast) - ema(values, slow)


def signal_line(values, fast: int, slow: int, signal: int):
    return ema(macd_line(values, fast, slow), signal)


class Macd(Strategy):
    fast = 12
    slow = 26
    signal = 9

    def init(self):
        close = self.data.Close
        self.macd = self.I(macd_line, close, self.fast, self.slow)
        self.signal_l = self.I(signal_line, close, self.fast, self.slow, self.signal)

    def next(self):
        if crossover(self.macd, self.signal_l):
            self.position.close()
            self.buy()
        elif crossover(self.signal_l, self.macd):
            self.position.close()


def validate(params: dict) -> None:
    if params["fast"] >= params["slow"]:
        raise ValueError(
            f"'fast' EMA period ({params['fast']}) must be less than "
            f"'slow' ({params['slow']})."
        )


STRATEGY = Macd

META = {
    "key": "macd",
    "name": "MACD Crossover",
    "description": (
        "Go long when the MACD line crosses above its signal line; exit when "
        "it crosses back below. Momentum trend-following with EMA smoothing."
    ),
    "params": {
        "fast": {"type": "int", "default": 12, "min": 2, "max": 50, "label": "Fast EMA period"},
        "slow": {"type": "int", "default": 26, "min": 5, "max": 200, "label": "Slow EMA period"},
        "signal": {"type": "int", "default": 9, "min": 2, "max": 50, "label": "Signal period"},
    },
}
