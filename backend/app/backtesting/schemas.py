"""Request/response schemas for the backtest API."""

from datetime import datetime

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDT"])
    interval: str = Field("1d", examples=["1d", "1h"])
    strategy: str = Field(..., examples=["ma_crossover"])
    name: str | None = Field(None, max_length=120, description="Optional label when saving.")
    params: dict = Field(default_factory=dict)
    start: datetime | None = None
    end: datetime | None = None
    cash: float = Field(10_000.0, gt=0)
    fee_pct: float = Field(0.001, ge=0, le=0.1)
    slippage_pct: float = Field(0.0005, ge=0, le=0.1)
