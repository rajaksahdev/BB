"""Gap detection over stored candles.

A "gap" is a missing candle between two consecutive stored candles (delta larger
than one interval step). Crypto trades 24/7, so for hourly/daily data a healthy
series should have effectively zero gaps. Binance occasionally has maintenance
windows, so we report rather than fail.
"""

from datetime import timedelta

from sqlalchemy import select

from app.data.binance import INTERVAL_MS
from app.db import SessionLocal
from app.models import Candle


def gap_report(symbol: str, interval: str, max_examples: int = 20) -> dict:
    """Return a coverage + gap summary for one (symbol, interval)."""
    step = timedelta(milliseconds=INTERVAL_MS[interval])
    with SessionLocal() as db:
        times = (
            db.execute(
                select(Candle.open_time)
                .where(Candle.symbol == symbol, Candle.interval == interval)
                .order_by(Candle.open_time)
            )
            .scalars()
            .all()
        )

    if not times:
        return {
            "symbol": symbol,
            "interval": interval,
            "count": 0,
            "gap_segments": 0,
            "missing_candles": 0,
            "gaps": [],
        }

    gaps: list[dict] = []
    missing_total = 0
    for prev, cur in zip(times, times[1:]):
        delta = cur - prev
        if delta > step:
            missing = round(delta / step) - 1
            missing_total += missing
            if len(gaps) < max_examples:
                gaps.append(
                    {
                        "after": prev.isoformat(),
                        "before": cur.isoformat(),
                        "missing": missing,
                    }
                )

    return {
        "symbol": symbol,
        "interval": interval,
        "count": len(times),
        "first": times[0].isoformat(),
        "last": times[-1].isoformat(),
        "gap_segments": sum(1 for p, c in zip(times, times[1:]) if c - p > step),
        "missing_candles": missing_total,
        "gaps": gaps,
    }
