# SPDX-License-Identifier: Apache-2.0
"""Proxy-mode genai client builder plus MOSS-only TTS compatibility shim.

Per RESEARCH Q1 verified: genai.Client(http_options=HttpOptions(base_url=...,
headers={Authorization: Bearer JWT})) is the canonical pattern. The SDK's
generate_content_stream(...) works unchanged once base_url + headers are set.

TTS is intentionally not proxied anymore: ``build_proxy_tts_chain`` keeps the old
call signature but returns the same local MOSS-only adapter as direct mode.

Phase 69 Plan 69-03 (OSS-02) — Client-side proxy fallback contract:
when the proxy returns 5xx, times out, refuses the connection, or returns a
non-JSON body, ``classify_proxy_error`` returns a ``ProxyUnavailable`` sentinel;
the caller (dj_cohost.py) catches it and the runtime emits a one-shot
"Co-host unavailable this session" transcript line + skips LLM emission for
the duration. 4xx and 429 are NOT classified — they fall through to existing
per-error messaging (v3.x SHIP-CUT). Anti-slop thesis: when grounding is
missing, refuse to lie. NO silent retries on the 4 trigger classes; the only
automatic re-check is the 60s ``probe_proxy_health`` canary.
"""

from __future__ import annotations

import json

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from livekit.agents import tts as agents_tts


def build_proxy_genai_client(jwt: str, proxy_base_url: str) -> genai.Client:
    """Build a genai.Client pointed at the vibemix proxy.

    The SDK's generate_content_stream(...) works unchanged once base_url and
    Authorization header are set via http_options.
    """
    return genai.Client(
        api_key="vibemix-proxy",  # dummy; proxy ignores x-goog-api-key
        http_options=types.HttpOptions(
            base_url=proxy_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=120_000,  # ms
        ),
    )


def build_proxy_tts_chain(
    jwt: str, proxy_base_url: str, voice: str | None = None
) -> agents_tts.FallbackAdapter:
    """Compatibility shim: proxy mode also uses local MOSS as the only TTS."""
    _ = (jwt, proxy_base_url)
    from vibemix.agent.local_tts import build_local_tts_adapter

    return build_local_tts_adapter(voice=voice)


# ---------------------------------------------------------------------------
# Phase 69 Plan 69-03 (OSS-02) — Client-side fallback surface
# ---------------------------------------------------------------------------
# Reason values for ``ProxyUnavailable``. Pinned by ``tests/integration/
# test_proxy_fallback.py``. Any future trigger class extension MUST update
# this constant + the classifier + the docstring contract above.
_REASON_5XX = "5xx"
_REASON_TIMEOUT = "timeout"
_REASON_CONNECTION_REFUSED = "connection_refused"
_REASON_BAD_BODY = "bad_body"


class ProxyUnavailable(Exception):
    """Sentinel raised when the Bravoh proxy is unreachable for one of the 4
    documented trigger classes (per Plan 69-03 / OSS-02):

    - ``5xx`` — proxy returned HTTP 500 / 502 / 503 / 504.
    - ``timeout`` — request exceeded its timeout (any ``httpx.TimeoutException``).
    - ``connection_refused`` — TCP connect failed (``httpx.ConnectError``).
    - ``bad_body`` — proxy returned non-JSON when JSON was expected
      (``json.JSONDecodeError`` or genai SDK wrapper).

    ``original`` carries the underlying exception (set as ``__cause__`` when the
    caller re-raises via ``raise unavail from exc``) so events.jsonl can record
    the root cause without leaking the wrapped traceback to the user.
    """

    def __init__(self, reason: str, original: Exception | None = None) -> None:
        super().__init__(f"proxy unavailable ({reason})")
        self.reason: str = reason
        self.original: Exception | None = original

    def __repr__(self) -> str:  # pragma: no cover — trivial
        return f"ProxyUnavailable(reason={self.reason!r})"


def classify_proxy_error(exc: Exception) -> ProxyUnavailable | None:
    """Inspect ``exc`` and return a ``ProxyUnavailable`` instance iff the
    exception matches one of the 4 documented trigger classes; else None.

    The 4xx range (including 429) intentionally falls through to None — those
    have their own per-error messaging in the existing v3.x SHIP-CUT path and
    MUST NOT be conflated with "co-host unavailable" (T-69P03-01 anti-
    regression test pins this boundary).

    Programming errors (ValueError, AssertionError, KeyError, etc.) and flow-
    control exceptions (KeyboardInterrupt, SystemExit) are NEVER classified —
    they must propagate to the caller for normal handling.
    """
    # --- 1. Timeout family. Check BEFORE the genai/httpx HTTPStatusError
    # classes so ConnectTimeout (which subclasses both ConnectError AND
    # TimeoutException via httpx.TimeoutException) is classified as timeout,
    # not connection_refused — timeout is the more specific signal.
    if isinstance(exc, httpx.TimeoutException):
        return ProxyUnavailable(_REASON_TIMEOUT, exc)

    # --- 2. Connection refused / network down. httpx.ConnectError wraps the
    # underlying OSError / ConnectionRefusedError. We deliberately do not
    # inspect the str() form — the class identity is the signal.
    if isinstance(exc, httpx.ConnectError):
        return ProxyUnavailable(_REASON_CONNECTION_REFUSED, exc)

    # --- 3. 5xx range. google.genai.errors.APIError (and its ServerError /
    # ClientError subclasses) expose ``.code`` as the HTTP status. The genai
    # SDK's ServerError is raised on 5xx by design; we also accept any
    # APIError with a 5xx code for forward compat. httpx.HTTPStatusError is
    # also accepted as a defensive catch for direct httpx callers.
    code: int | None = None
    if isinstance(exc, genai_errors.APIError):
        # genai >= 2.0 sets .code on construction; default attribute access
        # is safe (the class always sets it). Guard against None just in case.
        raw_code = getattr(exc, "code", None)
        if isinstance(raw_code, int):
            code = raw_code
    elif isinstance(exc, httpx.HTTPStatusError):
        resp = getattr(exc, "response", None)
        raw_code = getattr(resp, "status_code", None)
        if isinstance(raw_code, int):
            code = raw_code
    if code is not None and 500 <= code <= 599:
        return ProxyUnavailable(_REASON_5XX, exc)

    # --- 4. Bad body. json.JSONDecodeError is the canonical Python signal.
    # The genai SDK wraps malformed-body cases in UnknownApiResponseError.
    if isinstance(exc, json.JSONDecodeError):
        return ProxyUnavailable(_REASON_BAD_BODY, exc)
    unknown_resp = getattr(genai_errors, "UnknownApiResponseError", None)
    if unknown_resp is not None and isinstance(exc, unknown_resp):
        return ProxyUnavailable(_REASON_BAD_BODY, exc)

    # Anything else (4xx / 429 / programming errors / flow control): return
    # None so the caller re-raises the original exception unchanged.
    return None


def probe_proxy_health(proxy_base_url: str, timeout_s: float = 5.0) -> bool:
    """Synchronous best-effort canary GET against ``{proxy_base_url}/health``.

    Returns True iff the proxy responds with HTTP 200; False on anything else
    (non-200 status, network error, timeout, malformed URL, etc.). NEVER
    raises — the caller treats False as "still unavailable" and tries again
    on the next 60s tick.

    If the proxy has no ``/health`` endpoint yet (Bravoh ops repo work — see
    KAAN-ACTION-LEGAL.md §V7-PROXY), this returns False perpetually and the
    recovery "Co-host back online" line never fires; this is acceptable
    failure mode — the next real LLM call will succeed once the proxy is up
    and the unavailable flag clears on success. When §V7-PROXY ships /health
    on api.altidus.world, the recovery line fires automatically without any
    client-side change.
    """
    url = f"{proxy_base_url.rstrip('/')}/health"
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.get(url)
            return resp.status_code == 200
    except Exception:
        # Any failure (network, timeout, invalid URL, JSON, etc.) → still
        # unavailable. Caller's contract is "True iff up"; everything else
        # is False.
        return False
