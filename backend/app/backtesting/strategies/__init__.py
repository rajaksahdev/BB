"""Strategy registry.

Each strategy lives in its own module exposing ``STRATEGY`` (the backtesting.py
Strategy class) and ``META`` (name, description, tunable params for the UI).
Adding a strategy = adding one file + listing it here.
"""

from app.backtesting.strategies import (
    bollinger,
    dca,
    grid,
    ma_crossover,
    macd,
    rsi_reversion,
)

_MODULES = [ma_crossover, macd, rsi_reversion, bollinger, dca, grid]

STRATEGIES: dict[str, dict] = {
    mod.META["key"]: {
        "class": mod.STRATEGY,
        "meta": mod.META,
        # Optional cross-param check, e.g. fast < slow (single-param bounds
        # are enforced generically by the engine).
        "validate": getattr(mod, "validate", None),
    }
    for mod in _MODULES
}

__all__ = ["STRATEGIES"]
