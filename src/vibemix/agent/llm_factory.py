# SPDX-License-Identifier: Apache-2.0
"""LLM factory — Phase 4 verbatim direct mode + Phase 5 proxy mode dispatch.

Per CONTEXT (locked): mode='direct' is the Phase 5 default (Kaan's dev rig
keeps working). Phase 18 installer flips the runtime default to 'proxy'.
Missing required args raise ValueError IMMEDIATELY — NEVER silently downgrade
proxy → direct (that would defeat Phase 5's entire security goal).
"""

from __future__ import annotations

from typing import Literal

from google.genai import types
from livekit.plugins import google as google_plugin

from vibemix.agent.config import LLM_MODEL
from vibemix.llm.thinking_gate import validate_live_config


def _build_direct(api_key: str) -> google_plugin.LLM:
    """Phase 4 verbatim — port of v4:1983-1989."""
    # Plan 41-03 / LAT-08 — validate the live-coach config before
    # constructing the LLM wrapper. Zero per-turn cost: this runs once
    # per agent boot. Any future config-mutation seam that bypasses this
    # factory still hits the second gate inside DJCoHostAgent.__init__.
    gen_cfg = types.GenerateContentConfig(
        temperature=1.0,
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        max_output_tokens=220,
    )
    validate_live_config(gen_cfg)
    return google_plugin.LLM(
        model=LLM_MODEL,
        api_key=api_key,
        temperature=gen_cfg.temperature,
        thinking_config=gen_cfg.thinking_config,
        max_output_tokens=gen_cfg.max_output_tokens,
    )


def _build_proxy(proxy_base_url: str, jwt: str) -> google_plugin.LLM:
    """Phase 5 — build google_plugin.LLM with http_options pointed at the proxy.

    Decision (verified against .venv/lib/python3.12/site-packages/livekit/plugins/google/llm.py:117):
    `google_plugin.LLM.__init__` accepts `http_options: NotGivenOr[types.HttpOptions]`
    directly. We use that kwarg — no need to build a separate genai.Client.

    api_key="vibemix-proxy" is a non-empty dummy required by the SDK's
    validation path; the proxy ignores x-goog-api-key entirely (auth is via
    the Bearer JWT in the Authorization header).
    """
    # Plan 41-03 / LAT-08 — same gate as the direct path. Proxy mode must
    # not bypass the live-coach invariants.
    gen_cfg = types.GenerateContentConfig(
        temperature=1.0,
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        max_output_tokens=220,
    )
    validate_live_config(gen_cfg)
    return google_plugin.LLM(
        model=LLM_MODEL,
        api_key="vibemix-proxy",
        http_options=types.HttpOptions(
            base_url=proxy_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=120_000,
        ),
        temperature=gen_cfg.temperature,
        thinking_config=gen_cfg.thinking_config,
        max_output_tokens=gen_cfg.max_output_tokens,
    )


def build_llm(
    api_key: str | None = None,
    *,
    mode: Literal["direct", "proxy"] = "direct",
    proxy_base_url: str | None = None,
    jwt: str | None = None,
) -> google_plugin.LLM:
    """Factory entry — dispatches on mode.

    direct: requires api_key.
    proxy:  requires proxy_base_url AND jwt.

    Per CONTEXT decision (locked): missing required args raise ValueError
    IMMEDIATELY. NEVER silently downgrade proxy → direct.
    """
    if mode == "direct":
        if not api_key:
            raise ValueError("direct mode requires api_key")
        return _build_direct(api_key)
    if mode == "proxy":
        missing: list[str] = []
        if not proxy_base_url:
            missing.append("proxy_base_url")
        if not jwt:
            missing.append("jwt")
        if missing:
            raise ValueError(f"proxy mode requires {', '.join(missing)}")
        return _build_proxy(proxy_base_url, jwt)  # type: ignore[arg-type]
    raise ValueError(f"unknown mode: {mode}")
