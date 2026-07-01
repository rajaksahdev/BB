"""Lightweight in-process rate limiting.

The public ``POST /backtest`` endpoint runs a full simulation synchronously and
is unauthenticated, so without a guard a single client can pin the CPU and take
the service down (a real risk on small/free hosting tiers). This module provides
a fixed-window limiter keyed by client IP — no external store, no new
dependency. It resets on restart and is per-process, which is sufficient for the
single-instance deployment; move to Redis-backed limiting if we scale out.

Behind a proxy (Render/Railway) the real client IP is the first hop of the
``X-Forwarded-For`` header, not ``request.client.host`` (that is the proxy).
"""

import time
from collections import deque

from fastapi import HTTPException, Request


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # First entry is the original client; the rest are proxies.
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Fixed-window limiter: at most ``limit`` hits per ``window`` seconds/IP.

    Usable as a FastAPI dependency::

        limiter = RateLimiter(limit=20, window=60)

        @router.post("/backtest", dependencies=[Depends(limiter)])
        def post_backtest(...): ...
    """

    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = {}

    def __call__(self, request: Request) -> None:
        ip = _client_ip(request)
        now = time.monotonic()
        bucket = self._hits.setdefault(ip, deque())

        # Drop timestamps older than the window.
        cutoff = now - self.window
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= self.limit:
            retry_after = max(1, int(self.window - (now - bucket[0])))
            raise HTTPException(
                status_code=429,
                detail=(
                    "Rate limit exceeded — too many backtests. "
                    f"Try again in {retry_after}s."
                ),
                headers={"Retry-After": str(retry_after)},
            )
        bucket.append(now)

        # Opportunistic cleanup so idle IPs don't leak memory forever.
        if len(self._hits) > 10_000:
            for key in [k for k, v in self._hits.items() if not v]:
                del self._hits[key]
