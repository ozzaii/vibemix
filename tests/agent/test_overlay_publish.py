# SPDX-License-Identifier: Apache-2.0
"""Phase 24-02 Task 5 — DJCoHostAgent overlay-highlight publish path.

When ``ipc_bus`` is wired AND the citation action is ``emit`` (user heard
the response), every ``[screen:<element_id>]`` atom in the response
publishes one ``ipc.session.overlay-highlight`` envelope. ``strip`` /
``bypass`` (the linter chokepoint dispositions) are stress-tested
separately:

  * **emit** (clean response) → ring fires.
  * **strip** (invalid citation) → ring does NOT fire (user heard nothing).
  * **bypass** (one-shot guard let it through) → ring fires (user heard text).
  * **no [screen:*] citation** → ring does NOT fire.
  * **ipc_bus=None** → no errors, no emits.

Determinism is preserved by mocking ``ipc_bus`` as an AsyncMock — no live
WebSocket, no live AX, no live Tauri invoke.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import numpy as np
from livekit.agents import Agent

from vibemix.agent import DJCoHostAgent
from vibemix.coach import CitationLinter, StrippedRateTracker
from vibemix.state import AICoach, Event, EvidenceRegistry, MusicState

# --------------------------------------------------------------------------
# Helpers (mirror tests/agent/test_dj_cohost_linter.py)
# --------------------------------------------------------------------------


def _async_iter(chunks: list[str]):
    async def gen():
        for c in chunks:
            yield type("Chunk", (), {"text": c})()

    return gen()


class _FakeRecorder:
    def __init__(self, session_dir: Path) -> None:
        self.session_dir = session_dir
        self.events: list[tuple[str, dict]] = []

    def log_event(self, kind: str, **fields: Any) -> None:
        self.events.append((kind, fields))

    def push_voice(self, pcm: bytes) -> None:
        pass


class _FakeIpcBus:
    """Records every ``emit`` call. Async to match runtime/ws_bus.IpcBus.emit."""

    def __init__(self) -> None:
        self.emits: list[dict] = []

    async def emit(self, msg: dict) -> None:
        self.emits.append(msg)


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


def _build_agent(
    mocker,
    tmp_path: Path,
    *,
    registry: EvidenceRegistry | None = None,
    wired: bool = False,
    ipc_bus: _FakeIpcBus | None = None,
):
    """Build the agent. wired=True enables the citation linter chokepoint
    (Plan 20-01); ipc_bus, if non-None, enables the overlay publish path."""
    mocker.patch.object(Agent, "__init__", return_value=None)
    state = _build_state()
    recorder = _FakeRecorder(tmp_path)
    genai_client = mocker.MagicMock()

    kwargs: dict[str, Any] = {
        "genai_client": genai_client,
        "clean_audio_buf": mocker.MagicMock(),
        "screen_buf": mocker.MagicMock(),
        "state": state,
        "recorder": recorder,
        "llm_inst": mocker.MagicMock(),
        "tts_inst": mocker.MagicMock(),
    }
    if registry is not None:
        kwargs["evidence_registry"] = registry
    if wired:
        kwargs["citation_linter"] = CitationLinter()
        kwargs["stripped_rate_tracker"] = StrippedRateTracker()
        kwargs["ack_bank"] = mocker.MagicMock()
        fake_pcm = np.zeros(1024, dtype=np.int16)
        kwargs["ack_bank"].pick_for_event.return_value = (
            "generic_filler",
            fake_pcm,
            3,
        )
        kwargs["playback"] = mocker.MagicMock()
    if ipc_bus is not None:
        kwargs["ipc_bus"] = ipc_bus

    agent = DJCoHostAgent(**kwargs)
    return agent, genai_client, recorder, state


def _drive(agent: DJCoHostAgent) -> list[str]:
    async def _go() -> list[str]:
        out: list[str] = []
        async for txt in agent.llm_node(chat_ctx=None, tools=[], model_settings=None):
            out.append(txt)
        return out

    return asyncio.run(_go())


# --------------------------------------------------------------------------
# (a) Legacy emit + ipc_bus wired → ring publishes
# --------------------------------------------------------------------------


def test_legacy_emit_publishes_overlay_for_screen_citation(mocker, tmp_path) -> None:
    """Legacy (no linter) path with ipc_bus wired: a `[screen:waveform_a]`
    in the response publishes one overlay envelope. Legacy path treats
    every emitted response as citation_action=emit (the user heard it)."""
    bus = _FakeIpcBus()
    agent, gen, _, state = _build_agent(mocker, tmp_path, ipc_bus=bus)
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["nice [screen:waveform_a] arrangement"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)

    assert len(bus.emits) == 1
    payload = bus.emits[0]["payload"]
    assert bus.emits[0]["type"] == "ipc.session.overlay-highlight"
    assert payload["element_id"] == "waveform_a"
    assert payload["color"] == "amber"
    assert payload["duration_ms"] == 1300


# --------------------------------------------------------------------------
# (b) Wired emit (linter valid) → ring publishes
# --------------------------------------------------------------------------


def test_wired_valid_publishes_overlay(mocker, tmp_path) -> None:
    """Wired path + valid screen citation in registry → ring fires."""
    registry = EvidenceRegistry()
    registry.write("screen", "deck_a_low_eq", 12.0)
    bus = _FakeIpcBus()
    agent, gen, _, state = _build_agent(
        mocker, tmp_path, registry=registry, wired=True, ipc_bus=bus
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["nice [screen:deck_a_low_eq] move"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)

    assert len(bus.emits) == 1
    assert bus.emits[0]["payload"]["element_id"] == "deck_a_low_eq"


# --------------------------------------------------------------------------
# (c) Wired strip (invalid citation) → no ring
# --------------------------------------------------------------------------


def test_wired_strip_does_not_publish_overlay(mocker, tmp_path) -> None:
    """Wired path + invalid [ev:*] citation → linter strips → text was
    NOT emitted → overlay must NOT fire (user heard the ack, not the
    citation; ring would be ghost-firing)."""
    registry = EvidenceRegistry()  # empty — citation will not match
    bus = _FakeIpcBus()
    agent, gen, _, state = _build_agent(
        mocker, tmp_path, registry=registry, wired=True, ipc_bus=bus
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            ["unverified [ev:GHOST@99.0] and [screen:waveform_a] reply"]
        )
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)

    assert len(bus.emits) == 0


# --------------------------------------------------------------------------
# (d) No [screen:*] citation → no ring
# --------------------------------------------------------------------------


def test_no_screen_citation_no_publish(mocker, tmp_path) -> None:
    """Response with only [ev:*] / [aud:*] citations (no screen) → no overlay."""
    registry = EvidenceRegistry()
    registry.write("ev", "KICK_SWAP", 45.2)
    bus = _FakeIpcBus()
    agent, gen, _, state = _build_agent(
        mocker, tmp_path, registry=registry, wired=True, ipc_bus=bus
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["clean [ev:KICK_SWAP@45.2] drop"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)

    assert len(bus.emits) == 0


# --------------------------------------------------------------------------
# (e) ipc_bus=None → no errors, no emits, no spam
# --------------------------------------------------------------------------


def test_ipc_bus_none_is_silent(mocker, tmp_path) -> None:
    """Default construction (no ipc_bus kwarg) — backward compatible silence."""
    agent, gen, recorder, state = _build_agent(mocker, tmp_path)  # ipc_bus=None
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["nice [screen:waveform_a] reply"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    # Must complete without error — backward compat.
    chunks = _drive(agent)
    assert chunks == ["nice [screen:waveform_a] reply"]


# --------------------------------------------------------------------------
# (f) Multi-citation: one [screen:*] in a multi-atom citation → ring fires
# --------------------------------------------------------------------------


def test_multi_atom_citation_publishes_each_screen(mocker, tmp_path) -> None:
    """[ev:KICK_SWAP@45.2,screen:waveform_a] → 1 overlay (screen atom only)."""
    registry = EvidenceRegistry()
    registry.write("ev", "KICK_SWAP", 45.2)
    registry.write("screen", "waveform_a", 45.2)
    bus = _FakeIpcBus()
    agent, gen, _, state = _build_agent(
        mocker, tmp_path, registry=registry, wired=True, ipc_bus=bus
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            ["that [ev:KICK_SWAP@45.2,screen:waveform_a] drop was clean"]
        )
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)

    assert len(bus.emits) == 1
    assert bus.emits[0]["payload"]["element_id"] == "waveform_a"


# --------------------------------------------------------------------------
# (g) Two [screen:*] citations in same response → 2 emits, both deduped by
#     element_id at the Tauri side (this test only confirms the publish
#     path emits per-atom; renderer-side dedup is Plan 24-03 work).
# --------------------------------------------------------------------------


def test_two_screen_citations_publish_both(mocker, tmp_path) -> None:
    registry = EvidenceRegistry()
    registry.write("screen", "deck_a_low_eq", 12.0)
    registry.write("screen", "deck_b_mid_eq", 12.0)
    bus = _FakeIpcBus()
    agent, gen, _, state = _build_agent(
        mocker, tmp_path, registry=registry, wired=True, ipc_bus=bus
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(
            [
                "low [screen:deck_a_low_eq] then mid [screen:deck_b_mid_eq] sweep",
            ]
        )
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    _drive(agent)

    assert len(bus.emits) == 2
    element_ids = {e["payload"]["element_id"] for e in bus.emits}
    assert element_ids == {"deck_a_low_eq", "deck_b_mid_eq"}


# --------------------------------------------------------------------------
# (h) Bus emit failure does NOT crash the LLM response path
# --------------------------------------------------------------------------


def test_bus_emit_failure_is_swallowed(mocker, tmp_path) -> None:
    """Best-effort guarantee: an exception inside ipc_bus.emit must NOT
    propagate up and break the agent's response stream."""
    registry = EvidenceRegistry()
    registry.write("screen", "waveform_a", 12.0)

    class _BrokenBus:
        async def emit(self, msg: dict) -> None:
            raise RuntimeError("ws closed")

    bus = _BrokenBus()
    agent, gen, _, state = _build_agent(
        mocker, tmp_path, registry=registry, wired=True, ipc_bus=bus
    )
    mocker.patch("vibemix.agent.dj_cohost.snapshot_wav", return_value=b"FAKEWAV")
    mocker.patch.object(AICoach, "build_prompt", return_value="EVIDENCE: x")
    gen.aio.models.generate_content_stream = mocker.AsyncMock(
        return_value=_async_iter(["that [screen:waveform_a] move"])
    )

    ev = Event(type="HEARTBEAT", state=state, extra={})
    agent.set_next_event(ev)
    # The drive call must complete without raising despite the bus exception.
    chunks = _drive(agent)
    assert chunks == ["that [screen:waveform_a] move"]
