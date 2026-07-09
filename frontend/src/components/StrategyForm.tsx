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

interface Props {
  strategies: Strategy[];
  busy: boolean;
  onRun: (req: BacktestRequest) => void;
}

export default function StrategyForm({ strategies, busy, onRun }: Props) {
  const [symbol, setSymbol] = useState<string>(SYMBOLS[0]);
  const [interval, setInterval] = useState<string>(INTERVALS[0]);
  const [strategyKey, setStrategyKey] = useState<string>(strategies[0]?.key ?? "");
  const [cash, setCash] = useState<number>(10_000);
  const [feePct, setFeePct] = useState<number>(0.1); // shown as %, sent as fraction
  const [slippagePct, setSlippagePct] = useState<number>(0.05);

  // Per-strategy param values, keyed by strategy then param name.
  const [paramValues, setParamValues] = useState<Record<string, Record<string, number>>>({});

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

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!strategy) return;
    onRun({
      symbol,
      interval,
      strategy: strategy.key,
      params: currentParams,
      cash,
      fee_pct: feePct / 100,
      slippage_pct: slippagePct / 100,
    });
  }

  return (
    <form className="config-form" onSubmit={submit}>
      <div className="field-row">
        <label className="field">
          <span>Pair</span>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
            {SYMBOLS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Interval</span>
          <select value={interval} onChange={(e) => setInterval(e.target.value)}>
            {INTERVALS.map((i) => (
              <option key={i} value={i}>
                {i === "1d" ? "Daily" : "Hourly"}
              </option>
            ))}
          </select>
        </label>
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

      <button type="submit" className="run-btn" disabled={busy || !strategy}>
        {busy ? "Running…" : "Run backtest"}
      </button>
    </form>
  );
}
