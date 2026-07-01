"""Grid trading (buy dips, sell rips around a moving reference price)."""

from backtesting import Strategy


class Grid(Strategy):
    # Grid step as a fraction of price (5% = 0.05).
    spacing = 0.05
    # Fraction of equity bought at each downward grid level.
    order_size = 0.1

    def init(self):
        self._ref = None

    def next(self):
        price = float(self.data.Close[-1])
        if self._ref is None:
            self._ref = price
            return

        if price <= self._ref * (1 - self.spacing):
            # Price dropped a grid step -> accumulate.
            self.buy(size=float(self.order_size))
            self._ref = price
        elif price >= self._ref * (1 + self.spacing):
            # Price rose a grid step -> take profit on the position.
            if self.position:
                self.position.close()
            self._ref = price


STRATEGY = Grid

META = {
    "key": "grid",
    "name": "Grid Trading",
    "description": (
        "Accumulate as price steps down through grid levels and take profit as "
        "it steps back up. Thrives in ranging, choppy markets."
    ),
    "params": {
        "spacing": {"type": "float", "default": 0.05, "min": 0.01, "max": 0.25, "label": "Grid spacing (fraction)"},
        "order_size": {"type": "float", "default": 0.1, "min": 0.01, "max": 0.5, "label": "Size per level (fraction)"},
    },
}
