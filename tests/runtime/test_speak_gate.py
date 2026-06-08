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
