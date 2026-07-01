"""Dollar-Cost Averaging (periodic accumulation, buy-and-hold)."""

from backtesting import Strategy


class Dca(Strategy):
    # Buy every `period` bars (e.g. 7 daily bars ~= weekly).
    period = 7
    # Fraction of current equity deployed at each buy.
    allocation = 0.05

    def init(self):
        pass

    def next(self):
        bar = len(self.data) - 1
        if bar % int(self.period) == 0:
            # Deploy a fixed fraction of equity into the asset; never sell.
            if self.equity > 0:
                self.buy(size=float(self.allocation))


STRATEGY = Dca

META = {
    "key": "dca",
    "name": "Dollar-Cost Averaging",
    "description": (
        "Buy a fixed fraction of your portfolio on a regular schedule and hold. "
        "The simplest, most popular passive strategy."
    ),
    "params": {
        "period": {"type": "int", "default": 7, "min": 1, "max": 90, "label": "Buy every N bars"},
        "allocation": {"type": "float", "default": 0.05, "min": 0.01, "max": 0.5, "label": "Fraction per buy"},
    },
}
