# SPDX-License-Identifier: Apache-2.0
"""POST /api/vibemix/v1/register — install-UUID → JWT exchange.

Per CONTEXT: idempotent; same UUID returns a fresh JWT every call.
Per RESEARCH Q3: 90-day TTL via mint_jwt.

Rate-limited by IP (NOT install_uuid — caller has no UUID yet at
/register time; IP-keying blocks register-spam abuse). Uses
slowapi.util.get_remote_address as key_func.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import mint_jwt
from app.config import Settings


def _ip_limiter(settings: Settings) -> Limiter:
    """IP-keyed limiter — independent from the install_uuid limiter.

    Bound to the same Redis (or memory://) but uses a distinct key_func.
    """
    return Limiter(
        key_func=get_remote_address,
        storage_uri=settings.REDIS_URL,
        strategy="fixed-window",
        default_limits=[],
    )


class RegisterReq(BaseModel):
    install_uuid: str = Field(min_length=32, max_length=32, pattern=r"^[0-9a-f]{32}$")
    client_version: str = Field(min_length=1, max_length=32)


class RegisterResp(BaseModel):
    jwt: str
    expires_at: str  # ISO 8601 UTC
    quota_daily: int


def install(app: FastAPI, settings: Settings) -> None:
    """Mount the /register router with its dedicated IP limiter.

    Called from main.make_app() after app construction. Keeps the IP
    limiter encapsulated so it doesn't conflict with the install_uuid
    limiter.
    """
    limiter = _ip_limiter(settings)
    rate_str = f"{settings.RATE_LIMIT_PER_MIN}/minute"
    router = APIRouter()

    @router.post("/api/vibemix/v1/register", response_model=RegisterResp)
    @limiter.limit(rate_str)
    async def register(request: Request, body: RegisterReq) -> RegisterResp:
        token, exp = mint_jwt(body.install_uuid, body.client_version, settings)
        return RegisterResp(
            jwt=token,
            expires_at=exp.isoformat(),
            quota_daily=settings.RATE_LIMIT_PER_DAY,
        )

    # Stash the IP limiter on app.state so the global RateLimitExceeded
    # handler can introspect it if needed.
    app.state.register_limiter = limiter
    app.include_router(router)
