# BacktestLab

AI-assisted crypto strategy backtesting & builder platform. A **no-custody,
no-signals** web app where retail traders pick a pair, choose a pre-built
strategy, tune parameters with sliders, and backtest against real historical
Binance data — no coding required.

> ⚠️ **Not financial advice. Past performance does not guarantee future results.**
> BacktestLab is a research/analytics tool only. It never holds funds, places
> trades, or recommends trades.

## Stack

| Layer | Choice |
|-------|--------|
| Backend / API | Python 3.12 + FastAPI |
| Backtest engine | `backtesting.py` (Phase 2) |
| Database | PostgreSQL (Docker locally, Supabase in prod) |
| Market data | Binance public REST klines |
| Frontend | React + lightweight-charts (Phase 4) |
| Auth | Supabase Auth (Phase 3) |
| Billing | Lemon Squeezy (Merchant of Record) — hosted checkout + portal (Phase 5) |
| Hosting | Railway / Render (Phase 6) |

## Repo layout

```
BB/
├─ backend/
│  ├─ app/
│  │  ├─ main.py            # FastAPI app + CORS + routers
│  │  ├─ config.py          # env-driven settings (pydantic-settings)
│  │  ├─ db.py              # SQLAlchemy engine + session
│  │  ├─ api/               # health, backtest, backtests (saved)
│  │  ├─ backtesting/       # engine + 4 strategy modules
│  │  ├─ data/              # Binance fetcher + backfill
│  │  └─ models/            # Candle, User, SavedBacktest
│  ├─ alembic/             # migrations
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/                # React + TS + Vite + lightweight-charts (Phase 4)
│  └─ src/
│     ├─ api.ts             # typed API client + auth token
│     ├─ useAuth.ts         # dev-token / JWT auth state
│     ├─ App.tsx            # config → results + comparison + saving
│     └─ components/        # StrategyForm, EquityChart, StatsPanel, AuthBar, SavedList
├─ docker-compose.yml       # local Postgres 16
├─ EXECUTION_PLAN.md        # phase-gated build plan + DoD gates
└─ README.md
```

## Local development

Prereqs: Python 3.12 (`backend/.venv`), Docker Desktop, Node 24 (Phase 4+).

```bash
# 1. Start the database
docker compose up -d

# 2. Backend (from backend/)
.venv\Scripts\activate            # Windows
pip install -r requirements.txt   # first time only
alembic upgrade head              # apply migrations
uvicorn app.main:app --reload     # http://127.0.0.1:8000  (docs at /docs)
```

Verify: `GET http://127.0.0.1:8000/health` → `{"status":"ok","database":"up"}`.

```bash
# 3. Frontend (from frontend/, in a second terminal)
npm install                       # first time only
npm run dev                       # http://localhost:5173
```

The frontend reads the API base URL from `frontend/.env` (`VITE_API_URL`,
default `http://127.0.0.1:8000`). With both servers running, pick a pair +
strategy, tune the sliders, and run a backtest; sign in (dev mode accepts any
email) to save runs and compare them side by side.

## Tests

The backend has a pytest suite that locks in the phase Definition-of-Done gates
(health, strategy catalog, backtest engine, auth, saved-backtest CRUD, free-tier
limit, ownership isolation, billing gating + webhook tier flips).

```bash
# from backend/ (needs the Docker Postgres running)
pip install -r requirements-dev.txt   # first time only
python -m pytest                       # creates an isolated 'backtestlab_test' DB
```

The suite is self-contained: it spins up a separate `backtestlab_test` database,
creates the schema, and seeds synthetic candles — it never touches your dev data
and needs no backfill.

## Billing (Phase 5 — Lemon Squeezy)

We use **Lemon Squeezy**, a Merchant of Record, instead of Stripe — so we can go
live without business verification and the provider handles global sales tax/VAT.
Billing is **dormant until you add keys** — with none set, `/billing/*` actions
return `503` and the frontend hides upgrade UI, so the rest of the app runs
untouched. Full walkthrough in [`docs/LEMONSQUEEZY_SETUP.md`](docs/LEMONSQUEEZY_SETUP.md).
To turn it on (test mode):

```bash
# In backend/.env (see .env.example for details):
LEMONSQUEEZY_API_KEY=eyJ0eXAi...
LEMONSQUEEZY_STORE_ID=12345
LEMONSQUEEZY_VARIANT_PRO=67890         # the recurring Pro variant id
LEMONSQUEEZY_WEBHOOK_SECRET=your-signing-secret
FRONTEND_URL=http://localhost:5173

# Lemon Squeezy has no local CLI — expose the API with a tunnel and point a
# dashboard webhook at https://<tunnel>/billing/webhook:
ngrok http 8000
```

Flow: **Upgrade to Pro** → Lemon Squeezy Checkout → on success the
`subscription_created` webhook flips the user to `pro` (unlimited backtests).
**Manage billing** opens the customer portal to cancel; the `subscription_expired`
webhook flips the user back to `free`. Tier is driven entirely by
signature-verified webhooks (the source of truth), never trusted from the client.

## Deploy (Phase 6)

The repo ships a Render Blueprint ([`render.yaml`](render.yaml)) that provisions
the API (Docker), the static frontend, and a managed Postgres in one shot. The
backend image ([`backend/Dockerfile`](backend/Dockerfile)) runs `alembic upgrade
head` on boot and serves on `$PORT`.

**Checklist:**
1. **Supabase** — create a project; copy the JWT secret → `SUPABASE_JWT_SECRET`;
   use its Postgres URL (or Render's) as `DATABASE_URL`. The app normalizes
   `postgres://` URLs automatically.
2. **Render** — New ▸ Blueprint ▸ pick this repo. After first deploy, fill the
   `sync: false` secrets: `CORS_ORIGINS` + `FRONTEND_URL` = the web URL,
   `VITE_API_URL` = the API URL, plus Supabase/Lemon Squeezy keys.
3. **Lemon Squeezy** (optional) — add the `LEMONSQUEEZY_*` keys + a webhook
   pointing at `<api-url>/billing/webhook` (see the Billing section).
4. Set `AUTH_DEV_MODE=false` in prod (the Blueprint already does) so `dev:` tokens
   are rejected.
5. Verify: visit the web URL → run a backtest → sign in → save → upgrade.

> Railway works too: deploy `backend/` from the Dockerfile, host `frontend/` as a
> static site (`npm run build` → `dist/`), provision Postgres, and set the same
> env vars by hand.

## Build status

See [EXECUTION_PLAN.md](EXECUTION_PLAN.md). Currently: **Phases 0–6 built**
(landing page, disclaimers, loading/empty/error states, prod config + deploy
blueprint). Remaining to fully close Phase 6: provision the founder accounts
(Supabase/Render/domain), deploy, and confirm the e2e flow on the live URL.
