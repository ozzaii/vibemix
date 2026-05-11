# SPDX-License-Identifier: Apache-2.0
"""TTS chain — TTS-01..06 + PKG-02 + PYPROJECT-01.

Pins the OpenRouter monkey-patch as a module-load invariant (TTS-01) and the
factory's branching shape with/without OPENROUTER_API_KEY (TTS-02..06)."""

from __future__ import annotations

from pathlib import Path

from livekit.agents import tts as agents_tts
from livekit.plugins import openai as openai_plugin
from livekit.plugins.google.beta import gemini_tts as gemini_native_tts


def test_tts_01_monkey_patch_active_at_module_load() -> None:
    """TTS-01: the patch happens at module-load time. We trigger import inside
    the test body and immediately read AUDIO_STREAM_MODELS — no factory call."""
    from livekit.plugins.openai import tts as t

    import vibemix.agent.tts_chain  # noqa: F401 — import triggers the patch

    assert "google/gemini-3.1-flash-tts-preview" in t.AUDIO_STREAM_MODELS


def test_tts_02_with_openrouter_chain_has_3_entries(mocker) -> None:
    """TTS-02: with OPENROUTER_API_KEY → FallbackAdapter has 3 entries."""
    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(gemini_native_tts.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", openrouter_api_key="or")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    chain = kwargs["tts"]
    assert len(chain) == 3
    assert kwargs["max_retry_per_tts"] == 1
    assert isinstance(chain[0], openai_plugin.TTS)
    assert isinstance(chain[1], gemini_native_tts.TTS)
    assert isinstance(chain[2], gemini_native_tts.TTS)


def test_tts_03_without_openrouter_key_none_chain_has_2_entries(mocker) -> None:
    """TTS-03: openrouter_api_key=None → chain has 2 entries, no openai.TTS."""
    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(gemini_native_tts.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", openrouter_api_key=None)

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    chain = kwargs["tts"]
    assert len(chain) == 2
    # openai.TTS was never instantiated
    assert openai_plugin.TTS.__init__.call_count == 0
    assert isinstance(chain[0], gemini_native_tts.TTS)
    assert isinstance(chain[1], gemini_native_tts.TTS)


def test_tts_04_empty_string_openrouter_key_treated_as_none(mocker) -> None:
    """TTS-04: openrouter_api_key="" → same as None, exactly 2 entries."""
    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(gemini_native_tts.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", openrouter_api_key="")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    chain = kwargs["tts"]
    assert len(chain) == 2
    assert openai_plugin.TTS.__init__.call_count == 0


def test_tts_05_openrouter_kwargs_match_v4(mocker) -> None:
    """TTS-05: openai_plugin.TTS kwargs match v4:1994-2001 verbatim."""
    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(gemini_native_tts.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", openrouter_api_key="or")

    kw = openai_plugin.TTS.__init__.call_args.kwargs
    assert kw["model"] == "google/gemini-3.1-flash-tts-preview"
    assert kw["voice"] == "Achird"
    assert kw["api_key"] == "or"
    assert kw["base_url"] == "https://openrouter.ai/api/v1"
    assert kw["response_format"] == "pcm"
    # em-dash here is v4 verbatim (U+2014)
    assert (
        kw["instructions"]
        == "Casual studio friend, brief, natural — no theatrics, no announcer voice."
    )


def test_tts_06_gemini_native_kwargs_match_v4(mocker) -> None:
    """TTS-06: gemini_native_tts.TTS kwargs (both fallbacks) match v4:2003-2014."""
    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(gemini_native_tts.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", openrouter_api_key="or")

    # Two gemini_native_tts.TTS constructor calls — primary then fallback
    calls = gemini_native_tts.TTS.__init__.call_args_list
    assert len(calls) == 2

    primary_kw = calls[0].kwargs
    assert primary_kw["model"] == "gemini-3.1-flash-tts-preview"
    assert primary_kw["voice_name"] == "Achird"
    assert primary_kw["api_key"] == "g"
    assert (
        primary_kw["instructions"]
        == "Casual studio friend, brief, natural — no theatrics, no announcer voice."
    )

    fallback_kw = calls[1].kwargs
    assert fallback_kw["model"] == "gemini-2.5-flash-preview-tts"
    assert fallback_kw["voice_name"] == "Achird"
    assert fallback_kw["api_key"] == "g"
    assert (
        fallback_kw["instructions"]
        == "Casual studio friend, brief, natural — no theatrics, no announcer voice."
    )


def test_pkg_02_build_tts_chain_exported() -> None:
    """PKG-02: build_tts_chain resolves from vibemix.agent and is in __all__."""
    import vibemix.agent as vagent
    from vibemix.agent import build_tts_chain

    assert callable(build_tts_chain)
    assert "build_tts_chain" in vagent.__all__


def test_pyproject_01_livekit_plugins_openai_explicit() -> None:
    """PYPROJECT-01: pyproject.toml declares livekit-plugins-openai explicitly.

    The monkey-patch makes this load-bearing — must not be transitive-only.
    """
    text = Path("pyproject.toml").read_text()
    # tolerant — accept any version constraint
    assert '"livekit-plugins-openai>=' in text or "'livekit-plugins-openai>=" in text, (
        "livekit-plugins-openai must be an explicit dep in pyproject.toml"
    )


# ----------------------------------------------------------------------------
# Phase 5 — TTS-MODE-01..03 + ERR-05 — mode dispatch
# ----------------------------------------------------------------------------


def test_tts_mode_01_direct_default_preserves_phase4(mocker) -> None:
    """TTS-MODE-01: build_tts_chain(gemini_api_key='g') == Phase 4 (2 entries)."""
    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(gemini_native_tts.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g")  # no mode → default direct, no OR

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    chain = kwargs["tts"]
    assert len(chain) == 2
    assert openai_plugin.TTS.__init__.call_count == 0


def test_tts_mode_02_direct_with_openrouter(mocker) -> None:
    """TTS-MODE-02: direct mode with openrouter still gives 3 entries (Phase 4 verbatim)."""
    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(gemini_native_tts.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", openrouter_api_key="or", mode="direct")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    chain = kwargs["tts"]
    assert len(chain) == 3


def test_tts_mode_03_proxy_single_entry(mocker) -> None:
    """TTS-MODE-03: proxy mode returns 1-entry chain pointed at proxy/v1."""
    import pytest

    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(gemini_native_tts.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(
        mode="proxy",
        proxy_base_url="https://api.altidus.world",
        jwt="jwt-x",
    )

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    chain = kwargs["tts"]
    assert len(chain) == 1
    assert kwargs["max_retry_per_tts"] == 1

    or_kw = openai_plugin.TTS.__init__.call_args.kwargs
    assert or_kw["base_url"] == "https://api.altidus.world/v1"
    assert or_kw["api_key"] == "jwt-x"
    assert or_kw["model"] == "google/gemini-3.1-flash-tts-preview"
    assert or_kw["response_format"] == "pcm"

    # No gemini_native_tts entries in proxy mode
    assert gemini_native_tts.TTS.__init__.call_count == 0

    # Avoid the unused-pytest import warning
    _ = pytest


def test_err_05_direct_without_gemini_key_raises():
    import pytest

    from vibemix.agent.tts_chain import build_tts_chain

    with pytest.raises(ValueError, match="direct mode requires gemini_api_key"):
        build_tts_chain()


def test_err_05_proxy_without_args_raises():
    import pytest

    from vibemix.agent.tts_chain import build_tts_chain

    with pytest.raises(ValueError) as exc:
        build_tts_chain(mode="proxy")
    msg = str(exc.value)
    assert "proxy_base_url" in msg and "jwt" in msg


def test_err_05_unknown_mode_raises():
    import pytest

    from vibemix.agent.tts_chain import build_tts_chain

    with pytest.raises(ValueError, match="unknown mode"):
        build_tts_chain(mode="garbage")  # type: ignore[arg-type]
