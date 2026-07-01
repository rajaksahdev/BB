"""OHLCV candle storage.

One row per (symbol, interval, open_time). The unique constraint makes the
Phase 1 data fetcher idempotent: re-running a backfill upserts instead of
duplicating. Prices use NUMERIC for exactness (never float for money).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Candle(Base):
    __tablename__ = "candles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # e.g. "BTCUSDT". Binance symbol notation.
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    # e.g. "1h", "1d".
    interval: Mapped[str] = mapped_column(String(5), nullable=False)

    # Candle open time (UTC). Binance returns ms epoch; we store as timestamptz.
    open_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    open: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(30, 8), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "symbol", "interval", "open_time", name="uq_candle_symbol_interval_time"
        ),
        # Range scans for a backtest are (symbol, interval) filtered, time-ordered.
        Index("ix_candle_lookup", "symbol", "interval", "open_time"),
    )
