# SPDX-License-Identifier: Apache-2.0
"""LLM proxy routes — Gemini-native paths per RESEARCH Q1.

The genai SDK builds URLs as `{base_url}/v1beta/models/{model}:streamGenerateContent`.
The vibemix client points `genai.Client(http_options=HttpOptions(base_url=...))`
at this proxy, and the SDK's `generate_content_stream(...)` call lands HERE
unchanged.

Per RESEARCH Q6: SSE pass-through via StreamingResponse + X-Accel-Buffering: no.
Per RESEARCH Q5: quota check via app.state.quota_client.consume(uuid) BEFORE
upstream call. 429 + Retry-After on QuotaExceeded.
Per RESEARCH Common Pattern 3: circuit breaker per-route via upstream.gemini_breaker.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from google.genai import errors as genai_errors
from google.genai import types

from app.config import Settings
from app.quota import QuotaExceeded
from app.upstream import gemini_breaker, get_gemini_client

log = logging.getLogger("vibemix.proxy.gemini")

_LLM_CHUNK_DISCONNECT_INTERVAL = 10  # Check is_disconnected every Nth chunk

_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # Pitfall 2: prevent nginx response buffering
}


def _safe_detail(status: int) -> str:
    if status == 401:
        return "upstream auth failure"
    if 400 <= status < 500:
        return "upstream client error"
    return "upstream server error"


def install(app: FastAPI, settings: Settings) -> None:
    """Mount LLM routes with the install_uuid-keyed limiter."""
    limiter = app.state.limiter
    rate_str = f"{settings.RATE_LIMIT_PER_MIN}/minute"
    router = APIRouter()

    @router.post("/v1beta/models/{model}:streamGenerateContent")
    @limiter.limit(rate_str)
    async def llm_stream(request: Request, model: str):
        # 1. Circuit breaker pre-check
        if not gemini_breaker.allow():
            return JSONResponse(
                {"detail": "upstream unavailable"},
                status_code=503,
                headers={"Retry-After": str(gemini_breaker.retry_after())},
            )

        # 2. Quota check (raises QuotaExceeded → 429)
        install_uuid = request.state.install_uuid
        try:
            await request.app.state.quota_client.consume(install_uuid)
        except QuotaExceeded as e:
            return JSONResponse(
                {
                    "detail": "daily quota exceeded",
                    "quota_daily": settings.RATE_LIMIT_PER_DAY,
                },
                status_code=429,
                headers={"Retry-After": str(e.retry_after_seconds)},
            )

        # 3. Parse upstream-shaped body
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"detail": "invalid json body"}, status_code=400)
        contents = body.get("contents", [])
        raw_config = body.get("generationConfig") or body.get("config") or {}

        # 4. Stream from upstream Gemini
        client_ = get_gemini_client(settings)

        async def stream_generator():
            chunk_count = 0
            try:
                cfg = types.GenerateContentConfig(**raw_config) if raw_config else None
                stream = await client_.aio.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=cfg,
                )
                async for chunk in stream:
                    chunk_count += 1
                    payload = chunk.model_dump_json(exclude_none=True)
                    yield f"data: {payload}\r\n\r\n".encode("utf-8")

                    # Pitfall 7: check disconnect periodically, not every chunk
                    if chunk_count % _LLM_CHUNK_DISCONNECT_INTERVAL == 0:
                        if await request.is_disconnected():
                            break

                gemini_breaker.record_success()
            except asyncio.CancelledError:
                raise
            except genai_errors.APIError as e:
                # Sanitize — never leak upstream body (may contain raw API key)
                gemini_breaker.record_failure()
                status = getattr(e, "code", 500) or 500
                safe = _safe_detail(status)
                log.warning("gemini upstream APIError status=%d", status)
                err = {
                    "error": {
                        "code": status,
                        "message": safe,
                        "status": "UPSTREAM_ERROR",
                    }
                }
                yield f"data: {json.dumps(err)}\r\n\r\n".encode("utf-8")
            except Exception:
                gemini_breaker.record_failure()
                log.exception("gemini upstream unexpected exception")
                err = {
                    "error": {
                        "code": 500,
                        "message": "internal error",
                        "status": "INTERNAL",
                    }
                }
                yield f"data: {json.dumps(err)}\r\n\r\n".encode("utf-8")

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers=_STREAM_HEADERS,
        )

    @router.post("/v1beta/models/{model}:generateContent")
    @limiter.limit(rate_str)
    async def llm_nonstream(request: Request, model: str):
        if not gemini_breaker.allow():
            return JSONResponse(
                {"detail": "upstream unavailable"},
                status_code=503,
                headers={"Retry-After": str(gemini_breaker.retry_after())},
            )
        install_uuid = request.state.install_uuid
        try:
            await request.app.state.quota_client.consume(install_uuid)
        except QuotaExceeded as e:
            return JSONResponse(
                {
                    "detail": "daily quota exceeded",
                    "quota_daily": settings.RATE_LIMIT_PER_DAY,
                },
                status_code=429,
                headers={"Retry-After": str(e.retry_after_seconds)},
            )
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse({"detail": "invalid json body"}, status_code=400)
        contents = body.get("contents", [])
        raw_config = body.get("generationConfig") or body.get("config") or {}
        client_ = get_gemini_client(settings)
        try:
            cfg = types.GenerateContentConfig(**raw_config) if raw_config else None
            result = await client_.aio.models.generate_content(
                model=model,
                contents=contents,
                config=cfg,
            )
            gemini_breaker.record_success()
            return JSONResponse(json.loads(result.model_dump_json(exclude_none=True)))
        except genai_errors.APIError as e:
            gemini_breaker.record_failure()
            status = getattr(e, "code", 500) or 500
            return JSONResponse({"detail": _safe_detail(status)}, status_code=502)
        except Exception:
            gemini_breaker.record_failure()
            log.exception("gemini upstream unexpected exception (non-stream)")
            return JSONResponse({"detail": "internal error"}, status_code=500)

    app.include_router(router)
