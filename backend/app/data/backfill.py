"""Backfill OHLCV candles from Binance into Postgres.

Idempotent: uses INSERT ... ON CONFLICT (symbol, interval, open_time) DO UPDATE,
so re-running a backfill never duplicates rows and refreshes the trailing
(possibly partial) candle in place.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.dialects.postgresql import insert

from app.data.binance import (
    _CLOSE,
    _HIGH,
    _LOW,
    _OPEN,
    _OPEN_TIME,
    _VOLUME,
    fetch_klines,
)
from app.db import SessionLocal
from app.models import Candle

logger = logging.getLogger("backtestlab.backfill")

_BATCH = 1000


def _to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def _row_to_values(symbol: str, interval: str, row: list) -> dict:
    return {
        "symbol": symbol,
        "interval": interval,
        "open_time": _to_dt(row[_OPEN_TIME]),
        "open": row[_OPEN],
        "high": row[_HIGH],
        "low": row[_LOW],
        "close": row[_CLOSE],
        "volume": row[_VOLUME],
    }


def _upsert(db, rows: list[dict]) -> int:
    """Upsert a batch; returns number of rows written."""
    stmt = insert(Candle).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_candle_symbol_interval_time",
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
        },
    )
    db.execute(stmt)
    return len(rows)


def backfill(
    symbol: str, interval: str, start: datetime, end: datetime
) -> dict:
    """Backfill one (symbol, interval) over [start, end]. Returns a summary."""
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)

    fetched = 0
    written = 0
    buffer: list[dict] = []

    logger.info("Backfilling %s %s %s -> %s", symbol, interval, start, end)
    with SessionLocal() as db:
        for row in fetch_klines(symbol, interval, start_ms, end_ms):
            buffer.append(_row_to_values(symbol, interval, row))
            fetched += 1
            if len(buffer) >= _BATCH:
                written += _upsert(db, buffer)
                buffer = []
        if buffer:
            written += _upsert(db, buffer)
        db.commit()

    summary = {
        "symbol": symbol,
        "interval": interval,
        "fetched": fetched,
        "written": written,
    }
    logger.info("Done %s", summary)
    return summary
