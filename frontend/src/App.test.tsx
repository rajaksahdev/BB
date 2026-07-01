import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import * as api from "./api";
import type { BacktestResult, Me, Strategy } from "./api";

// lightweight-charts needs a real canvas; stub the chart in jsdom.
vi.mock("./components/EquityChart", () => ({
  default: () => <div data-testid="equity-chart" />,
}));

// Mock only the network calls; keep pure helpers (ApiError, SYMBOLS, resultToRequest…).
vi.mock("./api", async (importActual) => {
  const actual = await importActual<typeof import("./api")>();
  return {
    ...actual,
    setAuthToken: vi.fn(),
    getStrategies: vi.fn(),
    getBillingConfig: vi.fn(),
    getMe: vi.fn(),
    listSaved: vi.fn(),
    runBacktest: vi.fn(),
    saveBacktest: vi.fn(),
  };
});

const STRATEGY: Strategy = {
  key: "ma_crossover",
  name: "Moving Average Crossover",
  description: "Trend following.",
  params: {
    fast: { type: "int", default: 20, min: 2, max: 100, label: "Fast MA period" },
    slow: { type: "int", default: 50, min: 5, max: 300, label: "Slow MA period" },
  },
};

const RESULT: BacktestResult = {
  request: {
    symbol: "BTCUSDT",
    interval: "1d",
    strategy: "ma_crossover",
    params: { fast: 20, slow: 50 },
    start: "2021-01-01T00:00:00",
    end: "2023-12-31T00:00:00",
  },
  stats: {
    return_pct: 42.5,
    buy_hold_return_pct: 30,
    win_rate_pct: 50,
    max_drawdown_pct: -20,
    sharpe_ratio: 1.1,
    trade_count: 7,
    exposure_time_pct: 60,
    starting_cash: 10000,
    final_equity: 14250,
  },
  equity_curve: [{ time: "2021-01-01T00:00:00", equity: 10000 }],
  trades: [],
  assumptions: { fee_pct: 0.001, slippage_pct: 0.0005, position: "long-only", note: "" },
  disclaimer: "Not financial advice.",
};

const FREE_ME: Me = {
  id: "1",
  email: "free@example.com",
  tier: "free",
  usage_this_month: 5,
  monthly_limit: 5,
  remaining: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  vi.mocked(api.getStrategies).mockResolvedValue([STRATEGY]);
  vi.mocked(api.getBillingConfig).mockResolvedValue({ enabled: true });
  vi.mocked(api.getMe).mockResolvedValue(FREE_ME);
  vi.mocked(api.listSaved).mockResolvedValue([]);
  vi.mocked(api.runBacktest).mockResolvedValue(RESULT);
});

describe("App", () => {
  it("goes landing → lab → run → results", async () => {
    const user = userEvent.setup();
    render(<App />);

    // Landing first.
    expect(screen.getByText(/Open the lab/i)).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: /open the lab/i })[0]);

    // Lab loads strategies and renders the param form.
    expect(await screen.findByText("Fast MA period")).toBeInTheDocument();

    // Run a backtest -> results render.
    const form = screen.getByRole("button", { name: /run backtest/i }).closest("form")!;
    fireEvent.submit(form);

    expect(await screen.findByText("+42.50%")).toBeInTheDocument();
    expect(screen.getByTestId("equity-chart")).toBeInTheDocument();
    expect(api.runBacktest).toHaveBeenCalledTimes(1);
  });

  it("surfaces an Upgrade prompt when saving hits the free-tier limit (402)", async () => {
    // Start signed in so the Save button is actionable.
    localStorage.setItem("btlab.token", "dev:free@example.com");
    vi.mocked(api.saveBacktest).mockRejectedValue(
      new api.ApiError(402, "Free-tier limit reached (5 backtests/month)."),
    );
    vi.spyOn(window, "prompt").mockReturnValue("My run");

    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getAllByRole("button", { name: /open the lab/i })[0]);
    await screen.findByText("Fast MA period");
    fireEvent.submit(screen.getByRole("button", { name: /run backtest/i }).closest("form")!);
    await screen.findByText("+42.50%");

    // Save -> 402 -> warning banner with an Upgrade button.
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() =>
      expect(screen.getByText(/free-tier limit reached/i)).toBeInTheDocument(),
    );
    // The warning banner itself offers an Upgrade button (scoped to the banner,
    // since the header AuthBar also shows one for free users).
    const banner = screen.getByText(/free-tier limit reached/i).closest(".banner")!;
    expect(within(banner).getByRole("button", { name: /upgrade to pro/i })).toBeInTheDocument();
  });
});
