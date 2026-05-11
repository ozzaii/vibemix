# SPDX-License-Identifier: Apache-2.0
"""FastAPI app factory. Wave 1 shipped healthz; Wave 2 adds JWT middleware +
/register router + slowapi limiter wiring.

Plan 05-03 adds the LLM (/v1beta/models/{model}:streamGenerateContent
+ /v1beta/models/{model}:generateContent) and TTS (/v1/audio/speech)
routers.
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
    from app.routes import register as register_route

    settings = get_settings()

    # install_uuid-keyed limiter for protected routes (LLM + TTS land in plan 05-03).
    app.state.limiter = get_limiter(settings)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # JWTMiddleware added LAST — runs FIRST per request (FastAPI semantics)
    # so request.state.install_uuid is populated before slowapi key_func reads it.
    app.add_middleware(JWTMiddleware)

    # /register route + its dedicated IP limiter.
    register_route.install(app, settings)

    return app


app = make_app()
