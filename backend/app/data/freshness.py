"""Keep candle data fresh: top up recent candles from Binance on demand.

The initial backfill is a one-shot CLI; without a scheduler the newest candle
silently ages and every backtest quietly ends there. Render's free tier has no
cron, so instead the API tops itself up lazily: before a backtest runs,
``ensure_fresh`` checks how old the newest stored candle is and, if it's stale,
pulls the missing tail from Binance (``backfill`` upserts, so overlap is safe).

Failures are logged and swallowed — serving a backtest on slightly stale data
beats failing the request because Binance was unreachable.
"""

import logging
import threading
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.data.backfill import backfill
from app.db import SessionLocal
from app.models import Candle

logger = logging.getLogger("backtestlab.freshness")

# How long an interval's newest candle may lag before we top up: two periods,
# so a normally-progressing series (whose last candle is always < 1 period old)
# never triggers a fetch.
_INTERVAL_STALENESS: dict[str, timedelta] = {
    "1h": timedelta(hours=2),
    "1d": timedelta(days=2),
}

# Don't re-check a (symbol, interval) more often than this — one Binance
# round-trip per pair per window at most, even under request bursts.
_CHECK_EVERY_SECONDS = 15 * 60

_lock = threading.Lock()
_last_check: dict[tuple[str, str], float] = {}


def ensure_fresh(symbol: str, interval: str) -> None:
    """Top up (symbol, interval) from Binance if its newest candle is stale."""
    threshold = _INTERVAL_STALENESS.get(interval)
    if threshold is None:  # unknown interval — nothing sensible to fetch
        return

    key = (symbol, interval)
    now_mono = time.monotonic()
    with _lock:
        last = _last_check.get(key)
        if last is not None and now_mono - last < _CHECK_EVERY_SECONDS:
            return
        # Claim the slot before doing the work so concurrent requests skip out
        # instead of piling onto Binance; a failure is retried next window.
        _last_check[key] = now_mono

    try:
        with SessionLocal() as db:
            latest = db.scalar(
                select(func.max(Candle.open_time)).where(
                    Candle.symbol == symbol, Candle.interval == interval
                )
            )
        if latest is None:
            # Never backfilled — that's the CLI's job, not a lazy top-up's.
            return
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=UTC)

        now = datetime.now(tz=UTC)
        if now - latest <= threshold:
            return

        logger.info(
            "Candles for %s %s stale (newest %s) — topping up from Binance.",
            symbol,
            interval,
            latest.isoformat(),
        )
        backfill(symbol, interval, start=latest, end=now)
    except Exception:  # noqa: BLE001 - stale data beats a failed request
        logger.exception("Candle top-up failed for %s %s", symbol, interval)
