import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import StrategyForm from "./StrategyForm";
import type { Strategy } from "../api";

const STRATEGIES: Strategy[] = [
  {
    key: "ma_crossover",
    name: "Moving Average Crossover",
    description: "Trend following.",
    params: {
      fast: { type: "int", default: 20, min: 2, max: 100, label: "Fast MA period" },
      slow: { type: "int", default: 50, min: 5, max: 300, label: "Slow MA period" },
    },
  },
  {
    key: "grid",
    name: "Grid Trading",
    description: "Buy dips, sell rips.",
    params: {
      spacing: { type: "float", default: 0.05, min: 0.01, max: 0.25, label: "Grid spacing" },
    },
  },
];

describe("StrategyForm", () => {
  it("renders a control for each declared param of the selected strategy", () => {
    render(<StrategyForm strategies={STRATEGIES} busy={false} onRun={vi.fn()} onOptimize={vi.fn()} />);
    expect(screen.getByText("Fast MA period")).toBeInTheDocument();
    expect(screen.getByText("Slow MA period")).toBeInTheDocument();
    // Default strategy's description is shown.
    expect(screen.getByText("Trend following.")).toBeInTheDocument();
  });

  it("swaps the param controls when the strategy changes", () => {
    render(<StrategyForm strategies={STRATEGIES} busy={false} onRun={vi.fn()} onOptimize={vi.fn()} />);
    fireEvent.change(screen.getByDisplayValue("Moving Average Crossover"), {
      target: { value: "grid" },
    });
    expect(screen.getByText("Grid spacing")).toBeInTheDocument();
    expect(screen.queryByText("Fast MA period")).not.toBeInTheDocument();
  });

  it("submits a request with fee/slippage converted from percent to fraction", () => {
    const onRun = vi.fn();
    render(
      <StrategyForm strategies={STRATEGIES} busy={false} onRun={onRun} onOptimize={vi.fn()} />,
    );
    const form = screen.getByRole("button", { name: /run backtest/i }).closest("form")!;
    fireEvent.submit(form);

    expect(onRun).toHaveBeenCalledTimes(1);
    const req = onRun.mock.calls[0][0];
    expect(req.strategy).toBe("ma_crossover");
    expect(req.params).toEqual({ fast: 20, slow: 50 });
    // UI shows 0.1% fee / 0.05% slippage -> sent as fractions.
    expect(req.fee_pct).toBeCloseTo(0.001);
    expect(req.slippage_pct).toBeCloseTo(0.0005);
  });

  it("submits a sweep request in optimize mode (default: first param swept)", () => {
    const onOptimize = vi.fn();
    render(
      <StrategyForm
        strategies={STRATEGIES}
        busy={false}
        onRun={vi.fn()}
        onOptimize={onOptimize}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Optimize" }));
    const form = screen.getByRole("button", { name: /optimize \(/i }).closest("form")!;
    fireEvent.submit(form);

    expect(onOptimize).toHaveBeenCalledTimes(1);
    const req = onOptimize.mock.calls[0][0];
    expect(req.strategy).toBe("ma_crossover");
    expect(req.param_ranges).toHaveProperty("fast");
    expect(req.param_ranges).not.toHaveProperty("slow");
    // Unswept params travel as fixed values.
    expect(req.params).toEqual({ slow: 50 });
    expect(req.metric).toBe("return_pct");
  });

  it("disables the run button while busy", () => {
    render(
      <StrategyForm strategies={STRATEGIES} busy={true} onRun={vi.fn()} onOptimize={vi.fn()} />,
    );
    expect(screen.getByRole("button", { name: /running/i })).toBeDisabled();
  });
});
