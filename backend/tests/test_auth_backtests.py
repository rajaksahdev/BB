"""Phase 3 gates: auth, saved-backtest CRUD, free-tier limit, ownership isolation."""

from tests.conftest import auth, backtest_body

FREE_LIMIT = 5  # Settings.free_monthly_limit default


def test_me_requires_a_token(client):
    assert client.get("/me").status_code == 401


def test_me_rejects_malformed_header(client):
    assert client.get("/me", headers={"Authorization": "Token abc"}).status_code == 401


def test_me_with_dev_token(client):
    r = client.get("/me", headers=auth("alice@example.com"))
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["tier"] == "free"
    assert body["monthly_limit"] == FREE_LIMIT
    assert body["remaining"] == FREE_LIMIT


def test_create_requires_auth(client):
    assert client.post("/backtests", json=backtest_body(name="x")).status_code == 401


def test_save_list_get_delete_roundtrip(client):
    h = auth("bob@example.com")

    created = client.post("/backtests", json=backtest_body(name="My run"), headers=h)
    assert created.status_code == 201
    bid = created.json()["id"]

    listing = client.get("/backtests", headers=h)
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["id"] == bid
    assert rows[0]["name"] == "My run"
    assert "stats" in rows[0]

    detail = client.get(f"/backtests/{bid}", headers=h)
    assert detail.status_code == 200
    d = detail.json()
    assert d["id"] == bid
    assert "equity_curve" in d and "stats" in d

    assert client.delete(f"/backtests/{bid}", headers=h).status_code == 204
    assert client.get(f"/backtests/{bid}", headers=h).status_code == 404


def test_usage_counter_tracks_saves(client):
    h = auth("carol@example.com")
    client.post("/backtests", json=backtest_body(name="r1"), headers=h)
    me = client.get("/me", headers=h).json()
    assert me["usage_this_month"] == 1
    assert me["remaining"] == FREE_LIMIT - 1


def test_free_tier_limit_then_402(client):
    h = auth("dave@example.com")
    for i in range(FREE_LIMIT):
        r = client.post("/backtests", json=backtest_body(name=f"r{i}"), headers=h)
        assert r.status_code == 201
    blocked = client.post("/backtests", json=backtest_body(name="over"), headers=h)
    assert blocked.status_code == 402
    assert "limit" in blocked.json()["detail"].lower()


def test_ownership_isolation(client):
    owner = auth("owner@example.com")
    other = auth("intruder@example.com")

    bid = client.post("/backtests", json=backtest_body(name="secret"), headers=owner).json()["id"]

    # The other user can neither see nor fetch nor delete it.
    assert client.get("/backtests", headers=other).json() == []
    assert client.get(f"/backtests/{bid}", headers=other).status_code == 404
    assert client.delete(f"/backtests/{bid}", headers=other).status_code == 404
    # Owner still has it.
    assert client.get(f"/backtests/{bid}", headers=owner).status_code == 200
