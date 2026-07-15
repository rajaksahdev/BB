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
  // Extended metrics ship with new runs; backtests saved before they existed
  // simply omit them, so the whole section hides for those rows.
  const hasExtended = s.cagr_pct !== undefined;

  // Plain-English verdict: converts the two headline numbers into the
  // decision the user is actually here for.
  let verdict: string | null = null;
  if (s.return_pct !== null && s.buy_hold_return_pct !== null) {
    const diff = s.return_pct - s.buy_hold_return_pct;
    const dd = s.max_drawdown_pct !== null ? ` with ${Math.abs(s.max_drawdown_pct).toFixed(0)}% max drawdown` : "";
    verdict =
      diff >= 0
        ? `Beat buy-and-hold by ${diff.toFixed(1)} points${dd}.`
        : `Underperformed buy-and-hold by ${Math.abs(diff).toFixed(1)} points — simply holding did better.`;
  }

  return (
    <div className="stats-panel">
      {verdict && <p className={`verdict ${beatsHold ? "pos" : "neg"}`}>{verdict}</p>}
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
      {hasExtended && (
        <details className="more-stats">
          <summary>More metrics</summary>
          <div className="more-stats-grid">
            <MiniStat label="CAGR" value={pct(s.cagr_pct ?? null)} cls={signClass(s.cagr_pct ?? null)} />
            <MiniStat label="Sortino" value={num(s.sortino_ratio ?? null)} />
            <MiniStat label="Calmar" value={num(s.calmar_ratio ?? null)} />
            <MiniStat label="Volatility (ann.)" value={pct(s.volatility_ann_pct ?? null)} />
            <MiniStat label="Profit factor" value={num(s.profit_factor ?? null)} />
            <MiniStat label="Avg trade" value={pct(s.avg_trade_pct ?? null)} cls={signClass(s.avg_trade_pct ?? null)} />
            <MiniStat label="Best trade" value={pct(s.best_trade_pct ?? null)} cls="pos" />
            <MiniStat label="Worst trade" value={pct(s.worst_trade_pct ?? null)} cls="neg" />
          </div>
        </details>
      )}
      {(s.forced_exit_count ?? 0) > 0 && (
        <p className="forced-exit-note">
          Includes {s.forced_exit_count} position{s.forced_exit_count === 1 ? "" : "s"} closed
          at the end of the period (excluded from win rate &amp; trade stats).
        </p>
      )}
      <p className="assumptions-line">
        Modeled with {(result.assumptions.fee_pct * 100).toFixed(2)}% fee and{" "}
        {(result.assumptions.slippage_pct * 100).toFixed(2)}% slippage ·{" "}
        {result.assumptions.position} · {result.request.start.slice(0, 10)} →{" "}
        {result.request.end.slice(0, 10)}
      </p>
    </div>
  );
}

function MiniStat({ label, value, cls = "" }: { label: string; value: string; cls?: string }) {
  return (
    <div className="mini-stat">
      <span className="stat-label">{label}</span>
      <span className={`mini-stat-value ${value === "—" ? "" : cls}`}>{value}</span>
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
