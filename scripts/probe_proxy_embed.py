#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Legacy Bravoh proxy embedContent probe.

Product library embeddings are local CLAP ONNX and no longer require this
Gemini embedding route. By default this script emits a structured
``status="skipped"`` report and exits 0. Pass ``--legacy-live-probe`` only when
maintaining the legacy migration/fallback probe path.

Usage:
    python scripts/probe_proxy_embed.py
    python scripts/probe_proxy_embed.py --legacy-live-probe
    VIBEMIX_PROXY_BASE_URL=http://test python scripts/probe_proxy_embed.py --legacy-live-probe
    VIBEMIX_PROXY_JWT=<token> python scripts/probe_proxy_embed.py --legacy-live-probe

The live probe does NOT require a real JWT to detect endpoint availability:
a 401/403 response confirms the route exists; only 404/connection errors
indicate the legacy endpoint is missing.

Exit codes:
    0 — skipped by default, or legacy endpoint accessible in live-probe mode
    1 — legacy endpoint missing in live-probe mode
    2 — invocation error (bad env, missing httpx, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

DEFAULT_PROXY = "https://api.altidus.world"


def _emit(report: dict[str, Any], exit_code: int) -> None:
    print(json.dumps(report, indent=2))
    sys.exit(exit_code)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Legacy Bravoh proxy embedContent probe. Product embeddings are "
            "local CLAP; pass --legacy-live-probe to check the retired route."
        )
    )
    parser.add_argument(
        "--legacy-live-probe",
        action="store_true",
        help="actually call the legacy Gemini embedding proxy route",
    )
    args = parser.parse_args(argv)
    if not args.legacy_live_probe:
        _emit(
            {
                "status": "skipped",
                "reason": (
                    "Product library embeddings use local CLAP ONNX; "
                    "the Gemini embedContent proxy route is no longer required."
                ),
                "legacy_probe": "rerun with --legacy-live-probe if needed",
            },
            0,
        )

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
                    "The legacy embedding proxy route is unavailable. "
                    "This is not a product blocker unless you are running "
                    "legacy migration/probe tests that still need it."
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
