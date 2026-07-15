/**
 * Per-trade breakdown for a run (FR-03 detail). Collapsed by default so the
 * comparison grid stays compact; hidden entirely when a run has no trade list
 * (saved backtests are persisted without one).
 */

import type { Trade } from "../api";

interface Props {
  trades: Trade[];
}

function fmtTime(iso: string): string {
  // "2024-03-07T14:00:00" -> "2024-03-07 14:00"; daily candles keep 00:00.
  return iso.slice(0, 16).replace("T", " ");
}

function fmtPrice(p: number | null): string {
  return p === null ? "—" : p.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export default function TradesTable({ trades }: Props) {
  if (trades.length === 0) return null;
  return (
    <details className="trades">
      <summary>Trades ({trades.length})</summary>
      <div className="trades-scroll">
        <table>
          <thead>
            <tr>
              <th>Entry</th>
              <th>Exit</th>
              <th className="num">Entry $</th>
              <th className="num">Exit $</th>
              <th className="num">PnL $</th>
              <th className="num">Return</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => (
              <tr key={i}>
                <td>{fmtTime(t.entry_time)}</td>
                <td>
                  {fmtTime(t.exit_time)}
                  {t.exit_reason === "end_of_data" && (
                    <span className="eod-tag" title="Force-closed when the data window ended, not a strategy exit">
                      end of data
                    </span>
                  )}
                </td>
                <td className="num">{fmtPrice(t.entry_price)}</td>
                <td className="num">{fmtPrice(t.exit_price)}</td>
                <td className={`num ${t.pnl >= 0 ? "pos" : "neg"}`}>
                  {t.pnl >= 0 ? "+" : ""}
                  {t.pnl.toFixed(2)}
                </td>
                <td className={`num ${t.return_pct >= 0 ? "pos" : "neg"}`}>
                  {t.return_pct >= 0 ? "+" : ""}
                  {t.return_pct.toFixed(2)}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
