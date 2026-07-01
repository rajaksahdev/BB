"""Stripe billing service (Phase 5).

Self-contained wrapper around the Stripe SDK. Everything is gated on
``settings.billing_enabled`` so the app runs fine with no Stripe keys (billing
endpoints return 503; the frontend hides upgrade UI). Wire it up by setting
STRIPE_SECRET_KEY, STRIPE_PRICE_PRO and STRIPE_WEBHOOK_SECRET.

Flow:
  - Checkout: create a Customer (once, stored on the user) + a subscription
    Checkout Session for the Pro price; the user pays on Stripe-hosted pages.
  - Webhook: Stripe calls us back; we verify the signature and flip the user's
    tier based on subscription lifecycle events (the source of truth).
  - Portal: Stripe-hosted Customer Portal to manage/cancel the subscription.
"""

import logging

import stripe
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User

logger = logging.getLogger("backtestlab.billing")
settings = get_settings()


class BillingNotConfigured(RuntimeError):
    """Raised when a billing action is attempted without Stripe configured."""


def _client() -> None:
    if not settings.billing_enabled:
        raise BillingNotConfigured(
            "Billing is not configured. Set STRIPE_SECRET_KEY and STRIPE_PRICE_PRO."
        )
    stripe.api_key = settings.stripe_secret_key


def ensure_customer(db: Session, user: User) -> str:
    """Return the user's Stripe customer id, creating the customer if needed."""
    _client()
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    db.commit()
    return customer.id


def create_checkout_session(db: Session, user: User) -> str:
    """Create a subscription Checkout Session and return its hosted URL."""
    customer_id = ensure_customer(db, user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        client_reference_id=str(user.id),
        line_items=[{"price": settings.stripe_price_pro, "quantity": 1}],
        success_url=f"{settings.frontend_url}/?checkout=success",
        cancel_url=f"{settings.frontend_url}/?checkout=cancel",
        allow_promotion_codes=True,
    )
    return session.url


def create_portal_session(db: Session, user: User) -> str:
    """Create a Customer Portal session so the user can manage billing."""
    _client()
    if not user.stripe_customer_id:
        raise BillingNotConfigured("No Stripe customer on file for this user.")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.frontend_url}/?portal=return",
    )
    return session.url


# ---- Webhook handling ----

_ACTIVE_STATUSES = {"active", "trialing", "past_due"}


def _set_tier_by_customer(db: Session, customer_id: str, tier: str, sub_id: str | None) -> None:
    user = db.scalar(select(User).where(User.stripe_customer_id == customer_id))
    if user is None:
        logger.warning("Webhook for unknown customer %s — ignoring.", customer_id)
        return
    user.tier = tier
    user.stripe_subscription_id = sub_id if tier == "pro" else None
    db.commit()
    logger.info("User %s tier -> %s", user.id, tier)


def construct_event(payload: bytes, sig_header: str | None) -> stripe.Event:
    """Verify the Stripe signature and return the parsed event."""
    _client()
    if not settings.stripe_webhook_secret:
        raise BillingNotConfigured("STRIPE_WEBHOOK_SECRET is not set.")
    return stripe.Webhook.construct_event(
        payload, sig_header or "", settings.stripe_webhook_secret
    )


def handle_event(db: Session, event: stripe.Event) -> None:
    """Apply a verified Stripe event to local user state (idempotent)."""
    etype = event["type"]
    obj = event["data"]["object"]

    if etype == "checkout.session.completed":
        # Subscription purchased. Mark Pro and remember the subscription.
        customer_id = obj.get("customer")
        sub_id = obj.get("subscription")
        if customer_id:
            _set_tier_by_customer(db, customer_id, "pro", sub_id)

    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        customer_id = obj.get("customer")
        status = obj.get("status")
        if customer_id:
            tier = "pro" if status in _ACTIVE_STATUSES else "free"
            _set_tier_by_customer(db, customer_id, tier, obj.get("id"))

    elif etype == "customer.subscription.deleted":
        customer_id = obj.get("customer")
        if customer_id:
            _set_tier_by_customer(db, customer_id, "free", None)

    else:
        logger.debug("Unhandled Stripe event type: %s", etype)
