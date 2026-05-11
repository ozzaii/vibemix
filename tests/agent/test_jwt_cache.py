# SPDX-License-Identifier: Apache-2.0
"""JWT-01..07 — jwt_cache.get_or_refresh_jwt behavior.

Tests use httpx.MockTransport to mock /register and a fake keyring store
so no real keychain or network is touched.
"""

from __future__ import annotations

import asyncio
import json
import time

import httpx
import jwt as pyjwt
import pytest

from vibemix.agent import jwt_cache as jc


class _FakeKeyringStore:
    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service, account):
        return self._store.get((service, account))

    def set_password(self, service, account, value):
        self._store[(service, account)] = value


@pytest.fixture
def fake_keyring(monkeypatch):
    store = _FakeKeyringStore()
    monkeypatch.setattr(jc.keyring, "get_password", store.get_password)
    monkeypatch.setattr(jc.keyring, "set_password", store.set_password)
    return store


def _mint_test_jwt(uuid_hex="a" * 32, ttl_seconds=90 * 86400, version="0.1.0", secret="s"):
    now = int(time.time())
    return pyjwt.encode(
        {"install_uuid": uuid_hex, "iat": now, "exp": now + ttl_seconds, "ver": version},
        secret,
        algorithm="HS256",
    )


def _install_mock_transport(monkeypatch, handler):
    """Patch httpx.AsyncClient so it uses our MockTransport."""
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(jc.httpx, "AsyncClient", factory)


def _run(coro):
    return asyncio.run(coro)


def test_jwt_01_empty_keyring_hits_register(fake_keyring, monkeypatch):
    """JWT-01: with no cached JWT, POST /register and cache the result."""
    body_seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        body_seen["url"] = str(req.url)
        body_seen["json"] = json.loads(req.content)
        token = _mint_test_jwt()
        return httpx.Response(200, json={"jwt": token, "expires_at": "x", "quota_daily": 2000})

    _install_mock_transport(monkeypatch, handler)
    new_token = _run(jc.get_or_refresh_jwt("a" * 32, "https://api.altidus.world", "0.1.0"))
    assert new_token.count(".") == 2
    assert body_seen["url"].endswith("/api/vibemix/v1/register")
    assert body_seen["json"] == {"install_uuid": "a" * 32, "client_version": "0.1.0"}
    # Cached
    assert fake_keyring._store[("vibemix", "jwt")] == new_token


def test_jwt_02_valid_cached_jwt_skips_register(fake_keyring, monkeypatch):
    """JWT-02: cached JWT >7 days from expiry — no /register call."""
    call_count = {"n": 0}

    def handler(req):
        call_count["n"] += 1
        return httpx.Response(500)

    _install_mock_transport(monkeypatch, handler)
    fake_keyring._store[("vibemix", "jwt")] = _mint_test_jwt(ttl_seconds=80 * 86400)
    t = _run(jc.get_or_refresh_jwt("a" * 32, "https://api.altidus.world", "0.1.0"))
    assert t == fake_keyring._store[("vibemix", "jwt")]
    assert call_count["n"] == 0


def test_jwt_03_near_expiry_triggers_refresh(fake_keyring, monkeypatch):
    """JWT-03: cached JWT <7 days from expiry → refresh."""

    def handler(req):
        token = _mint_test_jwt(ttl_seconds=90 * 86400)
        return httpx.Response(200, json={"jwt": token, "expires_at": "x", "quota_daily": 2000})

    _install_mock_transport(monkeypatch, handler)
    old = _mint_test_jwt(ttl_seconds=2 * 86400)  # 2 days from expiry
    fake_keyring._store[("vibemix", "jwt")] = old
    new = _run(jc.get_or_refresh_jwt("a" * 32, "https://api.altidus.world", "0.1.0"))
    assert new != old
    assert fake_keyring._store[("vibemix", "jwt")] == new


def test_jwt_04_expired_triggers_refresh(fake_keyring, monkeypatch):
    """JWT-04: already-expired cached JWT → refresh."""

    def handler(req):
        token = _mint_test_jwt(ttl_seconds=90 * 86400)
        return httpx.Response(200, json={"jwt": token, "expires_at": "x", "quota_daily": 2000})

    _install_mock_transport(monkeypatch, handler)
    expired = _mint_test_jwt(ttl_seconds=-10)  # already expired
    fake_keyring._store[("vibemix", "jwt")] = expired
    new = _run(jc.get_or_refresh_jwt("a" * 32, "https://api.altidus.world", "0.1.0"))
    assert new != expired


def test_jwt_05_register_401_raises_runtimeerror(fake_keyring, monkeypatch):
    """JWT-05: /register returns 401 → RuntimeError, NO silent fallback."""

    def handler(req):
        return httpx.Response(401, json={"detail": "invalid"})

    _install_mock_transport(monkeypatch, handler)
    with pytest.raises(RuntimeError, match="proxy /register rejected"):
        _run(jc.get_or_refresh_jwt("a" * 32, "https://api.altidus.world", "0.1.0"))


def test_jwt_06_network_error_propagates(fake_keyring, monkeypatch):
    """JWT-06: httpx.HTTPError propagates (caller in __main__ handles it)."""

    def handler(req):
        raise httpx.ConnectError("no route to host")

    _install_mock_transport(monkeypatch, handler)
    with pytest.raises(httpx.HTTPError):
        _run(jc.get_or_refresh_jwt("a" * 32, "https://api.altidus.world", "0.1.0"))


def test_jwt_07_client_version_propagated(fake_keyring, monkeypatch):
    seen = {}

    def handler(req):
        seen["json"] = json.loads(req.content)
        token = _mint_test_jwt()
        return httpx.Response(200, json={"jwt": token, "expires_at": "x", "quota_daily": 2000})

    _install_mock_transport(monkeypatch, handler)
    _run(jc.get_or_refresh_jwt("b" * 32, "https://api.altidus.world", "9.9.9"))
    assert seen["json"]["client_version"] == "9.9.9"
