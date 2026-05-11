# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for proxy/tests.

- Autouse `_set_test_env`: deterministic env so every test sees required vars.
- `redis_client`: in-memory fakeredis (no external Redis).
- `app_factory`: callable returning a fresh FastAPI app with quota wired to fakeredis.
- `client`: httpx.AsyncClient bound to a fresh app via ASGITransport.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-do-not-use-in-prod-padded-to-32-bytes")
    # `memory://` keeps slowapi storage pure-Python (no real Redis needed).
    monkeypatch.setenv("REDIS_URL", "memory://")
    # Reset cached settings so each test sees fresh env
    from app.config import get_settings
    from app.upstream import gemini_breaker, openrouter_breaker

    get_settings.cache_clear()
    # Reset breakers between tests so failures don't leak across.
    gemini_breaker.reset()
    openrouter_breaker.reset()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def redis_client():
    from fakeredis import aioredis as fake_aioredis

    r = fake_aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def app_with_fake_quota(redis_client):
    """Return a fresh app with quota_client wired to fakeredis."""
    from app.main import make_app
    from app.quota import QuotaClient

    app = make_app()
    app.state.quota_client = QuotaClient.from_redis(redis_client, daily_quota=2000)
    return app


@pytest_asyncio.fixture
async def client(app_with_fake_quota):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_fake_quota), base_url="http://test"
    ) as c:
        yield c
