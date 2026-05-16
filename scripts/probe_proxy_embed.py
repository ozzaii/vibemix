#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 04 Wave 0 — Bravoh proxy embedContent probe.

Verifies the Bravoh proxy at https://api.altidus.world routes the
``models:embedContent`` endpoint. Failure surfaces as exit code 1 with
a structured JSON diagnostic on stdout — under ``gsd-autonomous fully``,
the orchestrator routes that to KAAN-ACTION-PROXY.md.

Usage:
    python scripts/probe_proxy_embed.py
    VIBEMIX_PROXY_BASE_URL=http://test python scripts/probe_proxy_embed.py
    VIBEMIX_PROXY_JWT=<token> python scripts/probe_proxy_embed.py

The script does NOT require a real JWT to detect endpoint availability —
a 401/403 response confirms the route exists; only 404/connection errors
indicate the endpoint is missing.

Exit codes:
    0 — endpoint accessible (any response other than 404 / connection error)
    1 — endpoint missing (404 or connection refused / DNS failure)
    2 — invocation error (bad env, missing httpx, etc.)
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

DEFAULT_PROXY = "https://api.altidus.world"


def _emit(report: dict[str, Any], exit_code: int) -> None:
    print(json.dumps(report, indent=2))
    sys.exit(exit_code)


def main() -> None:
    base = os.environ.get("VIBEMIX_PROXY_BASE_URL", DEFAULT_PROXY).rstrip("/")
    jwt = os.environ.get("VIBEMIX_PROXY_JWT", "probe-no-real-jwt-needed")
    url = f"{base}/v1beta/models/gemini-embedding-2:embedContent"

    try:
        import httpx
    except ImportError as e:
        _emit(
            {"status": "error", "reason": f"httpx unavailable: {e}"},
            2,
        )
        return

    payload = {
        "content": {"parts": [{"text": "ping"}]},
        "outputDimensionality": 768,
    }
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
        "User-Agent": "vibemix-proxy-probe/1.0",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            r = client.post(url, json=payload, headers=headers)
    except httpx.ConnectError as e:
        _emit(
            {
                "status": "endpoint_missing",
                "reason": f"connection refused / DNS failure: {e}",
                "url": url,
                "remediation": (
                    "Bravoh proxy is offline or DNS is broken. "
                    "Set VIBEMIX_PROXY_BASE_URL to a working host or "
                    "fix the upstream proxy."
                ),
            },
            1,
        )
        return
    except Exception as e:
        _emit(
            {"status": "error", "reason": str(e), "url": url},
            2,
        )
        return

    if r.status_code == 404:
        _emit(
            {
                "status": "endpoint_missing",
                "http_status": 404,
                "url": url,
                "body_preview": r.text[:512],
                "remediation": (
                    "Bravoh proxy does NOT route models:embedContent. "
                    "Either patch the proxy to forward this endpoint to "
                    "Gemini, or fall back to MOCK_PROXY_FOR_DEV=1 in tests."
                ),
            },
            1,
        )
        return

    # 200/401/403 → route exists. 401/403 just means our JWT is wrong;
    # the endpoint is reachable.
    _emit(
        {
            "status": "ok",
            "http_status": r.status_code,
            "url": url,
            "note": (
                "200 = full success; 401/403 = endpoint reachable but JWT "
                "invalid — the actual auth flow uses sidecar-issued tokens."
            ),
            "body_preview": r.text[:256],
        },
        0,
    )


if __name__ == "__main__":
    main()
