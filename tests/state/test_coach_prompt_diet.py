# SPDX-License-Identifier: Apache-2.0
"""Plan 19-02 — AICoach.build_prompt diet path + token-cap pinning.

Token-count proxy: ``len(prompt) // 4`` (project has no tiktoken dep — see
pyproject.toml; the 4-chars-per-token ratio is the empirical cl100k baseline
for English, good enough for cap assertions).

Caps:
- PROMPT_TOKEN_CAP_ACK  = 800   tokens for diet=True ack-eligible events.
- PROMPT_TOKEN_CAP_FULL = 1500  tokens for diet=False full events.

ACK_ELIGIBLE_EVENTS = {"HEARTBEAT", "MIX_MOVE", "LAYER_ARRIVAL", "KAAN_SPOKE"}.

The `diet=False` default path stays byte-identical to the existing v4 golden
output — the Phase 4 invariant. The diet path is a NEW code branch gated
behind a kwarg.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from vibemix.state import AICoach, Event, MusicState
from vibemix.state.deck_state import DeckState, DeckTrack
from vibemix.state.prompt_builder import (
    ACK_ELIGIBLE_EVENTS,
    PROMPT_TOKEN_CAP_ACK,
    PROMPT_TOKEN_CAP_FULL,
)

# 4 chars/token proxy — pyproject.toml has no tiktoken dep, so we use the
# cl100k empirical baseline ratio.
TOKEN_PROXY_CHARS_PER_TOKEN = 4


def _tokens(s: str) -> int:
    return len(s) // TOKEN_PROXY_CHARS_PER_TOKEN


def _ev(type_: str, state: MusicState | None = None, extra: dict | None = None) -> Event:
    return Event(type=type_, state=state or MusicState(), extra=extra or {})


def _populated_state() -> MusicState:
    """Build a maximally-populated MusicState — long history + recent moves +
    set_arc + track_history. Used to stress the diet=False FULL cap."""
    return MusicState(
        audible=True,
        rms=0.094,
        bands={"sub": 0.20, "low": 0.30, "mid": 0.30, "high": 0.20},
        bpm=126.0,
        audible_track="Daft Punk - Around the World (Mellow Mix Extended Re-edit)",
        audible_track_confidence=0.8,
        audible_deck="A",
        set_start_at=755.0,
        phase_history=[
            (100.0, "silent", "low"),
            (200.0, "low", "groove"),
            (300.0, "groove", "build"),
            (400.0, "build", "drop"),
        ],
        track_history=[
            (50.0, "Track One Title"),
            (150.0, "Track Two Title"),
            (250.0, "Track Three Title"),
            (350.0, "Track Four Title"),
            (450.0, "Track Five Title"),
        ],
        recent_moves=[
            (0.5, "A_play→ON"),
            (1.2, "A_low: cut→killed (big twist)"),
            (2.4, "xfader→A-side"),
            (3.1, "A_high: scoop→cut"),
            (4.7, "B_volume: down→up"),
            (5.5, "A_mid: flat→boost"),
            (6.8, "B_play→ON"),
            (7.9, "B_high: cut→flat"),
        ],
        long_arc=[i * 0.01 for i in range(30)],
    )


# ---------- module-level constants ----------


def test_constants_exported():
    """ACK_ELIGIBLE_EVENTS frozenset + both token caps importable from coach."""
    assert PROMPT_TOKEN_CAP_ACK == 800
    assert PROMPT_TOKEN_CAP_FULL == 1500
    assert isinstance(ACK_ELIGIBLE_EVENTS, frozenset)
    assert ACK_ELIGIBLE_EVENTS == frozenset(
        {"HEARTBEAT", "MIX_MOVE", "LAYER_ARRIVAL", "KAAN_SPOKE"}
    )


# ---------- diet=False byte-identical to v4 golden ----------


def test_diet_false_byte_identical_to_v4():
    """diet=False (default) returns the EXACT same string as calling without
    the kwarg — the v4 byte-identity invariant for the existing call sites."""
    ev = _ev("HEARTBEAT")
    out_no_kwarg = AICoach.build_prompt(ev)
    out_diet_false = AICoach.build_prompt(ev, diet=False)
    assert out_no_kwarg == out_diet_false


def test_diet_false_byte_identical_with_snapshot():
    """diet=False + registry_snapshot kwarg = same as default for snapshot path."""
    ev = _ev("HEARTBEAT")
    snap = {"ev": {"HEARTBEAT@30.0": (30.0,)}}
    out_no_diet = AICoach.build_prompt(ev, registry_snapshot=snap)
    out_diet_false = AICoach.build_prompt(ev, registry_snapshot=snap, diet=False)
    assert out_no_diet == out_diet_false


# ---------- diet=True per-event cap assertions ----------


def test_diet_true_heartbeat_under_cap(mocker):
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    ev = _ev("HEARTBEAT", _populated_state())
    out = AICoach.build_prompt(ev, diet=True)
    assert _tokens(out) <= PROMPT_TOKEN_CAP_ACK


def test_diet_true_mix_move_under_cap_with_moves_inline(mocker):
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    ev = _ev(
        "MIX_MOVE",
        _populated_state(),
        extra={"moves": ["A_low: cut→killed (big twist)", "xfader→A-side"]},
    )
    out = AICoach.build_prompt(ev, diet=True)
    assert _tokens(out) <= PROMPT_TOKEN_CAP_ACK
    # Moves list is still in the task tail (the MIX_MOVE task formats it).
    assert "A controller move was observed [A_low: cut→killed (big twist), xfader→A-side]" in out
    assert "did it land" not in out


def test_diet_true_layer_arrival_under_cap(mocker):
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    ev = _ev("LAYER_ARRIVAL", _populated_state())
    out = AICoach.build_prompt(ev, diet=True)
    assert _tokens(out) <= PROMPT_TOKEN_CAP_ACK


def test_diet_true_kaan_spoke_under_cap(mocker):
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    ev = _ev("KAAN_SPOKE", _populated_state())
    out = AICoach.build_prompt(ev, diet=True)
    assert _tokens(out) <= PROMPT_TOKEN_CAP_ACK


# ---------- diet=True drops history / set_arc / phase_history fields ----------


def test_diet_true_drops_history_fields(mocker):
    """The diet path drops phase_age / track_age / set_arc / phase_history /
    recent_tracks — only the 5 strictly-needed fields stay."""
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    ev = _ev("HEARTBEAT", _populated_state())
    out = AICoach.build_prompt(ev, diet=True)
    assert "phase_age=" not in out
    assert "track_age=" not in out
    assert "set_arc[" not in out
    assert "phase_history:" not in out
    assert "recent_tracks:" not in out


def test_diet_true_keeps_required_grounding_fields(mocker):
    """The compact evidence_line keeps core hearing/track/deck/time/move grounding."""
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    ev = _ev("MIX_MOVE", _populated_state(), extra={"moves": ["A_play→ON"]})
    out = AICoach.build_prompt(ev, diet=True)
    assert "hearing[" in out
    assert "track=" in out
    assert "deck=A" in out
    assert "set_time=" in out
    assert "recent_moves[8s]:" in out


def test_diet_true_mix_move_keeps_deck_context_for_single_deck_guard(mocker):
    """MIX_MOVE uses the diet path, so the one-deck transition guard must
    survive the compact prompt."""
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    state = _populated_state()
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(
                title="Strobe",
                camelot="8A",
                bpm=128.0,
                confidence=0.8,
                source="rekordbox_xml",
            )
        }
    )
    ev = _ev("MIX_MOVE", state, extra={"moves": ["A_play→ON"]})

    out = AICoach.build_prompt(ev, diet=True)

    assert "deck_context[" in out
    assert "deck_lanes_context[" in out
    assert "move_context[" in out
    assert "scope=single_deck_move_A" in out
    assert "transition_block=single_resolved_deck" in out
    assert out.count("live_evidence[") == 1
    assert "do NOT call this a transition or blend" in out
    assert _tokens(out) <= PROMPT_TOKEN_CAP_ACK


def test_diet_true_mix_move_can_include_compact_recall_context(mocker):
    """Hot MIX_MOVE recall stays diet-sized but shows the past signature."""
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    state = _populated_state()
    state.audio_delta = ["low energy fell 50% (strong)"]
    ev = _ev("MIX_MOVE", state, extra={"moves": ["A_low: flat→killed"]})
    survivors = [
        SimpleNamespace(
            record_id="20260520-2200:7",
            signature=(
                "coach_line | track=Strobe | phase=groove | deck=A | "
                "event=MIX_MOVE | move_effect=move_effect_context[rule=dsp_delta_not_causal_proof] "
                "| audio_delta=low energy fell 50% (strong) | said: heard the low cut thin out"
            ),
        )
    ]

    out = AICoach.build_prompt(ev, recall_moments=survivors, diet=True)

    assert "FROM A PAST SESSION" in out
    assert "[recall:20260520-2200:7]" in out
    assert "low energy fell 50% (strong)" in out
    assert "in the live audio" in out
    assert _tokens(out) <= PROMPT_TOKEN_CAP_ACK


def test_diet_true_mix_move_sanitizes_compact_recall_context(mocker):
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    state = _populated_state()
    state.audio_delta = ["low energy fell 50% (strong)"]
    ev = _ev("MIX_MOVE", state, extra={"moves": ["A_low: flat->killed"]})
    survivors = [
        SimpleNamespace(
            record_id="20260520-2200:7",
            signature=(
                "coach_line | event=MIX_MOVE "
                "| audio_window=audio_window_context[P1=master_global_mix "
                "deckA_audio=attached deckB_audio=stem isolated_decks=true] "
                "| said: That was a great transition."
            ),
        )
    ]

    out = AICoach.build_prompt(ev, recall_moments=survivors, diet=True)

    assert "FROM A PAST SESSION" in out
    assert "deckA_audio=attached" not in out
    assert "deckB_audio=stem" not in out
    assert "isolated_decks=true" not in out
    assert "great transition" not in out.lower()
    assert "audio_window=omitted_untrusted_audio_window" in out
    assert "said: omitted_past_live_outcome_claim" in out
    assert _tokens(out) <= PROMPT_TOKEN_CAP_ACK


# ---------- diet=True drops the | event=TYPE tag ----------


def test_diet_true_drops_event_tag():
    """The diet bracket drops the redundant | event=TYPE marker — task tail
    already encodes the event semantics."""
    ev = _ev("HEARTBEAT")
    out = AICoach.build_prompt(ev, diet=True)
    assert "event=HEARTBEAT" not in out


# ---------- diet=True drops the evidence-corpus footer ----------


def test_diet_true_drops_evidence_corpus_footer():
    """Plan 18-03's evidence-corpus footer is intentionally dropped on diet —
    Gemini relies on the audio Part for grounding instead."""
    ev = _ev("HEARTBEAT")
    snap = {
        "ev": {"HEARTBEAT@30.0": (30.0,), "MIX_MOVE@45.0": (45.0,)},
        "aud": {"rms": (5.0, 6.0)},
    }
    out = AICoach.build_prompt(ev, registry_snapshot=snap, diet=True)
    assert "evidence_corpus[" not in out


# ---------- diet=True on non-ack events raises ValueError ----------


@pytest.mark.parametrize("ev_type", ["PHASE", "TRACK_CHANGE", "MANUAL", "DROP"])
def test_diet_true_raises_value_error_on_non_ack_events(ev_type):
    """diet=True on a non-ack event fails loud — masks dispatch bugs at the
    call site (DJCoHostAgent.llm_node)."""
    ev = _ev(ev_type)
    with pytest.raises(ValueError, match="ACK_ELIGIBLE_EVENTS"):
        AICoach.build_prompt(ev, diet=True)


# ---------- diet=False FULL cap (asserted via test, not enforced at runtime) ----------


def test_full_event_cap_pinned_at_1500(mocker):
    """diet=False on a maximally-populated state stays under 1500 token-proxy.
    Asserted via test only — golden parity is the runtime invariant for
    diet=False, NOT a runtime cap check."""
    mocker.patch("vibemix.state.prompt_builder.time.time", return_value=1000.0)
    state = _populated_state()
    snap = {
        "ev": {
            "HEARTBEAT@30.0": (30.0,),
            "MIX_MOVE@45.0": (45.0,),
            "TRACK_CHANGE@10.0": (10.0,),
        },
        "aud": {"rms": (5.0, 6.0, 7.0), "bpm": (5.0,)},
        "mix": {"phase=drop": (45.0,)},
    }
    for ev_type in ("PHASE", "TRACK_CHANGE", "MANUAL"):
        ev = _ev(
            ev_type,
            state,
            extra=(
                {"prev_phase": "groove", "new_phase": "drop"}
                if ev_type == "PHASE"
                else {"prev_track": "Old Title"}
                if ev_type == "TRACK_CHANGE"
                else {}
            ),
        )
        out = AICoach.build_prompt(ev, registry_snapshot=snap, diet=False)
        assert _tokens(out) <= PROMPT_TOKEN_CAP_FULL, (
            f"FULL cap exceeded on {ev_type}: {_tokens(out)} > {PROMPT_TOKEN_CAP_FULL}"
        )
