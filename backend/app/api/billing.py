"""Billing API (FR-07): Stripe Checkout, Customer Portal, and webhook.

All endpoints degrade gracefully when Stripe is not configured: the action
endpoints return 503 and ``/billing/config`` reports ``enabled: false`` so the
frontend can hide upgrade UI.
"""

import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import billing
from app.auth import get_current_user
from app.config import get_settings
from app.db import get_db
from app.models import User

logger = logging.getLogger("backtestlab.billing")
settings = get_settings()
router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/config")
def billing_config() -> dict:
    """Tell the frontend whether billing is available (no secrets exposed)."""
    return {"enabled": settings.billing_enabled}


@router.post("/checkout")
def checkout(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Start a Pro subscription. Returns a Stripe-hosted Checkout URL."""
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is not configured.")
    if user.tier == "pro":
        raise HTTPException(status_code=409, detail="You already have an active Pro plan.")
    try:
        url = billing.create_checkout_session(db, user)
    except stripe.StripeError as exc:  # pragma: no cover - network/Stripe errors
        logger.exception("Stripe checkout failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message or exc}") from exc
    return {"url": url}


@router.post("/portal")
def portal(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Open the Stripe Customer Portal to manage/cancel the subscription."""
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is not configured.")
    try:
        url = billing.create_portal_session(db, user)
    except billing.BillingNotConfigured as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except stripe.StripeError as exc:  # pragma: no cover
        logger.exception("Stripe portal failed")
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc.user_message or exc}") from exc
    return {"url": url}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Receive Stripe events. Signature-verified; flips user tier on changes."""
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is not configured.")
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = billing.construct_event(payload, sig)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        # Bad payload or signature — reject so Stripe retries / flags it.
        raise HTTPException(status_code=400, detail=f"Invalid webhook: {exc}") from exc
    except billing.BillingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    billing.handle_event(db, event)
    return {"received": True}
