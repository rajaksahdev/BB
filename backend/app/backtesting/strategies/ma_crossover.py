"""Moving-Average Crossover (trend-following, long-only)."""

from backtesting import Strategy
from backtesting.lib import crossover

from app.backtesting.indicators import sma


class MaCrossover(Strategy):
    fast = 20
    slow = 50

    def init(self):
        close = self.data.Close
        self.ma_fast = self.I(sma, close, self.fast)
        self.ma_slow = self.I(sma, close, self.slow)

    def next(self):
        if crossover(self.ma_fast, self.ma_slow):
            self.position.close()
            self.buy()
        elif crossover(self.ma_slow, self.ma_fast):
            self.position.close()


STRATEGY = MaCrossover

META = {
    "key": "ma_crossover",
    "name": "Moving Average Crossover",
    "description": (
        "Go long when the fast moving average crosses above the slow one; "
        "exit when it crosses back below. Classic trend-following."
    ),
    "params": {
        "fast": {"type": "int", "default": 20, "min": 2, "max": 100, "label": "Fast MA period"},
        "slow": {"type": "int", "default": 50, "min": 5, "max": 300, "label": "Slow MA period"},
    },
}
