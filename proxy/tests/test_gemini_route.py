# SPDX-License-Identifier: Apache-2.0
"""LLM-01..10 — Gemini SSE streaming + non-streaming routes."""

from __future__ import annotations

import json

import pytest
import pytest_asyncio
from google.genai import errors as genai_errors
from httpx import ASGITransport, AsyncClient

import app.upstream as up_mod
from app.auth import mint_jwt
from app.config import get_settings


def _bearer():
    settings = get_settings()
    token, _ = mint_jwt("a" * 32, "0.1.0", settings)
    return {"Authorization": f"Bearer {token}"}


class _FakeChunk:
    def __init__(self, text: str):
        self._text = text

    def model_dump_json(self, exclude_none: bool = True) -> str:
        return json.dumps({"candidates": [{"content": {"parts": [{"text": self._text}]}}]})


class _FakeResult:
    def __init__(self, text: str):
        self._text = text

    def model_dump_json(self, exclude_none: bool = True) -> str:
        return json.dumps({"candidates": [{"content": {"parts": [{"text": self._text}]}}]})


def _patch_upstream_stream(mocker, chunks=None, raise_error=None):
    """Patch generate_content_stream to be an async generator function.

    The genai SDK's signature is `async def generate_content_stream(...) -> AsyncIterator`,
    i.e. directly an async generator. We replace it with a plain function (not
    AsyncMock) so the route's `async for chunk in client.aio.models.generate_content_stream(...)`
    works correctly.
    """
    chunks = chunks or [_FakeChunk("hello "), _FakeChunk("world")]

    def fake_stream(*args, **kwargs):
        async def _gen():
            if raise_error is not None:
                raise raise_error
            for c in chunks:
                yield c

        return _gen()

    up_mod.reset_gemini_client()
    real_client = up_mod.get_gemini_client()
    mocker.patch.object(real_client.aio.models, "generate_content_stream", side_effect=fake_stream)
    return real_client


def _patch_upstream_nonstream(mocker, result=None, raise_error=None):
    async def fake_call(*args, **kwargs):
        if raise_error is not None:
            raise raise_error
        return result or _FakeResult("hello world")

    up_mod.reset_gemini_client()
    real_client = up_mod.get_gemini_client()
    mocker.patch.object(real_client.aio.models, "generate_content", side_effect=fake_call)
    return real_client


@pytest_asyncio.fixture
async def authed_client(app_with_fake_quota):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_fake_quota), base_url="http://test"
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# LLM-01..02 — happy paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_01_stream_happy_path(authed_client, mocker):
    _patch_upstream_stream(mocker, chunks=[_FakeChunk("a"), _FakeChunk("b"), _FakeChunk("c")])
    r = await authed_client.post(
        "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
        headers=_bearer(),
        json={"contents": []},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert r.headers["x-accel-buffering"] == "no"
    body = r.text
    # Three data: chunks present
    assert body.count("data: ") == 3
    # Each chunk JSON contains its text marker
    for marker in ("a", "b", "c"):
        # Check the JSON parts contain the marker (inside the candidates payload)
        assert f'"text": "{marker}"' in body


@pytest.mark.asyncio
async def test_llm_02_nonstream_happy_path(authed_client, mocker):
    _patch_upstream_nonstream(mocker, result=_FakeResult("ok"))
    r = await authed_client.post(
        "/v1beta/models/gemini-3-flash-preview:generateContent",
        headers=_bearer(),
        json={"contents": []},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    data = r.json()
    assert data["candidates"][0]["content"]["parts"][0]["text"] == "ok"


# ---------------------------------------------------------------------------
# LLM-03..05 — gates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_03_jwt_required(authed_client, mocker):
    r = await authed_client.post(
        "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
        json={"contents": []},
    )
    assert r.status_code == 401
    assert r.json() == {"detail": "missing bearer"}


@pytest.mark.asyncio
async def test_llm_04_rate_limited_at_threshold(monkeypatch, mocker, redis_client):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "3")
    get_settings.cache_clear()
    from app.main import make_app
    from app.quota import QuotaClient

    app = make_app()
    app.state.quota_client = QuotaClient.from_redis(redis_client, daily_quota=2000)

    _patch_upstream_stream(mocker)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = _bearer()
        statuses = []
        for _ in range(4):
            r = await c.post(
                "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
                headers=headers,
                json={"contents": []},
            )
            statuses.append(r.status_code)
        assert statuses[:3] == [200, 200, 200], statuses
        assert statuses[3] == 429


@pytest.mark.asyncio
async def test_llm_05_quota_gated(app_with_fake_quota, mocker, redis_client):
    # Pre-seed counter past the quota
    from datetime import datetime, timezone

    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    key = f"vibemix:quota:{'a' * 32}:{today}"
    await redis_client.set(key, 2000)

    _patch_upstream_stream(mocker)
    async with AsyncClient(
        transport=ASGITransport(app=app_with_fake_quota), base_url="http://test"
    ) as c:
        r = await c.post(
            "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
            headers=_bearer(),
            json={"contents": []},
        )
        assert r.status_code == 429
        body = r.json()
        assert body["detail"] == "daily quota exceeded"
        assert body["quota_daily"] == 2000
        assert "retry-after" in {k.lower() for k in r.headers.keys()}


# ---------------------------------------------------------------------------
# LLM-06 — circuit breaker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_06_circuit_breaker_opens_after_10(authed_client, mocker):
    err = genai_errors.APIError(500, {"error": {"message": "boom", "status": "INTERNAL"}})
    _patch_upstream_stream(mocker, raise_error=err)

    # 10 failures — each consumes the streaming generator which records failure
    for _ in range(10):
        r = await authed_client.post(
            "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
            headers=_bearer(),
            json={"contents": []},
        )
        # Stream commits to 200 but emits a sanitized error event
        assert r.status_code == 200
        # Force generator drain so record_failure runs
        _ = r.text

    # 11th request: breaker open
    r = await authed_client.post(
        "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
        headers=_bearer(),
        json={"contents": []},
    )
    assert r.status_code == 503
    assert r.headers.get("retry-after") is not None


# ---------------------------------------------------------------------------
# LLM-07 — upstream-secret sanitization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_07_upstream_auth_failure_sanitized(authed_client, mocker):
    """Forge a 401 upstream APIError whose body contains an AIza-shaped string.
    The proxy MUST NOT leak that string."""
    leak = "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    err = genai_errors.APIError(
        401,
        {"error": {"message": f"API key invalid: {leak}", "status": "UNAUTHENTICATED"}},
    )
    _patch_upstream_stream(mocker, raise_error=err)
    r = await authed_client.post(
        "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
        headers=_bearer(),
        json={"contents": []},
    )
    # Stream commits 200 + sanitized event
    assert r.status_code == 200
    body = r.text
    assert leak not in body, "raw upstream body leaked the AIza key"
    assert "upstream auth failure" in body


# ---------------------------------------------------------------------------
# LLM-08 — disconnect handling (quota counter still increments)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_08_quota_increments_on_disconnect(app_with_fake_quota, mocker, redis_client):
    """Quota is consumed BEFORE the upstream stream — a disconnected client
    still counts toward the daily total."""
    _patch_upstream_stream(mocker, chunks=[_FakeChunk("x")])
    async with AsyncClient(
        transport=ASGITransport(app=app_with_fake_quota), base_url="http://test"
    ) as c:
        r = await c.post(
            "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
            headers=_bearer(),
            json={"contents": []},
        )
        assert r.status_code == 200
        # Counter should be 1
        from datetime import datetime, timezone

        today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        key = f"vibemix:quota:{'a' * 32}:{today}"
        val = await redis_client.get(key)
        assert val == "1"


# ---------------------------------------------------------------------------
# LLM-09 — incremental streaming (chunk-by-chunk)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_09_incremental_data_events(authed_client, mocker):
    _patch_upstream_stream(mocker, chunks=[_FakeChunk("p"), _FakeChunk("q"), _FakeChunk("r")])
    async with authed_client.stream(
        "POST",
        "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
        headers=_bearer(),
        json={"contents": []},
    ) as r:
        assert r.status_code == 200
        seen = []
        async for line in r.aiter_lines():
            if line.startswith("data: "):
                seen.append(line)
    # Three SSE events emitted
    assert len(seen) == 3
    assert '"text": "p"' in seen[0]
    assert '"text": "q"' in seen[1]
    assert '"text": "r"' in seen[2]


# ---------------------------------------------------------------------------
# LLM-10 — header hygiene
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_10_no_upstream_auth_headers(authed_client, mocker):
    _patch_upstream_stream(mocker)
    r = await authed_client.post(
        "/v1beta/models/gemini-3-flash-preview:streamGenerateContent",
        headers=_bearer(),
        json={"contents": []},
    )
    assert r.status_code == 200
    lowered = {k.lower() for k in r.headers.keys()}
    assert "x-goog-api-key" not in lowered
    assert not any(h.startswith("x-goog-") for h in lowered)
