"""Lemon Squeezy billing service (Phase 5).

Merchant-of-Record billing: we chose Lemon Squeezy over Stripe so we can launch
without business verification and let the provider handle global sales tax/VAT.
Self-contained wrapper over the Lemon Squeezy REST API (there is no official
Python SDK, so we call it with ``httpx``, which the data layer already uses).

Everything is gated on ``settings.billing_enabled`` so the app runs fine with no
keys (billing endpoints return 503; the frontend hides upgrade UI). Wire it up by
setting LEMONSQUEEZY_API_KEY, LEMONSQUEEZY_STORE_ID and LEMONSQUEEZY_VARIANT_PRO
(plus LEMONSQUEEZY_WEBHOOK_SECRET to verify webhooks).

Flow:
  - Checkout: create a hosted checkout for the Pro variant, embedding our user id
    in ``custom_data`` so the webhook can map the purchase back to the user.
  - Webhook: Lemon Squeezy calls us back; we verify the HMAC-SHA256 signature and
    set the user's tier from the subscription's status (the source of truth).
  - Portal: Lemon Squeezy hosts a per-customer portal to manage/cancel; we fetch
    its signed URL for the user's stored customer id.
"""

import hashlib
import hmac
import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User

logger = logging.getLogger("backtestlab.billing")
settings = get_settings()

API_BASE = "https://api.lemonsqueezy.com/v1"
_TIMEOUT = 20.0

# Subscription statuses that grant Pro. A "cancelled" subscription keeps access
# until the paid period ends (Lemon Squeezy then sends a "subscription_expired"
# event), so we keep it Pro until it truly expires.
_PRO_STATUSES = {"on_trial", "active", "past_due", "cancelled"}


class BillingNotConfigured(RuntimeError):
    """Raised when a billing action is attempted without Lemon Squeezy configured."""


def _headers() -> dict[str, str]:
    if not settings.billing_enabled:
        raise BillingNotConfigured(
            "Billing is not configured. Set LEMONSQUEEZY_API_KEY, "
            "LEMONSQUEEZY_STORE_ID and LEMONSQUEEZY_VARIANT_PRO."
        )
    return {
        "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


def create_checkout_session(db: Session, user: User) -> str:
    """Create a hosted Pro checkout and return its URL."""
    headers = _headers()
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {
                    "email": user.email,
                    # Echoed back to us in the webhook's meta.custom_data.
                    "custom": {"user_id": str(user.id)},
                },
                "product_options": {
                    "redirect_url": f"{settings.frontend_url}/?checkout=success",
                },
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": str(settings.lemonsqueezy_store_id),
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": str(settings.lemonsqueezy_variant_pro),
                    }
                },
            },
        }
    }
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(f"{API_BASE}/checkouts", headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()["data"]["attributes"]["url"]


def create_portal_session(db: Session, user: User) -> str:
    """Return the Lemon Squeezy customer-portal URL for this user."""
    headers = _headers()
    if not user.billing_customer_id:
        raise BillingNotConfigured("No Lemon Squeezy customer on file for this user.")
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(
            f"{API_BASE}/customers/{user.billing_customer_id}", headers=headers
        )
        resp.raise_for_status()
        urls = resp.json()["data"]["attributes"].get("urls") or {}
    portal = urls.get("customer_portal")
    if not portal:
        raise BillingNotConfigured("No customer portal URL available yet.")
    return portal


# ---- Webhook handling ----


def verify_signature(payload: bytes, signature: str | None) -> bool:
    """Verify the Lemon Squeezy webhook HMAC-SHA256 signature (hex digest)."""
    if not settings.lemonsqueezy_webhook_secret:
        raise BillingNotConfigured("LEMONSQUEEZY_WEBHOOK_SECRET is not set.")
    if not signature:
        return False
    digest = hmac.new(
        settings.lemonsqueezy_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


def _find_user(
    db: Session, user_id, customer_id, sub_id
) -> User | None:
    """Locate the user by (in order) our custom id, subscription id, customer id."""
    if user_id:
        try:
            found = db.get(User, uuid.UUID(str(user_id)))
        except (ValueError, TypeError):
            found = None
        if found is not None:
            return found
    if sub_id:
        found = db.scalar(
            select(User).where(User.billing_subscription_id == str(sub_id))
        )
        if found is not None:
            return found
    if customer_id:
        return db.scalar(
            select(User).where(User.billing_customer_id == str(customer_id))
        )
    return None


def handle_event(db: Session, event: dict) -> None:
    """Apply a verified Lemon Squeezy webhook to local user state (idempotent)."""
    meta = event.get("meta") or {}
    data = event.get("data") or {}
    attrs = data.get("attributes") or {}
    event_name = meta.get("event_name", "")

    # We only act on subscription lifecycle events.
    if not event_name.startswith("subscription_"):
        logger.debug("Unhandled Lemon Squeezy event: %s", event_name)
        return

    user_id = (meta.get("custom_data") or {}).get("user_id")
    sub_id = data.get("id")
    customer_id = attrs.get("customer_id")
    status = attrs.get("status")

    user = _find_user(db, user_id, customer_id, sub_id)
    if user is None:
        logger.warning(
            "Webhook for unknown user (sub %s customer %s) — ignoring.",
            sub_id,
            customer_id,
        )
        return

    tier = "pro" if status in _PRO_STATUSES else "free"
    if customer_id is not None:
        user.billing_customer_id = str(customer_id)
    user.billing_subscription_id = str(sub_id) if (sub_id and tier == "pro") else None
    user.tier = tier
    db.commit()
    logger.info("User %s tier -> %s (status=%s)", user.id, tier, status)
