# SPDX-License-Identifier: Apache-2.0
"""Runtime wiring for L2.11's library-grounded harmonic prompt."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from vibemix.learn.harmonic_practice import (
    HARMONIC_PRACTICE_GRADED_EVENT,
    HarmonicPracticePair,
    HarmonicPracticeTrack,
)
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.skill_tree import SKILL_MANIFEST
from vibemix.learn.state import LearnState
from vibemix.library.track_relation import compute_relation
from vibemix.state.evidence_registry import EvidenceRegistry


def _runtime(
    *,
    pair: HarmonicPracticePair | None,
    registry: EvidenceRegistry | None,
    progress: LearnProgress | None = None,
    clock_value: float = 0.0,
    events: list[tuple[str, dict]] | None = None,
):
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress or LearnProgress(),
        evidence_registry=registry,
        evidence_clock=lambda: clock_value,
        harmonic_pair_loader=lambda: pair,
        session_event_logger=(
            (lambda kind, fields: events.append((kind, dict(fields))))
            if events is not None
            else None
        ),
    )
    return runtime, ipc


def _tutor_payloads(ipc: MagicMock) -> list[dict]:
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


def test_l211_emits_library_grounded_harmonic_pair_prompt() -> None:
    pair = _pair()
    registry = EvidenceRegistry()
    registry.register_library(SimpleNamespace(tracks={"t1": None, "t2": None}))
    runtime, ipc = _runtime(pair=pair, registry=registry)

    runtime.send(
        "load",
        lesson_id="L2.11",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    payloads = _tutor_payloads(ipc)
    assert payloads[0]["text"] == (
        "the camelot wheel is a clock face with twenty-four labels. "
        "every track has one: for example, 8a or 12b."
    )
    assert payloads[1]["tts_marker"] == "L211.library_pair"
    assert payloads[1]["text"].startswith("your library pair:")
    assert "Artist - Source" in payloads[1]["text"]
    assert "Artist - Target" in payloads[1]["text"]
    assert payloads[1]["citations"] == ["[track:t1]", "[track:t2]"]


def test_l211_stays_fixture_only_when_no_library_pair() -> None:
    runtime, ipc = _runtime(pair=None, registry=None)

    runtime.send(
        "load",
        lesson_id="L2.11",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")

    payloads = _tutor_payloads(ipc)
    assert [payload["tts_marker"] for payload in payloads] == ["L211.beat0"]


def test_l211_final_continue_writes_cited_harmonic_practice_receipt(monkeypatch) -> None:
    saved: list[LearnProgress] = []
    monkeypatch.setattr("vibemix.learn.progress.save_progress", saved.append)
    pair = _pair()
    progress = LearnProgress()
    _make_competent(progress, "harmonic_mixing")
    registry = EvidenceRegistry()
    registry.register_library(SimpleNamespace(tracks={"t1": None, "t2": None}))
    events: list[tuple[str, dict]] = []
    runtime, ipc = _runtime(
        pair=pair,
        registry=registry,
        progress=progress,
        clock_value=91.25,
        events=events,
    )
    midi = {
        "type": "button",
        "control": "lesson_continue",
        "direction": "down",
        "source": "click",
    }

    runtime.send(
        "load",
        lesson_id="L2.11",
        course_id="course_2_transitions",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    assert runtime.handle_step_ack(midi) is True
    assert not registry.has("ev", HARMONIC_PRACTICE_GRADED_EVENT, 91.25, tol=1.0)
    assert runtime.handle_step_ack(midi) is True
    assert not registry.has("ev", HARMONIC_PRACTICE_GRADED_EVENT, 91.25, tol=1.0)

    runtime.send("ack_action", midi=midi)

    assert registry.has("ev", HARMONIC_PRACTICE_GRADED_EVENT, 91.25, tol=1.0)
    assert progress.skills["harmonic_mixing"]["live_proof_count"] == 1
    assert progress in saved
    assert any(
        call.args[0].get("type") == "ipc.learn.progress_state"
        and call.args[0].get("payload", {}).get("progress", {}).get("skills", {})
        .get("harmonic_mixing", {})
        .get("live_proof_count")
        == 1
        for call in ipc.emit.call_args_list
    )
    event = next(
        fields for kind, fields in events if kind == "learn_harmonic_practice_graded"
    )
    assert event["lesson_id"] == "L2.11"
    assert event["step_id"] == "L2.11.beat.2"
    assert event["source_track_id"] == "t1"
    assert event["target_track_id"] == "t2"
    assert event["credited"] == ["harmonic_mixing"]
    harmonic_grade_payloads = [
        payload
        for payload in _tutor_payloads(ipc)
        if payload["tts_marker"] == "L2.11.harmonic_grade"
    ]
    assert harmonic_grade_payloads == [
        {
            "text": f"compatible pair banked: 8A into 9A. {pair.why}.",
            "tts_marker": "L2.11.harmonic_grade",
            "citations": [
                "[ev:HARMONIC_PRACTICE_GRADED@91.250]",
                "[track:t1]",
                "[track:t2]",
            ],
            "data_state": "hint",
        }
    ]
    live_grades = _live_grade_payloads(ipc)
    assert live_grades[-1]["verdict"] == "locked"
    assert live_grades[-1]["phase_error_beats"] == 0.0
    assert live_grades[-1]["score"] == 1.0
    assert live_grades[-1]["citation"] == "[ev:HARMONIC_PRACTICE_GRADED@91.250]"


def _pair() -> HarmonicPracticePair:
    source = HarmonicPracticeTrack(
        track_id="t1",
        title="Source",
        artist="Artist",
        bpm=128.0,
        camelot="8A",
    )
    target = HarmonicPracticeTrack(
        track_id="t2",
        title="Target",
        artist="Artist",
        bpm=130.0,
        camelot="9A",
    )
    relation = compute_relation(
        src_track_id="t1",
        dst_track_id="t2",
        cosine=0.0,
        src_camelot="8A",
        dst_camelot="9A",
        src_bpm=128.0,
        dst_bpm=130.0,
    )
    return HarmonicPracticePair(source=source, target=target, relation=relation, score=1.0)


def _make_competent(progress: LearnProgress, skill_id: str) -> None:
    spec = SKILL_MANIFEST[skill_id]
    for lesson_id in spec.lesson_ids:
        progress.lessons[lesson_id] = {
            "completed": True,
            "completed_at": "2026-06-04T00:00:00Z",
            "strikes_used": 0,
        }
    setattr(progress, spec.gate, True)
