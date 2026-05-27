# SPDX-License-Identifier: Apache-2.0
"""Generate the public INTEL synthetic fixture corpus.

The fixtures are intentionally small and synthetic. They exercise the musical
intelligence contracts without depending on Kaan's library, real audio,
Rekordbox binaries, network calls, or model calls.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"
SEED = "vibemix-intel-fixtures-v1"
VECTOR_512_SEED = 270527

TRACKS = [
    {
        "track_id": "fx-hard-001",
        "title": "Fixture Hard Signal One",
        "artist": "Fixture Lab",
        "genre": "hardtechno",
        "bpm": 180.0,
        "camelot": "8A",
        "duration_s": 288.0,
        "location": "fixture://tracks/fx-hard-001.wav",
        "analysis_source": "synthetic_anlz",
    },
    {
        "track_id": "fx-hard-002",
        "title": "Fixture Hard Signal Two",
        "artist": "Fixture Lab",
        "genre": "hardtechno",
        "bpm": 180.0,
        "camelot": "9A",
        "duration_s": 260.0,
        "location": "fixture://tracks/fx-hard-002.wav",
        "analysis_source": "synthetic_anlz",
    },
    {
        "track_id": "fx-tech-003",
        "title": "Fixture Tool Groove",
        "artist": "Fixture Lab",
        "genre": "techno",
        "bpm": 136.0,
        "camelot": "8A",
        "duration_s": 372.0,
        "location": "fixture://tracks/fx-tech-003.wav",
        "analysis_source": "synthetic_anlz",
    },
    {
        "track_id": "fx-house-004",
        "title": "Fixture Warm House Window",
        "artist": "Fixture Lab",
        "genre": "house",
        "bpm": 126.0,
        "camelot": "8B",
        "duration_s": 334.0,
        "location": "fixture://tracks/fx-house-004.wav",
        "analysis_source": "synthetic_anlz",
    },
    {
        "track_id": "fx-dnb-005",
        "title": "Fixture Double Drop Grid",
        "artist": "Fixture Lab",
        "genre": "drum_and_bass",
        "bpm": 174.0,
        "camelot": "4A",
        "duration_s": 302.0,
        "location": "fixture://tracks/fx-dnb-005.wav",
        "analysis_source": "synthetic_anlz",
    },
    {
        "track_id": "fx-pop-006",
        "title": "Fixture Vocal Hook Risk",
        "artist": "Fixture Lab",
        "genre": "pop",
        "bpm": 122.0,
        "camelot": "5B",
        "duration_s": 214.0,
        "location": "fixture://tracks/fx-pop-006.wav",
        "analysis_source": "synthetic_anlz",
    },
    {
        "track_id": "fx-amb-007",
        "title": "Fixture Ambient Drift",
        "artist": "Fixture Lab",
        "genre": "ambient",
        "bpm": None,
        "camelot": None,
        "duration_s": 420.0,
        "location": "fixture://tracks/fx-amb-007.wav",
        "analysis_source": "synthetic_fallback",
    },
    {
        "track_id": "fx-bad-008",
        "title": "Fixture Malformed Edge",
        "artist": "Fixture Lab",
        "genre": "unknown",
        "bpm": None,
        "camelot": None,
        "duration_s": 64.0,
        "location": "fixture://tracks/fx-bad-008.wav",
        "analysis_source": "synthetic_edge_case",
    },
]

SECTION_BLUEPRINTS = {
    "fx-hard-001": [
        ("intro", 0, 32, 0.93, 0.30),
        ("groove", 32, 96, 0.84, 0.58),
        ("breakdown", 96, 128, 0.80, 0.42),
        ("drop", 128, 224, 0.91, 0.88),
        ("outro", 224, 288, 0.89, 0.50),
    ],
    "fx-hard-002": [
        ("groove", 0, 64, 0.78, 0.62),
        ("drop", 64, 176, 0.90, 0.90),
        ("outro", 176, 260, 0.82, 0.54),
    ],
    "fx-tech-003": [
        ("intro", 0, 64, 0.88, 0.36),
        ("groove", 64, 224, 0.86, 0.61),
        ("breakdown", 224, 256, 0.74, 0.38),
        ("outro", 256, 372, 0.87, 0.44),
    ],
    "fx-house-004": [
        ("intro", 0, 64, 0.92, 0.34),
        ("build", 64, 128, 0.78, 0.57),
        ("drop", 128, 256, 0.83, 0.78),
        ("outro", 256, 334, 0.85, 0.43),
    ],
    "fx-dnb-005": [
        ("intro", 0, 32, 0.82, 0.44),
        ("build", 32, 64, 0.84, 0.67),
        ("drop", 64, 160, 0.93, 0.95),
        ("breakdown", 160, 192, 0.80, 0.40),
        ("drop", 192, 272, 0.88, 0.91),
        ("outro", 272, 302, 0.76, 0.46),
    ],
    "fx-pop-006": [
        ("intro", 0, 16, 0.76, 0.30),
        ("verse", 16, 64, 0.70, 0.43),
        ("hook", 64, 112, 0.86, 0.82),
        ("bridge", 112, 144, 0.65, 0.48),
        ("outro", 144, 214, 0.74, 0.38),
    ],
    "fx-amb-007": [
        ("unknown", 0, 420, 0.40, 0.18),
    ],
    "fx-bad-008": [
        ("unknown", 0, 64, 0.20, None),
    ],
}

ROLE_VECTORS_8D = {
    "intro": [0.70, 0.45, 0.12, 0.10, 0.20, 0.18, 0.00, 0.05],
    "groove": [0.84, 0.72, 0.18, 0.05, 0.28, 0.25, 0.02, 0.10],
    "build": [0.76, 0.62, 0.30, 0.20, 0.45, 0.35, 0.10, 0.15],
    "breakdown": [0.38, 0.30, 0.08, 0.70, 0.22, 0.15, 0.30, 0.05],
    "drop": [0.95, 0.88, 0.20, 0.00, 0.55, 0.60, 0.05, 0.20],
    "outro": [0.58, 0.48, 0.10, 0.15, 0.18, 0.20, 0.00, 0.08],
    "verse": [0.48, 0.42, 0.50, 0.10, 0.30, 0.25, 0.40, 0.20],
    "hook": [0.72, 0.68, 0.78, 0.08, 0.50, 0.45, 0.70, 0.35],
    "bridge": [0.50, 0.38, 0.42, 0.45, 0.32, 0.28, 0.55, 0.18],
    "unknown": [0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10],
}


def _track_by_id() -> dict[str, dict[str, Any]]:
    return {track["track_id"]: track for track in TRACKS}


def _section_id(track_id: str, ordinal: int) -> str:
    return f"{track_id}#s{ordinal:03d}"


def build_sections() -> list[dict[str, Any]]:
    tracks = _track_by_id()
    sections: list[dict[str, Any]] = []
    for track_id, blueprints in SECTION_BLUEPRINTS.items():
        track = tracks[track_id]
        bpm = track["bpm"]
        seconds_per_beat = 60.0 / bpm if bpm else None
        for ordinal, (role, start_beat, end_beat, confidence, energy) in enumerate(blueprints):
            if seconds_per_beat is None:
                start_s = 0.0 if ordinal == 0 else float(start_beat)
                end_s = float(track["duration_s"]) if ordinal == 0 else float(end_beat)
            else:
                start_s = round(start_beat * seconds_per_beat, 3)
                end_s = round(end_beat * seconds_per_beat, 3)
            section_id = _section_id(track_id, ordinal)
            sections.append(
                {
                    "section_id": section_id,
                    "track_id": track_id,
                    "ordinal": ordinal,
                    "role": role,
                    "role_confidence": confidence,
                    "source": "fallback" if track_id in {"fx-amb-007", "fx-bad-008"} else "anlz",
                    "source_detail": "whole_track" if track_id == "fx-amb-007" else "pssi",
                    "start_s": start_s,
                    "end_s": end_s,
                    "start_beat": start_beat if bpm else None,
                    "end_beat": end_beat if bpm else None,
                    "bar_count": round((end_beat - start_beat) / 4, 2) if bpm else None,
                    "bpm": bpm,
                    "camelot": track["camelot"],
                    "energy": energy,
                    "semantic_vector_ref": f"vec8:{section_id}",
                    "timbre_vector_ref": f"vec512:{section_id}",
                    "tags": [track["genre"], role, "fixture"],
                    "provenance_ref": f"dataset_intel_synthetic_v1:{section_id}",
                }
            )
    return sections


def build_anlz_bundles(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_track: dict[str, list[dict[str, Any]]] = {}
    for section in sections:
        by_track.setdefault(section["track_id"], []).append(section)

    bundles = []
    for track in TRACKS:
        track_sections = by_track[track["track_id"]]
        bundles.append(
            {
                "track_id": track["track_id"],
                "ppth_path": track["location"],
                "anlz_paths": {
                    "DAT": f"fixture://rekordbox/{track['track_id']}/ANLZ0000.DAT",
                    "EXT": f"fixture://rekordbox/{track['track_id']}/ANLZ0000.EXT",
                },
                "pqtz": {
                    "bpm": track["bpm"],
                    "beat_count": max((s["end_beat"] or 0) for s in track_sections),
                    "downbeat_every": 4 if track["bpm"] else None,
                },
                "pssi": {
                    "mood": "high"
                    if track["genre"] in {"hardtechno", "techno", "house", "drum_and_bass"}
                    else "mid",
                    "phrases": [
                        {
                            "section_id": s["section_id"],
                            "beat": s["start_beat"],
                            "role": s["role"],
                            "confidence": s["role_confidence"],
                        }
                        for s in track_sections
                    ],
                },
            }
        )
    return bundles


def build_section_vectors_8d(sections: list[dict[str, Any]]) -> dict[str, list[float]]:
    vectors: dict[str, list[float]] = {}
    for section in sections:
        base = ROLE_VECTORS_8D[section["role"]]
        ordinal_offset = section["ordinal"] * 0.003
        vectors[f"vec8:{section['section_id']}"] = [
            round(min(1.0, value + ordinal_offset), 3) for value in base
        ]
    return vectors


def build_section_vectors_512d(section_count: int) -> np.ndarray:
    rng = np.random.default_rng(VECTOR_512_SEED)
    vectors = rng.normal(0.0, 1.0, size=(section_count, 512)).astype(np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / norms


def build_transition_pairs() -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "tr_001",
            "from_section_id": "fx-hard-001#s004",
            "to_section_id": "fx-hard-002#s000",
            "cue_slot": "A",
            "start_in_bars": 16,
            "scores": {
                "semantic": 0.91,
                "harmonic": 0.88,
                "bpm": 1.0,
                "energy_shape": 0.77,
                "role": 0.94,
                "phrase_alignment": 1.0,
                "cue_operability": 0.84,
                "taste": 0.60,
                "novelty": 0.42,
            },
            "risk_flags": [],
            "score": 0.86,
            "confidence": 0.82,
            "reason": "outro density matches hardtechno groove entry with neighbor key",
        },
        {
            "candidate_id": "tr_002",
            "from_section_id": "fx-tech-003#s003",
            "to_section_id": "fx-house-004#s000",
            "cue_slot": "A",
            "start_in_bars": 32,
            "scores": {
                "semantic": 0.72,
                "harmonic": 0.92,
                "bpm": 0.64,
                "energy_shape": 0.66,
                "role": 0.88,
                "phrase_alignment": 1.0,
                "cue_operability": 0.80,
                "taste": 0.50,
                "novelty": 0.58,
            },
            "risk_flags": ["tempo_bridge"],
            "score": 0.70,
            "confidence": 0.70,
            "reason": "tool outro can bridge to house intro but needs tempo handling",
        },
        {
            "candidate_id": "tr_003",
            "from_section_id": "fx-dnb-005#s001",
            "to_section_id": "fx-dnb-005#s002",
            "cue_slot": "C",
            "start_in_bars": 8,
            "scores": {
                "semantic": 0.82,
                "harmonic": 1.0,
                "bpm": 1.0,
                "energy_shape": 0.94,
                "role": 0.90,
                "phrase_alignment": 1.0,
                "cue_operability": 0.88,
                "taste": 0.55,
                "novelty": 0.25,
            },
            "risk_flags": ["same_track_demo"],
            "score": 0.83,
            "confidence": 0.86,
            "reason": "build to drop exact-timing demo for dense double-drop behavior",
        },
        {
            "candidate_id": "tr_004",
            "from_section_id": "fx-pop-006#s002",
            "to_section_id": "fx-house-004#s003",
            "cue_slot": "F",
            "start_in_bars": None,
            "scores": {
                "semantic": 0.45,
                "harmonic": 0.40,
                "bpm": 0.32,
                "energy_shape": 0.36,
                "role": 0.20,
                "phrase_alignment": 0.50,
                "cue_operability": 0.34,
                "taste": 0.20,
                "novelty": 0.70,
            },
            "risk_flags": ["vocal_clash", "unsafe_role_pair", "tempo_clash"],
            "score": 0.18,
            "confidence": 0.30,
            "reason": "hook over outro is a negative fixture that should rank low",
        },
        {
            "candidate_id": "tr_005",
            "from_section_id": "fx-hard-001#s004",
            "to_section_id": "fx-amb-007#s000",
            "cue_slot": None,
            "start_in_bars": None,
            "scores": {
                "semantic": 0.20,
                "harmonic": 0.0,
                "bpm": 0.0,
                "energy_shape": 0.12,
                "role": 0.10,
                "phrase_alignment": 0.0,
                "cue_operability": 0.0,
                "taste": 0.10,
                "novelty": 0.90,
            },
            "risk_flags": ["missing_bpm", "unknown_role", "suppress_live"],
            "score": 0.08,
            "confidence": 0.20,
            "reason": "ambient fallback should suppress live transition claims",
        },
    ]


def build_transition_slates(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "slate_id": "slate_001",
            "mode": "live_pill",
            "current_section_id": "fx-hard-001#s004",
            "candidate_ids": ["tr_001", "tr_005"],
            "top_candidate_id": "tr_001",
            "exact_timing_allowed": True,
        },
        {
            "slate_id": "slate_002",
            "mode": "prep_plan",
            "current_section_id": "fx-tech-003#s003",
            "candidate_ids": ["tr_002", "tr_004"],
            "top_candidate_id": "tr_002",
            "exact_timing_allowed": False,
        },
        {
            "slate_id": "slate_003",
            "mode": "live_pill",
            "current_section_id": "fx-pop-006#s002",
            "candidate_ids": ["tr_004"],
            "top_candidate_id": None,
            "exact_timing_allowed": False,
        },
    ]


def build_smart_cue_proposals() -> list[dict[str, Any]]:
    return [
        {
            "proposal_id": "cueprop_fx-hard-001_v1",
            "track_id": "fx-hard-001",
            "policy_version": "smart_cue_policy_v1",
            "status": "review",
            "summary": "Fixture hardtechno cues prioritize mix-in, breakdown, drop, and mix-out.",
            "anchors": [
                {
                    "slot": "A",
                    "section_id": "fx-hard-001#s000",
                    "label": "mix-in",
                    "start_s": 0.0,
                    "confidence": 0.93,
                },
                {
                    "slot": "C",
                    "section_id": "fx-hard-001#s002",
                    "label": "breakdown",
                    "start_s": 32.0,
                    "confidence": 0.80,
                },
                {
                    "slot": "D",
                    "section_id": "fx-hard-001#s003",
                    "label": "drop",
                    "start_s": 42.667,
                    "confidence": 0.91,
                },
                {
                    "slot": "F",
                    "section_id": "fx-hard-001#s004",
                    "label": "mix-out",
                    "start_s": 74.667,
                    "confidence": 0.89,
                },
            ],
        },
        {
            "proposal_id": "cueprop_fx-pop-006_v1",
            "track_id": "fx-pop-006",
            "policy_version": "smart_cue_policy_v1",
            "status": "review_only",
            "summary": "Fixture pop cues include vocal/hook risk flags.",
            "anchors": [
                {
                    "slot": "A",
                    "section_id": "fx-pop-006#s000",
                    "label": "mix-in",
                    "start_s": 0.0,
                    "confidence": 0.76,
                },
                {
                    "slot": "D",
                    "section_id": "fx-pop-006#s002",
                    "label": "hook",
                    "start_s": 31.475,
                    "confidence": 0.86,
                },
                {
                    "slot": "F",
                    "section_id": "fx-pop-006#s004",
                    "label": "mix-out",
                    "start_s": 70.82,
                    "confidence": 0.74,
                },
            ],
        },
    ]


def build_claim_ledgers() -> list[dict[str, Any]]:
    return [
        {
            "packet_id": "ctx_001",
            "claims": [
                {
                    "claim_id": "clm_ctx_001_000",
                    "claim_type": "transition_fit",
                    "subject_id": "tr_001",
                    "value": "compatible",
                    "confidence": 0.82,
                    "evidence_refs": ["candidate:tr_001"],
                    "allowed_phrases": ["compatible entry", "works as a next entry"],
                    "forbidden_phrases": ["perfect", "guaranteed"],
                },
                {
                    "claim_id": "clm_ctx_001_001",
                    "claim_type": "timing",
                    "subject_id": "tr_001",
                    "value": "16 bars",
                    "confidence": 0.81,
                    "evidence_refs": ["packet:ctx_001", "candidate:tr_001"],
                    "allowed_phrases": ["in 16 bars"],
                    "forbidden_phrases": ["exactly now"],
                },
                {
                    "claim_id": "clm_ctx_001_002",
                    "claim_type": "cue_slot",
                    "subject_id": "tr_001",
                    "value": "A",
                    "confidence": 0.84,
                    "evidence_refs": ["candidate:tr_001"],
                    "allowed_phrases": ["cue A", "hot cue A"],
                    "forbidden_phrases": ["cue H"],
                },
            ],
        },
        {
            "packet_id": "ctx_003",
            "claims": [
                {
                    "claim_id": "clm_ctx_003_000",
                    "claim_type": "timing",
                    "subject_id": "tr_002",
                    "value": None,
                    "confidence": 0.40,
                    "evidence_refs": ["packet:ctx_003"],
                    "allowed_phrases": ["timing is not locked"],
                    "forbidden_phrases": ["in 16 bars", "exactly"],
                }
            ],
        },
    ]


def build_context_packets() -> list[dict[str, Any]]:
    return [
        {
            "packet_id": "ctx_001",
            "schema_version": "intel_context_v1",
            "mode": "live",
            "intent": "live_next_pill",
            "current": {
                "track_id": "fx-hard-001",
                "section_id": "fx-hard-001#s004",
                "role": "outro",
                "playhead_confidence": 0.83,
                "blend_suppressed": False,
            },
            "candidate_ids": ["tr_001", "tr_005"],
            "allowed_actions": ["select", "hold", "suppress"],
            "allowed_claims": ["clm_ctx_001_000", "clm_ctx_001_001"],
            "confidence_policy": {"exact_timing_allowed": True, "min_select_confidence": 0.70},
        },
        {
            "packet_id": "ctx_002",
            "schema_version": "intel_context_v1",
            "mode": "prep",
            "intent": "transition_slate",
            "current": {
                "track_id": "fx-tech-003",
                "section_id": "fx-tech-003#s003",
                "role": "outro",
            },
            "candidate_ids": ["tr_002", "tr_004"],
            "allowed_actions": ["select", "hold", "ask"],
            "allowed_claims": [],
            "confidence_policy": {"exact_timing_allowed": False, "min_select_confidence": 0.55},
        },
        {
            "packet_id": "ctx_003",
            "schema_version": "intel_context_v1",
            "mode": "live",
            "intent": "live_next_pill",
            "current": {
                "track_id": "fx-tech-003",
                "section_id": "fx-tech-003#s003",
                "role": "outro",
                "playhead_confidence": 0.42,
                "blend_suppressed": False,
            },
            "candidate_ids": ["tr_002"],
            "allowed_actions": ["hold", "suppress"],
            "allowed_claims": ["clm_ctx_003_000"],
            "confidence_policy": {"exact_timing_allowed": False, "min_select_confidence": 0.70},
        },
        {
            "packet_id": "ctx_004",
            "schema_version": "intel_context_v1",
            "mode": "live",
            "intent": "live_next_pill",
            "current": {
                "track_id": "fx-pop-006",
                "section_id": "fx-pop-006#s002",
                "role": "hook",
                "playhead_confidence": 0.75,
                "blend_suppressed": True,
            },
            "candidate_ids": ["tr_004"],
            "allowed_actions": ["suppress"],
            "allowed_claims": [],
            "confidence_policy": {"exact_timing_allowed": False, "min_select_confidence": 0.70},
        },
        {
            "packet_id": "ctx_005",
            "schema_version": "intel_context_v1",
            "mode": "prep",
            "intent": "smart_hot_cues",
            "current": {"track_id": "fx-hard-001", "taste_consent": False},
            "candidate_ids": [],
            "cue_proposal_ids": ["cueprop_fx-hard-001_v1"],
            "allowed_actions": ["select", "hold", "ask"],
            "allowed_claims": [],
            "confidence_policy": {"exact_timing_allowed": False, "min_select_confidence": 0.55},
        },
        {
            "packet_id": "ctx_006",
            "schema_version": "intel_context_v1",
            "mode": "prep",
            "intent": "transition_slate",
            "current": {
                "track_id": "fx-amb-007",
                "section_id": "fx-amb-007#s000",
                "role": "unknown",
            },
            "candidate_ids": ["tr_005"],
            "allowed_actions": ["hold", "suppress"],
            "allowed_claims": [],
            "confidence_policy": {"exact_timing_allowed": False, "min_select_confidence": 0.55},
        },
        {
            "packet_id": "ctx_007",
            "schema_version": "intel_context_v1",
            "mode": "prep",
            "intent": "explain_transition",
            "current": {
                "track_id": "fx-hard-001",
                "section_id": "fx-hard-001#s004",
                "role": "outro",
            },
            "candidate_ids": ["tr_001"],
            "allowed_actions": ["select", "hold", "ask"],
            "allowed_claims": ["clm_ctx_001_000"],
            "confidence_policy": {"exact_timing_allowed": False, "min_select_confidence": 0.55},
        },
    ]


def build_jsonl_rows() -> dict[str, list[dict[str, Any]]]:
    return {
        "agent_decisions.jsonl": [
            {
                "decision_id": "dec_001",
                "packet_id": "ctx_001",
                "action": "select",
                "candidate_id": "tr_001",
                "cue_slot": "A",
                "timing_text": "in 16 bars",
                "spoken_text": "Use cue A in 16 bars.",
                "cited_claims": ["clm_ctx_001_001", "clm_ctx_001_002"],
                "confidence": 0.82,
            },
            {
                "decision_id": "dec_002",
                "packet_id": "ctx_004",
                "action": "suppress",
                "candidate_id": None,
                "cue_slot": None,
                "timing_text": None,
                "cited_claims": [],
                "confidence": 0.0,
            },
        ],
        "decision_traces.jsonl": [
            {
                "trace_id": "trace_001",
                "decision_id": "dec_001",
                "context_run_id": "ctxrun_fixture_001",
                "packet_id": "ctx_001",
                "decision_source": "deterministic",
                "validator_result": "ok",
                "latency_ms": 18,
            },
            {
                "trace_id": "trace_002",
                "decision_id": "dec_002",
                "context_run_id": "ctxrun_fixture_004",
                "packet_id": "ctx_004",
                "decision_source": "degraded",
                "validator_result": "suppressed_blend",
                "latency_ms": 9,
            },
        ],
        "live_awareness_snapshots.jsonl": [
            {
                "snapshot_id": "live_001",
                "track_id": "fx-hard-001",
                "section_id": "fx-hard-001#s004",
                "playhead_s": 75.0,
                "playhead_confidence": 0.83,
                "blend_suppressed": False,
                "exact_timing_allowed": True,
            },
            {
                "snapshot_id": "live_002",
                "track_id": "fx-pop-006",
                "section_id": "fx-pop-006#s002",
                "playhead_s": 40.0,
                "playhead_confidence": 0.75,
                "blend_suppressed": True,
                "exact_timing_allowed": False,
            },
        ],
        "gold_labels_redacted.jsonl": [
            {
                "label_id": "gold_001",
                "packet_id": "ctx_001",
                "candidate_id": "tr_001",
                "label": "accept",
                "rubric": "transition_utility",
                "redacted_notes": "Fixture label: useful hardtechno outro to groove entry.",
            },
            {
                "label_id": "gold_002",
                "packet_id": "ctx_004",
                "candidate_id": "tr_004",
                "label": "reject",
                "rubric": "risk",
                "redacted_notes": "Fixture label: vocal clash and blend suppression.",
            },
        ],
    }


def build_section_queries() -> list[dict[str, Any]]:
    return [
        {
            "query_id": "fixture_role_intro_mix_in",
            "target_role": "intro",
            "prototype_role": "intro",
            "mixable_roles": ["intro"],
            "min_role_confidence": 0.7,
            "min_bar_count": 4,
        },
        {
            "query_id": "fixture_role_groove_bed",
            "target_role": "groove",
            "prototype_role": "groove",
            "mixable_roles": ["groove"],
            "min_role_confidence": 0.7,
            "min_bar_count": 8,
        },
        {
            "query_id": "fixture_role_breakdown_reset",
            "target_role": "breakdown",
            "prototype_role": "breakdown",
            "mixable_roles": ["breakdown"],
            "min_role_confidence": 0.7,
            "min_bar_count": 4,
        },
        {
            "query_id": "fixture_role_drop_peak",
            "target_role": "drop",
            "prototype_role": "drop",
            "mixable_roles": ["drop"],
            "min_role_confidence": 0.7,
            "min_bar_count": 8,
        },
        {
            "query_id": "fixture_role_outro_mix_out",
            "target_role": "outro",
            "prototype_role": "outro",
            "mixable_roles": ["outro"],
            "min_role_confidence": 0.7,
            "min_bar_count": 4,
        },
        {
            "query_id": "fixture_role_build_lift",
            "target_role": "build",
            "prototype_role": "build",
            "mixable_roles": ["build"],
            "min_role_confidence": 0.7,
            "min_bar_count": 4,
        },
    ]


def build_taste_feedback_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(
        event_id: str,
        session_id: str,
        label: str,
        role_from: str,
        role_to: str,
        *,
        candidate_id: str,
        split: str = "calibration",
        action: str = "transition_labeled",
        risk_flags: list[str] | None = None,
        score: float = 0.70,
    ) -> None:
        rows.append(
            {
                "event_id": event_id,
                "session_id": session_id,
                "surface": "prep_chat",
                "action": action,
                "label": label,
                "split": split,
                "candidate_id": candidate_id,
                "role_from": role_from,
                "role_to": role_to,
                "risk_flags": risk_flags or [],
                "score": score,
                "profile_consent": True,
            }
        )

    for index in range(12):
        add(
            f"taste_pos_groove_{index:03d}",
            f"s{index % 4 + 1}",
            "would_play" if index % 3 else "played_next",
            "outro",
            "groove",
            candidate_id="tr_001",
            score=0.86,
        )
    for index in range(8):
        add(
            f"taste_pos_intro_{index:03d}",
            f"s{index % 4 + 2}",
            "would_play",
            "outro",
            "intro",
            candidate_id="tr_002",
            score=0.70,
        )
    for index in range(4):
        add(
            f"taste_maybe_lift_{index:03d}",
            f"s{index % 3 + 1}",
            "maybe",
            "breakdown",
            "drop",
            candidate_id="tr_003",
            score=0.76,
        )
    for index in range(4):
        add(
            f"taste_neg_vocal_{index:03d}",
            f"s{index % 4 + 1}",
            "vibe_no" if index % 2 else "no",
            "hook",
            "outro",
            candidate_id="tr_004",
            risk_flags=["vocal_clash", "unsafe_role_pair"],
            score=0.18,
        )
    for index in range(3):
        add(
            f"taste_technical_{index:03d}",
            f"s{index % 3 + 1}",
            "technical_no",
            "hook",
            "outro",
            candidate_id="tr_004",
            risk_flags=["vocal_clash", "tempo_clash"],
            score=0.18,
        )
    for index in range(10):
        add(
            f"taste_poison_{index:03d}",
            "s_poison",
            "no",
            "drop",
            "drop",
            candidate_id="tr_poison",
            split="poison",
            risk_flags=["fatigue"],
            score=0.74,
        )
    for index in range(4):
        add(
            f"taste_holdout_positive_{index:03d}",
            f"s_holdout_{index % 2 + 1}",
            "would_play",
            "outro",
            "groove" if index % 2 == 0 else "intro",
            candidate_id="tr_001" if index % 2 == 0 else "tr_002",
            split="holdout",
            score=0.80,
        )
    for index in range(2):
        add(
            f"taste_holdout_technical_{index:03d}",
            f"s_holdout_{index + 1}",
            "technical_no",
            "hook",
            "outro",
            candidate_id="tr_004",
            split="holdout",
            risk_flags=["vocal_clash", "tempo_clash"],
            score=0.18,
        )
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def write_xml_fixtures() -> None:
    before = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<DJ_PLAYLISTS Version=\"1.0.0\">
  <COLLECTION Entries=\"1\">
    <TRACK TrackID=\"fx-hard-001\" Name=\"Fixture Hard Signal One\" Artist=\"Fixture Lab\" Location=\"fixture://tracks/fx-hard-001.wav\" />
  </COLLECTION>
</DJ_PLAYLISTS>
"""
    after = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<DJ_PLAYLISTS Version=\"1.0.0\">
  <COLLECTION Entries=\"1\">
    <TRACK TrackID=\"fx-hard-001\" Name=\"Fixture Hard Signal One\" Artist=\"Fixture Lab\" Location=\"fixture://tracks/fx-hard-001.wav\">
      <POSITION_MARK Name=\"A\" Type=\"0\" Start=\"0.000\" Num=\"0\" Red=\"0\" Green=\"128\" Blue=\"255\" />
      <POSITION_MARK Name=\"D\" Type=\"0\" Start=\"42.667\" Num=\"3\" Red=\"255\" Green=\"64\" Blue=\"64\" />
      <POSITION_MARK Name=\"F\" Type=\"0\" Start=\"74.667\" Num=\"5\" Red=\"255\" Green=\"180\" Blue=\"64\" />
    </TRACK>
  </COLLECTION>
</DJ_PLAYLISTS>
"""
    (FIXTURE_DIR / "cue_baseline_before.xml").write_text(before, encoding="utf-8")
    (FIXTURE_DIR / "cue_baseline_after.xml").write_text(after, encoding="utf-8")


def write_readme() -> None:
    text = """# INTEL Synthetic Fixtures

Public, privacy-safe fixtures for the vibemix musical intelligence contracts.

These files are generated by `scripts/dev/generate_intel_fixtures.py`.
They intentionally contain no real audio, no local paths, no private library
data, no raw vectors in context packets, and no network-derived facts.

The 512D vector file is synthetic random data with deterministic seed
`vibemix-intel-fixtures-v1`; row order matches `sections.json` order.
Use `scripts/eval/intel_fixture_audit.py` before changing the corpus.
"""
    (FIXTURE_DIR / "README.md").write_text(text, encoding="utf-8")


def write_privacy_bad_examples() -> None:
    bad_dir = FIXTURE_DIR / "privacy_bad_examples"
    bad_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        bad_dir / "local_path.json",
        {
            "packet_id": "bad_local_path",
            "location": "/Users/ozai/Music/private-track.wav",
        },
    )
    write_json(
        bad_dir / "raw_vector_packet.json",
        {
            "packet_id": "bad_raw_vector",
            "raw_vector": [round(i / 512, 6) for i in range(512)],
        },
    )


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest(files: list[str]) -> dict[str, Any]:
    return {
        "fixture_version": "intel_fixture_v1",
        "dataset_card_id": "dataset_intel_synthetic_v1",
        "generated_by": "scripts/dev/generate_intel_fixtures.py",
        "seed": SEED,
        "files": {name: sha256_file(FIXTURE_DIR / name) for name in sorted(files)},
    }


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    sections = build_sections()
    pairs = build_transition_pairs()

    dataset_card = {
        "dataset_card_id": "dataset_intel_synthetic_v1",
        "fixture_version": "intel_fixture_v1",
        "created_for": "vibemix INTEL PR-0 fixture/readiness gates",
        "privacy_class": "public_synthetic",
        "recommended_uses": [
            "schema tests",
            "grounding tests",
            "privacy redaction tests",
            "deterministic scorer fixtures",
        ],
        "not_recommended_uses": [
            "claiming musical quality",
            "calibrating taste",
            "benchmarking CLAP quality",
        ],
    }

    write_readme()
    write_json(FIXTURE_DIR / "dataset_card.json", dataset_card)
    write_json(FIXTURE_DIR / "tracks.json", TRACKS)
    write_json(FIXTURE_DIR / "sections.json", sections)
    write_json(FIXTURE_DIR / "anlz_bundles.json", build_anlz_bundles(sections))
    write_json(FIXTURE_DIR / "section_vectors_8d.json", build_section_vectors_8d(sections))
    np.save(FIXTURE_DIR / "section_vectors_512d.npy", build_section_vectors_512d(len(sections)))
    write_json(FIXTURE_DIR / "transition_pairs.json", pairs)
    write_json(FIXTURE_DIR / "transition_slates.json", build_transition_slates(pairs))
    write_json(FIXTURE_DIR / "smart_cue_proposals.json", build_smart_cue_proposals())
    write_xml_fixtures()
    write_json(FIXTURE_DIR / "context_packets.json", build_context_packets())
    write_json(FIXTURE_DIR / "claim_ledgers.json", build_claim_ledgers())
    for name, rows in build_jsonl_rows().items():
        write_jsonl(FIXTURE_DIR / name, rows)
    write_jsonl(FIXTURE_DIR / "section_queries.jsonl", build_section_queries())
    write_jsonl(FIXTURE_DIR / "taste_feedback.jsonl", build_taste_feedback_rows())
    write_privacy_bad_examples()

    files = [
        "README.md",
        "dataset_card.json",
        "tracks.json",
        "sections.json",
        "anlz_bundles.json",
        "section_vectors_8d.json",
        "section_vectors_512d.npy",
        "transition_pairs.json",
        "transition_slates.json",
        "smart_cue_proposals.json",
        "cue_baseline_before.xml",
        "cue_baseline_after.xml",
        "context_packets.json",
        "claim_ledgers.json",
        "agent_decisions.jsonl",
        "decision_traces.jsonl",
        "live_awareness_snapshots.jsonl",
        "gold_labels_redacted.jsonl",
        "section_queries.jsonl",
        "taste_feedback.jsonl",
    ]
    write_json(FIXTURE_DIR / "MANIFEST.json", build_manifest(files))


if __name__ == "__main__":
    main()
