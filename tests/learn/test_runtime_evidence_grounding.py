# SPDX-License-Identifier: Apache-2.0
"""Learn runtime evidence grounding regression tests."""
from __future__ import annotations

from unittest.mock import MagicMock

from vibemix.audio.grid import BeatGrid
from vibemix.audio.miniplayer import DeckState
from vibemix.coach.citation_linter import CitationLinter
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import BeatmatchPracticeSnapshot, LessonRuntime
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


def _make_beatmatching_competent(progress: LearnProgress) -> None:
    spec = SKILL_MANIFEST["beatmatching"]
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
            "control": "eq_hi",
            "deck": "A",
            "value": 45,
            "prev_value": 20,
            "source": "midi",
            "direction": "down",
        }
    )

    assert handled is True
    hints = _hint_payloads(ipc)
    assert hints[-1]["citations"] == ["[midi:eq_hi:A@12.7]", "[screen:eq_hi:A]"]

    snapshot = registry.snapshot()
    assert 12.7 in snapshot["midi"]["eq_hi:A"]
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
