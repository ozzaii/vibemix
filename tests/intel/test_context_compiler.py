# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json

from vibemix.intel.context_compiler import compile_suggestion_context, compile_transition_context
from vibemix.intel.transition_scorer import (
    LivePosition,
    SectionRecord,
    TransitionScoringInput,
    score_transition_slate,
)


def _section(section_id: str, track_id: str, role: str, cue_slot: str = "A") -> SectionRecord:
    return SectionRecord(
        section_id=section_id,
        track_id=track_id,
        role=role,
        confidence=0.9,
        start_s=0.0,
        end_s=64.0,
        start_beat=0,
        bar_count=32,
        bpm=128.0,
        camelot="8A",
        energy_mean=50.0,
        cue_slot=cue_slot,
        cue_source="dj",
    )


def _suggestion_transition(
    *,
    candidate_id: str,
    to_track_id: str,
    to_section_id: str,
    semantic: float,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "from_track_id": "t1",
        "to_track_id": to_track_id,
        "from_section_id": "t1#s001",
        "to_section_id": to_section_id,
        "from_role": "outro",
        "to_role": "intro",
        "from_start_s": 224.0,
        "from_end_s": 300.0,
        "to_start_s": 0.0,
        "to_end_s": 80.0,
        "from_bpm": 128.0,
        "to_bpm": 128.0,
        "from_camelot": "8A",
        "to_camelot": "9A",
        "cue_slot": "A",
        "cue_source": "auto",
        "cue_confidence": 0.62,
        "start_in_bars": 8,
        "score": 0.84,
        "confidence": 0.91,
        "semantic_basis": "section_vector",
        "scores": {
            "semantic": semantic,
            "harmonic": 0.88,
            "bpm": 1.0,
            "energy_shape": 0.82,
            "role": 0.95,
            "phrase_alignment": 1.0,
            "cue_operability": 1.0,
            "taste": 0.5,
            "novelty": 0.7,
            "risk_penalty": 0.0,
        },
        "risk_flags": [],
        "reasons": ["section texture is close"],
    }


def test_compile_transition_context_bounds_and_redacts_live_packet() -> None:
    source = _section("t1#s000", "t1", "outro", "F")
    destinations = tuple(_section(f"t{i}#s000", f"t{i}", "intro") for i in range(2, 9))
    slate = score_transition_slate(
        TransitionScoringInput(
            source=source,
            destinations=destinations,
            mode="live",
            live_position=LivePosition(remaining_bars=16, playhead_confidence=0.95),
        ),
        max_candidates=7,
    )

    envelope = compile_transition_context(
        packet_id="ctx_001",
        mode="live",
        intent="live_next_pill",
        current={
            "active_track_id": "t1",
            "filepath": "/Users/ozai/Music/private.wav",
            "vector": [1.0, 0.0],
        },
        candidates=slate,
    )

    assert envelope.schema_version == "intel_context_v1"
    assert len(envelope.candidates) == 5
    assert envelope.allowed_actions == ("select", "hold", "suppress")
    assert "filepath" not in envelope.current
    assert "vector" not in envelope.current
    assert envelope.constraints["raw_vectors_included"] is False
    assert envelope.constraints["strict_claim_validation"] is True
    assert "/Users/ozai" not in json.dumps(envelope.current)
    assert envelope.citation_scope["candidate"] == tuple(
        candidate["candidate_id"] for candidate in envelope.candidates
    )
    assert envelope.citation_scope["claim"] == envelope.claim_ids


def test_compile_transition_context_exposes_score_components_without_vectors() -> None:
    source = _section("t1#s000", "t1", "outro", "F")
    destination = _section("t2#s000", "t2", "intro", "A")
    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(destination,))
    )

    envelope = compile_transition_context(
        packet_id="ctx_001",
        mode="prep",
        intent="transition_slate",
        current={"active_track_id": "t1"},
        candidates=slate,
    )

    candidate = envelope.candidates[0]
    assert candidate["candidate_id"] == "tr_001"
    assert candidate["recommended_cue_slot"] == "A"
    assert candidate["from_role"] == "outro"
    assert candidate["to_role"] == "intro"
    assert candidate["from_start_s"] == 0.0
    assert candidate["to_start_s"] == 0.0
    assert candidate["from_camelot"] == "8A"
    assert candidate["to_camelot"] == "8A"
    assert "semantic" in candidate["scores"]
    assert candidate["move_grade"]["slug"] in {"clean", "sexy", "bomb", "lit_aff"}
    assert candidate["move_grade"]["deserved"] is True
    assert "vector" not in candidate
    assert envelope.allowed_actions == ("select", "hold", "suppress", "ask")
    assert {claim["type"] for claim in envelope.claim_summary} >= {
        "track_identity",
        "transition_fit",
        "section_role",
        "section_boundary",
        "harmonic_fit",
        "tempo_fit",
        "energy_shape",
        "phrase_fit",
        "cue_operability",
        "cue_slot",
        "move_grade",
    }
    role_claims = [claim for claim in envelope.claim_summary if claim["type"] == "section_role"]
    assert {(claim["subject_id"], claim["value"]) for claim in role_claims} >= {
        ("t1#s000", "outro"),
        ("t2#s000", "intro"),
    }
    identity_claims = [
        claim for claim in envelope.claim_summary if claim["type"] == "track_identity"
    ]
    assert {(claim["subject_id"], claim["value"]) for claim in identity_claims} >= {("t2", "t2")}


def test_compile_transition_context_issues_grade_progress_claim_from_current() -> None:
    source = _section("t1#s000", "t1", "outro", "F")
    destination = _section("t2#s000", "t2", "intro", "A")
    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(destination,))
    )

    envelope = compile_transition_context(
        packet_id="ctx_001",
        mode="live",
        intent="live_next_pill",
        current={
            "active_track_id": "t1",
            "grade_progress": {
                "streak": 3,
                "total_xp": 200,
                "last_xp": 100,
                "earned": True,
                "heat": 100,
                "level": 2,
                "level_up": True,
                "levels_gained": 1,
            },
        },
        candidates=slate,
    )

    progress_claims = [
        claim for claim in envelope.claim_summary if claim["type"] == "grade_progress"
    ]
    assert len(progress_claims) == 1
    claim = progress_claims[0]
    assert claim["subject_id"] == "live_session"
    assert claim["value"] == 3
    assert claim["unit"] == "streak"
    assert "combo x3" in claim["allowed_phrases"]
    assert "deserved +100 xp" in claim["allowed_phrases"]
    assert "level up" in claim["allowed_phrases"]
    assert "lv 2" in claim["allowed_phrases"]
    assert "total_xp:200" in claim["reason_codes"]
    assert "level:2" in claim["reason_codes"]
    assert "level_up:true" in claim["reason_codes"]
    assert "levels_gained:1" in claim["reason_codes"]


def test_compile_suggestion_context_filters_candidates_with_private_identifiers() -> None:
    suggestion = {
        "transition": _suggestion_transition(
            candidate_id="tr_001",
            to_track_id="/Users/ozai/Music/private.wav",
            to_section_id="/Users/ozai/Music/private.wav#s000",
            semantic=0.92,
        )
    }

    envelope = compile_suggestion_context(
        packet_id="ctx_live_private_candidate",
        current={"active_track_id": "t1"},
        suggestion=suggestion,
    )

    assert envelope.candidates == ()
    assert envelope.claim_summary == ()
    assert "/Users/ozai" not in json.dumps(
        {
            "current": envelope.current,
            "candidates": envelope.candidates,
            "claims": envelope.claim_summary,
            "citation_scope": envelope.citation_scope,
        }
    )


def test_compile_suggestion_context_applies_cap_after_private_candidate_filter() -> None:
    suggestion = {
        "transition_alternatives": (
            {
                "track_id": "/Users/ozai/Music/private.wav",
                "transition": _suggestion_transition(
                    candidate_id="tr_001",
                    to_track_id="/Users/ozai/Music/private.wav",
                    to_section_id="/Users/ozai/Music/private.wav#s000",
                    semantic=0.95,
                ),
            },
            {
                "track_id": "t2",
                "transition": _suggestion_transition(
                    candidate_id="tr_002",
                    to_track_id="t2",
                    to_section_id="t2#s000",
                    semantic=0.92,
                ),
            },
        )
    }

    envelope = compile_suggestion_context(
        packet_id="ctx_live_safe_after_private",
        current={"active_track_id": "t1"},
        suggestion=suggestion,
        max_candidates=1,
    )

    assert len(envelope.candidates) == 1
    assert envelope.candidates[0]["to_track_id"] == "t2"
    assert "/Users/ozai" not in json.dumps(envelope.candidates)


def test_compile_transition_context_blocks_exact_timing_when_slate_has_none() -> None:
    source = _section("t1#s000", "t1", "outro", "F")
    destination = _section("t2#s000", "t2", "intro", "A")
    slate = score_transition_slate(
        TransitionScoringInput(source=source, destinations=(destination,), mode="prep")
    )

    envelope = compile_transition_context(
        packet_id="ctx_001",
        mode="prep",
        intent="transition_slate",
        current={},
        candidates=slate,
    )

    assert envelope.constraints["exact_timing_allowed"] is False
    assert envelope.confidence_policy["exact_timing_allowed"] is False
    assert "bars_until_event" not in {claim["type"] for claim in envelope.claim_summary}


def test_compile_suggestion_context_from_live_pill_shortlist() -> None:
    suggestion = {
        "track_id": "t2",
        "title": "Candidate",
        "artist": "Artist",
        "similarity": 0.91,
        "why": "similar vibe",
        "camelot": "9A",
        "bpm": 128.0,
        "transition_alternatives": (
            {
                "candidate_id": "tr_001",
                "track_id": "t2",
                "selected": True,
                "transition": _suggestion_transition(
                    candidate_id="tr_001",
                    to_track_id="t2",
                    to_section_id="t2#s000",
                    semantic=0.92,
                ),
            },
            {
                # Duplicate scorer-local ids are normalized by the compiler.
                "candidate_id": "tr_001",
                "track_id": "t3",
                "selected": False,
                "transition": _suggestion_transition(
                    candidate_id="tr_001",
                    to_track_id="t3",
                    to_section_id="t3#s000",
                    semantic=0.86,
                ),
            },
        ),
    }

    envelope = compile_suggestion_context(
        packet_id="ctx_live_001",
        current={
            "active_track_id": "t1",
            "filepath": "/Users/ozai/private.wav",
            "vector": [1.0, 0.0],
            "source_context": {
                "track_id": "t1",
                "position_s": 216.0,
                "playhead_confidence": 0.85,
                "source_loop_recent": False,
                "lookahead_allowed": True,
                "section_clock": "playhead",
                "current_section": {
                    "section_id": "t1#s000",
                    "track_id": "t1",
                    "role": "groove",
                    "confidence": 0.9,
                    "start_s": 0.0,
                    "end_s": 224.0,
                },
                "next_section": {
                    "section_id": "t1#s001",
                    "track_id": "t1",
                    "role": "outro",
                    "confidence": 0.9,
                    "start_s": 224.0,
                    "end_s": 300.0,
                },
                "bars_to_current_section_end": 4,
                "bars_to_next_section_start": 4,
            },
        },
        suggestion=suggestion,
    )

    assert envelope.mode == "live"
    assert envelope.intent == "live_next_pill"
    assert [candidate["candidate_id"] for candidate in envelope.candidates] == [
        "tr_001",
        "tr_002",
    ]
    assert [candidate["to_track_id"] for candidate in envelope.candidates] == ["t2", "t3"]
    assert envelope.candidates[0]["scores"]["semantic"] == 0.92
    assert envelope.candidates[0]["recommended_cue_source"] == "auto"
    assert envelope.candidates[0]["recommended_cue_confidence"] == 0.62
    assert "filepath" not in envelope.current
    assert "vector" not in envelope.current
    assert envelope.current["source_context"]["current_section"]["section_id"] == "t1#s000"
    assert "t1#s000" in envelope.citation_scope["section"]
    assert envelope.constraints["raw_vectors_included"] is False
    assert envelope.constraints["raw_audio_included"] is False
    assert envelope.constraints["strict_claim_validation"] is True
    claim_types = {claim["type"] for claim in envelope.claim_summary}
    assert {"semantic_match", "cue_slot", "bars_until_event", "current_position"} <= claim_types
    section_roles = {
        (claim["subject_id"], claim["value"])
        for claim in envelope.claim_summary
        if claim["type"] == "section_role"
    }
    assert ("t1#s000", "groove") in section_roles
    source_timing_claims = [
        claim
        for claim in envelope.claim_summary
        if claim["type"] == "bars_until_event" and claim["subject_id"] in {"t1#s000", "t1#s001"}
    ]
    assert {claim["value"] for claim in source_timing_claims} == {4}


def test_compile_suggestion_context_sanitizes_nonfinite_and_nested_private_payloads() -> None:
    transition = _suggestion_transition(
        candidate_id="tr_001",
        to_track_id="t2",
        to_section_id="t2#s000",
        semantic=float("nan"),
    )
    transition.update(
        {
            "from_bpm": float("inf"),
            "cue_confidence": float("inf"),
            "start_in_bars": float("nan"),
            "score": float("inf"),
            "confidence": float("nan"),
            "scores": {
                **transition["scores"],
                "semantic": float("nan"),
                "harmonic": float("inf"),
            },
        }
    )
    envelope = compile_suggestion_context(
        packet_id="ctx_live_bad_numbers",
        current={
            "active_track_id": "t1",
            "source_context": {
                "track_id": "t1",
                "position_s": float("inf"),
                "playhead_confidence": float("nan"),
                "debug_path": "/Users/ozai/Music/private.wav",
                "raw_audio": [0, 1, 2],
                "current_section": {
                    "section_id": "t1#s000",
                    "track_id": "t1",
                    "role": "groove",
                    "confidence": 0.9,
                    "start_s": 0.0,
                    "end_s": 224.0,
                    "local_path": "/Users/ozai/Music/private.wav",
                },
            },
        },
        suggestion={"transition": transition},
    )

    candidate = envelope.candidates[0]
    assert candidate["from_bpm"] is None
    assert candidate["recommended_cue_confidence"] is None
    assert candidate["start_in_bars"] is None
    assert candidate["score"] == 0.0
    assert candidate["confidence"] == 0.0
    assert candidate["scores"]["semantic"] == 0.5
    assert candidate["scores"]["harmonic"] == 0.5
    assert envelope.constraints["exact_timing_allowed"] is False
    assert "current_position" not in {claim["type"] for claim in envelope.claim_summary}

    serialized = json.dumps(
        {
            "current": envelope.current,
            "candidates": envelope.candidates,
            "claims": envelope.claim_summary,
        },
        sort_keys=True,
    )
    assert "/Users/" not in serialized
    assert "raw_audio" not in serialized
    assert "NaN" not in serialized
    assert "Infinity" not in serialized
