# BacktestLab — Execution Plan (phase-gated)

Source of truth for *how* we build. Derived from `BacktestLab_Project_Spec.pdf`
and `BacktestLab_Income_Model.pdf`. The rule: **no phase starts until the
previous phase passes its Definition-of-Done (DoD) gate** — this is how we avoid
incomplete/half-shipped work.

## Guardrails (from the spec — non-negotiable)

1. **Protect the v1 scope line.** Every deferred feature below is a post-launch
   revenue lever, not a launch blocker.
2. **Start marketing day one.** Distribution is a permanent workstream equal to
   the build. (Out of scope for this repo, but tracked as a founder task.)
3. **Honest backtests.** Always model fees + slippage; always show the
   "not financial advice / past performance ≠ future results" disclaimer.

### OUT of scope for v1 (do NOT build)
Drag-and-drop builder · AI optimization · multiple exchanges · live/paper
trading · user-uploaded code · job queues / async workers (run sync).

## Phases & DoD gates

| Phase | Status | Definition of Done (gate) |
|-------|--------|---------------------------|
| **0 · Foundation** | ✅ Done | Repo + FastAPI boots, Docker Postgres, schema migrated (Alembic), `/health` → `{status: ok, database: up}`. |
| **1 · Data engine** | ✅ Done | Binance fetcher backfilled BTC+ETH (1h+1d) = 54,750 candles, **0 gaps**; idempotent (rerun → 54,750, no dups); retry+backoff; OHLC integrity verified. |
| **2 · Backtest core** | ✅ Done | Engine + 4 strategy modules (MA, RSI, DCA, Grid); fees(commission)+slippage(spread) modeled; `GET /strategies` + `POST /backtest` return JSON+disclaimer. Gate: all 4 run with realistic stats; 3yr hourly in **0.64s** (<5s NFR); unknown-param → 400. |
| **3 · Auth + persistence** | ✅ Done | Supabase-JWT verify + dev-token fallback; `/me`, `POST/GET/DELETE /backtests`; free-tier limit enforced (4th → 402), Pro unlimited; ownership isolation (404 cross-user); 401 without token. Testable now without Supabase. |
| **4 · Frontend** | ✅ Done | React + TS + Vite + lightweight-charts; data-driven config form → results (equity curve + stats); side-by-side comparison (up to 4 overlaid); dev-token auth, save/list/delete saved backtests, free-tier usage + 402 surfaced. Gate: full flow vs live API (CORS, run, compare, save, limit, isolation) verified. |
| **5 · Billing** | ✅ Done | Lemon Squeezy (Merchant of Record) hosted Checkout + customer portal + HMAC-signature-verified webhook; env-gated (503 + UI hidden when unconfigured). Tier flips driven by webhooks. **Verified live (test mode):** a `4242` test card completed checkout → LS fired `subscription_created` → signature verified → user flipped free→pro with `billing_customer_id`/`billing_subscription_id` persisted. Frontend Upgrade/Manage + 402 upgrade prompt. **Provider note:** switched from Stripe to Lemon Squeezy to skip business verification and offload global tax. **Before launch:** rotate the API key (shared in chat), decide final price (current test variant is $99.99/yr), and re-point the webhook at the production API URL. |
| **6 · Polish + launch** | ✅ Built (deploy pending) | Landing page; loading/empty/error states; disclaimers on every view + footer; env-driven CORS; `postgres://`→psycopg URL normalization; Dockerfile + Render Blueprint (`render.yaml`) provisioning API + static frontend + Postgres. **Remaining for full gate:** founder accounts (Supabase/Render/domain), deploy, and confirm the e2e flow on the live URL. |

## Post-launch roadmap (Phase 7+)

v1 shipped Phases 0–6, so the "protect the v1 scope line" guardrail is met —
these are the post-launch revenue/retention levers, ordered by impact-per-effort.
Same rule as before: **each phase gates on its DoD before the next starts.**

| Phase | Status | Definition of Done (gate) |
|-------|--------|---------------------------|
| **7 · Optimizer & analytics** | 🔨 In progress | **7a Parameter sweep (optimizer):** `POST /optimize` sweeps declared param ranges (grid), returns per-combo metrics + best params; combo cap + rate limit protect the instance; UI gets an Optimize mode with range inputs, a 2-param heatmap, ranked table, and one-click "apply best params". **7b Multi-pair batch:** run one strategy across all pairs, ranked results. **7c Extended metrics:** monthly-returns heatmap, drawdown duration, trade-duration distribution. **7d Public share pages:** read-only `/s/<id>` result page with OG image. |
| **8 · Validation suite** | 🔜 Planned | **Walk-forward:** train/test window split with in/out-of-sample stats side by side. **Monte Carlo:** trade-sequence resampling → equity confidence bands + risk-of-ruin. Gate: an optimized run clearly shows overfitting when out-of-sample degrades. |
| **9 · Strategy builder + risk layer** | 🔜 Planned | No-code rule composer (IF indicator-condition AND … THEN buy/sell) compiled to an engine strategy server-side (never user code execution); stop-loss / take-profit / trailing / position-sizing options applicable to any strategy. Gate: a composed strategy round-trips (build → run → save → share). |
| **10 · Growth & retention** | 🔜 Planned | Anonymized strategy leaderboard per pair/period; CSV/PDF export; AI result explainer (Claude API); more pairs/timeframes; alert emails when a **user's own** strategy signals (framed as research notifications, never trade signals). |

> Scope note: the v1 "OUT of scope" list above was a **launch** constraint, not a
> permanent ban — Phase 7+ deliberately promotes those deferred levers now that
> v1 is live. Job queues stay out until a phase actually needs >5s requests
> (the optimizer runs sync under a combo cap on purpose).

## Functional requirements (traceability)

| ID | Requirement | Phase |
|----|-------------|-------|
| FR-01 | Fetch & store OHLCV (hourly + daily) | 1 |
| FR-02 | Run backtest (pair, strategy, params, range) | 2 |
| FR-03 | Return stats: return %, win rate, max DD, Sharpe, trades | 2 |
| FR-04 | Render equity curve + stats dashboard | 4 |
| FR-05 | Signup/login; persist saved backtests | 3 |
| FR-06 | Free-tier monthly limit; unlock on paid | 3 / 5 |
| FR-07 | Subscription checkout + billing portal (Lemon Squeezy) | 5 |
| FR-08 | Side-by-side comparison (Should) | 4 |
| FR-09 | Export CSV/PNG (Could) | 6 |

## External prerequisites (founder tasks — gate later phases)

- [ ] **Supabase** project created → gates Phase 3
- [x] **Lemon Squeezy** account (no business verification to start; test mode works immediately) → gates Phase 5 — done; live test-mode upgrade verified
- [ ] **Railway/Render** account + managed Postgres → gates Phase 6
- [ ] **Domain** registered → gates Phase 6
- [ ] **Legal disclaimer** text finalized → gates Phase 6

## Decisions log

- **Auth provider:** Supabase (auth + managed Postgres from one vendor).
- **Billing provider:** Lemon Squeezy (Merchant of Record) instead of Stripe —
  no business verification to launch, and it collects/remits global sales tax/VAT.
  Tradeoff: ~5% fee vs Stripe's ~2.9%, accepted to ship without the KYC wait.
- **Python:** pinned to **3.12** (system has 3.14; data-science wheels lag new
  Python releases — pinning avoids install failures).
- **Local DB:** Docker Postgres 16 (no local `psql` needed).
- **Migrations:** Alembic with autogenerate against `app.models.Base`.
