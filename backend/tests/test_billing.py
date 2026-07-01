"""Phase 5 gates: billing is env-gated, and webhooks drive the user's tier."""

import uuid

from app import billing
from app.config import get_settings
from app.db import SessionLocal
from app.models import User
from tests.conftest import auth


def test_billing_config_disabled_by_default(client):
    assert client.get("/billing/config").json() == {"enabled": False}


def test_checkout_requires_auth(client):
    assert client.post("/billing/checkout").status_code == 401


def test_checkout_unconfigured_is_503(client):
    r = client.post("/billing/checkout", headers=auth("u@example.com"))
    assert r.status_code == 503


def test_portal_unconfigured_is_503(client):
    r = client.post("/billing/portal", headers=auth("u@example.com"))
    assert r.status_code == 503


def test_webhook_unconfigured_is_503(client):
    assert client.post("/billing/webhook", json={}).status_code == 503


def test_billing_config_enabled_when_keys_present(client, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(s, "stripe_price_pro", "price_fake")
    assert client.get("/billing/config").json() == {"enabled": True}


def _make_user_with_customer(customer_id: str) -> uuid.UUID:
    uid = uuid.uuid4()
    with SessionLocal() as db:
        db.add(
            User(
                id=uid,
                email=f"{uid}@billing.test",
                tier="free",
                stripe_customer_id=customer_id,
            )
        )
        db.commit()
    return uid


def _tier(uid: uuid.UUID) -> str:
    with SessionLocal() as db:
        return db.get(User, uid).tier


def test_webhook_checkout_completed_upgrades_to_pro():
    cust = "cus_" + uuid.uuid4().hex[:10]
    uid = _make_user_with_customer(cust)
    with SessionLocal() as db:
        billing.handle_event(
            db,
            {
                "type": "checkout.session.completed",
                "data": {"object": {"customer": cust, "subscription": "sub_1"}},
            },
        )
    assert _tier(uid) == "pro"


def test_webhook_subscription_deleted_downgrades_to_free():
    cust = "cus_" + uuid.uuid4().hex[:10]
    uid = _make_user_with_customer(cust)
    with SessionLocal() as db:
        billing.handle_event(
            db,
            {"type": "checkout.session.completed", "data": {"object": {"customer": cust, "subscription": "sub_1"}}},
        )
        billing.handle_event(
            db,
            {"type": "customer.subscription.deleted", "data": {"object": {"customer": cust}}},
        )
    assert _tier(uid) == "free"


def test_webhook_unknown_customer_is_ignored():
    # Should not raise even when no local user matches the customer.
    with SessionLocal() as db:
        billing.handle_event(
            db,
            {"type": "customer.subscription.deleted", "data": {"object": {"customer": "cus_ghost"}}},
        )
