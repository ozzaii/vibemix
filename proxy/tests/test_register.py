# SPDX-License-Identifier: Apache-2.0
"""REG-01..06 — /api/vibemix/v1/register endpoint behavior."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth import decode_jwt
from app.config import get_settings


@pytest_asyncio.fixture
async def fresh_client():
    """Build a fresh app — needed because tests may monkeypatch env and we
    want each test to pick up fresh settings via make_app()."""
    from app.main import make_app

    app = make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_reg_01_happy_path_returns_jwt(fresh_client):
    r = await fresh_client.post(
        "/api/vibemix/v1/register",
        json={"install_uuid": "a" * 32, "client_version": "0.1.0"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["jwt"] and isinstance(body["jwt"], str)
    assert body["jwt"].count(".") == 2
    assert "expires_at" in body and ("T" in body["expires_at"])
    settings = get_settings()
    assert body["quota_daily"] == settings.RATE_LIMIT_PER_DAY


@pytest.mark.asyncio
async def test_reg_02_jwt_round_trips(fresh_client):
    r = await fresh_client.post(
        "/api/vibemix/v1/register",
        json={"install_uuid": "b" * 32, "client_version": "0.2.0"},
    )
    assert r.status_code == 200
    token = r.json()["jwt"]
    settings = get_settings()
    claims = decode_jwt(token, settings)
    assert claims["install_uuid"] == "b" * 32
    assert claims["ver"] == "0.2.0"


@pytest.mark.parametrize(
    "bad_uuid",
    ["a" * 31, "a" * 33, "A" * 32, "g" * 32],
    ids=["too-short", "too-long", "uppercase", "non-hex"],
)
@pytest.mark.asyncio
async def test_reg_03_bad_uuid_format_422(fresh_client, bad_uuid):
    r = await fresh_client.post(
        "/api/vibemix/v1/register",
        json={"install_uuid": bad_uuid, "client_version": "0.1.0"},
    )
    assert r.status_code == 422


@pytest.mark.parametrize("bad_ver", ["", "x" * 33], ids=["empty", "too-long"])
@pytest.mark.asyncio
async def test_reg_04_bad_client_version_422(fresh_client, bad_ver):
    r = await fresh_client.post(
        "/api/vibemix/v1/register",
        json={"install_uuid": "c" * 32, "client_version": bad_ver},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_reg_05_idempotent_same_uuid(fresh_client):
    body = {"install_uuid": "d" * 32, "client_version": "0.1.0"}
    r1 = await fresh_client.post("/api/vibemix/v1/register", json=body)
    r2 = await fresh_client.post("/api/vibemix/v1/register", json=body)
    assert r1.status_code == 200 and r2.status_code == 200
    settings = get_settings()
    c1 = decode_jwt(r1.json()["jwt"], settings)
    c2 = decode_jwt(r2.json()["jwt"], settings)
    # Both decode to same UUID (idempotent)
    assert c1["install_uuid"] == c2["install_uuid"] == "d" * 32


@pytest.mark.asyncio
async def test_reg_06_ip_keyed_rate_limit(monkeypatch):
    """4th request from same IP at rate=3 returns 429.

    Rebuilds the app under a low rate so the test doesn't have to fire 61 reqs.
    """
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "3")
    from app.config import get_settings as _gs

    _gs.cache_clear()
    from app.main import make_app

    app = make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        body = {"install_uuid": "e" * 32, "client_version": "0.1.0"}
        statuses = []
        for _ in range(4):
            r = await c.post("/api/vibemix/v1/register", json=body)
            statuses.append(r.status_code)
        # First 3 OK, 4th 429
        assert statuses[:3] == [200, 200, 200], statuses
        assert statuses[3] == 429
        # slowapi sets Retry-After
        last = await c.post("/api/vibemix/v1/register", json=body)
        assert last.status_code == 429
