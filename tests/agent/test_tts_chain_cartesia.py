# SPDX-License-Identifier: Apache-2.0
"""Cartesia residue must not re-enter the MOSS-only voice policy."""

from __future__ import annotations

import sys
from pathlib import Path

from livekit.agents import tts as agents_tts


def test_cartesia_plugin_is_not_a_runtime_dependency() -> None:
    root = Path(__file__).resolve().parents[2]
    package_name = "livekit-" + "plugins-cartesia"
    assert package_name not in (root / "pyproject.toml").read_text()
    assert package_name not in (root / "uv.lock").read_text()


def test_cartesia_key_is_accepted_only_as_legacy_noop(mocker) -> None:
    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    fake_moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", cartesia_api_key="c", mode="direct")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert kwargs["tts"] == [fake_moss_cls.return_value]
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
