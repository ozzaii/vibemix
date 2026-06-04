# SPDX-License-Identifier: Apache-2.0
"""Chatterbox-only TTS chain contract."""

from __future__ import annotations

import subprocess
import sys

from livekit.agents import tts as agents_tts


def _patch_chatterbox_chain(mocker):
    mocker.patch("vibemix.agent.chatterbox_tts.chatterbox_available", return_value=True)
    fake_chatterbox_cls = mocker.patch("vibemix.agent.chatterbox_tts.ChatterboxLocalTTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)
    return fake_chatterbox_cls


def test_tts_chain_direct_is_chatterbox_only(mocker) -> None:
    fake_chatterbox_cls = _patch_chatterbox_chain(mocker)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(mode="direct")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert kwargs["tts"] == [fake_chatterbox_cls.return_value]
    assert kwargs["max_retry_per_tts"] == 1
    fake_chatterbox_cls.return_value.prewarm.assert_called_once()


def test_tts_chain_proxy_is_chatterbox_only_without_proxy_args(mocker) -> None:
    fake_chatterbox_cls = _patch_chatterbox_chain(mocker)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(mode="proxy")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert kwargs["tts"] == [fake_chatterbox_cls.return_value]
    assert kwargs["max_retry_per_tts"] == 1


def test_tts_chain_missing_chatterbox_runtime_fails_loud(mocker) -> None:
    from vibemix.agent.chatterbox_tts import ChatterboxUnavailable
    from vibemix.agent.tts_chain import build_tts_chain

    mocker.patch("vibemix.agent.chatterbox_tts.chatterbox_available", return_value=False)
    mocker.patch(
        "vibemix.agent.chatterbox_tts.chatterbox_unavailable_reason",
        return_value="mlx-audio not installed",
    )

    try:
        build_tts_chain()
    except ChatterboxUnavailable as exc:
        assert "mlx-audio not installed" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("build_tts_chain must fail when Chatterbox is unavailable")


def test_tts_chain_unknown_mode_raises(mocker) -> None:
    _patch_chatterbox_chain(mocker)
    from vibemix.agent.tts_chain import build_tts_chain

    try:
        build_tts_chain(mode="garbage")  # type: ignore[arg-type]
    except ValueError as exc:
        assert "unknown mode" in str(exc)
    else:  # pragma: no cover - assertion clarity
        raise AssertionError("unknown mode must raise")


def test_tts_chain_does_not_import_openai_tts_plugin() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys\n"
                "import vibemix.agent.tts_chain\n"
                "assert 'livekit.plugins.openai.tts' not in sys.modules\n"
                "print('OK')\n"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert proc.stdout.strip() == "OK"


def test_pkg_02_build_tts_chain_exported() -> None:
    import vibemix.agent as vagent
    from vibemix.agent import build_tts_chain

    assert callable(build_tts_chain)
    assert "build_tts_chain" in vagent.__all__
