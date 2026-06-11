# SPDX-License-Identifier: Apache-2.0
"""Steer-register contract — the hype-cell coach-language leak fix.

Fleet-measured 2026-06-10 (36-run persona wave, dj-sim-wave-20260610
FLEET-FEEDBACK-REPORT.md): the per-turn task tails in prompt_builder are
written in the coach register ("Lead with the instruction…") and override the
HYPE_PRO cell by recency — hype users heard patronizing coaching
(would-use-again 2.2/10) while the per-line judge scored those same lines the
campaign's best (friend 2.26). The fix keeps both instruments happy:

- the default ('coach') register is BYTE-IDENTICAL to the measured steers —
  the 2026-06-09/10 bench campaign's numbers stay pinned;
- the 'peer' register (HYPE_PRO / HYPE_BEGINNER cells only) voices the SAME
  grounded receipt as a peer call — citation copying, deck gates, and the
  single-space silence contract identical, only the register changes.
"""

from __future__ import annotations

from vibemix.prompts.matrix import steer_register
from vibemix.state import Event, MusicState
from vibemix.state.prompt_builder import AICoach

ENERGY_RECEIPT = (
    "Energy-read receipt: source=master_mix. The master-mix read points "
    "toward holding the groove steady. Copy these citations exactly: "
    "[energy:master_read=audio_groove_12_abcd1234]."
)


def _grounded_state(*, bpm: float = 128.0, rms: float = 0.06) -> MusicState:
    ms = MusicState()
    ms.audible = True
    ms.bpm = bpm
    ms.rms = rms
    ms.bands = {"sub": 0.25, "low": 0.30, "mid": 0.25, "high": 0.20}
    ms.phase = "drop"
    return ms


def _phase_receipt_event() -> Event:
    return Event(
        "PHASE",
        _grounded_state(),
        extra={
            "prev_phase": "build",
            "new_phase": "drop",
            "energy_read_voice_line": ENERGY_RECEIPT,
        },
    )


def _mix_move_event() -> Event:
    return Event(
        "MIX_MOVE",
        _grounded_state(),
        extra={"moves": ["A_low: flat→killed (big twist)"]},
    )


def _heartbeat_event(extra: dict | None = None) -> Event:
    return Event("HEARTBEAT", _grounded_state(), extra=extra or {})


# =========================================================================== #
# matrix.steer_register — the (skill, mode) → register map                     #
# =========================================================================== #


def test_steer_register_cell_mapping():
    """'peer' only for the hype cells with a distinct hype identity.
    ("intermediate", "hype") IS SVEN_COACH_IDENTITY (pinned verbatim), so it
    keeps the coach register; a foreign value falls back to 'coach' so a
    corrupt config can never change what the brain is asked to do."""
    assert steer_register("pro", "hype") == "peer"
    assert steer_register("beginner", "hype") == "peer"
    assert steer_register("intermediate", "hype") == "coach"
    for skill in ("beginner", "intermediate", "pro"):
        assert steer_register(skill, "coach") == "coach"
    assert steer_register("weird", "hype") == "coach"
    assert steer_register("pro", "weird") == "coach"
    # Normalization parity with build_system_instruction (lower+strip): a
    # config that selects the HYPE_PRO cell can never keep the coach steers.
    assert steer_register("PRO", "hype") == "peer"
    assert steer_register(" pro ", " HYPE ") == "peer"


# =========================================================================== #
# Default register == 'coach' == today's measured bytes                        #
# =========================================================================== #


def test_default_register_is_coach_byte_identical():
    """task_for_event with no kwarg and with steer_register='coach' produce
    the SAME bytes — the measured bench-campaign steers are the default and
    every existing caller (bench/assemble.py, learn) is untouched."""
    for ev in (_phase_receipt_event(), _mix_move_event(), _heartbeat_event()):
        assert AICoach.task_for_event(ev) == AICoach.task_for_event(
            ev, steer_register="coach"
        )


# =========================================================================== #
# PHASE + receipt — peer voices the call, contracts identical                  #
# =========================================================================== #


def test_phase_receipt_peer_voices_call_keeps_contracts():
    coach = AICoach.task_for_event(_phase_receipt_event())
    peer = AICoach.task_for_event(_phase_receipt_event(), steer_register="peer")

    assert "Lead with its instruction" in coach
    assert "Lead with its instruction" not in peer
    assert "what to hold" not in peer
    # The SAME receipt + grounding contract ride the peer register.
    assert "Energy-read receipt: source=master_mix" in peer
    assert "copy the receipt's citations exactly" in peer
    assert peer.endswith("output a single space to stay silent.")


# =========================================================================== #
# MIX_MOVE — peer keeps every deck/effect gate, drops the instruction lead     #
# =========================================================================== #


def test_mix_move_peer_keeps_deck_and_effect_gates():
    coach = AICoach.task_for_event(_mix_move_event())
    peer = AICoach.task_for_event(_mix_move_event(), steer_register="peer")

    assert "Lead with the instruction" in coach
    assert "Lead with the instruction" not in peer
    for contract in (
        "transition_block/watch => do NOT call this",
        "Claim a sonic effect of the move only when move_effect_context",
        "name it in passing at most",
    ):
        assert contract in peer, f"peer MIX_MOVE lost contract: {contract}"
    assert peer.endswith("output a single space to stay silent.")


# =========================================================================== #
# HEARTBEAT — peer makes a forward call, keeps grounding + silence             #
# =========================================================================== #


def test_heartbeat_peer_forward_call_keeps_grounding():
    coach = AICoach.task_for_event(_heartbeat_event())
    peer = AICoach.task_for_event(_heartbeat_event(), steer_register="peer")

    assert "a move to set up" in coach
    assert "a move to set up" not in peer
    assert "Ground it in the audio you just heard." in peer
    assert "copy an exact bracket from grounding_refs" in peer
    assert peer.endswith("space to stay silent.")


def test_heartbeat_energy_receipt_peer_register():
    """The energy-receipt hint (the strongest of the measured recency
    overrides) re-voices as a peer read; citations + silence identical."""
    ev = _heartbeat_event(extra={"energy_read_voice_line": ENERGY_RECEIPT})
    coach = AICoach.task_for_event(ev)
    peer = AICoach.task_for_event(ev, steer_register="peer")

    assert "say that one nudge in your own words" in coach
    assert "say that one nudge in your own words" not in peer
    assert "copy the receipt's citations exactly" in peer
    assert peer.endswith("output a single space to stay silent.")


# =========================================================================== #
# build_prompt threads the register (full + diet paths)                        #
# =========================================================================== #


def test_build_prompt_threads_steer_register():
    prompt = AICoach.build_prompt(_phase_receipt_event(), steer_register="peer")
    assert "Lead with its instruction" not in prompt
    assert "copy the receipt's citations exactly" in prompt

    diet_peer = AICoach.build_prompt(
        _heartbeat_event(), diet=True, steer_register="peer"
    )
    assert "a move to set up" not in diet_peer


# =========================================================================== #
# dj_cohost resolution — env path + the explicit lens wins                     #
# =========================================================================== #


def test_resolve_steer_register_env_paths(monkeypatch):
    from vibemix.agent import dj_cohost as dc

    monkeypatch.setattr(
        "vibemix.runtime.settings.read_shared_lens",
        lambda store, default=None: None,
    )
    monkeypatch.setattr("vibemix.runtime.config_store.load_config", lambda: None)

    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "pro")
    monkeypatch.setenv("VIBEMIX_MODE", "hype")
    assert dc._resolve_steer_register() == "peer"

    monkeypatch.setenv("VIBEMIX_MODE", "coach")
    assert dc._resolve_steer_register() == "coach"

    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "intermediate")
    monkeypatch.setenv("VIBEMIX_MODE", "hype")
    assert dc._resolve_steer_register() == "coach"


def test_resolve_steer_register_lens_wins(monkeypatch):
    """The persisted lens is the user's EXPLICIT persona choice — it wins over
    the VIBEMIX_MODE env, mirroring _resolve_prompt_cell (LENS-02)."""
    from vibemix.agent import dj_cohost as dc

    monkeypatch.setenv("VIBEMIX_SKILL_LEVEL", "pro")
    monkeypatch.setenv("VIBEMIX_MODE", "coach")
    monkeypatch.setattr("vibemix.runtime.config_store.load_config", lambda: None)

    monkeypatch.setattr(
        "vibemix.runtime.settings.read_shared_lens",
        lambda store, default=None: "hype",
    )
    assert dc._resolve_steer_register() == "peer"

    monkeypatch.setattr(
        "vibemix.runtime.settings.read_shared_lens",
        lambda store, default=None: "tutor",
    )
    assert dc._resolve_steer_register() == "coach"
