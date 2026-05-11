# SPDX-License-Identifier: Apache-2.0
"""AUTH-01..06 — PyJWT mint/decode helpers.

AUTH-06 is the LOAD-BEARING SECURITY GATE: alg=none attack must be rejected.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from app.auth import decode_jwt, mint_jwt
from app.config import Settings


@pytest.fixture
def settings():
    return Settings(
        GEMINI_API_KEY="g",
        OPENROUTER_API_KEY="o",
        JWT_SECRET="test-secret-padded-to-be-at-least-32-bytes-long",
        REDIS_URL="memory://",
    )


def test_auth_01_mint_returns_token_and_expiry(settings):
    token, exp = mint_jwt("a" * 32, "0.1.0", settings)
    assert isinstance(token, str) and token.count(".") == 2
    assert exp.tzinfo is not None  # tz-aware
    claims = pyjwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    assert claims["install_uuid"] == "a" * 32
    assert claims["ver"] == "0.1.0"
    assert isinstance(claims["iat"], int)
    assert isinstance(claims["exp"], int)
    diff = claims["exp"] - claims["iat"]
    assert abs(diff - settings.JWT_TTL_DAYS * 86400) <= 2


def test_auth_02_decode_round_trip(settings):
    token, _ = mint_jwt("b" * 32, "0.2.0", settings)
    claims = decode_jwt(token, settings)
    assert claims["install_uuid"] == "b" * 32
    assert claims["ver"] == "0.2.0"
    assert "iat" in claims and "exp" in claims


def test_auth_03_expired_token_raises(settings):
    now = datetime.now(tz=timezone.utc)
    past = now - timedelta(seconds=10)
    expired = pyjwt.encode(
        {
            "install_uuid": "c" * 32,
            "iat": int((now - timedelta(days=1)).timestamp()),
            "exp": int(past.timestamp()),
            "ver": "0.1.0",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_jwt(expired, settings)


def test_auth_04_bad_signature_raises(settings):
    token = pyjwt.encode(
        {"install_uuid": "d" * 32, "iat": 0, "exp": 9999999999, "ver": "0.1.0"},
        "different-secret-also-padded-to-32-bytes-min",
        algorithm="HS256",
    )
    with pytest.raises(pyjwt.InvalidSignatureError):
        decode_jwt(token, settings)


def test_auth_05_malformed_token_raises(settings):
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_jwt("not.a.jwt", settings)
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_jwt("", settings)


def test_auth_06_alg_none_blocked(settings):
    """AUTH-06 — LOAD-BEARING SECURITY GATE.

    PyJWT requires explicit options to encode alg=none. We forge a token with
    alg=none and assert decode_jwt rejects it because the algorithm allowlist
    is exactly ['HS256']. If this test fails, the proxy is exploitable.
    """
    evil = pyjwt.encode(
        {"install_uuid": "e" * 32, "iat": 0, "exp": 99999999999},
        "",
        algorithm="none",
    )
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_jwt(evil, settings)
