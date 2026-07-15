"""Phase 0 + Phase 2 gates: health, strategy catalog, and the backtest engine."""

import pytest

from tests.conftest import EMPTY_SYMBOL, backtest_body

STRATEGY_KEYS = ["ma_crossover", "macd", "rsi_reversion", "bollinger", "dca", "grid"]


def test_health_reports_db_up(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"


def test_strategies_catalog(client):
    r = client.get("/strategies")
    assert r.status_code == 200
    strategies = r.json()
    keys = {s["key"] for s in strategies}
    assert keys == set(STRATEGY_KEYS)
    for s in strategies:
        assert s["name"] and s["description"]
        assert isinstance(s["params"], dict)  # powers the UI form


def test_backtest_returns_stats_curve_and_disclaimer(client):
    r = client.post("/backtest", json=backtest_body())
    assert r.status_code == 200
    body = r.json()

    stats = body["stats"]
    for key in (
        "return_pct",
        "buy_hold_return_pct",
        "win_rate_pct",
        "max_drawdown_pct",
        "sharpe_ratio",
        "sortino_ratio",
        "cagr_pct",
        "profit_factor",
        "best_trade_pct",
        "worst_trade_pct",
        "trade_count",
    ):
        assert key in stats

    assert len(body["equity_curve"]) > 1
    assert body["equity_curve"][0].keys() >= {"time", "equity"}
    # The curve's final point matches the reported final equity (no
    # downsampling drop-off).
    assert body["equity_curve"][-1]["equity"] == pytest.approx(
        stats["final_equity"], rel=0.01
    )
    # Honest-backtest guardrail: fees + slippage modeled and disclosed.
    assert body["assumptions"]["fee_pct"] == 0.001
    assert body["assumptions"]["slippage_pct"] == 0.0005
    assert "not financial advice" in body["disclaimer"].lower()


@pytest.mark.parametrize("strategy", STRATEGY_KEYS)
def test_every_strategy_runs(client, strategy):
    # Empty params -> engine fills defaults; every strategy should produce a run.
    r = client.post("/backtest", json=backtest_body(strategy=strategy, params={}))
    assert r.status_code == 200, r.text
    stats = r.json()["stats"]
    assert stats["trade_count"] >= 0
    assert isinstance(stats["starting_cash"], (int, float))


def test_unknown_param_is_400(client):
    r = client.post("/backtest", json=backtest_body(params={"bogus": 5}))
    assert r.status_code == 400
    assert "bogus" in r.json()["detail"].lower()


def test_unknown_strategy_is_400(client):
    r = client.post("/backtest", json=backtest_body(strategy="does_not_exist"))
    assert r.status_code == 400


def test_inverted_ma_periods_is_400(client):
    # fast must stay below slow or the crossover logic silently inverts.
    r = client.post("/backtest", json=backtest_body(params={"fast": 80, "slow": 20}))
    assert r.status_code == 400
    assert "fast" in r.json()["detail"].lower()


def test_param_out_of_range_is_400(client):
    # ma_crossover 'fast' max is 100.
    r = client.post("/backtest", json=backtest_body(params={"fast": 9999, "slow": 30}))
    assert r.status_code == 400


def test_insufficient_data_is_400(client):
    r = client.post("/backtest", json=backtest_body(symbol=EMPTY_SYMBOL))
    assert r.status_code == 400
    assert "data" in r.json()["detail"].lower()
