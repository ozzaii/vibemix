# SPDX-License-Identifier: Apache-2.0
"""Viber live-context proof CLI tests."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

import vibemix.__main__ as main_mod
from vibemix.library.codex_curate import (
    CodexChatResult,
    normalize_live_context_for_viber,
    render_live_context_preview,
)
from vibemix.library.rekordbox import TrackEntry
from vibemix.runtime.config_store import ConfigStore, load_config


def _live_context_capabilities() -> list[str]:
    return [
        "deck_state",
        "deck_mixer",
        "deck_lanes_context",
        "deck_reference_context",
        "deck_source_context",
        "deck_source_status",
        "deck_audio_context",
        "deck_audio_separation_context",
        "deck_audio_features_context",
        "deck_audio_delta_context",
        "deck_audio_window_context",
        "audio_part_context",
        "audio_window_context",
        "audio_window_map",
        "audio_delta",
        "live_evidence",
    ]


def _deck_source_status() -> dict[str, str]:
    return {
        "controller": "connected",
        "controller_connection": "connected",
        "library": "present",
        "library_tracks": "24",
        "library_source": "rekordbox_xml",
        "library_match": "matched",
        "nowplaying": "blocked_non_deck_owner",
        "nowplaying_owner": "com.apple.webkit.gpu",
        "nowplaying_title": "pink_floyd",
        "audible_deck": "A",
        "resolution": "library_cache_match",
        "resolved_side": "A",
        "screen_vision": "disabled",
    }


def _audio_window_map() -> dict:
    return {
        "p1": "master_global_mix",
        "p1_heard": True,
        "timeline": "past_action_future",
        "together_audio": "P1_global_mix",
        "decks_together": True,
        "deckA_audio": "not_attached",
        "deckB_audio": "not_attached",
        "per_deck_audio": "structured_text_only",
        "duplicate_audio": "same_master_not_deck_split",
        "deck_separation": "deck_lanes_context",
        "lane_aliases": "deck1:A,deck2:B",
        "pre_s": [-6.0, -1.0],
        "current_s": [-1.0, 0.0],
        "action_s": [-1.0, 0.0],
        "move_anchors": [
            {
                "label": "A_low: cut->killed",
                "token": "A_low_cut_to_killed",
                "age_s": 0.3,
                "relation": "inside_P1",
            }
        ],
        "future": {"heard": False, "span": "not_attached"},
        "rule": "time_alignment_not_outcome_verdict",
    }


def _audio_part_context() -> str:
    return (
        "audio_part_context[surface=live_context P1=live_global_mix "
        "P1_model_heard=false P1_runtime_observed=true P1_audience_heard=true "
        "P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B "
        "together_audio=P1 per_deck_audio=not_attached "
        "duplicate_audio=same_master_not_deck_split rule=part_labels_not_outcome_verdict]"
    )


def _deck_pair_audio_part_context(deck_a: str = "P2", deck_b: str = "P3") -> str:
    return (
        "audio_part_context[surface=gemini_parts P1=live_global_mix "
        "P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true "
        "P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B "
        f"together_audio=P1 part_order=P1,{deck_a},{deck_b} "
        "per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts "
        f"deckA_part={deck_a} {deck_a}=deckA_configured_capture "
        f"{deck_a}_model_heard=true {deck_a}_audience_heard=false "
        f"{deck_a}_deck_audio=deckA_configured_capture "
        f"{deck_a}_rule=deck_pair_capture_reference_not_quality_verdict "
        f"deckB_part={deck_b} {deck_b}=deckB_configured_capture "
        f"{deck_b}_model_heard=true {deck_b}_audience_heard=false "
        f"{deck_b}_deck_audio=deckB_configured_capture "
        f"{deck_b}_rule=deck_pair_capture_reference_not_quality_verdict "
        "rule=part_labels_not_outcome_verdict]"
    )


def _deck_pair_audio_window_context(deck_a: str = "P2", deck_b: str = "P3") -> str:
    return (
        "audio_window_context[P1=master_global_mix P1_heard=true "
        "timeline=past_action_future together_audio=P1_global_mix decks_together=true "
        f"deckA_audio={deck_a} deckB_audio={deck_b} "
        "per_deck_audio=deck_pair_parts duplicate_audio=separate_deck_pair_parts "
        "deck_separation=deck_lanes_context "
        "deck_audio_separation=deck_audio_separation_context "
        "lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 "
        "action=-1.0..0.0 rule=time_alignment_not_outcome_verdict "
        "move_anchor=none future_heard=false future=not_attached]"
    )


def _deck_pair_audio_window_map(deck_a: str = "P2", deck_b: str = "P3") -> dict:
    row = _audio_window_map()
    row.update(
        {
            "deckA_audio": deck_a,
            "deckB_audio": deck_b,
            "per_deck_audio": "deck_pair_parts",
            "duplicate_audio": "separate_deck_pair_parts",
            "deck_audio_separation": "deck_audio_separation_context",
            "deck_part_span_s": [-3.0, 0.0],
            "deck_part_activity": {"A": "active", "B": "active"},
        }
    )
    return row


def _deck_audio_separation_context() -> str:
    return (
        "deck_audio_separation_context[requested_device=BlackHole_2ch "
        "capture_device=BlackHole_2ch input_channels=2 opened_channels=2 "
        "sample_rate=48000 device_capacity=stereo_or_less mode=global_mix_only "
        "current_capture=P1_global_mix gemini_audio=mono_downmix_of_capture "
        "deckA_audio=not_captured deckB_audio=not_captured "
        "per_deck_audio=not_attached isolated_decks=false "
        "upgrade_path=multi_channel_deck_pair_capture "
        "rule=separation_capability_not_outcome]"
    )


def _deck_pair_audio_separation_context() -> str:
    return (
        "deck_audio_separation_context[requested_device=BlackHole_16ch "
        "capture_device=BlackHole_16ch input_channels=16 opened_channels=4 "
        "sample_rate=48000 device_capacity=multichannel_available "
        "mode=deck_pair_capture_configured master_channels=0,1,2,3 "
        "current_capture=P1_global_mix_plus_deck_pairs "
        "gemini_audio=mono_downmix_of_master_capture deckA_audio=captured "
        "deckB_audio=captured per_deck_audio=captured_not_attached "
        "isolated_decks=runtime_capture_available deck_pairs=A:0,1+B:2,3 "
        "upgrade_path=attach_deck_pair_audio_parts_when_needed "
        "deck_audio_activity=A_active+B_silent "
        "rule=separation_capability_not_outcome]"
    )


def _deck_pair_audio_separation_context_with_route_diagnosis(
    *,
    active_unassigned_pairs: str = "none",
) -> str:
    active_unassigned_token = active_unassigned_pairs.replace(",", "_")
    return (
        "deck_audio_separation_context[requested_device=BlackHole_16ch "
        "capture_device=BlackHole_16ch input_channels=16 opened_channels=4 "
        "sample_rate=48000 device_capacity=multichannel_available "
        "mode=deck_pair_capture_unverified master_channels=0,1,2,3 "
        "current_capture=P1_global_mix_plus_unverified_deck_pairs "
        "gemini_audio=mono_downmix_of_master_capture deckA_audio=captured_unverified "
        "deckB_audio=captured_unverified per_deck_audio=unverified_not_attached "
        "isolated_decks=false deck_pairs=A:0,1+B:2,3 "
        "verification=awaiting_live_audio_on_both_deck_pairs "
        "upgrade_path=verify_rekordbox_deck_routing_or_use_manual_map "
        "active_sides_seen=A deck_audio_activity=A_active+B_silent "
        "route_diagnosis=configured_deck_lane_missing_audio__inactive_sides_B"
        "__active_sides_A__configured_pairs_A:0_1+B:2_3__opened_active_pairs_0_1"
        f"__active_unassigned_pairs_{active_unassigned_token}"
        "__rule_opened_channel_probe_not_rekordbox_control "
        "rule=separation_capability_not_outcome]"
    )


def _deck_audio_features_context() -> str:
    return (
        "deck_audio_features_context[source=deck_pair_capture "
        "window=latest_callback per_deck_audio=captured_features "
        "A_activity=active A_rms=0.020 A_peak=0.100 A_zcr=0.030 "
        "B_activity=silent B_rms=0.000 B_peak=0.000 B_zcr=0.000 "
        "rule=deck_audio_features_not_outcome_verdict]"
    )


def _deck_audio_delta_context() -> str:
    return (
        "deck_audio_delta_context[source=deck_pair_capture "
        "window=latest_callback per_deck_delta=captured_feature_delta "
        "A_delta=rms_rose_100pct_strong B_delta=rms_fell_50pct_strong "
        "rule=deck_audio_delta_not_causal_proof]"
    )


def _deck_audio_window_context() -> str:
    return (
        "deck_audio_window_context[source=deck_pair_capture "
        "timeline=pre_action_current pre=-6.0..-1.0 current=-1.0..0.0 "
        "action=-1.0..0.0 per_deck_audio=captured_window_features "
        "A_pre=active_rms_0.020_peak_0.100_flux_0.004 "
        "A_current=active_rms_0.040_peak_0.120_flux_0.009 "
        "A_delta=rms_rose_100pct_strong "
        "B_pre=active_rms_0.030_peak_0.110_flux_0.006 "
        "B_current=active_rms_0.020_peak_0.090_flux_0.004 "
        "B_delta=rms_fell_33pct_clear "
        "rule=deck_audio_window_not_causal_or_quality_verdict]"
    )


def _deck_audio_window_evidence() -> str:
    return (
        "deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_active_pre_0.030_current_0.020"
    )


def test_merge_viber_live_context_frame_combines_deck_and_recent_moves():
    context: dict = {}

    flat_flags = main_mod._merge_viber_live_context_frame(
        context,
        {
            "live_context_schema_version": 2,
            "live_context_capabilities": _live_context_capabilities(),
            "deck": "A",
            "audible": True,
            "phase": "groove",
            "bpm": 128.0,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "camelot": "8A",
                    "confidence": 0.82,
                    "source": "rekordbox_xml",
                }
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 64,
                "deck_confidence": 0.82,
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
            },
            "deck_source_context": (
                "deck_source_context[identity_state=MusicState.deck_state "
                "primary=nowplaying_controller_attribution_to_library_cache "
                "resolved=A unresolved=B sources=rekordbox_xml live_db=not_read "
                "event_xml=diagnostic_only second_deck=independent_source_required "
                "rule=unresolved_deck_is_not_transition_evidence]"
            ),
            "deck_source_status": _deck_source_status(),
            "deck_audio_separation_context": _deck_audio_separation_context(),
            "audio_part_context": _audio_part_context(),
            "audio_delta": ["sub energy fell 50% (strong)"],
            "audio_window_context": (
                "audio_window_context[P1=master_global_mix P1_heard=true "
                "timeline=past_action_future move_anchor=A_low_cut_to_killed@-0.3s:inside_P1 "
                "future=not_attached deckA_audio=not_attached deckB_audio=not_attached "
                "per_deck_audio=structured_text_only duplicate_audio=same_master_not_deck_split "
                "deck_separation=deck_lanes_context lane_aliases=deck1:A,deck2:B "
                "action=-1.0..0.0 rule=time_alignment_not_outcome_verdict]"
            ),
            "audio_window_map": _audio_window_map(),
            "live_evidence": {
                "mix": [
                    "deck_audio_support=single_deck_A",
                    "transition_block=single_resolved_deck",
                    "deck_lanes=A_known_route_dominant+B_unknown_route_dominant",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_dominant",
                ],
                "refs": [
                    "mix:deck_audio_support=single_deck_A",
                    "mix:transition_block=single_resolved_deck",
                    "mix:deck_lanes=A_known_route_dominant+B_unknown_route_dominant",
                    "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_dominant",
                ],
            },
            "music": 0.9,
        },
    )
    snap_flags = main_mod._merge_viber_live_context_frame(
        context,
        {
            "type": "ipc.session.snapshot",
            "payload": {
                "midi_events": [
                    {"control": "A_low: cut->killed", "value": None},
                    {"control": "xfader->center", "value": None},
                ]
            },
        },
    )

    assert flat_flags == {
        "changed": True,
        "flat_deck_frame": True,
        "session_snapshot": False,
    }
    assert snap_flags == {
        "changed": True,
        "flat_deck_frame": False,
        "session_snapshot": True,
    }
    assert context["deck"] == "A"
    assert context["live_context_schema_version"] == 2
    assert "audio_part_context" in context["live_context_capabilities"]
    assert "deck_audio_separation_context" in context["live_context_capabilities"]
    assert "audio_window_map" in context["live_context_capabilities"]
    assert context["music"] == 0.9
    assert context["deck_source_context"].startswith("deck_source_context[")
    assert "second_deck=independent_source_required" in context["deck_source_context"]
    assert context["deck_source_status"]["resolution"] == "library_cache_match"
    assert context["audio_delta"] == ["sub energy fell 50% (strong)"]
    assert context["deck_audio_separation_context"] == _deck_audio_separation_context()
    assert context["audio_part_context"] == _audio_part_context()
    assert context["audio_window_context"].startswith("audio_window_context[")
    assert context["audio_window_map"]["p1"] == "master_global_mix"
    assert context["live_evidence"]["mix"] == [
        "deck_audio_support=single_deck_A",
        "transition_block=single_resolved_deck",
        "deck_lanes=A_known_route_dominant+B_unknown_route_dominant",
        "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_dominant",
    ]
    assert context["recent_moves"] == ["A_low: cut->killed", "xfader->center"]
    preview = render_live_context_preview(context)
    assert "live_context[" in preview
    assert "live_context_transport[" in preview
    assert "schema=2" in preview
    assert "capabilities=" in preview
    assert "deck_source_status" in preview
    assert "audio_part_context" in preview
    assert "audio_window_map" in preview
    assert "status=fresh_schema_v2" in preview
    assert "rule=transport_receipt_not_musical_evidence" in preview
    assert "src=rekordbox_xml" in preview
    assert "second_deck_identity=unknown_or_suppressed" in preview
    assert "deck_lanes_context[" in preview
    assert "deck_reference_context[" in preview
    assert "deck_source_context[" in preview
    assert "deck1=A" in preview
    assert "deck2=B" in preview
    assert "second_deck=independent_source_required" in preview
    assert "rule=unresolved_deck_is_not_transition_evidence" in preview
    assert "audio=P1_global_mix" in preview
    assert "B(identity=unknown" in preview
    assert "mixer_context[" in preview
    assert "deck_audio_context[" in preview
    assert "source=global_mix" in preview
    assert "support=two_deck_route" in preview
    assert "audio_part_context[" in preview
    assert "surface=live_context" in preview
    assert "P1=live_global_mix" in preview
    assert "P1_model_heard=false" in preview
    assert "P1_deck_audio=global_mix_not_stems" in preview
    assert "audio_window_context[" in preview
    assert "audio_window_map[" in preview
    assert "P1=master_global_mix" in preview
    assert "future=not_attached" in preview
    assert "deckA_audio=not_attached" in preview
    assert "deckB_audio=not_attached" in preview
    assert "move_context[" in preview
    assert "transition_block=single_resolved_deck" in preview
    assert "deck_change_context[" in preview
    assert "A_low(now=killed route=dominant)" in preview
    assert "move_effect_context[" in preview
    assert "sub energy fell 50% (strong)" in preview
    assert "rule=move_effect_prediction_and_measurement_agree" in preview
    assert "live_evidence[" in preview
    assert "mix:transition_block=single_resolved_deck" in preview
    assert "mix:deck_lanes=A_known_route_dominant+B_unknown_route_dominant" in preview
    assert (
        "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_dominant" in preview
    )
    assert "claim_policy[" in preview
    assert "multi_deck_outcome=blocked" in preview


def test_merge_viber_live_context_frame_resets_stale_live_evidence_packets():
    context = {
        "live_evidence": {
            "mix": ["deck_lanes=A_known_route_dominant+B_unknown_route_muted"],
            "refs": ["mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted"],
        }
    }

    flags = main_mod._merge_viber_live_context_frame(
        context,
        {
            "deck_state": {},
            "live_evidence": {
                "mix": ["transition_block=single_resolved_deck"],
                "refs": ["mix:transition_block=single_resolved_deck"],
                "midi": [{"key": "A_low_cut_to_killed", "t": 42.04}],
            },
        },
    )

    assert flags["flat_deck_frame"] is True
    assert context["live_evidence"]["mix"] == [
        "transition_block=single_resolved_deck",
    ]
    assert context["live_evidence"]["refs"] == [
        "mix:transition_block=single_resolved_deck",
    ]
    assert context["live_evidence"]["midi"] == [{"key": "A_low_cut_to_killed", "t": 42.0}]


def test_merge_viber_live_context_frame_prioritizes_safety_evidence_under_cap():
    context = {
        "live_evidence": {
            "mix": [f"noise_{index}=kept" for index in range(8)],
            "refs": [f"mix:noise_{index}=kept" for index in range(8)],
        }
    }

    main_mod._merge_viber_live_context_frame(
        context,
        {
            "deck_state": {},
            "live_evidence": {
                "mix": [
                    "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                    "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
                    "transition_block=single_resolved_deck",
                    "deck_audio_capture=A_active+B_silent",
                    "deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000",
                    "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                    (
                        "deck_audio_window=A_active_pre_0.020_current_0.040+"
                        "B_silent_pre_0.030_current_0.000"
                    ),
                ],
                "refs": [
                    "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                    "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                    "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
                    "mix:transition_block=single_resolved_deck",
                    "mix:deck_audio_capture=A_active+B_silent",
                    "mix:deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000",
                    "mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                    (
                        "mix:deck_audio_window=A_active_pre_0.020_current_0.040+"
                        "B_silent_pre_0.030_current_0.000"
                    ),
                ],
            },
        },
    )

    assert len(context["live_evidence"]["mix"]) == 8
    assert (
        "deck_lanes=A_known_route_dominant+B_unknown_route_muted" in context["live_evidence"]["mix"]
    )
    assert (
        "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted"
        in context["live_evidence"]["mix"]
    )
    assert (
        "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none"
        in context["live_evidence"]["mix"]
    )
    assert "transition_block=single_resolved_deck" in context["live_evidence"]["mix"]
    assert "deck_audio_capture=A_active+B_silent" in context["live_evidence"]["mix"]
    assert (
        "deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000"
        in context["live_evidence"]["mix"]
    )
    assert (
        "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong"
        in context["live_evidence"]["mix"]
    )
    assert (
        "deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_silent_pre_0.030_current_0.000"
    ) in context["live_evidence"]["mix"]
    assert "noise_0=kept" not in context["live_evidence"]["mix"]
    assert (
        "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted"
        in context["live_evidence"]["refs"]
    )
    assert (
        "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted"
        in context["live_evidence"]["refs"]
    )
    assert (
        "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none"
        in context["live_evidence"]["refs"]
    )
    assert "mix:transition_block=single_resolved_deck" in context["live_evidence"]["refs"]
    assert "mix:deck_audio_capture=A_active+B_silent" in context["live_evidence"]["refs"]
    assert (
        "mix:deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000"
        in context["live_evidence"]["refs"]
    )
    assert (
        "mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong"
        in context["live_evidence"]["refs"]
    )
    assert (
        "mix:deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_silent_pre_0.030_current_0.000"
    ) in context["live_evidence"]["refs"]
    assert "mix:noise_0=kept" not in context["live_evidence"]["refs"]


def test_viber_normalization_derives_reference_source_evidence_from_deck_frame():
    context = {
        "deck": "mix",
        "audible": False,
        "music": 0.0,
        "deck_state": {},
        "deck_mixer": {
            "connected": True,
            "xfader": 64,
            "deck_confidence": 0.5,
            "A": {"vol": 127, "eq_low": 79, "eq_mid": 71, "eq_hi": 77, "filter": 64},
            "B": {"vol": 127, "eq_low": 70, "eq_mid": 77, "eq_hi": 76, "filter": 64},
        },
        "live_evidence": {
            "mix": ["deck_audio_support=two_deck_route"],
            "refs": ["mix:deck_audio_support=two_deck_route"],
        },
    }

    normalized = normalize_live_context_for_viber(context)
    readiness = main_mod._viber_live_context_readiness(
        context,
        frames_seen=1,
        flat_deck_frame_seen=True,
        session_snapshot_seen=False,
    )

    assert normalized is not None
    assert (
        "deck_reference=deck1_A_unknown_route_dominant+deck2_B_unknown_route_dominant"
        in normalized["live_evidence"]["mix"]
    )
    assert (
        "deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none"
        in normalized["live_evidence"]["mix"]
    )
    assert "transition_block=no_resolved_decks" in normalized["live_evidence"]["mix"]
    assert (
        "mix:deck_reference=deck1_A_unknown_route_dominant+deck2_B_unknown_route_dominant"
        in normalized["live_evidence"]["refs"]
    )
    assert (
        "mix:deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none"
        in normalized["live_evidence"]["refs"]
    )
    assert readiness["checks"]["deck_reference_evidence_seen"] is True
    assert readiness["checks"]["deck_reference_route_evidence_seen"] is True
    assert readiness["checks"]["deck_source_evidence_seen"] is True
    assert readiness["checks"]["transition_gate_seen"] is True
    assert "live_evidence had no citable deck_reference atom" not in readiness["blockers"]
    assert "live_evidence had no citable deck_source atom" not in readiness["blockers"]


def test_merge_viber_live_context_frame_clears_stale_evidence_on_explicit_deck_state():
    context = {
        "music": 0.2,
        "audio_delta": ["sub energy fell 50% (strong)"],
        "live_evidence": {"mix": ["transition_block=single_resolved_deck"]},
    }

    flags = main_mod._merge_viber_live_context_frame(
        context,
        {
            "deck_state": {},
            "music": 0.01,
            "audio_delta": [],
            "live_evidence": {},
        },
    )

    assert flags["flat_deck_frame"] is True
    assert context["music"] == 0.2
    assert context["audio_delta"] == ["sub energy fell 50% (strong)"]
    assert "live_evidence" not in context


def test_merge_viber_live_context_frame_resets_live_evidence_for_new_deck_frame():
    context = {
        "deck_state": {"A": {"title": "Old", "confidence": 0.9}},
        "live_evidence": {
            "mix": [
                "transition_block=single_resolved_deck",
                "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
            ],
            "refs": ["mix:transition_block=single_resolved_deck"],
        },
    }

    flags = main_mod._merge_viber_live_context_frame(
        context,
        {
            "deck_state": {},
            "deck_mixer": {
                "connected": True,
                "xfader": 64,
                "A": {"vol": 127, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 127, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "live_evidence": {
                "mix": ["deck_audio_support=two_deck_route"],
                "refs": ["mix:deck_audio_support=two_deck_route"],
            },
        },
    )

    assert flags["flat_deck_frame"] is True
    assert context["deck_state"] == {}
    assert context["live_evidence"] == {
        "mix": ["deck_audio_support=two_deck_route"],
        "refs": ["mix:deck_audio_support=two_deck_route"],
    }


def test_viber_live_context_readiness_reports_physical_proof_blockers():
    readiness = main_mod._viber_live_context_readiness(
        {
            "deck": "A",
            "audible": False,
            "music": 0.0,
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.82}},
            "deck_mixer": {"connected": False},
            "live_evidence": {
                "mix": [
                    "transition_block=single_resolved_deck",
                    "deck_lanes=A_known_route_unknown+B_unknown_route_unknown",
                    "deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown",
                ],
                "refs": ["mix:transition_block=single_resolved_deck"],
            },
        },
        frames_seen=2,
        flat_deck_frame_seen=True,
        session_snapshot_seen=False,
    )

    assert readiness["ready"] is False
    assert readiness["diagnosis"] == "stale_live_runtime"
    assert readiness["stale_live_runtime"] is True
    assert "Restart the Vibemix live session" in readiness["next_action"]
    assert readiness["checks"]["deck_state_resolved"] is True
    assert readiness["checks"]["deck_lane_context_seen"] is True
    assert readiness["checks"]["deck_reference_context_seen"] is True
    assert readiness["checks"]["deck_source_context_seen"] is True
    assert readiness["checks"]["transition_gate_seen"] is True
    assert readiness["checks"]["deck_lane_evidence_seen"] is True
    assert readiness["checks"]["deck_lane_route_evidence_seen"] is False
    assert readiness["checks"]["deck_reference_evidence_seen"] is True
    assert readiness["checks"]["deck_reference_route_evidence_seen"] is False
    assert readiness["checks"]["deck_source_evidence_seen"] is True
    assert "deck_state had no citable track_id at confidence floor" in readiness["blockers"]
    assert "controller mixer posture was not connected" in readiness["blockers"]
    assert (
        "controller mixer posture did not include both deck A and deck B" in readiness["blockers"]
    )
    assert "no recent controller moves were observed" in readiness["blockers"]
    assert "live master audio was not observed above the audible floor" in readiness["blockers"]
    assert "no bounded audio_delta was observed" in readiness["blockers"]
    assert "live_evidence deck_lanes atom had no concrete deck route tiers" in readiness["blockers"]
    assert (
        "live_evidence deck_reference atom had no concrete deck route tiers"
        in readiness["blockers"]
    )
    assert "live_evidence had no citable deck_source atom" not in readiness["blockers"]


def test_viber_live_context_readiness_explains_deck_identity_source_blockers():
    readiness = main_mod._viber_live_context_readiness(
        {
            "live_context_schema_version": 2,
            "live_context_capabilities": _live_context_capabilities(),
            "deck": "A",
            "audible": False,
            "music": 0.0,
            "deck_state": {},
            "deck_mixer": {
                "connected": True,
                "xfader": 0,
                "A": {"vol": 127, "play": True},
                "B": {"vol": 0, "play": False},
            },
            "deck_source_status": {
                "controller": "present",
                "controller_connection": "connected",
                "library": "present",
                "library_tracks": "24",
                "library_source": "rekordbox_xml",
                "library_match": "ambiguous_label",
                "nowplaying": "deck_candidate",
                "nowplaying_title": "seen",
                "audible_deck": "A",
                "resolution": "library_miss",
                "second_deck_source": "suppressed_requires_independent_source",
                "screen_vision": "disabled",
            },
            "live_evidence": {
                "mix": [
                    "transition_block=no_resolved_decks",
                    "deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none",
                ],
                "refs": ["mix:transition_block=no_resolved_decks"],
            },
        },
        frames_seen=2,
        flat_deck_frame_seen=True,
        session_snapshot_seen=False,
    )

    assert readiness["ready"] is False
    assert readiness["diagnosis"] == "missing_physical_proof"
    assert readiness["deck_source_status"]["library_match"] == "ambiguous_label"
    assert (
        "deck identity source: Now Playing did not match a unique library row"
        in readiness["blockers"]
    )
    assert "second deck identity source requires independent deck evidence" in readiness["blockers"]
    assert "second deck identity source is not enabled" in readiness["blockers"]


def test_viber_live_context_readiness_diagnoses_stale_socket_before_physical_proof():
    readiness = main_mod._viber_live_context_readiness(
        {
            "deck": "B",
            "audible": False,
            "music": 0.0,
            "deck_state": {},
            "deck_mixer": {
                "connected": True,
                "A": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 127, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "live_evidence": {
                "mix": [
                    "transition_block=no_resolved_decks",
                    "deck_lanes=A_unknown_route_muted+B_unknown_route_dominant",
                    "deck_reference=deck1_A_unknown_route_muted+deck2_B_unknown_route_dominant",
                    "deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none",
                ],
                "refs": ["mix:transition_block=no_resolved_decks"],
            },
        },
        frames_seen=6,
        flat_deck_frame_seen=True,
        session_snapshot_seen=True,
    )

    assert readiness["ready"] is False
    assert readiness["diagnosis"] == "stale_live_runtime"
    assert readiness["stale_live_runtime"] is True
    assert readiness["live_context_schema_version"] == 0
    assert readiness["missing_capabilities"] == [
        "audio_delta",
        "audio_part_context",
        "audio_window_map",
        "deck_audio_delta_context",
        "deck_audio_features_context",
        "deck_audio_separation_context",
        "deck_audio_window_context",
        "deck_source_status",
        "live_evidence",
    ]
    assert "live_context_schema_version=2" in readiness["next_action"]
    assert (
        "live socket did not advertise structured live-context schema v2" in readiness["blockers"]
    )


def test_viber_live_context_readiness_requires_source_for_citable_track():
    readiness = main_mod._viber_live_context_readiness(
        {
            "deck": "A",
            "live_context_schema_version": 2,
            "live_context_capabilities": _live_context_capabilities(),
            "audible": True,
            "music": 0.2,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "track-1",
                    "camelot": "8A",
                    "confidence": 0.82,
                }
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 32,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "recent_moves": ["A_low: cut->killed"],
            "deck_source_status": _deck_source_status(),
            "audio_delta": ["sub energy fell 50% (strong)"],
            "audio_window_map": _audio_window_map(),
            "live_evidence": {
                "mix": [
                    "transition_block=single_resolved_deck",
                    "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                ],
                "refs": [
                    "mix:transition_block=single_resolved_deck",
                    "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                    "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                ],
            },
        },
        frames_seen=12,
        flat_deck_frame_seen=True,
        session_snapshot_seen=True,
    )

    assert readiness["ready"] is False
    assert readiness["checks"]["deck_state_citable_track"] is True
    assert readiness["checks"]["deck_state_source_provenance"] is False
    assert readiness["checks"]["deck_lane_context_seen"] is True
    assert readiness["checks"]["deck_reference_context_seen"] is True
    assert readiness["checks"]["deck_source_context_seen"] is True
    assert readiness["checks"]["deck_lane_evidence_seen"] is True
    assert readiness["checks"]["deck_lane_route_evidence_seen"] is True
    assert readiness["checks"]["deck_reference_evidence_seen"] is True
    assert readiness["checks"]["deck_reference_route_evidence_seen"] is True
    assert readiness["checks"]["deck_source_evidence_seen"] is True
    assert (
        "deck_state had no trusted source provenance for a citable track" in readiness["blockers"]
    )
    assert "live_evidence had no citable deck_source atom" not in readiness["blockers"]


def test_viber_live_context_readiness_names_too_narrow_deck_capture_device():
    readiness = main_mod._viber_live_context_readiness(
        {
            "live_context_schema_version": 2,
            "live_context_capabilities": _live_context_capabilities(),
            "deck": "A",
            "audible": True,
            "music": 0.2,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "track-1",
                    "confidence": 0.82,
                    "source": "folder_cache",
                }
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 32,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "recent_moves": ["A_low: cut->killed"],
            "deck_source_status": _deck_source_status(),
            "deck_audio_separation_context": (
                "deck_audio_separation_context[requested_device=BlackHole_2ch "
                "capture_device=BlackHole_2ch input_channels=2 opened_channels=2 "
                "sample_rate=48000 device_capacity=stereo_or_less mode=global_mix_only "
                "required_opened_channels=4 "
                "capture_reason=capture_device_too_few_channels "
                "routing_hint=rekordbox_settings_A:0+1+B:2+3 "
                "routing_hint_rule=output_routing_not_live_audio_proof "
                "setup_block=capture_device_too_few_channels "
                "current_capture=P1_global_mix gemini_audio=mono_downmix_of_capture "
                "deckA_audio=not_captured deckB_audio=not_captured "
                "per_deck_audio=not_attached isolated_decks=false "
                "upgrade_path=multi_channel_deck_pair_capture "
                "rule=separation_capability_not_outcome]"
            ),
            "audio_delta": ["sub energy fell 50% (strong)"],
            "audio_window_map": _audio_window_map(),
            "live_evidence": {
                "mix": [
                    "transition_block=single_resolved_deck",
                    "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                    "deck_source=deck1_A_known_src_folder_cache+deck2_B_unknown_src_none",
                ],
                "refs": [
                    "mix:transition_block=single_resolved_deck",
                    "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                    "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                    "mix:deck_source=deck1_A_known_src_folder_cache+deck2_B_unknown_src_none",
                ],
            },
        },
        frames_seen=12,
        flat_deck_frame_seen=True,
        session_snapshot_seen=True,
    )

    assert readiness["ready"] is False
    assert "deck-pair audio capture was not configured in the live packet" in readiness[
        "blockers"
    ]
    assert (
        "deck-pair route hint requires a multichannel capture device/opened channels"
        in readiness["blockers"]
    )


def test_viber_live_context_sample_complete_waits_for_proof_when_required():
    cold_context = {
        "deck": "A",
        "deck_state": {"A": {"title": "Strobe", "confidence": 0.82}},
    }

    assert (
        main_mod._viber_live_context_sample_complete(
            cold_context,
            frames_seen=2,
            flat_deck_frame_seen=True,
            session_snapshot_seen=True,
            require_proof=False,
        )
        is True
    )
    assert (
        main_mod._viber_live_context_sample_complete(
            cold_context,
            frames_seen=2,
            flat_deck_frame_seen=True,
            session_snapshot_seen=True,
            require_proof=True,
        )
        is False
    )


def test_viber_live_context_readiness_passes_for_deck_controller_audio_evidence():
    readiness = main_mod._viber_live_context_readiness(
        {
            "live_context_schema_version": 2,
            "live_context_capabilities": _live_context_capabilities(),
            "deck": "A",
            "audible": True,
            "music": 0.2,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "track-1",
                    "camelot": "8A",
                    "confidence": 0.82,
                    "source": "folder_cache",
                },
                "B": {
                    "title": "Signal",
                    "track_id": "track-2",
                    "camelot": "9A",
                    "confidence": 0.84,
                    "source": "folder_cache",
                },
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 32,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 96, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "recent_moves": ["A_low: cut->killed"],
            "deck_source_status": _deck_source_status(),
            "deck_audio_separation_context": _deck_pair_audio_separation_context().replace(
                "A_active+B_silent",
                "A_active+B_active",
            ),
            "deck_audio_features_context": _deck_audio_features_context()
            .replace("B_activity=silent", "B_activity=active")
            .replace("B_rms=0.000", "B_rms=0.030")
            .replace("B_peak=0.000", "B_peak=0.110")
            .replace("B_zcr=0.000", "B_zcr=0.035"),
            "deck_audio_delta_context": _deck_audio_delta_context(),
            "deck_audio_window_context": _deck_audio_window_context(),
            "audio_delta": ["sub energy fell 50% (strong)"],
            "audio_window_map": _audio_window_map(),
            "live_evidence": {
                "mix": [
                    "transition_candidate=two_resolved_decks_captured_audio",
                    "deck_lanes=A_known_route_dominant+B_known_route_present",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "deck_source=deck1_A_known_src_folder_cache+deck2_B_known_src_folder_cache",
                    "deck_audio_capture=A_active+B_active",
                    "deck_audio_features=A_active_rms_0.020+B_active_rms_0.030",
                    "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                    _deck_audio_window_evidence(),
                ],
                "refs": [
                    "mix:transition_candidate=two_resolved_decks_captured_audio",
                    "mix:deck_lanes=A_known_route_dominant+B_known_route_present",
                    "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "mix:deck_source=deck1_A_known_src_folder_cache+deck2_B_known_src_folder_cache",
                    "mix:deck_audio_capture=A_active+B_active",
                    "mix:deck_audio_features=A_active_rms_0.020+B_active_rms_0.030",
                    "mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                    "mix:" + _deck_audio_window_evidence(),
                ],
            },
        },
        frames_seen=12,
        flat_deck_frame_seen=True,
        session_snapshot_seen=True,
    )

    assert readiness == {
        "ready": True,
        "diagnosis": "ready",
        "next_action": "Live Viber deck/audio context proof is ready.",
        "checks": {
            "frames_seen": True,
            "flat_deck_frame_seen": True,
            "live_context_schema_seen": True,
            "live_context_capabilities_seen": True,
            "deck_state_resolved": True,
            "deck_state_citable_track": True,
            "deck_state_source_provenance": True,
            "deck_state_pair_resolved": True,
            "deck_state_pair_citable_tracks": True,
            "deck_state_pair_source_provenance": True,
            "deck_lane_context_seen": True,
            "deck_reference_context_seen": True,
            "deck_source_context_seen": True,
            "deck_source_status_seen": True,
            "controller_connected": True,
            "controller_deck_posture_seen": True,
            "recent_moves_seen": True,
            "audio_part_context_seen": True,
            "deck_audio_separation_context_seen": True,
            "deck_audio_features_context_seen": True,
            "deck_audio_delta_context_seen": True,
            "deck_audio_window_context_seen": True,
            "deck_pair_capture_configured": True,
            "deck_audio_capture_evidence_seen": True,
            "deck_audio_capture_active": True,
            "deck_audio_capture_both_active": True,
            "deck_audio_features_evidence_seen": True,
            "deck_audio_delta_evidence_seen": True,
            "deck_audio_window_evidence_seen": True,
            "audio_window_context_seen": True,
            "audio_window_map_seen": True,
            "audio_part_window_labels_consistent": True,
            "audio_observed": True,
            "audio_delta_seen": True,
            "live_evidence_seen": True,
            "transition_gate_seen": True,
            "deck_lane_evidence_seen": True,
            "deck_lane_route_evidence_seen": True,
            "deck_reference_evidence_seen": True,
            "deck_reference_route_evidence_seen": True,
            "deck_source_evidence_seen": True,
        },
        "blockers": [],
        "stale_live_runtime": False,
        "resolved_decks": ["A", "B"],
        "citable_decks": ["A", "B"],
        "sourced_decks": ["A", "B"],
        "mixer_posture_sides": ["A", "B"],
        "max_music": 0.2,
        "live_context_schema_version": 2,
        "missing_capabilities": [],
        "deck_source_status": {
            "controller": "connected",
            "controller_connection": "connected",
            "library": "present",
            "library_tracks": "24",
            "library_source": "rekordbox_xml",
            "library_match": "matched",
            "nowplaying": "blocked_non_deck_owner",
            "nowplaying_owner": "com.apple.webkit.gpu",
            "nowplaying_title": "pink_floyd",
            "audible_deck": "a",
            "resolution": "library_cache_match",
            "resolved_side": "a",
            "screen_vision": "disabled",
        },
        "session_snapshot_seen": True,
    }


def test_viber_live_context_readiness_rejects_mismatched_deck_audio_part_labels():
    readiness = main_mod._viber_live_context_readiness(
        {
            "live_context_schema_version": 2,
            "live_context_capabilities": _live_context_capabilities(),
            "deck": "mix",
            "audible": True,
            "music": 0.2,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "track-1",
                    "camelot": "8A",
                    "confidence": 0.82,
                    "source": "folder_cache",
                },
                "B": {
                    "title": "Signal",
                    "track_id": "track-2",
                    "camelot": "9A",
                    "confidence": 0.84,
                    "source": "folder_cache",
                },
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 48,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 96, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "recent_moves": ["xfader: A->center"],
            "deck_source_status": _deck_source_status(),
            "deck_audio_separation_context": _deck_pair_audio_separation_context().replace(
                "A_active+B_silent",
                "A_active+B_active",
            ),
            "deck_audio_features_context": _deck_audio_features_context()
            .replace("B_activity=silent", "B_activity=active")
            .replace("B_rms=0.000", "B_rms=0.030")
            .replace("B_peak=0.000", "B_peak=0.110")
            .replace("B_zcr=0.000", "B_zcr=0.035"),
            "deck_audio_delta_context": _deck_audio_delta_context(),
            "deck_audio_window_context": _deck_audio_window_context(),
            "audio_part_context": _deck_pair_audio_part_context("P4", "P5"),
            "audio_window_context": _deck_pair_audio_window_context("P2", "P3"),
            "audio_window_map": _deck_pair_audio_window_map("P2", "P3"),
            "audio_delta": ["sub energy fell 50% (strong)"],
            "live_evidence": {
                "mix": [
                    "transition_candidate=two_resolved_decks_captured_audio",
                    "deck_lanes=A_known_route_dominant+B_known_route_present",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "deck_source=deck1_A_known_src_folder_cache+deck2_B_known_src_folder_cache",
                    "deck_audio_capture=A_active+B_active",
                    "deck_audio_features=A_active_rms_0.020+B_active_rms_0.030",
                    "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                    _deck_audio_window_evidence(),
                ],
                "refs": [
                    "mix:transition_candidate=two_resolved_decks_captured_audio",
                    "mix:deck_lanes=A_known_route_dominant+B_known_route_present",
                    "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "mix:deck_source=deck1_A_known_src_folder_cache+deck2_B_known_src_folder_cache",
                    "mix:deck_audio_capture=A_active+B_active",
                    "mix:deck_audio_features=A_active_rms_0.020+B_active_rms_0.030",
                    "mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                    "mix:" + _deck_audio_window_evidence(),
                ],
            },
        },
        frames_seen=12,
        flat_deck_frame_seen=True,
        session_snapshot_seen=True,
    )

    assert readiness["ready"] is False
    assert readiness["checks"]["audio_part_context_seen"] is True
    assert readiness["checks"]["audio_window_context_seen"] is True
    assert readiness["checks"]["audio_window_map_seen"] is False
    assert readiness["checks"]["audio_part_window_labels_consistent"] is False
    assert "audio Part labels disagreed with audio_window deck labels" in readiness["blockers"]
    assert "no structured audio_window_map was observed" in readiness["blockers"]


def test_viber_live_context_readiness_requires_both_deck_audio_lanes_active():
    readiness = main_mod._viber_live_context_readiness(
        {
            "live_context_schema_version": 2,
            "live_context_capabilities": _live_context_capabilities(),
            "deck": "mix",
            "audible": True,
            "music": 0.2,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "track-1",
                    "camelot": "8A",
                    "confidence": 0.82,
                    "source": "folder_cache",
                },
                "B": {
                    "title": "Signal",
                    "track_id": "track-2",
                    "camelot": "9A",
                    "confidence": 0.84,
                    "source": "folder_cache",
                },
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 48,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 96, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "recent_moves": ["xfader: A->center"],
            "deck_source_status": _deck_source_status(),
            "deck_audio_separation_context": (
                _deck_pair_audio_separation_context_with_route_diagnosis()
            ),
            "deck_audio_features_context": _deck_audio_features_context(),
            "deck_audio_delta_context": _deck_audio_delta_context(),
            "deck_audio_window_context": _deck_audio_window_context(),
            "audio_part_context": _audio_part_context(),
            "audio_delta": ["sub energy fell 50% (strong)"],
            "audio_window_map": _audio_window_map(),
            "live_evidence": {
                "mix": [
                    "transition_candidate=two_resolved_decks_captured_audio",
                    "deck_lanes=A_known_route_dominant+B_known_route_present",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "deck_source=deck1_A_known_src_folder_cache+deck2_B_known_src_folder_cache",
                    "deck_audio_capture=A_active+B_silent",
                    "deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000",
                    "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                    (
                        "deck_audio_window=A_active_pre_0.020_current_0.040+"
                        "B_silent_pre_0.030_current_0.000"
                    ),
                ],
                "refs": [
                    "mix:transition_candidate=two_resolved_decks_captured_audio",
                    "mix:deck_lanes=A_known_route_dominant+B_known_route_present",
                    "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "mix:deck_source=deck1_A_known_src_folder_cache+deck2_B_known_src_folder_cache",
                    "mix:deck_audio_capture=A_active+B_silent",
                    "mix:deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000",
                    "mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                    (
                        "mix:deck_audio_window=A_active_pre_0.020_current_0.040+"
                        "B_silent_pre_0.030_current_0.000"
                    ),
                ],
            },
        },
        frames_seen=12,
        flat_deck_frame_seen=True,
        session_snapshot_seen=True,
    )

    assert readiness["ready"] is False
    assert readiness["checks"]["deck_audio_capture_active"] is True
    assert readiness["checks"]["deck_audio_capture_both_active"] is False
    assert readiness["deck_audio_route_diagnosis"]["inactive_sides"] == "B"
    assert readiness["deck_audio_route_diagnosis"]["active_unassigned_pairs"] == "none"
    assert "deck_audio_capture did not show active audio on both deck lanes" in readiness[
        "blockers"
    ]


def test_viber_live_context_readiness_requires_rendered_deck_lane_context():
    readiness = main_mod._viber_live_context_readiness(
        {
            "deck": "none",
            "audible": True,
            "music": 0.2,
            "deck_state": {},
            "deck_mixer": {"connected": False},
            "recent_moves": ["A_low: cut->killed"],
            "audio_window_context": (
                "audio_window_context[P1=master_global_mix P1_heard=true "
                "timeline=past_action_future move_anchor=A_low_cut_to_killed@age_unknown "
                "future=not_attached deckA_audio=not_attached deckB_audio=not_attached "
                "per_deck_audio=structured_text_only duplicate_audio=same_master_not_deck_split "
                "deck_separation=deck_lanes_context lane_aliases=deck1:A,deck2:B "
                "action=-1.0..0.0 rule=time_alignment_not_outcome_verdict]"
            ),
            "audio_delta": ["sub energy fell 50% (strong)"],
            "live_evidence": {
                "mix": [
                    "transition_block=no_resolved_decks",
                    "deck_lanes=A_unknown_route_unknown+B_unknown_route_unknown",
                ],
                "refs": [
                    "mix:transition_block=no_resolved_decks",
                    "mix:deck_lanes=A_unknown_route_unknown+B_unknown_route_unknown",
                ],
            },
        },
        frames_seen=12,
        flat_deck_frame_seen=True,
        session_snapshot_seen=True,
    )

    assert readiness["ready"] is False
    assert readiness["checks"]["deck_lane_context_seen"] is False
    assert readiness["checks"]["deck_reference_context_seen"] is False
    assert readiness["checks"]["deck_source_context_seen"] is False
    assert readiness["checks"]["deck_lane_evidence_seen"] is True
    assert readiness["checks"]["deck_lane_route_evidence_seen"] is False
    assert readiness["checks"]["deck_reference_evidence_seen"] is False
    assert readiness["checks"]["deck_reference_route_evidence_seen"] is False
    assert readiness["checks"]["deck_source_evidence_seen"] is False
    assert "rendered live context had no per-deck lane map" in readiness["blockers"]
    assert "rendered live context had no deck1/deck2 reference map" in readiness["blockers"]
    assert "rendered live context had no deck source/provenance map" in readiness["blockers"]
    assert "live_evidence had no citable deck_reference atom" in readiness["blockers"]
    assert (
        "live_evidence deck_reference atom had no concrete deck route tiers"
        in readiness["blockers"]
    )
    assert "live_evidence had no citable deck_source atom" in readiness["blockers"]


def test_viber_live_context_readiness_ignores_untrusted_audio_window_context():
    readiness = main_mod._viber_live_context_readiness(
        {
            "deck": "none",
            "audible": False,
            "deck_state": {},
            "audio_window_context": (
                "audio_window_context[P1=master_global_mix deckA_audio=not_attached "
                "deckB_audio=not_attached]"
            ),
        },
        frames_seen=12,
        flat_deck_frame_seen=True,
        session_snapshot_seen=True,
    )

    assert readiness["checks"]["audio_window_context_seen"] is False
    assert "no time-aligned audio_window_context was observed" in readiness["blockers"]


def test_merge_viber_live_context_frame_keeps_moves_across_empty_delta_snapshot():
    context = {
        "deck": "A",
        "deck_state": {"A": {"title": "Strobe", "camelot": "8A", "confidence": 0.8}},
        "recent_moves": ["A_low: cut->killed"],
    }

    flags = main_mod._merge_viber_live_context_frame(
        context,
        {"type": "ipc.session.snapshot", "payload": {"midi_events": []}},
    )

    assert flags == {
        "changed": False,
        "flat_deck_frame": False,
        "session_snapshot": True,
    }
    assert context["recent_moves"] == ["A_low: cut->killed"]
    assert "recent_moves[A_low: cut->killed]" in render_live_context_preview(context)


def test_library_cache_probe_reports_folder_cache_source(tmp_path, monkeypatch):
    monkeypatch.setattr(main_mod.RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    lib = main_mod.RekordboxLibrary()
    lib.tracks = {
        "folder:abc": TrackEntry(
            track_id="folder:abc",
            title="Strobe",
            artist="",
            album="",
            bpm=0.0,
            key="",
            duration_s=120.0,
            cues=(),
            filepath=str(tmp_path / "strobe.wav"),
        )
    }
    lib._write_cache(str(tmp_path), tmp_path.stat().st_mtime)

    status = main_mod._library_cache_probe()

    assert status["loaded"] is True
    assert status["track_count"] == 1
    assert status["source_type"] == "folder_cache"
    assert status["source_path"] == str(tmp_path)


def test_rekordbox_event_probe_reports_empty_vs_live_payload(tmp_path):
    empty_event = tmp_path / "empty.xml"
    empty_event.write_text(
        '<EVENT event_item="" event_item_count="0" '
        'event_controller_item="" event_controller_item_count="0"/>',
        encoding="utf-8",
    )
    live_event = tmp_path / "live.xml"
    live_event.write_text(
        '<EVENT event_item_count="1" event_controller_item_count="2"/>',
        encoding="utf-8",
    )

    assert main_mod._rekordbox_event_probe(empty_event)["has_live_deck_payload"] is False
    live_status = main_mod._rekordbox_event_probe(live_event)
    assert live_status["has_live_deck_payload"] is True
    assert live_status["event_item_count"] == 1
    assert live_status["event_controller_item_count"] == 2


def test_viber_source_status_reports_ws_port_listener(monkeypatch):
    monkeypatch.setattr(
        main_mod,
        "_ws_port_listener_probe",
        lambda: {
            "host": "127.0.0.1",
            "port": 8765,
            "listening": True,
            "pid": 44456,
            "name": "uvicorn",
            "looks_like_vibemix": False,
        },
    )
    monkeypatch.setattr(
        main_mod,
        "rekordbox_deck_output_routing_hint",
        lambda **_kwargs: {
            "source": "rekordbox_settings",
            "settings_file": "rekordbox6/rekordbox3.settings",
            "settings_entry": "audioDeviceManager_PerformanceMode_1178899479",
            "output_device": "Aggregate_Device",
            "mixer_mode": "external",
            "deck_channels": {"A": (0, 1), "B": (2, 3)},
            "fits_input_channels": True,
            "rule": "rekordbox_output_routing_hint_not_live_audio_proof",
        },
    )

    status = main_mod._viber_local_source_status()

    assert status["ws_port_listener"]["listening"] is True
    assert status["ws_port_listener"]["name"] == "uvicorn"
    assert status["rekordbox_deck_routing_hint"]["deck_channels"] == {
        "A": (0, 1),
        "B": (2, 3),
    }
    assert (
        status["rekordbox_deck_routing_hint"]["rule"]
        == "rekordbox_output_routing_hint_not_live_audio_proof"
    )


def test_ws_port_listener_lsof_probe_reports_wrong_owner(monkeypatch):
    def fake_run(argv, **_kwargs):
        if argv[0] == "lsof":
            return subprocess.CompletedProcess(argv, 0, stdout="p44456\ncpython3.12\n", stderr="")
        if argv[0] == "ps":
            return subprocess.CompletedProcess(
                argv,
                0,
                stdout=(
                    "/Users/ozai/projects/mithril/.venv/bin/python3 "
                    "/Users/ozai/projects/mithril/.venv/bin/uvicorn "
                    "dev_api_cors:app --host 127.0.0.1 --port 8765\n"
                ),
                stderr="",
            )
        raise AssertionError(argv)

    monkeypatch.setattr(subprocess, "run", fake_run)

    status = main_mod._ws_port_listener_lsof_probe("127.0.0.1", 8765)

    assert status["listening"] is True
    assert status["pid"] == 44456
    assert status["name"] == "python3.12"
    assert "uvicorn dev_api_cors:app" in status["cmdline"][0]
    assert status["looks_like_vibemix"] is False


def test_ws_port_listener_probe_uses_lsof_when_psutil_denied(monkeypatch):
    class FakePsutil:
        @staticmethod
        def net_connections(kind="tcp"):
            assert kind == "tcp"
            raise PermissionError("denied")

    def fake_run(argv, **_kwargs):
        assert argv[0] == "lsof"
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="")

    monkeypatch.setitem(sys.modules, "psutil", FakePsutil)
    monkeypatch.setattr(subprocess, "run", fake_run)

    status = main_mod._ws_port_listener_probe()

    assert status["listening"] is False
    assert status["fallback"] == "lsof"
    assert status["psutil_error"] == "net_connections failed: PermissionError"
    assert "error" not in status


def test_viber_live_context_hint_names_wrong_port_owner():
    hint = main_mod._viber_live_context_hint(
        "server rejected WebSocket connection: HTTP 403",
        {
            "ws_port_listener": {
                "listening": True,
                "pid": 44456,
                "name": "uvicorn",
                "looks_like_vibemix": False,
            }
        },
    )

    assert "Port 8765 is occupied by uvicorn pid=44456" in hint
    assert "not the Vibemix live socket" in hint


def test_viber_setup_hint_turns_rekordbox_route_hint_into_env(monkeypatch):
    monkeypatch.delenv("VIBEMIX_INPUT_DEVICE", raising=False)
    setup_hint = main_mod._viber_setup_hint_from_source_status(
        {
            "rekordbox_deck_routing_hint": {
                "source": "rekordbox_settings",
                "settings_file": "rekordbox6/rekordbox3.settings",
                "settings_entry": "audioDeviceManager_PerformanceMode_1178899479",
                "output_device": "Aggregate_Device",
                "mixer_mode": "external",
                "deck_channels": {"A": (0, 1), "B": (2, 3)},
                "fits_input_channels": True,
                "rule": "rekordbox_output_routing_hint_not_live_audio_proof",
            }
        },
        {"ready": False},
    )

    assert setup_hint == {
        "status": "rekordbox_route_hint_found",
        "deck_channels": "A=0,1;B=2,3",
        "opened_channels_min": 4,
        "recommended_env": {
            "VIBEMIX_DECK_AUDIO_CHANNELS": "auto",
        },
        "explicit_env": {
            "VIBEMIX_INPUT_DEVICE": "BlackHole 16ch",
            "VIBEMIX_DECK_AUDIO_CHANNELS": "A=0,1;B=2,3",
        },
        "auto_upgrade_input_device": "BlackHole 16ch",
        "output_device": "Aggregate_Device",
        "next_action": (
            "Rekordbox deck route hint found (A=0,1;B=2,3 via Aggregate_Device). "
            "Start the live session with VIBEMIX_DECK_AUDIO_CHANNELS=auto; "
            "Vibemix will try BlackHole 16ch for the deck-pair capture automatically. "
            "Play both decks, move a controller, "
            "then rerun `vibemix library live-context --require-proof`."
        ),
        "rule": "setup_hint_not_live_audio_proof",
    }


def test_viber_setup_hint_respects_explicit_input_device(monkeypatch):
    monkeypatch.setenv("VIBEMIX_INPUT_DEVICE", "BlackHole 2ch")
    setup_hint = main_mod._viber_setup_hint_from_source_status(
        {
            "rekordbox_deck_routing_hint": {
                "source": "rekordbox_settings",
                "settings_file": "rekordbox6/rekordbox3.settings",
                "settings_entry": "audioDeviceManager_PerformanceMode_1178899479",
                "output_device": "Aggregate_Device",
                "mixer_mode": "external",
                "deck_channels": {"A": (0, 1), "B": (2, 3)},
                "fits_input_channels": True,
                "rule": "rekordbox_output_routing_hint_not_live_audio_proof",
            }
        },
        {"ready": False},
    )

    assert setup_hint is not None
    assert setup_hint["recommended_env"] == {
        "VIBEMIX_INPUT_DEVICE": "BlackHole 16ch",
        "VIBEMIX_DECK_AUDIO_CHANNELS": "auto",
    }
    assert setup_hint["auto_upgrade_input_device"] is None
    assert "VIBEMIX_INPUT_DEVICE='BlackHole 16ch'" in setup_hint["next_action"]


def test_viber_live_context_operator_actions_name_connected_controller_gaps():
    actions = main_mod._viber_live_context_operator_actions(
        {
            "ready": False,
            "diagnosis": "missing_physical_proof",
            "next_action": "Collect the missing live proof legs shown in blockers.",
            "checks": {
                "frames_seen": True,
                "flat_deck_frame_seen": True,
                "controller_connected": True,
                "recent_moves_seen": False,
                "audio_observed": True,
                "deck_state_resolved": False,
                "deck_state_pair_resolved": False,
                "deck_pair_capture_configured": True,
                "deck_audio_capture_both_active": False,
            },
            "blockers": [
                "no recent controller moves were observed",
                "deck_audio_capture did not show active audio on both deck lanes",
            ],
        }
    )

    assert [action["code"] for action in actions] == [
        "move_controller",
        "resolve_deck_identity",
        "feed_both_deck_lanes",
    ]
    assert "one active deck lane" in actions[-1]["detail"]
    assert "BlackHole channels 1/2" in actions[-1]["detail"]
    assert "Deck 2 to channels 3/4" in actions[-1]["detail"]
    assert "deck_audio_capture=A_active+B_active" in actions[-1]["detail"]


def test_viber_live_context_operator_actions_include_library_index_setup():
    actions = main_mod._viber_live_context_operator_actions(
        {
            "ready": False,
            "diagnosis": "missing_physical_proof",
            "checks": {
                "frames_seen": True,
                "flat_deck_frame_seen": True,
                "controller_connected": True,
                "recent_moves_seen": False,
                "audio_observed": True,
                "deck_state_resolved": False,
                "deck_state_pair_resolved": False,
                "deck_pair_capture_configured": True,
                "deck_audio_capture_both_active": False,
            },
            "blockers": ["deck identity source: library cache is missing"],
        },
        source_status={
            "library_cache": {
                "source_type": "missing",
                "loaded": False,
                "track_count": 0,
            },
            "library_setup_candidates": [
                {
                    "kind": "music_folder",
                    "path": "/Users/ka/Music/PSYMIND",
                    "confidence": "high",
                    "reason": "bounded scan saw 42 supported audio files",
                    "command": (
                        "uv run python -m vibemix library embed-folder "
                        "/Users/ka/Music/PSYMIND"
                    ),
                    "audio_files_seen": 42,
                    "import_action": {
                        "type": "ipc.library.import",
                        "payload": {
                            "path": "/Users/ka/Music/PSYMIND",
                            "schema_version": "1",
                        },
                    },
                }
            ],
            "rekordbox_app": {"exists": True},
            "rekordbox_master_db": {"exists": True},
        },
    )

    assert actions[0]["code"] == "index_library"
    assert actions[0]["recommended_surfaces"] == [
        "settings.library.drop",
        "library.ingest",
        "library.embed-folder",
    ]
    assert actions[0]["source_kind"] == "missing"
    assert actions[0]["candidate_sources"][0]["path"] == "/Users/ka/Music/PSYMIND"
    assert actions[0]["recommended_import_action"] == {
        "type": "ipc.library.import",
        "payload": {
            "path": "/Users/ka/Music/PSYMIND",
            "schema_version": "1",
        },
    }
    assert "music_folder:/Users/ka/Music/PSYMIND" in actions[0]["detail"]
    assert "Drop a Rekordbox collection.xml or a music folder" in actions[0]["detail"]
    assert "does not read the live SQLCipher master.db" in actions[0]["detail"]
    assert "resolve_deck_identity" in [action["code"] for action in actions]


def test_viber_live_context_operator_actions_recommends_local_channel_map_override():
    actions = main_mod._viber_live_context_operator_actions(
        {
            "ready": False,
            "diagnosis": "missing_physical_proof",
            "checks": {
                "frames_seen": True,
                "flat_deck_frame_seen": True,
                "controller_connected": True,
                "recent_moves_seen": True,
                "audio_observed": True,
                "deck_state_resolved": True,
                "deck_state_pair_resolved": True,
                "deck_pair_capture_configured": True,
                "deck_audio_capture_both_active": False,
            },
            "blockers": [
                "deck_audio_capture did not show active audio on both deck lanes",
            ],
            "deck_audio_separation_context": (
                _deck_pair_audio_separation_context_with_route_diagnosis(
                    active_unassigned_pairs="4,5"
                )
            ),
        }
    )

    assert [action["code"] for action in actions] == ["feed_both_deck_lanes"]
    assert actions[0]["route_diagnosis"]["inactive_sides"] == "B"
    assert actions[0]["route_diagnosis"]["active_unassigned_pairs"] == "4,5"
    assert actions[0]["recommended_env"] == {"VIBEMIX_DECK_AUDIO_CHANNELS": "A=0,1;B=4,5"}
    assert "local channel-map override" in actions[0]["detail"]


def test_apply_viber_operator_recommended_env_persists_deck_channel_map(tmp_path):
    config_path = tmp_path / "config.json"
    ConfigStore().save(config_path)
    result = {
        "operator_actions": [
            {
                "code": "feed_both_deck_lanes",
                "recommended_env": {"VIBEMIX_DECK_AUDIO_CHANNELS": "A=0,1;B=4,5"},
            }
        ]
    }

    applied = main_mod._apply_viber_operator_recommended_env(
        result,
        config_path=config_path,
    )

    assert applied["applied"] is True
    assert applied["restart_required"] is True
    assert applied["env"] == {"VIBEMIX_DECK_AUDIO_CHANNELS": "A=0,1;B=4,5"}
    assert load_config(config_path).extra["deck_audio.channels"] == "A=0,1;B=4,5"


def test_apply_deck_audio_config_to_env_respects_explicit_env(monkeypatch):
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "off")
    config = ConfigStore(extra={"deck_audio.channels": "A=0,1;B=4,5"})

    applied = main_mod._apply_deck_audio_config_to_env(config)

    assert applied == {}
    assert os.environ["VIBEMIX_DECK_AUDIO_CHANNELS"] == "off"


def test_apply_deck_audio_config_to_env_seeds_persisted_viber_setup(monkeypatch):
    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)
    config = ConfigStore(extra={"deck_audio.channels": "A=0,1;B=4,5"})

    applied = main_mod._apply_deck_audio_config_to_env(config)

    assert applied == {"VIBEMIX_DECK_AUDIO_CHANNELS": "A=0,1;B=4,5"}
    assert os.environ["VIBEMIX_DECK_AUDIO_CHANNELS"] == "A=0,1;B=4,5"


def test_viber_live_context_operator_actions_promote_setup_hint():
    setup_hint = {
        "next_action": "Start with VIBEMIX_DECK_AUDIO_CHANNELS=auto.",
        "recommended_env": {"VIBEMIX_DECK_AUDIO_CHANNELS": "auto"},
        "rule": "setup_hint_not_live_audio_proof",
    }
    actions = main_mod._viber_live_context_operator_actions(
        {
            "ready": False,
            "diagnosis": "missing_physical_proof",
            "checks": {
                "frames_seen": True,
                "flat_deck_frame_seen": True,
                "controller_connected": True,
                "recent_moves_seen": True,
                "audio_observed": True,
                "deck_state_resolved": True,
                "deck_state_pair_resolved": True,
                "deck_pair_capture_configured": False,
                "deck_audio_capture_both_active": False,
            },
            "blockers": ["deck-pair audio capture was not configured in the live packet"],
        },
        setup_hint=setup_hint,
    )

    assert actions[0]["code"] == "apply_route_hint"
    assert actions[0]["recommended_env"] == {"VIBEMIX_DECK_AUDIO_CHANNELS": "auto"}
    assert actions[0]["setup_hint"]["rule"] == "setup_hint_not_live_audio_proof"
    assert actions[1]["code"] == "configure_deck_pair_capture"
    assert actions[1]["recommended_env"] == {"VIBEMIX_DECK_AUDIO_CHANNELS": "A=0,1;B=2,3"}


def test_cmd_library_live_context_json_success(monkeypatch, capsys):
    async def fake_sample(timeout_s: float, max_frames: int, *, require_proof: bool):
        assert timeout_s == 0.2
        assert max_frames == 4
        assert require_proof is False
        return {
            "ok": True,
            "source": "ws://127.0.0.1:8765",
            "frames_seen": 2,
            "flat_deck_frame_seen": True,
            "session_snapshot_seen": True,
            "live_context": {"deck": "A"},
            "preview": "live_context[deck=A]",
            "readiness": {"ready": True, "blockers": []},
            "error": None,
            "hint": None,
        }

    monkeypatch.setattr(main_mod, "_sample_viber_live_context", fake_sample)

    rc = main_mod._cmd_library_live_context(
        argparse.Namespace(json=True, timeout=0.2, frames=4, require_proof=False)
    )

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True
    assert out["preview"] == "live_context[deck=A]"


def test_cmd_library_live_context_writes_proof_artifact(monkeypatch, tmp_path, capsys):
    proof_path = tmp_path / "proof" / "live-context.json"

    async def fake_sample(timeout_s: float, max_frames: int, *, require_proof: bool):
        assert require_proof is True
        return {
            "ok": True,
            "source": "ws://127.0.0.1:8765",
            "frames_seen": 12,
            "flat_deck_frame_seen": True,
            "session_snapshot_seen": True,
            "live_context": {
                "deck": "A",
                "live_evidence": {
                    "mix": ["deck_lanes=A_known_route_dominant+B_unknown_route_muted"]
                },
            },
            "preview": "deck_lanes_context[A=known:dominant | B=unknown:muted]",
            "readiness": {"ready": True, "blockers": []},
            "source_status": {"live_db_policy": {"reads_rekordbox_master_db_live": False}},
            "error": None,
            "hint": None,
        }

    monkeypatch.setattr(main_mod, "_sample_viber_live_context", fake_sample)

    rc = main_mod._cmd_library_live_context(
        argparse.Namespace(
            json=False,
            timeout=0.2,
            frames=12,
            require_proof=True,
            out=str(proof_path),
        )
    )

    assert rc == 0
    assert "deck_lanes_context[" in capsys.readouterr().out
    payload = json.loads(proof_path.read_text(encoding="utf-8"))
    assert payload["proof_path"] == str(proof_path)
    assert payload["readiness"]["ready"] is True
    assert payload["live_context"]["live_evidence"]["mix"] == [
        "deck_lanes=A_known_route_dominant+B_unknown_route_muted"
    ]


def test_cmd_library_live_context_wait_ready_retries_until_physical_proof(monkeypatch, capsys):
    calls: list[bool] = []
    sleeps: list[float] = []

    async def fake_sample(timeout_s: float, max_frames: int, *, require_proof: bool):
        assert timeout_s == 0.2
        assert max_frames == 4
        calls.append(require_proof)
        if len(calls) == 1:
            return {
                "ok": True,
                "source": "ws://127.0.0.1:8765",
                "frames_seen": 4,
                "flat_deck_frame_seen": True,
                "session_snapshot_seen": True,
                "live_context": {"deck": "A"},
                "preview": "live_context[deck=A]",
                "readiness": {
                    "ready": False,
                    "blockers": ["live master audio was not observed above the audible floor"],
                },
                "error": None,
                "hint": None,
            }
        return {
            "ok": True,
            "source": "ws://127.0.0.1:8765",
            "frames_seen": 4,
            "flat_deck_frame_seen": True,
            "session_snapshot_seen": True,
            "live_context": {"deck": "A", "audio_delta": ["low energy fell"]},
            "preview": "live_context[deck=A]",
            "readiness": {"ready": True, "blockers": []},
            "error": None,
            "hint": None,
        }

    async def fake_sleep(delay: float):
        sleeps.append(delay)

    monkeypatch.setattr(main_mod, "_sample_viber_live_context", fake_sample)
    monkeypatch.setattr(main_mod.asyncio, "sleep", fake_sleep)

    rc = main_mod._cmd_library_live_context(
        argparse.Namespace(
            json=True,
            timeout=0.2,
            frames=4,
            require_proof=False,
            wait_ready=5.0,
            interval=0.25,
            out=None,
        )
    )

    assert rc == 0
    assert calls == [True, True]
    assert sleeps == [0.25]
    payload = json.loads(capsys.readouterr().out)
    assert payload["readiness"]["ready"] is True
    assert payload["proof_attempts"] == 2
    assert payload["wait_ready_s"] == 5.0


def test_cmd_library_live_context_text_failure(monkeypatch, capsys):
    async def fake_sample(timeout_s: float, max_frames: int, *, require_proof: bool):
        return {
            "ok": False,
            "source": "ws://127.0.0.1:8765",
            "frames_seen": 0,
            "flat_deck_frame_seen": False,
            "session_snapshot_seen": False,
            "live_context": {},
            "preview": "",
            "readiness": {"ready": False, "blockers": ["no websocket frames arrived"]},
            "setup_hint": {
                "next_action": (
                    "Rekordbox deck route hint found (A=0,1;B=2,3 via Aggregate_Device). "
                    "Start the live session with VIBEMIX_INPUT_DEVICE='BlackHole 16ch' "
                    "VIBEMIX_DECK_AUDIO_CHANNELS=auto."
                ),
                "rule": "setup_hint_not_live_audio_proof",
            },
            "error": "connect failed",
            "hint": "start the session",
        }

    monkeypatch.setattr(main_mod, "_sample_viber_live_context", fake_sample)

    rc = main_mod._cmd_library_live_context(
        argparse.Namespace(json=False, timeout=0.1, frames=1, require_proof=False)
    )

    assert rc == 1
    err = capsys.readouterr().err
    assert "live-context unavailable: connect failed" in err
    assert "start the session" in err
    assert "setup hint: Rekordbox deck route hint found" in err
    assert "VIBEMIX_DECK_AUDIO_CHANNELS=auto" in err


def test_cmd_library_live_context_require_proof_fails_with_blockers(monkeypatch, capsys):
    async def fake_sample(timeout_s: float, max_frames: int, *, require_proof: bool):
        assert require_proof is True
        return {
            "ok": True,
            "source": "ws://127.0.0.1:8765",
            "frames_seen": 2,
            "flat_deck_frame_seen": True,
            "session_snapshot_seen": True,
            "live_context": {"deck": "A"},
            "preview": "live_context[deck=A]",
            "readiness": {
                "ready": False,
                "blockers": ["controller mixer posture was not connected"],
                "next_action": "Collect the missing live proof legs.",
            },
            "operator_actions": [
                {
                    "code": "connect_controller",
                    "detail": "Connect the DJ controller over USB.",
                }
            ],
            "error": None,
            "hint": None,
        }

    monkeypatch.setattr(main_mod, "_sample_viber_live_context", fake_sample)

    rc = main_mod._cmd_library_live_context(
        argparse.Namespace(json=False, timeout=0.1, frames=1, require_proof=True)
    )

    assert rc == 1
    out = capsys.readouterr()
    assert "live_context[deck=A]" in out.out
    assert "controller mixer posture was not connected" in out.err
    assert "next action: Collect the missing live proof legs." in out.err
    assert "operator action: connect_controller: Connect the DJ controller over USB." in out.err


def test_viber_live_context_payload_extracts_nested_proof_artifact():
    proof = {
        "ok": True,
        "live_context": {"deck": "A", "live_context_schema_version": 2},
        "readiness": {"ready": True},
    }

    assert main_mod._viber_live_context_from_json_payload(proof) == {
        "deck": "A",
        "live_context_schema_version": 2,
    }
    assert main_mod._viber_live_context_from_json_payload({"deck": "B"}) == {"deck": "B"}
    assert main_mod._viber_live_context_from_json_payload(["not", "a", "dict"]) is None


def test_cmd_library_chat_reads_live_context_proof_file(monkeypatch, tmp_path, capsys):
    import vibemix.library.codex_curate as codex_mod

    proof_path = tmp_path / "live-context.json"
    proof_path.write_text(
        json.dumps(
            {
                "ok": True,
                "live_context": {
                    "deck": "A",
                    "live_context_schema_version": 2,
                    "live_context_capabilities": _live_context_capabilities(),
                    "audio_delta": ["low energy fell 50% (strong)"],
                },
                "readiness": {"ready": True},
            }
        ),
        encoding="utf-8",
    )
    captured: dict = {}

    def fake_chat(message, library, *, history=None, live_context=None, **_kwargs):
        captured["message"] = message
        captured["history"] = history
        captured["live_context"] = live_context
        return CodexChatResult(reply="I can see deck A context.", stop_reason="model_done")

    monkeypatch.setattr(codex_mod, "chat_with_codex", fake_chat)

    rc = main_mod._cmd_library_chat(
        argparse.Namespace(
            message="was that good?",
            history=None,
            live_context=None,
            live_context_file=str(proof_path),
            backend="codex",
            json=True,
        )
    )

    assert rc == 0
    assert captured["message"] == "was that good?"
    assert captured["live_context"]["deck"] == "A"
    assert captured["live_context"]["audio_delta"] == ["low energy fell 50% (strong)"]
    out = json.loads(capsys.readouterr().out)
    assert out["reply"] == "I can see deck A context."


def test_cmd_library_chat_fails_loudly_for_bad_live_context_file(tmp_path, capsys):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("[]", encoding="utf-8")

    rc = main_mod._cmd_library_chat(
        argparse.Namespace(
            message="was that good?",
            history=None,
            live_context=None,
            live_context_file=str(bad_path),
            backend="codex",
            json=True,
        )
    )

    assert rc == 1
    err = json.loads(capsys.readouterr().err)
    assert err["stop_reason"] == "live_context_file_error"
    assert "live-context object" in err["reply"]


def _write_ready_single_deck_proof(path) -> None:
    path.write_text(
        json.dumps(
            {
                "ok": True,
                "live_context": {
                    "deck": "A",
                    "audible": True,
                    "music": 0.8,
                    "live_context_schema_version": 2,
                    "live_context_capabilities": _live_context_capabilities(),
                    "deck_state": {
                        "A": {
                            "title": "Strobe",
                            "track_id": "track-1",
                            "confidence": 0.9,
                            "source": "rekordbox_xml",
                        }
                    },
                    "deck_mixer": {
                        "connected": True,
                        "A": {"vol": 110, "eq_low": 2},
                        "B": {"vol": 0, "eq_low": 64},
                    },
                    "recent_moves": ["A_low: flat->killed"],
                    "deck_audio_separation_context": _deck_audio_separation_context(),
                    "audio_delta": ["low energy fell 50% (strong)"],
                    "live_evidence": {
                        "mix": ["transition_block=single_resolved_deck"],
                        "refs": ["mix:transition_block=single_resolved_deck"],
                    },
                },
                "readiness": {"ready": True},
            }
        ),
        encoding="utf-8",
    )


def _write_ready_single_deck_deck_audio_proof(path) -> None:
    path.write_text(
        json.dumps(
            {
                "ok": True,
                "live_context": {
                    "deck": "A",
                    "audible": True,
                    "music": 0.8,
                    "live_context_schema_version": 2,
                    "live_context_capabilities": _live_context_capabilities(),
                    "deck_state": {
                        "A": {
                            "title": "Strobe",
                            "track_id": "track-1",
                            "confidence": 0.9,
                            "source": "rekordbox_xml",
                        }
                    },
                    "deck_mixer": {
                        "connected": True,
                        "xfader": 32,
                        "A": {
                            "vol": 110,
                            "eq_low": 2,
                            "eq_mid": 64,
                            "eq_hi": 64,
                            "filter": 64,
                        },
                        "B": {
                            "vol": 0,
                            "eq_low": 64,
                            "eq_mid": 64,
                            "eq_hi": 64,
                            "filter": 64,
                        },
                    },
                    "recent_moves": ["A_low: flat->killed"],
                    "deck_source_status": _deck_source_status(),
                    "deck_audio_separation_context": _deck_pair_audio_separation_context(),
                    "deck_audio_features_context": _deck_audio_features_context(),
                        "deck_audio_delta_context": _deck_audio_delta_context(),
                        "deck_audio_window_context": _deck_audio_window_context(),
                        "audio_part_context": _audio_part_context(),
                    "audio_delta": ["low energy fell 50% (strong)"],
                    "audio_window_map": _audio_window_map(),
                    "live_evidence": {
                        "mix": [
                            "transition_block=single_resolved_deck",
                            "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                            "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                            "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
                            "deck_audio_capture=A_active+B_silent",
                            "deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000",
                            "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                            (
                                "deck_audio_window=A_active_pre_0.020_current_0.040+"
                                "B_silent_pre_0.030_current_0.000"
                            ),
                        ],
                        "refs": [
                            "mix:transition_block=single_resolved_deck",
                            "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                            "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                            "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none",
                            "mix:deck_audio_capture=A_active+B_silent",
                            "mix:deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000",
                            "mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong",
                            (
                                "mix:deck_audio_window=A_active_pre_0.020_current_0.040+"
                                "B_silent_pre_0.030_current_0.000"
                            ),
                        ],
                    },
                },
                "readiness": {"ready": True},
            }
        ),
        encoding="utf-8",
    )


def test_cmd_library_verify_live_reply_rejects_unsupported_transition_claim(tmp_path, capsys):
    proof_path = tmp_path / "proof.json"
    chat_path = tmp_path / "chat.json"
    _write_ready_single_deck_proof(proof_path)
    chat_path.write_text(
        json.dumps({"reply": "Great transition, that blend was clean.", "move_grades": []}),
        encoding="utf-8",
    )

    rc = main_mod._cmd_library_verify_live_reply(
        argparse.Namespace(
            live_context_file=str(proof_path),
            chat_result_file=str(chat_path),
            reply=None,
            json=True,
        )
    )

    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert "unsupported_live_outcome_claim" in out["violations"]
    assert "Great transition" not in out["corrected_reply"]
    assert "clear two-deck proof" in out["corrected_reply"]


def test_cmd_library_verify_live_reply_rejects_audio_source_detail_claim(tmp_path, capsys):
    proof_path = tmp_path / "proof.json"
    _write_ready_single_deck_proof(proof_path)

    rc = main_mod._cmd_library_verify_live_reply(
        argparse.Namespace(
            live_context_file=str(proof_path),
            chat_result_file=None,
            reply="The vocal opened up and the kick got tighter.",
            json=True,
        )
    )

    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert "unsupported_audio_source_detail_claim" in out["violations"]
    assert "vocal" not in out["corrected_reply"].lower()
    assert "kick" not in out["corrected_reply"].lower()
    assert "source-level proof" in out["corrected_reply"]


def test_cmd_library_verify_live_reply_rejects_deck_audio_rich_single_deck_transition(
    tmp_path, capsys
):
    proof_path = tmp_path / "proof.json"
    chat_path = tmp_path / "chat.json"
    _write_ready_single_deck_deck_audio_proof(proof_path)
    chat_path.write_text(
        json.dumps(
            {
                "reply": "Great transition, the incoming deck landed clean.",
                "move_grades": [
                    {
                        "track_id": "track-1",
                        "label": "LIT AFF",
                        "reason": "transition_slate said it was clean",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    rc = main_mod._cmd_library_verify_live_reply(
        argparse.Namespace(
            live_context_file=str(proof_path),
            chat_result_file=str(chat_path),
            reply=None,
            json=True,
        )
    )

    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["proof_ready"] is True
    assert out["claim_policy"] == "blocked"
    assert out["move_grades_allowed"] is False
    assert "unsupported_live_outcome_claim" in out["violations"]
    assert "move_grades_without_live_proof" in out["violations"]
    assert "Great transition" not in out["corrected_reply"]
    assert "incoming deck landed clean" not in out["corrected_reply"]
    assert "clear two-deck proof" in out["corrected_reply"]


def test_cmd_library_verify_live_reply_rejects_public_self_correction(tmp_path, capsys):
    proof_path = tmp_path / "proof.json"
    _write_ready_single_deck_proof(proof_path)

    rc = main_mod._cmd_library_verify_live_reply(
        argparse.Namespace(
            live_context_file=str(proof_path),
            chat_result_file=None,
            reply="I saw the deck A low move, but I can't call it a transition.",
            json=True,
        )
    )

    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert "unsupported_live_outcome_claim" in out["violations"]
    assert out["proof_ready"] is True
    assert out["corrected_reply"] == (
        "I can't call that a transition until I have clear two-deck proof."
    )


def test_cmd_library_verify_live_reply_rejects_public_debug_labels(tmp_path, capsys):
    proof_path = tmp_path / "proof.json"
    _write_ready_single_deck_proof(proof_path)

    rc = main_mod._cmd_library_verify_live_reply(
        argparse.Namespace(
            live_context_file=str(proof_path),
            chat_result_file=None,
            reply=(
                "I need to correct the live read: resolved decks=none; "
                "live evidence gate: transition_block=no_resolved_decks; "
                "claim_policy=blocked."
            ),
            json=True,
        )
    )

    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False
    assert "unsupported_live_outcome_claim" in out["violations"]
    assert "correct the live read" not in out["corrected_reply"]
    assert "resolved decks" not in out["corrected_reply"]
    assert "claim_policy" not in out["corrected_reply"]
    assert "clear two-deck proof" in out["corrected_reply"]


def test_cmd_library_verify_live_reply_rejects_unready_proof_artifact(tmp_path, capsys):
    proof_path = tmp_path / "proof.json"
    _write_ready_single_deck_proof(proof_path)
    payload = json.loads(proof_path.read_text(encoding="utf-8"))
    payload["readiness"] = {"ready": False}
    proof_path.write_text(json.dumps(payload), encoding="utf-8")

    rc = main_mod._cmd_library_verify_live_reply(
        argparse.Namespace(
            live_context_file=str(proof_path),
            chat_result_file=None,
            reply="I can't call that a transition from this proof.",
            json=True,
        )
    )

    assert rc == 1
    out = json.loads(capsys.readouterr().out)
    assert "proof_not_ready" in out["violations"]
