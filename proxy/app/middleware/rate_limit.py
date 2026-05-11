# SPDX-License-Identifier: Apache-2.0
"""slowapi limiter wiring.

Per RESEARCH Q2: we use the @limiter.limit() decorator, NOT
SlowAPIMiddleware. The decorator path runs key_func at handler time,
AFTER JWTMiddleware sets request.state.install_uuid.

Two key funcs:
- install_uuid_key — for protected routes (LLM, TTS in plan 05-03).
- get_remote_address (slowapi.util) — for /register (no install_uuid yet;
  IP-keyed to block register-spam attacks).
"""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter

from app.config import Settings


def install_uuid_key(request: Request) -> str:
    """key_func for install_uuid-keyed limit.

    Raises RuntimeError if request.state.install_uuid is unset — this
    is a wiring bug (route was rate-limited without being JWT-gated),
    not a runtime condition. Crash loudly at impl, not in prod.
    """
    uuid_val = getattr(request.state, "install_uuid", None)
    if not uuid_val:
        raise RuntimeError(
            "install_uuid_key called on a request without "
            "request.state.install_uuid — JWTMiddleware must run before "
            "this rate-limited route"
        )
    return uuid_val


def get_limiter(settings: Settings) -> Limiter:
    """Build the install_uuid-keyed limiter wired to Redis (or memory://)."""
    return Limiter(
        key_func=install_uuid_key,
        storage_uri=settings.REDIS_URL,
        strategy="fixed-window",
        default_limits=[],  # explicit — no global default
    )
