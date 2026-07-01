"""Request/response schemas for the backtest API."""

from datetime import datetime, timedelta

from pydantic import BaseModel, Field, model_validator

# We only hold a few years of backfilled candles; reject absurd ranges up front
# so a request can't ask the engine to load/simulate an unbounded span.
_MAX_RANGE = timedelta(days=366 * 12)  # ~12 years, comfortably covers the data
# Strategies declare a handful of params; a huge dict is either a mistake or an
# abuse attempt. Cap it before it reaches the engine's per-key validation.
_MAX_PARAMS = 32


class BacktestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20, examples=["BTCUSDT"])
    interval: str = Field("1d", max_length=8, examples=["1d", "1h"])
    strategy: str = Field(..., min_length=1, max_length=40, examples=["ma_crossover"])
    name: str | None = Field(None, max_length=120, description="Optional label when saving.")
    params: dict = Field(default_factory=dict)
    start: datetime | None = None
    end: datetime | None = None
    cash: float = Field(10_000.0, gt=0, le=1e12)
    fee_pct: float = Field(0.001, ge=0, le=0.1)
    slippage_pct: float = Field(0.0005, ge=0, le=0.1)

    @model_validator(mode="after")
    def _check_bounds(self) -> "BacktestRequest":
        if len(self.params) > _MAX_PARAMS:
            raise ValueError(f"Too many params (max {_MAX_PARAMS}).")
        if self.start is not None and self.end is not None:
            if self.end <= self.start:
                raise ValueError("'end' must be after 'start'.")
            if self.end - self.start > _MAX_RANGE:
                raise ValueError("Requested date range is too large (max ~12 years).")
        return self
