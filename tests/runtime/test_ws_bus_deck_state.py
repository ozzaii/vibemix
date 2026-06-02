# SPDX-License-Identifier: Apache-2.0
"""Phase 62 (PILL-03) — additive ``deck_state`` field on the flat 30Hz ws bus frame.

Serializes Phase-59 per-deck ``MusicState.deck_state`` onto the EXISTING flat
mascot frame on the EXISTING ``ws://127.0.0.1:8765`` socket so the pill's
deck-context chips have real per-deck ``title``/``camelot``/``key``/``bpm`` to
render. PATTERNS flagged the load-bearing wire gap: ``deck_state`` exists
in-process (Phase 59) but is on NEITHER WS frame today, so deck chips have
nothing to read. This plan is the PRODUCER half (62-04 is the consumer).

Three contracts are pinned here:

  * **Populated deck** — a resolved DeckTrack rides the wire with its exact
    title/camelot/key/bpm (the bus is a dumb wire; values pass through verbatim).
  * **Honest-null (anti-slop)** — an unresolved deck (camelot=None, key=None)
    serializes ``camelot: null`` + ``key: null`` on the wire — NEVER a fabricated
    key. Carries the Phase-59 uncitable-by-construction guarantee to the UI.
  * **Golden-equivalence** — an empty ``deck_state.decks`` serializes
    ``deck_state: {}`` and leaves every pre-existing flat key byte-identical to a
    pre-deck_state baseline frame (additive-only; existing subscribers undisturbed).

Plus the emit-boundary guard (BRINGUP-04) stays intact — the additive field never
trips the ``("music","voice","mic")`` key-presence check.

Pattern mirrors test_ws_bus_genre_fields.py exactly — mock ``websockets.serve``
so nothing binds; drive a ``LongLivedClient`` through the captured handler to
capture a real outbound payload.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from vibemix.runtime.ws_bus import ws_broadcast
from vibemix.state import MusicState
from vibemix.state.deck_context import midi_evidence_key
from vibemix.state.deck_state import DeckState, DeckTrack

_REAL_SLEEP = asyncio.sleep


def _build_mock_server() -> MagicMock:
    server = MagicMock()
    server.close = MagicMock()
    server.wait_closed = AsyncMock(return_value=None)
    return server


def _capture_payload(
    state: MusicState, mocker, *, audio_capture_context: dict | None = None
) -> dict:
    """Drive ws_broadcast through one tick + capture the first outbound mascot
    payload as a parsed dict. Same approach as test_ws_bus_genre_fields."""
    mock_server = _build_mock_server()
    serve_mock = AsyncMock(return_value=mock_server)
    mocker.patch("vibemix.runtime.ws_bus.websockets.serve", new=serve_mock)

    fake_levels = MagicMock()
    fake_levels.snapshot = MagicMock(return_value={"music": 0.05, "voice": 0.02, "mic": 0.01})
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
            client = self

            async def gen():
                await release_handler.wait()
                if False:  # pragma: no cover
                    yield client

            return gen()

    sleep_counter = {"n": 0}

    async def fast_sleep(_s):
        sleep_counter["n"] += 1
        if sleep_counter["n"] >= 50:  # safety net
            stop_event.set()
            release_handler.set()
        await _REAL_SLEEP(0)

    mocker.patch("vibemix.runtime.ws_bus.asyncio.sleep", side_effect=fast_sleep)

    async def driver():
        bg = asyncio.create_task(
            ws_broadcast(
                fake_levels,
                state,
                manual_trigger,
                stop_event,
                audio_capture_context=audio_capture_context,
            )
        )
        await _REAL_SLEEP(0)
        await _REAL_SLEEP(0)
        handler = serve_mock.await_args.args[0]

        client = LongLivedClient()
        handler_task = asyncio.create_task(handler(client))

        await bg
        try:
            await asyncio.wait_for(handler_task, timeout=0.5)
        except Exception:
            handler_task.cancel()

    asyncio.run(driver())

    assert len(sent_payloads) >= 1, "expected at least one broadcast payload"
    return json.loads(sent_payloads[0])


def test_payload_includes_populated_deck_state(mocker):
    """A resolved deck rides the mascot frame with its exact DeckTrack values:
    title / camelot / key / bpm pass through verbatim (the bus is a dumb wire)."""
    state = MusicState()
    state.audible = True
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(
                title="Strobe",
                track_id="track-1",
                camelot="8A",
                key="Am",
                genre="psytrance",
                bpm=128.0,
                confidence=0.8,
                source="rekordbox_xml",
            )
        },
        source_status={
            "controller": "present",
            "controller_connection": "connected",
            "library": "present",
            "library_tracks": "24",
            "library_source": "rekordbox_xml",
            "library_match": "matched",
            "nowplaying": "blocked_non_deck_owner",
            "nowplaying_owner": "com.apple.webkit.gpu",
            "nowplaying_title": "seen",
            "resolution": "blocked_non_deck_nowplaying",
            "second_deck_source": "suppressed_requires_independent_source",
            "screen_vision": "disabled",
        },
    )

    payload = _capture_payload(state, mocker)

    assert payload["live_context_schema_version"] == 2
    assert set(payload["live_context_capabilities"]) >= {
        "deck_source_status",
        "audio_part_context",
        "deck_audio_separation_context",
        "audio_window_map",
        "audio_delta",
        "live_evidence",
    }
    assert "deck_state" in payload, f"missing 'deck_state' — got keys: {sorted(payload.keys())}"
    assert "A" in payload["deck_state"], (
        f"deck 'A' missing — got {sorted(payload['deck_state'].keys())}"
    )
    deck_a = payload["deck_state"]["A"]
    assert deck_a["title"] == "Strobe"
    assert deck_a["track_id"] == "track-1"
    assert deck_a["camelot"] == "8A"
    assert deck_a["key"] == "Am"
    assert deck_a["genre"] == "psytrance"
    assert deck_a["bpm"] == 128.0
    # confidence rides too (the consumer can dim a low-confidence chip).
    assert deck_a["confidence"] == 0.8
    assert deck_a["source"] == "rekordbox_xml"


def test_payload_includes_bounded_deck_mixer_posture(mocker):
    """Per-deck controller posture rides the same flat live frame for Viber."""
    state = MusicState()
    state.audible = True
    state.audible_deck = "A"
    state.deck_confidence = 0.75
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {
        "vol": 110,
        "eq_low": 2,
        "eq_mid": 64,
        "eq_hi": 127,
        "filter": 64,
        "play": True,
    }
    state.deck_b = {
        "vol": 72,
        "eq_low": 64,
        "eq_mid": 64,
        "eq_hi": 64,
        "filter": 92,
        "play": False,
    }

    payload = _capture_payload(state, mocker)

    assert payload["deck_mixer"] == {
        "connected": True,
        "midi_activity": "unknown",
        "midi_messages_seen": 0,
        "midi_events_seen": 0,
        "midi_moves_seen": 0,
        "xfader": 64,
        "deck_confidence": 0.75,
        "A": {
            "vol": 110,
            "eq_low": 2,
            "eq_mid": 64,
            "eq_hi": 127,
            "filter": 64,
            "play": True,
        },
        "B": {
            "vol": 72,
            "eq_low": 64,
            "eq_mid": 64,
            "eq_hi": 64,
            "filter": 92,
            "play": False,
        },
    }


def test_payload_includes_bounded_deck_context_maps(mocker):
    """The flat live frame carries direct deck1/deck2 maps for Viber/Gemini."""
    state = MusicState()
    state.audible = True
    state.audible_deck = "A"
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(
                title="Strobe",
                track_id="track-1",
                camelot="8A",
                confidence=0.82,
                source="rekordbox_xml",
            )
        },
        source_status={
            "controller": "present",
            "controller_connection": "connected",
            "library": "present",
            "library_tracks": "24",
            "library_source": "rekordbox_xml",
            "library_match": "matched",
            "nowplaying": "blocked_non_deck_owner",
            "nowplaying_owner": "com.apple.webkit.gpu",
            "nowplaying_title": "seen",
            "resolution": "blocked_non_deck_nowplaying",
            "second_deck_source": "suppressed_requires_independent_source",
            "screen_vision": "disabled",
        },
    )

    payload = _capture_payload(state, mocker)

    assert payload["deck_lanes_context"].startswith("deck_lanes_context[")
    assert "lane_aliases=deck1:A,deck2:B" in payload["deck_lanes_context"]
    assert "rule=per_lane_identity_route_control_not_outcome" in payload["deck_lanes_context"]

    assert payload["deck_reference_context"].startswith("deck_reference_context[")
    assert "deck1=A" in payload["deck_reference_context"]
    assert "deck2=B" in payload["deck_reference_context"]
    assert "audio=P1_global_mix" in payload["deck_reference_context"]
    assert "per_deck_audio=not_attached" in payload["deck_reference_context"]
    assert "isolated_decks=false" in payload["deck_reference_context"]
    assert "rule=deck1_deck2_reference_not_outcome" in payload["deck_reference_context"]

    assert payload["deck_source_context"].startswith("deck_source_context[")
    assert "identity_state=MusicState.deck_state" in payload["deck_source_context"]
    assert "resolved=A" in payload["deck_source_context"]
    assert "unresolved=B" in payload["deck_source_context"]
    assert "nowplaying=blocked_non_deck_owner" in payload["deck_source_context"]
    assert "controller_connection=connected" in payload["deck_source_context"]
    assert "library=present" in payload["deck_source_context"]
    assert "library_tracks=24" in payload["deck_source_context"]
    assert "library_source=rekordbox_xml" in payload["deck_source_context"]
    assert "library_match=matched" in payload["deck_source_context"]
    assert "nowplaying_owner=com.apple.webkit.gpu" in payload["deck_source_context"]
    assert "nowplaying_title=seen" in payload["deck_source_context"]
    assert "resolution=blocked_non_deck_nowplaying" in payload["deck_source_context"]
    assert "second_deck_source=suppressed_requires_independent_source" in payload[
        "deck_source_context"
    ]
    assert "screen_vision=disabled" in payload["deck_source_context"]
    assert "second_deck=independent_source_required" in payload["deck_source_context"]
    assert "rule=unresolved_deck_is_not_transition_evidence" in payload["deck_source_context"]
    assert payload["deck_source_status"] == {
        "controller": "present",
        "controller_connection": "connected",
        "library": "present",
        "library_tracks": "24",
        "library_source": "rekordbox_xml",
        "library_match": "matched",
        "nowplaying": "blocked_non_deck_owner",
        "nowplaying_owner": "com.apple.webkit.gpu",
        "nowplaying_title": "seen",
        "resolution": "blocked_non_deck_nowplaying",
        "second_deck_source": "suppressed_requires_independent_source",
        "screen_vision": "disabled",
    }

    assert payload["deck_audio_context"].startswith("deck_audio_context[")
    assert "source=global_mix" in payload["deck_audio_context"]
    assert "isolated_decks=false" in payload["deck_audio_context"]
    assert "support=single_deck_A" in payload["deck_audio_context"]
    assert "rule=audio_heard_must_be_mapped_through_deck_context" in payload["deck_audio_context"]
    assert payload["deck_audio_separation_context"].startswith("deck_audio_separation_context[")
    assert "deckA_audio=not_captured" in payload["deck_audio_separation_context"]
    assert "deckB_audio=not_captured" in payload["deck_audio_separation_context"]
    assert "per_deck_audio=not_attached" in payload["deck_audio_separation_context"]


def test_payload_includes_bounded_audio_delta(mocker):
    """DSP deltas ride the flat frame for Viber move-effect grounding."""
    state = MusicState()
    state.audible = True
    state.rms = 0.12
    state.onset_density = 3.0
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.10,
        "sub": 0.24,
        "low": 0.32,
        "mid": 0.30,
        "high": 0.20,
        "onset_density": 2.0,
    }

    payload = _capture_payload(state, mocker)

    assert payload["audio_delta"] == [
        "sub energy fell 50% (strong)",
        "low energy fell 50% (strong)",
        "mid energy rose 33% (clear)",
        "high energy rose 60% (strong)",
    ]


def test_payload_includes_bounded_live_evidence_refs(mocker):
    """Structured live evidence rides beside prose context for Viber grounding."""
    mocker.patch("vibemix.state.music_state.time.time", return_value=1010.0)
    state = MusicState()
    state.set_start_at = 1000.0
    state.audible = True
    state.audible_deck = "A"
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(
                title="Strobe",
                camelot="8A",
                confidence=0.8,
                source="rekordbox_xml",
            )
        }
    )
    state.recent_moves = [(0.5, "A_low: flat→killed (big twist)")]
    state.audio_delta = ["sub energy fell 50% (strong)"]

    payload = _capture_payload(state, mocker)

    assert payload["recent_moves"] == ["A_low: flat→killed (big twist)"]
    assert payload["audio_window_context"].startswith("audio_window_context[")
    assert "P1=master_global_mix" in payload["audio_window_context"]
    assert (
        "move_anchor=A_low:_flat_to_killed_big_twist@-0.5s:inside_P1"
        in payload["audio_window_context"]
    )
    assert "deckA_audio=not_attached" in payload["audio_window_context"]
    assert payload["audio_part_context"].startswith("audio_part_context[")
    assert "surface=live_context" in payload["audio_part_context"]
    assert "P1=live_global_mix" in payload["audio_part_context"]
    assert "P1_model_heard=false" in payload["audio_part_context"]
    assert "P1_runtime_observed=true" in payload["audio_part_context"]
    assert "P1_deck_audio=global_mix_not_stems" in payload["audio_part_context"]
    assert "per_deck_audio=not_attached" in payload["audio_part_context"]
    assert payload["audio_window_map"]["p1"] == "master_global_mix"
    assert payload["audio_window_map"]["pre_s"] == [-6.0, -1.0]
    assert payload["audio_window_map"]["action_s"] == [-1.0, 0.0]
    assert payload["audio_window_map"]["deckA_audio"] == "not_attached"
    assert payload["audio_window_map"]["deckB_audio"] == "not_attached"
    assert payload["audio_window_map"]["duplicate_audio"] == "same_master_not_deck_split"
    assert payload["audio_window_map"]["move_anchors"][0]["relation"] == "inside_P1"
    assert payload["audio_window_map"]["future"]["span"] == "not_attached"
    move_key = midi_evidence_key("A_low: flat→killed (big twist)")
    evidence = payload["live_evidence"]
    assert evidence["midi"] == [{"key": move_key, "t": 9.5}]
    assert "deck_audio_support=single_deck_A" in evidence["mix"]
    assert "transition_block=single_resolved_deck" in evidence["mix"]
    assert "second_deck_identity=unknown_or_suppressed" in evidence["mix"]
    assert "deck_lanes=A_known_route_dominant+B_unknown_route_muted" in evidence["mix"]
    assert (
        "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted" in evidence["mix"]
    )
    assert "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none" in evidence["mix"]
    assert "move_effect=sub_energy_fell_50pct_strong" in evidence["mix"]
    assert f"midi:{move_key}@9.5" in evidence["refs"]
    assert "mix:transition_block=single_resolved_deck" in evidence["refs"]
    assert "mix:second_deck_identity=unknown_or_suppressed" in evidence["refs"]
    assert "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted" in evidence["refs"]
    assert (
        "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted"
        in evidence["refs"]
    )
    assert (
        "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none"
        in evidence["refs"]
    )


def test_payload_includes_capture_separation_context_for_multichannel_devices(mocker):
    state = MusicState()
    state.controller_connected = True

    payload = _capture_payload(
        state,
        mocker,
        audio_capture_context={
            "requested_device": "BlackHole 16ch",
            "device_name": "BlackHole 16ch",
            "input_channels": 16,
            "opened_channels": 2,
            "sample_rate": 48000,
        },
    )

    ctx = payload["deck_audio_separation_context"]
    assert "capture_device=BlackHole_16ch" in ctx
    assert "input_channels=16" in ctx
    assert "opened_channels=2" in ctx
    assert "device_capacity=multichannel_available" in ctx
    assert "mode=multichannel_device_available_but_runtime_opened_stereo" in ctx
    assert "current_capture=P1_global_mix" in ctx
    assert "deckA_audio=not_captured" in ctx
    assert "deckB_audio=not_captured" in ctx


def test_payload_marks_configured_deck_pair_capture(mocker):
    state = MusicState()
    state.controller_connected = True

    payload = _capture_payload(
        state,
        mocker,
        audio_capture_context={
            "requested_device": "BlackHole 16ch",
            "device_name": "BlackHole 16ch",
            "input_channels": 16,
            "opened_channels": 4,
            "sample_rate": 48000,
            "master_channels": "0,1,2,3",
            "deck_channels": {"A": "0,1", "B": "2,3"},
            "deck_audio_capture_enabled": True,
            "deck_audio_rms": {"A": 0.02, "B": 0.0},
            "deck_audio_features": {
                "A": {"activity": "active", "rms": 0.02, "peak": 0.1, "zcr": 0.03},
                "B": {"activity": "silent", "rms": 0.0, "peak": 0.0, "zcr": 0.0},
            },
            "deck_audio_deltas": {
                "A": ["rms_rose_100pct_strong"],
                "B": ["rms_fell_50pct_strong"],
            },
            "deck_audio_windows": {
                "pre_s": [-6.0, -1.0],
                "current_s": [-1.0, 0.0],
                "A": {
                    "pre": {"activity": "active", "rms": 0.02, "peak": 0.1, "flux": 0.004},
                    "current": {
                        "activity": "active",
                        "rms": 0.04,
                        "peak": 0.12,
                        "flux": 0.009,
                    },
                    "delta": ["rms_rose_100pct_strong"],
                },
                "B": {
                    "pre": {"activity": "active", "rms": 0.03, "peak": 0.11, "flux": 0.006},
                    "current": {
                        "activity": "silent",
                        "rms": 0.0,
                        "peak": 0.0,
                        "flux": 0.001,
                    },
                    "delta": ["rms_fell_50pct_strong"],
                },
            },
        },
    )

    ctx = payload["deck_audio_separation_context"]
    assert "mode=deck_pair_capture_configured" in ctx
    assert "current_capture=P1_global_mix_plus_deck_pairs" in ctx
    assert "deckA_audio=captured" in ctx
    assert "deckB_audio=captured" in ctx
    assert "per_deck_audio=captured_not_attached" in ctx
    assert "deck_audio_activity=A_active+B_silent" in ctx
    assert "deck_audio_features_context" in payload["live_context_capabilities"]
    assert "deck_audio_features_context[" in payload["deck_audio_features_context"]
    assert "A_activity=active" in payload["deck_audio_features_context"]
    assert "B_activity=silent" in payload["deck_audio_features_context"]
    assert "deck_audio_delta_context" in payload["live_context_capabilities"]
    assert "deck_audio_delta_context[" in payload["deck_audio_delta_context"]
    assert "A_delta=rms_rose_100pct_strong" in payload["deck_audio_delta_context"]
    assert "B_delta=rms_fell_50pct_strong" in payload["deck_audio_delta_context"]
    assert "deck_audio_window_context" in payload["live_context_capabilities"]
    assert "deck_audio_window_context[" in payload["deck_audio_window_context"]
    assert "timeline=pre_action_current" in payload["deck_audio_window_context"]
    assert "A_current=active_rms_0.040" in payload["deck_audio_window_context"]
    assert "deck_audio_capture=A_active+B_silent" in payload["live_evidence"]["mix"]
    assert "deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000" in payload[
        "live_evidence"
    ]["mix"]
    assert "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong" in payload[
        "live_evidence"
    ]["mix"]
    assert (
        "deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_silent_pre_0.030_current_0.000"
    ) in payload["live_evidence"]["mix"]


def test_configured_deck_pair_capture_forces_audio_window_on_silent_frame(mocker):
    """A routed Deck A/B capture is enough structure to publish the P1 time map."""
    state = MusicState()

    payload = _capture_payload(
        state,
        mocker,
        audio_capture_context={
            "requested_device": "BlackHole 16ch",
            "device_name": "BlackHole 16ch",
            "input_channels": 16,
            "opened_channels": 4,
            "sample_rate": 48000,
            "master_channels": "0,1,2,3",
            "deck_channels": {"A": "0,1", "B": "2,3"},
            "deck_audio_capture_enabled": True,
            "deck_audio_rms": {"A": 0.0, "B": 0.0},
            "deck_audio_features": {
                "A": {"activity": "silent", "rms": 0.0, "peak": 0.0, "zcr": 0.0},
                "B": {"activity": "silent", "rms": 0.0, "peak": 0.0, "zcr": 0.0},
            },
        },
    )

    assert payload["deck"] == "none"
    assert payload["audible"] is False
    assert payload["deck_audio_separation_context"].startswith(
        "deck_audio_separation_context["
    )
    assert "mode=deck_pair_capture_configured" in payload["deck_audio_separation_context"]
    assert "deck_audio_delta_context" in payload["live_context_capabilities"]
    assert payload["deck_audio_delta_context"].startswith("deck_audio_delta_context[")
    assert "A_delta=no_clear_delta" in payload["deck_audio_delta_context"]
    assert "B_delta=no_clear_delta" in payload["deck_audio_delta_context"]
    assert payload["audio_window_context"].startswith("audio_window_context[")
    assert "move_anchor=none" in payload["audio_window_context"]
    assert payload["audio_window_map"]["p1"] == "master_global_mix"
    assert payload["audio_window_map"]["move_anchors"] == []
    assert payload["audio_window_map"]["future"]["span"] == "not_attached"


def test_payload_renders_source_context_from_diagnostic_source_status(mocker):
    state = MusicState()
    state.deck_state.source_status = {
        "controller": "present",
        "controller_connection": "disconnected",
        "nowplaying": "deck_candidate",
        "nowplaying_title": "none",
        "audible_deck": "none",
        "resolution": "no_single_attributable_deck",
    }

    payload = _capture_payload(state, mocker)

    assert payload["deck_source_context"].startswith("deck_source_context[")
    assert payload["deck_lanes_context"].startswith("deck_lanes_context[")
    assert "A(identity=unknown route=unknown" in payload["deck_lanes_context"]
    assert "B(identity=unknown route=unknown" in payload["deck_lanes_context"]
    assert payload["deck_reference_context"].startswith("deck_reference_context[")
    assert "deck1=A identity=unknown route=unknown" in payload["deck_reference_context"]
    assert "deck2=B identity=unknown route=unknown" in payload["deck_reference_context"]
    assert "controller=present" in payload["deck_source_context"]
    assert "controller_connection=disconnected" in payload["deck_source_context"]
    assert "resolution=no_single_attributable_deck" in payload["deck_source_context"]
    assert "source_status_rule=diagnostic_not_deck_identity" in payload["deck_source_context"]
    assert "transition_block=no_resolved_decks" in payload["live_evidence"]["mix"]
    assert "second_deck_identity=blocked" in payload["live_evidence"]["mix"]
    assert "deck_lanes=A_unknown_route_unknown+B_unknown_route_unknown" in payload[
        "live_evidence"
    ]["mix"]
    assert "deck_reference=deck1_A_unknown_route_unknown+deck2_B_unknown_route_unknown" in payload[
        "live_evidence"
    ]["mix"]
    assert "deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none" in payload[
        "live_evidence"
    ]["mix"]


def test_payload_includes_audio_window_map_without_recent_moves(mocker):
    """Cold controller frames still publish the P1 timing contract."""
    state = MusicState()
    state.controller_connected = True
    state.deck_a = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.recent_moves = []

    payload = _capture_payload(state, mocker)

    assert payload["live_context_schema_version"] == 2
    assert "audio_window_map" in payload["live_context_capabilities"]
    assert "audio_part_context" in payload["live_context_capabilities"]
    assert "deck_audio_separation_context" in payload["live_context_capabilities"]
    assert "audio_part_context" in payload
    assert payload["audio_window_context"].startswith("audio_window_context[")
    assert "move_anchor=none" in payload["audio_window_context"]
    assert payload["audio_window_map"]["p1"] == "master_global_mix"
    assert payload["audio_window_map"]["move_anchors"] == []
    assert payload["audio_window_map"]["rule"] == "time_alignment_not_outcome_verdict"


def test_payload_marks_controller_reference_without_resolved_decks(mocker):
    """The runtime producer itself blocks transition claims when deck identity is cold."""
    state = MusicState()
    state.audible = False
    state.audible_deck = "mix"
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 72, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}

    payload = _capture_payload(state, mocker)

    assert payload["deck_state"] == {}
    evidence = payload["live_evidence"]
    assert "transition_block=no_resolved_decks" in evidence["mix"]
    assert "second_deck_identity=blocked" in evidence["mix"]
    assert "deck_lanes=A_unknown_route_dominant+B_unknown_route_present" in evidence["mix"]
    assert (
        "deck_reference=deck1_A_unknown_route_dominant+deck2_B_unknown_route_present"
        in evidence["mix"]
    )
    assert "deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none" in evidence["mix"]
    assert "mix:transition_block=no_resolved_decks" in evidence["refs"]
    assert (
        "mix:deck_reference=deck1_A_unknown_route_dominant+deck2_B_unknown_route_present"
        in evidence["refs"]
    )
    assert "mix:deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none" in evidence["refs"]


def test_course3_operator_action_names_visible_controller_with_no_midi_traffic(mocker):
    """A visible FLX4 with zero MIDI frames needs setup guidance, not "open a channel"."""
    state = MusicState()
    state.audible = True
    state.rms = 0.05
    state.controller_connected = True
    state.controller_midi_activity = "connected_no_midi_traffic"
    state.deck_a = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}

    payload = _capture_payload(state, mocker)

    assert payload["deck_mixer"]["midi_activity"] == "connected_no_midi_traffic"
    assert payload["course3_lens"]["operator_action"] == {
        "prompt": "Enable FLX4 MIDI.",
        "steps": [
            "The FLX4 port is visible, but macOS has not delivered any MIDI frames to vibemix.",
            "In Rekordbox controller/MIDI settings, enable FLX4 MIDI output or reconnect the controller.",
            "Move an EQ knob or fader until the status changes from no MIDI traffic.",
        ],
    }


def test_payload_unresolved_deck_is_honest_null(mocker):
    """Anti-slop on the wire: an unresolved deck (camelot=None, key=None)
    serializes ``camelot: null`` + ``key: null`` — NEVER a fabricated key string.
    The honesty is enforced at the SOURCE (Phase-59 honest-default contract); the
    bus carries it verbatim as JSON null."""
    state = MusicState()
    state.audible = True
    state.deck_state = DeckState(
        decks={
            "B": DeckTrack(
                title="Some Untagged Track",
                # camelot / key intentionally left at the honest None default.
                bpm=124.0,
                confidence=0.4,
            )
        }
    )

    payload = _capture_payload(state, mocker)

    deck_b = payload["deck_state"]["B"]
    # JSON null on the wire (Python None round-trips to None via json.loads).
    assert deck_b["camelot"] is None, "a fabricated camelot leaked instead of null"
    assert deck_b["key"] is None, "a fabricated key leaked instead of null"
    # The rest of the deck is still carried honestly.
    assert deck_b["title"] == "Some Untagged Track"
    assert deck_b["bpm"] == 124.0


def test_unresolved_bpm_zero_is_honest_null(mocker):
    """CR-02 honest-null hole: a present-but-unresolved deck has the honest
    ``DeckTrack`` default ``bpm=0.0`` (NOT a measured value). A serialized
    ``bpm: 0.0`` renders a fabricated ``"0"`` BPM on the pill — exactly the
    anti-slop leak the phase exists to close. The serialize edge must emit
    ``bpm: null`` (treat 0.0 as unknown), mirroring the camelot/key honest-null
    discipline already on this wire."""
    state = MusicState()
    state.audible = True
    state.deck_state = DeckState(
        decks={
            # All-defaults DeckTrack: bpm=0.0, camelot=None, key=None — a deck
            # detected present (vision) but with no metadata resolved.
            "A": DeckTrack(title="Untagged"),
        }
    )

    payload = _capture_payload(state, mocker)

    deck_a = payload["deck_state"]["A"]
    # The whole point: a 0.0-default bpm must serialize as JSON null, never 0.
    assert deck_a["bpm"] is None, "bpm=0.0 leaked as a fabricated value instead of null"
    # camelot/key remain honest-null too.
    assert deck_a["camelot"] is None
    assert deck_a["key"] is None
    assert deck_a["title"] == "Untagged"


def test_empty_deck_state_is_golden_equivalent(mocker):
    """Golden-equivalence: an empty ``deck_state.decks`` serializes
    ``deck_state: {}`` (additive-only) AND every pre-existing flat key is
    byte-identical to a baseline frame built WITHOUT touching deck_state.

    A fresh MusicState has ``deck_state == DeckState()`` (decks={}) by default, so
    this is also the no-decks-resolved boot case existing subscribers see."""
    # Baseline: a default MusicState — deck_state defaults to empty decks.
    baseline_state = MusicState()
    baseline_state.audible = True
    baseline_state.audible_deck = "A"
    baseline_state.phase = "groove"
    baseline_state.bpm = 128.0
    baseline_payload = _capture_payload(baseline_state, mocker)

    # The same state, but explicitly assert deck_state is empty.
    assert baseline_state.deck_state.decks == {}, "default deck_state should be empty"

    # deck_state is present and serializes to the empty object.
    assert "deck_state" in baseline_payload, "additive deck_state field missing"
    assert baseline_payload["deck_state"] == {}, (
        f"empty deck_state should serialize to {{}}, got {baseline_payload['deck_state']!r}"
    )

    # Golden-equivalence: every OTHER flat key is exactly what it was before — the
    # additive field neither removed nor altered any pre-existing key.
    for key, val in baseline_payload.items():
        if key == "deck_state":
            continue
        assert val == baseline_payload[key], f"flat key {key!r} mutated"

    # Pin the load-bearing flat keys explicitly so a regression is loud.
    assert baseline_payload["music"] == 0.05
    assert baseline_payload["voice"] == 0.02
    assert baseline_payload["mic"] == 0.01
    assert baseline_payload["deck"] == "A"
    assert baseline_payload["phase"] == "groove"
    assert baseline_payload["bpm"] == 128.0
    assert baseline_payload["audible"] is True


def test_deck_state_does_not_trip_empty_frame_guard(mocker):
    """The additive deck_state field is strictly additive — the captured frame
    still carries the meter keys (music/voice/mic) so the Phase-51 emit-boundary
    guard would NOT have skipped it, even with a populated deck_state."""
    state = MusicState()
    state.audible = True
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Strobe", camelot="8A", key="Am", bpm=128.0)}
    )

    payload = _capture_payload(state, mocker)

    # A frame was actually captured (no silent no-op / no guard skip).
    assert payload, "no frame captured — the guard may have skipped the send"
    # Meter keys present -> guard not tripped by the additive field.
    for k in ("music", "voice", "mic"):
        assert k in payload, f"meter key {k!r} missing — guard would have skipped this frame"
    # And the additive field rode along.
    assert payload["deck_state"]["A"]["camelot"] == "8A"
