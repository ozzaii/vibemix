# SPDX-License-Identifier: Apache-2.0
"""PlaybackQueueAudioOutput — SINK-01..10 + PKG-04.

Pins capture_frame → PlaybackQueue.push + VoiceRecorder.push_voice + segment
timing; flush → on_playback_finished only when a segment was started;
clear_buffer is a no-op.
"""

from __future__ import annotations

import asyncio

from livekit.agents.voice import io as voice_io

from vibemix.agent import PlaybackQueueAudioOutput
from vibemix.audio import OUTPUT_SR

# ---------- fixtures ----------


def _build_sink(mocker, sample_rate: int = OUTPUT_SR):
    """Build a PlaybackQueueAudioOutput with the parent __init__ mocked so we
    don't depend on a real LiveKit session/Session-router state."""
    mocker.patch.object(voice_io.AudioOutput, "__init__", return_value=None)
    # The event-emitter base class initializes _events in its __init__; since
    # we mocked __init__, also mock on_playback_started + on_playback_finished
    # at the *class* level so dispatch never touches the missing _events attr.
    mocker.patch.object(voice_io.AudioOutput, "on_playback_started", return_value=None)
    mocker.patch.object(voice_io.AudioOutput, "on_playback_finished", return_value=None)
    playback = mocker.MagicMock()
    recorder = mocker.MagicMock()
    sink = PlaybackQueueAudioOutput(playback, recorder, sample_rate=sample_rate)
    # Parent __init__ was mocked; provide the `sample_rate` property fallback
    # path by setting the underlying attribute the property reads. LiveKit's
    # AudioOutput stores sample_rate; we set it manually to match.
    sink._sample_rate = sample_rate  # type: ignore[attr-defined]
    # Mock super().capture_frame so the parent doesn't try to write anywhere.
    mocker.patch.object(
        voice_io.AudioOutput, "capture_frame", new=mocker.AsyncMock(return_value=None)
    )
    return sink, playback, recorder


def _make_frame(data: bytes = b"\x00\x01\x02\x03", samples: int = 480, sr: int = OUTPUT_SR):
    """Plain stand-in for rtc.AudioFrame — bytes(frame.data) handles both."""

    class _F:
        pass

    f = _F()
    f.data = data
    f.samples_per_channel = samples
    f.sample_rate = sr
    return f


def _run(coro):
    return asyncio.run(coro)


# ---------- SINK-01..10 ----------


def test_sink_01_subclass_and_default_sample_rate(mocker) -> None:
    """SINK-01: subclass of voice_io.AudioOutput; default sample_rate == OUTPUT_SR."""
    assert issubclass(PlaybackQueueAudioOutput, voice_io.AudioOutput)
    assert OUTPUT_SR == 24000
    _sink, _, _ = _build_sink(mocker)
    # Provided default was OUTPUT_SR — we passed it explicitly above; verify
    # the constructor signature default by inspecting the signature.
    import inspect

    sig = inspect.signature(PlaybackQueueAudioOutput.__init__)
    assert sig.parameters["sample_rate"].default == OUTPUT_SR


def test_sink_02_super_init_kwargs(mocker) -> None:
    """SINK-02: super().__init__ called with label, capabilities(pause=False),
    sample_rate."""
    mocker.patch.object(voice_io.AudioOutput, "__init__", return_value=None)
    playback = mocker.MagicMock()
    recorder = mocker.MagicMock()
    PlaybackQueueAudioOutput(playback, recorder, sample_rate=24000)
    kw = voice_io.AudioOutput.__init__.call_args.kwargs
    assert kw["label"] == "dj-cohost.playback"
    assert kw["sample_rate"] == 24000
    caps = kw["capabilities"]
    # capabilities is voice_io.AudioOutputCapabilities(pause=False)
    assert getattr(caps, "pause", None) is False


def test_sink_03_first_frame_fires_on_playback_started(mocker) -> None:
    """SINK-03: first capture_frame sets _segment_started_at and calls
    on_playback_started."""
    sink, _, _ = _build_sink(mocker)
    assert sink._segment_started_at is None

    _run(sink.capture_frame(_make_frame()))

    assert sink._segment_started_at is not None
    voice_io.AudioOutput.on_playback_started.assert_called_once()
    kw = voice_io.AudioOutput.on_playback_started.call_args.kwargs
    assert kw["created_at"] == sink._segment_started_at


def test_sink_04_second_frame_does_not_refire_on_playback_started(mocker) -> None:
    """SINK-04: only fires once per segment."""
    sink, _, _ = _build_sink(mocker)

    _run(sink.capture_frame(_make_frame()))
    _run(sink.capture_frame(_make_frame()))

    assert voice_io.AudioOutput.on_playback_started.call_count == 1


def test_sink_05_push_to_playback_and_recorder(mocker) -> None:
    """SINK-05: capture_frame pushes bytes to both PlaybackQueue + VoiceRecorder."""
    sink, playback, recorder = _build_sink(mocker)
    payload = b"\x00\x01\x02\x03\x04\x05"

    _run(sink.capture_frame(_make_frame(data=payload)))

    playback.push.assert_called_once_with(payload)
    recorder.push_voice.assert_called_once_with(payload)


def test_sink_06_empty_data_is_noop_for_push(mocker) -> None:
    """SINK-06: bytes(frame.data) == b"" → no push, no push_voice."""
    sink, playback, recorder = _build_sink(mocker)
    _run(sink.capture_frame(_make_frame(data=b"")))
    assert playback.push.call_count == 0
    assert recorder.push_voice.call_count == 0


def test_sink_07_segment_duration_accumulates(mocker) -> None:
    """SINK-07: two frames @ 480 samples / 24000 Hz → 0.04s total."""
    sink, _, _ = _build_sink(mocker)
    _run(sink.capture_frame(_make_frame(samples=480, sr=24000)))
    _run(sink.capture_frame(_make_frame(samples=480, sr=24000)))
    assert abs(sink._segment_duration - 0.04) < 1e-6


def test_sink_08_flush_emits_on_playback_finished(mocker) -> None:
    """SINK-08: flush after at least one frame → on_playback_finished fires
    with playback_position=_segment_duration, interrupted=False. State resets."""
    sink, _, _ = _build_sink(mocker)
    mocker.patch.object(voice_io.AudioOutput, "flush", return_value=None)

    _run(sink.capture_frame(_make_frame(samples=480, sr=24000)))
    pre_duration = sink._segment_duration
    sink.flush()

    voice_io.AudioOutput.on_playback_finished.assert_called_once()
    kw = voice_io.AudioOutput.on_playback_finished.call_args.kwargs
    assert abs(kw["playback_position"] - pre_duration) < 1e-6
    assert kw["interrupted"] is False
    assert sink._segment_started_at is None
    assert sink._segment_duration == 0.0


def test_sink_09_flush_without_segment_is_noop_for_on_playback_finished(mocker) -> None:
    """SINK-09: flush on fresh sink → on_playback_finished NOT called;
    super().flush() still called."""
    sink, _, _ = _build_sink(mocker)
    flush_super = mocker.patch.object(voice_io.AudioOutput, "flush", return_value=None)

    sink.flush()

    voice_io.AudioOutput.on_playback_finished.assert_not_called()
    flush_super.assert_called_once()


def test_sink_10_clear_buffer_is_noop(mocker) -> None:
    """SINK-10: clear_buffer returns None and does not touch playback/recorder."""
    sink, playback, recorder = _build_sink(mocker)
    out = sink.clear_buffer()
    assert out is None
    assert playback.method_calls == []
    assert recorder.method_calls == []


def test_pkg_04_playback_queue_audio_output_exported() -> None:
    """PKG-04: PlaybackQueueAudioOutput resolves from vibemix.agent."""
    import vibemix.agent as vagent

    assert "PlaybackQueueAudioOutput" in vagent.__all__
