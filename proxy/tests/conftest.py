# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for proxy/tests.

- Autouse `_set_test_env`: deterministic env so every test sees required vars.
- `redis_client`: in-memory fakeredis (no external Redis).
- `app`: the FastAPI app built fresh per-test via `make_app()`.
- `client`: httpx.AsyncClient bound to the app via ASGITransport.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _set_test_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-do-not-use-in-prod")
    # `memory://` keeps slowapi storage pure-Python (no real Redis needed).
    monkeypatch.setenv("REDIS_URL", "memory://")
    # Reset cached settings so each test sees fresh env
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def redis_client():
    from fakeredis import aioredis as fake_aioredis

    r = fake_aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest_asyncio.fixture
async def client():
    from app.main import make_app

    app = make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
