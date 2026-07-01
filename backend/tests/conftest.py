"""Pytest fixtures for the BacktestLab backend.

Strategy: point everything at an **isolated test database** before importing the
app. Because ``DATABASE_URL`` is read at import time by both ``get_db`` and the
engine's direct ``SessionLocal`` (used to load candles), setting it here makes
the whole app — endpoints *and* the backtest engine — use the test DB. No
dependency overrides or live backfilled data required: we seed synthetic
candles ourselves so the suite is fully self-contained.
"""

import math
import os
from datetime import UTC, datetime, timedelta

import psycopg
import pytest

# --- Must happen before importing any app module ---------------------------
os.environ["AUTH_DEV_MODE"] = "true"
# Don't let the /backtest rate limiter throttle the suite (all TestClient calls
# share one client IP). Rate-limit behavior is covered by a focused unit test.
os.environ["BACKTEST_RATE_LIMIT"] = "100000"
# Ensure billing is OFF by default (individual tests opt in via monkeypatch).
for _k in ("STRIPE_SECRET_KEY", "STRIPE_PRICE_PRO", "STRIPE_WEBHOOK_SECRET"):
    os.environ.pop(_k, None)

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://backtestlab:backtestlab@localhost:5432/backtestlab_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

TEST_SYMBOL = "TESTUSDT"
TEST_INTERVAL = "1d"
EMPTY_SYMBOL = "EMPTYUSDT"  # exists nowhere -> "not enough data" path


def _ensure_test_database() -> None:
    """Create the test database if it doesn't exist (idempotent)."""
    name = TEST_DATABASE_URL.rsplit("/", 1)[1]
    admin_dsn = "postgresql://backtestlab:backtestlab@localhost:5432/postgres"
    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{name}"')


_ensure_test_database()

# Now safe to import the app (binds to the test DB).
from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Candle  # noqa: E402


def _seed_candles() -> None:
    """Insert a deterministic synthetic OHLCV series for TEST_SYMBOL.

    A gentle uptrend plus a sine oscillation (period ~50 bars) so trend and
    mean-reversion strategies both find crossings to trade on.
    """
    from sqlalchemy import func, select

    with SessionLocal() as db:
        have = db.scalar(
            select(func.count()).select_from(Candle).where(Candle.symbol == TEST_SYMBOL)
        )
        if have:
            return
        start = datetime(2021, 1, 1, tzinfo=UTC)
        price = 100.0
        rows = []
        for i in range(300):
            osc = math.sin(i / 8.0) * 0.04  # ±4% wave
            close = price * (1.0 + osc) * 1.002  # slight drift up
            o, c = price, close
            hi = max(o, c) * 1.01
            lo = min(o, c) * 0.99
            rows.append(
                Candle(
                    symbol=TEST_SYMBOL,
                    interval=TEST_INTERVAL,
                    open_time=start + timedelta(days=i),
                    open=round(o, 2),
                    high=round(hi, 2),
                    low=round(lo, 2),
                    close=round(c, 2),
                    volume=1000 + i,
                )
            )
            price = close
        db.add_all(rows)
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def _setup_schema():
    """Create tables and seed candles once for the whole test session."""
    Base.metadata.create_all(engine)
    _seed_candles()
    yield


@pytest.fixture(autouse=True)
def _clean_user_tables():
    """Isolate each test: wipe users + saved_backtests (keep candles)."""
    from sqlalchemy import text

    with SessionLocal() as db:
        db.execute(text("TRUNCATE saved_backtests, users RESTART IDENTITY CASCADE"))
        db.commit()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---- helpers ----

def auth(email: str = "tester@example.com") -> dict:
    """Authorization header for a dev-token user identified by email."""
    return {"Authorization": f"Bearer dev:{email}"}


def backtest_body(**overrides) -> dict:
    """A valid /backtest (and /backtests) request body for the seeded symbol."""
    body = {
        "symbol": TEST_SYMBOL,
        "interval": TEST_INTERVAL,
        "strategy": "ma_crossover",
        "params": {"fast": 10, "slow": 30},
        "cash": 10_000,
        "fee_pct": 0.001,
        "slippage_pct": 0.0005,
    }
    body.update(overrides)
    return body
