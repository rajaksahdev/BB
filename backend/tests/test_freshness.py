"""Lazy candle top-up (app.data.freshness) + the /symbols catalog endpoint."""

from datetime import UTC, datetime, timedelta

import pytest

from app.data import freshness
from tests.conftest import TEST_INTERVAL, TEST_SYMBOL


@pytest.fixture(autouse=True)
def _reset_throttle():
    """Each test starts with a clean per-pair check throttle."""
    freshness._last_check.clear()
    freshness._inflight.clear()
    yield
    freshness._last_check.clear()
    freshness._inflight.clear()


@pytest.fixture
def backfill_calls(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(
        freshness, "backfill", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    return calls


def test_stale_pair_triggers_topup(backfill_calls):
    # Seeded TESTUSDT candles end in 2021 — far beyond the 2-day threshold.
    freshness.ensure_fresh(TEST_SYMBOL, TEST_INTERVAL)
    assert len(backfill_calls) == 1
    args, kwargs = backfill_calls[0]
    assert args == (TEST_SYMBOL, TEST_INTERVAL)
    assert kwargs["start"].year == 2021  # resumes from the newest stored candle
    assert kwargs["end"] > kwargs["start"]


def test_throttle_skips_second_check(backfill_calls):
    freshness.ensure_fresh(TEST_SYMBOL, TEST_INTERVAL)
    freshness.ensure_fresh(TEST_SYMBOL, TEST_INTERVAL)
    assert len(backfill_calls) == 1


def test_fresh_pair_does_not_fetch(backfill_calls):
    from app.db import SessionLocal
    from app.models import Candle

    symbol = "FRESHUSDT"
    with SessionLocal() as db:
        db.add(
            Candle(
                symbol=symbol,
                interval="1d",
                open_time=datetime.now(tz=UTC) - timedelta(hours=1),
                open=1, high=1, low=1, close=1, volume=1,
            )
        )
        db.commit()
    try:
        freshness.ensure_fresh(symbol, "1d")
        assert backfill_calls == []
    finally:
        with SessionLocal() as db:
            db.query(Candle).filter(Candle.symbol == symbol).delete()
            db.commit()


def test_mildly_stale_pair_tops_up_in_background(monkeypatch):
    """3 days old on a 1d interval (threshold 2d, gross bound 6d): the request
    must not block — the top-up runs on a background thread."""
    import threading

    from app.db import SessionLocal
    from app.models import Candle

    symbol = "MILDUSDT"
    with SessionLocal() as db:
        db.add(
            Candle(
                symbol=symbol,
                interval="1d",
                open_time=datetime.now(tz=UTC) - timedelta(days=3),
                open=1, high=1, low=1, close=1, volume=1,
            )
        )
        db.commit()

    fetched = threading.Event()
    calls: list[str] = []

    def fake_backfill(*args, **kwargs):
        calls.append(threading.current_thread().name)
        fetched.set()

    monkeypatch.setattr(freshness, "backfill", fake_backfill)
    try:
        freshness.ensure_fresh(symbol, "1d")
        assert fetched.wait(timeout=5), "background top-up never ran"
        assert calls[0] != threading.main_thread().name, (
            "mildly-stale top-up ran on the request thread (hot path)"
        )
    finally:
        with SessionLocal() as db:
            db.query(Candle).filter(Candle.symbol == symbol).delete()
            db.commit()


def test_never_backfilled_pair_is_left_alone(backfill_calls):
    freshness.ensure_fresh("NOSUCHUSDT", "1d")
    assert backfill_calls == []


def test_unknown_interval_is_skipped(backfill_calls):
    freshness.ensure_fresh(TEST_SYMBOL, "5m")
    assert backfill_calls == []


def test_backfill_failure_is_swallowed(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("binance down")

    monkeypatch.setattr(freshness, "backfill", boom)
    freshness.ensure_fresh(TEST_SYMBOL, TEST_INTERVAL)  # must not raise


def test_symbols_endpoint_lists_seeded_data(client):
    resp = client.get("/symbols")
    assert resp.status_code == 200
    body = resp.json()
    assert TEST_SYMBOL in body["symbols"]
    assert TEST_INTERVAL in body["intervals"]
