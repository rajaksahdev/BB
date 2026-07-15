/**
 * Results dashboard (FR-03): headline stats for a single backtest run.
 */

import type { BacktestResult } from "../api";

function pct(v: number | null): string {
  return v === null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function num(v: number | null, digits = 2): string {
  return v === null ? "—" : v.toFixed(digits);
}

function money(v: number): string {
  return v.toLocaleString(undefined, { style: "currency", currency: "USD" });
}

function signClass(v: number | null): string {
  if (v === null) return "";
  return v >= 0 ? "pos" : "neg";
}

export default function StatsPanel({ result }: { result: BacktestResult }) {
  const s = result.stats;
  const beatsHold =
    s.return_pct !== null &&
    s.buy_hold_return_pct !== null &&
    s.return_pct >= s.buy_hold_return_pct;

  return (
    <div className="stats-panel">
      <div className="stat-grid">
        <Stat label="Return" value={pct(s.return_pct)} cls={signClass(s.return_pct)} big />
        <Stat
          label="Buy & Hold"
          value={pct(s.buy_hold_return_pct)}
          cls={signClass(s.buy_hold_return_pct)}
          hint={beatsHold ? "strategy beat holding" : "holding beat strategy"}
          hintCls={beatsHold ? "pos" : "neg"}
        />
        <Stat label="Final equity" value={money(s.final_equity)} />
        <Stat label="Win rate" value={pct(s.win_rate_pct)} />
        <Stat label="Max drawdown" value={pct(s.max_drawdown_pct)} cls="neg" />
        <Stat label="Sharpe" value={num(s.sharpe_ratio)} />
        <Stat label="Trades" value={String(s.trade_count)} />
        <Stat label="Exposure" value={pct(s.exposure_time_pct)} />
      </div>
      <p className="assumptions-line">
        Modeled with {(result.assumptions.fee_pct * 100).toFixed(2)}% fee and{" "}
        {(result.assumptions.slippage_pct * 100).toFixed(2)}% slippage ·{" "}
        {result.assumptions.position} · {result.request.start.slice(0, 10)} →{" "}
        {result.request.end.slice(0, 10)}
      </p>
    </div>
  );
}

function Stat({
  label,
  value,
  cls = "",
  hint,
  hintCls = "",
  big = false,
}: {
  label: string;
  value: string;
  cls?: string;
  hint?: string;
  hintCls?: string;
  big?: boolean;
}) {
  return (
    <div className={`stat ${big ? "stat-big" : ""}`}>
      <span className="stat-label">{label}</span>
      <span className={`stat-value ${cls}`}>{value}</span>
      {hint && <span className={`stat-hint ${hintCls}`}>{hint}</span>}
    </div>
  );
}
