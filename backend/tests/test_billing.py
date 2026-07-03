"""Phase 5 gates: billing is env-gated, and signed webhooks drive the user's tier.

Provider is Lemon Squeezy (Merchant of Record). We never hit the network here:
config gating, HMAC signature verification, and the tier-flip logic are all
exercised against locally-built, locally-signed webhook payloads.
"""

import hashlib
import hmac
import json
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


def _enable_billing(monkeypatch):
    """Turn billing on for the process-wide (lru_cached) settings instance."""
    s = get_settings()
    monkeypatch.setattr(s, "lemonsqueezy_api_key", "lsq_test_fake")
    monkeypatch.setattr(s, "lemonsqueezy_store_id", "12345")
    monkeypatch.setattr(s, "lemonsqueezy_variant_pro", "67890")
    monkeypatch.setattr(s, "lemonsqueezy_webhook_secret", "whsec_fake")
    return s


def test_billing_config_enabled_when_keys_present(client, monkeypatch):
    _enable_billing(monkeypatch)
    assert client.get("/billing/config").json() == {"enabled": True}


def test_webhook_bad_signature_rejected(client, monkeypatch):
    _enable_billing(monkeypatch)
    r = client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"X-Signature": "deadbeef", "Content-Type": "application/json"},
    )
    assert r.status_code == 400


def test_webhook_valid_signature_upgrades_to_pro(client, monkeypatch):
    s = _enable_billing(monkeypatch)
    uid = _make_user()
    _post_signed(client, s, _sub_event("subscription_created", "active", uid, "sub_1", "cust_1"))
    assert _tier(uid) == "pro"


def test_webhook_expired_downgrades_to_free(client, monkeypatch):
    s = _enable_billing(monkeypatch)
    uid = _make_user()
    _post_signed(client, s, _sub_event("subscription_created", "active", uid, "sub_1", "cust_1"))
    _post_signed(client, s, _sub_event("subscription_expired", "expired", uid, "sub_1", "cust_1"))
    assert _tier(uid) == "free"


def test_handle_event_unknown_user_is_ignored():
    # Should not raise even when no local user matches the event.
    with SessionLocal() as db:
        billing.handle_event(
            db, _sub_event("subscription_expired", "expired", uuid.uuid4(), "ghost", "ghost")
        )


# ---- helpers ----


def _make_user() -> uuid.UUID:
    uid = uuid.uuid4()
    with SessionLocal() as db:
        db.add(User(id=uid, email=f"{uid}@billing.test", tier="free"))
        db.commit()
    return uid


def _tier(uid: uuid.UUID) -> str:
    with SessionLocal() as db:
        return db.get(User, uid).tier


def _sub_event(name: str, status: str, user_id, sub_id: str, customer_id: str) -> dict:
    """Shape a Lemon Squeezy subscription webhook payload."""
    return {
        "meta": {"event_name": name, "custom_data": {"user_id": str(user_id)}},
        "data": {"id": sub_id, "attributes": {"status": status, "customer_id": customer_id}},
    }


def _post_signed(client, settings, body: dict):
    payload = json.dumps(body).encode()
    sig = hmac.new(
        settings.lemonsqueezy_webhook_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    r = client.post(
        "/billing/webhook",
        content=payload,
        headers={"X-Signature": sig, "Content-Type": "application/json"},
    )
    assert r.status_code == 200, r.text
    return r
