import { useEffect, useRef, useState } from "react";
import {
  ApiError,
  deleteSaved,
  getBillingConfig,
  getSaved,
  getStrategies,
  getSymbols,
  INTERVALS,
  openPortal,
  resultToRequest,
  runBacktest,
  saveBacktest,
  savedToResult,
  startCheckout,
  SYMBOLS,
  type BacktestRequest,
  type BacktestResult,
  type Strategy,
} from "./api";
import { useAuth } from "./useAuth";
import { parseSharedConfig, sharedToRequest, shareUrlForResult } from "./share";
import StrategyForm from "./components/StrategyForm";
import StatsPanel from "./components/StatsPanel";
import AuthBar from "./components/AuthBar";
import SavedList from "./components/SavedList";
import Landing from "./components/Landing";
import Legal from "./components/Legal";
import TradesTable from "./components/TradesTable";
import EquityChart, { type EquitySeries } from "./components/EquityChart";
import { colorForIndex } from "./chartColors";
import "./App.css";

const DISCLAIMER_SHORT =
  "For research and educational use only. Not financial advice. Past performance does not " +
  "guarantee future results. BacktestLab never holds funds or places trades.";

interface Run {
  id: number;
  label: string;
  color: string;
  result: BacktestResult;
  savedId?: string; // set once persisted (or when loaded from a saved row)
  saving?: boolean;
}

const MAX_RUNS = 4; // overlay cap for the comparison view

// Free hosting spins the API down when idle; the first request can take ~1
// minute. Retry the initial load on this backoff before declaring it down.
const RETRY_DELAYS_MS = [5_000, 15_000, 30_000, 45_000];

type ApiStatus = "connecting" | "waking" | "up" | "down";

type View = "landing" | "app" | "terms" | "refunds";

function viewForPath(pathname: string): View | null {
  if (pathname === "/terms") return "terms";
  if (pathname === "/refunds") return "refunds";
  return null;
}

export default function App() {
  const auth = useAuth();
  const signedIn = !!auth.token;

  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [apiStatus, setApiStatus] = useState<ApiStatus>("connecting");
  const [symbols, setSymbols] = useState<readonly string[]>(SYMBOLS);
  const [intervals, setIntervals] = useState<readonly string[]>(INTERVALS);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [runErr, setRunErr] = useState<string | null>(null);
  const [notice, setNotice] = useState<{
    kind: "info" | "warn";
    text: string;
    action?: "upgrade";
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [runs, setRuns] = useState<Run[]>([]);
  const [nextId, setNextId] = useState(1);
  const [savedReload, setSavedReload] = useState(0);
  const [billingEnabled, setBillingEnabled] = useState(false);
  // A share link carries the full run config in the querystring; parse it
  // once so the lab can prefill the form and (autorun) re-execute the run.
  const [shared] = useState(() => parseSharedConfig(window.location.search));
  // Show the marketing landing first, unless we're returning from checkout,
  // following a share link, or landing directly on a legal page (/terms,
  // /refunds — the static host rewrites every path to index.html).
  const [view, setView] = useState<View>(() => {
    const legal = viewForPath(window.location.pathname);
    if (legal) return legal;
    if (parseSharedConfig(window.location.search)) return "app";
    const p = new URLSearchParams(window.location.search);
    return p.get("checkout") || p.get("portal") ? "app" : "landing";
  });

  // Legal pages get real URLs (payment reviews require linkable terms/refund
  // pages); the landing/app switch stays at "/" as before.
  function navigate(next: View) {
    const path = next === "terms" ? "/terms" : next === "refunds" ? "/refunds" : "/";
    if (window.location.pathname !== path) window.history.pushState({}, "", path);
    setView(next);
    window.scrollTo(0, 0);
  }

  useEffect(() => {
    const onPop = () => setView(viewForPath(window.location.pathname) ?? "landing");
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  useEffect(() => {
    let cancelled = false;

    // Kicks off on landing mount, so the API warms up while the visitor reads.
    async function loadStrategies() {
      for (let attempt = 0; ; attempt++) {
        try {
          const list = await getStrategies();
          if (cancelled) return;
          setStrategies(list);
          setApiStatus("up");
          return;
        } catch (e) {
          if (cancelled) return;
          if (attempt >= RETRY_DELAYS_MS.length) {
            setApiStatus("down");
            setLoadErr(String((e as Error).message ?? e));
            return;
          }
          setApiStatus("waking");
          await new Promise((r) => setTimeout(r, RETRY_DELAYS_MS[attempt]));
          if (cancelled) return;
        }
      }
    }

    void loadStrategies();
    getBillingConfig().then((c) => setBillingEnabled(c.enabled)).catch(() => setBillingEnabled(false));
    // Data-driven pair/interval lists; the hardcoded defaults stay on failure.
    getSymbols()
      .then(({ symbols: s, intervals: i }) => {
        if (cancelled) return;
        if (s.length > 0) setSymbols(s);
        if (i.length > 0) setIntervals(i);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Auto-run a shared config once the strategy catalog is loaded, then clean
  // the URL so a refresh doesn't re-run it.
  const sharedRunDone = useRef(false);
  useEffect(() => {
    if (!shared?.autorun || sharedRunDone.current || strategies.length === 0) return;
    if (!strategies.some((s) => s.key === shared.strategy)) return; // stale link
    sharedRunDone.current = true;
    window.history.replaceState({}, "", "/");
    void handleRun(sharedToRequest(shared), "shared link");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategies, shared]);

  async function handleShare(run: Run) {
    const url = shareUrlForResult(run.result);
    try {
      await navigator.clipboard.writeText(url);
      setNotice({ kind: "info", text: "Share link copied — anyone opening it reruns this exact backtest." });
    } catch {
      window.prompt("Copy this share link:", url);
    }
  }

  // Keep a stable handle to the latest refreshMe so the run-once mount effect
  // below can call it without taking `auth` as a dependency.
  const refreshMeRef = useRef(auth.refreshMe);
  refreshMeRef.current = auth.refreshMe;

  // Handle the redirect back from Lemon Squeezy Checkout / Portal (once, on mount).
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const checkout = params.get("checkout");
    if (checkout === "success") {
      setNotice({ kind: "info", text: "Payment received — your Pro plan is being activated." });
      void refreshMeRef.current();
    } else if (checkout === "cancel") {
      setNotice({ kind: "info", text: "Checkout canceled — no charge was made." });
    }
    if (checkout || params.get("portal")) {
      // Clean the URL so a refresh doesn't replay the notice.
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  function addRun(result: BacktestResult, label: string, savedId?: string) {
    setRuns((prev) => {
      const next = [...prev, { id: nextId, label, color: colorForIndex(prev.length), result, savedId }];
      // Keep the most recent MAX_RUNS, re-coloring so colors stay stable left→right.
      return next.slice(-MAX_RUNS).map((r, i) => ({ ...r, color: colorForIndex(i) }));
    });
    setNextId((n) => n + 1);
  }

  function labelFor(
    req: { symbol: string; interval: string; strategy: string; params: Record<string, number> },
    periodLabel?: string,
  ) {
    const strat = strategies.find((s) => s.key === req.strategy);
    const paramStr = Object.entries(req.params)
      .map(([k, v]) => `${k}=${v}`)
      .join(", ");
    const period = periodLabel ? ` · ${periodLabel}` : "";
    return `${req.symbol} ${req.interval} · ${strat?.name ?? req.strategy} (${paramStr})${period}`;
  }

  async function handleRun(req: BacktestRequest, periodLabel?: string) {
    setBusy(true);
    setRunErr(null);
    try {
      const result = await runBacktest(req);
      addRun(result, labelFor(req, periodLabel));
    } catch (e) {
      setRunErr(e instanceof ApiError ? e.message : String((e as Error).message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave(run: Run) {
    if (!signedIn) {
      setNotice({ kind: "info", text: "Sign in to save backtests." });
      return;
    }
    const name = window.prompt("Name this backtest:", run.label.slice(0, 120));
    if (name === null) return; // cancelled
    setRuns((prev) => prev.map((r) => (r.id === run.id ? { ...r, saving: true } : r)));
    setNotice(null);
    try {
      const saved = await saveBacktest(resultToRequest(run.result, name.trim() || run.label));
      setRuns((prev) =>
        prev.map((r) => (r.id === run.id ? { ...r, saving: false, savedId: saved.id } : r)),
      );
      setSavedReload((k) => k + 1);
      await auth.refreshMe(); // usage counter moved
      setNotice({ kind: "info", text: "Saved." });
    } catch (e) {
      setRuns((prev) => prev.map((r) => (r.id === run.id ? { ...r, saving: false } : r)));
      if (e instanceof ApiError && e.status === 402) {
        setNotice({ kind: "warn", text: e.message, action: billingEnabled ? "upgrade" : undefined });
      } else if (e instanceof ApiError && e.status === 401) {
        setNotice({ kind: "warn", text: "Your session expired — sign in again." });
        auth.signOut();
      } else {
        setNotice({ kind: "warn", text: `Couldn’t save: ${(e as Error).message}` });
      }
    }
  }

  async function handleLoadSaved(id: string) {
    if (runs.some((r) => r.savedId === id)) return; // already on screen
    try {
      const detail = await getSaved(id);
      addRun(savedToResult(detail), detail.name || labelFor(detail), id);
    } catch (e) {
      setNotice({ kind: "warn", text: `Couldn’t load: ${(e as Error).message}` });
    }
  }

  async function handleDeleteSaved(id: string) {
    if (!window.confirm("Delete this saved backtest?")) return;
    try {
      await deleteSaved(id);
      setSavedReload((k) => k + 1);
      await auth.refreshMe();
      // Detach the savedId from any on-screen run so its Save button returns.
      setRuns((prev) => prev.map((r) => (r.savedId === id ? { ...r, savedId: undefined } : r)));
    } catch (e) {
      setNotice({ kind: "warn", text: `Couldn’t delete: ${(e as Error).message}` });
    }
  }

  async function handleUpgrade() {
    if (!signedIn) {
      setNotice({ kind: "info", text: "Sign in first, then upgrade to Pro." });
      return;
    }
    try {
      const { url } = await startCheckout();
      window.location.href = url; // hand off to Lemon Squeezy-hosted Checkout
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : (e as Error).message;
      setNotice({ kind: "warn", text: `Couldn’t start checkout: ${msg}` });
    }
  }

  async function handleManageBilling() {
    try {
      const { url } = await openPortal();
      window.location.href = url;
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : (e as Error).message;
      setNotice({ kind: "warn", text: `Couldn’t open billing portal: ${msg}` });
    }
  }

  function removeRun(id: number) {
    setRuns((prev) =>
      prev.filter((r) => r.id !== id).map((r, i) => ({ ...r, color: colorForIndex(i) })),
    );
  }

  const series: EquitySeries[] = runs.map((r) => ({
    label: r.label,
    color: r.color,
    points: r.result.equity_curve,
  }));

  return (
    <div className="app">
      <header className="app-header">
        <button className="brand" onClick={() => navigate("landing")} title="Home">
          <h1>BacktestLab</h1>
          <p className="tagline">
            Backtest crypto strategies on real Binance history — no code, no custody.
          </p>
        </button>
        <AuthBar
          me={auth.me}
          signedIn={signedIn}
          billingEnabled={billingEnabled}
          mode={auth.mode}
          onSignInDev={auth.signInDev}
          onSignIn={auth.signIn}
          onSignUp={auth.signUp}
          onSignOut={auth.signOut}
          onUpgrade={handleUpgrade}
          onManageBilling={handleManageBilling}
        />
      </header>

      {apiStatus === "waking" && (
        <div className="running-bar wake-banner">
          <span className="spinner" /> Waking the API — free hosting spins down when idle,
          the first load can take up to a minute…
        </div>
      )}

      {view === "landing" ? (
        <Landing onLaunch={() => navigate("app")} />
      ) : view === "terms" || view === "refunds" ? (
        <Legal page={view} onBack={() => navigate("landing")} />
      ) : (
        AppLab()
      )}

      <footer className="app-footer">
        <p className="footer-disclaimer">{DISCLAIMER_SHORT}</p>
        <p className="footer-links">
          <a
            href="/terms"
            onClick={(e) => {
              e.preventDefault();
              navigate("terms");
            }}
          >
            Terms of Service
          </a>
          {" · "}
          <a
            href="/refunds"
            onClick={(e) => {
              e.preventDefault();
              navigate("refunds");
            }}
          >
            Refund Policy
          </a>
        </p>
        <p className="footer-meta">
          BacktestLab · research tool · data from Binance public API
        </p>
      </footer>
    </div>
  );

  // The lab view (config → results + comparison + saving). Kept as a closure so
  // it shares App state without prop-drilling.
  function AppLab() {
    return (
      <>
        {loadErr && <div className="banner error">Couldn’t load strategies: {loadErr}</div>}
      {notice && (
        <div className={`banner ${notice.kind === "warn" ? "warn" : "info"}`}>
          {notice.text}
          {notice.action === "upgrade" && (
            <button className="upgrade-btn banner-upgrade" onClick={handleUpgrade}>
              Upgrade to Pro
            </button>
          )}
          <button className="banner-close" onClick={() => setNotice(null)} aria-label="Dismiss">
            ×
          </button>
        </div>
      )}

      <main className="layout">
        <div className="sidebar">
          <section className="panel config-panel">
            <h2>Configure</h2>
            {strategies.length > 0 ? (
              <StrategyForm
                strategies={strategies}
                symbols={symbols}
                intervals={intervals}
                busy={busy}
                onRun={handleRun}
                initial={shared ?? undefined}
              />
            ) : (
              !loadErr && <p className="muted">Loading strategies…</p>
            )}
            {runErr && <div className="banner error inline">{runErr}</div>}
          </section>

          <section className="panel saved-panel">
            <h2>
              Saved backtests
              {signedIn && auth.me && auth.me.monthly_limit !== null && (
                <span
                  className={`usage-chip${(auth.me.remaining ?? 0) === 0 ? " full" : ""}`}
                  title="Free-tier saved backtests this month; Pro is unlimited"
                >
                  {auth.me.usage_this_month}/{auth.me.monthly_limit} this month
                </span>
              )}
            </h2>
            <SavedList
              signedIn={signedIn}
              reloadKey={savedReload}
              onLoad={handleLoadSaved}
              onDelete={handleDeleteSaved}
            />
          </section>
        </div>

        <section className="panel results-panel">
          <div className="results-head">
            <h2>
              Results{" "}
              {runs.length > 1 && <span className="compare-badge">comparing {runs.length}</span>}
            </h2>
            {runs.length > 0 && (
              <button className="link-btn" onClick={() => setRuns([])}>
                Clear all
              </button>
            )}
          </div>

          {busy && (
            <div className="running-bar">
              <span className="spinner" /> Running backtest on real history…
            </div>
          )}

          {runs.length === 0 ? (
            busy ? null : (
              <div className="empty-state">
                <p>Run a backtest to see the equity curve and stats here.</p>
                <p className="muted">Run more than one to compare them side by side.</p>
                <ol className="empty-steps">
                  <li>Pick a pair &amp; period</li>
                  <li>Choose a strategy</li>
                  <li>Run the backtest</li>
                </ol>
              </div>
            )
          ) : (
            <>
              <EquityChart series={series} />

              <div className="legend">
                {runs.map((r) => (
                  <span className="legend-item" key={r.id}>
                    <span className="swatch" style={{ background: r.color }} />
                    {r.label}
                    <button
                      className="legend-remove"
                      onClick={() => removeRun(r.id)}
                      title="Remove"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>

              <div className={`compare-grid cols-${Math.min(runs.length, MAX_RUNS)}`}>
                {runs.map((r) => (
                  <div className="compare-col" key={r.id}>
                    <div className="compare-col-head">
                      <h3 className="compare-title">
                        <span className="swatch" style={{ background: r.color }} />
                        {r.label}
                      </h3>
                      <button
                        className="share-btn"
                        onClick={() => handleShare(r)}
                        title="Copy a link that reruns this exact backtest"
                      >
                        Share
                      </button>
                      {r.savedId ? (
                        <span className="saved-badge">
                          <svg
                            viewBox="0 0 24 24"
                            width="12"
                            height="12"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="3"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            aria-hidden="true"
                          >
                            <path d="M5 13l4 4L19 7" />
                          </svg>
                          Saved
                        </span>
                      ) : (
                        <button
                          className="save-btn"
                          onClick={() => handleSave(r)}
                          disabled={r.saving}
                        >
                          {r.saving ? "Saving…" : "Save"}
                        </button>
                      )}
                    </div>
                    <StatsPanel result={r.result} />
                    <TradesTable trades={r.result.trades} />
                  </div>
                ))}
              </div>

              <p className="disclaimer">{runs[runs.length - 1].result.disclaimer}</p>
            </>
          )}
        </section>
      </main>
      </>
    );
  }
}
