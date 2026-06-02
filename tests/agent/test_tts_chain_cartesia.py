# SPDX-License-Identifier: Apache-2.0
"""Cartesia residue must not re-enter the MOSS-only voice policy."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from livekit.agents import tts as agents_tts


def test_cartesia_plugin_is_not_a_runtime_dependency() -> None:
    root = Path(__file__).resolve().parents[2]
    package_name = "livekit-" + "plugins-cartesia"
    assert package_name not in (root / "pyproject.toml").read_text()
    assert package_name not in (root / "uv.lock").read_text()


def test_cartesia_key_is_not_a_supported_tts_argument(mocker) -> None:
    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    with pytest.raises(TypeError):
        build_tts_chain(cartesia_api_key="c", mode="direct")  # type: ignore[call-arg]

    moss_cls.assert_not_called()
    assert "livekit.plugins.cartesia" not in sys.modules


def test_cartesia_env_is_ignored_by_tts_chain(mocker, monkeypatch) -> None:
    monkeypatch.setenv("CARTESIA_API_KEY", "env-cartesia-key")
    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    fake_moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(mode="direct")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert kwargs["tts"] == [fake_moss_cls.return_value]
    assert "livekit.plugins.cartesia" not in sys.modules


def test_automix_demo_source_does_not_request_cartesia_key() -> None:
    """Manual demo comments must not imply Cartesia is still a voice input."""
    root = Path(__file__).resolve().parents[2]
    text = (root / "scripts" / "automix_demo_smoke.py").read_text(encoding="utf-8")

    assert "CARTESIA_API_KEY" not in text
