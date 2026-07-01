"""Strategy registry.

Each strategy lives in its own module exposing ``STRATEGY`` (the backtesting.py
Strategy class) and ``META`` (name, description, tunable params for the UI).
Adding a strategy = adding one file + listing it here.
"""

from app.backtesting.strategies import dca, grid, ma_crossover, rsi_reversion

_MODULES = [ma_crossover, rsi_reversion, dca, grid]

STRATEGIES: dict[str, dict] = {
    mod.META["key"]: {"class": mod.STRATEGY, "meta": mod.META} for mod in _MODULES
}

__all__ = ["STRATEGIES"]
