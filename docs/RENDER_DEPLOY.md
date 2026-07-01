# Render deploy checklist (env vars + first-deploy steps)

Deploy uses the Blueprint in [`render.yaml`](../render.yaml): it provisions the
API (Docker), the static frontend, and a managed Postgres in one shot. The API
Dockerfile runs `alembic upgrade head` on boot, so **schema migrations are
automatic** — you do not run them by hand.

Do it in this order. There's a chicken-and-egg: some vars need URLs that don't
exist until the services are created, so you deploy once, fill the URLs, then
redeploy.

---

## 0. Prereq

`main` is pushed to https://github.com/rajaksahdev/BB (done).

## 1. Create the Blueprint

Render Dashboard → **New ▸ Blueprint** → pick `rajaksahdev/BB`. It reads
`render.yaml` and shows three resources: `backtestlab-db`, `backtestlab-api`,
`backtestlab-web`. Apply. The first build will run; the `sync: false` vars are
empty for now (that's expected — fill them in step 3).

## 2. Note the two URLs Render assigns

After creation you'll have (names may get a random suffix):

- **API:** `https://backtestlab-api.onrender.com`
- **Web:** `https://backtestlab-web.onrender.com`

## 3. Fill the environment variables

### API service (`backtestlab-api`)

| Var | Set by | Value |
|---|---|---|
| `DATABASE_URL` | ✅ auto (Blueprint) | wired from `backtestlab-db` — leave it |
| `APP_ENV` | ✅ auto | `production` |
| `AUTH_DEV_MODE` | ✅ auto | `false` — **never** accept `dev:` tokens in prod |
| `CORS_ORIGINS` | 🔑 you | the **Web URL**, e.g. `https://backtestlab-web.onrender.com` (no trailing slash) |
| `FRONTEND_URL` | 🔑 you | same **Web URL** (Stripe Checkout/Portal redirect target) |
| `SUPABASE_JWT_SECRET` | 🔑 you | Supabase → Project Settings → API → **JWT Secret** |
| `STRIPE_SECRET_KEY` | 🔑 you (later) | `sk_test_…` now / `sk_live_…` at launch. Leave blank → billing stays off (503 + UI hidden) |
| `STRIPE_PRICE_PRO` | 🔑 you (later) | the recurring `price_…` |
| `STRIPE_WEBHOOK_SECRET` | 🔑 you (later) | from the **Dashboard** webhook endpoint (see step 6) — the Stripe CLI is dev-only |

Optional (have sane defaults; override only if needed): `SUPABASE_JWT_AUD`
(`authenticated`), `FREE_MONTHLY_LIMIT` (`5`), `BACKTEST_RATE_LIMIT` (`20`),
`BACKTEST_RATE_WINDOW` (`60`), `LOG_LEVEL` (`info`).

### Web service (`backtestlab-web`)

| Var | Set by | Value |
|---|---|---|
| `VITE_API_URL` | 🔑 you | the **API URL**, e.g. `https://backtestlab-api.onrender.com` |

> ⚠️ **`VITE_API_URL` is baked in at BUILD time** (Vite `import.meta.env`). If
> you set/change it after the first build, you **must trigger a manual redeploy**
> of `backtestlab-web` (Manual Deploy ▸ Clear build cache & deploy) or the old
> value stays compiled into the bundle. Setting env vars alone does nothing for
> a static site until it rebuilds.

After filling API vars, the API redeploys automatically. Redeploy the web
service once `VITE_API_URL` is set.

## 4. Seed the database (REQUIRED — the prod DB starts EMPTY)

Migrations create the tables but there are **no candles**, so every backtest
returns *"not enough data"* until you backfill. Run the backfill against prod
**once**:

- Render → `backtestlab-api` → **Shell** tab, then:

  ```bash
  python -m app.data.run_backfill --symbols BTCUSDT ETHUSDT --intervals 1h 1d
  ```

  (Add `SOLUSDT` etc. if you want more pairs. It's idempotent — safe to rerun;
  it prints a gap report at the end, which should show 0 gaps.)

> Free-plan note: the Shell needs the service running. If Shell isn't available
> on your plan, add a temporary Render **Job** running the same command, or run
> it locally with `DATABASE_URL` pointed at the Render Postgres **external**
> connection string.

## 5. Smoke-test the live app

```bash
curl https://backtestlab-api.onrender.com/health
# -> {"status":"ok","database":"up"}
```

Then in the browser (Web URL): run a backtest → equity curve renders → sign in
(real Supabase login, since dev tokens are off) → save → list. If CORS blocks
the API call, re-check `CORS_ORIGINS` exactly matches the Web origin.

## 6. Stripe in production (do at launch, after verification)

The Stripe **CLI** is for local dev only. In prod you register a Dashboard
webhook:

1. Stripe Dashboard (live) → Developers → **Webhooks** → **Add endpoint**:
   URL = `https://backtestlab-api.onrender.com/billing/webhook`.
2. Subscribe to: `checkout.session.completed`,
   `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`.
3. Copy the endpoint's **Signing secret** (`whsec_…`) → set
   `STRIPE_WEBHOOK_SECRET` on the API service; set the live `STRIPE_SECRET_KEY`
   and `STRIPE_PRICE_PRO` too. API redeploys → `/billing/config` returns
   `{"enabled": true}`.

Until you're verified, you can point these at **test-mode** values and confirm
the whole flow (see [`STRIPE_TEST_MODE.md`](STRIPE_TEST_MODE.md)) — the Phase 5
gate closes in test mode.

---

## Free-tier realities (know before you rely on it)

- **Web service spins down after ~15 min idle** → first request cold-starts
  (~50s). Fine for a demo; upgrade the API to a paid instance before you drive
  real traffic.
- **Free Postgres expires after ~90 days.** For anything you care about, use a
  paid Render DB **or** point `DATABASE_URL` at your **Supabase** Postgres (one
  DB for auth + data). The app normalizes `postgres://` URLs automatically.
- The `render.yaml` sets both services to `plan: free`; bump to paid in the
  dashboard or the Blueprint when you're ready.

## Quick reference — who sets what

- ✅ **Auto (don't touch):** `DATABASE_URL`, `APP_ENV`, `AUTH_DEV_MODE`
- 🔑 **You, from the URLs:** `CORS_ORIGINS`, `FRONTEND_URL`, `VITE_API_URL`
- 🔑 **You, from Supabase:** `SUPABASE_JWT_SECRET`
- 🔑 **You, from Stripe (optional until launch):** `STRIPE_SECRET_KEY`,
  `STRIPE_PRICE_PRO`, `STRIPE_WEBHOOK_SECRET`
