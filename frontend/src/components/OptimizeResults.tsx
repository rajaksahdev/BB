/**
 * Optimizer results (Phase 7a): best-params card, a 2-param heatmap (grid
 * sweeps) with a hover readout, and the ranked combo table. Exact values live
 * in the readout + table, so cell color never carries a number alone.
 */

import { useMemo, useState } from "react";
import {
  METRIC_LABELS,
  type OptimizeCombo,
  type OptimizeResult,
} from "../api";
import { heatColor } from "../chartColors";

interface Props {
  result: OptimizeResult;
  busy: boolean;
  /** Run a normal backtest with a combo's full parameter set. */
  onApply: (params: Record<string, number>) => void;
  onClose: () => void;
}

const TABLE_ROWS = 12;

const fmt = (v: number | null, digits = 2) =>
  v === null || v === undefined ? "—" : v.toFixed(digits);

export default function OptimizeResults({ result, busy, onApply, onClose }: Props) {
  const { swept, grid, results, best, request } = result;
  const metric = request.metric;
  const [hovered, setHovered] = useState<OptimizeCombo | null>(null);

  // Params for a combo = fixed params + its swept values.
  const fullParams = (c: OptimizeCombo) => ({ ...request.fixed_params, ...c.params });

  const metricOf = (c: OptimizeCombo) => c[metric];

  const [min, max] = useMemo(() => {
    const vals = results.map(metricOf).filter((v): v is number => v !== null);
    return [Math.min(...vals), Math.max(...vals)];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [results, metric]);

  // Heatmap lookup: "x|y" -> combo. Only for 2-param sweeps.
  const [xParam, yParam] = [swept[1], swept[0]];
  const cellMap = useMemo(() => {
    if (swept.length !== 2) return null;
    const m = new Map<string, OptimizeCombo>();
    for (const c of results) m.set(`${c.params[xParam]}|${c.params[yParam]}`, c);
    return m;
  }, [results, swept.length, xParam, yParam]);

  const readout = hovered ?? best;

  return (
    <div className="opt-results">
      <div className="opt-head">
        <h3>
          Optimizer · {request.symbol} {request.interval} · ranked by{" "}
          {METRIC_LABELS[metric]}
        </h3>
        <span className="opt-meta">
          {result.combos_run} combos in {(result.elapsed_ms / 1000).toFixed(1)}s
          {result.combos_skipped > 0 && ` · ${result.combos_skipped} invalid skipped`}
        </span>
        <button className="banner-close" onClick={onClose} aria-label="Dismiss optimizer results">
          ×
        </button>
      </div>

      <div className="opt-best">
        <div className="opt-best-text">
          <span className="opt-best-label">Best {METRIC_LABELS[metric]}</span>
          <strong className="opt-best-value">{fmt(metricOf(best))}</strong>
          <span className="opt-best-params">
            {Object.entries(best.params)
              .map(([k, v]) => `${k}=${v}`)
              .join(" · ")}
          </span>
        </div>
        <button
          className="run-btn opt-apply"
          disabled={busy}
          onClick={() => onApply(best.full_params)}
        >
          Backtest best params
        </button>
      </div>

      {cellMap && (
        <div className="opt-heatmap-wrap">
          <table className="opt-heatmap" role="grid" aria-label="Parameter sweep heatmap">
            <thead>
              <tr>
                <th className="opt-corner">
                  {yParam} ↓ / {xParam} →
                </th>
                {grid[xParam].map((x) => (
                  <th key={x} scope="col">
                    {x}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {grid[yParam].map((y) => (
                <tr key={y}>
                  <th scope="row">{y}</th>
                  {grid[xParam].map((x) => {
                    const combo = cellMap.get(`${x}|${y}`);
                    const v = combo ? metricOf(combo) : null;
                    return (
                      <td key={x}>
                        {combo ? (
                          <button
                            className={`opt-cell${combo === readout ? " focused" : ""}`}
                            style={v !== null ? { background: heatColor(v, min, max) } : undefined}
                            title={`${yParam}=${y}, ${xParam}=${x}: ${fmt(v)}`}
                            aria-label={`${yParam}=${y}, ${xParam}=${x}: ${METRIC_LABELS[metric]} ${fmt(v)}`}
                            onMouseEnter={() => setHovered(combo)}
                            onMouseLeave={() => setHovered(null)}
                            onFocus={() => setHovered(combo)}
                            onBlur={() => setHovered(null)}
                            onClick={() => onApply(fullParams(combo))}
                            disabled={busy}
                          />
                        ) : (
                          <span className="opt-cell invalid" title="Invalid combination" />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>

          <div className="opt-scale" aria-hidden="true">
            <span>{fmt(min)}</span>
            <span
              className="opt-scale-bar"
              style={{
                background:
                  min < 0 && max > 0
                    ? `linear-gradient(90deg, ${heatColor(min, min, max)}, ${heatColor(0, min, max)} ${Math.round((-min / (max - min)) * 100)}%, ${heatColor(max, min, max)})`
                    : `linear-gradient(90deg, ${heatColor(min, min, max)}, ${heatColor(max, min, max)})`,
              }}
            />
            <span>{fmt(max)}</span>
          </div>

          <p className="opt-readout" aria-live="polite">
            <strong>
              {Object.entries(readout.params)
                .map(([k, v]) => `${k}=${v}`)
                .join(", ")}
            </strong>
            {" — "}return {fmt(readout.return_pct)}% · Sharpe {fmt(readout.sharpe_ratio)} · max DD{" "}
            {fmt(readout.max_drawdown_pct)}% · win {fmt(readout.win_rate_pct, 1)}% ·{" "}
            {readout.trade_count} trades — click a cell to backtest it
          </p>
        </div>
      )}

      <div className="table-scroll">
        <table className="opt-table">
          <thead>
            <tr>
              <th>#</th>
              {swept.map((p) => (
                <th key={p}>{p}</th>
              ))}
              {(Object.keys(METRIC_LABELS) as (keyof typeof METRIC_LABELS)[]).map((m) => (
                <th key={m} className={m === metric ? "opt-metric-col" : undefined}>
                  {METRIC_LABELS[m]}
                </th>
              ))}
              <th>Trades</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {results.slice(0, TABLE_ROWS).map((c, i) => (
              <tr key={swept.map((p) => c.params[p]).join("|")}>
                <td className="opt-rank">{i + 1}</td>
                {swept.map((p) => (
                  <td key={p}>{c.params[p]}</td>
                ))}
                <td className={metric === "return_pct" ? "opt-metric-col" : undefined}>
                  {fmt(c.return_pct)}
                </td>
                <td className={metric === "sharpe_ratio" ? "opt-metric-col" : undefined}>
                  {fmt(c.sharpe_ratio)}
                </td>
                <td className={metric === "win_rate_pct" ? "opt-metric-col" : undefined}>
                  {fmt(c.win_rate_pct, 1)}
                </td>
                <td className={metric === "max_drawdown_pct" ? "opt-metric-col" : undefined}>
                  {fmt(c.max_drawdown_pct)}
                </td>
                <td>{c.trade_count}</td>
                <td>
                  <button
                    className="link-btn"
                    disabled={busy}
                    onClick={() => onApply(fullParams(c))}
                  >
                    Backtest
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {results.length > TABLE_ROWS && (
        <p className="muted opt-more">
          Top {TABLE_ROWS} of {results.length} combinations shown.
        </p>
      )}

      <p className="opt-overfit-note">
        Optimized parameters are fit to this exact period — expect worse
        out-of-sample performance. Validate on a different date range before
        trusting a result.
      </p>
    </div>
  );
}
