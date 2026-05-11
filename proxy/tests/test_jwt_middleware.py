# SPDX-License-Identifier: Apache-2.0
"""MW-01..07 — JWTMiddleware behavior."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
import pytest_asyncio
from fastapi import Request
from httpx import ASGITransport, AsyncClient

from app.auth import mint_jwt
from app.config import get_settings


@pytest_asyncio.fixture
async def stub_app():
    """Build a fresh app with stub routes for middleware testing."""
    from app.main import make_app

    app = make_app()

    @app.get("/some-other-path")
    async def _stub(request: Request):
        return {"uuid": request.state.install_uuid}

    @app.get("/healthz/extra")
    async def _stub_extra():
        return {"ok": True}

    return app


@pytest_asyncio.fixture
async def stub_client(stub_app):
    async with AsyncClient(transport=ASGITransport(app=stub_app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_mw_01_healthz_bypasses_auth(stub_client):
    r = await stub_client.get("/healthz")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_mw_02_register_path_allowlisted(stub_client):
    # /register accepts only POST; GET would 405 BUT crucially not 401.
    r = await stub_client.post(
        "/api/vibemix/v1/register",
        json={"install_uuid": "a" * 32, "client_version": "0.1.0"},
    )
    # 200 (happy path — /register lives in main.py now) or 422 (validation failed),
    # but NOT 401 — that's what we're pinning here.
    assert r.status_code != 401


@pytest.mark.asyncio
async def test_mw_03_missing_bearer_returns_401(stub_client):
    r = await stub_client.get("/some-other-path")
    assert r.status_code == 401
    assert r.json() == {"detail": "missing bearer"}


@pytest.mark.asyncio
async def test_mw_04_malformed_token_returns_401(stub_client):
    r = await stub_client.get("/some-other-path", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401
    assert r.json() == {"detail": "invalid token"}


@pytest.mark.asyncio
async def test_mw_05_expired_token_returns_401(stub_client):
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    expired = pyjwt.encode(
        {
            "install_uuid": "a" * 32,
            "iat": int((now - timedelta(days=2)).timestamp()),
            "exp": int((now - timedelta(seconds=10)).timestamp()),
            "ver": "0.1.0",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    r = await stub_client.get("/some-other-path", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401
    assert r.json() == {"detail": "token expired"}


@pytest.mark.asyncio
async def test_mw_06_valid_token_sets_install_uuid(stub_client):
    settings = get_settings()
    token, _ = mint_jwt("a" * 32, "0.1.0", settings)
    r = await stub_client.get("/some-other-path", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"uuid": "a" * 32}


@pytest.mark.asyncio
async def test_mw_07_allowlist_is_literal_not_prefix(stub_client):
    """`/healthz/extra` is NOT allowlisted — `/healthz` IS, exactly."""
    r = await stub_client.get("/healthz/extra")
    assert r.status_code == 401
