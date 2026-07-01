/**
 * Saved backtests (FR-05): list the signed-in user's saved runs, load one into
 * the comparison view, or delete it.
 */

import { useEffect, useState } from "react";
import { listSaved, type SavedSummary } from "../api";

interface Props {
  signedIn: boolean;
  // Bump to force a reload (e.g. after a new save).
  reloadKey: number;
  onLoad: (id: string) => void;
  onDelete: (id: string) => void;
}

function pct(v: number | null): string {
  return v === null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export default function SavedList({ signedIn, reloadKey, onLoad, onDelete }: Props) {
  const [items, setItems] = useState<SavedSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!signedIn) {
      setItems([]);
      return;
    }
    setLoading(true);
    listSaved()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [signedIn, reloadKey]);

  if (!signedIn) {
    return <p className="muted small">Sign in to save and revisit backtests.</p>;
  }
  if (loading && items.length === 0) {
    return <p className="muted small">Loading…</p>;
  }
  if (items.length === 0) {
    return <p className="muted small">No saved backtests yet. Run one and hit “Save”.</p>;
  }

  return (
    <ul className="saved-list">
      {items.map((it) => (
        <li className="saved-item" key={it.id}>
          <button className="saved-load" onClick={() => onLoad(it.id)} title="Load into comparison">
            <span className="saved-name">{it.name || `${it.symbol} ${it.strategy}`}</span>
            <span className="saved-meta">
              {it.symbol} · {it.interval} · {it.strategy}
            </span>
            <span className={`saved-return ${(it.stats.return_pct ?? 0) >= 0 ? "pos" : "neg"}`}>
              {pct(it.stats.return_pct)}
            </span>
          </button>
          <button
            className="saved-delete"
            onClick={() => onDelete(it.id)}
            title="Delete"
            aria-label="Delete saved backtest"
          >
            🗑
          </button>
        </li>
      ))}
    </ul>
  );
}
