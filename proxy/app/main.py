# SPDX-License-Identifier: Apache-2.0
"""FastAPI app factory. Wave 3 adds LLM (Gemini-native) + TTS (OpenAI-compat)
routes on top of Wave 2's JWT + slowapi infrastructure.

Routes:
- GET  /healthz                                                 (unauth)
- POST /api/vibemix/v1/register                                 (unauth, IP-limited)
- POST /v1beta/models/{model}:streamGenerateContent             (JWT + per-uuid limit + quota)
- POST /v1beta/models/{model}:generateContent                   (JWT + per-uuid limit + quota)
- POST /v1/audio/speech                                         (JWT + per-uuid limit + quota)
"""

from __future__ import annotations

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


def make_app() -> FastAPI:
    """Factory — returns a fresh FastAPI app.

    Tests use this per-test to pick up monkeypatched env. Module-level
    `app = make_app()` is the uvicorn entrypoint.
    """
    app = FastAPI(
        title="vibemix-proxy",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    # Lazy imports — keep app boot fast and let tests monkeypatch env first.
    from app.config import get_settings
    from app.middleware.jwt import JWTMiddleware
    from app.middleware.rate_limit import get_limiter
    from app.quota import QuotaClient
    from app.routes import gemini as gemini_route
    from app.routes import openai_compat as openai_compat_route
    from app.routes import register as register_route

    settings = get_settings()

    # install_uuid-keyed limiter for protected routes (LLM + TTS).
    app.state.limiter = get_limiter(settings)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Production quota client — for tests, conftest overrides app.state.quota_client
    # with a fakeredis-backed instance via QuotaClient.from_redis(...).
    # `memory://` (slowapi's in-memory storage spec) is NOT a real Redis URL —
    # if tests pass that REDIS_URL we defer client construction until override.
    if settings.REDIS_URL.startswith(("redis://", "rediss://", "unix://")):
        app.state.quota_client = QuotaClient(
            settings.REDIS_URL, daily_quota=settings.RATE_LIMIT_PER_DAY
        )
    else:
        app.state.quota_client = None  # test conftest overrides via fakeredis

    # JWTMiddleware added LAST — runs FIRST per request (FastAPI semantics)
    # so request.state.install_uuid is populated before slowapi key_func reads it.
    app.add_middleware(JWTMiddleware)

    # Routes
    register_route.install(app, settings)
    gemini_route.install(app, settings)
    openai_compat_route.install(app, settings)

    return app


app = make_app()
