# SPDX-License-Identifier: Apache-2.0
"""Phase 12 Wave 2 — SessionLoop handler dispatch + snapshot shape.

Covers (per plan must-haves):
  * 4 ipc.* handlers registered: ipc.session.mute, ipc.settings.set,
    ipc.settings.get, ipc.status.recheck.
  * ``ipc.session.mute toggle:true`` flips ``self.muted`` AND calls
    ``playback_queue.clear()`` when ref is provided; ack carries
    new ``muted`` state.
  * ``ipc.settings.get`` emits ``ipc.settings.state`` with current
    config_store snapshot.
  * ``ipc.settings.set`` dispatches via SettingsApplier; failure
    surfaces as ``ipc.error`` (not a crash).
  * ``ipc.status.recheck`` emits ``ipc.status.tick`` for known
    components; unknown component → ``ipc.error``.
  * 30Hz snapshot conforms to schema (validator-checked on emit).
  * Snapshot fallback when MusicState is None: zeroed meters + IDLE +
    grounded=false (schema-valid).
  * Invalid inbound payload via the validation wrapper → ipc.error.

Uses the FakeBus pattern from ``tests/wizard/conftest.py`` (the bus
records every emit + the handler-registration map) — same surface as
the real ``WizardBus`` so handler dispatch is exercised without a
real WS server.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from vibemix.runtime import config_store as cs_mod
from vibemix.runtime.config_store import ConfigStore
from vibemix.runtime.session_loop import (
    SNAPSHOT_INTERVAL,
    SessionLoop,
    run_session,
)
from vibemix.runtime.settings import SettingsApplier
from vibemix.ui_bus.validator import validate_message


# ---------------------------------------------------------------------------
# Local FakeBus — mirrors tests/wizard/conftest.py FakeBus but lives here
# so we don't cross-import test packages. Surface matches WizardBus.
# ---------------------------------------------------------------------------


class FakeBus:
    """In-memory stand-in for ``vibemix.runtime.ws_bus.WizardBus``."""

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}
        self.emitted: list[dict] = []
        self.started = False
        self.stopped = False

    def register_handler(
        self, message_type: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        self.handlers[message_type] = handler

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def emit(self, msg: dict) -> None:
        validate_message(msg)
        self.emitted.append(json.loads(json.dumps(msg)))

    def emitted_by_type(self, msg_type: str) -> list[dict]:
        return [m for m in self.emitted if m.get("type") == msg_type]


@pytest.fixture
def fake_bus() -> FakeBus:
    return FakeBus()


@pytest.fixture(autouse=True)
def _redirect_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``save_config()`` writes into ``tmp_path/config.json``."""
    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    return target


# ---------------------------------------------------------------------------
# Fakes for the injected runtime refs
# ---------------------------------------------------------------------------


class FakeMusicState:
    """Duck-typed MusicState — has only the fields SessionLoop reads."""

    def __init__(
        self,
        *,
        audible: bool = True,
        phase: str = "groove",
        bpm: float = 124.0,
        audible_track: str | None = "Foo - Bar",
        audible_deck: str = "A",
        recent_moves: list | None = None,
    ) -> None:
        self.audible = audible
        self.phase = phase
        self.bpm = bpm
        self.audible_track = audible_track
        self.audible_deck = audible_deck
        self.recent_moves = recent_moves or []


class FakeLevels:
    """Duck-typed Levels — only ``snapshot()`` is read."""

    def __init__(self, *, music=0.2, voice=0.0, mic=0.0) -> None:
        self.music = music
        self.voice = voice
        self.mic = mic

    def snapshot(self) -> dict[str, float]:
        return {"music": self.music, "voice": self.voice, "mic": self.mic}


class FakeControllerState:
    """Duck-typed ControllerState — only ``recent_moves`` is read."""

    def __init__(self, moves: list | None = None) -> None:
        self.recent_moves = moves or []


def _drive(bus: FakeBus, msg: dict) -> None:
    """Dispatch ``msg`` to the registered handler via asyncio.run."""
    handler = bus.handlers[msg["type"]]
    asyncio.run(handler(msg))


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


def test_register_handlers_covers_all_session_types(fake_bus: FakeBus) -> None:
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    expected = {
        "ipc.session.mute",
        "ipc.settings.set",
        "ipc.settings.get",
        "ipc.status.recheck",
    }
    assert expected.issubset(set(fake_bus.handlers.keys()))


# ---------------------------------------------------------------------------
# Boot — emits ipc.boot + initial ipc.settings.state
# ---------------------------------------------------------------------------


def test_boot_emits_ipc_boot_and_initial_settings_state(fake_bus: FakeBus) -> None:
    loop = SessionLoop(fake_bus)
    asyncio.run(loop.boot())
    boots = fake_bus.emitted_by_type("ipc.boot")
    assert len(boots) == 1
    assert boots[0]["payload"] == {"ready": True}
    settings = fake_bus.emitted_by_type("ipc.settings.state")
    assert len(settings) == 1
    payload = settings[0]["payload"]
    assert payload["voice"] == "kore"
    assert payload["mode"] == "coach"
    assert payload["genre"] == "tech-house"
    assert payload["muted"] is False


# ---------------------------------------------------------------------------
# Mute toggle
# ---------------------------------------------------------------------------


def test_mute_toggle_flips_state_and_acks(fake_bus: FakeBus) -> None:
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.session.mute",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"toggle": True},
        },
    )
    assert loop.muted is True
    acks = fake_bus.emitted_by_type("ipc.session.mute")
    assert len(acks) == 1
    assert acks[0]["payload"] == {"muted": True}

    # Second toggle un-mutes.
    _drive(
        fake_bus,
        {
            "type": "ipc.session.mute",
            "ts": "2026-05-12T08:00:01+00:00",
            "payload": {"toggle": True},
        },
    )
    assert loop.muted is False
    acks = fake_bus.emitted_by_type("ipc.session.mute")
    assert acks[-1]["payload"] == {"muted": False}


def test_mute_toggle_drains_playback_queue(fake_bus: FakeBus) -> None:
    pq = MagicMock(spec=["clear"])
    loop = SessionLoop(fake_bus, playback_queue=pq)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.session.mute",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"toggle": True},
        },
    )
    pq.clear.assert_called_once()
    # Unmuting does NOT call clear again — only mute-engage drains.
    pq.clear.reset_mock()
    _drive(
        fake_bus,
        {
            "type": "ipc.session.mute",
            "ts": "2026-05-12T08:00:01+00:00",
            "payload": {"toggle": True},
        },
    )
    pq.clear.assert_not_called()


def test_mute_clear_failure_does_not_crash(fake_bus: FakeBus) -> None:
    """A PlaybackQueue that raises on clear() must not bring the loop down."""
    pq = MagicMock(spec=["clear"])
    pq.clear.side_effect = RuntimeError("drain failed")
    loop = SessionLoop(fake_bus, playback_queue=pq)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.session.mute",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"toggle": True},
        },
    )
    # State still flips, ack still emits.
    assert loop.muted is True
    assert fake_bus.emitted_by_type("ipc.session.mute")[-1]["payload"] == {"muted": True}


# ---------------------------------------------------------------------------
# Settings get / set
# ---------------------------------------------------------------------------


def test_settings_get_emits_current_state(fake_bus: FakeBus) -> None:
    cfg = ConfigStore(voice="puck", mode="hype")
    loop = SessionLoop(fake_bus, config_store=cfg)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.settings.get",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {},
        },
    )
    state = fake_bus.emitted_by_type("ipc.settings.state")[-1]["payload"]
    assert state["voice"] == "puck"
    assert state["mode"] == "hype"
    assert state["muted"] is False


def test_settings_set_success_emits_fresh_state(fake_bus: FakeBus) -> None:
    cfg = ConfigStore()
    cascade = MagicMock(spec=["set_voice"])
    applier = SettingsApplier(config_store=cfg, cascade_agent=cascade)
    loop = SessionLoop(fake_bus, config_store=cfg, settings_applier=applier)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.settings.set",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"field": "voice", "value": "puck"},
        },
    )
    cascade.set_voice.assert_called_once_with("puck")
    state = fake_bus.emitted_by_type("ipc.settings.state")[-1]["payload"]
    assert state["voice"] == "puck"


def test_settings_set_failure_emits_ipc_error(fake_bus: FakeBus) -> None:
    cfg = ConfigStore()
    # No cascade_agent — apply will fail with "cascade_agent not wired"
    loop = SessionLoop(fake_bus, config_store=cfg)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.settings.set",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"field": "voice", "value": "puck"},
        },
    )
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) == 1
    assert errors[0]["payload"]["original_type"] == "ipc.settings.set"
    assert "cascade_agent" in errors[0]["payload"]["reason"]


# ---------------------------------------------------------------------------
# Status recheck
# ---------------------------------------------------------------------------


def test_status_recheck_emits_tick_for_known_component(
    fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    # Force the probe helpers to deterministic returns.
    monkeypatch.setattr(loop, "_probe_midi_count", lambda: 1)
    monkeypatch.setattr(loop, "_probe_screen_status", lambda: "ok")
    _drive(
        fake_bus,
        {
            "type": "ipc.status.recheck",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"component": "midi"},
        },
    )
    ticks = fake_bus.emitted_by_type("ipc.status.tick")
    assert len(ticks) == 1
    assert ticks[0]["payload"]["midi"] == 1
    assert ticks[0]["payload"]["screen"] == "ok"


def test_status_recheck_unknown_component_emits_ipc_error(fake_bus: FakeBus) -> None:
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.status.recheck",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"component": "rocket"},
        },
    )
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) == 1
    assert errors[0]["payload"]["original_type"] == "ipc.status.recheck"


# ---------------------------------------------------------------------------
# Snapshot shape — schema-valid in every path
# ---------------------------------------------------------------------------


def test_snapshot_fallback_when_music_state_missing(fake_bus: FakeBus) -> None:
    """Without MusicState the snapshot is IDLE + zeroed meters + grounded=false."""
    loop = SessionLoop(fake_bus)
    snapshot = loop._build_snapshot()
    payload_json = snapshot.to_json()  # Validates against schema
    payload = json.loads(payload_json)["payload"]
    assert payload["cohost_status"] == "IDLE"
    assert payload["grounded"] is False
    assert payload["meters"]["music"] == {"rms": 0.0, "peak": 0.0}
    assert payload["bpm"] is None
    assert payload["track"] is None


def test_snapshot_with_music_state_audible(fake_bus: FakeBus) -> None:
    """Audible music + non-trivial voice → LISTENING/TALKING, grounded=true."""
    ms = FakeMusicState(audible=True, bpm=124.0, audible_track="Foo - Bar")
    levels = FakeLevels(music=0.3, voice=0.0, mic=0.0)
    loop = SessionLoop(fake_bus, music_state=ms, levels=levels)
    payload_json = loop._build_snapshot().to_json()
    payload = json.loads(payload_json)["payload"]
    assert payload["cohost_status"] == "LISTENING"
    assert payload["grounded"] is True
    assert payload["bpm"] == 124.0
    assert payload["track"] == {"title": "Foo - Bar", "artist": None, "deck": "A"}


def test_snapshot_talking_when_voice_loud(fake_bus: FakeBus) -> None:
    ms = FakeMusicState(audible=True)
    levels = FakeLevels(music=0.3, voice=0.4)
    loop = SessionLoop(fake_bus, music_state=ms, levels=levels)
    payload = json.loads(loop._build_snapshot().to_json())["payload"]
    assert payload["cohost_status"] == "TALKING"


def test_snapshot_clamps_meters_to_unit_range(fake_bus: FakeBus) -> None:
    """Schema requires rms/peak in [0, 1]; values outside must be clamped."""
    levels = FakeLevels(music=1.5, voice=-0.2, mic=0.0)
    loop = SessionLoop(fake_bus, levels=levels)
    # If clamping is broken the schema validator throws here.
    payload = json.loads(loop._build_snapshot().to_json())["payload"]
    assert payload["meters"]["music"]["rms"] == 1.0
    assert payload["meters"]["voice"]["rms"] == 0.0


def test_snapshot_includes_transcript_delta(fake_bus: FakeBus) -> None:
    loop = SessionLoop(fake_bus)
    loop.append_transcript(role="ai", text="here we go")
    loop.append_transcript(role="ai", text="big drop incoming")
    payload = json.loads(loop._build_snapshot().to_json())["payload"]
    deltas = payload["transcript_delta"]
    assert len(deltas) == 2
    assert deltas[0]["role"] == "ai"
    assert deltas[0]["text"] == "here we go"
    # Next snapshot drains — delta is empty
    payload2 = json.loads(loop._build_snapshot().to_json())["payload"]
    assert payload2["transcript_delta"] == []


def test_snapshot_drains_new_midi_moves_only(fake_bus: FakeBus) -> None:
    cs = FakeControllerState(moves=[(0.1, "play_a"), (0.2, "cue_b")])
    loop = SessionLoop(fake_bus, controller_state=cs)
    payload = json.loads(loop._build_snapshot().to_json())["payload"]
    midi = payload["midi_events"]
    assert [m["control"] for m in midi] == ["play_a", "cue_b"]
    # Append a new move — only the new one shows in the next snapshot
    cs.recent_moves.append((0.3, "xfader"))
    payload2 = json.loads(loop._build_snapshot().to_json())["payload"]
    assert [m["control"] for m in payload2["midi_events"]] == ["xfader"]


def test_transcript_ring_caps_at_200(fake_bus: FakeBus) -> None:
    """Internal ring is bounded so a long session doesn't leak memory."""
    loop = SessionLoop(fake_bus)
    for i in range(250):
        loop.append_transcript(role="ai", text=f"line {i}")
    assert len(loop._transcript) == 200


# ---------------------------------------------------------------------------
# Invalid payload paths — ipc.error rather than crash
# ---------------------------------------------------------------------------


def test_invalid_inbound_emits_ipc_error_when_wrapped(fake_bus: FakeBus) -> None:
    """When the validation wrapper is installed, a bad payload surfaces
    as ``ipc.error`` instead of crashing the handler.

    The bus's outer schema check is the primary guard; the wrapper is
    belt-and-suspenders for tests that bypass the bus."""
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    # Wrap the settings.set handler with validation.
    inner = fake_bus.handlers["ipc.settings.set"]
    fake_bus.handlers["ipc.settings.set"] = loop._wrap_with_validation(
        inner, "ipc.settings.set"
    )
    # A payload missing the required ``field`` violates the schema.
    bad_msg = {
        "type": "ipc.settings.set",
        "ts": "2026-05-12T08:00:00+00:00",
        "payload": {"value": "puck"},
    }
    asyncio.run(fake_bus.handlers["ipc.settings.set"](bad_msg))
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) == 1
    assert errors[0]["payload"]["original_type"] == "ipc.settings.set"


# ---------------------------------------------------------------------------
# Snapshot loop runs at ~30Hz
# ---------------------------------------------------------------------------


def test_snapshot_loop_emits_multiple_frames(fake_bus: FakeBus) -> None:
    """The 30Hz snapshot loop emits multiple frames inside a short window.

    Drive ``_snapshot_loop`` directly with a near-immediate stop event so
    we don't need to wait the real 1/30s cadence.
    """

    async def run_briefly():
        loop = SessionLoop(fake_bus)
        # Fire the stop after a few intervals so the loop emits 2-3 frames
        # then exits cleanly.
        async def stop_soon():
            await asyncio.sleep(SNAPSHOT_INTERVAL * 3.0)
            loop.request_stop()

        await asyncio.gather(loop._snapshot_loop(), stop_soon())

    asyncio.run(run_briefly())
    snapshots = fake_bus.emitted_by_type("ipc.session.snapshot")
    assert len(snapshots) >= 2


# ---------------------------------------------------------------------------
# Full run lifecycle — register + boot + snapshot + stop
# ---------------------------------------------------------------------------


def test_run_lifecycle(fake_bus: FakeBus) -> None:
    """End-to-end: handlers registered → boot emitted → snapshot ticks →
    stop event fires → bus stopped."""

    async def run_briefly():
        loop = SessionLoop(fake_bus)

        async def stop_soon():
            await asyncio.sleep(SNAPSHOT_INTERVAL * 4.0)
            loop.request_stop()

        await asyncio.gather(loop.run(), stop_soon())

    asyncio.run(run_briefly())
    # Bus lifecycle
    assert fake_bus.started is True
    assert fake_bus.stopped is True
    # Boot fired
    assert len(fake_bus.emitted_by_type("ipc.boot")) == 1
    # At least one snapshot
    assert len(fake_bus.emitted_by_type("ipc.session.snapshot")) >= 1
    # Initial settings.state from boot
    assert len(fake_bus.emitted_by_type("ipc.settings.state")) >= 1


# ---------------------------------------------------------------------------
# Settings.set with no `value` key (schema requires it but the handler
# must still degrade gracefully if a future schema change relaxes that)
# ---------------------------------------------------------------------------


def test_settings_set_missing_value_returns_error(fake_bus: FakeBus) -> None:
    """A payload with field=voice and no value is rejected gracefully."""
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    handler = fake_bus.handlers["ipc.settings.set"]
    # Bypass bus-level schema (which would have rejected this) by calling
    # the handler directly with a synthetic payload.
    asyncio.run(handler({"type": "ipc.settings.set", "ts": "x", "payload": {"field": "voice"}}))
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# Re-export contract
# ---------------------------------------------------------------------------


def test_runtime_package_reexports_session_loop() -> None:
    """``from vibemix.runtime import SessionLoop, run_session`` resolves."""
    from vibemix.runtime import SessionLoop as SL
    from vibemix.runtime import run_session as rs

    assert SL is SessionLoop
    assert rs is run_session
