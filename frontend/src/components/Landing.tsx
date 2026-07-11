/**
 * Marketing landing page (Phase 6). Explains the product and routes into the
 * lab. Disclaimers are front-and-center per the spec guardrail.
 *
 * The hero shows a decorative, animated "terminal" preview of a backtest —
 * a strategy equity curve vs buy & hold — so visitors see the product's
 * output before they click anything. All numbers in it are illustrative.
 */

interface Props {
  onLaunch: () => void;
}

const TICKS = [
  "Free to run — no account needed",
  "Fees + slippage modeled on every run",
  "Results in under a second",
];

const PROOF = [
  { num: "54,750", label: "real Binance candles" },
  { num: "0", label: "data gaps" },
  { num: "<1s", label: "typical backtest" },
  { num: "4", label: "runs compared side by side" },
];

const STRATEGIES = [
  {
    name: "MA Crossover",
    desc: "Ride trends: buy when the fast average crosses above the slow one.",
    params: "fast · slow",
    spark: (
      <svg className="spark" viewBox="0 0 120 44" aria-hidden="true">
        <path className="spark-muted" d="M4 30 C34 27, 64 22, 116 12" />
        <path
          className="spark-line"
          d="M4 36 C24 38, 34 20, 50 22 C66 24, 76 8, 116 6"
        />
      </svg>
    ),
  },
  {
    name: "RSI Reversion",
    desc: "Buy oversold, sell overbought — fade the extremes.",
    params: "period · buy < · sell >",
    spark: (
      <svg className="spark" viewBox="0 0 120 44" aria-hidden="true">
        <line className="spark-band" x1="4" y1="11" x2="116" y2="11" />
        <line className="spark-band" x1="4" y1="33" x2="116" y2="33" />
        <path
          className="spark-line"
          d="M4 22 L14 10 L24 30 L34 14 L44 34 L54 12 L64 28 L74 10 L84 32 L94 16 L104 30 L116 14"
        />
      </svg>
    ),
  },
  {
    name: "DCA",
    desc: "Buy a fixed amount on a schedule, whatever the price.",
    params: "interval · amount",
    spark: (
      <svg className="spark" viewBox="0 0 120 44" aria-hidden="true">
        <path
          className="spark-line"
          d="M4 38 L18 38 L18 34 L32 34 L32 30 L46 30 L46 27 L60 27 L60 22 L74 22 L74 18 L88 18 L88 12 L102 12 L102 8 L116 8"
        />
      </svg>
    ),
  },
  {
    name: "Grid Trading",
    desc: "Ladder buys and sells across a price range; profit from chop.",
    params: "levels · spacing",
    spark: (
      <svg className="spark" viewBox="0 0 120 44" aria-hidden="true">
        <line className="spark-band" x1="4" y1="10" x2="116" y2="10" />
        <line className="spark-band" x1="4" y1="22" x2="116" y2="22" />
        <line className="spark-band" x1="4" y1="34" x2="116" y2="34" />
        <path
          className="spark-line"
          d="M4 22 L16 10 L28 34 L40 12 L52 32 L64 14 L76 30 L88 10 L100 32 L116 18"
        />
      </svg>
    ),
  },
];

const STEPS = [
  {
    title: "Configure",
    body: "Pick BTC or ETH, choose a strategy, drag the sliders. No code.",
  },
  {
    title: "Run on real history",
    body: "Executes against years of actual Binance data — fees and slippage included.",
  },
  {
    title: "Compare & save",
    body: "Overlay up to four runs on one chart and keep the ones that held up.",
  },
];

/** Illustrative equity curves for the hero preview (not real results). */
const DEMO_STRAT =
  "0,196 28,188 56,193 84,178 112,184 140,165 168,172 196,150 224,158 " +
  "252,138 280,146 308,122 336,131 364,108 392,118 420,92 448,101 " +
  "476,74 504,84 532,58 560,44";
const DEMO_HOLD =
  "0,196 28,180 56,190 84,168 112,186 140,158 168,178 196,150 224,170 " +
  "252,142 280,162 308,132 336,158 364,126 392,150 420,118 448,142 " +
  "476,112 504,132 532,104 560,118";

function DemoTerminal() {
  return (
    <div className="term" aria-hidden="true">
      <div className="term-bar">
        <span className="term-dots">
          <i />
          <i />
          <i />
        </span>
        <span className="term-title">backtest — BTCUSDT · 1h · ma_crossover(20/50)</span>
        <span className="term-chip">0.42s</span>
      </div>
      <div className="term-body">
        <svg className="term-chart" viewBox="0 0 560 220" preserveAspectRatio="none">
          <defs>
            <linearGradient id="demo-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4f7cff" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#4f7cff" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[55, 110, 165].map((y) => (
            <line key={y} className="term-grid" x1="0" y1={y} x2="560" y2={y} />
          ))}
          <polygon
            className="term-area"
            points={`${DEMO_STRAT} 560,220 0,220`}
            fill="url(#demo-fill)"
          />
          <polyline className="term-hold" points={DEMO_HOLD} />
          <polyline className="term-strat" points={DEMO_STRAT} />
          <circle className="term-dot" cx="560" cy="44" r="4" />
        </svg>
        <div className="term-legend">
          <span>
            <i className="term-swatch strat" /> MA cross (20/50)
          </span>
          <span>
            <i className="term-swatch hold" /> Buy &amp; hold
          </span>
        </div>
        <div className="term-stats">
          <div className="tstat">
            <span className="tstat-label">Return</span>
            <span className="tstat-value pos">+148.2%</span>
          </div>
          <div className="tstat">
            <span className="tstat-label">Max DD</span>
            <span className="tstat-value">−17.4%</span>
          </div>
          <div className="tstat">
            <span className="tstat-label">Sharpe</span>
            <span className="tstat-value">1.61</span>
          </div>
          <div className="tstat">
            <span className="tstat-label">Win rate</span>
            <span className="tstat-value">58%</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Landing({ onLaunch }: Props) {
  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-copy">
          <span className="hero-eyebrow">
            <i className="pulse-dot" /> Real Binance OHLCV · BTC &amp; ETH · hourly + daily
          </span>
          <h2 className="hero-title">
            Prove your strategy on <span className="accent">years of real</span> market history.
          </h2>
          <p className="hero-sub">
            BacktestLab is a no-custody, no-signals research tool. Tune a strategy, run it
            against actual market data, and see exactly how it would have performed — fees
            and slippage included.
          </p>
          <div className="hero-cta">
            <button className="run-btn hero-btn" onClick={onLaunch}>
              Open the lab →
            </button>
          </div>
          <ul className="hero-ticks">
            {TICKS.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <DemoTerminal />
      </section>

      <p className="hero-disclaimer">
        ⚠️ Not financial advice. Past performance does not guarantee future results. The chart
        above is illustrative. BacktestLab never holds funds, places trades, or recommends
        trades.
      </p>

      <section className="proof-strip">
        {PROOF.map((p) => (
          <div className="proof-item" key={p.label}>
            <span className="proof-num">{p.num}</span>
            <span className="proof-label">{p.label}</span>
          </div>
        ))}
      </section>

      <section className="strategies">
        <h3 className="section-title">Four strategies, ready to tune</h3>
        <p className="section-sub">
          No code, no formulas — every parameter is a slider. Click one to try it.
        </p>
        <div className="strat-grid">
          {STRATEGIES.map((s) => (
            <button className="strat-card" key={s.name} onClick={onLaunch}>
              {s.spark}
              <span className="strat-name">{s.name}</span>
              <span className="strat-desc">{s.desc}</span>
              <span className="strat-params">{s.params}</span>
              <span className="strat-go">Tune it →</span>
            </button>
          ))}
        </div>
      </section>

      <section className="how">
        <h3 className="section-title">How it works</h3>
        <ol className="how-steps">
          {STEPS.map((s, i) => (
            <li className="how-step" key={s.title}>
              <span className="how-num">{i + 1}</span>
              <span className="how-title">{s.title}</span>
              <span className="how-body">{s.body}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="cta-band">
        <h3 className="cta-title">Stop guessing. Start measuring.</h3>
        <p className="cta-sub">
          Your first backtest is one click away — no sign-up, no card, no code.
        </p>
        <button className="run-btn hero-btn" onClick={onLaunch}>
          Start backtesting
        </button>
      </section>
    </div>
  );
}
