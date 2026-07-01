"""Load OHLCV candles from Postgres into a backtesting.py-ready DataFrame.

backtesting.py requires columns named exactly Open/High/Low/Close (Volume
optional) indexed by an ascending DatetimeIndex.
"""

from datetime import datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candle

_OHLCV = ["Open", "High", "Low", "Close", "Volume"]


def load_ohlcv(
    db: Session,
    symbol: str,
    interval: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> pd.DataFrame:
    """Return an OHLCV DataFrame for (symbol, interval) over [start, end]."""
    query = (
        select(
            Candle.open_time,
            Candle.open,
            Candle.high,
            Candle.low,
            Candle.close,
            Candle.volume,
        )
        .where(Candle.symbol == symbol, Candle.interval == interval)
        .order_by(Candle.open_time)
    )
    if start is not None:
        query = query.where(Candle.open_time >= start)
    if end is not None:
        query = query.where(Candle.open_time <= end)

    rows = db.execute(query).all()
    if not rows:
        return pd.DataFrame(columns=_OHLCV)

    df = pd.DataFrame(rows, columns=["open_time", *_OHLCV])
    df = df.set_index("open_time")
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    for col in _OHLCV:
        df[col] = df[col].astype(float)
    return df
