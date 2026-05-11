# SPDX-License-Identifier: Apache-2.0
"""LLM factory — verbatim port of cohost_v4.py:1983-1989.

Phase 5 (FastAPI Proxy + Install-UUID JWT) will swap ``api_key`` for a
proxy-issued JWT; the ``api_key`` parameter on ``build_llm`` is the seam.
"""

from __future__ import annotations

from google.genai import types
from livekit.plugins import google as google_plugin

from vibemix.agent.config import LLM_MODEL


def build_llm(api_key: str) -> google_plugin.LLM:
    """Build the LiveKit ``google_plugin.LLM`` instance — verbatim port of v4:1983-1989.

    ``thinking_level="minimal"`` keeps the model fast (no extended reasoning
    chain). ``temperature=1.0`` is the v4 tuning. ``max_output_tokens=220``
    caps reply length to match the "one short sentence" anti-slop rule in
    SYSTEM_INSTRUCTION.
    """
    return google_plugin.LLM(
        model=LLM_MODEL,
        api_key=api_key,
        temperature=1.0,
        thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        max_output_tokens=220,
    )
