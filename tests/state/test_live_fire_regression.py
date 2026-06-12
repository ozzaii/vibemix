"""Regression pins for the 11 real live_claim_guard fires (2026-06-07..11).

This file is the direct measure of Kaan's complaint ("Sven is always blocked
by the anti-slop guard"): every false-positive fire must SPEAK, every
separable claim must TRIM keeping the model's own words, and every true
positive must hold WITHOUT a canned disclaimer ever reaching speech. The
fixture carries the verbatim raw lines plus 8 true-positive controls that
must keep holding — freeing Sven must not reopen the fabrication classes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibemix.state.deck_state import DeckState
from vibemix.state.deck_context import (
    LIVE_CANDIDATE_HELD_REPLY,
    LIVE_COACHING_ADVICE_HELD_REPLY,
    LIVE_EVENT_WITNESS_HELD_REPLY,
    LIVE_MOVE_EFFECT_HELD_REPLY,
    LIVE_SPECTRAL_CLAIM_HELD_REPLY,
    LIVE_TRANSITION_HELD_REPLY,
    apply_live_claim_guard,
)
from vibemix.state.music_state import MusicState

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "live_fires_2026_06_07_11.json").read_text()
)
FIRES = {f["id"]: f for f in FIXTURE["fires"]}
TP_CONTROLS = {c["id"]: c for c in FIXTURE["tp_controls"]}

CANNED_REPLIES = (
    LIVE_TRANSITION_HELD_REPLY,
    LIVE_CANDIDATE_HELD_REPLY,
    LIVE_MOVE_EFFECT_HELD_REPLY,
    LIVE_COACHING_ADVICE_HELD_REPLY,
    LIVE_SPECTRAL_CLAIM_HELD_REPLY,
    LIVE_EVENT_WITNESS_HELD_REPLY,
)


def _state_from(spec: dict) -> tuple[MusicState, tuple[str, ...]]:
    state = MusicState()
    state.rms = float(spec.get("rms", 0.05))
    state.bands = dict(spec.get("bands", {"sub": 0.5, "low": 0.3, "mid": 0.15, "high": 0.05}))
    state.audible = state.rms >= 0.01
    state.deck_state = DeckState(decks={})
    return state, tuple(spec.get("moves", ()))


def _run(fire: dict, *, audio_delta_items: list[str] | None = None):
    state, moves = _state_from(fire["state"])
    return apply_live_claim_guard(
        fire["raw_text"],
        state,
        moves,
        audio_delta_items=audio_delta_items,
        event_type=fire["event"],
    )


# --- the false positives: good coach lines the old guard silenced ----------

@pytest.mark.parametrize("fire_id", ["fire01", "fire02", "fire03", "fire05", "fire10"])
def test_blocked_policy_future_directives_speak(fire_id: str) -> None:
    """Deck-pairing vocabulary in a future/imperative clause carries no claim —
    'when you transition', 'before you slide the next layer in' must speak."""
    fire = FIRES[fire_id]
    result = _run(fire)
    assert result.corrected is False, (
        f"{fire_id} still held: policy={result.policy} reason={result.reason}\n"
        f"raw: {fire['raw_text']}\nwhy this is a FP: {fire['why']}"
    )
    assert result.text == fire["raw_text"]


@pytest.mark.parametrize("fire_id", ["fire06", "fire09"])
def test_band_intensity_fires_pass_the_ladder(fire_id: str) -> None:
    """The direction-blind band-intensity class is no longer a ladder concern;
    the ladder must pass these directives untouched (the dj_cohost boundary
    speaks them with a live_claim_observation — pinned in tests/agent)."""
    fire = FIRES[fire_id]
    result = _run(fire)
    assert result.corrected is False, (
        f"{fire_id} held by ladder: policy={result.policy} reason={result.reason}"
    )


# --- the separable claims: trim keeps the model's own words ----------------

@pytest.mark.parametrize("fire_id", ["fire04", "fire08"])
def test_separable_claims_trim_keeping_model_words(fire_id: str) -> None:
    fire = FIRES[fire_id]
    result = _run(fire)
    assert result.corrected is True
    assert result.emit_corrected is True, (
        f"{fire_id} should trim (emit model words), got policy={result.policy}"
    )
    assert result.text.strip()
    assert result.text != fire["raw_text"]
    for canned in CANNED_REPLIES:
        assert canned not in result.text


# --- the true positives: hold, silently, no canned speech ------------------

@pytest.mark.parametrize("fire_id", ["fire07", "fire11"])
def test_true_positive_fires_hold_without_canned_speech(fire_id: str) -> None:
    fire = FIRES[fire_id]
    result = _run(fire)
    assert result.corrected is True
    assert result.emit_corrected is False
    assert result.speakable is False, (
        f"{fire_id}: a hold must be speakable=False so the boundary never "
        f"voices the held text (policy={result.policy})"
    )


def test_fire11_spectral_hold_releases_with_offered_rose_delta() -> None:
    """The one spectral keeper collateral: a clear mid rise offered in the
    packet licenses 'those new mids' even while the band sits below floor."""
    fire = FIRES["fire11"]
    result = _run(fire, audio_delta_items=[fire["passes_with_delta"]])
    assert result.corrected is False, (
        f"rose-delta escape failed: policy={result.policy} reason={result.reason}"
    )


# --- the adversarial controls: freeing Sven must not reopen these ----------

@pytest.mark.parametrize("control_id", sorted(TP_CONTROLS))
def test_tp_controls_keep_holding(control_id: str) -> None:
    control = TP_CONTROLS[control_id]
    state = MusicState()
    state.rms = 0.05
    state.audible = True
    state.bands = {"sub": 0.5, "low": 0.3, "mid": 0.2, "high": 0.1}
    state.deck_state = DeckState(decks={})
    state.vocal_active = False
    # tp08 pins the cold-state (requires_more_evidence) diagnosis hold: no moves.
    moves: tuple[str, ...] = () if control_id in {"tp07", "tp08"} else ("A eq low cut",)
    result = apply_live_claim_guard(
        control["raw_text"],
        state,
        moves,
        event_type=control["event"],
    )
    assert result.corrected is True, (
        f"{control_id} now speaks — fabrication class reopened!\n"
        f"line: {control['raw_text']}\nwhy it must hold: {control['why']}"
    )
    assert result.emit_corrected is False
    assert result.speakable is False
