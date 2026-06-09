# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.runtime.speak_gate import (
    decide_speak_gate,
    event_speak_fingerprint,
    interruption_worthiness,
)
from vibemix.state import Event, MusicState


def _event(
    event_type: str,
    extra: dict | None = None,
    *,
    bands: dict[str, float] | None = None,
    state_values: dict[str, object] | None = None,
) -> Event:
    state = MusicState()
    if bands is not None:
        state.bands = bands
    for key, value in (state_values or {}).items():
        setattr(state, key, value)
    return Event(event_type, state, extra=extra or {})


def test_plain_heartbeat_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("HEARTBEAT"))

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_plain_phase_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("PHASE", {"prev_phase": "build", "new_phase": "low"}))

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_plain_layer_arrival_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("LAYER_ARRIVAL", {"band": "high"}))

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_manual_heartbeat_reaches_sven() -> None:
    decision = decide_speak_gate(_event("HEARTBEAT"), manual=True)

    assert decision.verdict == "speak"
    assert decision.reason == "human_or_manual"


def test_kaan_spoke_heartbeat_reaches_sven() -> None:
    decision = decide_speak_gate(_event("HEARTBEAT"), kaan_just_spoke=True)

    assert decision.verdict == "speak"
    assert decision.reason == "human_or_manual"


def test_grounded_heartbeat_payload_still_needs_interruption_worthiness() -> None:
    decision = decide_speak_gate(
        _event("HEARTBEAT", {"set_progress_voice_line": "[mix:set_progress=next]"}),
    )

    assert decision.verdict == "silent"
    assert decision.reason == "below_worthiness"
    assert decision.worthiness is not None
    assert decision.worthiness < 0.38


def test_grounded_heartbeat_payload_reaches_sven_when_audio_builds() -> None:
    decision = decide_speak_gate(
        _event(
            "HEARTBEAT",
            {"set_progress_voice_line": "[mix:set_progress=next]"},
            state_values={"audible": True, "rms": 0.12, "buildup_score": 0.85},
        ),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"
    assert decision.worthiness is not None
    assert decision.worthiness >= 0.38


def test_energy_read_heartbeat_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event(
            "HEARTBEAT",
            {"energy_read_voice_line": "[energy:master_read=audio_build_4]"},
            state_values={
                "audible": True,
                "rms": 0.12,
                "buildup_score": 0.50,
                "audio_delta": ["master energy rose 42%"],
            },
        ),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_grounded_phase_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event(
            "PHASE",
            {
                "prev_phase": "groove",
                "new_phase": "build",
                "judge_evidence_line": "[judge:transition=clean]",
            },
            state_values={"audible": True, "rms": 0.12},
        ),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_structural_events_keep_existing_speech_path() -> None:
    decision = decide_speak_gate(
        _event(
            "MIX_MOVE",
            {"moves": ["eq_low:A"]},
            state_values={"audible": True, "rms": 0.12},
        )
    )

    assert decision.verdict == "speak"
    assert decision.reason == "event_priority"


def test_same_payload_across_event_types_suppressed_as_repeat() -> None:
    """Broken-record guard (default-slop-sweep finding): the SAME deterministic
    spoken line ("Artist - Title next.") attached to two different event types
    must not be voiced twice. The full event fingerprints differ (type= prefix +
    bands= segment), so the exact-match repeat check misses it — only a
    type-independent payload check catches the broken record."""
    line = "Daft Punk - Around the World next."
    spoken_phase = _event(
        "PHASE",
        {"prev_phase": "build", "new_phase": "peak", "next_suggestion_voice_line": line},
        state_values={"audible": True, "rms": 0.12, "buildup_score": 0.5},
    )
    # That PHASE line was just spoken -> its fingerprint is in recent memory.
    recent = (event_speak_fingerprint(spoken_phase),)
    # A later TRANSITION_OPPORTUNITY carries the SAME suggestion line and would
    # otherwise reach 'speak' (priority payload + audible clears the floor).
    transition = _event(
        "TRANSITION_OPPORTUNITY",
        {"a_side": "5A", "a_camelot": "5A", "b_side": "8B", "b_camelot": "8B", "clash": "low", "next_suggestion_voice_line": line},
        state_values={"audible": True, "rms": 0.12},
    )
    decision = decide_speak_gate(transition, recent_fingerprints=recent)
    assert decision.verdict == "silent"
    assert decision.reason == "repeat_of_recent"


def test_different_payload_across_event_types_still_speaks() -> None:
    """Guard rail: a DIFFERENT spoken line across event types is NOT muted by the
    payload-repeat check — only a byte-identical line is a broken record."""
    spoken_phase = _event(
        "PHASE",
        {"prev_phase": "build", "new_phase": "peak", "next_suggestion_voice_line": "Track A next."},
        state_values={"audible": True, "rms": 0.12, "buildup_score": 0.5},
    )
    recent = (event_speak_fingerprint(spoken_phase),)
    transition = _event(
        "TRANSITION_OPPORTUNITY",
        {"a_side": "5A", "a_camelot": "5A", "b_side": "8B", "b_camelot": "8B", "clash": "low", "next_suggestion_voice_line": "Track B next."},
        state_values={"audible": True, "rms": 0.12},
    )
    decision = decide_speak_gate(transition, recent_fingerprints=recent)
    assert decision.verdict == "speak"


def test_priority_event_in_dead_air_holds_below_floor() -> None:
    decision = decide_speak_gate(_event("MIX_MOVE", {"moves": ["eq_low:A"]}))

    assert decision.verdict == "hold"
    assert decision.reason == "priority_below_floor"
    assert decision.worthiness is not None
    assert decision.worthiness < 0.24


def test_priority_event_without_detector_payload_holds() -> None:
    for event_type in ("KICK_SWAP", "KICK_DENSITY_SHIFT"):
        decision = decide_speak_gate(_event(event_type))

        assert decision.verdict == "hold"
        assert decision.reason == "priority_missing_payload"


def test_spectrum_narration_event_bare_delta_stays_silent() -> None:
    # A spectral delta with no forward-coachable anchor is pure narration —
    # measured friend ~0.13 / should_NOT ~97% (BENCH-AUDIT-2026-06-08). The gate
    # silences it, the same anti-slop rule the describe-bank set follows.
    cases = {
        "KICK_SWAP": {"prev_centroid_hz": 120.0, "new_centroid_hz": 180.0, "delta_hz": 60.0},
        "KICK_DENSITY_SHIFT": {"prev_density": 6.0, "new_density": 4.5, "delta": -1.5},
        "DISTORTION_CLIMB": {"chain_position": "master", "distortion_db": 6.0},
        "ACID_LINE_ENTRY": {"formant_hz": 800.0, "resonance_q": 4.0},
    }
    for event_type, extra in cases.items():
        decision = decide_speak_gate(_event(event_type, extra))
        assert decision.verdict == "silent", event_type
        assert decision.reason == "spectrum_narration_no_anchor", event_type


def test_spectrum_narration_event_with_move_anchor_reaches_sven() -> None:
    # A spectrum event paired with a real controller move has something forward
    # to coach — it earns the line.
    decision = decide_speak_gate(
        _event(
            "KICK_DENSITY_SHIFT",
            {
                "prev_density": 6.0,
                "new_density": 4.5,
                "delta": -1.5,
                "moves": ["A_low: flat->kill (big twist)"],
            },
        )
    )

    assert decision.verdict == "speak"
    assert decision.reason == "event_priority"


def test_spectrum_narration_event_with_grounded_voice_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event(
            "KICK_SWAP",
            {
                "prev_centroid_hz": 120.0,
                "new_centroid_hz": 180.0,
                "delta_hz": 60.0,
                "next_suggestion_voice_line": "[track:track-42] [mix:next_suggestion=track-42]",
            },
        )
    )

    assert decision.verdict == "speak"
    assert decision.reason == "event_priority"


def test_gate_classifies_every_known_event_type_no_silent_slop_hole() -> None:
    # Coverage guard for the proven lever (friend = f(should_NOT %); the gate is
    # the only lever). Every event type the gate assigns a base worthiness to must
    # be either GATED (silent/hold on a bare payload) or explicitly allow-listed as
    # an intentional bare-speak (a moment grounded by detection). A NEW event type
    # added without classification would bare-pass to speech as soon as live audio
    # nudges worthiness over the priority floor (base 0.20 + audible 0.06 + rms 0.03
    # = 0.29 > 0.24) -- a silent narrator-slop regression. This forces the triage.
    from vibemix.runtime import speak_gate as g

    gated = set(g._DESCRIBE_BANK_EVENT_TYPES) | set(g._PRIORITY_EVENT_REQUIRED_EXTRA_KEYS)
    # DROP (armed by drop prediction) and KEY_CLASH (a deterministic camelot clash)
    # are grounded by detection and are the genuine in-the-moment calls; the live-
    # claim guard still defends an unsupported harmonic claim at the response
    # boundary. MANUAL / KAAN_SPOKE short-circuit before worthiness, so they never
    # carry a base worthiness.
    bare_speak_intentional = {"DROP", "KEY_CLASH"}
    classified = gated | bare_speak_intentional
    unclassified = set(g._EVENT_BASE_WORTHINESS) - classified

    assert unclassified == set(), (
        f"event types with a base worthiness but no gate classification: {sorted(unclassified)} "
        "-- gate each (describe-bank / priority-required / spectrum-narration) or add it to the "
        "intentional bare-speak allow-list with a grounding justification"
    )
    # spectrum-narration only TIGHTENS priority events; it must never widen the
    # speaking surface beyond the priority-required set.
    assert set(g._SPECTRUM_NARRATION_EVENT_TYPES) <= set(g._PRIORITY_EVENT_REQUIRED_EXTRA_KEYS)


def test_every_describe_bank_type_silent_on_bare_payload() -> None:
    from vibemix.runtime import speak_gate as g

    for event_type in g._DESCRIBE_BANK_EVENT_TYPES:
        decision = decide_speak_gate(_event(event_type))
        assert decision.verdict == "silent", event_type
        assert decision.reason == "describe_bank_only", event_type


def test_every_priority_required_type_holds_on_missing_payload() -> None:
    from vibemix.runtime import speak_gate as g

    for event_type in g._PRIORITY_EVENT_REQUIRED_EXTRA_KEYS:
        decision = decide_speak_gate(_event(event_type))
        assert decision.verdict == "hold", event_type
        assert decision.reason == "priority_missing_payload", event_type


def test_intentional_bare_speak_types_speak_on_bare_payload() -> None:
    # The allow-listed grounded moments earn a line even on a bare payload.
    for event_type in ("DROP", "KEY_CLASH"):
        decision = decide_speak_gate(
            _event(event_type, state_values={"audible": True, "rms": 0.12})
        )
        assert decision.verdict == "speak", event_type
        assert decision.reason == "event_priority", event_type


def test_plain_track_change_stays_silent_by_default() -> None:
    decision = decide_speak_gate(_event("TRACK_CHANGE", {"new_track": "B"}))

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_grounded_track_change_payload_reaches_sven() -> None:
    decision = decide_speak_gate(
        _event(
            "TRACK_CHANGE",
            {"next_suggestion_voice_line": "[track:track-42] [mix:next_suggestion=track-42]"},
        ),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_repeat_of_recent_phase_stays_silent() -> None:
    ev = _event(
        "PHASE",
        {
            "prev_phase": "groove",
            "new_phase": "build",
            "judge_evidence_line": "[judge:transition=clean]",
        },
        bands={"sub": 0.26, "low": 0.31, "mid": 0.22, "high": 0.11},
        state_values={"audible": True, "rms": 0.12},
    )
    fingerprint = event_speak_fingerprint(ev)

    decision = decide_speak_gate(ev, recent_fingerprints=(fingerprint,))

    assert decision.verdict == "silent"
    assert decision.reason == "repeat_of_recent"


def test_novel_phase_with_fresh_band_still_speaks() -> None:
    old = _event(
        "PHASE",
        {
            "prev_phase": "groove",
            "new_phase": "build",
            "judge_evidence_line": "[judge:transition=clean]",
        },
        bands={"sub": 0.2, "low": 0.2, "mid": 0.2, "high": 0.2},
        state_values={"audible": True, "rms": 0.12},
    )
    new = _event(
        "PHASE",
        {
            "prev_phase": "groove",
            "new_phase": "build",
            "judge_evidence_line": "[judge:transition=clean]",
        },
        bands={"sub": 0.6, "low": 0.2, "mid": 0.2, "high": 0.2},
        state_values={"audible": True, "rms": 0.12},
    )

    decision = decide_speak_gate(new, recent_fingerprints=(event_speak_fingerprint(old),))

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_empty_recent_fingerprints_preserves_default_gate() -> None:
    decision = decide_speak_gate(
        _event("PHASE", {"new_phase": "build"}),
        recent_fingerprints=(),
    )

    assert decision.verdict == "silent"
    assert decision.reason == "describe_bank_only"


def test_manual_overrides_repeat() -> None:
    ev = _event(
        "PHASE",
        {"new_phase": "build", "judge_evidence_line": "[judge:transition=clean]"},
    )
    fingerprint = event_speak_fingerprint(ev)

    decision = decide_speak_gate(ev, manual=True, recent_fingerprints=(fingerprint,))

    assert decision.verdict == "speak"
    assert decision.reason == "human_or_manual"


def test_track_change_does_not_dedup_against_phase() -> None:
    phase = _event("PHASE", {"new_phase": "build"})
    track_change = _event("TRACK_CHANGE", {"new_track": "Next"})

    assert event_speak_fingerprint(phase) != event_speak_fingerprint(track_change)


def test_interruption_worthiness_rewards_real_heartbeat_audio_trajectory() -> None:
    steady = _event(
        "HEARTBEAT",
        state_values={"audible": True, "rms": 0.12, "buildup_score": 0.0},
    )
    building = _event(
        "HEARTBEAT",
        state_values={"audible": True, "rms": 0.12, "buildup_score": 0.85},
    )

    assert interruption_worthiness(steady) < 0.38
    assert interruption_worthiness(building) >= 0.38


def test_interruption_worthiness_penalizes_recent_speech() -> None:
    ev = _event(
        "HEARTBEAT",
        state_values={
            "audible": True,
            "rms": 0.12,
            "buildup_score": 0.85,
            "last_kaan_spoke_at": 100.0,
        },
    )

    assert interruption_worthiness(ev, now_s=104.0) < interruption_worthiness(ev, now_s=140.0)


# --------------------------------------------------------------------------- #
# Energy-nudge novelty guard (2026-06-09 iter2 judge finding)                  #
# --------------------------------------------------------------------------- #

_RECEIPT_STEADY_A = (
    "Energy-read receipt: source=master_mix. The master-mix read points toward "
    "holding the groove steady. Live deltas: sub energy rose 0.18 to 0.42. "
    "Use this as one forward coaching nudge scoped to master-mix energy. "
    "Copy these citations exactly: [energy:master_read=audio_groove_37_3937c6c8]."
)
_RECEIPT_STEADY_B = (
    "Energy-read receipt: source=master_mix. The master-mix read points toward "
    "holding the groove steady. Live deltas: mid energy fell 0.31 to 0.22. "
    "Phrase read: current section feels like groove. "
    "Use this as one forward coaching nudge scoped to master-mix energy. "
    "Copy these citations exactly: [energy:master_read=audio_groove_64_f00aa894]."
)
_RECEIPT_LIFT = (
    "Energy-read receipt: source=master_mix. The master-mix read points toward "
    "lifting the next phrase without rushing it. Live deltas: high energy rose "
    "0.12 to 0.30. Use this as one forward coaching nudge scoped to master-mix "
    "energy. Copy these citations exactly: "
    "[energy:master_read=audio_build_91_77aa00bb]."
)


def _phase_with_receipt(receipt: str, *, prev: str, new: str, bands: dict | None = None):
    return _event(
        "PHASE",
        {"prev_phase": prev, "new_phase": new, "energy_read_voice_line": receipt},
        bands=bands,
        state_values={"audible": True, "rms": 0.12},
    )


def test_same_energy_nudge_different_digest_suppressed_as_repeat() -> None:
    """Iter2 measured hole (2026-06-09 OpenRouter judge on the receipt-wire
    replay): all 5 spoken lines voiced the SAME 'holding the groove steady'
    nudge — every receipt carried fresh deltas/digest/bands, so neither the
    exact-match guard nor the cross-type guard fired and the listener heard
    the same advice five times (earned_not_constant 0.2). The same READ is
    worth one line; re-speaking is earned only when the read CHANGES."""
    spoken = _phase_with_receipt(
        _RECEIPT_STEADY_A,
        prev="build",
        new="drop",
        bands={"sub": 0.4, "low": 0.3, "mid": 0.2, "high": 0.1},
    )
    same_nudge_fresh_context = _phase_with_receipt(
        _RECEIPT_STEADY_B,
        prev="drop",
        new="groove",
        bands={"sub": 0.1, "low": 0.2, "mid": 0.4, "high": 0.3},
    )

    decision = decide_speak_gate(
        same_nudge_fresh_context,
        recent_fingerprints=(event_speak_fingerprint(spoken),),
    )

    assert decision.verdict == "silent"
    assert decision.reason == "repeat_of_recent"


def test_changed_energy_nudge_still_speaks() -> None:
    """A CHANGED read earns a line: after 'holding steady' was spoken, a
    'lifting the next phrase' receipt passes the gate — novelty is judged on
    the nudge, not on receipt prose."""
    spoken = _phase_with_receipt(_RECEIPT_STEADY_A, prev="build", new="drop")
    changed_read = _phase_with_receipt(_RECEIPT_LIFT, prev="groove", new="build")

    decision = decide_speak_gate(
        changed_read,
        recent_fingerprints=(event_speak_fingerprint(spoken),),
    )

    assert decision.verdict == "speak"
    assert decision.reason == "grounded_voice_payload"


def test_same_energy_nudge_across_event_types_suppressed() -> None:
    """The nudge guard is event-type-blind: a HEARTBEAT that spoke 'holding
    the groove steady' silences a PHASE arriving with the same read."""
    heartbeat_spoken = _event(
        "HEARTBEAT",
        {"energy_read_voice_line": _RECEIPT_STEADY_A},
        state_values={"audible": True, "rms": 0.12},
    )
    phase_same_read = _phase_with_receipt(_RECEIPT_STEADY_B, prev="drop", new="groove")

    decision = decide_speak_gate(
        phase_same_read,
        recent_fingerprints=(event_speak_fingerprint(heartbeat_spoken),),
    )

    assert decision.verdict == "silent"
    assert decision.reason == "repeat_of_recent"


def test_fingerprint_embeds_energy_nudge_segment() -> None:
    """event_speak_fingerprint carries the reduced nudge as its own segment so
    recorded spoken turns expose it to the novelty guard. Receipts without a
    'points toward' clause fall back to the existing full-text payload atom."""
    ev = _phase_with_receipt(_RECEIPT_STEADY_A, prev="build", new="drop")
    segments = event_speak_fingerprint(ev).split("|")
    assert "nudge=holding the groove steady" in segments

    bare = _event(
        "PHASE",
        {
            "prev_phase": "build",
            "new_phase": "drop",
            "energy_read_voice_line": "[energy:master_read=audio_build_4]",
        },
        state_values={"audible": True, "rms": 0.12},
    )
    assert not any(
        seg.startswith("nudge=") for seg in event_speak_fingerprint(bare).split("|")
    )


def test_nudge_atom_round_trips_real_producer_output() -> None:
    """Anti-drift lock (slop-audit residual, 2026-06-09): `_energy_nudge_atom`
    scrapes the receipt PROSE — if build_energy_read_voice_line ever rewords
    its "points toward" clause, the novelty guard dies silently with every
    hardcoded-literal test still green. This feeds a REAL producer receipt
    through the reducer so a template reword reddens here."""
    from vibemix.runtime.energy_read_voice import build_energy_read_voice_line
    from vibemix.state.evidence_registry import EvidenceRegistry

    state = MusicState()
    state.audible = True
    state.phase = "build"
    state.energy_curve = [0.30, 0.30, 0.45, 0.50]  # lifting arc → change nudge
    # (a settling arc no longer yields a receipt at all — iter5 holds the
    # steady/no-info bodies from the voice path entirely)

    line = build_energy_read_voice_line(
        None,
        event_type="PHASE",
        evidence_registry=EvidenceRegistry(),
        state=state,
    )
    assert isinstance(line, str) and "points toward" in line

    ev = _event(
        "PHASE",
        {"prev_phase": "groove", "new_phase": "build", "energy_read_voice_line": line},
        state_values={"audible": True, "rms": 0.12},
    )
    atom = event_speak_fingerprint(ev).split("|")
    nudges = [seg for seg in atom if seg.startswith("nudge=")]
    assert nudges == ["nudge=lifting the next phrase without rushing it"]
