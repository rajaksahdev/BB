import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatsPanel from "./StatsPanel";
import type { BacktestResult } from "../api";

const RESULT: BacktestResult = {
  request: {
    symbol: "BTCUSDT",
    interval: "1d",
    strategy: "ma_crossover",
    params: { fast: 10, slow: 30 },
    start: "2021-01-01T00:00:00",
    end: "2023-12-31T00:00:00",
  },
  stats: {
    return_pct: 96.4,
    buy_hold_return_pct: 106.0,
    win_rate_pct: 31.6,
    max_drawdown_pct: -38.0,
    sharpe_ratio: 0.59,
    trade_count: 19,
    exposure_time_pct: 54.9,
    starting_cash: 10000,
    final_equity: 19640,
    sortino_ratio: 1.12,
    calmar_ratio: 0.66,
    cagr_pct: 25.3,
    volatility_ann_pct: 41.7,
    profit_factor: 1.85,
    avg_trade_pct: 3.6,
    best_trade_pct: 42.1,
    worst_trade_pct: -12.4,
  },
  equity_curve: [],
  trades: [],
  assumptions: {
    fee_pct: 0.001,
    slippage_pct: 0.0005,
    position: "long-only",
    note: "modeled",
  },
  disclaimer: "Not financial advice.",
};

describe("StatsPanel", () => {
  it("renders the headline stats", () => {
    render(<StatsPanel result={RESULT} />);
    expect(screen.getByText("+96.40%")).toBeInTheDocument(); // return
    expect(screen.getByText("19")).toBeInTheDocument(); // trades
    expect(screen.getByText("0.59")).toBeInTheDocument(); // sharpe
  });

  it("shows the modeled fee + slippage assumptions", () => {
    render(<StatsPanel result={RESULT} />);
    expect(screen.getByText(/0\.10% fee/)).toBeInTheDocument();
    expect(screen.getByText(/0\.05% slippage/)).toBeInTheDocument();
  });

  it("renders the extended metrics when present", () => {
    render(<StatsPanel result={RESULT} />);
    expect(screen.getByText("More metrics")).toBeInTheDocument();
    expect(screen.getByText("1.85")).toBeInTheDocument(); // profit factor
    expect(screen.getByText("+25.30%")).toBeInTheDocument(); // CAGR
  });

  it("hides the extended section for saved rows that predate it", () => {
    const legacy = { ...RESULT, stats: { ...RESULT.stats, cagr_pct: undefined } };
    render(<StatsPanel result={legacy} />);
    expect(screen.queryByText("More metrics")).not.toBeInTheDocument();
  });

  it("renders an em-dash for missing (null) metrics", () => {
    const noWin = { ...RESULT, stats: { ...RESULT.stats, win_rate_pct: null } };
    render(<StatsPanel result={noWin} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
