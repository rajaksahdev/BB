"""Binance public REST client for historical klines (candles).

No API key needed for historical klines. We paginate forward in 1000-candle
pages and retry transient failures (network errors, 429 rate-limit, 5xx) with
exponential backoff. This is the only place that talks to Binance.
"""

import logging
import time
from collections.abc import Iterator

import httpx

from app.config import get_settings

logger = logging.getLogger("backtestlab.binance")
settings = get_settings()

# Supported intervals -> duration in milliseconds.
INTERVAL_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

# Binance kline array indices.
_OPEN_TIME, _OPEN, _HIGH, _LOW, _CLOSE, _VOLUME = 0, 1, 2, 3, 4, 5

_MAX_LIMIT = 1000
_MAX_RETRIES = 5


class BinanceError(Exception):
    """Raised when Binance cannot be reached after retries, or returns an error."""


def _request_with_retry(
    client: httpx.Client, path: str, params: dict
) -> list:
    """GET with exponential backoff on transient failures."""
    delay = 1.0
    last_err: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = client.get(path, params=params, timeout=20.0)
            if resp.status_code == 200:
                return resp.json()
            # Rate-limited (429) or IP-banned (418): respect Retry-After.
            if resp.status_code in (429, 418):
                wait = float(resp.headers.get("Retry-After", delay))
                logger.warning("Binance %s; backing off %.1fs", resp.status_code, wait)
                time.sleep(wait)
                delay = min(delay * 2, 60)
                continue
            if 500 <= resp.status_code < 600:
                logger.warning("Binance %s; retry %d", resp.status_code, attempt)
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            # 4xx other than rate-limit are not retryable.
            raise BinanceError(
                f"Binance HTTP {resp.status_code}: {resp.text[:200]}"
            )
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            last_err = exc
            logger.warning("Network error (try %d/%d): %s", attempt, _MAX_RETRIES, exc)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise BinanceError(
        f"Binance unreachable after {_MAX_RETRIES} retries: {last_err}"
    )


def fetch_klines(
    symbol: str, interval: str, start_ms: int, end_ms: int
) -> Iterator[list]:
    """Yield raw kline rows for [start_ms, end_ms], paginating forward.

    Each yielded row is Binance's array form; callers read indices via the
    module-level _OPEN/_HIGH/... constants (see backfill.py).
    """
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    step = INTERVAL_MS[interval]
    cursor = start_ms
    with httpx.Client(base_url=settings.binance_base_url) as client:
        while cursor <= end_ms:
            page = _request_with_retry(
                client,
                "/api/v3/klines",
                {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": _MAX_LIMIT,
                },
            )
            if not page:
                break
            for row in page:
                yield row
            # Advance past the last candle we received.
            cursor = page[-1][_OPEN_TIME] + step
            if len(page) < _MAX_LIMIT:
                break
