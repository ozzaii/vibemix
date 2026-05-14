# SPDX-License-Identifier: Apache-2.0
"""Plan 19-02 Task 2 — DJCoHostAgent.llm_node diet wiring.

Pins:
- Audio Part window: 6.0s on ack-eligible events, 18.0s (INVOKE_AUDIO_SECONDS)
  on full events.
- Screen Part: SKIPPED on MIX_MOVE + HEARTBEAT (SCREEN_SKIP_EVENTS).
- AICoach.build_prompt called with diet=True on ack events, diet=False on full.
- recorder.log_event llm_invoke payload exposes diet bool + audio_seconds int
  for Phase 16 ear-test telemetry.
- Pending None falls back to MANUAL (full window, diet=False).

Reuses the test_dj_cohost.py fixture pattern (mocker, tmp_path,
_FakeRecorder) — see tests/agent/test_dj_cohost.py for the shared shape.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.agent.dj_cohost import SCREEN_SKIP_EVENTS
from vibemix.audio import INVOKE_AUDIO_SECONDS
from vibemix.state import AICoach, Event, MusicState
from vibemix.state.coach import ACK_ELIGIBLE_EVENTS

# 6s window from Plan 19-02 — diet path payload.
DIET_AUDIO_SECONDS = 6.0


# ---------- helpers (mirrored from tests/agent/test_dj_cohost.py) ----------


def _async_iter(chunks):
    async def gen():
        for c in chunks:
            yield type("Chunk", (), {"text": c})()

    return gen()


class _FakeRecorder:
    def __init__(self, session_dir: Path):
        self.session_dir = session_dir
        self.events: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
        self.events.append((kind, fields))

    def push_voice(self, pcm: bytes) -> None:
        pass


def _build_state() -> MusicState:
    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    s.audible_track = "Daft Punk - Around the World"
    s.audible_track_confidence = 0.8
    s.phase = "peak"
    s.rms = 0.05
    s.bpm = 128.0
    return s


def _build_agent(mocker, tmp_path: Path) -> tuple[DJCoHostAgent, Any, _FakeRecorder, MusicState]:
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()
    screen_buf = mocker.MagicMock()
    agent = DJCoHostAgent(
        genai_client=genai_client,
        clean_audio_buf=mocker.MagicMock(),
        screen_buf=screen_buf,
        state=state,
        recorder=recorder,
        llm_inst=mocker.MagicMock(),
        tts_inst=mocker.MagicMock(),
    )
    return agent, genai_client, recorder, state


def _drive_llm_node(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        chunks: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            chunks.append(txt)
        return chunks

    return asyncio.run(_go())


def _drive_with_event(
    mocker, tmp_path: Path, ev_type: str | None
) -> tuple[Any, _FakeRecorder, DJCoHostAgent]:
    """Build agent, set pending event of ev_type (or None), drive llm_node,
    return (snapshot_wav_mock, recorder, agent) so tests can assert on the
    snapshot_wav call args + recorder log_event payload."""
    agent, gen_client, recorder, state = _build_agent(mocker, tmp_path)
    snapshot_wav_mock = mocker.patch(
        "vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV"
    )
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen_client.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["ok"])
    )
    if ev_type is not None:
        ev = Event(type=ev_type, state=state, extra={})
        agent.set_next_event(ev)
    _drive_llm_node(agent)
    return snapshot_wav_mock, recorder, agent


# ---------- audio window pinning ----------


def test_phase_event_uses_full_18s_window_no_diet(mocker, tmp_path):
    snapshot_wav_mock, _, _ = _drive_with_event(mocker, tmp_path, "PHASE")
    assert snapshot_wav_mock.call_args.args[1] == INVOKE_AUDIO_SECONDS
    AICoach.build_prompt.assert_called_once()
    assert AICoach.build_prompt.call_args.kwargs.get("diet") is False


def test_track_change_uses_full_18s_window_no_diet(mocker, tmp_path):
    snapshot_wav_mock, _, _ = _drive_with_event(mocker, tmp_path, "TRACK_CHANGE")
    assert snapshot_wav_mock.call_args.args[1] == INVOKE_AUDIO_SECONDS
    assert AICoach.build_prompt.call_args.kwargs.get("diet") is False


def test_manual_uses_full_18s_window_no_diet(mocker, tmp_path):
    snapshot_wav_mock, _, _ = _drive_with_event(mocker, tmp_path, "MANUAL")
    assert snapshot_wav_mock.call_args.args[1] == INVOKE_AUDIO_SECONDS
    assert AICoach.build_prompt.call_args.kwargs.get("diet") is False


def test_heartbeat_uses_6s_window_diet(mocker, tmp_path):
    snapshot_wav_mock, _, _ = _drive_with_event(mocker, tmp_path, "HEARTBEAT")
    assert snapshot_wav_mock.call_args.args[1] == DIET_AUDIO_SECONDS
    assert AICoach.build_prompt.call_args.kwargs.get("diet") is True


def test_mix_move_uses_6s_window_diet(mocker, tmp_path):
    snapshot_wav_mock, _, _ = _drive_with_event(mocker, tmp_path, "MIX_MOVE")
    assert snapshot_wav_mock.call_args.args[1] == DIET_AUDIO_SECONDS
    assert AICoach.build_prompt.call_args.kwargs.get("diet") is True


def test_layer_arrival_uses_6s_window_diet(mocker, tmp_path):
    snapshot_wav_mock, _, _ = _drive_with_event(mocker, tmp_path, "LAYER_ARRIVAL")
    assert snapshot_wav_mock.call_args.args[1] == DIET_AUDIO_SECONDS
    assert AICoach.build_prompt.call_args.kwargs.get("diet") is True


def test_kaan_spoke_uses_6s_window_diet(mocker, tmp_path):
    snapshot_wav_mock, _, _ = _drive_with_event(mocker, tmp_path, "KAAN_SPOKE")
    assert snapshot_wav_mock.call_args.args[1] == DIET_AUDIO_SECONDS
    assert AICoach.build_prompt.call_args.kwargs.get("diet") is True


def test_pending_none_falls_back_to_manual_full_window(mocker, tmp_path):
    """When _pending_event is None, the fallback path uses MANUAL — full
    18s window, diet=False."""
    snapshot_wav_mock, _, _ = _drive_with_event(mocker, tmp_path, ev_type=None)
    assert snapshot_wav_mock.call_args.args[1] == INVOKE_AUDIO_SECONDS
    AICoach.build_prompt.assert_called_once()
    assert AICoach.build_prompt.call_args.kwargs.get("diet") is False
    # Fallback Event was constructed with type=MANUAL.
    fallback_ev = AICoach.build_prompt.call_args.args[0]
    assert fallback_ev.type == "MANUAL"


# ---------- screen-skip set ----------


def test_screen_skip_set_contains_only_mix_move_and_heartbeat():
    """SCREEN_SKIP_EVENTS pins the two event classes that NEVER append a
    screen Part regardless of whether _screen_buf has a frame. CONTEXT D-08
    rule — pre-wires v2.x re-enable path."""
    assert SCREEN_SKIP_EVENTS == frozenset({"MIX_MOVE", "HEARTBEAT"})


def test_screen_skip_set_is_subset_of_ack_eligible_events():
    """Sanity — every screen-skip event is also ack-eligible (the diet
    path is a superset of the screen-skip path)."""
    assert SCREEN_SKIP_EVENTS.issubset(ACK_ELIGIBLE_EVENTS)


# ---------- recorder log_event payload ----------


def test_log_event_payload_contains_diet_and_audio_seconds(mocker, tmp_path):
    """llm_invoke payload exposes diet (bool) + audio_seconds (int) for
    Phase 16 ear-test telemetry — events.jsonl correlates Gemini reaction
    quality to the diet dispatch (T-19-02-04 mitigation)."""
    _, recorder, _ = _drive_with_event(mocker, tmp_path, "MIX_MOVE")
    invoke_events = [e for e in recorder.events if e[0] == "llm_invoke"]
    assert len(invoke_events) == 1
    fields = invoke_events[0][1]
    assert fields["diet"] is True
    assert fields["audio_seconds"] == 6
    assert isinstance(fields["audio_seconds"], int)


def test_log_event_payload_diet_false_on_phase(mocker, tmp_path):
    """Mirror — PHASE event logs diet=False + audio_seconds=18."""
    _, recorder, _ = _drive_with_event(mocker, tmp_path, "PHASE")
    invoke_events = [e for e in recorder.events if e[0] == "llm_invoke"]
    assert len(invoke_events) == 1
    fields = invoke_events[0][1]
    assert fields["diet"] is False
    assert fields["audio_seconds"] == 18
