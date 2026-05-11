# SPDX-License-Identifier: Apache-2.0
"""FastAPI app factory. Wave 1 ships ONLY the scaffold + healthz.

Plan 05-02 adds JWT middleware + /register router.
Plan 05-03 adds the LLM (/v1beta/models/{model}:streamGenerateContent
+ /v1beta/models/{model}:generateContent) and TTS (/v1/audio/speech)
routers + the slowapi limiter binding.
"""

from __future__ import annotations

from fastapi import FastAPI


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

    return app


app = make_app()
