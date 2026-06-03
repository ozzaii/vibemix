# SPDX-License-Identifier: Apache-2.0
"""Learn tutor speech audio callback wiring."""
from __future__ import annotations

from unittest.mock import MagicMock

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
