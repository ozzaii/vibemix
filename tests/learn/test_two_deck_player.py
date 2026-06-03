# SPDX-License-Identifier: Apache-2.0
"""TwoDeckPlayer regression tests."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock

import numpy as np
import pytest

from vibemix.audio.miniplayer import MiniDeck
from vibemix.learn import two_deck_player
from vibemix.learn.two_deck_player import TwoDeckPlayer


class _FakeStream:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def close(self) -> None:
        self.closed = True


def _deck() -> MiniDeck:
    a = np.ones((1024, 2), dtype=np.float32)
    b = np.zeros((1024, 2), dtype=np.float32)
    return MiniDeck(a, b, rate_a=1.0, rate_b=1.0, xfader=0.0)


def _cold_state() -> MagicMock:
    state = MagicMock(name="MusicState_stub")
    state.session_active = False
    state.audible_deck = "none"
    return state


def test_two_deck_player_owns_headphone_output_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    streams: list[_FakeStream] = []

    def fake_output_stream(**kwargs) -> _FakeStream:
        stream = _FakeStream(**kwargs)
        streams.append(stream)
        return stream

    monkeypatch.setattr("sounddevice.OutputStream", fake_output_stream)

    player = TwoDeckPlayer(7, _deck(), state=_cold_state(), sample_rate=44_100)
    player.start()

    assert len(streams) == 1
    stream = streams[0]
    assert stream.started is True
    assert stream.kwargs["device"] == 7
    assert stream.kwargs["samplerate"] == 44_100
    assert stream.kwargs["channels"] == 2
    assert stream.kwargs["dtype"] == "float32"
    assert stream.kwargs["latency"] == "low"


def test_two_deck_callback_renders_and_advances_minideck(monkeypatch: pytest.MonkeyPatch) -> None:
    streams: list[_FakeStream] = []
    monkeypatch.setattr(
        "sounddevice.OutputStream",
        lambda **kwargs: streams.append(_FakeStream(**kwargs)) or streams[-1],
    )
    deck = _deck()
    player = TwoDeckPlayer(0, deck, state=_cold_state())
    player.start()

    out = np.empty((128, 2), dtype=np.float32)
    streams[0].kwargs["callback"](out, 128, None, None)

    assert np.any(out > 0.0)
    assert deck.state().a_frame == pytest.approx(128.0)
    assert deck.state().b_frame == pytest.approx(128.0)


def test_two_deck_callback_degrades_to_silence_on_render_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    streams: list[_FakeStream] = []
    monkeypatch.setattr(
        "sounddevice.OutputStream",
        lambda **kwargs: streams.append(_FakeStream(**kwargs)) or streams[-1],
    )
    deck = MagicMock(name="MiniDeck")
    deck.render_block.side_effect = RuntimeError("synthetic render failure")
    player = TwoDeckPlayer(0, deck, state=_cold_state())
    player.start()

    out = np.ones((64, 2), dtype=np.float32)
    streams[0].kwargs["callback"](out, 64, None, None)

    assert np.all(out == 0.0)


def test_two_deck_callback_clamps_once_at_output_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    streams: list[_FakeStream] = []
    monkeypatch.setattr(
        "sounddevice.OutputStream",
        lambda **kwargs: streams.append(_FakeStream(**kwargs)) or streams[-1],
    )
    deck = MagicMock(name="MiniDeck")
    deck.render_block.return_value = np.array([[1.4, -1.6], [0.25, -0.25]], dtype=np.float32)
    player = TwoDeckPlayer(0, deck, state=_cold_state())
    player.start()

    out = np.empty((2, 2), dtype=np.float32)
    streams[0].kwargs["callback"](out, 2, None, None)

    np.testing.assert_array_equal(
        out,
        np.array([[1.0, -1.0], [0.25, -0.25]], dtype=np.float32),
    )


def test_two_deck_player_refuses_playback_during_audible_live_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_stream_cls = MagicMock(name="sd.OutputStream")
    monkeypatch.setattr("sounddevice.OutputStream", mock_stream_cls)
    state = MagicMock(name="MusicState_stub")
    state.session_active = True
    state.audible_deck = "A"

    player = TwoDeckPlayer(0, _deck(), state=state)
    player.start()

    mock_stream_cls.assert_not_called()


def test_two_deck_player_does_not_touch_playback_queue() -> None:
    src = inspect.getsource(two_deck_player)

    assert "PlaybackQueue" not in src
