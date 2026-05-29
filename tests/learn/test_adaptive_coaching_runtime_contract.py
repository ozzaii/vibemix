# SPDX-License-Identifier: Apache-2.0
"""Focused release contract for grounded adaptive Learn coaching."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.coach.citation_linter import CitationLinter
from vibemix.learn.ipc_handlers import register_learn_handlers
from vibemix.learn.progress import LearnProgress, load_progress
from vibemix.learn.runtime import LessonRuntime
from vibemix.learn.state import LearnState
from vibemix.runtime.ws_bus import IpcRouterBus
from vibemix.state.evidence_registry import EvidenceRegistry


def _runtime(
    *,
    evidence_registry: EvidenceRegistry | None = None,
    evidence_clock_value: float | None = None,
) -> tuple[LessonRuntime, MagicMock, LearnProgress]:
    ipc = MagicMock(name="ipc_router")
    progress = LearnProgress()
    runtime = LessonRuntime(
        learn_state=LearnState(),
        midi_mirror=MagicMock(name="midi_mirror"),
        controller_state=MagicMock(name="controller_state"),
        ipc_router=ipc,
        progress_store=progress,
        evidence_registry=evidence_registry,
        evidence_clock=(lambda: evidence_clock_value)
        if evidence_clock_value is not None
        else None,
    )
    return runtime, ipc, progress


def _hint_payloads(ipc: MagicMock) -> list[dict]:
    return [
        call.args[0]["payload"]
        for call in ipc.emit.call_args_list
        if call.args
        and call.args[0].get("type") == "ipc.learn.tutor_speak"
        and call.args[0].get("payload", {}).get("data_state") == "hint"
    ]


def test_timed_hint_is_loop_grounded_and_persists_strike_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A timed nudge is quiet frontstage copy plus durable backstage state."""
    target = tmp_path / "learn-progress.json"
    monkeypatch.setattr("vibemix.learn.progress.progress_path", lambda: target)
    runtime, ipc, progress = _runtime()

    runtime.send(
        "load",
        lesson_id="L1.03",
        course_id="course_1_anatomy",
        controller_id="pioneer_ddj_flx4",
    )
    runtime.send("begin")
    runtime.send("strike")

    assert runtime.current_state.id == "hint_strike_1"
    assert progress.lessons["L1.03"]["strikes_used"] == 1
    reloaded, was_corrupt = load_progress()
    assert was_corrupt is False
    assert reloaded.lessons["L1.03"]["strikes_used"] == 1

    hint = _hint_payloads(ipc)[-1]
    loop = hint["teaching_loop"]
    assert loop["turn_kind"] == "hint"
    assert loop["route_path"] == "learn_tutor"
    assert loop["observation"]["strikes_used"] == 1
    assert loop["verification"]["observable_control_ids"] == ["eq_hi:A"]
    assert hint["citations"] == ["[screen:eq_hi:A]"]


def test_wrong_screen_action_adapts_without_advancing_through_ipc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The same IPC path as the UI gets a specific correction, not silence."""
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: tmp_path / "learn-progress.json",
    )
    runtime, ipc, progress = _runtime()
    router = IpcRouterBus()
    midi_mirror = MagicMock(name="midi_mirror_inbound")
    midi_mirror.current_profile.return_value = None
    register_learn_handlers(
        ipc_router=router,
        lesson_runtime=runtime,
        midi_mirror=midi_mirror,
        progress=progress,
    )

    async def start_and_miss() -> tuple[bool, bool]:
        started = await router.dispatch(
            {
                "type": "ipc.learn.start_lesson",
                "payload": {"lesson_id": "L1.03", "level": "fresh"},
            }
        )
        missed = await router.dispatch(
            {
                "type": "ipc.learn.ack",
                "payload": {
                    "control_id": "eq_mid:A",
                    "source": "click",
                    "value": 127,
                    "prev_value": 0,
                    "direction": "down",
                },
            }
        )
        return started, missed

    assert asyncio.run(start_and_miss()) == (True, True)
    assert runtime.current_state.id == "awaiting_action"

    hint = _hint_payloads(ipc)[-1]
    loop = hint["teaching_loop"]
    assert hint["text"] == "that was deck A mid EQ. use deck A high EQ."
    assert hint["citations"] == ["[screen:eq_mid:A]", "[screen:eq_hi:A]"]
    assert loop["turn_kind"] == "adapt"
    assert loop["verification"]["kind"] == "cc_delta"
    assert loop["verification"]["observable_control_ids"] == ["eq_hi:A"]


def test_small_midi_move_uses_registry_citation_and_shared_verification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A weak but correct control move cites the observed MIDI evidence."""
    monkeypatch.setattr(
        "vibemix.learn.progress.progress_path",
        lambda: tmp_path / "learn-progress.json",
    )
    registry = EvidenceRegistry()
    runtime, ipc, _progress = _runtime(
        evidence_registry=registry,
        evidence_clock_value=12.7,
    )
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
    assert runtime.current_state.id == "awaiting_action"
    hint = _hint_payloads(ipc)[-1]
    loop = hint["teaching_loop"]
    assert hint["text"] == "move deck A high EQ farther."
    assert hint["citations"] == ["[midi:eq_hi:A@12.7]", "[screen:eq_hi:A]"]
    assert loop["turn_kind"] == "adapt"
    assert loop["verification"]["control"] == "eq_hi"
    assert loop["verification"]["deck"] == "A"
    assert loop["verification"]["min_delta"] > 0

    snapshot = registry.snapshot()
    assert 12.7 in snapshot["midi"]["eq_hi:A"]
    assert 12.7 in snapshot["screen"]["eq_hi:A"]
    assert CitationLinter().check(
        " ".join(hint["citations"]),
        snapshot,
        mode="live",
    ).valid is True
