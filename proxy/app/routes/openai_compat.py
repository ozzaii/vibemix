# SPDX-License-Identifier: Apache-2.0
"""OpenAI-compatible TTS proxy route.

The vibemix client uses livekit-plugins-openai.TTS(base_url=proxy/v1).
That SDK calls POST {base_url}/audio/speech with OpenAI's body shape.
We proxy to OpenRouter's identical endpoint with our OPENROUTER_API_KEY.

Per RESEARCH Q6 TTS section: PCM streaming via httpx.AsyncClient.stream
with aiter_bytes(chunk_size=4096).
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import Settings
from app.quota import QuotaExceeded
from app.upstream import get_http_client, openrouter_breaker

log = logging.getLogger("vibemix.proxy.tts")

_TTS_UPSTREAM_URL = "https://openrouter.ai/api/v1/audio/speech"
_TTS_CHUNK_SIZE = 4096
_TTS_CHUNK_DISCONNECT_INTERVAL = 50  # Per Pitfall 7

_STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "X-Accel-Buffering": "no",
}


def install(app: FastAPI, settings: Settings) -> None:
    limiter = app.state.limiter
    rate_str = f"{settings.RATE_LIMIT_PER_MIN}/minute"
    router = APIRouter()

    @router.post("/v1/audio/speech")
    @limiter.limit(rate_str)
    async def tts_speech(request: Request):
        # 1. Circuit breaker
        if not openrouter_breaker.allow():
            return JSONResponse(
                {"detail": "upstream unavailable"},
                status_code=503,
                headers={"Retry-After": str(openrouter_breaker.retry_after())},
            )

        # 2. Quota
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

        # 3. Parse body — forward as-is
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"detail": "invalid json body"}, status_code=400)

        http = get_http_client()

        async def stream_pcm():
            chunk_count = 0
            try:
                async with http.stream(
                    "POST",
                    _TTS_UPSTREAM_URL,
                    json=body,
                    headers={
                        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                ) as upstream_resp:
                    if upstream_resp.status_code >= 400:
                        openrouter_breaker.record_failure()
                        # Drain + discard upstream body — sanitize.
                        await upstream_resp.aread()
                        # On upstream 4xx/5xx we cannot change the response
                        # status (StreamingResponse already committed to 200).
                        # Client sees empty body → LiveKit plugin gets silence.
                        # Status is logged loudly for ops debug.
                        log.error("tts upstream status=%d", upstream_resp.status_code)
                        return

                    openrouter_breaker.record_success()
                    async for chunk in upstream_resp.aiter_bytes(chunk_size=_TTS_CHUNK_SIZE):
                        yield chunk
                        chunk_count += 1
                        if chunk_count % _TTS_CHUNK_DISCONNECT_INTERVAL == 0:
                            if await request.is_disconnected():
                                break
            except httpx.HTTPError as e:
                openrouter_breaker.record_failure()
                log.warning("tts upstream httpx error: %s", e.__class__.__name__)
            except Exception:
                openrouter_breaker.record_failure()
                log.exception("tts upstream unexpected exception")

        return StreamingResponse(
            stream_pcm(),
            media_type="audio/pcm",
            headers=_STREAM_HEADERS,
        )

    app.include_router(router)
