# Turn on Stripe billing in TEST mode (close the Phase 5 gate)

You do **not** need business verification for this — Stripe test keys work the
moment you sign up. Verification only gates *live* payments. This runbook takes
you from "no keys" to "a test card upgraded a user and the webhook flipped their
tier", which is the Phase 5 Definition-of-Done.

Everything here uses **Test mode** (toggle top-right of the Stripe Dashboard).
Test card: `4242 4242 4242 4242`, any future expiry, any CVC, any ZIP.

---

## 1. Grab three values from Stripe (test mode)

| Env var | Where |
|---|---|
| `STRIPE_SECRET_KEY` (`sk_test_…`) | Dashboard → Developers → API keys → **Secret key** |
| `STRIPE_PRICE_PRO` (`price_…`) | Dashboard → Product catalog → **+ Add product** → name "Pro", add a **recurring** price (e.g. $9/mo) → open the price → copy its **Price ID** |
| `STRIPE_WEBHOOK_SECRET` (`whsec_…`) | Printed by the Stripe CLI in step 3 (local) — or from a Dashboard webhook endpoint |

## 2. Put them in `backend/.env`

```dotenv
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PRICE_PRO=price_...
STRIPE_WEBHOOK_SECRET=whsec_...        # fill after step 3
FRONTEND_URL=http://localhost:5173     # where Checkout redirects back
```

Restart the API after editing `.env`. Sanity check billing is now live:

```bash
curl http://127.0.0.1:8000/billing/config
# -> {"enabled": true}   (was {"enabled": false} with no keys)
```

## 3. Forward webhooks to your local API (Stripe CLI)

Install the CLI (https://stripe.com/docs/stripe-cli), then:

```bash
stripe login
stripe listen --forward-to localhost:8000/billing/webhook
```

- It prints a `whsec_…` — paste that into `STRIPE_WEBHOOK_SECRET` and restart the API.
- **Leave this terminal running** while you test; it relays events to your machine.

Our webhook is signature-verified and handles exactly these events (all
forwarded by `stripe listen` automatically):

- `checkout.session.completed` → tier **pro**
- `customer.subscription.created` / `updated` → **pro** if active/trialing/past_due, else **free**
- `customer.subscription.deleted` → tier **free**

## 4. Run the upgrade flow

1. Start both servers (`uvicorn app.main:app --reload` and `npm run dev`).
2. In the app, **sign in** with a dev token — email `you@example.com` (dev mode
   accepts `Bearer dev:you@example.com`). This creates a local user, tier `free`.
3. Click **Upgrade to Pro** → you're sent to Stripe Checkout → pay with
   `4242 4242 4242 4242`.
4. Stripe redirects back to `FRONTEND_URL/?checkout=success`, and the
   `checkout.session.completed` webhook fires (watch the `stripe listen`
   terminal — you'll see a `200` back from `/billing/webhook`).

## 5. Confirm the tier flipped (the actual gate)

**Via the API** — the fastest check:

```bash
curl -H "Authorization: Bearer dev:you@example.com" http://127.0.0.1:8000/me
# -> tier should now be "pro"; stripe_customer_id / stripe_subscription_id set
```

**Or in the DB:**

```bash
docker exec -it backtestlab-db psql -U backtestlab -d backtestlab \
  -c "select email, tier, stripe_customer_id from users;"
```

Also verify the free-tier limit lifted: a `pro` user can save more than
`FREE_MONTHLY_LIMIT` (5) backtests without hitting the `402`.

## 6. Confirm the downgrade

1. Click **Manage billing** → opens the Stripe Customer Portal → **Cancel plan**.
2. The `customer.subscription.deleted` (or `.updated` → canceled) webhook fires.
3. `GET /me` → tier back to **free**.

You can also fire events without the UI:

```bash
stripe trigger checkout.session.completed
stripe trigger customer.subscription.deleted
```

(These use Stripe's synthetic objects; for a *real* tier flip on your user,
prefer the actual Checkout flow in step 4 so the customer id matches.)

---

## When verification finishes (going live — later, at launch)

1. Flip the Dashboard to **live** and repeat step 1 with **live** keys
   (`sk_live_…`, a live `price_…`).
2. Create a **Dashboard webhook endpoint** at
   `https://<your-api-domain>/billing/webhook` (the CLI is dev-only) and
   subscribe to the four events above; copy its live `whsec_…`.
3. Set the live `STRIPE_*` env vars in Render (the `sync: false` secrets).
4. Do one real (or Stripe-test-clock) end-to-end pass on the live URL.

Until then, **test mode fully closes the Phase 5 build gate** — no verification
required.
