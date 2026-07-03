# Turn on Lemon Squeezy billing (close the Phase 5 gate)

We use **Lemon Squeezy** (a Merchant of Record) instead of Stripe so we can
launch **without waiting on business verification**, and so the provider handles
global sales tax / VAT for us. You can build and test the whole flow in **Test
mode** the moment you sign up; verification/payout details only gate real
payouts, not the build.

This runbook takes you from "no keys" to "a test card upgraded a user and the
webhook flipped their tier" — the Phase 5 Definition-of-Done.

Test card: `4242 4242 4242 4242`, any future expiry, any CVC.

---

## 1. Grab four values from Lemon Squeezy (test mode)

Toggle **Test mode** in the dashboard first (top of the sidebar).

| Env var | Where |
|---|---|
| `LEMONSQUEEZY_API_KEY` | Settings → **API** → create an API key (copy it once). |
| `LEMONSQUEEZY_STORE_ID` | Settings → **Stores** → the store's numeric id. |
| `LEMONSQUEEZY_VARIANT_PRO` | **Products** → new Product "Pro" → add a **recurring** variant (e.g. $9/mo) → open the variant → copy its **id** (a number). |
| `LEMONSQUEEZY_WEBHOOK_SECRET` | Settings → **Webhooks** (created in step 3) — a signing secret you choose. |

## 2. Put them in `backend/.env`

```dotenv
LEMONSQUEEZY_API_KEY=eyJ0eXAi...
LEMONSQUEEZY_STORE_ID=12345
LEMONSQUEEZY_VARIANT_PRO=67890
LEMONSQUEEZY_WEBHOOK_SECRET=your-signing-secret   # fill after step 3
FRONTEND_URL=http://localhost:5173                # where Checkout redirects back
```

Restart the API after editing `.env`. Sanity check billing is now live:

```bash
curl http://127.0.0.1:8000/billing/config
# -> {"enabled": true}   (was {"enabled": false} with no keys)
```

## 3. Expose your local API and register the webhook

Lemon Squeezy has no local CLI (unlike Stripe), so it needs a public URL to
reach your machine. Start a tunnel:

```bash
# either of these:
ngrok http 8000
cloudflared tunnel --url http://localhost:8000
```

Copy the public `https://…` URL, then in **Settings → Webhooks → +**:

- **Callback URL:** `https://<your-tunnel>/billing/webhook`
- **Signing secret:** any random string — put the same value in
  `LEMONSQUEEZY_WEBHOOK_SECRET` and restart the API.
- **Events:** subscribe to the `subscription_*` events (created, updated,
  cancelled, expired, paused, resumed). Our handler acts on any of them and
  derives the tier from the subscription's `status`.

Our webhook is HMAC-SHA256 signature-verified (`X-Signature` header). Tier
mapping:

- status `on_trial` / `active` / `past_due` / `cancelled` → **pro**
  (`cancelled` keeps access until the period ends, then `expired` fires)
- status `expired` / `unpaid` / `paused` → **free**

## 4. Run the upgrade flow

1. Start both servers (`uvicorn app.main:app --reload` and `npm run dev`).
2. In the app, **sign in** with a dev token — email `you@example.com` (dev mode
   accepts `Bearer dev:you@example.com`). This creates a local user, tier `free`.
3. Click **Upgrade to Pro** → you're sent to Lemon Squeezy Checkout → pay with
   `4242 4242 4242 4242`.
4. Lemon Squeezy redirects back to `FRONTEND_URL/?checkout=success` and fires the
   `subscription_created` webhook (watch your tunnel / API logs for the `200`
   from `/billing/webhook`).

## 5. Confirm the tier flipped (the actual gate)

```bash
curl -H "Authorization: Bearer dev:you@example.com" http://127.0.0.1:8000/me
# -> tier should now be "pro"; billing_customer_id / billing_subscription_id set
```

Or in the DB:

```bash
docker exec -it backtestlab-db psql -U backtestlab -d backtestlab \
  -c "select email, tier, billing_customer_id from users;"
```

Also verify the free-tier limit lifted: a `pro` user can save more than
`FREE_MONTHLY_LIMIT` (5) backtests without hitting the `402`.

## 6. Confirm the downgrade

1. Click **Manage billing** → opens the Lemon Squeezy customer portal → cancel
   the subscription.
2. Cancelling sends `subscription_updated` (status `cancelled`, still Pro until
   period end) and later `subscription_expired` (status `expired` → **free**).
   To test the free flip immediately, resend/trigger an `expired` event from the
   dashboard's webhook log.
3. `GET /me` → tier back to **free** once expired.

---

## Going live (later, at launch)

1. Complete the store's business/payout details in Lemon Squeezy and turn **Test
   mode off**. As a Merchant of Record, Lemon Squeezy collects and remits sales
   tax/VAT for you — no per-country tax registration on your side.
2. Recreate the production webhook pointing at
   `https://<your-api-domain>/billing/webhook` with a fresh signing secret.
3. Set the live `LEMONSQUEEZY_*` env vars in Render (the `sync: false` secrets).
4. Do one real end-to-end pass on the live URL.

Until then, **test mode fully closes the Phase 5 build gate** — no verification
required.
