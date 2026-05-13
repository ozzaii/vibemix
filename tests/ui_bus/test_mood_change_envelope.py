# SPDX-License-Identifier: Apache-2.0
"""Phase 13-05 Task 2 — ipc.mascot.mood_change schema + SettingsApplier emit.

Covers (per plan must_haves):
  * MascotMoodChangeMessage validates against the schema (round-trip).
  * Schema REJECTS bad mood values and missing-mood payloads.
  * check_ipc_schema.py count-parity holds at 27 wrappers == 27 oneOf entries.
  * SettingsApplier.apply("mood", "teacher") writes MusicState.mood +
    ConfigStore.mood + emits ipc.mascot.mood_change.
  * SettingsApplier.apply("mood", "invalid") returns (False, err) — no
    silent fallback (T-13-05-01 mitigation).
  * SettingsApplier.apply("click_through", "not-a-bool") returns (False, err).
  * ws_broadcast 30Hz snapshot payload includes mood / bpm_confidence /
    downbeat_phase keys.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import jsonschema
import pytest

# Ensure the runtime test fixture path is resolvable.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vibemix.runtime import config_store as cs_mod
from vibemix.runtime.config_store import ConfigStore
from vibemix.runtime.settings import SettingsApplier
from vibemix.runtime.ws_bus import ws_broadcast
from vibemix.state import MusicState
from vibemix.ui_bus import MascotMoodChange, MascotMoodChangePayload, validate_message


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _redirect_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ConfigStore.save() into tmp_path/config.json."""
    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    return target


@pytest.fixture
def store() -> ConfigStore:
    return ConfigStore()


@pytest.fixture
def music_state() -> MusicState:
    return MusicState()


@pytest.fixture
def ws_bus_spy() -> MagicMock:
    """Records every emit() call so we can assert the mood_change envelope."""
    bus = MagicMock()
    bus.emit = AsyncMock(return_value=None)
    return bus


def _apply(applier: SettingsApplier, field: str, value):
    return asyncio.run(applier.apply(field, value))


# ---------------------------------------------------------------------------
# Schema-level tests
# ---------------------------------------------------------------------------


def test_mascot_mood_change_roundtrips_through_schema():
    """A valid envelope round-trips: dataclass.to_json() → parse → validate."""
    msg = MascotMoodChange.make(mood="teacher", previous_mood="hype-man", at=12.34)
    raw = msg.to_json()
    parsed = json.loads(raw)
    # Should pass validation without raising.
    validate_message(parsed)
    assert parsed["type"] == "ipc.mascot.mood_change"
    assert parsed["payload"]["mood"] == "teacher"
    assert parsed["payload"]["previous_mood"] == "hype-man"


def test_schema_rejects_invalid_mood_enum():
    """A mood outside the 3-element set must fail schema validation."""
    bad = {
        "type": "ipc.mascot.mood_change",
        "ts": "2026-05-12T10:00:00+00:00",
        "payload": {"mood": "party-rocker"},
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bad)


def test_schema_rejects_missing_mood_field():
    """payload.mood is required — drop it and validation must fail."""
    bad = {
        "type": "ipc.mascot.mood_change",
        "ts": "2026-05-12T10:00:00+00:00",
        "payload": {},
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_message(bad)


def test_count_parity_holds_after_addition():
    """Wave 0 invariant — schema oneOf count must equal wrapper-dataclass count.

    Plan 13-05 grew both 26 → 27. Plan 15-01 grew both 27 → 34 (+7 recordings.*
    families). The check_ipc_schema.py invariant is what fails the CI build if
    either side regresses, so we assert it here directly.
    """
    from vibemix.ui_bus import messages as ui_bus_messages

    wrapper_count = sum(
        1
        for name in dir(ui_bus_messages)
        if isinstance(obj := getattr(ui_bus_messages, name), type)
        and hasattr(obj, "__dataclass_fields__")
        and "type" in obj.__dataclass_fields__
    )

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "tauri" / "ui" / "src" / "ipc" / "messages.schema.json"
    )
    schema = json.loads(schema_path.read_text())
    oneof_count = len(schema["oneOf"])

    assert wrapper_count == oneof_count == 34, (
        f"count parity violated: wrappers={wrapper_count} vs oneOf={oneof_count}; "
        "expected both 34 after Plan 15-01"
    )


# ---------------------------------------------------------------------------
# SettingsApplier — mood
# ---------------------------------------------------------------------------


def test_apply_mood_writes_music_state_and_config_and_emits(
    store, music_state, ws_bus_spy
):
    applier = SettingsApplier(
        config_store=store,
        music_state=music_state,
        ws_bus=ws_bus_spy,
    )
    success, error = _apply(applier, "mood", "teacher")
    assert (success, error) == (True, None)
    assert music_state.mood == "teacher"
    # mood is persisted via ConfigStore.extra (Phase 13-05 deliberate
    # choice — keeps the typed Phase-12 ConfigStore surface untouched).
    assert store.extra.get("mood") == "teacher"
    # Exactly one emit call carrying a valid ipc.mascot.mood_change frame.
    assert ws_bus_spy.emit.await_count == 1
    sent = ws_bus_spy.emit.await_args.args[0]
    assert sent["type"] == "ipc.mascot.mood_change"
    assert sent["payload"]["mood"] == "teacher"
    assert sent["payload"]["previous_mood"] == "hype-man"
    validate_message(sent)  # belt-and-braces — the envelope is schema-valid.


def test_apply_mood_invalid_value_returns_error_no_emit(
    store, music_state, ws_bus_spy
):
    """Invalid mood → dispatcher-shape ack (False, err); no state mutation,
    no emit. Matches the existing SettingsApplier contract."""
    applier = SettingsApplier(
        config_store=store,
        music_state=music_state,
        ws_bus=ws_bus_spy,
    )
    success, error = _apply(applier, "mood", "party-rocker")
    assert success is False
    assert "mood" in (error or "")
    assert music_state.mood == "hype-man"  # unchanged
    ws_bus_spy.emit.assert_not_called()


def test_apply_mood_unwired_dependencies_returns_error(store):
    """Without music_state or ws_bus refs, the applier returns (False, err)
    rather than crashing — consistent with the cascade/audio_core pattern."""
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "mood", "teacher")
    assert success is False
    assert error  # some explanatory string


# ---------------------------------------------------------------------------
# SettingsApplier — click_through
# ---------------------------------------------------------------------------


def test_apply_click_through_persists_only_no_music_state_write(
    store, music_state, ws_bus_spy
):
    """click_through is a Rust/webview concern — ConfigStore only."""
    applier = SettingsApplier(
        config_store=store,
        music_state=music_state,
        ws_bus=ws_bus_spy,
    )
    success, error = _apply(applier, "click_through", True)
    assert (success, error) == (True, None)
    # ConfigStore extra holds the bool (not a typed field — we treat
    # click_through as a pass-through to the Rust shell).
    assert store.extra.get("click_through") is True or store.click_through is True  # type: ignore[attr-defined]
    # MusicState NOT touched.
    assert music_state.mood == "hype-man"
    # NO mood_change emit (different ipc envelope).
    ws_bus_spy.emit.assert_not_called()


def test_apply_click_through_invalid_type_rejected(store, music_state, ws_bus_spy):
    applier = SettingsApplier(
        config_store=store,
        music_state=music_state,
        ws_bus=ws_bus_spy,
    )
    success, error = _apply(applier, "click_through", "yes")
    assert success is False
    assert error and "click_through" in error


# ---------------------------------------------------------------------------
# ws_broadcast snapshot payload extension
# ---------------------------------------------------------------------------


def test_ws_broadcast_snapshot_includes_new_phase_13_fields(mocker):
    """The 30Hz mascot snapshot MUST carry mood / bpm_confidence /
    downbeat_phase so the renderer (Plan 13-04) can read them off the
    bus without a second round-trip."""
    from unittest.mock import AsyncMock, MagicMock

    mock_server = MagicMock()
    mock_server.close = MagicMock()
    mock_server.wait_closed = AsyncMock(return_value=None)
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(
        return_value={"music": 0.05, "voice": 0.02, "mic": 0.01}
    )
    state = MusicState()
    state.audible = True
    state.audible_deck = "B"
    state.phase = "groove"
    state.mood = "teacher"
    state.bpm_confidence = 0.78
    state.downbeat_phase = 0.42

    manual_trigger = asyncio.Event()
    stop_event = asyncio.Event()

    sent_payloads: list[str] = []
    release_handler = asyncio.Event()

    class LongLivedClient:
        async def send(self, payload):
            sent_payloads.append(payload)
            stop_event.set()
            release_handler.set()

        def __aiter__(self):
            async def gen():
                await release_handler.wait()
                if False:  # pragma: no cover
                    yield

            return gen()

    _REAL_SLEEP = asyncio.sleep
    counter = {"n": 0}

    async def fast_sleep(_s):
        counter["n"] += 1
        if counter["n"] >= 50:
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    async def driver():
        bg = asyncio.create_task(
            ws_broadcast(fake_levels, state, manual_trigger, stop_event)
        )
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]
        client = LongLivedClient()
        ht = asyncio.create_task(handler(client))
        await bg
        try:
            await asyncio.wait_for(ht, timeout=0.5)
        except Exception:
            ht.cancel()

    asyncio.run(driver())
    assert sent_payloads, "expected at least one broadcast payload"
    payload = json.loads(sent_payloads[0])
    # Phase 13 additions
    for key in ("mood", "bpm_confidence", "downbeat_phase"):
        assert key in payload, f"missing key {key} in payload {payload}"
    assert payload["mood"] == "teacher"
    assert payload["bpm_confidence"] == pytest.approx(0.78)
    assert payload["downbeat_phase"] == pytest.approx(0.42)
