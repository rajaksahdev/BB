/**
 * Backtest config form (FR-02). The strategy param controls are generated
 * dynamically from each strategy's declared param schema, so adding a strategy
 * on the backend automatically gets a UI here.
 */

import { useMemo, useState } from "react";
import {
  INTERVALS,
  SYMBOLS,
  type BacktestRequest,
  type Strategy,
} from "../api";
import type { SharedConfig } from "../share";

interface Props {
  strategies: Strategy[];
  busy: boolean;
  onRun: (req: BacktestRequest, periodLabel?: string) => void;
  /** Pairs/intervals with data (from GET /symbols); defaults cover offline dev. */
  symbols?: readonly string[];
  intervals?: readonly string[];
  /** Prefill from a share link (see share.ts). */
  initial?: SharedConfig;
}

const INTERVAL_LABELS: Record<string, string> = { "1d": "Daily", "1h": "Hourly" };

/** Backtest period presets. `start`/`end` are computed at submit time. */
interface Period {
  key: string;
  label: string;
  /** Compact label for the segmented picker; `label` stays on run titles. */
  short: string;
  range: () => { start?: string; end?: string };
}

// Naive UTC ISO (no timezone suffix) to match the backend's stored open_time.
const isoDay = (d: Date) => d.toISOString().slice(0, 10) + "T00:00:00";
const monthsAgo = (n: number) => {
  const d = new Date();
  d.setUTCMonth(d.getUTCMonth() - n);
  return d;
};
const yearStart = (y: number) => new Date(Date.UTC(y, 0, 1));

/** Returning users pick up where they left off (share links take precedence). */
const STORAGE_KEY = "backtestlab.lastConfig";

interface StoredConfig {
  symbol?: string;
  interval?: string;
  strategyKey?: string;
  periodKey?: string;
  cash?: number;
  feePct?: number;
  slippagePct?: number;
  paramValues?: Record<string, Record<string, number>>;
}

function loadStoredConfig(): StoredConfig {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") as StoredConfig;
  } catch {
    return {};
  }
}

const THIS_YEAR = new Date().getUTCFullYear();
const PERIODS: Period[] = [
  { key: "all", label: "All history", short: "All", range: () => ({}) },
  { key: "12m", label: "Last 12 months", short: "12M", range: () => ({ start: isoDay(monthsAgo(12)) }) },
  { key: "24m", label: "Last 24 months", short: "24M", range: () => ({ start: isoDay(monthsAgo(24)) }) },
  { key: "ytd", label: `${THIS_YEAR} YTD`, short: "YTD", range: () => ({ start: isoDay(yearStart(THIS_YEAR)) }) },
  ...[THIS_YEAR - 1, THIS_YEAR - 2].map((y) => ({
    key: `y${y}`,
    label: String(y),
    short: String(y),
    range: () => ({ start: isoDay(yearStart(y)), end: isoDay(yearStart(y + 1)) }),
  })),
];

export default function StrategyForm({
  strategies,
  busy,
  onRun,
  symbols = SYMBOLS,
  intervals = INTERVALS,
  initial,
}: Props) {
  const [stored] = useState<StoredConfig>(initial ? {} : loadStoredConfig);
  const [symbol, setSymbol] = useState<string>(initial?.symbol ?? stored.symbol ?? symbols[0]);
  const [interval, setInterval] = useState<string>(
    initial?.interval ?? stored.interval ?? intervals[0],
  );
  const [strategyKey, setStrategyKey] = useState<string>(() => {
    for (const key of [initial?.strategy, stored.strategyKey]) {
      if (key && strategies.some((s) => s.key === key)) return key;
    }
    return strategies[0]?.key ?? "";
  });
  const [periodKey, setPeriodKey] = useState<string>(
    PERIODS.some((p) => p.key === stored.periodKey) ? stored.periodKey! : "all",
  );
  const [cash, setCash] = useState<number>(initial?.cash ?? stored.cash ?? 10_000);
  const [feePct, setFeePct] = useState<number>(initial?.feePct ?? stored.feePct ?? 0.1); // shown as %, sent as fraction
  const [slippagePct, setSlippagePct] = useState<number>(
    initial?.slippagePct ?? stored.slippagePct ?? 0.05,
  );

  // Per-strategy param values, keyed by strategy then param name.
  const [paramValues, setParamValues] = useState<Record<string, Record<string, number>>>(() => {
    if (initial && Object.keys(initial.params).length > 0) {
      return { [initial.strategy]: initial.params };
    }
    return stored.paramValues ?? {};
  });

  const strategy = useMemo(
    () => strategies.find((s) => s.key === strategyKey),
    [strategies, strategyKey],
  );

  const currentParams = useMemo(() => {
    if (!strategy) return {};
    const saved = paramValues[strategy.key] ?? {};
    const defaults = Object.fromEntries(
      Object.entries(strategy.params).map(([k, spec]) => [k, spec.default]),
    );
    return { ...defaults, ...saved };
  }, [strategy, paramValues]);

  function setParam(key: string, value: number) {
    if (!strategy) return;
    setParamValues((prev) => ({
      ...prev,
      [strategy.key]: { ...prev[strategy.key], [key]: value },
    }));
  }

  // Mirror the backend's cross-param rule so the user gets instant feedback
  // instead of a 400 after the round-trip.
  const paramWarning =
    "fast" in currentParams &&
    "slow" in currentParams &&
    Number(currentParams.fast) >= Number(currentParams.slow)
      ? "Fast period must be below slow — as set, the crossover logic inverts."
      : null;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!strategy || paramWarning) return;
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          symbol, interval, strategyKey, periodKey, cash, feePct, slippagePct, paramValues,
        } satisfies StoredConfig),
      );
    } catch {
      /* storage may be unavailable (private mode) — running still works */
    }
    const period = PERIODS.find((p) => p.key === periodKey) ?? PERIODS[0];
    onRun(
      {
        symbol,
        interval,
        strategy: strategy.key,
        params: currentParams,
        cash: Math.max(1, cash || 0), // a cleared input parses to 0/NaN
        fee_pct: feePct / 100,
        slippage_pct: slippagePct / 100,
        ...period.range(),
      },
      period.key === "all" ? undefined : period.label,
    );
  }

  return (
    <form className="config-form" onSubmit={submit}>
      <div className="field-row">
        <label className="field">
          <span>Pair</span>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Interval</span>
          <select value={interval} onChange={(e) => setInterval(e.target.value)}>
            {intervals.map((i) => (
              <option key={i} value={i}>
                {INTERVAL_LABELS[i] ?? i}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="field">
        <span id="period-label">Period</span>
        <div className="segmented" role="group" aria-labelledby="period-label">
          {PERIODS.map((p) => (
            <button
              type="button"
              key={p.key}
              className={`seg-btn${p.key === periodKey ? " active" : ""}`}
              aria-pressed={p.key === periodKey}
              title={p.label}
              onClick={() => setPeriodKey(p.key)}
            >
              {p.short}
            </button>
          ))}
        </div>
      </div>

      <label className="field">
        <span>Strategy</span>
        <select value={strategyKey} onChange={(e) => setStrategyKey(e.target.value)}>
          {strategies.map((s) => (
            <option key={s.key} value={s.key}>
              {s.name}
            </option>
          ))}
        </select>
      </label>

      {strategy && <p className="strategy-desc">{strategy.description}</p>}

      {strategy &&
        Object.entries(strategy.params).map(([key, spec]) => (
          <label className="field slider-field" key={key}>
            <span>
              {spec.label}
              <strong className="param-value">
                {spec.type === "float"
                  ? Number(currentParams[key]).toFixed(2)
                  : currentParams[key]}
              </strong>
            </span>
            <input
              type="range"
              min={spec.min}
              max={spec.max}
              step={spec.type === "float" ? 0.01 : 1}
              value={currentParams[key]}
              onChange={(e) => setParam(key, Number(e.target.value))}
            />
          </label>
        ))}

      {paramWarning && <p className="param-warning">{paramWarning}</p>}

      <fieldset className="cost-assumptions">
        <legend>Cost assumptions</legend>
        <div className="field-row">
          <label className="field">
            <span>Starting cash ($)</span>
            <input
              type="number"
              min={1}
              step="any"
              value={cash}
              onChange={(e) => setCash(Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span>Fee (%)</span>
            <input
              type="number"
              min={0}
              max={10}
              step={0.01}
              value={feePct}
              onChange={(e) => setFeePct(Number(e.target.value))}
            />
          </label>
          <label className="field">
            <span>Slippage (%)</span>
            <input
              type="number"
              min={0}
              max={10}
              step={0.01}
              value={slippagePct}
              onChange={(e) => setSlippagePct(Number(e.target.value))}
            />
          </label>
        </div>
      </fieldset>

      <button type="submit" className="run-btn" disabled={busy || !strategy || !!paramWarning}>
        {busy ? (
          <>
            <span className="btn-spinner" aria-hidden="true" /> Running…
          </>
        ) : (
          "Run backtest"
        )}
      </button>
    </form>
  );
}
