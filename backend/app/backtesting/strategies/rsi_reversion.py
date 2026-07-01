"""RSI Mean-Reversion (buy oversold, exit overbought, long-only)."""

from backtesting import Strategy

from app.backtesting.indicators import rsi


class RsiReversion(Strategy):
    rsi_period = 14
    oversold = 30
    overbought = 70

    def init(self):
        self.rsi = self.I(rsi, self.data.Close, self.rsi_period)

    def next(self):
        value = self.rsi[-1]
        if value != value:  # NaN guard (warm-up period)
            return
        if not self.position and value < self.oversold:
            self.buy()
        elif self.position and value > self.overbought:
            self.position.close()


STRATEGY = RsiReversion

META = {
    "key": "rsi_reversion",
    "name": "RSI Mean-Reversion",
    "description": (
        "Buy when RSI falls below the oversold threshold; exit when it rises "
        "above the overbought threshold. Bets on snap-backs."
    ),
    "params": {
        "rsi_period": {"type": "int", "default": 14, "min": 2, "max": 50, "label": "RSI period"},
        "oversold": {"type": "int", "default": 30, "min": 5, "max": 45, "label": "Oversold level"},
        "overbought": {"type": "int", "default": 70, "min": 55, "max": 95, "label": "Overbought level"},
    },
}
