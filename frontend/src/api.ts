/**
 * Typed client for the BacktestLab API.
 *
 * The base URL is configurable via VITE_API_URL (see .env); it defaults to the
 * local FastAPI dev server, whose CORS allowlist already includes :5173.
 */

const API_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

// ---- Types (mirror the backend response shapes) ----

export type ParamType = "int" | "float";

export interface ParamSpec {
  type: ParamType;
  default: number;
  min?: number;
  max?: number;
  label: string;
}

export interface Strategy {
  key: string;
  name: string;
  description: string;
  params: Record<string, ParamSpec>;
}

export interface Stats {
  return_pct: number | null;
  buy_hold_return_pct: number | null;
  win_rate_pct: number | null;
  max_drawdown_pct: number | null;
  sharpe_ratio: number | null;
  trade_count: number;
  exposure_time_pct: number | null;
  starting_cash: number;
  final_equity: number;
  // Extended metrics (absent on backtests saved before they were added).
  sortino_ratio?: number | null;
  calmar_ratio?: number | null;
  cagr_pct?: number | null;
  volatility_ann_pct?: number | null;
  profit_factor?: number | null;
  avg_trade_pct?: number | null;
  best_trade_pct?: number | null;
  worst_trade_pct?: number | null;
  /** Trades force-closed at the end of the data window (not strategy exits). */
  forced_exit_count?: number;
}

export interface EquityPoint {
  time: string; // ISO timestamp
  equity: number;
}

export interface Trade {
  entry_time: string;
  exit_time: string;
  entry_price: number | null;
  exit_price: number | null;
  pnl: number;
  return_pct: number;
  /** "signal" = strategy exit; "end_of_data" = force-closed when data ended. */
  exit_reason?: "signal" | "end_of_data";
}

export interface Assumptions {
  fee_pct: number;
  slippage_pct: number;
  position: string;
  note: string;
}

export interface BacktestRequest {
  symbol: string;
  interval: string;
  strategy: string;
  params: Record<string, number>;
  cash: number;
  fee_pct: number;
  slippage_pct: number;
  start?: string; // ISO datetime — omit for full history
  end?: string;
  name?: string; // optional label, used when saving
}

export interface Me {
  id: string;
  email: string;
  tier: "free" | "pro";
  usage_this_month: number;
  monthly_limit: number | null; // null == unlimited (Pro)
  remaining: number | null;
}

/** Summary row returned by GET /backtests (list). */
export interface SavedSummary {
  id: string;
  name: string | null;
  symbol: string;
  interval: string;
  strategy: string;
  params: Record<string, number>;
  created_at: string;
  stats: Stats;
}

/** Full row returned by GET /backtests/{id}. Flatter than BacktestResult. */
export interface SavedDetail {
  id: string;
  name: string | null;
  symbol: string;
  interval: string;
  strategy: string;
  params: Record<string, number>;
  start: string;
  end: string;
  created_at: string;
  stats: Stats;
  equity_curve: EquityPoint[];
  assumptions: Assumptions;
}

export interface BacktestResult {
  request: {
    symbol: string;
    interval: string;
    strategy: string;
    params: Record<string, number>;
    start: string;
    end: string;
  };
  stats: Stats;
  equity_curve: EquityPoint[];
  trades: Trade[];
  assumptions: Assumptions;
  disclaimer: string;
}

// ---- Auth token (dev token or Supabase JWT) ----

let authToken: string | null = null;

/** Set the bearer token attached to authenticated requests (null clears it). */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

// ---- Fetch helpers ----

/** Error carrying the HTTP status so callers can branch (e.g. 402 limit, 401). */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

/** Abort requests that hang (e.g. the API cold-starting on free hosting). */
const DEFAULT_TIMEOUT_MS = 20_000;

async function request<T>(
  path: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...rest } = init ?? {};
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (authToken) headers.Authorization = `Bearer ${authToken}`;

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...rest,
      headers: { ...headers, ...rest.headers },
      signal: ctrl.signal,
    });
  } catch {
    throw new ApiError(
      0,
      "Can't reach the API — it may be waking up from sleep (free hosting spins " +
        "down when idle). It usually answers within a minute; retrying.",
    );
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    // FastAPI errors come back as { detail: string | [...] }.
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail))
        detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {
      /* keep status-line fallback */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function getStrategies(): Promise<Strategy[]> {
  return request<Strategy[]>("/strategies");
}

/** Pairs/intervals that actually have candle data (drives the config selects). */
export function getSymbols(): Promise<{ symbols: string[]; intervals: string[] }> {
  return request<{ symbols: string[]; intervals: string[] }>("/symbols");
}

export function runBacktest(body: BacktestRequest): Promise<BacktestResult> {
  return request<BacktestResult>("/backtest", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ---- Authenticated endpoints ----

export function getMe(): Promise<Me> {
  return request<Me>("/me");
}

/** Run + persist a backtest. Throws ApiError(402) when the free limit is hit. */
export function saveBacktest(body: BacktestRequest): Promise<BacktestResult & { id: string }> {
  return request("/backtests", { method: "POST", body: JSON.stringify(body) });
}

export function listSaved(): Promise<SavedSummary[]> {
  return request<SavedSummary[]>("/backtests");
}

export function getSaved(id: string): Promise<SavedDetail> {
  return request<SavedDetail>(`/backtests/${id}`);
}

export function deleteSaved(id: string): Promise<void> {
  return request<void>(`/backtests/${id}`, { method: "DELETE" });
}

// ---- Billing (Phase 5) ----

export function getBillingConfig(): Promise<{ enabled: boolean }> {
  return request<{ enabled: boolean }>("/billing/config");
}

/** Start a Pro Checkout; resolves to the Lemon Squeezy-hosted URL to redirect to. */
export function startCheckout(): Promise<{ url: string }> {
  return request<{ url: string }>("/billing/checkout", { method: "POST" });
}

/** Open the Lemon Squeezy customer portal; resolves to the hosted URL. */
export function openPortal(): Promise<{ url: string }> {
  return request<{ url: string }>("/billing/portal", { method: "POST" });
}

const DISCLAIMER =
  "For research and educational use only. This is NOT financial advice. " +
  "Past performance does not guarantee future results. Results model " +
  "estimated fees and slippage and may differ from live trading.";

/** Adapt a saved (flat) row into the BacktestResult shape the views expect. */
export function savedToResult(d: SavedDetail): BacktestResult {
  return {
    request: {
      symbol: d.symbol,
      interval: d.interval,
      strategy: d.strategy,
      params: d.params,
      start: d.start,
      end: d.end,
    },
    stats: d.stats,
    equity_curve: d.equity_curve,
    trades: [],
    assumptions: d.assumptions,
    disclaimer: DISCLAIMER,
  };
}

/** Rebuild the request that produced a result (for saving an ad-hoc run). */
export function resultToRequest(r: BacktestResult, name?: string): BacktestRequest {
  return {
    symbol: r.request.symbol,
    interval: r.request.interval,
    strategy: r.request.strategy,
    params: r.request.params,
    cash: r.stats.starting_cash,
    fee_pct: r.assumptions.fee_pct,
    slippage_pct: r.assumptions.slippage_pct,
    // Pin the window the run actually covered, so saving a ranged run
    // re-executes the same period rather than all history.
    start: r.request.start,
    end: r.request.end,
    name,
  };
}

export const SYMBOLS = ["BTCUSDT", "ETHUSDT"] as const;
export const INTERVALS = ["1d", "1h"] as const;
