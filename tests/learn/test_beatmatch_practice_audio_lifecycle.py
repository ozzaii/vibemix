# SPDX-License-Identifier: Apache-2.0
"""Audible beatmatch-practice player lifecycle regression tests."""

from __future__ import annotations

from unittest.mock import MagicMock

from vibemix.learn.curriculum import course_lesson_ids
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState


class _FakePracticePlayer:
    def __init__(self, *, fail_start: bool = False) -> None:
        self.fail_start = fail_start
        self.starts = 0
        self.stops = 0

    def start(self) -> None:
        self.starts += 1
        if self.fail_start:
            raise RuntimeError("boom")

    def stop(self) -> None:
        self.stops += 1


def _runtime() -> LessonRuntime:
    return LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=LearnProgress(),
    )


def _runtime_with_recorder(recorder) -> LessonRuntime:
    return LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=LearnProgress(),
        beatmatch_practice_action_recorder=recorder,
    )


def _load_begin(
    runtime: LessonRuntime,
    *,
    lesson_id: str,
    course_id: str = "course_2_transitions",
) -> None:
    runtime.send(
        "load",
        lesson_id=lesson_id,
        course_id=course_id,
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")


def test_beatmatch_lesson_starts_and_stops_practice_player(monkeypatch) -> None:
    monkeypatch.setattr("vibemix.learn.progress.save_progress", lambda _progress: None)
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L2.01")

    assert player.starts == 1

    runtime.send("observer_complete", completed=True)

    assert player.stops == 1


def test_non_beatmatch_lesson_does_not_start_practice_player() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L0.00-press-play", course_id="course_0")

    assert player.starts == 0


def test_eq_swap_lesson_starts_practice_player() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L2.04")

    assert player.starts == 1


def test_course_one_deck_control_lesson_starts_practice_player() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L1.03", course_id="course_1_anatomy")

    assert player.starts == 1


def test_course_one_master_volume_lesson_starts_practice_player() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L1.09", course_id="course_1_anatomy")

    assert player.starts == 1


def test_course_one_waveform_demo_lesson_starts_practice_player() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L1.13", course_id="course_1_anatomy")

    assert player.starts == 1


def test_course_one_recital_starts_practice_player_from_flow_controls() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L1.16", course_id="course_1_anatomy")

    assert player.starts == 1


def test_course_two_conceptual_demo_lessons_start_practice_player() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L2.11")

    assert player.starts == 1

    runtime.send("observer_complete", completed=True)
    _load_begin(runtime, lesson_id="L2.13")

    assert player.starts == 2


def test_beginner_practice_courses_keep_all_non_dialog_lessons_audible() -> None:
    """Course 1/2 practice lessons keep the owned demo loop available."""

    audible: dict[str, bool] = {}
    for course_id in ("course_1_anatomy", "course_2_transitions"):
        for lesson_id in course_lesson_ids(course_id):
            runtime = _runtime()
            player = _FakePracticePlayer()
            runtime.set_beatmatch_practice_player(player)

            _load_begin(runtime, lesson_id=lesson_id, course_id=course_id)

            audible[lesson_id] = player.starts > 0

    silent = {lesson_id for lesson_id, started in audible.items() if not started}
    assert silent == {"L1.01"}
    assert all(audible[lesson_id] for lesson_id in course_lesson_ids("course_2_transitions"))


def test_loop_and_hotcue_lessons_start_practice_player() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L2.09")

    assert player.starts == 1

    runtime.send("observer_complete", completed=True)
    _load_begin(runtime, lesson_id="L2.10")

    assert player.starts == 2


def test_recovery_drill_lesson_starts_practice_player_from_drill_shapes() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L3.05", course_id="course_3_play_mode")

    assert player.starts == 1


def test_practice_audio_ack_applies_before_lesson_gate() -> None:
    calls: list[tuple[str | None, dict]] = []

    def recorder(lesson_id: str | None, midi: dict) -> bool:
        calls.append((lesson_id, dict(midi)))
        return False

    runtime = _runtime_with_recorder(recorder)
    _load_begin(runtime, lesson_id="L2.01")

    runtime.handle_practice_audio_ack(
        {"type": "cc", "control": "tempo", "deck": "B", "value": 64, "prev_value": 63}
    )

    assert calls == [
        (
            "L2.01",
            {"type": "cc", "control": "tempo", "deck": "B", "value": 64, "prev_value": 63},
        )
    ]


def test_free_practice_ack_records_practice_receipt_without_completion(
    monkeypatch,
) -> None:
    calls: list[tuple[str | None, dict]] = []
    saved: list[LearnProgress] = []

    def recorder(lesson_id: str | None, midi: dict) -> bool:
        calls.append((lesson_id, dict(midi)))
        return False

    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    progress = LearnProgress()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        beatmatch_practice_action_recorder=recorder,
        waveform_payload_loader=lambda: {"sample_rate": 44_100, "decks": {}},
    )
    player = _FakePracticePlayer()
    runtime.set_beatmatch_practice_player(player)

    runtime.handle_practice_audio_ack(
        {
            "type": "cc",
            "control": "eq_hi",
            "deck": "A",
            "value": 127,
            "prev_value": 64,
            "source": "click",
        }
    )

    assert player.starts == 1
    assert runtime.current_state.id == "idle"
    assert calls == [
        (
            None,
            {
                "type": "cc",
                "control": "eq_hi",
                "deck": "A",
                "value": 127,
                "prev_value": 64,
                "source": "click",
            },
        )
    ]
    assert len(saved) == 1
    assert progress.lessons["L1.03"]["completed"] is False
    assert progress.lessons["L1.03"]["practice_sources"] == {
        "hardware": 0,
        "screen": 1,
    }
    assert progress.lessons["L1.03"]["last_practice_source"] == "screen"
    assert progress.lessons["L1.03"]["completed_at"] is None
    progress_snapshots = [
        call.args[0]
        for call in ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.progress_state"
    ]
    assert progress_snapshots
    mission = progress_snapshots[-1]["payload"]["progress"]["next_practice_mission"]
    assert mission["lesson_id"] == "L1.03"
    assert mission["mode"] == "finish"


def test_free_practice_receipt_dedupes_repeated_drag_frames(monkeypatch) -> None:
    saved: list[LearnProgress] = []
    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
        beatmatch_practice_action_recorder=lambda _lesson_id, _midi: False,
        waveform_payload_loader=lambda: {"sample_rate": 44_100, "decks": {}},
    )
    runtime.set_beatmatch_practice_player(_FakePracticePlayer())

    for value in (72, 96, 127):
        runtime.handle_practice_audio_ack(
            {
                "type": "cc",
                "control": "eq_hi",
                "deck": "A",
                "value": value,
                "prev_value": 64,
                "source": "click",
            }
        )

    assert len(saved) == 1
    assert progress.lessons["L1.03"]["practice_sources"] == {
        "hardware": 0,
        "screen": 1,
    }


def test_loading_another_lesson_stops_active_practice_player() -> None:
    runtime = _runtime()
    player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L2.01")
    runtime.send("observer_complete", completed=True)
    runtime.send(
        "load",
        lesson_id="L2.02",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )

    assert player.starts == 1
    assert player.stops >= 1


def test_replacing_practice_player_stops_old_player() -> None:
    runtime = _runtime()
    old_player = _FakePracticePlayer()
    new_player = _FakePracticePlayer()

    runtime.set_beatmatch_practice_player(old_player)
    _load_begin(runtime, lesson_id="L2.01")
    runtime.set_beatmatch_practice_player(new_player)

    assert old_player.starts == 1
    assert old_player.stops == 1
    assert new_player.starts == 1


def test_practice_player_start_failure_does_not_wedge_lesson(capsys) -> None:
    runtime = _runtime()
    player = _FakePracticePlayer(fail_start=True)

    runtime.set_beatmatch_practice_player(player)
    _load_begin(runtime, lesson_id="L2.01")

    assert runtime.current_state.id == "awaiting_action"
    assert player.starts == 1
    assert "beatmatch practice player start failed" in capsys.readouterr().err
