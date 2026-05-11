# SPDX-License-Identifier: Apache-2.0
"""JWT cache with /register-driven refresh.

Per CONTEXT: 90-day JWT TTL. Refresh when <7 days from expiry.
/register is idempotent (RESEARCH Q3); caller passes same install_uuid.

Per CONTEXT decision (locked): on permanent failure (proxy 401, network
broken), raise — NEVER silently fall back to direct mode.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import httpx
import jwt as pyjwt
import keyring
import keyring.errors

log = logging.getLogger("vibemix.jwt_cache")

_SERVICE = "vibemix"
_ACCOUNT_JWT = "jwt"
_JWT_REFRESH_WINDOW_DAYS = 7


def _peek_exp(token: str) -> datetime | None:
    """Read `exp` claim without signature verification (client has no secret)."""
    try:
        claims = pyjwt.decode(token, options={"verify_signature": False})
        exp_ts = int(claims["exp"])
        return datetime.fromtimestamp(exp_ts, tz=UTC)
    except (pyjwt.DecodeError, KeyError, TypeError, ValueError):
        return None


def _needs_refresh(token: str | None) -> bool:
    if not token:
        return True
    exp = _peek_exp(token)
    if exp is None:
        return True
    return exp - datetime.now(tz=UTC) < timedelta(days=_JWT_REFRESH_WINDOW_DAYS)


def _read_cached_jwt() -> str | None:
    try:
        return keyring.get_password(_SERVICE, _ACCOUNT_JWT)
    except keyring.errors.KeyringError as e:
        log.warning("keyring read of cached JWT failed: %s", e.__class__.__name__)
        return None


def _cache_jwt(token: str) -> None:
    try:
        keyring.set_password(_SERVICE, _ACCOUNT_JWT, token)
    except keyring.errors.KeyringError as e:
        log.warning(
            "keyring write of JWT failed: %s — JWT will be re-fetched next launch",
            e.__class__.__name__,
        )


async def get_or_refresh_jwt(install_uuid: str, proxy_base_url: str, client_version: str) -> str:
    """Return a valid JWT for the given install_uuid.

    Hits the proxy's /api/vibemix/v1/register only when cached JWT is
    missing or within 7 days of expiry.

    Raises:
        RuntimeError: proxy /register returned non-200 (sanitized — body NOT echoed).
        httpx.HTTPError: network failure reaching the proxy.
    """
    cached = _read_cached_jwt()
    if not _needs_refresh(cached):
        return cached  # type: ignore[return-value]

    url = f"{proxy_base_url.rstrip('/')}/api/vibemix/v1/register"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            json={"install_uuid": install_uuid, "client_version": client_version},
        )
    if resp.status_code != 200:
        # Sanitize — do not echo response body (could contain misleading info)
        raise RuntimeError(f"proxy /register rejected install_uuid (status={resp.status_code})")
    data = resp.json()
    new_jwt = data["jwt"]
    _cache_jwt(new_jwt)
    return new_jwt
