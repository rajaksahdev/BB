/**
 * Marketing landing page (Phase 6). Explains the product and routes into the
 * lab. Disclaimers are front-and-center per the spec guardrail.
 */

interface Props {
  onLaunch: () => void;
}

const FEATURES = [
  {
    title: "Real historical data",
    body: "Backtest against actual Binance OHLCV — BTC & ETH, hourly and daily. No toy data.",
  },
  {
    title: "No code required",
    body: "Pick a pair, choose a strategy, drag the sliders. Results in under a second.",
  },
  {
    title: "Honest results",
    body: "Every run models trading fees and slippage. We show return, win rate, drawdown, and Sharpe.",
  },
  {
    title: "Compare side by side",
    body: "Overlay multiple runs to see which parameters actually held up — and save the keepers.",
  },
];

const STRATEGIES = ["Moving Average Crossover", "RSI Reversion", "DCA", "Grid Trading"];

const STEPS = [
  "Pick a pair and a pre-built strategy.",
  "Tune the parameters with sliders.",
  "Run the backtest on real history.",
  "Read the stats, compare, and save.",
];

export default function Landing({ onLaunch }: Props) {
  return (
    <div className="landing">
      <section className="hero">
        <h2 className="hero-title">
          Backtest crypto strategies on <span className="accent">real</span> market history.
        </h2>
        <p className="hero-sub">
          BacktestLab is a no-custody, no-signals research tool. Tune a strategy, run it against
          actual Binance data, and see how it would have performed — fees and slippage included.
        </p>
        <div className="hero-cta">
          <button className="run-btn hero-btn" onClick={onLaunch}>
            Open the lab →
          </button>
          <span className="hero-note">Free to try · no account needed to run</span>
        </div>
        <p className="hero-disclaimer">
          ⚠️ Not financial advice. Past performance does not guarantee future results. BacktestLab
          never holds funds, places trades, or recommends trades.
        </p>
      </section>

      <section className="features">
        {FEATURES.map((f) => (
          <div className="feature-card" key={f.title}>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </div>
        ))}
      </section>

      <section className="how">
        <h3 className="section-title">How it works</h3>
        <ol className="steps">
          {STEPS.map((s, i) => (
            <li key={i}>
              <span className="step-num">{i + 1}</span>
              {s}
            </li>
          ))}
        </ol>
        <p className="strategies-line">
          Strategies included: {STRATEGIES.join(" · ")}.
        </p>
        <button className="run-btn" onClick={onLaunch}>
          Start backtesting
        </button>
      </section>
    </div>
  );
}
