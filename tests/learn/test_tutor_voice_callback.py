# SPDX-License-Identifier: Apache-2.0
"""Learn tutor speech audio callback wiring."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from vibemix.__main__ import _build_learn_tutor_speak_audio
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState


def _runtime(
    callback=None,
) -> tuple[LessonRuntime, MagicMock]:
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(
            current_lesson_id="L2.01",
            current_course_id="course_2_transitions",
            current_controller_id="pioneer_ddj_flx4",
        ),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        tutor_speak_audio=callback,
    )
    return runtime, ipc


def test_tutor_beat_calls_audio_callback_once_with_text_and_marker() -> None:
    calls: list[tuple[str, str]] = []
    runtime, ipc = _runtime(lambda text, marker: calls.append((text, marker)))

    runtime._emit_tutor_beat(0)

    assert len(calls) == 1
    text, marker = calls[0]
    assert text.startswith("sync stays off")
    assert marker == "L201.beat0"
    payload = ipc.emit.call_args.args[0]["payload"]
    assert payload["text"] == text
    assert payload["tts_marker"] == marker


def test_missing_tutor_audio_callback_keeps_subtitle_emit_safe() -> None:
    runtime, ipc = _runtime(None)

    runtime._emit_tutor_beat(0)

    payload = ipc.emit.call_args.args[0]["payload"]
    assert payload["tts_marker"] == "L201.beat0"


class _FakePlayback:
    def __init__(self) -> None:
        self.chunks: list[bytes] = []

    def push(self, pcm: bytes) -> None:
        self.chunks.append(pcm)


class _FakeTutorTTS:
    sample_rate = 24_000

    def synthesize_pcm(self, text: str, on_pcm) -> None:
        assert text
        on_pcm(b"\x01\x00" * 32)


class _FailingTutorTTS:
    sample_rate = 24_000

    def synthesize_pcm(self, _text: str, _on_pcm) -> None:
        raise RuntimeError("voice offline")


def _wait_for(done: threading.Event) -> None:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if done.wait(0.01):
            return
    raise AssertionError("timed out waiting for Learn tutor voice thread")


def test_learn_tutor_voice_logs_queue_and_completion() -> None:
    playback = _FakePlayback()
    events: list[tuple[str, dict]] = []
    done = threading.Event()

    def log(kind: str, fields: dict) -> None:
        events.append((kind, dict(fields)))
        if kind == "learn_tutor_voice_complete":
            done.set()

    speak = _build_learn_tutor_speak_audio(
        voice_tts=_FakeTutorTTS(),
        playback=playback,
        muted=lambda: False,
        event_logger=log,
    )

    speak("sync stays off for this drill.", "L201.beat0")
    _wait_for(done)

    assert [kind for kind, _fields in events] == [
        "learn_tutor_voice_queued",
        "learn_tutor_voice_complete",
    ]
    assert events[0][1] == {"tts_marker": "L201.beat0", "chars": 30}
    assert events[1][1] == {"tts_marker": "L201.beat0", "bytes": 64}
    assert playback.chunks == [b"\x01\x00" * 32]


def test_learn_tutor_voice_logs_muted_skip_without_thread() -> None:
    playback = _FakePlayback()
    events: list[tuple[str, dict]] = []
    speak = _build_learn_tutor_speak_audio(
        voice_tts=_FakeTutorTTS(),
        playback=playback,
        muted=lambda: True,
        event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    speak("line", "L201.beat0")

    assert events == [
        (
            "learn_tutor_voice_skipped",
            {"reason": "muted", "tts_marker": "L201.beat0"},
        )
    ]
    assert playback.chunks == []


def test_learn_tutor_voice_logs_synthesis_error() -> None:
    playback = _FakePlayback()
    events: list[tuple[str, dict]] = []
    done = threading.Event()

    def log(kind: str, fields: dict) -> None:
        events.append((kind, dict(fields)))
        if kind == "learn_tutor_voice_error":
            done.set()

    speak = _build_learn_tutor_speak_audio(
        voice_tts=_FailingTutorTTS(),
        playback=playback,
        muted=lambda: False,
        event_logger=log,
    )

    speak("line", "L201.beat0")
    _wait_for(done)

    assert [kind for kind, _fields in events] == [
        "learn_tutor_voice_queued",
        "learn_tutor_voice_error",
    ]
    assert events[1][1] == {"tts_marker": "L201.beat0", "error": "RuntimeError"}
    assert playback.chunks == []
