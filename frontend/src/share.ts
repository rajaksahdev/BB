/**
 * Shareable run links (FR-09 starter): the full backtest config is encoded in
 * the URL querystring, so a pasted link lands in the lab pre-filled and —
 * with autorun — re-executes the exact same window immediately.
 */

import type { BacktestRequest, BacktestResult } from "./api";

export interface SharedConfig {
  symbol: string;
  interval: string;
  strategy: string;
  params: Record<string, number>;
  cash?: number;
  feePct?: number; // display units (%): 0.1 == 0.1%
  slippagePct?: number;
  start?: string;
  end?: string;
  autorun: boolean;
}

/** Build a share URL reproducing this result's exact config and window. */
export function shareUrlForResult(r: BacktestResult): string {
  const q = new URLSearchParams();
  q.set("symbol", r.request.symbol);
  q.set("interval", r.request.interval);
  q.set("strategy", r.request.strategy);
  for (const [k, v] of Object.entries(r.request.params)) q.set(`p_${k}`, String(v));
  q.set("cash", String(r.stats.starting_cash));
  q.set("fee", String(r.assumptions.fee_pct * 100));
  q.set("slip", String(r.assumptions.slippage_pct * 100));
  q.set("start", r.request.start);
  q.set("end", r.request.end);
  q.set("autorun", "1");
  return `${window.location.origin}/?${q.toString()}`;
}

/** Parse a share querystring; null when it doesn't carry a config. */
export function parseSharedConfig(search: string): SharedConfig | null {
  const q = new URLSearchParams(search);
  const symbol = q.get("symbol");
  const strategy = q.get("strategy");
  if (!symbol || !strategy) return null;

  const params: Record<string, number> = {};
  for (const [key, val] of q.entries()) {
    if (key.startsWith("p_") && !Number.isNaN(Number(val))) {
      params[key.slice(2)] = Number(val);
    }
  }
  const num = (key: string): number | undefined => {
    const v = q.get(key);
    return v !== null && v !== "" && !Number.isNaN(Number(v)) ? Number(v) : undefined;
  };
  return {
    symbol,
    interval: q.get("interval") ?? "1d",
    strategy,
    params,
    cash: num("cash"),
    feePct: num("fee"),
    slippagePct: num("slip"),
    start: q.get("start") ?? undefined,
    end: q.get("end") ?? undefined,
    autorun: q.get("autorun") === "1",
  };
}

/** Turn a parsed shared config into a runnable request. */
export function sharedToRequest(c: SharedConfig): BacktestRequest {
  return {
    symbol: c.symbol,
    interval: c.interval,
    strategy: c.strategy,
    params: c.params,
    cash: c.cash ?? 10_000,
    fee_pct: (c.feePct ?? 0.1) / 100,
    slippage_pct: (c.slippagePct ?? 0.05) / 100,
    ...(c.start ? { start: c.start } : {}),
    ...(c.end ? { end: c.end } : {}),
  };
}
