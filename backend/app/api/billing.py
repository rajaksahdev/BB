"""Billing API (FR-07): Lemon Squeezy checkout, customer portal, and webhook.

All endpoints degrade gracefully when Lemon Squeezy is not configured: the action
endpoints return 503 and ``/billing/config`` reports ``enabled: false`` so the
frontend can hide upgrade UI.
"""

import json
import logging

import httpx
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
    """Start a Pro subscription. Returns a Lemon Squeezy-hosted checkout URL."""
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is not configured.")
    if user.tier == "pro":
        raise HTTPException(status_code=409, detail="You already have an active Pro plan.")
    try:
        url = billing.create_checkout_session(db, user)
    except httpx.HTTPError as exc:  # pragma: no cover - network/provider errors
        logger.exception("Lemon Squeezy checkout failed")
        raise HTTPException(status_code=502, detail=f"Billing provider error: {exc}") from exc
    return {"url": url}


@router.post("/portal")
def portal(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    """Open the Lemon Squeezy customer portal to manage/cancel the subscription."""
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is not configured.")
    try:
        url = billing.create_portal_session(db, user)
    except billing.BillingNotConfigured as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except httpx.HTTPError as exc:  # pragma: no cover
        logger.exception("Lemon Squeezy portal failed")
        raise HTTPException(status_code=502, detail=f"Billing provider error: {exc}") from exc
    return {"url": url}


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Receive Lemon Squeezy events. Signature-verified; flips user tier on changes."""
    if not settings.billing_enabled:
        raise HTTPException(status_code=503, detail="Billing is not configured.")
    payload = await request.body()
    sig = request.headers.get("x-signature")
    try:
        valid = billing.verify_signature(payload, sig)
    except billing.BillingNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not valid:
        # Bad or missing signature — reject so the provider retries / flags it.
        raise HTTPException(status_code=400, detail="Invalid webhook signature.")
    try:
        event = json.loads(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}") from exc

    billing.handle_event(db, event)
    return {"received": True}
