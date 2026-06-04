# SPDX-License-Identifier: Apache-2.0
"""Learn runtime evidence grounding regression tests."""
from __future__ import annotations

import inspect
from unittest.mock import MagicMock

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState
from vibemix.coach.citation_linter import CitationLinter
from vibemix.learn.beatmatch_practice_driver import BeatmatchPracticeDriver
from vibemix.learn.control_practice import CONTROL_PRACTICE_GRADED_EVENT
from vibemix.learn.cue_placement_practice_driver import CuePlacementPracticeDriver
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import (
    BeatmatchPracticeSnapshot,
    CuePlacementPracticeSnapshot,
    LessonRuntime,
)
from vibemix.learn.skill_tree import SKILL_MANIFEST
from vibemix.learn.state import LearnState
from vibemix.state.evidence_registry import EvidenceRegistry

_SR = 44100


def _runtime_with_evidence(
    *,
    clock_value: float,
) -> tuple[LessonRuntime, EvidenceRegistry, MagicMock]:
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: clock_value,
    )
    return runtime, registry, ipc


def _beat_grid(bpm: float = 128.0) -> BeatGrid:
    return BeatGrid(anchor_frame=0.0, bpm=bpm, sample_rate=_SR)


def _locked_beatmatch_snapshot() -> BeatmatchPracticeSnapshot:
    grid = _beat_grid()
    return BeatmatchPracticeSnapshot(
        grid_a=grid,
        grid_b=grid,
        deck_state=DeckState(
            a_frame=0.0,
            b_frame=0.0,
            rate_a=1.0,
            rate_b=1.0,
            xfader=0.5,
        ),
    )


def _drifting_beatmatch_snapshot() -> BeatmatchPracticeSnapshot:
    grid = _beat_grid()
    return BeatmatchPracticeSnapshot(
        grid_a=grid,
        grid_b=grid,
        deck_state=DeckState(
            a_frame=0.0,
            b_frame=grid.beat_len_frames * 0.25,
            rate_a=1.0,
            rate_b=1.0,
            xfader=0.5,
        ),
    )


def _sliding_beatmatch_snapshot() -> BeatmatchPracticeSnapshot:
    grid = _beat_grid()
    return BeatmatchPracticeSnapshot(
        grid_a=grid,
        grid_b=grid,
        deck_state=DeckState(
            a_frame=0.0,
            b_frame=grid.beat_len_frames * -0.05,
            rate_a=1.0,
            rate_b=1.0,
            xfader=0.5,
        ),
    )


def _stopped_beatmatch_snapshot() -> BeatmatchPracticeSnapshot:
    grid = _beat_grid()
    return BeatmatchPracticeSnapshot(
        grid_a=grid,
        grid_b=grid,
        deck_state=DeckState(
            a_frame=0.0,
            b_frame=0.0,
            rate_a=1.0,
            rate_b=0.0,
            xfader=0.5,
        ),
    )


def _make_beatmatching_competent(progress: LearnProgress) -> None:
    spec = SKILL_MANIFEST["beatmatching"]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-02T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)


def _make_phrasing_competent(progress: LearnProgress) -> None:
    spec = SKILL_MANIFEST["phrasing_performance"]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-02T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)


def _make_skill_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-02T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)


def _hint_payloads(ipc: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args
        and call.args[0].get("type") == "ipc.learn.tutor_speak"
        and call.args[0].get("payload", {}).get("data_state") == "hint"
    ]


def _tutor_speak_payloads(ipc: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.tutor_speak"
    ]


def _live_grade_payloads(ipc: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.live_grade"
    ]


def test_runtime_grade_feedback_avoids_empty_compliments() -> None:
    """Runtime-authored grade lines must describe the measured result."""

    source = (
        inspect.getsource(LessonRuntime._emit_live_beatmatch_grade)
        + inspect.getsource(LessonRuntime._emit_live_cue_placement_grade)
        + inspect.getsource(LessonRuntime._recovery_drill_success_text)
    ).lower()
    for token in (
        "nice",
        "good -",
        "great job",
        "awesome",
        "amazing",
        "congrats",
        "you got this",
    ):
        assert token not in source


def test_adaptive_midi_hint_writes_registry_and_time_keyed_citation() -> None:
    """MIDI adaptive coaching cites the exact registry-backed action."""
    runtime, registry, ipc = _runtime_with_evidence(clock_value=12.7)
    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    handled = runtime.handle_mismatch_ack(
        {
            "type": "cc",
            "control": "eq_mid",
            "deck": "A",
            "value": 45,
            "prev_value": 20,
            "source": "midi",
            "direction": "down",
        }
    )

    assert handled is True
    hints = _hint_payloads(ipc)
    assert hints[-1]["citations"] == ["[midi:eq_mid:A@12.7]", "[screen:eq_hi:A]"]

    snapshot = registry.snapshot()
    assert 12.7 in snapshot["midi"]["eq_mid:A"]
    assert 12.7 in snapshot["screen"]["eq_hi:A"]

    result = CitationLinter().check(
        " ".join(hints[-1]["citations"]),
        snapshot,
        mode="live",
    )
    assert result.valid is True


def test_timed_hint_cites_the_registry_backed_highlight() -> None:
    """No-action hints cite the control the screen already highlighted."""
    runtime, registry, ipc = _runtime_with_evidence(clock_value=18.0)
    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send("strike")

    hint = _hint_payloads(ipc)[-1]
    assert hint["citations"] == ["[screen:eq_hi:A]"]

    snapshot = registry.snapshot()
    assert 18.0 in snapshot["screen"]["eq_hi:A"]
    result = CitationLinter().check(
        " ".join(hint["citations"]),
        snapshot,
        mode="live",
    )
    assert result.valid is True


def test_matching_action_writes_registry_for_debrief_grounding() -> None:
    """A successful lesson action is also recorded for later debrief/profile use."""
    runtime, registry, _ipc = _runtime_with_evidence(clock_value=33.3)
    runtime.send(
        "load",
        lesson_id="L0.00-press-play",
        course_id="course_0",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    runtime.send(
        "ack_action",
        midi={
            "type": "button",
            "control": "play",
            "deck": "A",
            "direction": "down",
            "source": "midi",
        },
    )

    snapshot = registry.snapshot()
    assert 33.3 in snapshot["midi"]["play:A"]
    assert 33.3 in snapshot["screen"]["play:A"]
    result = CitationLinter().check(
        "[midi:play:A@33.3] [screen:play:A]",
        snapshot,
        mode="live",
    )
    assert result.valid is True


def test_runtime_logs_learn_milestones_to_session_event_sink() -> None:
    """Learn leaves a lesson timeline in the existing recordings spine."""
    events: list[tuple[str, dict]] = []
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=LearnProgress(),
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send(
        "ack_action",
        midi={
            "type": "cc",
            "control": "eq_hi",
            "deck": "A",
            "value": 127,
            "prev_value": 0,
            "source": "midi",
        },
    )

    kinds = [kind for kind, _fields in events]
    assert "learn_lesson_loaded" in kinds
    assert "learn_tutor_speak" in kinds
    assert "ai_message" in kinds
    assert "learn_action_observed" in kinds

    ai_message = next(fields for kind, fields in events if kind == "ai_message")
    assert ai_message["engine"] == "learn_tutor"
    assert ai_message["surface"] == "learn"
    assert ai_message["direction"] == "assistant"
    assert ai_message["event"] == "learn_tutor_speak"
    assert ai_message["provider"] == "authored_fixture"
    assert ai_message["stop_reason"] == "authored_fixture"
    assert ai_message["message"]
    assert ai_message["extra"]["lesson_id"] == "L1.03"
    assert ai_message["extra"]["course_id"] == "course_1_anatomy"
    assert ai_message["extra"]["step_id"] == "L1.03.practice"
    assert ai_message["extra"]["tts_marker"]
    assert ai_message["extra"]["source"] == "learn_runtime"

    action = next(fields for kind, fields in events if kind == "learn_action_observed")
    assert action["lesson_id"] == "L1.03"
    assert action["step_id"] == "L1.03.practice"
    assert action["observed_control_id"] == "eq_hi:A"
    assert action["expected_control_id"] == "eq_hi:A"
    assert action["matched"] is True
    assert isinstance(action["evidence_time"], float)


def test_matched_eq_lesson_action_writes_control_receipt_and_progress(monkeypatch) -> None:
    """A matched Learn control action can credit Skill Wall progress."""
    saved: list[LearnProgress] = []
    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    progress = LearnProgress()
    _make_skill_competent(progress, "eq_mixing")
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    events: list[tuple[str, dict]] = []
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 58.25,
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    runtime.send(
        "load",
        lesson_id="L2.04",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send(
        "ack_action",
        midi={
            "type": "cc",
            "control": "eq_low",
            "deck": "A",
            "value": 127,
            "prev_value": 0,
            "source": "midi",
        },
    )

    assert registry.has("ev", CONTROL_PRACTICE_GRADED_EVENT, 58.25, tol=1.0)
    assert progress.skills["eq_mixing"]["live_proof_count"] == 1
    assert progress in saved
    assert any(
        call.args[0].get("type") == "ipc.learn.progress_state"
        and call.args[0].get("payload", {}).get("progress", {}).get("skills", {})
        .get("eq_mixing", {})
        .get("live_proof_count")
        == 1
        for call in ipc.emit.call_args_list
    )
    event = next(
        fields for kind, fields in events if kind == "learn_control_practice_graded"
    )
    assert event["lesson_id"] == "L2.04"
    assert event["control"] == "eq_low"
    assert event["deck"] == "A"
    assert event["skill_id"] == "eq_mixing"
    assert event["credited"] == ["eq_mixing"]


def test_observer_ack_writes_control_receipt_before_lesson_cycle_ack(monkeypatch) -> None:
    """Observer-driven L1.14 actions still become cited control practice."""
    saved: list[LearnProgress] = []
    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    progress = LearnProgress()
    _make_skill_competent(progress, "eq_mixing")
    registry = EvidenceRegistry()
    observer = MagicMock(name="observer")
    observer.matches.return_value = True
    events: list[tuple[str, dict]] = []
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 60.0,
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )
    runtime.register_lesson_observer("L1.14", observer)
    midi = {
        "type": "cc",
        "control": "eq_low",
        "deck": "A",
        "value": 127,
        "prev_value": 0,
        "source": "midi",
    }

    runtime.send(
        "load",
        lesson_id="L1.14",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    handled = runtime.handle_observer_ack(midi)

    assert handled is True
    observer.ack.assert_called_once_with(lesson_id="L1.14")
    assert registry.has("ev", CONTROL_PRACTICE_GRADED_EVENT, 60.0, tol=1.0)
    assert progress.skills["eq_mixing"]["live_proof_count"] == 1
    assert progress in saved
    action = next(fields for kind, fields in events if kind == "learn_action_observed")
    assert action["lesson_id"] == "L1.14"
    assert action["observed_control_id"] == "eq_low:A"
    assert action["expected_control_id"] is None
    control_grade = next(
        fields for kind, fields in events if kind == "learn_control_practice_graded"
    )
    assert control_grade["lesson_id"] == "L1.14"
    assert control_grade["skill_id"] == "eq_mixing"
    assert control_grade["credited"] == ["eq_mixing"]


def test_beatmatch_practice_tick_writes_receipt_and_credits_once(monkeypatch) -> None:
    """The Learn-owned beatmatch practice hook uses the exact evidence clock."""
    saved: list[LearnProgress] = []
    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    progress = LearnProgress()
    _make_beatmatching_competent(progress)
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    events: list[tuple[str, dict]] = []
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 42.4,
        beatmatch_practice_loader=_locked_beatmatch_snapshot,
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    result = runtime._grade_beatmatch_practice_tick()

    assert result is not None
    assert result.event is not None
    assert result.grade.verdict == "locked"
    assert result.credited == ("beatmatching",)
    assert registry.has("ev", "BEATMATCH_GRADED", 42.4, tol=1.0)
    assert progress.skills["beatmatching"]["live_proof_count"] == 1
    assert saved == [progress]
    assert any(
        call.args[0].get("type") == "ipc.learn.progress_state"
        for call in ipc.emit.call_args_list
    )
    assert events[-1][0] == "learn_beatmatch_practice_graded"
    assert events[-1][1]["credited"] == ["beatmatching"]

    repeated = runtime._grade_beatmatch_practice_tick()

    assert repeated is not None
    assert repeated.event is None
    assert repeated.credited == ()
    assert progress.skills["beatmatching"]["live_proof_count"] == 1


def test_live_beatmatch_grade_voices_locked_with_resolving_citation(monkeypatch) -> None:
    """Q3: a credited locked grade becomes an authored cited tutor line."""
    monkeypatch.setattr("vibemix.learn.progress.save_progress", lambda _progress: None)
    progress = LearnProgress()
    _make_beatmatching_competent(progress)
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 42.4,
        beatmatch_practice_loader=_locked_beatmatch_snapshot,
    )
    runtime.send(
        "load",
        lesson_id="L2.01",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )

    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())

    payload = _tutor_speak_payloads(ipc)[-1]
    live_grade = _live_grade_payloads(ipc)[-1]
    assert payload["text"] == "tempo and phase are matched."
    assert payload["tts_marker"] == "L2.01.grade"
    assert payload["data_state"] == "hint"
    assert payload["citations"] == ["[ev:BEATMATCH_GRADED@42.400]"]
    assert live_grade == {
        "verdict": "locked",
        "phase_error_beats": 0.0,
        "score": 1.0,
        "citation": "[ev:BEATMATCH_GRADED@42.400]",
    }
    result = CitationLinter().check(" ".join(payload["citations"]), registry.snapshot())
    assert result.valid is True

    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())

    assert len(_tutor_speak_payloads(ipc)) == 1
    assert len(_live_grade_payloads(ipc)) == 2
    assert _live_grade_payloads(ipc)[-1]["citation"] is None


def test_credited_beatmatch_grade_completes_and_loads_next_lesson(monkeypatch) -> None:
    """A cited locked L2.01 grade credits, completes, snapshots, and opens L2.02."""
    monkeypatch.setattr("vibemix.learn.progress.save_progress", lambda _progress: None)
    progress = LearnProgress()
    _make_beatmatching_competent(progress)
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 42.4,
        beatmatch_practice_loader=_locked_beatmatch_snapshot,
        beatmatch_practice_action_recorder=lambda _lesson_id, _midi: True,
    )
    runtime.send(
        "load",
        lesson_id="L2.01",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    consumed = runtime.handle_beatmatch_practice_ack(
        {"type": "cc", "control": "tempo", "deck": "B", "value": 64, "prev_value": 0}
    )
    runtime.send("finish")

    assert consumed is True
    assert progress.skills["beatmatching"]["live_proof_count"] == 1
    assert progress.lessons["L2.01"]["completed"] is True
    assert runtime._learn.current_lesson_id == "L2.02"
    assert runtime.current_state.id == "awaiting_action"
    emitted = [call.args[0] for call in ipc.emit.call_args_list if call.args]
    complete_index = next(
        index
        for index, env in enumerate(emitted)
        if isinstance(env, dict) and env.get("type") == "ipc.learn.complete_lesson"
    )
    next_loaded_index = next(
        index
        for index, env in enumerate(emitted)
        if (
            isinstance(env, dict)
            and env.get("type") == "ipc.learn.lesson_loaded"
            and env.get("payload", {}).get("lesson_id") == "L2.02"
        )
    )
    assert complete_index < next_loaded_index
    snapshots = [
        env["payload"]["progress"]
        for env in emitted
        if isinstance(env, dict) and env.get("type") == "ipc.learn.progress_state"
    ]
    assert snapshots[-1]["skills"]["beatmatching"]["live_proof_count"] == 1
    assert any(row["skill_id"] == "beatmatching" for row in snapshots[-1]["skill_wall"])


def test_live_beatmatch_grade_cites_locked_event_before_mastery_credit() -> None:
    """A measured locked grade cites its event even before skill credit unlocks."""
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 43.2,
        beatmatch_practice_loader=_locked_beatmatch_snapshot,
    )
    runtime.send(
        "load",
        lesson_id="L2.01",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )

    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())

    payload = _tutor_speak_payloads(ipc)[-1]
    live_grade = _live_grade_payloads(ipc)[-1]
    assert payload["text"] == "tempo and phase are matched."
    assert payload["citations"] == ["[ev:BEATMATCH_GRADED@43.200]"]
    assert live_grade["citation"] == "[ev:BEATMATCH_GRADED@43.200]"
    assert registry.has("ev", "BEATMATCH_GRADED", 43.2, tol=1.0)
    assert progress.skills.get("beatmatching", {}).get("live_proof_count", 0) == 0


def test_recovery_drill_lesson_arms_each_authored_owned_deck_miss() -> None:
    """L3.05 is not just metadata: each authored drill changes the owned deck."""
    driver = BeatmatchPracticeDriver()
    registry = EvidenceRegistry()
    events: list[tuple[str, dict]] = []
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: 71.0,
        beatmatch_practice_loader=driver.snapshot,
        beatmatch_practice_action_recorder=driver.record_action,
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    runtime.send(
        "load",
        lesson_id="L3.05",
        course_id="course_3_play_mode",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    live_grades = _live_grade_payloads(runtime._ipc)
    assert live_grades[-1]["verdict"] == "tempo_off"
    assert live_grades[-1]["citation"] == "[ev:RECOVERY_DRILL_ARMED@71.000]"
    tutor_payload = _tutor_speak_payloads(runtime._ipc)[-1]
    assert tutor_payload["text"] == (
        "I pitched deck B up into the clash - hear that pull, then bail out clean."
    )
    assert tutor_payload["citations"] == ["[ev:RECOVERY_DRILL_ARMED@71.000]"]
    assert registry.has("ev", "RECOVERY_DRILL_ARMED", 71.0, tol=1.0)
    drill_events = [
        fields for kind, fields in events if kind == "learn_recovery_drill_armed"
    ]
    assert drill_events[-1]["drill"] == "key_clash"
    assert drill_events[-1]["evidence_time"] == 71.0

    handled = runtime.handle_step_ack(
        {"type": "button", "control": "lesson_continue", "direction": "down"}
    )

    assert handled is True
    live_grades = _live_grade_payloads(runtime._ipc)
    assert live_grades[-1]["verdict"] == "trainwreck"
    assert live_grades[-1]["citation"] == "[ev:RECOVERY_DRILL_ARMED@71.000]"
    tutor_payload = _tutor_speak_payloads(runtime._ipc)[-1]
    assert tutor_payload["text"] == (
        "Deck B is a quarter-beat off - the kicks are fighting, so cut or filter out."
    )
    assert tutor_payload["citations"] == ["[ev:RECOVERY_DRILL_ARMED@71.000]"]
    drill_events = [
        fields for kind, fields in events if kind == "learn_recovery_drill_armed"
    ]
    assert drill_events[-1]["drill"] == "misaligned_phrase"
    assert drill_events[-1]["evidence_time"] == 71.0
    assert runtime.current_state.id == "awaiting_action"


def test_recovery_drill_bailout_actions_give_meaningful_credit(monkeypatch) -> None:
    """Recovery drills credit the actual bailout move, not a generic continue click."""
    monkeypatch.setattr("vibemix.learn.progress.save_progress", lambda _progress: None)
    driver = BeatmatchPracticeDriver()
    registry = EvidenceRegistry()
    events: list[tuple[str, dict]] = []
    progress = LearnProgress()
    _make_skill_competent(progress, "transitions")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 72.5,
        beatmatch_practice_loader=driver.snapshot,
        beatmatch_practice_action_recorder=driver.record_action,
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )
    runtime.send(
        "load",
        lesson_id="L3.05",
        course_id="course_3_play_mode",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    handled = runtime.handle_recovery_drill_ack(
        {
            "type": "cc",
            "control": "eq_hi",
            "deck": "B",
            "direction": "up",
            "value": 110,
            "prev_value": 64,
            "source": "click",
        }
    )

    assert handled is True
    assert runtime.current_step_id == "L3.05.beat.0"
    hint = _hint_payloads(runtime._ipc)[-1]
    assert hint["text"] == (
        "That move does not get deck B out. Use echo-out, sweep deck B's "
        "filter, pull its volume down, or cut the crossfader away."
    )
    assert hint["citations"] == ["[ev:RECOVERY_DRILL_ARMED@72.500]"]
    assert not registry.has("ev", "RECOVERY_DRILL_RECOVERED", 72.5, tol=1.0)
    assert progress.skills["transitions"]["live_proof_count"] == 0

    handled = runtime.handle_recovery_drill_ack(
        {
            "type": "cc",
            "control": "filter",
            "deck": "B",
            "direction": "up",
            "value": 96,
            "prev_value": 64,
            "source": "click",
        }
    )

    assert handled is True
    assert runtime.current_state.id == "awaiting_action"
    assert runtime.current_step_id == "L3.05.beat.1"
    assert registry.has("ev", "RECOVERY_DRILL_RECOVERED", 72.5, tol=1.0)
    assert progress.skills["transitions"]["live_proof_count"] == 1
    tutor_texts = [payload["text"] for payload in _tutor_speak_payloads(runtime._ipc)]
    assert (
        "that filter sweep pulls deck B out, so deck A reads clean."
        in tutor_texts
    )
    recovery_events = [
        fields for kind, fields in events if kind == "learn_recovery_drill_recovered"
    ]
    assert recovery_events[-1]["bailout"] == "deck B filter sweep"
    assert recovery_events[-1]["credited"] == ["transitions"]

    handled = runtime.handle_recovery_drill_ack(
        {
            "type": "cc",
            "control": "vol",
            "deck": "B",
            "direction": "down",
            "value": 0,
            "prev_value": 80,
            "source": "click",
        }
    )

    assert handled is True
    assert progress.lessons["L3.05"]["completed"] is True
    assert runtime._learn.current_lesson_id == "L3.06"
    assert runtime.current_state.id == "awaiting_action"
    emitted_types = [
        call.args[0].get("type")
        for call in runtime._ipc.emit.call_args_list
        if call.args and isinstance(call.args[0], dict)
    ]
    assert "ipc.learn.complete_lesson" in emitted_types
    assert emitted_types.count("ipc.learn.advance") >= 2
    recovery_events = [
        fields for kind, fields in events if kind == "learn_recovery_drill_recovered"
    ]
    assert recovery_events[-1]["bailout"] == "deck B volume cut"
    assert recovery_events[-1]["credited"] == ["transitions"]
    assert progress.skills["transitions"]["live_proof_count"] == 2


def test_live_beatmatch_grade_voices_drift_without_fabricated_citation() -> None:
    """Measured non-locked coaching is authored, but no ev atom is invented."""
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: 13.0,
        beatmatch_practice_loader=_sliding_beatmatch_snapshot,
    )

    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())

    payload = _tutor_speak_payloads(ipc)[-1]
    live_grade = _live_grade_payloads(ipc)[-1]
    assert payload["text"] == "close, you're sliding behind — nudge the jog."
    assert payload["citations"] == []
    assert live_grade["verdict"] == "drifting"
    assert live_grade["citation"] is None
    assert live_grade["phase_error_beats"] > 0
    assert "ev" not in registry.snapshot()


def test_live_beatmatch_grade_abstain_emits_nothing() -> None:
    """Stopped decks keep the calibrated abstain silence."""
    runtime, _registry, ipc = _runtime_with_evidence(clock_value=7.0)
    runtime._beatmatch_practice_loader = _stopped_beatmatch_snapshot

    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())

    assert _tutor_speak_payloads(ipc) == []
    assert _live_grade_payloads(ipc) == []


def test_live_beatmatch_grade_dedupes_sustained_same_verdict() -> None:
    """The 1 Hz grade loop must not pulse unchanged drift as fresh feedback."""
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: 13.0,
        beatmatch_practice_loader=_sliding_beatmatch_snapshot,
    )

    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())
    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())

    assert len(_tutor_speak_payloads(ipc)) == 1
    assert len(_live_grade_payloads(ipc)) == 1


def test_live_beatmatch_grade_keeps_meter_updates_when_phase_changes() -> None:
    """Meaningful phase movement still reaches the meter without repeat speech."""
    grid = _beat_grid()
    snapshots = [
        BeatmatchPracticeSnapshot(
            grid_a=grid,
            grid_b=grid,
            deck_state=DeckState(
                a_frame=0.0,
                b_frame=grid.beat_len_frames * -0.05,
                rate_a=1.0,
                rate_b=1.0,
                xfader=0.5,
            ),
        ),
        BeatmatchPracticeSnapshot(
            grid_a=grid,
            grid_b=grid,
            deck_state=DeckState(
                a_frame=0.0,
                b_frame=grid.beat_len_frames * -0.08,
                rate_a=1.0,
                rate_b=1.0,
                xfader=0.5,
            ),
        ),
    ]
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: 13.0,
        beatmatch_practice_loader=lambda: snapshots.pop(0) if snapshots else None,
    )

    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())
    runtime._emit_live_beatmatch_grade(runtime._grade_beatmatch_practice_tick())

    assert len(_tutor_speak_payloads(ipc)) == 1
    grades = _live_grade_payloads(ipc)
    assert len(grades) == 2
    assert grades[0]["verdict"] == "drifting"
    assert grades[1]["verdict"] == "drifting"
    assert grades[1]["phase_error_beats"] > grades[0]["phase_error_beats"]


def test_live_beatmatch_grade_tick_stops_after_completion(monkeypatch) -> None:
    """Completed Learn lessons must not keep pulsing stale live-grade HUD frames."""
    monkeypatch.setattr("vibemix.learn.progress.save_progress", lambda _progress: None)
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: 13.0,
        beatmatch_practice_loader=_sliding_beatmatch_snapshot,
    )
    runtime.send(
        "load",
        lesson_id="L2.01",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    runtime._emit_live_beatmatch_grade_tick()

    assert len(_live_grade_payloads(ipc)) == 1

    runtime.send("observer_complete", completed=True)
    runtime._emit_live_beatmatch_grade_tick()

    assert runtime.current_state.id == "completed"
    assert len(_live_grade_payloads(ipc)) == 1


def test_matched_beatmatch_action_records_and_grades_immediately(monkeypatch) -> None:
    """A live matched lesson action can arm the owned-deck beatmatch grader."""
    saved: list[LearnProgress] = []
    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    progress = LearnProgress()
    _make_beatmatching_competent(progress)
    registry = EvidenceRegistry()
    events: list[tuple[str, dict]] = []
    recorded: list[tuple[str | None, dict]] = []
    armed = False

    def record_action(lesson_id: str | None, midi: dict) -> bool:
        nonlocal armed
        recorded.append((lesson_id, dict(midi)))
        armed = True
        return True

    def load_snapshot() -> BeatmatchPracticeSnapshot | None:
        return _locked_beatmatch_snapshot() if armed else None

    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 91.2,
        beatmatch_practice_loader=load_snapshot,
        beatmatch_practice_action_recorder=record_action,
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )
    runtime.send(
        "load",
        lesson_id="L2.02",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    runtime.send(
        "ack_action",
        midi={
            "type": "button",
            "control": "sync",
            "deck": "B",
            "direction": "down",
            "value": 127,
            "prev_value": 0,
        },
    )

    assert recorded == [
        (
            "L2.02",
            {
                "type": "button",
                "control": "sync",
                "deck": "B",
                "direction": "down",
                "value": 127,
                "prev_value": 0,
            },
        )
    ]
    assert registry.has("ev", "BEATMATCH_GRADED", 91.2, tol=1.0)
    assert progress.skills["beatmatching"]["live_proof_count"] == 1
    assert progress in saved
    assert any(kind == "learn_beatmatch_practice_graded" for kind, _fields in events)
    tutor_payload = _tutor_speak_payloads(runtime._ipc)[-1]
    assert tutor_payload["text"] == "tempo and phase are matched."
    assert tutor_payload["citations"] == ["[ev:BEATMATCH_GRADED@91.200]"]


def test_uncredited_beatmatch_practice_ack_stays_active_for_recovery() -> None:
    """A measured bad beatmatch grade coaches without completing the lesson."""
    progress = LearnProgress()
    registry = EvidenceRegistry()
    events: list[tuple[str, dict]] = []
    recorded: list[tuple[str | None, dict]] = []

    def record_action(lesson_id: str | None, midi: dict) -> bool:
        recorded.append((lesson_id, dict(midi)))
        return True

    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 92.4,
        beatmatch_practice_loader=_sliding_beatmatch_snapshot,
        beatmatch_practice_action_recorder=record_action,
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )
    runtime.send(
        "load",
        lesson_id="L2.01",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    handled = runtime.handle_beatmatch_practice_ack(
        {
            "type": "cc",
            "control": "tempo",
            "deck": "B",
            "direction": "up",
            "value": 100,
            "prev_value": 64,
            "source": "click",
        }
    )

    assert handled is True
    assert runtime.current_state.id == "awaiting_action"
    assert recorded == [
        (
            "L2.01",
            {
                "type": "cc",
                "control": "tempo",
                "deck": "B",
                "direction": "up",
                "value": 100,
                "prev_value": 64,
                "source": "click",
            },
        )
    ]
    assert _live_grade_payloads(runtime._ipc)[-1]["verdict"] == "drifting"
    tutor_payload = _tutor_speak_payloads(runtime._ipc)[-1]
    assert tutor_payload["text"] == "close, you're sliding behind — nudge the jog."
    assert tutor_payload["citations"] == []
    assert not registry.has("ev", "BEATMATCH_GRADED", 92.4, tol=1.0)
    assert progress.lessons["L2.01"]["completed"] is False
    assert not any(kind == "learn_lesson_completed" for kind, _fields in events)


def test_locked_beatmatch_practice_ack_advances_after_cited_grade() -> None:
    """The same beatmatch ack path completes only once the grade is locked."""
    progress = LearnProgress()
    registry = EvidenceRegistry()

    def record_action(_lesson_id: str | None, _midi: dict) -> bool:
        return True

    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 93.1,
        beatmatch_practice_loader=_locked_beatmatch_snapshot,
        beatmatch_practice_action_recorder=record_action,
    )
    runtime.send(
        "load",
        lesson_id="L2.01",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    handled = runtime.handle_beatmatch_practice_ack(
        {
            "type": "cc",
            "control": "tempo",
            "deck": "B",
            "direction": "down",
            "value": 64,
            "prev_value": 20,
            "source": "click",
        }
    )

    assert handled is True
    assert runtime.current_state.id in {"advancing", "completed"}
    live_grade = _live_grade_payloads(runtime._ipc)[-1]
    assert live_grade["verdict"] == "locked"
    assert live_grade["citation"] == "[ev:BEATMATCH_GRADED@93.100]"
    assert registry.has("ev", "BEATMATCH_GRADED", 93.1, tol=1.0)


def test_beatmatch_practice_rearms_after_unlocked_grade(monkeypatch) -> None:
    """A sustained lock credits once, then a drift grade re-arms the next lock."""
    monkeypatch.setattr("vibemix.learn.progress.save_progress", lambda _progress: None)
    progress = LearnProgress()
    _make_beatmatching_competent(progress)
    snapshots = [
        _locked_beatmatch_snapshot(),
        _locked_beatmatch_snapshot(),
        _drifting_beatmatch_snapshot(),
        _locked_beatmatch_snapshot(),
    ]
    registry = EvidenceRegistry()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 50.0 + len(snapshots),
        beatmatch_practice_loader=lambda: snapshots.pop(0) if snapshots else None,
    )

    first = runtime._grade_beatmatch_practice_tick()
    sustained = runtime._grade_beatmatch_practice_tick()
    drift = runtime._grade_beatmatch_practice_tick()
    relock = runtime._grade_beatmatch_practice_tick()

    assert first is not None and first.credited == ("beatmatching",)
    assert sustained is not None and sustained.credited == ()
    assert drift is not None and drift.grade.verdict == "trainwreck"
    assert relock is not None and relock.credited == ("beatmatching",)
    assert progress.skills["beatmatching"]["live_proof_count"] == 2


def test_cue_placement_practice_tick_writes_receipt_and_credits_once(monkeypatch) -> None:
    """The owned cue-placement hook writes cited phrasing evidence."""
    saved: list[LearnProgress] = []
    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    progress = LearnProgress()
    _make_phrasing_competent(progress)
    grid = _beat_grid()
    target = grid.beat_at(16)
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    events: list[tuple[str, dict]] = []
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 64.0,
        cue_placement_practice_loader=lambda: CuePlacementPracticeSnapshot(
            grid=grid,
            cue_frame=target,
            target_frame=target,
        ),
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    result = runtime._grade_cue_placement_practice_tick()

    assert result is not None
    assert result.event is not None
    assert result.grade.verdict == "drop_locked"
    assert result.credited == ("phrasing_performance",)
    assert registry.has("ev", "CUE_PLACEMENT_GRADED", 64.0, tol=1.0)
    assert progress.skills["phrasing_performance"]["live_proof_count"] == 1
    assert progress.skills.get("beatmatching", {}).get("live_proof_count", 0) == 0
    assert saved == [progress]
    assert any(
        call.args[0].get("type") == "ipc.learn.progress_state"
        for call in ipc.emit.call_args_list
    )
    assert events[-1][0] == "learn_cue_placement_practice_graded"
    assert events[-1][1]["credited"] == ["phrasing_performance"]

    repeated = runtime._grade_cue_placement_practice_tick()

    assert repeated is not None
    assert repeated.event is None
    assert repeated.credited == ()
    assert progress.skills["phrasing_performance"]["live_proof_count"] == 1


def test_matched_cue_action_records_and_grades_immediately(monkeypatch) -> None:
    """A matched hot-cue lesson action can arm the cue-placement grader."""
    saved: list[LearnProgress] = []
    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    progress = LearnProgress()
    _make_phrasing_competent(progress)
    grid = _beat_grid()
    target = grid.beat_at(16)
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    events: list[tuple[str, dict]] = []
    recorded: list[tuple[str | None, dict]] = []
    armed = False

    def record_action(lesson_id: str | None, midi: dict) -> bool:
        nonlocal armed
        recorded.append((lesson_id, dict(midi)))
        armed = True
        return True

    def load_snapshot() -> CuePlacementPracticeSnapshot | None:
        if not armed:
            return None
        return CuePlacementPracticeSnapshot(grid=grid, cue_frame=target, target_frame=target)

    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 73.5,
        cue_placement_practice_loader=load_snapshot,
        cue_placement_practice_action_recorder=record_action,
        playhead_payload_loader=lambda: {
            "sample_rate": _SR,
            "decks": {
                "A": {"frame": 0.0, "position_s": 0.0, "bpm": 128.0},
                "B": {
                    "frame": target,
                    "position_s": target / _SR,
                    "bpm": 128.0,
                },
            },
        },
        session_event_logger=lambda kind, fields: events.append((kind, dict(fields))),
    )

    midi = {
        "type": "button",
        "control": "hotcue",
        "deck": "B",
        "direction": "down",
        "source": "midi",
    }
    runtime.send(
        "load",
        lesson_id="L2.10",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    assert not any(
        call.args[0].get("type") == "ipc.learn.tutor_speak"
        and call.args[0].get("payload", {}).get("tts_marker") == "L2.10.cue_grade"
        for call in ipc.emit.call_args_list
    )
    runtime.send("ack_action", midi=midi)

    assert len(recorded) == 1
    lesson_id, recorded_midi = recorded[0]
    assert lesson_id == "L2.10"
    for key, value in midi.items():
        assert recorded_midi[key] == value
    assert recorded_midi["cue_frame"] == target
    assert "action_elapsed_s" not in recorded_midi
    assert registry.has("ev", "CUE_PLACEMENT_GRADED", 73.5, tol=1.0)
    assert not registry.has("ev", CONTROL_PRACTICE_GRADED_EVENT, 73.5, tol=1.0)
    assert progress.skills["phrasing_performance"]["live_proof_count"] == 1
    assert progress in saved
    assert any(kind == "learn_cue_placement_practice_graded" for kind, _fields in events)
    cue_grade_speaks = [
        call.args[0]
        for call in ipc.emit.call_args_list
        if call.args[0].get("type") == "ipc.learn.tutor_speak"
        and call.args[0].get("payload", {}).get("tts_marker") == "L2.10.cue_grade"
    ]
    assert len(cue_grade_speaks) == 1
    cue_grade_payload = cue_grade_speaks[0]["payload"]
    assert cue_grade_payload["text"] == "hot cue landed on the drop."
    assert cue_grade_payload["citations"] == ["[ev:CUE_PLACEMENT_GRADED@73.500]"]


def test_cue_placement_practice_uses_deck_playhead_not_lesson_elapsed(monkeypatch) -> None:
    """A delayed hot-cue press grades from deck B's playhead frame, not wall time."""
    monkeypatch.setattr("vibemix.learn.progress.save_progress", lambda _progress: None)
    progress = LearnProgress()
    _make_phrasing_competent(progress)
    driver = CuePlacementPracticeDriver()
    grid = _beat_grid()
    target = grid.beat_at(16)
    registry = EvidenceRegistry()
    ipc = MagicMock(name="ipc_router")
    recorded: list[dict] = []

    def record_action(lesson_id: str | None, midi: dict) -> bool:
        recorded.append(dict(midi))
        return driver.record_action(lesson_id, midi)

    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 81.25,
        cue_placement_practice_loader=driver.snapshot,
        cue_placement_practice_action_recorder=record_action,
        playhead_payload_loader=lambda: {
            "sample_rate": _SR,
            "decks": {
                "A": {"frame": 0.0, "position_s": 0.0, "bpm": 128.0},
                "B": {
                    "frame": target,
                    "position_s": target / _SR,
                    "bpm": 128.0,
                },
            },
        },
    )

    runtime.send(
        "load",
        lesson_id="L2.10",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime._learn.lesson_started_at -= 999.0
    runtime.send(
        "ack_action",
        midi={
            "type": "button",
            "control": "hotcue",
            "deck": "B",
            "direction": "down",
            "source": "midi",
        },
    )

    assert len(recorded) == 1
    assert recorded[0]["cue_frame"] == target
    assert "action_elapsed_s" not in recorded[0]
    assert registry.has("ev", "CUE_PLACEMENT_GRADED", 81.25, tol=1.0)
    assert any(
        call.args[0].get("type") == "ipc.learn.tutor_speak"
        and call.args[0].get("payload", {}).get("citations")
        == ["[ev:CUE_PLACEMENT_GRADED@81.250]"]
        for call in ipc.emit.call_args_list
    )


def test_cue_placement_practice_rearms_after_wrong_drop(monkeypatch) -> None:
    """A sustained cue lock credits once, then a wrong drop re-arms the next lock."""
    monkeypatch.setattr("vibemix.learn.progress.save_progress", lambda _progress: None)
    progress = LearnProgress()
    _make_phrasing_competent(progress)
    grid = _beat_grid()
    target = grid.beat_at(16)
    snapshots = [
        CuePlacementPracticeSnapshot(grid=grid, cue_frame=target, target_frame=target),
        CuePlacementPracticeSnapshot(grid=grid, cue_frame=target, target_frame=target),
        CuePlacementPracticeSnapshot(grid=grid, cue_frame=grid.beat_at(17), target_frame=target),
        CuePlacementPracticeSnapshot(grid=grid, cue_frame=target, target_frame=target),
    ]
    registry = EvidenceRegistry()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=MagicMock(name="ipc_router"),
        progress_store=progress,
        evidence_registry=registry,
        evidence_clock=lambda: 72.0 + len(snapshots),
        cue_placement_practice_loader=lambda: snapshots.pop(0) if snapshots else None,
    )

    first = runtime._grade_cue_placement_practice_tick()
    sustained = runtime._grade_cue_placement_practice_tick()
    wrong_drop = runtime._grade_cue_placement_practice_tick()
    relock = runtime._grade_cue_placement_practice_tick()

    assert first is not None and first.credited == ("phrasing_performance",)
    assert sustained is not None and sustained.credited == ()
    assert wrong_drop is not None and wrong_drop.grade.verdict == "wrong_drop"
    assert relock is not None and relock.credited == ("phrasing_performance",)
    assert progress.skills["phrasing_performance"]["live_proof_count"] == 2
