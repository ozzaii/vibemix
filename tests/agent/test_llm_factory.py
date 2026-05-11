# SPDX-License-Identifier: Apache-2.0
"""LLM factory — LLM-01 + LLM-02. Verifies the build_llm constructor kwargs
match v4:1983-1989 verbatim. Mocks ``google_plugin.LLM.__init__`` so no
network/credentials are required."""

from __future__ import annotations

import inspect

from livekit.plugins import google as google_plugin

from vibemix.agent.llm_factory import build_llm


def test_llm_01_build_llm_kwargs_match_v4(mocker) -> None:
    """LLM-01: build_llm passes the v4:1983-1989 kwargs to google_plugin.LLM."""
    mocker.patch.object(google_plugin.LLM, "__init__", return_value=None)
    inst = build_llm("dummy-key")
    assert isinstance(inst, google_plugin.LLM)

    kwargs = google_plugin.LLM.__init__.call_args.kwargs
    assert kwargs["model"] == "gemini-3-flash-preview"
    assert kwargs["api_key"] == "dummy-key"
    assert kwargs["temperature"] == 1.0
    assert kwargs["max_output_tokens"] == 220
    # thinking_config is a types.ThinkingConfig — the Pydantic model coerces
    # the string "minimal" to a ThinkingLevel enum whose .value/.name compares
    # case-insensitively to "minimal" (e.g. ThinkingLevel.MINIMAL).
    tc = kwargs["thinking_config"]
    level = getattr(tc, "thinking_level", None)
    assert level is not None
    assert str(getattr(level, "value", level)).lower() == "minimal"


def test_llm_02_signature_accepts_api_key_positional_or_kw() -> None:
    """LLM-02: signature is ``build_llm(api_key: str)`` — single param, str hint."""
    sig = inspect.signature(build_llm)
    params = list(sig.parameters.values())
    assert len(params) == 1
    p = params[0]
    assert p.name == "api_key"
    # With `from __future__ import annotations`, hints are stored as strings.
    assert p.annotation == "str" or p.annotation is str
    # Default Param kind is POSITIONAL_OR_KEYWORD — the spec says "positional-or-keyword".
    assert p.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
