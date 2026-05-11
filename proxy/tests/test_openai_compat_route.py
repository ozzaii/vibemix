# SPDX-License-Identifier: Apache-2.0
"""TTS-01..10 — OpenAI-compatible TTS route + httpx mock + OpenRouter sanitization."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.upstream as up_mod
from app.auth import mint_jwt
from app.config import get_settings


def _bearer():
    settings = get_settings()
    token, _ = mint_jwt("a" * 32, "0.1.0", settings)
    return {"Authorization": f"Bearer {token}"}


_DEFAULT_BODY = {
    "model": "google/gemini-3.1-flash-tts-preview",
    "input": "hello",
    "voice": "Achird",
    "response_format": "pcm",
}


def _install_mock_upstream(
    captured: dict | None = None,
    *,
    status: int = 200,
    body: bytes = b"PCM_BYTES_DATA_AAAAAAAAAAAAAAAAAA",
    sleep_per_chunk: float = 0.0,
):
    """Install an httpx.MockTransport on the upstream singleton."""

    def handler(request: httpx.Request) -> httpx.Response:
        if captured is not None:
            captured["url"] = str(request.url)
            captured["body"] = request.content
            captured["headers"] = dict(request.headers)
        return httpx.Response(status, content=body)

    transport = httpx.MockTransport(handler)
    up_mod.set_http_client(httpx.AsyncClient(transport=transport, timeout=10.0))


@pytest_asyncio.fixture
async def authed_client(app_with_fake_quota):
    async with AsyncClient(
        transport=ASGITransport(app=app_with_fake_quota), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_http():
    yield
    await up_mod.close_http_client()


# ---------------------------------------------------------------------------
# TTS-01 — happy path streams PCM bytes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_01_pcm_streaming_happy_path(authed_client):
    _install_mock_upstream(body=b"\x00\x01\x02\x03" * 1000)
    r = await authed_client.post("/v1/audio/speech", headers=_bearer(), json=_DEFAULT_BODY)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/pcm")
    assert r.headers["x-accel-buffering"] == "no"
    assert len(r.content) == 4000


@pytest.mark.asyncio
async def test_tts_02_jwt_required(authed_client):
    _install_mock_upstream()
    r = await authed_client.post("/v1/audio/speech", json=_DEFAULT_BODY)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_tts_03_rate_limited(monkeypatch, redis_client):
    monkeypatch.setenv("RATE_LIMIT_PER_MIN", "3")
    get_settings.cache_clear()
    from app.main import make_app
    from app.quota import QuotaClient

    _install_mock_upstream()
    app = make_app()
    app.state.quota_client = QuotaClient.from_redis(redis_client, daily_quota=2000)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = _bearer()
        statuses = []
        for _ in range(4):
            r = await c.post("/v1/audio/speech", headers=headers, json=_DEFAULT_BODY)
            statuses.append(r.status_code)
        assert statuses[:3] == [200, 200, 200], statuses
        assert statuses[3] == 429


@pytest.mark.asyncio
async def test_tts_04_quota_gated(app_with_fake_quota, redis_client):
    _install_mock_upstream()
    from datetime import datetime, timezone

    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    key = f"vibemix:quota:{'a' * 32}:{today}"
    await redis_client.set(key, 2000)

    async with AsyncClient(
        transport=ASGITransport(app=app_with_fake_quota), base_url="http://test"
    ) as c:
        r = await c.post("/v1/audio/speech", headers=_bearer(), json=_DEFAULT_BODY)
        assert r.status_code == 429
        assert r.json()["detail"] == "daily quota exceeded"
        assert "retry-after" in {k.lower() for k in r.headers.keys()}


# ---------------------------------------------------------------------------
# TTS-05 — upstream 401 sanitized (no body echo)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_05_upstream_401_sanitized(authed_client):
    """Upstream returns 401 with leaked key in body. Proxy emits 200 + empty
    body (the architectural compromise — see route docstring). Key MUST NOT
    appear in response."""
    leak_body = b'{"error":{"message":"Invalid key: sk-or-v1-ABCDEF0123456789abcdef0123"}}'
    _install_mock_upstream(status=401, body=leak_body)
    r = await authed_client.post("/v1/audio/speech", headers=_bearer(), json=_DEFAULT_BODY)
    assert r.status_code == 200
    assert r.content == b""
    assert b"sk-or-v1-" not in r.content


# ---------------------------------------------------------------------------
# TTS-06 — circuit breaker on 10 consecutive upstream 5xx
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_06_circuit_breaker_opens(authed_client):
    _install_mock_upstream(status=500, body=b"server boom")
    # 10 failures
    for _ in range(10):
        r = await authed_client.post("/v1/audio/speech", headers=_bearer(), json=_DEFAULT_BODY)
        assert r.status_code == 200  # streaming committed
        _ = r.content  # drain
    # 11th — breaker open
    r = await authed_client.post("/v1/audio/speech", headers=_bearer(), json=_DEFAULT_BODY)
    assert r.status_code == 503
    assert r.headers.get("retry-after") is not None


# ---------------------------------------------------------------------------
# TTS-07 — disconnect handling (quota still counted)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_07_quota_counted_even_on_short_stream(app_with_fake_quota, redis_client):
    _install_mock_upstream(body=b"\x00" * 100)
    async with AsyncClient(
        transport=ASGITransport(app=app_with_fake_quota), base_url="http://test"
    ) as c:
        r = await c.post("/v1/audio/speech", headers=_bearer(), json=_DEFAULT_BODY)
        assert r.status_code == 200
        from datetime import datetime, timezone

        today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        key = f"vibemix:quota:{'a' * 32}:{today}"
        val = await redis_client.get(key)
        assert val == "1"


# ---------------------------------------------------------------------------
# TTS-08 — header hygiene (no upstream auth echoed back)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_08_no_auth_echo(authed_client):
    _install_mock_upstream()
    r = await authed_client.post("/v1/audio/speech", headers=_bearer(), json=_DEFAULT_BODY)
    assert r.status_code == 200
    lowered = {k.lower() for k in r.headers.keys()}
    assert "authorization" not in lowered


# ---------------------------------------------------------------------------
# TTS-09 — body forwarded as-is (no fields added/dropped)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_09_body_forwarded_unchanged(authed_client):
    import json

    captured: dict = {}
    _install_mock_upstream(captured=captured)
    body = {
        "model": "google/gemini-3.1-flash-tts-preview",
        "input": "hello world",
        "voice": "Sulafat",
        "response_format": "pcm",
        "instructions": "be brief",
        "speed": 1.0,
    }
    r = await authed_client.post("/v1/audio/speech", headers=_bearer(), json=body)
    assert r.status_code == 200
    upstream_body = json.loads(captured["body"].decode())
    assert upstream_body == body  # identical, no additions or removals
    # Upstream URL is the hardcoded OpenRouter endpoint
    assert captured["url"] == "https://openrouter.ai/api/v1/audio/speech"
    # Upstream auth is the proxy's OPENROUTER_API_KEY
    assert captured["headers"]["authorization"].startswith("Bearer ")
    assert captured["headers"]["authorization"].endswith(get_settings().OPENROUTER_API_KEY)


# ---------------------------------------------------------------------------
# TTS-10 — chunk size — large upstream body arrives at client intact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tts_10_large_body_arrives_intact(authed_client):
    big = b"\xaa" * 12000  # 12KB > chunk_size=4096 → 3+ chunks
    _install_mock_upstream(body=big)
    r = await authed_client.post("/v1/audio/speech", headers=_bearer(), json=_DEFAULT_BODY)
    assert r.status_code == 200
    assert r.content == big
