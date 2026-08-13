"""Phase 7a gate: the parameter-sweep optimizer (POST /optimize)."""

import pytest

from tests.conftest import EMPTY_SYMBOL, TEST_INTERVAL, TEST_SYMBOL


def optimize_body(**overrides) -> dict:
    body = {
        "symbol": TEST_SYMBOL,
        "interval": TEST_INTERVAL,
        "strategy": "ma_crossover",
        "param_ranges": {
            "fast": {"min": 5, "max": 20, "step": 5},
            "slow": {"min": 20, "max": 50, "step": 10},
        },
        "metric": "return_pct",
        "fee_pct": 0.001,
        "slippage_pct": 0.0005,
    }
    body.update(overrides)
    return body


def test_optimize_returns_ranked_grid(client):
    r = client.post("/optimize", json=optimize_body())
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["swept"] == ["fast", "slow"]
    assert body["grid"]["fast"] == [5, 10, 15, 20]
    assert body["grid"]["slow"] == [20, 30, 40, 50]

    # fast=20/slow=20 is invalid (fast must be < slow) — skipped, not an error.
    assert body["combos_skipped"] >= 1
    assert body["combos_run"] + body["combos_skipped"] == 16

    results = body["results"]
    assert len(results) == body["combos_run"]
    for row in results:
        assert set(row["params"]) == {"fast", "slow"}
        for key in ("return_pct", "sharpe_ratio", "max_drawdown_pct",
                    "win_rate_pct", "trade_count"):
            assert key in row

    # Ranked best-first by the requested metric (Nones, if any, sort last).
    metric_vals = [row["return_pct"] for row in results if row["return_pct"] is not None]
    assert metric_vals == sorted(metric_vals, reverse=True)

    # Best echoes the top row and includes runnable full params.
    assert body["best"]["params"] == results[0]["params"]
    full = body["best"]["full_params"]
    assert full["fast"] == results[0]["params"]["fast"]
    assert full["slow"] == results[0]["params"]["slow"]

    # Honesty guardrails carry over from the engine.
    assert body["assumptions"]["fee_pct"] == 0.001
    assert "not financial advice" in body["disclaimer"].lower()


def test_optimize_best_matches_single_backtest(client):
    r = client.post("/optimize", json=optimize_body())
    assert r.status_code == 200
    best = r.json()["best"]

    single = client.post(
        "/backtest",
        json={
            "symbol": TEST_SYMBOL,
            "interval": TEST_INTERVAL,
            "strategy": "ma_crossover",
            "params": best["full_params"],
            "cash": 10_000,
            "fee_pct": 0.001,
            "slippage_pct": 0.0005,
        },
    )
    assert single.status_code == 200
    assert single.json()["stats"]["return_pct"] == pytest.approx(
        best["return_pct"], rel=1e-6
    )


def test_optimize_single_param_sweep(client):
    r = client.post(
        "/optimize",
        json=optimize_body(param_ranges={"fast": {"min": 5, "max": 15, "step": 5}},
                           params={"slow": 40}),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["swept"] == ["fast"]
    assert body["request"]["fixed_params"]["slow"] == 40
    assert body["combos_run"] == 3


def test_optimize_metric_sharpe(client):
    r = client.post("/optimize", json=optimize_body(metric="sharpe_ratio"))
    assert r.status_code == 200
    results = r.json()["results"]
    vals = [row["sharpe_ratio"] for row in results if row["sharpe_ratio"] is not None]
    assert vals == sorted(vals, reverse=True)


def test_optimize_combo_cap_is_400(client, monkeypatch):
    from app.api import backtest as backtest_api

    monkeypatch.setattr(backtest_api._settings, "optimize_max_combos", 4)
    r = client.post("/optimize", json=optimize_body())  # 16 combos > cap of 4
    assert r.status_code == 400
    assert "combinations" in r.json()["detail"].lower()


def test_optimize_three_swept_params_is_422(client):
    # Schema caps the sweep at 2 params (table/heatmap is the product surface).
    r = client.post(
        "/optimize",
        json=optimize_body(
            strategy="bollinger",
            param_ranges={
                "a": {"min": 1, "max": 2},
                "b": {"min": 1, "max": 2},
                "c": {"min": 1, "max": 2},
            },
        ),
    )
    assert r.status_code == 422


def test_optimize_unknown_param_is_400(client):
    r = client.post(
        "/optimize", json=optimize_body(param_ranges={"bogus": {"min": 1, "max": 5}})
    )
    assert r.status_code == 400
    assert "bogus" in r.json()["detail"].lower()


def test_optimize_range_outside_bounds_is_400(client):
    # ma_crossover 'fast' is bounded to [2, 100].
    r = client.post(
        "/optimize",
        json=optimize_body(param_ranges={"fast": {"min": 1, "max": 500, "step": 50}}),
    )
    assert r.status_code == 400
    assert "within" in r.json()["detail"].lower()


def test_optimize_all_combos_invalid_is_400(client):
    # Every fast in [60..80] >= every slow in [10..20] -> whole grid invalid.
    r = client.post(
        "/optimize",
        json=optimize_body(
            param_ranges={
                "fast": {"min": 60, "max": 80, "step": 10},
                "slow": {"min": 10, "max": 20, "step": 5},
            }
        ),
    )
    assert r.status_code == 400
    assert "invalid" in r.json()["detail"].lower()


def test_optimize_insufficient_data_is_400(client):
    r = client.post("/optimize", json=optimize_body(symbol=EMPTY_SYMBOL))
    assert r.status_code == 400
    assert "data" in r.json()["detail"].lower()
