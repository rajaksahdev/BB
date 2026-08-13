"""Pre-deploy hardening: rate limiting, input bounds, body-size guard."""

import pytest
from fastapi import HTTPException, Request

from app.ratelimit import RateLimiter
from tests.conftest import backtest_body


def _fake_request(ip: str = "1.2.3.4") -> Request:
    """Minimal ASGI scope so RateLimiter can read the client IP."""
    scope = {
        "type": "http",
        "headers": [],
        "client": (ip, 12345),
    }
    return Request(scope)


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit=3, window=60.0)
    req = _fake_request()
    for _ in range(3):
        limiter(req)  # first 3 allowed
    with pytest.raises(HTTPException) as exc:
        limiter(req)  # 4th rejected
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_engine_busy_returns_429(client, monkeypatch):
    """When every engine slot is taken, /backtest answers 429 + Retry-After
    instead of queueing unboundedly on the GIL."""
    from app.backtesting import engine

    class Exhausted:
        def acquire(self, timeout=None):
            return False

        def release(self):  # pragma: no cover - never acquired
            pass

    monkeypatch.setattr(engine, "_run_slots", Exhausted())
    r = client.post("/backtest", json=backtest_body())
    assert r.status_code == 429
    assert "retry" in r.json()["detail"].lower()
    assert "Retry-After" in r.headers


def test_rate_limiter_is_per_ip():
    limiter = RateLimiter(limit=1, window=60.0)
    limiter(_fake_request("10.0.0.1"))
    # A different IP has its own budget — must not be blocked.
    limiter(_fake_request("10.0.0.2"))


def _forwarded_request(xff: str) -> Request:
    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", xff.encode())],
        "client": ("10.0.0.5", 999),  # proxy IP
    }
    return Request(scope)


def test_rate_limiter_prefers_forwarded_for():
    """Behind a proxy the real client is the LAST X-Forwarded-For entry (the
    one appended by the trusted proxy in front of us)."""
    limiter = RateLimiter(limit=1, window=60.0)
    limiter(_forwarded_request("203.0.113.9"))
    with pytest.raises(HTTPException):
        limiter(_forwarded_request("203.0.113.9"))  # same real client -> blocked


def test_rate_limiter_ignores_spoofed_forwarded_prefix():
    """A client forging X-Forwarded-For prefixes must not mint fresh buckets:
    proxies append, so everything before the last entry is attacker-controlled."""
    limiter = RateLimiter(limit=1, window=60.0)
    limiter(_forwarded_request("6.6.6.1, 203.0.113.9"))
    with pytest.raises(HTTPException):
        # Different forged prefix, same real client appended by the proxy.
        limiter(_forwarded_request("6.6.6.2, 203.0.113.9"))


def test_backtest_rejects_reversed_date_range(client):
    body = backtest_body()
    body["start"] = "2021-01-01T00:00:00Z"
    body["end"] = "2020-01-01T00:00:00Z"  # before start
    r = client.post("/backtest", json=body)
    assert r.status_code == 422


def test_backtest_rejects_absurd_date_range(client):
    body = backtest_body()
    body["start"] = "1900-01-01T00:00:00Z"
    body["end"] = "2100-01-01T00:00:00Z"  # ~200 years
    r = client.post("/backtest", json=body)
    assert r.status_code == 422


def test_backtest_rejects_nan_param(client):
    """NaN compares False against every bound, so it must be rejected outright
    — not slip past min/max validation into the engine."""
    r = client.post("/backtest", json=backtest_body(params={"fast": 10, "slow": "NaN"}))
    assert r.status_code == 400
    assert "number" in r.json()["detail"]


def test_backtest_rejects_non_numeric_param(client):
    # A list/dict param must be a clean 400, not a TypeError -> 500.
    r = client.post("/backtest", json=backtest_body(params={"fast": [10], "slow": 30}))
    assert r.status_code == 400
    assert "number" in r.json()["detail"]


def test_optimize_rejects_nan_fixed_param(client):
    body = {
        "symbol": backtest_body()["symbol"],
        "interval": backtest_body()["interval"],
        "strategy": "ma_crossover",
        "param_ranges": {"fast": {"min": 5, "max": 20, "step": 5}},
        "params": {"slow": "NaN"},
    }
    r = client.post("/optimize", json=body)
    assert r.status_code == 400
    assert "number" in r.json()["detail"]


def test_optimize_rejects_nan_sweep_range(client):
    body = {
        "symbol": backtest_body()["symbol"],
        "interval": backtest_body()["interval"],
        "strategy": "ma_crossover",
        "param_ranges": {"fast": {"min": "NaN", "max": 20}},
    }
    r = client.post("/optimize", json=body)
    assert r.status_code == 422  # rejected at the schema (allow_inf_nan=False)


def test_dev_token_rejected_in_production(client, monkeypatch):
    """Fail-safe: even with AUTH_DEV_MODE=true, a production deploy must never
    accept forgeable dev tokens."""
    from app import auth as auth_module

    monkeypatch.setattr(auth_module.settings, "app_env", "production")
    r = client.get("/me", headers={"Authorization": "Bearer dev:evil@example.com"})
    assert r.status_code in (401, 503)  # anything but an authenticated 200


def test_backtest_rejects_oversized_body(client):
    # A single field with a ~100KB value: exceeds the 64KB cap, so the body-size
    # middleware rejects it before any field validation runs.
    body = backtest_body()
    body["params"] = {"pad": "x" * 100_000}
    r = client.post("/backtest", json=body)
    assert r.status_code == 413
