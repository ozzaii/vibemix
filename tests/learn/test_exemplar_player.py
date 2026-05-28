# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 03 — EXEMPLAR-04 ``ExemplarPlayer`` + ``_choose_gain_db`` (RED-state stub).

``ExemplarPlayer`` owns its OWN ``sd.OutputStream`` on a user-picked
headphone device. It does NOT reuse ``audio.buffers.PlaybackQueue`` (which
is mic-gated at ``audio/buffers.py:195`` — reuse would silence Kaan's mic
during exemplar playback).

Gain policy (from 93-RESEARCH.md §Pattern 6):

    - Default ``-12 dB`` for safe headphone level.
    - Drop to ``-18 dB`` when master deck RMS > ``0.5`` linear (≈ -6 dBFS)
      so headphone bleed doesn't compete with hot master mix.
    - Below ``SILENT_RMS=0.012`` → default ``-12 dB`` (no special handling
      for "no master" state).

P93 also lands the Course 3 active-session guard SCAFFOLDING (``can_play()``
returns True for now; P96 wires the real guard against ``state.session_active``
and ``state.audible_deck``).

REQ-ID: EXEMPLAR-04 (dedicated headphone audio routing + gain policy).
Downstream plan that flips this skip: **Plan 93-03**.
"""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import pytest

try:
    from vibemix.learn import audio_cue  # Plan 93-03
    from vibemix.learn.audio_cue import ExemplarPlayer, _choose_gain_db  # Plan 93-03
except ImportError:
    pytest.skip(
        "tests/learn/test_exemplar_player.py awaiting Plan 93-03 — "
        "ExemplarPlayer + _choose_gain_db in src/vibemix/learn/audio_cue.py.",
        allow_module_level=True,
    )


def test_choose_gain_db_default_silent_master() -> None:
    """``_choose_gain_db(0.0)`` returns the default ``-12 dB`` — silent
    master is treated as "no special handling" (no need to duck)."""
    assert _choose_gain_db(0.0) == -12.0, (
        f"silent master → default -12 dB; got {_choose_gain_db(0.0)!r}"
    )


def test_choose_gain_db_lowers_when_master_loud() -> None:
    """``_choose_gain_db(0.7)`` (above 0.5 linear-RMS / ≈ -6 dBFS threshold)
    drops to ``-18 dB`` to avoid bleed competing with the hot master."""
    assert _choose_gain_db(0.7) == -18.0, (
        f"loud master (RMS > 0.5) → -18 dB ducking; got {_choose_gain_db(0.7)!r}"
    )


def test_choose_gain_db_default_when_master_below_silent_rms() -> None:
    """``_choose_gain_db(0.001)`` (well below ``SILENT_RMS=0.012``) returns
    default ``-12 dB`` — the early-exit silent-master branch."""
    assert _choose_gain_db(0.001) == -12.0, (
        f"sub-SILENT_RMS master → default -12 dB; got {_choose_gain_db(0.001)!r}"
    )


def test_exemplar_player_opens_own_output_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``ExemplarPlayer.play()`` must create its OWN ``sd.OutputStream`` —
    bound to the configured headphone device_index, channels=2, dtype="float32".

    We monkeypatch ``sd.OutputStream`` to a MagicMock and assert the
    constructor receives ``device=2, channels=2, dtype='float32'``.
    """
    mock_stream_cls = MagicMock(name="sd.OutputStream")
    monkeypatch.setattr("sounddevice.OutputStream", mock_stream_cls)
    # load_audio_stereo returns (samples, sr); short fixture so the test stays cheap.
    import numpy as np

    fake_samples = np.zeros((SR := 44100, 2), dtype=np.float32)
    monkeypatch.setattr(
        "vibemix.library.audio_decode.load_audio_stereo",
        lambda path: (fake_samples, SR),
    )

    # Build a MusicState stub with the audio_rms attribute the gain helper reads.
    # P96-03 added the active-session guard to can_play() that reads
    # session_active + audible_deck; default MagicMock attrs are truthy
    # which would trip the guard and short-circuit play(). Explicitly set
    # both fields to the cold-path values so the guard permits playback.
    state_stub = MagicMock(name="MusicState_stub")
    state_stub.audio_rms = 0.0
    state_stub.session_active = False  # cold path → can_play=True
    state_stub.audible_deck = "none"

    player = ExemplarPlayer(device_index=2, state=state_stub)
    player.play("/tmp/synthetic.wav")

    # OutputStream was constructed at least once with the expected kwargs.
    assert mock_stream_cls.called, "ExemplarPlayer.play must instantiate sd.OutputStream"
    call_kwargs = mock_stream_cls.call_args.kwargs
    assert call_kwargs.get("device") == 2, (
        f"OutputStream(device=2) expected; got device={call_kwargs.get('device')!r}"
    )
    assert call_kwargs.get("channels") == 2, (
        f"OutputStream(channels=2) expected; got channels={call_kwargs.get('channels')!r}"
    )
    assert call_kwargs.get("dtype") == "float32", (
        f"OutputStream(dtype='float32') expected; got {call_kwargs.get('dtype')!r}"
    )


def test_exemplar_player_does_not_touch_playback_queue() -> None:
    """Static check: ``audio_cue`` source must NOT reference ``PlaybackQueue``.

    ``PlaybackQueue`` is mic-gated (``audio/buffers.py:195``); reusing it for
    exemplar playback would silence Kaan's mic during the lesson. Hard
    architectural rule per 93-RESEARCH.md §Don't-Hand-Roll.
    """
    src = inspect.getsource(audio_cue)
    assert "PlaybackQueue" not in src, (
        "audio_cue.py must NOT import or reference PlaybackQueue — "
        "the ExemplarPlayer owns its own sd.OutputStream on a separate "
        "device. Reuse of PlaybackQueue would silence Kaan's mic during "
        "exemplar playback (mic-gate at audio/buffers.py:195)."
    )


def test_can_play_returns_true_when_lens_off_cold_state() -> None:
    """``ExemplarPlayer.can_play()`` returns ``True`` on the cold-state
    path (session_active=False) regardless of audible_deck.

    P93 shipped this as scaffolding returning True unconditionally;
    Plan 96-03 (EXEMPLAR-06) replaced the body with the real guard
    ``return not (session_active and audible_deck != "none")``. The
    cold path (lens off) still returns True so existing P93/P94/P95
    fixtures with default MusicState stay green. The full truth-table
    coverage lives in tests/learn/test_course3_no_exemplar_during_live.py.
    """
    state_stub = MagicMock(name="MusicState_stub")
    state_stub.audio_rms = 0.0
    state_stub.session_active = False  # lens off → cold path
    state_stub.audible_deck = "none"
    player = ExemplarPlayer(device_index=0, state=state_stub)
    assert player.can_play() is True, (
        "cold-path can_play() must return True; P96 guard kept the "
        "lens-off branch permissive."
    )


def test_stop_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """``ExemplarPlayer.stop()`` called twice without a prior ``play()``
    must NOT raise — idempotent stop is part of the contract so callers
    can blindly stop on cleanup paths.
    """
    state_stub = MagicMock(name="MusicState_stub")
    state_stub.audio_rms = 0.0
    player = ExemplarPlayer(device_index=0, state=state_stub)
    # Two stops in a row, no play in between — must not raise.
    player.stop()
    player.stop()
