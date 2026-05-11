# SPDX-License-Identifier: Apache-2.0
"""LLM factory — LLM-01 + LLM-MODE-01..03 + ERR-01..04 + ERR-06.

Verifies the Phase 4 direct-mode kwargs match v4:1983-1989 verbatim, the
Phase 5 proxy-mode dispatch wires http_options correctly, and missing-arg
combinations raise ValueError immediately (NO silent fallback).
"""

from __future__ import annotations

import inspect

import pytest
from livekit.plugins import google as google_plugin

from vibemix.agent.llm_factory import build_llm


def test_llm_01_build_llm_direct_kwargs_match_v4(mocker) -> None:
    """LLM-01: build_llm passes the v4:1983-1989 kwargs in direct mode."""
    mocker.patch.object(google_plugin.LLM, "__init__", return_value=None)
    inst = build_llm("dummy-key")
    assert isinstance(inst, google_plugin.LLM)

    kwargs = google_plugin.LLM.__init__.call_args.kwargs
    assert kwargs["model"] == "gemini-3-flash-preview"
    assert kwargs["api_key"] == "dummy-key"
    assert kwargs["temperature"] == 1.0
    assert kwargs["max_output_tokens"] == 220
    tc = kwargs["thinking_config"]
    level = getattr(tc, "thinking_level", None)
    assert level is not None
    assert str(getattr(level, "value", level)).lower() == "minimal"


def test_llm_02_signature_extended_with_mode_kwargs() -> None:
    """Phase 5: signature is ``build_llm(api_key=None, *, mode='direct',
    proxy_base_url=None, jwt=None)`` — 4 params, mode/proxy_base_url/jwt
    are keyword-only."""
    sig = inspect.signature(build_llm)
    params = list(sig.parameters.values())
    assert [p.name for p in params] == ["api_key", "mode", "proxy_base_url", "jwt"]
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    for p in params[1:]:
        assert p.kind == inspect.Parameter.KEYWORD_ONLY


def test_llm_mode_01_direct_default_preserves_phase4(mocker) -> None:
    """LLM-MODE-01: build_llm(api_key) (no mode) == Phase 4 direct."""
    mocker.patch.object(google_plugin.LLM, "__init__", return_value=None)
    build_llm("key-x")
    kw = google_plugin.LLM.__init__.call_args.kwargs
    assert kw["api_key"] == "key-x"
    assert "http_options" not in kw  # direct mode never sets http_options


def test_llm_mode_02_explicit_direct_same_as_default(mocker) -> None:
    """LLM-MODE-02: explicit mode='direct' is equivalent."""
    mocker.patch.object(google_plugin.LLM, "__init__", return_value=None)
    build_llm("key-x", mode="direct")
    kw = google_plugin.LLM.__init__.call_args.kwargs
    assert kw["api_key"] == "key-x"
    assert "http_options" not in kw


def test_llm_mode_03_proxy_uses_http_options(mocker) -> None:
    """LLM-MODE-03: proxy mode threads HttpOptions(base_url, Authorization)."""
    mocker.patch.object(google_plugin.LLM, "__init__", return_value=None)
    build_llm(mode="proxy", proxy_base_url="https://api.altidus.world", jwt="jwt-x")
    kw = google_plugin.LLM.__init__.call_args.kwargs
    assert kw["api_key"] == "vibemix-proxy"
    ho = kw["http_options"]
    assert ho.base_url == "https://api.altidus.world"
    assert ho.headers["Authorization"] == "Bearer jwt-x"


def test_llm_mode_03b_proxy_strips_trailing_slash(mocker) -> None:
    """Trailing slash on proxy_base_url is stripped."""
    mocker.patch.object(google_plugin.LLM, "__init__", return_value=None)
    build_llm(mode="proxy", proxy_base_url="https://api.altidus.world/", jwt="jwt-x")
    ho = google_plugin.LLM.__init__.call_args.kwargs["http_options"]
    assert ho.base_url == "https://api.altidus.world"


def test_err_01_direct_without_api_key_raises():
    with pytest.raises(ValueError, match="direct mode requires api_key"):
        build_llm()


def test_err_02_proxy_without_args_raises():
    with pytest.raises(ValueError) as exc:
        build_llm(mode="proxy")
    msg = str(exc.value)
    assert "proxy_base_url" in msg and "jwt" in msg


def test_err_03_proxy_without_base_url_raises():
    with pytest.raises(ValueError, match="proxy_base_url"):
        build_llm(mode="proxy", jwt="x")


def test_err_04_proxy_without_jwt_raises():
    with pytest.raises(ValueError, match="jwt"):
        build_llm(mode="proxy", proxy_base_url="x")


def test_err_06_unknown_mode_raises():
    with pytest.raises(ValueError, match="unknown mode"):
        build_llm(api_key="x", mode="garbage")  # type: ignore[arg-type]
