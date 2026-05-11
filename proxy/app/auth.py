# SPDX-License-Identifier: Apache-2.0
"""PyJWT helpers — HS256 install-UUID bearer tokens.

Per RESEARCH Q3: pyjwt>=2.12.1 (CVE-2026-32597 fix). Algorithm whitelist
is EXPLICIT (['HS256']) — never None, never 'none'. RESEARCH security
table T-05-09 (alg=none bypass) is mitigated here.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

import jwt

from app.config import Settings

JWT_ALG = "HS256"
_ALG_ALLOWLIST = ["HS256"]  # NEVER include 'none' here.


def mint_jwt(install_uuid: str, client_version: str, settings: Settings) -> Tuple[str, datetime]:
    """Mint a fresh JWT. Returns (token, expires_at_utc)."""
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(days=settings.JWT_TTL_DAYS)
    payload = {
        "install_uuid": install_uuid,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "ver": client_version,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALG)
    return token, exp


def decode_jwt(token: str, settings: Settings) -> dict:
    """Decode and validate a JWT.

    Raises:
        jwt.ExpiredSignatureError: token `exp` claim is in the past.
        jwt.InvalidTokenError: bad signature, malformed token,
            wrong algorithm, missing required claims.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=_ALG_ALLOWLIST,  # explicit — defeats alg=none attack
    )
