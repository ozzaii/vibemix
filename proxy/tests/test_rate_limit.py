# SPDX-License-Identifier: Apache-2.0
"""RATE-01..04 — install_uuid_key + get_limiter + exception handler wiring."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter
from starlette.requests import Request as StarletteRequest

from app.config import get_settings
from app.middleware.rate_limit import get_limiter, install_uuid_key


def _make_request_with_uuid(uuid_val):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/x",
        "headers": [],
        "query_string": b"",
        "client": ("1.2.3.4", 0),
    }
    req = StarletteRequest(scope)
    if uuid_val is not None:
        req.state.install_uuid = uuid_val
    return req


def test_rate_01_install_uuid_key_returns_value():
    req = _make_request_with_uuid("a" * 32)
    assert install_uuid_key(req) == "a" * 32


def test_rate_02_install_uuid_key_raises_when_missing():
    req = _make_request_with_uuid(None)
    with pytest.raises(RuntimeError):
        install_uuid_key(req)


def test_rate_03_limiter_is_constructed():
    settings = get_settings()
    limiter = get_limiter(settings)
    assert isinstance(limiter, Limiter)


@pytest.mark.asyncio
async def test_rate_04_rate_limit_exceeded_handler_returns_429():
    """Hit any rate-limited route enough times to trigger 429. We use
    /register at rate=2 to keep the test fast."""
    import os

    os.environ["RATE_LIMIT_PER_MIN"] = "2"
    get_settings.cache_clear()
    from app.main import make_app

    app = make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        body = {"install_uuid": "f" * 32, "client_version": "0.1.0"}
        r1 = await c.post("/api/vibemix/v1/register", json=body)
        r2 = await c.post("/api/vibemix/v1/register", json=body)
        r3 = await c.post("/api/vibemix/v1/register", json=body)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 429
