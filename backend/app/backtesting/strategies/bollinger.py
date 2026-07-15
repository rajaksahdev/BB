"""Bollinger Band Mean-Reversion (buy the lower band, exit at the middle)."""

from backtesting import Strategy

from app.backtesting.indicators import rolling_std, sma


class Bollinger(Strategy):
    period = 20
    # Band width in standard deviations.
    num_std = 2.0

    def init(self):
        close = self.data.Close
        self.mid = self.I(sma, close, self.period)
        self.std = self.I(rolling_std, close, self.period)

    def next(self):
        mid = self.mid[-1]
        std = self.std[-1]
        if mid != mid or std != std:  # NaN guard (warm-up period)
            return
        price = float(self.data.Close[-1])
        lower = mid - self.num_std * std
        if not self.position and price < lower:
            self.buy()
        elif self.position and price >= mid:
            self.position.close()


STRATEGY = Bollinger

META = {
    "key": "bollinger",
    "name": "Bollinger Band Reversion",
    "description": (
        "Buy when price closes below the lower Bollinger band; exit when it "
        "reverts to the middle band (SMA). Mean-reversion for ranging markets."
    ),
    "params": {
        "period": {"type": "int", "default": 20, "min": 5, "max": 100, "label": "Band period"},
        "num_std": {"type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "label": "Band width (std devs)"},
    },
}
