# SPDX-License-Identifier: Apache-2.0
"""Runtime wiring for L2.11's library-grounded harmonic prompt."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from vibemix.learn.harmonic_practice import (
    HarmonicPracticePair,
    HarmonicPracticeTrack,
)
from vibemix.learn.progress import LearnProgress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.library.track_relation import compute_relation
from vibemix.state.evidence_registry import EvidenceRegistry


def _runtime(*, pair: HarmonicPracticePair | None, registry: EvidenceRegistry | None):
    ipc = MagicMock(name="ipc_router")
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=LearnProgress(),
        evidence_registry=registry,
        harmonic_pair_loader=lambda: pair,
    )
    return runtime, ipc


def _tutor_payloads(ipc: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args and call.args[0].get("type") == "ipc.learn.tutor_speak"
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
