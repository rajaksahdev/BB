"""Honesty guardrails on the engine itself.

1. Next-bar execution: orders must fill at the NEXT bar's open, never at the
   signal bar's close (look-ahead bias) — the core trust property of the app.
2. Forced end-of-data exits: positions closed only because the data window
   ended are labeled and excluded from trade-quality stats (win rate etc.).
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.db import SessionLocal
from app.models import Candle
from tests.conftest import backtest_body

NEXTBAR_SYMBOL = "NEXTBARUSDT"


@pytest.fixture(scope="module", autouse=True)
def _seed_nextbar_candles():
    """A deterministic V-shape series: 30 falling bars then 30 rising bars.

    Every bar's open is the previous close, so each open is unique and a fill
    price identifies exactly which bar (and which side of it) filled the order.
    """
    from sqlalchemy import func, select

    with SessionLocal() as db:
        have = db.scalar(
            select(func.count()).select_from(Candle).where(Candle.symbol == NEXTBAR_SYMBOL)
        )
        if have:
            return
        start = datetime(2022, 1, 1, tzinfo=UTC)
        closes = [200.0 - 2 * i for i in range(30)] + [145.0 + 3 * i for i in range(30)]
        rows = []
        prev_close = closes[0]
        for i, close in enumerate(closes):
            o = prev_close
            rows.append(
                Candle(
                    symbol=NEXTBAR_SYMBOL,
                    interval="1d",
                    open_time=start + timedelta(days=i),
                    open=o,
                    high=max(o, close) * 1.01,
                    low=min(o, close) * 0.99,
                    close=close,
                    volume=1000,
                )
            )
            prev_close = close
        db.add_all(rows)
        db.commit()


def _sma(vals, n):
    return [
        sum(vals[i - n + 1 : i + 1]) / n if i >= n - 1 else None for i in range(len(vals))
    ]


def test_orders_fill_at_next_bar_open(client):
    """The first MA-crossover buy must fill at the open of the bar AFTER the
    signal bar — with zero fee/slippage, at exactly that open price."""
    r = client.post(
        "/backtest",
        json=backtest_body(
            symbol=NEXTBAR_SYMBOL,
            params={"fast": 2, "slow": 5},
            fee_pct=0.0,
            slippage_pct=0.0,
        ),
    )
    assert r.status_code == 200, r.text
    trades = r.json()["trades"]
    assert trades, "expected at least one trade on the V-shape fixture"
    first = min(trades, key=lambda t: t["entry_time"])

    # Recompute the signal bar independently: first bar where SMA2 crosses
    # strictly above SMA5 (same crossover semantics as backtesting.lib).
    closes = [200.0 - 2 * i for i in range(30)] + [145.0 + 3 * i for i in range(30)]
    opens = [closes[0]] + closes[:-1]
    sma2, sma3 = _sma(closes, 2), _sma(closes, 5)
    signal_bar = next(
        i
        for i in range(1, len(closes))
        if None not in (sma2[i], sma3[i], sma2[i - 1], sma3[i - 1])
        and sma2[i - 1] <= sma3[i - 1]
        and sma2[i] > sma3[i]
    )

    start = datetime(2022, 1, 1)
    expected_entry_time = (start + timedelta(days=signal_bar + 1)).isoformat()
    assert first["entry_time"] == expected_entry_time, (
        "order filled on the wrong bar — look-ahead bias regression"
    )
    assert first["entry_price"] == pytest.approx(opens[signal_bar + 1]), (
        "order filled at the signal bar's close instead of the next bar's open"
    )


def test_dca_forced_exits_are_labeled_and_excluded(client):
    """DCA never sells: its only 'exits' are the end-of-data force-close.
    Those must be labeled, counted, and excluded from win-rate-style stats."""
    r = client.post("/backtest", json=backtest_body(strategy="dca", params={}))
    assert r.status_code == 200, r.text
    body = r.json()
    stats = body["stats"]

    assert stats["forced_exit_count"] >= 1
    assert stats["forced_exit_count"] == stats["trade_count"]
    # No strategy-decided exits -> trade-quality stats are honest nulls.
    for key in ("win_rate_pct", "profit_factor", "avg_trade_pct", "best_trade_pct"):
        assert stats[key] is None, f"{key} should be null when all exits are forced"
    assert all(t["exit_reason"] == "end_of_data" for t in body["trades"])


def test_signal_exits_keep_trade_stats(client):
    """A strategy with real exits still reports win-rate-style stats, and its
    signal trades are labeled as such."""
    r = client.post("/backtest", json=backtest_body())  # ma_crossover 10/30
    assert r.status_code == 200, r.text
    body = r.json()
    signal_trades = [t for t in body["trades"] if t["exit_reason"] == "signal"]
    assert signal_trades, "seeded wave data should produce signal exits"
    assert body["stats"]["win_rate_pct"] is not None
