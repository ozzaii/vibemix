# SPDX-License-Identifier: Apache-2.0
"""JWTMiddleware — verifies bearer token on every non-allowlisted request.

Per RESEARCH Q2: this is a BaseHTTPMiddleware subclass added LAST in
main.py via `app.add_middleware(JWTMiddleware)`. FastAPI semantics:
last-added = outermost = runs FIRST on the request path. So this
middleware sets `request.state.install_uuid` BEFORE the slowapi
decorator's key_func runs at route-handler time.
"""

from __future__ import annotations

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.auth import decode_jwt
from app.config import get_settings


class JWTMiddleware(BaseHTTPMiddleware):
    """JWT bearer verification with a literal-set path allowlist."""

    UNAUTH_PATHS: frozenset[str] = frozenset(
        {
            "/healthz",
            "/api/vibemix/v1/register",
            "/docs",
            "/openapi.json",
        }
    )

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        # Allowlist — literal set membership, NOT prefix match.
        if request.url.path in self.UNAUTH_PATHS:
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return JSONResponse({"detail": "missing bearer"}, status_code=401)

        token = auth[7:]  # 'Bearer ' is 7 chars
        settings = get_settings()
        try:
            claims = decode_jwt(token, settings)
        except jwt.ExpiredSignatureError:
            return JSONResponse({"detail": "token expired"}, status_code=401)
        except jwt.InvalidTokenError:
            return JSONResponse({"detail": "invalid token"}, status_code=401)

        request.state.install_uuid = claims["install_uuid"]
        return await call_next(request)
