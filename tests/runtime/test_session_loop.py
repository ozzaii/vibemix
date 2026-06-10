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
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from vibemix.runtime import config_store as cs_mod
from vibemix.runtime import session_loop as session_loop_mod
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
        predicted_drop_in_sec: float | None = None,
    ) -> None:
        self.audible = audible
        self.phase = phase
        self.bpm = bpm
        self.audible_track = audible_track
        self.audible_deck = audible_deck
        self.recent_moves = recent_moves or []
        self.predicted_drop_in_sec = predicted_drop_in_sec


class FakeLevels:
    """Duck-typed Levels — only ``snapshot()`` is read."""

    def __init__(
        self,
        *,
        music=0.2,
        voice=0.0,
        mic=0.0,
        music_peak=None,
        voice_peak=None,
        mic_peak=None,
    ) -> None:
        self.music = music
        self.voice = voice
        self.mic = mic
        self.music_peak = music if music_peak is None else music_peak
        self.voice_peak = voice if voice_peak is None else voice_peak
        self.mic_peak = mic if mic_peak is None else mic_peak

    def snapshot(self) -> dict[str, float]:
        return {
            "music": self.music,
            "voice": self.voice,
            "mic": self.mic,
            "music_peak": self.music_peak,
            "voice_peak": self.voice_peak,
            "mic_peak": self.mic_peak,
        }


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
        "ipc.library.import",
        "ipc.library.import_cancel",
        "ipc.session.mute",
        "ipc.settings.set",
        "ipc.settings.set_brain",
        "ipc.settings.get",
        "ipc.status.recheck",
    }
    assert expected.issubset(set(fake_bus.handlers.keys()))


def test_parse_folder_import_progress_line() -> None:
    parsed = session_loop_mod._parse_folder_import_progress(
        "[12/40] skip My Cool Track (Extended Mix).flac  ~€0.0000"
    )
    assert parsed == (40, 12, "skip", "My Cool Track (Extended Mix).flac")
    assert session_loop_mod._parse_folder_import_progress("random banner") is None


def test_library_import_routes_folder_to_ingest(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library as library_mod

    folder = tmp_path / "crate"
    folder.mkdir()
    calls: dict[str, object] = {}

    class FakeStore:
        def close(self) -> None:
            calls["closed"] = True

    def fake_ingest_folder(folder_arg, embedder, store, **kwargs):
        calls["folder"] = folder_arg
        calls["persist_library"] = kwargs.get("persist_library")
        calls["compute_band_shares"] = kwargs.get("compute_band_shares")
        progress = kwargs["progress"]
        progress("[1/2] ok first.mp3  ~€0.0000")
        progress("[2/2] skip second.mp3  ~€0.0000")
        return SimpleNamespace(total=2, skipped_cached=1)

    monkeypatch.setattr(library_mod, "build_embedder", lambda *a, **k: object())
    monkeypatch.setattr(library_mod, "open_store", lambda *a, **k: FakeStore())
    monkeypatch.setattr(library_mod, "ingest_folder", fake_ingest_folder)

    loop = SessionLoop(fake_bus)

    async def _run() -> None:
        await loop._on_library_import(
            {
                "type": "ipc.library.import",
                "ts": "2026-06-05T00:00:00Z",
                "payload": {"path": str(folder), "schema_version": "1"},
            }
        )
        assert loop._library_import_task is not None
        await loop._library_import_task

    asyncio.run(_run())

    assert calls["folder"] == folder
    assert calls["persist_library"] is True
    assert calls["compute_band_shares"] is True
    assert calls["closed"] is True
    progress = fake_bus.emitted_by_type("ipc.library.import_progress")
    assert [p["payload"]["done"] for p in progress] == [1, 2, 2]
    assert progress[-1]["payload"]["cache_hits"] == 1


def test_library_import_routes_xml_to_existing_importer(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library as library_mod
    import vibemix.library.importer as importer_mod

    xml_path = tmp_path / "collection.xml"
    calls: dict[str, object] = {}

    class FakeStore:
        def close(self) -> None:
            calls["closed"] = True

    async def fake_import_library_async(
        xml_arg, embedder, store, *, on_progress, evidence_registry
    ):
        calls["xml"] = xml_arg
        calls["evidence_registry"] = evidence_registry
        on_progress(
            {
                "total": 3,
                "done": 1,
                "current_track_name": "Artist - Track",
                "cache_hits": 0,
                "cancelled": False,
            }
        )
        return {"total": 3, "done": 1, "cache_hits": 0, "cancelled": False}

    registry = MagicMock()
    monkeypatch.setattr(library_mod, "build_embedder", lambda *a, **k: object())
    monkeypatch.setattr(library_mod, "open_store", lambda *a, **k: FakeStore())
    monkeypatch.setattr(importer_mod, "import_library_async", fake_import_library_async)

    loop = SessionLoop(fake_bus, evidence_registry=registry)

    async def _run() -> None:
        await loop._on_library_import(
            {
                "type": "ipc.library.import",
                "ts": "2026-06-05T00:00:00Z",
                "payload": {"path": str(xml_path), "schema_version": "1"},
            }
        )
        assert loop._library_import_task is not None
        await loop._library_import_task

    asyncio.run(_run())

    assert calls["xml"] == xml_path
    assert calls["evidence_registry"] is registry
    assert calls["closed"] is True
    progress = fake_bus.emitted_by_type("ipc.library.import_progress")
    assert len(progress) == 1
    assert progress[0]["payload"]["current_track_name"] == "Artist - Track"


def test_library_import_routes_catalog_before_xml(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = SessionLoop(fake_bus)
    catalog = tmp_path / "collection.nml"
    calls: dict[str, object] = {}

    async def fake_catalog_import(source) -> None:
        calls["catalog_source"] = type(source).__name__

    async def fake_xml_import(path: Path) -> None:
        calls["xml"] = path

    monkeypatch.setattr(loop, "_start_catalog_source_import", fake_catalog_import)
    monkeypatch.setattr(loop, "_start_xml_import", fake_xml_import)

    asyncio.run(loop._run_library_import(catalog))

    assert calls == {"catalog_source": "TraktorSource"}


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
    assert payload["voice"] == "Adam"
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
    cfg = ConfigStore(
        voice="Bella",
        mode="hype",
        extra={"lens": "critique", "learn.headphone_device_index": 3},
    )
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
    assert state["voice"] == "Bella"
    assert state["mode"] == "hype"
    assert state["lens"] == "critique"
    assert state["learn.headphone_device_index"] == 3
    assert state["muted"] is False


def test_settings_get_sanitizes_corrupt_config_values(fake_bus: FakeBus) -> None:
    defaults = ConfigStore()
    cfg = ConfigStore()
    cfg.voice = 42  # type: ignore[assignment]
    cfg.mode = "storm"  # type: ignore[assignment]
    cfg.genre = None  # type: ignore[assignment]
    cfg.output_device_id = 42  # type: ignore[assignment]
    cfg.output_profile = "club"  # type: ignore[assignment]
    cfg.retention_days = "forever"  # type: ignore[assignment]
    cfg.push_to_mute_hotkey = ""  # type: ignore[assignment]
    cfg.lighter_blur = "yes"  # type: ignore[assignment]
    cfg.extra["lens"] = "bogus"
    cfg.extra["learn.headphone_device_index"] = True
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
    assert state["voice"] == defaults.voice
    assert state["mode"] == defaults.mode
    assert state["genre"] == defaults.genre
    assert state["output_device_id"] is None
    assert state["output_profile"] == defaults.output_profile
    assert state["retention_days"] == defaults.retention_days
    assert state["push_to_mute_hotkey"] == defaults.push_to_mute_hotkey
    assert state["lighter_blur"] == defaults.lighter_blur
    assert state["lens"] is None
    assert state["learn.headphone_device_index"] is None


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
            "payload": {"field": "voice", "value": "Bella"},
        },
    )
    cascade.set_voice.assert_called_once_with("Bella")
    state = fake_bus.emitted_by_type("ipc.settings.state")[-1]["payload"]
    assert state["voice"] == "Bella"


def test_settings_set_failure_emits_ipc_error(fake_bus: FakeBus) -> None:
    cfg = ConfigStore()
    # A genuinely-invalid value still fails (validation, not a missing hook —
    # missing hooks now persist + succeed deferred-live). 'chill' isn't a mode.
    loop = SessionLoop(fake_bus, config_store=cfg)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.settings.set",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"field": "mode", "value": "chill"},
        },
    )
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) == 1
    assert errors[0]["payload"]["original_type"] == "ipc.settings.set"
    assert "mode" in errors[0]["payload"]["reason"]


def test_settings_set_brain_direct_persists_key_and_acks_without_secret(
    fake_bus: FakeBus,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    _redirect_config_path: Path,
) -> None:
    import vibemix.runtime.session_loop as session_loop_mod

    env_path = tmp_path / ".env"
    monkeypatch.setattr(session_loop_mod, "brain_env_path", lambda: env_path)
    cfg = ConfigStore()
    loop = SessionLoop(fake_bus, config_store=cfg)
    loop.register_handlers()

    _drive(
        fake_bus,
        {
            "type": "ipc.settings.set_brain",
            "ts": "2026-06-04T08:00:00+00:00",
            "payload": {
                "mode": "direct",
                "gemini_api_key": "AIza-test-secret-value",
            },
        },
    )

    assert cfg.llm_mode == "direct"
    assert json.loads(_redirect_config_path.read_text())["llm_mode"] == "direct"
    assert "GEMINI_API_KEY=AIza-test-secret-value" in env_path.read_text()
    acks = fake_bus.emitted_by_type("ipc.settings.brain_ack")
    assert len(acks) == 1
    assert acks[0]["payload"] == {
        "ok": True,
        "mode": "direct",
        "key_set": True,
        "restart_required": True,
        "error": None,
    }
    assert "AIza-test-secret-value" not in json.dumps(fake_bus.emitted)


def test_settings_set_brain_proxy_persists_mode_without_key_write(
    fake_bus: FakeBus,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import vibemix.runtime.session_loop as session_loop_mod

    env_path = tmp_path / ".env"
    monkeypatch.setattr(session_loop_mod, "brain_env_path", lambda: env_path)
    cfg = ConfigStore(llm_mode="direct")
    loop = SessionLoop(fake_bus, config_store=cfg)
    loop.register_handlers()

    _drive(
        fake_bus,
        {
            "type": "ipc.settings.set_brain",
            "ts": "2026-06-04T08:00:00+00:00",
            "payload": {"mode": "proxy", "gemini_api_key": "AIza-ignored"},
        },
    )

    assert cfg.llm_mode == "proxy"
    assert not env_path.exists()
    ack = fake_bus.emitted_by_type("ipc.settings.brain_ack")[0]["payload"]
    assert ack["ok"] is True
    assert ack["mode"] == "proxy"
    assert ack["key_set"] is False
    assert "AIza-ignored" not in json.dumps(fake_bus.emitted)


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
    assert ticks[0]["payload"]["livekit"] == "connecting"
    assert ticks[0]["payload"]["gemini"] == "down"
    assert ticks[0]["payload"]["midi"] == 1
    assert ticks[0]["payload"]["screen"] == "ok"


def test_status_recheck_accepts_legacy_numeric_ts(
    fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    monkeypatch.setattr(loop, "_probe_midi_count", lambda: 1)
    monkeypatch.setattr(loop, "_probe_screen_status", lambda: "ok")

    _drive(
        fake_bus,
        {
            "type": "ipc.status.recheck",
            "ts": 1_780_205_767.4745522,
            "payload": {"component": "midi"},
        },
    )

    assert fake_bus.emitted_by_type("ipc.error") == []
    tick = fake_bus.emitted_by_type("ipc.status.tick")[-1]["payload"]
    assert tick["midi"] == 1
    assert tick["screen"] == "ok"


def test_live_status_recheck_mirrors_attached_runtime(fake_bus: FakeBus) -> None:
    loop = SessionLoop(
        fake_bus,
        music_state=MagicMock(),
        controller_state=MagicMock(port_name="DDJ-FLX4"),
        screen_available=False,
    )
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.status.recheck",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"component": "livekit"},
        },
    )
    tick = fake_bus.emitted_by_type("ipc.status.tick")[-1]["payload"]
    assert tick["livekit"] == "ok"
    assert tick["gemini"] == "ok"
    assert tick["midi"] == 1
    assert tick["screen"] == "unavailable"


def test_live_status_recheck_reports_visible_controller_without_midi_as_connected(
    fake_bus: FakeBus,
) -> None:
    loop = SessionLoop(
        fake_bus,
        music_state=MagicMock(
            controller_connected=True,
            controller_midi_activity="connected_no_midi_traffic",
            controller_midi_messages_seen=0,
        ),
        controller_state=MagicMock(port_name="DDJ-FLX4"),
        screen_available=True,
    )
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.status.recheck",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"component": "midi"},
        },
    )
    tick = fake_bus.emitted_by_type("ipc.status.tick")[-1]["payload"]
    assert tick["livekit"] == "ok"
    assert tick["gemini"] == "ok"
    assert tick["midi"] == 1
    assert tick["midi_activity"] == "connected_no_midi_traffic"
    assert tick["midi_device"] == "DDJ-FLX4"


def test_live_status_recheck_reports_disconnected_controller_activity(
    fake_bus: FakeBus,
) -> None:
    loop = SessionLoop(
        fake_bus,
        music_state=MagicMock(
            controller_connected=False,
            controller_midi_activity="unknown",
            controller_midi_messages_seen=0,
        ),
        controller_state=MagicMock(
            port_name=None,
            activity_snapshot=lambda: {
                "connected": False,
                "port_name": None,
                "messages_seen_total": 0,
                "events_seen_total": 0,
                "moves_seen_total": 0,
            },
        ),
        screen_available=True,
    )
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.status.recheck",
            "ts": "2026-05-12T08:00:00+00:00",
            "payload": {"component": "midi"},
        },
    )
    tick = fake_bus.emitted_by_type("ipc.status.tick")[-1]["payload"]
    assert tick["midi"] == 0
    assert tick["midi_activity"] == "disconnected"
    assert tick["midi_device"] is None


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
    levels = FakeLevels(music=0.3, voice=0.0, mic=0.0, music_peak=0.74)
    loop = SessionLoop(fake_bus, music_state=ms, levels=levels)
    payload_json = loop._build_snapshot().to_json()
    payload = json.loads(payload_json)["payload"]
    assert payload["cohost_status"] == "LISTENING"
    assert payload["grounded"] is True
    assert payload["meters"]["music"] == {"rms": 0.3, "peak": 0.74}
    assert payload["bpm"] == 124.0
    assert payload["track"] == {"title": "Foo - Bar", "artist": None, "deck": "A"}


def test_snapshot_with_drop_prediction_emits_bar_count(fake_bus: FakeBus) -> None:
    ms = FakeMusicState(audible=True, bpm=128.0, predicted_drop_in_sec=15.0)
    levels = FakeLevels(music=0.3, voice=0.0, mic=0.0)
    loop = SessionLoop(fake_bus, music_state=ms, levels=levels)
    payload = json.loads(loop._build_snapshot().to_json())["payload"]
    assert payload["drop_pred_bars"] == 8


def test_snapshot_talking_when_voice_loud(fake_bus: FakeBus) -> None:
    ms = FakeMusicState(audible=True)
    levels = FakeLevels(music=0.3, voice=0.4)
    loop = SessionLoop(fake_bus, music_state=ms, levels=levels)
    payload = json.loads(loop._build_snapshot().to_json())["payload"]
    assert payload["cohost_status"] == "TALKING"


def test_snapshot_talking_holds_bpm_without_grounding_music(fake_bus: FakeBus) -> None:
    ms = FakeMusicState(
        audible=False,
        bpm=117.6,
        audible_track="Cached Track",
        predicted_drop_in_sec=15.0,
    )
    levels = FakeLevels(music=0.0, voice=0.4)
    loop = SessionLoop(fake_bus, music_state=ms, levels=levels)
    payload = json.loads(loop._build_snapshot().to_json())["payload"]
    assert payload["cohost_status"] == "TALKING"
    assert payload["grounded"] is False
    assert payload["bpm"] == 117.6
    assert payload["drop_pred_bars"] is None
    assert payload["track"] is None


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
    fake_bus.handlers["ipc.settings.set"] = loop._wrap_with_validation(inner, "ipc.settings.set")
    # A payload missing the required ``field`` violates the schema.
    bad_msg = {
        "type": "ipc.settings.set",
        "ts": "2026-05-12T08:00:00+00:00",
        "payload": {"value": "Bella"},
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


def test_session_start_failure_emits_ipc_error_with_cause(fake_bus: FakeBus) -> None:
    """The GO LIVE failure envelope must carry the CAUSE, not just the
    exception class — the deck notice renders this string verbatim."""

    async def boom() -> None:
        raise RuntimeError("proxy setup failed: proxy /register rejected (status=401)")

    loop = SessionLoop(fake_bus, session_start=boom, session_is_active=lambda: False)
    loop.register_handlers()
    _drive(
        fake_bus,
        {"type": "ipc.session.start", "ts": "2026-06-10T00:00:00+00:00", "payload": {}},
    )
    errs = fake_bus.emitted_by_type("ipc.error")
    assert len(errs) == 1
    assert errs[0]["payload"]["original_type"] == "ipc.session.start"
    assert "proxy /register rejected" in errs[0]["payload"]["reason"]


def test_folder_import_total_failure_surfaces_failed_and_ipc_error(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 100%-failed folder import must NOT look like success on the wire."""
    import vibemix.library as library_mod

    folder = tmp_path / "crate"
    folder.mkdir()

    class FakeStore:
        def close(self) -> None:
            pass

    def fake_ingest_folder(folder_arg, embedder, store, **kwargs):
        progress = kwargs["progress"]
        progress("[1/2] err first.mp3  ~€0.0000")
        progress("[2/2] err second.mp3  ~€0.0000")
        return SimpleNamespace(
            total=2,
            embedded=0,
            skipped_cached=0,
            failed=2,
            failures=[
                (str(folder / "first.mp3"), "unprobeable"),
                (str(folder / "second.mp3"), "unprobeable"),
            ],
        )

    monkeypatch.setattr(library_mod, "build_embedder", lambda *a, **k: object())
    monkeypatch.setattr(library_mod, "open_store", lambda *a, **k: FakeStore())
    monkeypatch.setattr(library_mod, "ingest_folder", fake_ingest_folder)

    loop = SessionLoop(fake_bus)

    async def _run() -> None:
        await loop._on_library_import(
            {
                "type": "ipc.library.import",
                "ts": "2026-06-05T00:00:00Z",
                "payload": {"path": str(folder), "schema_version": "1"},
            }
        )
        assert loop._library_import_task is not None
        await loop._library_import_task

    asyncio.run(_run())

    progress = fake_bus.emitted_by_type("ipc.library.import_progress")
    assert [p["payload"]["failed"] for p in progress] == [1, 2, 2]
    final = progress[-1]["payload"]
    assert final["failure_reason"] == "first.mp3: unprobeable"
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) == 1
    assert errors[0]["payload"]["original_type"] == "ipc.library.import"
    assert "all 2 files failed" in errors[0]["payload"]["reason"]
    assert "first.mp3: unprobeable" in errors[0]["payload"]["reason"]


def test_folder_import_partial_failure_reports_failed_without_ipc_error(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library as library_mod

    folder = tmp_path / "crate"
    folder.mkdir()

    class FakeStore:
        def close(self) -> None:
            pass

    def fake_ingest_folder(folder_arg, embedder, store, **kwargs):
        progress = kwargs["progress"]
        progress("[1/2] ok first.mp3  ~€0.0000")
        progress("[2/2] err second.mp3  ~€0.0000")
        return SimpleNamespace(
            total=2,
            embedded=1,
            skipped_cached=0,
            failed=1,
            failures=[(str(folder / "second.mp3"), "decode error")],
        )

    monkeypatch.setattr(library_mod, "build_embedder", lambda *a, **k: object())
    monkeypatch.setattr(library_mod, "open_store", lambda *a, **k: FakeStore())
    monkeypatch.setattr(library_mod, "ingest_folder", fake_ingest_folder)

    loop = SessionLoop(fake_bus)

    async def _run() -> None:
        await loop._on_library_import(
            {
                "type": "ipc.library.import",
                "ts": "2026-06-05T00:00:00Z",
                "payload": {"path": str(folder), "schema_version": "1"},
            }
        )
        assert loop._library_import_task is not None
        await loop._library_import_task

    asyncio.run(_run())

    final = fake_bus.emitted_by_type("ipc.library.import_progress")[-1]["payload"]
    assert final["failed"] == 1
    assert final["failure_reason"] == "second.mp3: decode error"
    assert fake_bus.emitted_by_type("ipc.error") == []


# ---------------------------------------------------------------------------
# Lane A (2026-06-10) — wizard→live pending library-import handoff
# ---------------------------------------------------------------------------


def _isolate_config_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    if sys.platform == "win32":
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        monkeypatch.setenv("APPDATA", str(tmp_path))


def test_kick_pending_library_import_consumes_marker(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wizard-queued source is popped from config and routed through the
    real import path with CLAP ensured first; the marker never re-fires."""
    _isolate_config_home(tmp_path, monkeypatch)
    import vibemix.library.model_assets as model_assets
    from vibemix.runtime.config_store import (
        PENDING_LIBRARY_IMPORT_KEY,
        ConfigStore,
        load_config,
    )

    installed: list[str] = []
    monkeypatch.setattr(
        model_assets,
        "install_models",
        lambda target, **k: (installed.append(target), {"ok": True, "results": []})[1],
    )
    ran: list[Path] = []

    async def fake_run(self, source_path: Path) -> None:
        ran.append(source_path)

    monkeypatch.setattr(SessionLoop, "_run_library_import", fake_run)

    store = ConfigStore(extra={PENDING_LIBRARY_IMPORT_KEY: "/Users/x/Music/crates"})
    loop = SessionLoop(fake_bus, config_store=store)

    async def _run() -> None:
        task = loop.kick_pending_library_import()
        assert task is not None
        await task

    asyncio.run(_run())

    assert installed == ["clap"]
    assert ran == [Path("/Users/x/Music/crates")]
    assert PENDING_LIBRARY_IMPORT_KEY not in load_config().extra


def test_kick_pending_library_import_noop_without_marker(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_config_home(tmp_path, monkeypatch)
    from vibemix.runtime.config_store import ConfigStore

    loop = SessionLoop(fake_bus, config_store=ConfigStore())

    async def _run() -> None:
        assert loop.kick_pending_library_import() is None

    asyncio.run(_run())
    assert fake_bus.emitted_by_type("ipc.error") == []


def test_kick_pending_import_clap_failure_emits_ipc_error(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLAP install failure surfaces as ipc.error — never a silent dead-end —
    and the real import is NOT attempted."""
    _isolate_config_home(tmp_path, monkeypatch)
    import vibemix.library.model_assets as model_assets
    from vibemix.runtime.config_store import PENDING_LIBRARY_IMPORT_KEY, ConfigStore

    monkeypatch.setattr(
        model_assets,
        "install_models",
        lambda target, **k: {"ok": False, "results": [{"errors": ["network down"]}]},
    )
    ran: list[Path] = []

    async def fake_run(self, source_path: Path) -> None:
        ran.append(source_path)

    monkeypatch.setattr(SessionLoop, "_run_library_import", fake_run)

    store = ConfigStore(extra={PENDING_LIBRARY_IMPORT_KEY: "/Users/x/Music/crates"})
    loop = SessionLoop(fake_bus, config_store=store)

    async def _run() -> None:
        task = loop.kick_pending_library_import()
        assert task is not None
        await task

    asyncio.run(_run())

    assert ran == []
    errors = fake_bus.emitted_by_type("ipc.error")
    assert errors and "CLAP" in errors[0]["payload"]["reason"]


# ---------------------------------------------------------------------------
# Staleness action handler — restored Package 5J wiring (was one-ended at
# a153915c: the renderer's staleness-banner emitted
# ipc.library.staleness_action but the 364c55ba restructure dropped the
# Python handler; receipts in the 2026-06-10 stale-test alignment report).
# ---------------------------------------------------------------------------


def test_staleness_action_handler_registered(fake_bus: FakeBus) -> None:
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    assert "ipc.library.staleness_action" in fake_bus.handlers


def test_staleness_action_snooze_persists_and_clears_retained(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """snooze_7d routes to apply_snooze_action and drops the retained nudge."""
    import vibemix.library as library_mod

    applied: list[str] = []
    cleared: list[str] = []
    monkeypatch.setattr(
        library_mod, "apply_snooze_action", lambda action: applied.append(action)
    )
    fake_bus.clear_retained = lambda mtype: cleared.append(mtype)  # type: ignore[attr-defined]

    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.library.staleness_action",
            "ts": "2026-06-10T00:00:00Z",
            "payload": {"action": "snooze_7d", "schema_version": "1"},
        },
    )
    assert applied == ["snooze_7d"]
    assert cleared == ["ipc.library.staleness_nudge"]


def test_staleness_reindex_uses_recorded_source_not_renderer_path(
    fake_bus: FakeBus, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Package 5J consent boundary: reindex_folder re-imports ONLY the
    recorded source folder — a renderer-supplied path is never trusted."""
    import vibemix.library.staleness as staleness_mod

    recorded = tmp_path / "recorded-crate"
    recorded.mkdir()
    monkeypatch.setattr(
        staleness_mod, "library_freshness_status", lambda *a, **k: object()
    )
    monkeypatch.setattr(
        staleness_mod, "refreshable_source", lambda status: (str(recorded), "folder")
    )
    ran: list[Path] = []

    async def fake_run(self, source_path: Path) -> None:
        ran.append(source_path)

    monkeypatch.setattr(SessionLoop, "_run_library_import", fake_run)

    loop = SessionLoop(fake_bus)
    loop.register_handlers()

    async def _run() -> None:
        await fake_bus.handlers["ipc.library.staleness_action"](
            {
                "type": "ipc.library.staleness_action",
                "ts": "2026-06-10T00:00:00Z",
                "payload": {
                    "action": "reindex_folder",
                    "schema_version": "1",
                },
            }
        )
        task = loop._library_import_task
        assert task is not None
        await task

    asyncio.run(_run())
    assert ran == [recorded]


def test_staleness_reindex_rejected_when_source_not_folder(
    fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An XML/unknown recorded source never triggers a folder reindex."""
    import vibemix.library.staleness as staleness_mod

    monkeypatch.setattr(
        staleness_mod, "library_freshness_status", lambda *a, **k: object()
    )
    monkeypatch.setattr(
        staleness_mod, "refreshable_source", lambda status: (None, None)
    )
    ran: list[Path] = []

    async def fake_run(self, source_path: Path) -> None:
        ran.append(source_path)

    monkeypatch.setattr(SessionLoop, "_run_library_import", fake_run)

    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.library.staleness_action",
            "ts": "2026-06-10T00:00:00Z",
            "payload": {"action": "reindex_folder", "schema_version": "1"},
        },
    )
    assert ran == []


def test_boot_staleness_nudge_emitted_when_stale(
    fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_boot_sweeps emits the staleness nudge so the banner can show."""
    import vibemix.library.staleness as staleness_mod

    monkeypatch.setattr(
        staleness_mod,
        "freshness_nudge_payload",
        lambda *a, **k: {
            "age_days": 42,
            "snoozed_until_ts": None,
            "source_path": "/Users/x/Music/crates",
            "source_kind": "folder",
        },
    )
    loop = SessionLoop(fake_bus)
    asyncio.run(loop.run_boot_sweeps())
    nudges = fake_bus.emitted_by_type("ipc.library.staleness_nudge")
    assert len(nudges) == 1
    assert nudges[0]["payload"]["age_days"] == 42


def test_boot_staleness_nudge_silent_when_fresh(
    fake_bus: FakeBus, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibemix.library.staleness as staleness_mod

    monkeypatch.setattr(
        staleness_mod, "freshness_nudge_payload", lambda *a, **k: None
    )
    loop = SessionLoop(fake_bus)
    asyncio.run(loop.run_boot_sweeps())
    assert fake_bus.emitted_by_type("ipc.library.staleness_nudge") == []
