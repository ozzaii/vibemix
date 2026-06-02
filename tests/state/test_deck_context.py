# SPDX-License-Identifier: Apache-2.0
"""Prompt-facing deck_context formatter tests."""

from __future__ import annotations

import time

import pytest

from vibemix.state.deck_context import (
    apply_live_claim_guard,
    live_claim_policy,
    live_evidence_packet,
    live_mix_evidence_keys,
    midi_evidence_key,
    move_evidence_atoms,
    normalize_audio_part_context_text,
    normalize_audio_window_context_text,
    normalize_deck_audio_context_text,
    normalize_deck_audio_delta_context_text,
    normalize_deck_audio_features_context_text,
    normalize_deck_audio_separation_context_text,
    normalize_deck_audio_window_context_text,
    normalize_deck_lanes_context_text,
    normalize_deck_reference_context_text,
    normalize_deck_source_context_text,
    normalize_set_window_context_text,
    render_audio_delta_items,
    render_audio_part_context,
    render_audio_window_context,
    render_audio_window_map,
    render_context_feed_contract,
    render_deck_audio_context,
    render_deck_audio_delta_context,
    render_deck_audio_features_context,
    render_deck_audio_separation_context,
    render_deck_audio_window_context,
    render_deck_change_context,
    render_deck_context,
    render_deck_lane_context,
    render_deck_reference_context,
    render_deck_source_context,
    render_grounding_ref_context,
    render_live_evidence_context,
    render_mixer_context,
    render_move_context,
    render_move_effect_context,
    render_set_window_context,
    sanitize_historical_move_signature_for_prompt,
    should_defer_live_claim_stream,
)
from vibemix.state.deck_state import DeckState, DeckTrack
from vibemix.state.music_state import MusicState


def _deck(
    title: str | None = "Strobe",
    *,
    camelot: str | None = "8A",
    confidence: float = 0.8,
    bpm: float = 128.0,
    genre: str | None = None,
    source: str = "rekordbox_xml",
) -> DeckTrack:
    return DeckTrack(
        title=title,
        track_id="t1" if title else None,
        bpm=bpm,
        genre=genre,
        camelot=camelot,
        confidence=confidence,
        source=source,
    )


def _deck_pair_audio_capture(
    *,
    both_active: bool = True,
    with_delta: bool = True,
    with_window: bool = True,
) -> dict:
    b_rms = 0.031 if both_active else 0.0
    capture = {
        "deck_audio_capture_enabled": True,
        "deck_audio_rms": {"A": 0.024, "B": b_rms},
        "deck_audio_features": {
            "A": {"activity": "active", "rms": 0.024, "peak": 0.11, "zcr": 0.03},
            "B": {
                "activity": "active" if both_active else "silent",
                "rms": b_rms,
                "peak": 0.10 if both_active else 0.0,
                "zcr": 0.04 if both_active else 0.0,
            },
        },
    }
    if with_delta:
        capture["deck_audio_deltas"] = {
            "A": ["rms_rose_60pct_strong"],
            "B": ["rms_fell_20pct_slight"],
        }
    if with_window:
        capture["deck_audio_windows"] = {
            "A": {
                "pre": {"activity": "active", "rms": 0.015, "peak": 0.08},
                "current": {"activity": "active", "rms": 0.024, "peak": 0.11},
                "delta": ["rms_rose_60pct_strong"],
            },
            "B": {
                "pre": {"activity": "active" if both_active else "silent", "rms": b_rms},
                "current": {
                    "activity": "active" if both_active else "silent",
                    "rms": b_rms,
                },
                "delta": ["rms_fell_20pct_slight"] if both_active else [],
            },
        }
    return capture


def _deck_pair_audio_capture_with_rms_deltas(a_delta: str, b_delta: str) -> dict:
    capture = _deck_pair_audio_capture(with_delta=False)
    capture["deck_audio_deltas"] = {
        "A": [a_delta],
        "B": [b_delta],
    }
    return capture


def test_empty_deck_state_emits_nothing() -> None:
    assert render_deck_context(MusicState()) is None


def test_context_feed_contract_labels_cache_history_and_speed() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.controller_connected = True
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    state.recent_moves = [(1.2, "A_low: flat→killed (big twist)")]
    state.audio_delta = ["sub energy fell 50% (strong)"]

    out = render_context_feed_contract(
        state,
        ["A_low: flat→killed (big twist)"],
        surface="gemini_p1",
        audio_seconds=6.0,
    )

    assert out is not None
    assert out.startswith("context_feed_contract[")
    assert "surface=gemini_p1" in out
    assert "labels=deck1:A,deck2:B" in out
    assert "sources=MusicState.deck_state+deck_mixer+EvidenceRegistry+perceive_cache" in out
    assert "volatile=deck_state+deck_mixer+recent_moves+audio_delta+audio_window" in out
    assert "history=past_comparison_not_live_proof" in out
    assert "cache=static_persona_rules_only" in out
    assert "per_turn=small_text+single_P1_audio" in out
    assert "ttl=recent_moves_8s+audio_window_6s" in out
    assert "speed=no_extra_model_pass" in out
    assert "rule=label_provenance_freshness_before_reasoning" in out


def test_context_feed_contract_stays_silent_when_no_live_packet() -> None:
    assert render_context_feed_contract(MusicState()) is None


def test_set_window_context_stays_silent_when_cold() -> None:
    assert render_set_window_context(MusicState()) is None


def test_set_window_context_master_only_honesty_contract(mocker) -> None:
    mocker.patch("vibemix.state.deck_context.time.time", return_value=1000.0)
    state = MusicState(
        audible=True,
        rms=0.08,
        bpm=149.0,
        long_arc=[0.10, 0.13, 0.17, 0.21],
        trajectory_narrative="phrase=build; energy rising; newest move A_low at 2s",
        recent_moves=[
            (2.0, "A_low: flat→killed (big twist)"),
            (7.5, "xfader→center"),
        ],
        phase_history=[
            (880.0, "groove", "build"),
            (940.0, "build", "drop"),
        ],
        track_history=[
            (760.0, "Intro Track"),
            (910.0, "Incoming Track"),
        ],
        audio_delta=["sub energy fell 50% (strong)"],
        move_audio_delta=["low energy fell 40% (clear)"],
    )
    state.deck_state = DeckState(
        decks={
            "A": _deck("Varazslo", bpm=163.0, camelot="7B", genre="psytrance"),
            "B": _deck("Ananta Gathering", bpm=159.0, camelot="8A", genre="psytrance"),
        }
    )

    out = render_set_window_context(state)

    assert out is not None
    assert out.startswith("set_window_context[")
    assert normalize_set_window_context_text(out) == out
    assert "span=-300..0.0" in out
    assert "audio_attached=P1_only_last_60-90s" in out
    assert "history=structured_text_only" in out
    assert "energy_arc=up:4" in out
    assert "moves=A_low_flat_to_killed_big_twist@-2.0s,xfader_to_center@-7.5s" in out
    assert "events=PHASE_build_to_drop@-60.0s,TRACK_Incoming_Track@-90.0s" in out
    assert "transitions=1" in out
    assert "phase_boundaries=2" in out
    assert "decks=deck1:A(" in out
    assert "deck2:B(" in out
    assert "genre=psytrance" in out
    assert "trajectory=phrase_build_energy_rising_newest_move_A_low_at_2s" in out
    assert "per_deck_audio=not_attached" in out
    assert "isolated_decks=false" in out
    assert "rule=long_window_is_structured_history_not_audio_proof" in out
    assert "isolated_decks=true" not in out
    assert "deckA_audio=attached" not in out
    assert "transition_verdict=" not in out
    assert "quality_verdict=" not in out


def test_set_window_context_lifts_moves_to_twelve_but_stays_bounded(mocker) -> None:
    mocker.patch("vibemix.state.deck_context.time.time", return_value=1000.0)
    state = MusicState(
        recent_moves=[(float(i), f"A_low: move {i}") for i in range(14)],
        phase_history=[(999.0, "groove", "build")],
    )

    out = render_set_window_context(state)

    assert out is not None
    assert "A_low_move_0@-0.0s" in out
    assert "A_low_move_11@-11.0s" in out
    assert "A_low_move_12@-12.0s" not in out
    assert "A_low_move_13@-13.0s" not in out


def test_set_window_context_normalizer_rejects_per_deck_audio_claims() -> None:
    bad = (
        "set_window_context[span=-300..0.0 audio_attached=P1_only_last_60-90s "
        "history=structured_text_only moves=none events=none transitions=0 phase_boundaries=0 "
        "decks=unknown per_deck_audio=not_attached isolated_decks=true "
        "rule=long_window_is_structured_history_not_audio_proof]"
    )

    assert normalize_set_window_context_text(bad) is None


def test_single_resolved_deck_blocks_transition_language() -> None:
    state = MusicState(audible_deck="A", deck_confidence=0.85)
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})

    out = render_deck_context(state)

    assert out is not None
    assert "audible=A" in out
    assert "resolved=A" in out
    assert "identity_scope=single_resolved_deck" in out
    assert "known_decks=A" in out
    assert "second_deck_identity=unknown_or_suppressed" in out
    assert "identity_rule=do_not_invent_unresolved_decks" in out
    assert "transition_block=single_resolved_deck" in out
    assert "A='Strobe'" in out
    assert "key=8A" in out


def test_two_resolved_decks_mark_mix_candidate() -> None:
    state = MusicState(audible_deck="mix", deck_confidence=0.5)
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A", bpm=128.0),
            "B": _deck("InB", camelot="9A", bpm=130.0),
        }
    )

    out = render_deck_context(state)

    assert out is not None
    assert "resolved=A+B" in out
    assert "identity_scope=two_resolved_decks" in out
    assert "known_decks=A+B" in out
    assert "second_deck_identity=observed" in out
    assert "transition_candidate=two_resolved_decks_mixing" in out
    assert "A='OutA'" in out
    assert "B='InB'" in out


def test_two_resolved_decks_single_audible_is_watch_not_claim() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.8)
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )

    out = render_deck_context(state)
    policy, reason = live_claim_policy(state)
    result = apply_live_claim_guard("That was a great transition.", state)

    assert out is not None
    assert "transition_watch=two_resolved_decks_single_audible_A" in out
    assert policy == "watch_not_claim"
    assert reason == "two_resolved_decks_single_audible_A"
    assert result.corrected is True


def test_unresolved_decks_block_transition_language() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Mystery", confidence=0.1, source="unknown")}
    )

    out = render_deck_context(state)

    assert out is not None
    assert "resolved=none" in out
    assert "identity_scope=no_resolved_decks" in out
    assert "second_deck_identity=blocked" in out
    assert "transition_block=no_resolved_decks" in out
    assert "loaded=" not in out


def test_title_without_key_still_counts_as_deck_identity() -> None:
    state = MusicState(audible_deck="B")
    state.deck_state = DeckState(decks={"B": _deck("Readable Title", camelot=None)})

    out = render_deck_context(state)

    assert out is not None
    assert "resolved=B" in out
    assert "B='Readable Title'" in out
    assert "key=" not in out


def test_deck_context_carries_source_genre_next_to_loaded_track() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Varazslo", genre="psytrance")})

    out = render_deck_context(state)

    assert out is not None
    assert "loaded=A='Varazslo' key=8A bpm=128 genre='psytrance' src=rekordbox_xml" in out


def test_single_deck_play_move_blocks_transition_language() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})

    out = render_move_context(state, ["A_play→ON"])

    assert out is not None
    assert "scope=single_deck_move_A" in out
    assert "sides=A" in out
    assert "controls=play" in out
    assert "transition_block=single_resolved_deck" in out


def test_mixer_context_names_per_deck_controller_posture() -> None:
    state = MusicState(audible_deck="A", deck_confidence=0.72)
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {
        "vol": 112,
        "eq_low": 2,
        "eq_mid": 64,
        "eq_hi": 82,
        "filter": 64,
        "play": True,
    }
    state.deck_b = {
        "vol": 28,
        "eq_low": 64,
        "eq_mid": 64,
        "eq_hi": 64,
        "filter": 100,
        "play": False,
    }

    out = render_mixer_context(state)

    assert out is not None
    assert "mixer_context[" in out
    assert "xfader=center" in out
    assert "deck_conf=0.72" in out
    assert "A(vol=open low=killed mid=flat hi=boost filter=flat play=on)" in out
    assert "B(vol=low low=flat mid=flat hi=flat filter=boost play=off)" in out


def test_deck_audio_context_maps_global_audio_to_controller_route() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.72)
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {"vol": 112, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}

    out = render_deck_audio_context(state)

    assert out is not None
    assert "deck_audio_context[" in out
    assert "source=global_mix" in out
    assert "isolated_decks=false" in out
    assert "A=dominant" in out
    assert "B=muted" in out
    assert "support=single_deck_A" in out


def test_audio_window_context_anchors_move_inside_master_audio() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.72)
    state.recent_moves = [(0.7, "A_low: flat->killed")]

    out = render_audio_window_context(
        state,
        ["A_low: flat->killed"],
        audio_seconds=6.0,
        lookahead_part_label="P2",
        lookahead_horizon_s=3.0,
    )

    assert out is not None
    assert out.startswith("audio_window_context[")
    assert "P1=master_global_mix" in out
    assert "P1_heard=true" in out
    assert "timeline=past_action_future" in out
    assert "pre=-6.0..-1.0" in out
    assert "current=-1.0..0.0" in out
    assert "action=-1.0..0.0" in out
    assert "move_anchor=A_low:_flat-_killed@-0.7s:inside_P1" in out
    assert "P2=source_file_lookahead" in out
    assert "future_heard=false" in out
    assert "future=0.0..+3.0" in out
    assert "future_rule=forecast_only_not_audience_evidence" in out
    assert "together_audio=P1_global_mix" in out
    assert "decks_together=true" in out
    assert "deckA_audio=not_attached" in out
    assert "deckB_audio=not_attached" in out
    assert "per_deck_audio=structured_text_only" in out
    assert "duplicate_audio=same_master_not_deck_split" in out
    assert "deck_separation=deck_lanes_context" in out
    assert "lane_aliases=deck1:A,deck2:B" in out
    assert "rule=time_alignment_not_outcome_verdict" in out


def test_audio_part_context_labels_parts_without_claiming_deck_stems() -> None:
    out = render_audio_part_context(
        audio_seconds=6.0,
        mic_part_label="P2",
        lookahead_part_label="P3",
        lookahead_horizon_s=3.0,
    )

    assert out.startswith("audio_part_context[")
    assert "surface=gemini_parts" in out
    assert "P1=live_global_mix" in out
    assert "P1_model_heard=true" in out
    assert "P1_runtime_observed=true" in out
    assert "P1_audience_heard=true" in out
    assert "P1_span=-6.0..0.0" in out
    assert "P1_deck_audio=global_mix_not_stems" in out
    assert "deck1=A" in out
    assert "deck2=B" in out
    assert "together_audio=P1" in out
    assert "part_order=P1,P2,P3" in out
    assert "per_deck_audio=not_attached" in out
    assert "duplicate_audio=same_master_not_deck_split" in out
    assert "P2=user_mic" in out
    assert "P2_role=user_speech" in out
    assert "P2_span=-8.0..0.0" in out
    assert "P2_tokens_est=256" in out
    assert "P2_deck_audio=none" in out
    assert "P2_rule=not_deck_audio" in out
    assert "P3=source_file_lookahead" in out
    assert "P3_model_heard=true" in out
    assert "P3_audience_heard=false" in out
    assert "P3_span=0.0..+3.0" in out
    assert "P3_deck_audio=none" in out
    assert "P3_rule=forecast_only_not_current_live_evidence" in out
    assert "model_audio_tokens_est=544" in out
    assert "rule=part_labels_not_outcome_verdict" in out
    assert "deckA_audio=attached" not in out
    assert "deckB_audio=attached" not in out
    assert normalize_audio_part_context_text(out) == out


def test_audio_part_context_can_label_viber_live_context_without_fake_audio_part() -> None:
    out = render_audio_part_context(
        audio_seconds=6.0,
        surface="viber_live_context",
        p1_model_heard=False,
    )

    assert "surface=viber_live_context" in out
    assert "P1_model_heard=false" in out
    assert "P1_runtime_observed=true" in out
    assert "P1_deck_audio=global_mix_not_stems" in out
    assert "per_deck_audio=not_attached" in out
    assert "model_audio_tokens_est=0" in out
    assert normalize_audio_part_context_text(out) == out


def test_audio_part_context_labels_configured_deck_pair_parts() -> None:
    out = render_audio_part_context(
        audio_seconds=6.0,
        deck_part_labels={"A": "P2", "B": "P3"},
        deck_part_activity={"A": "active", "B": "silent"},
        deck_part_seconds=3.0,
    )

    assert "P1=live_global_mix" in out
    assert "audio_token_rate=32_per_second" in out
    assert "P1_tokens_est=192" in out
    assert "part_order=P1,P2,P3" in out
    assert "per_deck_audio=deck_pair_parts" in out
    assert "duplicate_audio=separate_deck_pair_parts" in out
    assert "deckA_part=P2" in out
    assert "deckB_part=P3" in out
    assert "P2=deckA_configured_capture" in out
    assert "P3=deckB_configured_capture" in out
    assert "P2_span=-3.0..0.0" in out
    assert "P2_tokens_est=96" in out
    assert "P2_activity=deckA_active" in out
    assert "P3_activity=deckB_silent" in out
    assert "model_audio_tokens_est=384" in out
    assert "P2_rule=deck_pair_capture_reference_not_quality_verdict" in out
    assert "P3_rule=deck_pair_capture_reference_not_quality_verdict" in out
    assert normalize_audio_part_context_text(out) == out


def test_audio_part_context_orders_deck_parts_after_mic_and_lookahead() -> None:
    out = render_audio_part_context(
        audio_seconds=6.0,
        mic_part_label="P2",
        lookahead_part_label="P3",
        deck_part_labels={"A": "P4", "B": "P5"},
        deck_part_activity={"A": "active", "B": "active"},
        deck_part_seconds=3.0,
    )

    assert "part_order=P1,P2,P3,P4,P5" in out
    assert "P2=user_mic" in out
    assert "P3=source_file_lookahead" in out
    assert "deckA_part=P4" in out
    assert "deckB_part=P5" in out
    assert "P4=deckA_configured_capture" in out
    assert "P5=deckB_configured_capture" in out
    assert normalize_audio_part_context_text(out) == out


def test_audio_part_context_trust_validator_rejects_incomplete_deck_pair_map() -> None:
    missing_b = (
        "audio_part_context[surface=gemini_parts P1=live_global_mix "
        "P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true "
        "P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 "
        "part_order=P1,P2 per_deck_audio=deck_pair_parts "
        "duplicate_audio=separate_deck_pair_parts deckA_part=P2 "
        "P2=deckA_configured_capture P2_model_heard=true "
        "P2_audience_heard=false P2_deck_audio=deckA_configured_capture "
        "P2_rule=deck_pair_capture_reference_not_quality_verdict "
        "rule=part_labels_not_outcome_verdict]"
    )
    colliding = (
        "audio_part_context[surface=gemini_parts P1=live_global_mix "
        "P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true "
        "P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 "
        "part_order=P1,P2 per_deck_audio=deck_pair_parts "
        "duplicate_audio=separate_deck_pair_parts deckA_part=P2 deckB_part=P2 "
        "P2=deckA_configured_capture P2=deckB_configured_capture "
        "P2_model_heard=true P2_audience_heard=false "
        "P2_deck_audio=deckA_configured_capture "
        "P2_rule=deck_pair_capture_reference_not_quality_verdict "
        "rule=part_labels_not_outcome_verdict]"
    )
    role_conflict = (
        "audio_part_context[surface=gemini_parts P1=live_global_mix "
        "P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true "
        "P1_deck_audio=global_mix_not_stems deck1=A deck2=B together_audio=P1 "
        "part_order=P1,P2,P3 per_deck_audio=deck_pair_parts "
        "duplicate_audio=separate_deck_pair_parts deckA_part=P2 "
        "P2=deckA_configured_capture P2_model_heard=true "
        "P2_audience_heard=false P2_deck_audio=deckA_configured_capture "
        "P2_rule=deck_pair_capture_reference_not_quality_verdict deckB_part=P3 "
        "P3=deckB_configured_capture P3_model_heard=true "
        "P3_audience_heard=false P3_deck_audio=deckB_configured_capture "
        "P3_rule=deck_pair_capture_reference_not_quality_verdict "
        "P2=user_mic P2_deck_audio=none P2_rule=not_deck_audio "
        "rule=part_labels_not_outcome_verdict]"
    )

    assert normalize_audio_part_context_text(missing_b) is None
    assert normalize_audio_part_context_text(colliding) is None
    assert normalize_audio_part_context_text(role_conflict) is None


def test_audio_part_context_renderer_falls_back_on_conflicting_deck_part_labels() -> None:
    out = render_audio_part_context(
        audio_seconds=6.0,
        mic_part_label="P2",
        deck_part_labels={"A": "P2", "B": "P3"},
        deck_part_activity={"A": "active", "B": "active"},
        deck_part_seconds=3.0,
    )

    assert "part_order=P1,P2" in out
    assert "per_deck_audio=not_attached" in out
    assert "deckA_part=" not in out
    assert "deckB_part=" not in out
    assert "P2=user_mic" in out
    assert normalize_audio_part_context_text(out) == out


def test_audio_part_context_trust_validator_rejects_stem_claims() -> None:
    unsafe = (
        "audio_part_context[surface=bad P1=live_global_mix "
        "P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true "
        "P1_deck_audio=stems deck1=A deck2=B together_audio=P1 "
        "per_deck_audio=attached duplicate_audio=same_master_not_deck_split "
        "rule=part_labels_not_outcome_verdict]"
    )

    assert normalize_audio_part_context_text(unsafe) is None


def test_audio_window_map_structures_old_action_future_without_extra_audio() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.72)
    state.recent_moves = [(0.7, "A_low: flat->killed")]

    out = render_audio_window_map(
        state,
        ["A_low: flat->killed"],
        audio_seconds=6.0,
        lookahead_part_label="P2",
        lookahead_horizon_s=3.0,
    )

    assert out is not None
    assert out["p1"] == "master_global_mix"
    assert out["p1_heard"] is True
    assert out["timeline"] == "past_action_future"
    assert out["pre_s"] == [-6.0, -1.0]
    assert out["current_s"] == [-1.0, 0.0]
    assert out["action_s"] == [-1.0, 0.0]
    assert out["together_audio"] == "P1_global_mix"
    assert out["deckA_audio"] == "not_attached"
    assert out["deckB_audio"] == "not_attached"
    assert out["duplicate_audio"] == "same_master_not_deck_split"
    assert out["move_anchors"] == [
        {
            "label": "A_low: flat->killed",
            "token": "A_low:_flat-_killed",
            "age_s": 0.7,
            "relation": "inside_P1",
        }
    ]
    assert out["future"]["part"] == "P2"
    assert out["future"]["heard"] is False
    assert out["future"]["span_s"] == [0.0, 3.0]
    assert out["future"]["rule"] == "forecast_only_not_audience_evidence"
    assert out["rule"] == "time_alignment_not_outcome_verdict"


def test_audio_window_context_keeps_audio_source_limits_before_long_move_anchors() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.72)
    long_moves = [
        "A_low: flat->killed with a very long controller label that could otherwise push source limits away",
        "A_filter: flat->boosted with another long controller label in the same live proof window",
        "B_hi: flat->cut with a third long controller label from the bounded recent move list",
    ]

    out = render_audio_window_context(state, long_moves, audio_seconds=6.0)

    assert out is not None
    early = out[:420]
    assert "P1=master_global_mix" in early
    assert "P1_heard=true" in early
    assert "timeline=past_action_future" in early
    assert "together_audio=P1_global_mix" in early
    assert "deckA_audio=not_attached" in early
    assert "deckB_audio=not_attached" in early
    assert "duplicate_audio=same_master_not_deck_split" in early
    assert "action=-1.0..0.0" in early
    assert "rule=time_alignment_not_outcome_verdict" in early


def test_audio_window_context_trust_validator_rejects_context_poor_packets() -> None:
    safe = (
        "audio_window_context[P1=master_global_mix P1_heard=true "
        "timeline=past_action_future deckA_audio=not_attached "
        "deckB_audio=not_attached per_deck_audio=structured_text_only "
        "duplicate_audio=same_master_not_deck_split deck_separation=deck_lanes_context "
        "lane_aliases=deck1:A,deck2:B action=-1.0..0.0 "
        "rule=time_alignment_not_outcome_verdict]"
    )

    assert normalize_audio_window_context_text(safe) == safe
    assert (
        normalize_audio_window_context_text(
            "audio_window_context[P1=master_global_mix deckA_audio=not_attached "
            "deckB_audio=not_attached]"
        )
        is None
    )
    assert (
        normalize_audio_window_context_text(
            "audio_window_context[P1=master_global_mix P1_heard=true "
            "timeline=past_action_future deckA_audio=attached deckB_audio=not_attached "
            "per_deck_audio=structured_text_only "
            "duplicate_audio=same_master_not_deck_split deck_separation=deck_lanes_context "
            "lane_aliases=deck1:A,deck2:B action=-1.0..0.0 "
            "rule=time_alignment_not_outcome_verdict]"
        )
        is None
    )


def test_audio_window_context_trust_validator_keeps_no_move_contract_intact() -> None:
    state = MusicState()
    state.controller_connected = True

    packet = render_audio_window_context(state, [], audio_seconds=6.0)

    assert packet is not None
    trusted = normalize_audio_window_context_text(packet)
    assert trusted == packet
    assert trusted.endswith("future=not_attached]")
    assert "move_anchor=none" in trusted


def test_audio_window_context_can_reference_attached_deck_pair_parts() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.recent_moves = [(0.4, "A_low: flat->killed")]

    packet = render_audio_window_context(
        state,
        ["A_low: flat->killed"],
        audio_seconds=6.0,
        deck_part_labels={"A": "P2", "B": "P3"},
        deck_part_activity={"A": "active", "B": "silent"},
        deck_part_seconds=3.0,
    )

    assert packet is not None
    assert "deckA_audio=P2" in packet
    assert "deckB_audio=P3" in packet
    assert "per_deck_audio=deck_pair_parts" in packet
    assert "duplicate_audio=separate_deck_pair_parts" in packet
    assert "deck_audio_separation=deck_audio_separation_context" in packet
    assert "deck_part_span=-3.0..0.0" in packet
    assert "deckA_activity=active" in packet
    assert "deckB_activity=silent" in packet
    assert normalize_audio_window_context_text(packet) == packet


def test_audio_window_context_rejects_colliding_deck_part_labels() -> None:
    packet = (
        "audio_window_context[P1=master_global_mix P1_heard=true "
        "timeline=past_action_future together_audio=P1_global_mix decks_together=true "
        "deckA_audio=P2 deckB_audio=P2 per_deck_audio=deck_pair_parts "
        "duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context "
        "deck_audio_separation=deck_audio_separation_context "
        "lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 "
        "action=-1.0..0.0 rule=time_alignment_not_outcome_verdict "
        "move_anchor=none future_heard=false future=not_attached]"
    )

    assert normalize_audio_window_context_text(packet) is None


def test_audio_window_renderers_fall_back_on_conflicting_deck_part_labels() -> None:
    state = MusicState(audible=True, audible_deck="mix")

    text = render_audio_window_context(
        state,
        [],
        audio_seconds=6.0,
        mic_part_label="P2",
        deck_part_labels={"A": "P2", "B": "P3"},
        deck_part_activity={"A": "active", "B": "active"},
        deck_part_seconds=3.0,
    )
    structured = render_audio_window_map(
        state,
        [],
        audio_seconds=6.0,
        mic_part_label="P2",
        deck_part_labels={"A": "P2", "B": "P3"},
        deck_part_activity={"A": "active", "B": "active"},
        deck_part_seconds=3.0,
    )

    assert text is not None
    assert "deckA_audio=not_attached" in text
    assert "deckB_audio=not_attached" in text
    assert "per_deck_audio=structured_text_only" in text
    assert normalize_audio_window_context_text(text) == text
    assert structured is not None
    assert structured["deckA_audio"] == "not_attached"
    assert structured["deckB_audio"] == "not_attached"
    assert structured["per_deck_audio"] == "structured_text_only"


def test_audio_window_map_can_reference_attached_deck_pair_parts() -> None:
    state = MusicState(audible=True, audible_deck="mix")

    out = render_audio_window_map(
        state,
        [],
        audio_seconds=6.0,
        deck_part_labels={"A": "P2", "B": "P3"},
        deck_part_activity={"A": "active", "B": "silent"},
        deck_part_seconds=3.0,
    )

    assert out is not None
    assert out["deckA_audio"] == "P2"
    assert out["deckB_audio"] == "P3"
    assert out["per_deck_audio"] == "deck_pair_parts"
    assert out["duplicate_audio"] == "separate_deck_pair_parts"
    assert out["deck_audio_separation"] == "deck_audio_separation_context"
    assert out["deck_part_span_s"] == [-3.0, 0.0]
    assert out["deck_part_activity"] == {"A": "active", "B": "silent"}


def test_live_deck_context_validators_reject_context_poor_packets() -> None:
    lanes = (
        "deck_lanes_context[A(identity=known route=dominant) | B(identity=unknown route=muted) "
        "lane_aliases=deck1:A,deck2:B rule=per_lane_identity_route_control_not_outcome]"
    )
    deck_ref = (
        "deck_reference_context[(deck1=A identity=known route=dominant) "
        "(deck2=B identity=unknown route=muted) audio=P1_global_mix "
        "per_deck_audio=not_attached isolated_decks=false "
        "rule=deck1_deck2_reference_not_outcome]"
    )
    deck_audio = (
        "deck_audio_context[audio=audible source=global_mix isolated_decks=false "
        "routing=A_dominant B_muted support=single_deck_A "
        "rule=audio_heard_must_be_mapped_through_deck_context]"
    )
    deck_source = (
        "deck_source_context[identity_state=MusicState.deck_state "
        "primary=nowplaying_controller_attribution_to_library_cache resolved=A unresolved=B "
        "sources=rekordbox_xml live_db=not_read event_xml=diagnostic_only "
        "second_deck=independent_source_required "
        "rule=unresolved_deck_is_not_transition_evidence]"
    )

    assert normalize_deck_lanes_context_text(lanes) == lanes
    assert normalize_deck_reference_context_text(deck_ref) == deck_ref
    assert normalize_deck_source_context_text(deck_source) == deck_source
    assert normalize_deck_audio_context_text(deck_audio) == deck_audio
    assert normalize_deck_lanes_context_text("deck_lanes_context[A(identity=known)]") is None
    assert (
        normalize_deck_reference_context_text(
            "deck_reference_context[deck1=A deck2=B audio=P1_global_mix isolated_decks=true]"
        )
        is None
    )
    assert (
        normalize_deck_source_context_text(
            "deck_source_context[identity_state=MusicState.deck_state "
            "second_deck=inferred rule=unresolved_deck_is_transition_evidence]"
        )
        is None
    )
    assert (
        normalize_deck_audio_context_text(
            "deck_audio_context[source=deckA isolated_decks=true "
            "rule=audio_heard_must_be_mapped_through_deck_context]"
        )
        is None
    )


def test_historical_move_signature_sanitizer_rewrites_unsafe_audio_and_verdict() -> None:
    signature = (
        "coach_line | event=MIX_MOVE "
        "| audio_window=audio_window_context[P1=master_global_mix "
        "deckA_audio=attached deckB_audio=stem isolated_decks=true] "
        "| audio_delta=low energy fell 50% (strong) "
        "| said: That was a great transition. "
        "| [midi:A_low@9.0]"
    )

    out = sanitize_historical_move_signature_for_prompt(signature, cap=520)

    assert "deckA_audio=attached" not in out
    assert "deckB_audio=stem" not in out
    assert "isolated_decks=true" not in out
    assert "[midi:" not in out
    assert "great transition" not in out.lower()
    assert "audio_window=omitted_untrusted_audio_window" in out
    assert "said: omitted_past_live_outcome_claim" in out


def test_historical_move_signature_sanitizer_upgrades_legacy_master_audio_window() -> None:
    signature = (
        "coach_line | event=MIX_MOVE "
        "| audio_window=audio_window_context[P1=master_global_mix "
        "move_anchor=A_low@-0.8s:inside_P1 deckA_audio=not_attached] "
        "| said: not a transition, just a single-deck EQ move"
    )

    out = sanitize_historical_move_signature_for_prompt(signature, cap=520)

    assert "legacy_context_upgraded=true" in out
    assert "deckA_audio=not_attached" in out
    assert "deckB_audio=not_attached" in out
    assert "duplicate_audio=same_master_not_deck_split" in out
    assert "deck_separation=deck_lanes_context" in out
    assert "said: not a transition" in out


def test_audio_window_context_rejects_untrusted_part_label() -> None:
    state = MusicState(audible=True)

    out = render_audio_window_context(state, audio_seconds=6.0, lookahead_part_label="deck_A")

    assert out is not None
    assert "deck_A=source_file_lookahead" not in out
    assert "future=not_attached" in out


def test_deck_lane_context_maps_identity_route_and_controls_per_lane() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.72)
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {
        "vol": 112,
        "eq_low": 2,
        "eq_mid": 64,
        "eq_hi": 82,
        "filter": 64,
        "play": True,
    }
    state.deck_b = {
        "vol": 0,
        "eq_low": 64,
        "eq_mid": 64,
        "eq_hi": 64,
        "filter": 100,
        "play": False,
    }
    state.deck_state = DeckState(decks={"A": _deck("Strobe", genre="psytrance")})

    out = render_deck_lane_context(state)

    assert out is not None
    assert out.startswith("deck_lanes_context[")
    assert (
        "A(identity=known title='Strobe' key=8A bpm=128 genre='psytrance' "
        "src=rekordbox_xml conf=0.80"
    ) in out
    assert "route=dominant vol=open low=killed mid=flat hi=boost filter=flat play=on" in out
    assert "B(identity=unknown route=muted vol=closed" in out
    assert "lane_aliases=deck1:A,deck2:B" in out
    assert "rule=per_lane_identity_route_control_not_outcome" in out

    compact = render_deck_lane_context(state, compact=True)

    assert compact is not None
    assert "A=known:dominant" in compact
    assert "B=unknown:muted" in compact
    assert "lane_aliases=deck1:A,deck2:B" in compact


def test_deck_reference_context_names_deck_one_and_deck_two_without_stems() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.72)
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {
        "vol": 110,
        "eq_low": 2,
        "eq_mid": 64,
        "eq_hi": 127,
        "filter": 64,
        "play": True,
    }
    state.deck_b = {
        "vol": 0,
        "eq_low": 64,
        "eq_mid": 64,
        "eq_hi": 64,
        "filter": 64,
        "play": False,
    }
    state.deck_state = DeckState(decks={"A": _deck("Strobe", genre="psytrance")})

    out = render_deck_reference_context(state)

    assert out is not None
    assert out.startswith("deck_reference_context[")
    assert "deck1=A" in out
    assert "identity=known" in out
    assert "title='Strobe'" in out
    assert "genre='psytrance'" in out
    assert "route=dominant" in out
    assert "low=killed" in out
    assert "hi=max" in out
    assert "deck2=B" in out
    assert "identity=unknown" in out
    assert "route=muted" in out
    assert "audio=P1_global_mix" in out
    assert "per_deck_audio=not_attached" in out
    assert "isolated_decks=false" in out
    assert "rule=deck1_deck2_reference_not_outcome" in out


def test_deck_source_context_explains_unresolved_second_deck_source_gap() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.72)
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {"vol": 110, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})

    out = render_deck_source_context(state)

    assert out is not None
    assert out.startswith("deck_source_context[")
    assert "identity_state=MusicState.deck_state" in out
    assert "primary=nowplaying_controller_attribution_to_library_cache" in out
    assert "resolved=A" in out
    assert "unresolved=B" in out
    assert "sources=rekordbox_xml" in out
    assert "live_db=not_read" in out
    assert "event_xml=diagnostic_only" in out
    assert "second_deck=independent_source_required" in out
    assert "rule=unresolved_deck_is_not_transition_evidence" in out

    compact = render_deck_source_context(state, compact=True)

    assert compact is not None
    assert "source_ladder=" not in compact
    assert "second_deck=independent_source_required" in compact


def test_deck_source_context_labels_non_deck_nowplaying_blocker() -> None:
    state = MusicState(audible=False, audible_deck="B", deck_confidence=0.7)
    state.controller_connected = True
    state.deck_state.source_status = {
        "controller": "present",
        "controller_connection": "connected",
        "nowplaying": "blocked_non_deck_owner",
        "nowplaying_owner": "com.apple.webkit.gpu",
        "nowplaying_title": "seen",
        "audible_deck": "B",
        "resolution": "blocked_non_deck_nowplaying",
    }

    out = render_deck_source_context(state)

    assert out is not None
    assert "resolved=none" in out
    assert "controller=present" in out
    assert "controller_connection=connected" in out
    assert "nowplaying=blocked_non_deck_owner" in out
    assert "nowplaying_owner=com.apple.webkit.gpu" in out
    assert "nowplaying_title=seen" in out
    assert "source_audible_deck=B" in out
    assert "resolution=blocked_non_deck_nowplaying" in out
    assert "source_status_rule=diagnostic_not_deck_identity" in out


def test_deck_source_context_renders_source_status_without_deck_rows() -> None:
    state = MusicState(audible=False, audible_deck="none")
    state.deck_state.source_status = {
        "controller": "present",
        "controller_connection": "disconnected",
        "nowplaying": "deck_candidate",
        "nowplaying_title": "none",
        "audible_deck": "none",
        "resolution": "no_single_attributable_deck",
    }

    out = render_deck_source_context(state)
    packet = live_evidence_packet(state, [])

    assert out is not None
    assert "resolved=none" in out
    assert "unresolved=none" in out
    assert "controller=present" in out
    assert "controller_connection=disconnected" in out
    assert "resolution=no_single_attributable_deck" in out
    assert "source_status_rule=diagnostic_not_deck_identity" in out
    assert "transition_block=no_resolved_decks" in packet["mix"]
    assert "second_deck_identity=blocked" in packet["mix"]
    assert "deck_lanes=A_unknown_route_unknown+B_unknown_route_unknown" in packet["mix"]
    assert (
        "deck_reference=deck1_A_unknown_route_unknown+deck2_B_unknown_route_unknown"
        in packet["mix"]
    )
    assert "deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none" in packet["mix"]


def test_deck_source_context_renders_source_resolution_diagnostics() -> None:
    state = MusicState(audible=False, audible_deck="A")
    state.deck_state.source_status = {
        "controller": "present",
        "controller_connection": "connected",
        "library": "present",
        "library_tracks": "24",
        "library_source": "folder_cache",
        "library_match": "ambiguous_label",
        "nowplaying": "deck_candidate",
        "nowplaying_title": "seen",
        "audible_deck": "A",
        "resolution": "library_miss",
        "second_deck_source": "suppressed_requires_independent_source",
        "screen_vision": "disabled",
    }

    out = render_deck_source_context(state)

    assert out is not None
    assert "resolved=none" in out
    assert "unresolved=A+B" in out
    assert "library=present" in out
    assert "library_tracks=24" in out
    assert "library_source=folder_cache" in out
    assert "library_match=ambiguous_label" in out
    assert "second_deck_source=suppressed_requires_independent_source" in out
    assert "screen_vision=disabled" in out
    assert "source_status_rule=diagnostic_not_deck_identity" in out


def test_deck_lane_reference_context_render_source_status_without_deck_rows() -> None:
    state = MusicState()
    state.deck_state.source_status = {
        "controller": "present",
        "controller_connection": "disconnected",
        "resolution": "no_single_attributable_deck",
    }

    lanes = render_deck_lane_context(state)
    reference = render_deck_reference_context(state)

    assert lanes is not None
    assert "A(identity=unknown route=unknown" in lanes
    assert "B(identity=unknown route=unknown" in lanes
    assert "lane_aliases=deck1:A,deck2:B" in lanes
    assert "rule=per_lane_identity_route_control_not_outcome" in lanes
    assert reference is not None
    assert "deck1=A identity=unknown route=unknown" in reference
    assert "deck2=B identity=unknown route=unknown" in reference
    assert "rule=deck1_deck2_reference_not_outcome" in reference


def test_deck_lane_context_keeps_low_confidence_identity_unresolved() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.deck_state = DeckState(
        decks={"A": DeckTrack(title="Maybe", confidence=0.1, source="unknown")}
    )

    out = render_deck_lane_context(state)

    assert out is not None
    assert "A(identity=unresolved src=unknown conf=0.10 route=unknown" in out
    assert "B(identity=unknown route=unknown controls=unobserved)" in out
    assert "title='Maybe'" not in out


def test_deck_lane_context_labels_last_known_identity_as_unverified() -> None:
    state = MusicState(audible=True, audible_deck="B")
    state.controller_connected = True
    state.deck_a = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 127, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_state = DeckState(
        decks={
            "A": DeckTrack(
                title="Strobe",
                track_id="track-1",
                camelot="8A",
                bpm=128.0,
                confidence=0.29,
                source="last_known",
            ),
            "B": DeckTrack(
                title="Signal",
                track_id="track-2",
                camelot="9A",
                bpm=130.0,
                confidence=0.8,
                source="rekordbox_xml",
            ),
        },
        source_status={
            "last_known_sides": "A",
            "last_known_rule": "context_only_not_current_identity_proof",
        },
    )

    lanes = render_deck_lane_context(state)
    reference = render_deck_reference_context(state)
    deck_context = render_deck_context(state)
    packet = live_evidence_packet(state, [])

    assert lanes is not None
    assert "A(identity=last_known_unverified" in lanes
    assert "last_title='Strobe'" in lanes
    assert "last_key=8A" in lanes
    assert "B(identity=known title='Signal'" in lanes
    assert reference is not None
    assert "deck1=A identity=last_known_unverified src=last_known last_title='Strobe'" in reference
    assert deck_context is not None
    assert "resolved=B" in deck_context
    assert "transition_block=single_resolved_deck" in deck_context
    assert "deck_source=deck1_A_unresolved_src_last_known+deck2_B_known_src_rekordbox_xml" in packet[
        "mix"
    ]


def test_deck_audio_context_marks_two_deck_route_as_candidate_support() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 72, "eq_low": 8, "eq_mid": 64, "eq_hi": 64, "filter": 92}
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )

    out = render_deck_audio_context(state)
    deck_context = render_deck_context(state)
    result = apply_live_claim_guard("That transition is forming.", state)
    verdict = apply_live_claim_guard("That was a great transition.", state)

    assert out is not None
    assert "support=two_deck_route" in out
    assert deck_context is not None
    assert "transition_candidate=two_resolved_decks_mixing" in deck_context
    assert result.corrected is False
    assert result.policy == "candidate_not_verdict"
    assert verdict.corrected is True
    assert "transition candidate" in verdict.text


def test_live_claim_guard_allows_verdict_with_citable_deck_pair_audio_delta() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    capture = _deck_pair_audio_capture()
    moves = ["xfader→center"]

    policy, reason = live_claim_policy(state, moves, audio_capture_context=capture)
    result = apply_live_claim_guard(
        "That was a great transition.",
        state,
        moves,
        audio_capture_context=capture,
    )

    assert policy == "supported_verdict"
    assert reason == "two_deck_audio_window_delta_proof"
    assert should_defer_live_claim_stream(state, moves, audio_capture_context=capture) is True
    assert result.corrected is False
    assert result.policy == "supported_verdict"
    assert result.text == "That was a great transition."


def test_live_claim_guard_strips_judge_overpraise_below_strong_score() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    capture = _deck_pair_audio_capture()
    moves = ["xfader→center"]
    judge_line = (
        "[judge:transition@128.4] Judge graded the transition: compatible keys; "
        "both basslines up, low-end mud (blend score 0.50/1)"
    )

    result = apply_live_claim_guard(
        "That was a bomb transition.",
        state,
        moves,
        audio_capture_context=capture,
        judge_evidence_line=judge_line,
    )

    assert result.corrected is True
    assert result.policy == "judge_verdict_not_hype_grade"
    assert result.reason == "judge_score_below_strong_praise"
    assert "restrained" in result.text
    assert "bomb transition" not in result.text
    assert "judge_score=0.50" in result.summary


def test_live_claim_guard_allows_strong_judge_praise_when_score_supports_it() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    capture = _deck_pair_audio_capture()
    moves = ["xfader→center"]
    judge_line = (
        "[judge:transition@128.4] Judge graded the transition: compatible keys; "
        "clean low end, one bass ducked (blend score 0.88/1)"
    )

    result = apply_live_claim_guard(
        "That was a bomb transition.",
        state,
        moves,
        audio_capture_context=capture,
        judge_evidence_line=judge_line,
    )

    assert result.corrected is False
    assert result.policy == "supported_verdict"
    assert result.text == "That was a bomb transition."


def test_live_claim_guard_requires_attached_deck_audio_parts_when_requested() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    capture = _deck_pair_audio_capture()
    moves = ["xfader→center"]

    policy, reason = live_claim_policy(
        state,
        moves,
        audio_capture_context=capture,
        deck_audio_parts_attached=False,
    )
    result = apply_live_claim_guard(
        "That was a great transition.",
        state,
        moves,
        audio_capture_context=capture,
        deck_audio_parts_attached=False,
    )

    assert policy == "candidate_not_verdict"
    assert reason == "deck_audio_parts_not_attached"
    assert should_defer_live_claim_stream(
        state,
        moves,
        audio_capture_context=capture,
        deck_audio_parts_attached=False,
    ) is True
    assert result.corrected is True
    assert result.policy == "candidate_not_verdict"
    assert result.reason == "deck_audio_parts_not_attached"
    assert "transition candidate" in result.text


def test_live_claim_guard_keeps_candidate_when_deck_pair_audio_delta_missing() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    capture = _deck_pair_audio_capture(with_delta=False)
    moves = ["xfader→center"]

    result = apply_live_claim_guard(
        "That was a great transition.",
        state,
        moves,
        audio_capture_context=capture,
    )

    assert result.corrected is True
    assert result.policy == "candidate_not_verdict"
    assert "transition candidate" in result.text


def test_live_claim_guard_keeps_candidate_when_deck_audio_window_missing() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    capture = _deck_pair_audio_capture(with_window=False)
    moves = ["xfader→center"]

    policy, reason = live_claim_policy(state, moves, audio_capture_context=capture)
    result = apply_live_claim_guard(
        "That was a great transition.",
        state,
        moves,
        audio_capture_context=capture,
    )

    assert policy == "candidate_not_verdict"
    assert reason is None
    assert result.corrected is True
    assert result.policy == "candidate_not_verdict"
    assert "transition candidate" in result.text


def test_live_claim_guard_requires_trusted_sources_for_supported_verdict() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A", source="rekordbox_xml"),
            "B": _deck("InB", camelot="9A", source="beatport_scrape"),
        }
    )
    capture = _deck_pair_audio_capture()
    moves = ["xfader→center"]

    result = apply_live_claim_guard(
        "That was a great transition.",
        state,
        moves,
        audio_capture_context=capture,
    )

    assert result.corrected is True
    assert result.policy == "candidate_not_verdict"
    assert "transition candidate" in result.text


def test_deck_audio_separation_context_marks_stereo_capture_as_global_mix_only() -> None:
    out = render_deck_audio_separation_context(
        {
            "requested_device": "BlackHole 2ch",
            "device_name": "BlackHole 2ch",
            "input_channels": 2,
            "opened_channels": 2,
            "sample_rate": 48000,
        }
    )

    assert out.startswith("deck_audio_separation_context[")
    assert "capture_device=BlackHole_2ch" in out
    assert "input_channels=2" in out
    assert "opened_channels=2" in out
    assert "sample_rate=48000" in out
    assert "mode=global_mix_only" in out
    assert "current_capture=P1_global_mix" in out
    assert "gemini_audio=mono_downmix_of_capture" in out
    assert "deckA_audio=not_captured" in out
    assert "deckB_audio=not_captured" in out
    assert "per_deck_audio=not_attached" in out
    assert normalize_deck_audio_separation_context_text(out) == out


def test_deck_audio_separation_context_exposes_unopened_multichannel_capacity() -> None:
    out = render_deck_audio_separation_context(
        {
            "requested_device": "BlackHole 16ch",
            "device_name": "BlackHole 16ch",
            "input_channels": 16,
            "opened_channels": 2,
            "sample_rate": 48000,
            "deck_audio_routing_hint": (
                "rekordbox_deck_routing_hint[source=rekordbox_settings "
                "deck_outputs=A:0,1+B:2,3 "
                "rule=rekordbox_output_routing_hint_not_live_audio_proof]"
            ),
        }
    )

    assert "device_capacity=multichannel_available" in out
    assert "mode=multichannel_device_available_but_runtime_opened_stereo" in out
    assert "routing_hint=rekordbox_settings_A:0+1+B:2+3" in out
    assert "routing_hint_rule=output_routing_not_live_audio_proof" in out
    assert "upgrade_path=multi_channel_deck_pair_capture" in out
    assert normalize_deck_audio_separation_context_text(out) == out


def test_deck_audio_separation_context_marks_too_narrow_auto_capture() -> None:
    out = render_deck_audio_separation_context(
        {
            "requested_device": "BlackHole 2ch",
            "device_name": "BlackHole 2ch",
            "input_channels": 2,
            "opened_channels": 2,
            "sample_rate": 48000,
            "deck_audio_capture_enabled": False,
            "deck_audio_capture_reason": "capture_device_too_few_channels",
            "deck_audio_required_opened_channels": 4,
            "deck_audio_routing_hint": (
                "rekordbox_deck_routing_hint[source=rekordbox_settings "
                "deck_outputs=A:0,1+B:2,3 "
                "rule=rekordbox_output_routing_hint_not_live_audio_proof]"
            ),
        }
    )

    assert "device_capacity=stereo_or_less" in out
    assert "mode=global_mix_only" in out
    assert "required_opened_channels=4" in out
    assert "capture_reason=capture_device_too_few_channels" in out
    assert "setup_block=capture_device_too_few_channels" in out
    assert "routing_hint=rekordbox_settings_A:0+1+B:2+3" in out
    assert "deckA_audio=not_captured" in out
    assert "deckB_audio=not_captured" in out
    assert normalize_deck_audio_separation_context_text(out) == out


def test_deck_audio_separation_context_marks_configured_deck_pair_capture() -> None:
    out = render_deck_audio_separation_context(
        {
            "requested_device": "BlackHole 16ch",
            "device_name": "BlackHole 16ch",
            "input_channels": 16,
            "opened_channels": 4,
            "sample_rate": 48000,
            "master_channels": "0,1,2,3",
            "deck_audio_master_source": "controller_weighted_deck_pairs",
            "deck_channels": {"A": "0,1", "B": "2,3"},
            "deck_audio_capture_enabled": True,
            "deck_audio_rms": {"A": 0.02, "B": 0.0},
            "deck_audio_route_diagnosis": {
                "status": "configured_deck_lane_missing_audio",
                "inactive_sides": "B",
                "active_sides": "A",
                "configured_pairs": "A:0,1+B:2,3",
                "opened_active_pairs": "0,1",
                "active_unassigned_pairs": "none",
                "likely_cause": "inactive_deck_pair_route",
                "next_action": "route_inactive_deck_to_configured_pair",
                "rule": "opened_channel_probe_not_rekordbox_control",
            },
        }
    )

    assert "mode=deck_pair_capture_configured" in out
    assert "current_capture=P1_global_mix_plus_deck_pairs" in out
    assert "master_source=controller_weighted_deck_pairs" in out
    assert "deckA_audio=captured" in out
    assert "deckB_audio=captured" in out
    assert "per_deck_audio=captured_not_attached" in out
    assert "isolated_decks=runtime_capture_available" in out
    assert "deck_pairs=A:0,1+B:2,3" in out
    assert "deck_audio_activity=A_active+B_silent" in out
    assert "route_diagnosis=configured_deck_lane_missing_audio" in out
    assert "likely_cause_inactive_deck_pair_route" in out
    assert "next_action_route_inactive_deck_to_configured_pair" in out
    assert normalize_deck_audio_separation_context_text(out) == out


def test_deck_audio_separation_context_marks_unverified_auto_deck_pair_capture() -> None:
    out = render_deck_audio_separation_context(
        {
            "requested_device": "BlackHole 16ch",
            "device_name": "BlackHole 16ch",
            "input_channels": 16,
            "opened_channels": 4,
            "sample_rate": 48000,
            "master_channels": "0,1,2,3",
            "deck_audio_master_source": "controller_weighted_deck_pairs",
            "deck_channels": {"A": "0,1", "B": "2,3"},
            "deck_audio_capture_configured": True,
            "deck_audio_capture_enabled": False,
            "deck_audio_capture_verified": False,
            "deck_audio_active_sides_seen": "A",
            "deck_audio_rms": {"A": 0.02, "B": 0.0},
            "deck_audio_route_diagnosis": {
                "status": "configured_deck_lane_missing_audio",
                "inactive_sides": "B",
                "active_sides": "A",
                "configured_pairs": "A:0,1+B:2,3",
                "opened_active_pairs": "0,1",
                "active_unassigned_pairs": "none",
                "likely_cause": "inactive_deck_pair_route",
                "next_action": "route_inactive_deck_to_configured_pair",
                "rule": "opened_channel_probe_not_rekordbox_control",
            },
        }
    )

    assert "mode=deck_pair_capture_unverified" in out
    assert "current_capture=P1_global_mix_plus_unverified_deck_pairs" in out
    assert "deckA_audio=captured_unverified" in out
    assert "deckB_audio=captured_unverified" in out
    assert "per_deck_audio=unverified_not_attached" in out
    assert "isolated_decks=false" in out
    assert "verification=awaiting_live_audio_on_both_deck_pairs" in out
    assert "active_sides_seen=A" in out
    assert "deck_audio_activity=A_active+B_silent" in out
    assert "route_diagnosis=configured_deck_lane_missing_audio" in out
    assert "inactive_sides_B" in out
    assert "opened_active_pairs_0_1" in out
    assert "active_unassigned_pairs_none" in out
    assert "likely_cause_inactive_deck_pair_route" in out
    assert "next_action_route_inactive_deck_to_configured_pair" in out
    assert normalize_deck_audio_separation_context_text(out) == out


def test_deck_audio_features_context_labels_per_deck_measurements() -> None:
    out = render_deck_audio_features_context(
        {
            "deck_channels": {"A": "0,1", "B": "2,3"},
            "deck_audio_capture_enabled": True,
            "deck_audio_features": {
                "A": {
                    "activity": "active",
                    "rms": 0.0244,
                    "peak": 0.11,
                    "zcr": 0.045,
                    "flux": 0.008,
                    "crest": 4.51,
                },
                "B": {"activity": "silent", "rms": 0.0002, "peak": 0.002, "zcr": 0.0},
            },
        }
    )

    assert out is not None
    assert out.startswith("deck_audio_features_context[")
    assert "source=deck_pair_capture" in out
    assert "per_deck_audio=captured_features" in out
    assert "A_activity=active" in out
    assert "A_rms=0.024" in out
    assert "A_peak=0.110" in out
    assert "A_zcr=0.045" in out
    assert "A_flux=0.008" in out
    assert "A_crest=4.5" in out
    assert "B_activity=silent" in out
    assert "B_rms=0.000" in out
    assert "rule=deck_audio_features_not_outcome_verdict" in out
    assert normalize_deck_audio_features_context_text(out) == out


def test_deck_audio_features_context_requires_configured_capture() -> None:
    assert (
        render_deck_audio_features_context(
            {
                "deck_audio_capture_enabled": True,
                "deck_audio_features": {"A": {"activity": "active", "rms": 0.02}},
            }
        )
        is None
    )


def test_deck_audio_delta_context_labels_per_deck_feature_changes() -> None:
    out = render_deck_audio_delta_context(
        {
            "deck_channels": {"A": "0,1", "B": "2,3"},
            "deck_audio_capture_enabled": True,
            "deck_audio_deltas": {
                "A": ["rms_rose_100pct_strong", "peak_rose_80pct_strong"],
                "B": ["rms_fell_50pct_strong"],
            },
        }
    )

    assert out is not None
    assert out.startswith("deck_audio_delta_context[")
    assert "source=deck_pair_capture" in out
    assert "per_deck_delta=captured_feature_delta" in out
    assert "A_delta=rms_rose_100pct_strong+peak_rose_80pct_strong" in out
    assert "B_delta=rms_fell_50pct_strong" in out
    assert "rule=deck_audio_delta_not_causal_proof" in out
    assert normalize_deck_audio_delta_context_text(out) == out


def test_deck_audio_delta_context_labels_no_clear_delta_when_lanes_are_stable() -> None:
    out = render_deck_audio_delta_context(
        {
            "deck_channels": {"A": "0,1", "B": "2,3"},
            "deck_audio_capture_enabled": True,
            "deck_audio_features": {
                "A": {"activity": "silent", "rms": 0.0, "peak": 0.0},
                "B": {"activity": "silent", "rms": 0.0, "peak": 0.0},
            },
        }
    )

    assert out is not None
    assert out.startswith("deck_audio_delta_context[")
    assert "A_delta=no_clear_delta" in out
    assert "B_delta=no_clear_delta" in out
    assert "rule=deck_audio_delta_not_causal_proof" in out
    assert normalize_deck_audio_delta_context_text(out) == out


def test_deck_audio_window_context_labels_pre_and_current_deck_lanes() -> None:
    out = render_deck_audio_window_context(
        {
            "deck_channels": {"A": "0,1", "B": "2,3"},
            "deck_audio_capture_enabled": True,
            "deck_audio_windows": {
                "pre_s": [-6.0, -1.0],
                "current_s": [-1.0, 0.0],
                "A": {
                    "pre": {"activity": "active", "rms": 0.02, "peak": 0.05, "flux": 0.004},
                    "current": {
                        "activity": "active",
                        "rms": 0.04,
                        "peak": 0.1,
                        "flux": 0.009,
                    },
                    "delta": ["rms_rose_100pct_strong"],
                },
                "B": {
                    "pre": {"activity": "active", "rms": 0.03, "peak": 0.09, "flux": 0.006},
                    "current": {
                        "activity": "silent",
                        "rms": 0.001,
                        "peak": 0.003,
                        "flux": 0.001,
                    },
                    "delta": ["rms_fell_96pct_strong"],
                },
            },
        }
    )

    assert out is not None
    assert out.startswith("deck_audio_window_context[")
    assert "source=deck_pair_capture" in out
    assert "timeline=pre_action_current" in out
    assert "pre=-6.0..-1.0" in out
    assert "current=-1.0..0.0" in out
    assert "A_pre=active_rms_0.020_peak_0.050_flux_0.004" in out
    assert "A_current=active_rms_0.040_peak_0.100_flux_0.009" in out
    assert "A_delta=rms_rose_100pct_strong" in out
    assert "B_current=silent_rms_0.001_peak_0.003_flux_0.001" in out
    assert "B_delta=rms_fell_96pct_strong" in out
    assert "rule=deck_audio_window_not_causal_or_quality_verdict" in out
    assert normalize_deck_audio_window_context_text(out) == out


def test_deck_audio_window_context_rejects_quality_verdicts() -> None:
    bad = (
        "deck_audio_window_context[source=deck_pair_capture timeline=pre_action_current "
        "per_deck_audio=captured_window_features A_current=active_rms_0.040 "
        "quality_verdict=great_transition "
        "rule=deck_audio_window_not_causal_or_quality_verdict]"
    )

    assert normalize_deck_audio_window_context_text(bad) is None


def test_live_evidence_adds_captured_deck_audio_activity_without_identity_upgrade() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.deck_a = {"vol": 100, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 100, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}

    packet = live_evidence_packet(
        state,
        audio_capture_context={
            "deck_audio_capture_enabled": True,
            "deck_audio_rms": {"A": 0.02, "B": 0.03},
            "deck_audio_features": {
                "A": {"activity": "active", "rms": 0.02},
                "B": {"activity": "active", "rms": 0.03},
            },
            "deck_audio_deltas": {
                "A": ["rms_rose_100pct_strong"],
                "B": ["rms_fell_50pct_strong"],
            },
            "deck_audio_windows": {
                "pre_s": (-6.0, -1.0),
                "current_s": (-1.0, 0.0),
                "A": {
                    "pre": {"activity": "active", "rms": 0.02},
                    "current": {"activity": "active", "rms": 0.04},
                    "delta": ["rms_rose_100pct_strong"],
                },
                "B": {
                    "pre": {"activity": "active", "rms": 0.03},
                    "current": {"activity": "active", "rms": 0.02},
                    "delta": ["rms_fell_50pct_strong"],
                },
            },
        },
    )

    assert "deck_audio_capture=A_active+B_active" in packet["mix"]
    assert "deck_audio_features=A_active_rms_0.020+B_active_rms_0.030" in packet["mix"]
    assert "deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong" in packet[
        "mix"
    ]
    assert (
        "deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_active_pre_0.030_current_0.020"
    ) in packet["mix"]
    assert "transition_block=no_resolved_decks" in packet["mix"]
    assert "transition_candidate=two_resolved_decks_captured_audio" not in packet["mix"]


def test_live_evidence_allows_candidate_when_two_resolved_decks_have_captured_audio() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.deck_state = DeckState(
        decks={
            "A": _deck("Left"),
            "B": _deck("Right", camelot="9A"),
        }
    )

    packet = live_evidence_packet(
        state,
        audio_capture_context={
            "deck_audio_capture_enabled": True,
            "deck_audio_rms": {"A": 0.02, "B": 0.03},
        },
    )

    assert "deck_audio_capture=A_active+B_active" in packet["mix"]
    assert "transition_candidate=two_resolved_decks_captured_audio" in packet["mix"]


def test_deck_audio_separation_context_rejects_attached_stem_claim() -> None:
    bad = (
        "deck_audio_separation_context[deckA_audio=attached deckB_audio=attached "
        "current_capture=P1_global_mix per_deck_audio=attached "
        "rule=separation_capability_not_outcome]"
    )

    assert normalize_deck_audio_separation_context_text(bad) is None


def test_deck_change_context_maps_recent_move_to_current_route() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}

    out = render_deck_change_context(state, ["A_low: cut→killed (big twist)"])

    assert out is not None
    assert "deck_change_context[" in out
    assert "support=single_deck_A" in out
    assert "A_low(now=killed route=dominant)" in out
    assert "rule=history_hint_not_quality_verdict" in out


def test_deck_change_context_maps_xfader_to_two_deck_route() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 72, "eq_low": 8, "eq_mid": 64, "eq_hi": 64, "filter": 92}

    out = render_deck_change_context(state, ["xfader→center"])

    assert out is not None
    assert "support=two_deck_route" in out
    assert "xfader(now=center routes=A:dominant+B:present)" in out


def test_move_effect_context_maps_recent_move_to_dsp_delta() -> None:
    state = MusicState(audible=True, rms=0.12, onset_density=3.0)
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.10,
        "sub": 0.24,
        "low": 0.32,
        "mid": 0.30,
        "high": 0.20,
        "onset_density": 2.0,
    }

    items = render_audio_delta_items(state)
    out = render_move_effect_context(state, ["A_low: flat→killed"])

    assert "sub energy fell 50% (strong)" in items
    assert "low energy fell 50% (strong)" in items
    assert out is not None
    assert "move_effect_context[" in out
    assert "deltas=sub energy fell 50% (strong); low energy fell 50% (strong)" in out
    assert "license=low_kill:sub:pred_fell_" in out
    assert "measured_fell" in out
    assert "rule=move_effect_prediction_and_measurement_agree" in out


def test_move_effect_context_refuses_stale_eq_move_when_controller_state_disagrees() -> None:
    state = MusicState(audible=True, rms=0.12, onset_density=3.0)
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.10,
        "sub": 0.24,
        "low": 0.32,
        "mid": 0.30,
        "high": 0.20,
        "onset_density": 2.0,
    }

    out = render_move_effect_context(state, ["A_low: flat->killed"])

    assert out is not None
    assert "license=low_kill:" not in out
    assert "rule=dsp_delta_not_causal_proof" in out


def test_move_effect_context_prefers_move_aligned_delta_over_flat_tick_delta() -> None:
    state = MusicState(audible=True, rms=0.12, audible_deck="A")
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.move_audio_delta = ["sub energy fell 50% (strong)", "low energy fell 50% (strong)"]

    out = render_move_effect_context(
        state,
        ["A_low: flat->killed"],
        audio_delta_items=[],
    )

    assert out is not None
    assert "deltas=sub energy fell 50% (strong); low energy fell 50% (strong)" in out
    assert "license=low_kill:sub:pred_fell_" in out
    assert "rule=move_effect_prediction_and_measurement_agree" in out


def test_audio_delta_items_include_bounded_master_lufs_receipt() -> None:
    state = MusicState(audible=True, rms=0.12, onset_density=3.0, master_lufs=-11.0)
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.12,
        "master_lufs": -14.0,
        "sub": 0.12,
        "low": 0.16,
        "mid": 0.40,
        "high": 0.32,
        "onset_density": 3.0,
    }

    items = render_audio_delta_items(state)
    mix_keys = live_mix_evidence_keys(state, audio_delta_items=items)

    assert items == ["master lufs delta rose 3 lu (clear)"]
    assert "audio_delta=master_lufs_delta_rose_3_lu_clear" in mix_keys


def test_audio_delta_items_include_brightness_share_receipt() -> None:
    state = MusicState(audible=True, rms=0.12, onset_density=3.0, master_lufs=-14.0)
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.12,
        "master_lufs": -14.0,
        "sub": 0.12,
        "low": 0.16,
        "mid": 0.25,
        "high": 0.25,
        "onset_density": 3.0,
    }

    items = render_audio_delta_items(state)
    mix_keys = live_mix_evidence_keys(state, audio_delta_items=items)

    assert items == [
        "mid energy rose 60% (strong)",
        "high energy rose 28% (clear)",
        "brightness share rose 44% (strong)",
    ]
    assert "audio_delta=brightness_share_rose_44pct_strong" in mix_keys


def test_audio_delta_items_strip_flat_master_lufs_receipt() -> None:
    state = MusicState(audible=True, rms=0.12, onset_density=3.0, master_lufs=-13.8)
    state.prev_perceive = {"master_lufs": -14.0}

    assert render_audio_delta_items(state) == []


def test_audio_delta_items_strip_flat_brightness_share_receipt() -> None:
    state = MusicState(audible=True, rms=0.12, onset_density=3.0)
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.27, "high": 0.24}
    state.prev_perceive = {
        "sub": 0.12,
        "low": 0.16,
        "mid": 0.25,
        "high": 0.25,
        "rms": 0.12,
        "onset_density": 3.0,
    }

    assert render_audio_delta_items(state) == []


def test_move_effect_context_maps_recent_move_to_deck_audio_windows() -> None:
    state = MusicState(audible=True, audible_deck="A")

    out = render_move_effect_context(
        state,
        ["A_low: flat→killed"],
        audio_delta_items=[],
        audio_capture_context=_deck_pair_audio_capture(),
    )

    assert out is not None
    assert "move_effect_context[" in out
    assert "deck_deltas=A:rms_rose_60pct_strong+B:rms_fell_20pct_slight" in out
    assert "deck_windows=A:active:pre_0.015:current_0.024:delta_rms_rose_60pct_strong" in out
    assert "B:active:pre_0.031:current_0.031:delta_rms_fell_20pct_slight" in out
    assert "rule=move_audio_timing_not_causal_or_quality_proof" in out


def test_move_effect_context_licenses_xfade_when_curve_and_deck_delta_agree() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.recent_moves = [(0.8, "xfader→center"), (0.2, "xfader→B-side")]
    capture = _deck_pair_audio_capture_with_rms_deltas(
        "rms_fell_60pct_strong",
        "rms_rose_20pct_slight",
    )

    out = render_move_effect_context(
        state,
        ["xfader→B-side"],
        audio_delta_items=[],
        audio_capture_context=capture,
    )

    assert out is not None
    assert "license=xfade:center_to_b_side:" in out
    assert "A_pred_fell_7db+B_pred_rose_3db" in out
    assert "measured_match" in out
    assert "rule=move_effect_prediction_and_measurement_agree" in out


def test_move_effect_context_keeps_xfade_watch_rule_when_previous_bucket_missing() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.recent_moves = [(0.2, "xfader→B-side")]
    capture = _deck_pair_audio_capture_with_rms_deltas(
        "rms_fell_60pct_strong",
        "rms_rose_20pct_slight",
    )

    out = render_move_effect_context(
        state,
        ["xfader→B-side"],
        audio_delta_items=[],
        audio_capture_context=capture,
    )

    assert out is not None
    assert "license=xfade:" not in out
    assert "rule=move_audio_timing_not_causal_or_quality_proof" in out


def test_grounding_refs_render_only_registered_deck_move_atoms() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.set_start_at = time.time() - 42.0
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    state.recent_moves = [(1.2, "A_low: flat→killed (big twist)")]
    state.audio_delta = ["sub energy fell 50% (strong)"]
    move_key = midi_evidence_key("A_low: flat→killed (big twist)")
    mix_keys = live_mix_evidence_keys(state, ["A_low: flat→killed (big twist)"])

    assert move_evidence_atoms(state, ["A_low: flat→killed (big twist)"]) == [(move_key, 40.8)]
    assert "deck_audio_support=single_deck_A" in mix_keys
    assert "transition_block=single_resolved_deck" in mix_keys
    assert "second_deck_identity=unknown_or_suppressed" in mix_keys
    assert "deck_lanes=A_known_route_dominant+B_unknown_route_muted" in mix_keys
    assert "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted" in mix_keys
    assert "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none" in mix_keys
    assert "move_effect=low_kill:sub:pred_fell_19db:measured_fell" in mix_keys
    assert "move_effect=sub_energy_fell_50pct_strong" in mix_keys

    out = render_grounding_ref_context(
        state,
        registry_snapshot={
            "midi": {move_key: (40.8,)},
            "mix": {key: (42.0,) for key in mix_keys},
        },
        moves=["A_low: flat→killed (big twist)"],
    )

    assert out is not None
    assert f"[midi:{move_key}@40.8]" in out
    assert "[mix:deck_audio_support=single_deck_A]" in out
    assert "[mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted]" in out
    assert "[mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted]" in out
    assert "[mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none]" in out
    assert "[mix:move_effect=low_kill:sub:pred_fell_19db:measured_fell]" in out
    assert "[mix:move_effect=sub_energy_fell_50pct_strong]" in out
    assert render_grounding_ref_context(state, registry_snapshot={}) is None


def test_grounding_refs_render_registered_deck_audio_window_receipt() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {"vol": 112, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 96, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    audio_capture_context = {
        "deck_audio_capture_enabled": True,
        "deck_audio_rms": {"A": 0.04, "B": 0.02},
        "deck_audio_features": {
            "A": {"activity": "active", "rms": 0.04},
            "B": {"activity": "active", "rms": 0.02},
        },
        "deck_audio_deltas": {
            "A": ["rms_rose_100pct_strong"],
            "B": ["rms_fell_33pct_clear"],
        },
        "deck_audio_windows": {
            "A": {
                "pre": {"activity": "active", "rms": 0.02},
                "current": {"activity": "active", "rms": 0.04},
            },
            "B": {
                "pre": {"activity": "active", "rms": 0.03},
                "current": {"activity": "active", "rms": 0.02},
            },
        },
    }
    mix_keys = live_mix_evidence_keys(state, audio_capture_context=audio_capture_context)
    expected = (
        "deck_audio_window=A_active_pre_0.020_current_0.040+"
        "B_active_pre_0.030_current_0.020"
    )

    out = render_grounding_ref_context(
        state,
        registry_snapshot={"mix": {key: (42.0,) for key in mix_keys}},
        audio_capture_context=audio_capture_context,
    )

    assert expected in mix_keys
    assert out is not None
    assert f"[mix:{expected}]" in out


def test_live_evidence_context_renders_deck_move_and_audio_categories() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.set_start_at = time.time() - 42.0
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    state.recent_moves = [(1.2, "A_low: flat→killed (big twist)")]
    state.audio_delta = ["sub energy fell 50% (strong)"]

    packet = live_evidence_packet(state, ["A_low: flat→killed (big twist)"])
    out = render_live_evidence_context(state, ["A_low: flat→killed (big twist)"])

    assert packet["midi"] == [
        {
            "key": midi_evidence_key("A_low: flat→killed (big twist)"),
            "t": 40.8,
        }
    ]
    assert "transition_block=single_resolved_deck" in packet["mix"]
    assert "second_deck_identity=unknown_or_suppressed" in packet["mix"]
    assert "deck_lanes=A_known_route_dominant+B_unknown_route_muted" in packet["mix"]
    assert (
        "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted" in packet["mix"]
    )
    assert "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none" in packet["mix"]
    assert "move_scope=single_deck_move_A" in packet["mix"]
    assert "move_effect=low_kill:sub:pred_fell_19db:measured_fell" in packet["mix"]
    assert "move_effect=sub_energy_fell_50pct_strong" in packet["mix"]
    assert out is not None
    assert "live_evidence[" in out
    assert "refs=midi:" in out
    assert "mix:transition_block=single_resolved_deck" in out
    assert "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted" in out
    assert "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted" in out
    assert "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none" in out
    assert "rule=evidence_categories_not_quality_verdict" in out


def test_live_evidence_context_marks_single_deck_even_without_recent_moves() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})

    out = render_live_evidence_context(state, [])

    assert out == (
        "live_evidence[refs=mix:transition_block=single_resolved_deck,"
        "mix:second_deck_identity=unknown_or_suppressed,"
        "mix:deck_lanes=A_known_route_unknown+B_unknown_route_unknown,"
        "mix:deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown,"
        "mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none "
        "mix=transition_block=single_resolved_deck,"
        "second_deck_identity=unknown_or_suppressed,"
        "deck_lanes=A_known_route_unknown+B_unknown_route_unknown,"
        "deck_reference=deck1_A_known_route_unknown+deck2_B_unknown_route_unknown,"
        "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none "
        "rule=evidence_categories_not_quality_verdict]"
    )


def test_live_evidence_context_marks_controller_reference_without_resolved_decks() -> None:
    state = MusicState(audible=False, audible_deck="mix")
    state.controller_connected = True
    state.xfader = 64
    state.deck_a = {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 72, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}

    packet = live_evidence_packet(state, [])
    out = render_live_evidence_context(state, [])

    assert "transition_block=no_resolved_decks" in packet["mix"]
    assert "second_deck_identity=blocked" in packet["mix"]
    assert "deck_lanes=A_unknown_route_dominant+B_unknown_route_present" in packet["mix"]
    assert (
        "deck_reference=deck1_A_unknown_route_dominant+deck2_B_unknown_route_present"
        in packet["mix"]
    )
    assert "deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none" in packet["mix"]
    assert out is not None
    assert "mix:transition_block=no_resolved_decks" in out
    assert "mix:deck_reference=deck1_A_unknown_route_dominant+deck2_B_unknown_route_present" in out
    assert "mix:deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none" in out


def test_live_evidence_context_filters_stale_implicit_moves() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    state.recent_moves = [(9.0, "A_low: flat→killed (big twist)")]

    out = render_live_evidence_context(state)

    assert out is not None
    assert "move_scope=single_deck_move_A" not in out
    assert "midi:" not in out
    assert "transition_block=single_resolved_deck" in out


def test_live_claim_guard_licenses_grounded_move_effect_causal_verdict() -> None:
    state = MusicState(audible=True, rms=0.12, audible_deck="A")
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.10,
        "sub": 0.24,
        "low": 0.32,
        "mid": 0.30,
        "high": 0.20,
        "onset_density": 2.0,
    }
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    moves = ["A_low: flat→killed"]

    result = apply_live_claim_guard("That low cut cleaned the mix.", state, moves)

    assert should_defer_live_claim_stream(state, moves) is True
    assert result.corrected is False
    assert result.policy == "move_effect_supported"
    assert result.reason == "prediction_and_measured_delta_agree"
    assert result.text == "That low cut cleaned the mix."
    assert "low_kill:sub:pred_fell_19db:measured_fell" in result.summary
    assert "move_effect=low_kill:sub:pred_fell_19db:measured_fell" in result.summary


def test_live_claim_guard_licenses_grounded_control_texture_causality() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.move_audio_delta = ["sub energy fell 50% (strong)", "low energy fell 50% (strong)"]
    moves = ["A_low: flat->killed"]

    result = apply_live_claim_guard("That low cut made it thin out.", state, moves)

    assert result.corrected is False
    assert result.policy == "move_effect_supported"
    assert result.reason == "prediction_and_measured_delta_agree"
    assert result.text == "That low cut made it thin out."
    assert "low_kill:sub:pred_fell_" in result.summary


def test_live_claim_guard_refuses_texture_word_when_direction_disagrees() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.move_audio_delta = ["sub energy fell 50% (strong)", "low energy fell 50% (strong)"]

    result = apply_live_claim_guard(
        "That EQ move made the low end boomy.",
        state,
        ["A_low: flat->killed"],
    )

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"


@pytest.mark.parametrize(
    "reply",
    [
        "That EQ move made the low end boomy.",
        "That low cut took the weight out.",
        "That low cut made the mix thinner.",
    ],
)
def test_live_claim_guard_refuses_unlicensed_control_texture_causality(reply: str) -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.move_audio_delta = ["mid energy rose 20% (slight)"]

    result = apply_live_claim_guard(reply, state, ["A_low: flat->killed"])

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"
    assert "can't tell" in result.text.lower()


def test_live_claim_guard_allows_broad_texture_read_without_control_causality() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.move_audio_delta = ["sub energy fell 50% (strong)", "low energy fell 50% (strong)"]
    reply = "The low end got boomy for a moment."

    result = apply_live_claim_guard(reply, state, ["A_low: flat->killed"])

    assert result.corrected is False
    assert result.text == reply


def test_live_claim_guard_refuses_move_effect_when_measured_bands_are_flat() -> None:
    state = MusicState(audible=True, rms=0.12, audible_deck="A")
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.12,
        "sub": 0.12,
        "low": 0.16,
        "mid": 0.40,
        "high": 0.32,
        "onset_density": 2.0,
    }
    state.deck_state = DeckState(decks={"A": _deck("OutA", camelot="8A")})
    moves = ["A_low: flat→killed"]

    result = apply_live_claim_guard("That low cut cleaned the mix.", state, moves)

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"
    assert "can't tell" in result.text.lower()


def test_live_claim_guard_refuses_stale_eq_kill_when_controller_state_disagrees() -> None:
    state = MusicState(audible=True, rms=0.12, audible_deck="A")
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {
        "rms": 0.10,
        "sub": 0.24,
        "low": 0.32,
        "mid": 0.30,
        "high": 0.20,
        "onset_density": 2.0,
    }

    result = apply_live_claim_guard("That low cut cleaned the mix.", state, ["A_low: flat->killed"])

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"
    assert "can't tell" in result.text.lower()


def test_live_claim_guard_refuses_stale_eq_boost_when_controller_state_disagrees() -> None:
    state = MusicState(audible=True, rms=0.12, audible_deck="A")
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.bands = {"sub": 0.24, "low": 0.32, "mid": 0.30, "high": 0.20}
    state.prev_perceive = {
        "rms": 0.10,
        "sub": 0.12,
        "low": 0.16,
        "mid": 0.30,
        "high": 0.20,
        "onset_density": 2.0,
    }

    result = apply_live_claim_guard("That low boost opened the mix.", state, ["A_low: flat->boosted"])

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"
    assert "can't tell" in result.text.lower()


def test_live_claim_guard_prefers_move_aligned_delta_over_flat_tick_delta() -> None:
    state = MusicState(audible=True, rms=0.12, audible_deck="A")
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.move_audio_delta = ["sub energy fell 50% (strong)", "low energy fell 50% (strong)"]

    result = apply_live_claim_guard(
        "That low cut cleaned the mix.",
        state,
        ["A_low: flat->killed"],
        audio_delta_items=[],
    )
    mix_keys = live_mix_evidence_keys(state, ["A_low: flat->killed"], audio_delta_items=[])

    assert result.corrected is False
    assert result.policy == "move_effect_supported"
    assert "low_kill:sub:pred_fell_" in result.summary
    assert "move_effect=low_kill:sub:pred_fell_19db:measured_fell" in mix_keys
    assert "move_effect=sub_energy_fell_50pct_strong" in mix_keys


def test_live_claim_guard_licenses_xfade_effect_when_curve_and_deck_delta_agree() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.recent_moves = [(0.8, "xfader→center"), (0.2, "xfader→B-side")]
    capture = _deck_pair_audio_capture_with_rms_deltas(
        "rms_fell_60pct_strong",
        "rms_rose_20pct_slight",
    )

    result = apply_live_claim_guard(
        "The crossfader opened the blend.",
        state,
        ["xfader→B-side"],
        audio_delta_items=[],
        audio_capture_context=capture,
    )

    assert result.corrected is False
    assert result.policy == "move_effect_supported"
    assert result.reason == "prediction_and_measured_delta_agree"
    assert "xfade:center_to_b_side:" in result.summary
    assert "move_effect=xfade:center_to_b_side:" in result.summary


def test_live_claim_guard_refuses_xfade_effect_when_deck_delta_disagrees() -> None:
    state = MusicState(audible=True, audible_deck="mix")
    state.recent_moves = [(0.8, "xfader→center"), (0.2, "xfader→B-side")]
    capture = _deck_pair_audio_capture_with_rms_deltas(
        "rms_rose_60pct_strong",
        "rms_fell_20pct_slight",
    )

    result = apply_live_claim_guard(
        "The crossfader opened the blend.",
        state,
        ["xfader→B-side"],
        audio_delta_items=[],
        audio_capture_context=capture,
    )

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"
    assert "can't tell" in result.text.lower()


def test_live_claim_guard_corrects_bare_move_effect_quality_verdict() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    state.audio_delta = ["low energy fell 50% (strong)"]
    moves = ["A_low: flat→killed"]

    result = apply_live_claim_guard("That landed.", state, moves)

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert "That landed" not in result.text
    assert "can't tell" in result.text.lower()


def test_live_claim_guard_suppresses_eq_audio_song_detail_verdict() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    state.audio_delta = ["low energy fell 50% (strong)"]
    moves = ["A_low: flat->killed"]

    result = apply_live_claim_guard(
        "That EQ move made the vocal open up and the kick got tighter.",
        state,
        moves,
    )

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"
    assert "vocal" not in result.text.lower()
    assert "kick" not in result.text.lower()
    assert "tighter" not in result.text.lower()


def test_live_claim_guard_preserves_move_effect_correlation_disclaimer() -> None:
    state = MusicState(audible=True, rms=0.12, audible_deck="A")
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {"sub": 0.24, "low": 0.32}
    reply = "Around the move, low energy fell; not causal proof yet."

    result = apply_live_claim_guard(reply, state, ["A_low: flat→killed"])

    assert result.corrected is False
    assert result.text == reply


def test_live_claim_guard_corrects_mixer_low_kill_contradiction() -> None:
    state = MusicState(audible=True, audible_deck="mix", deck_confidence=0.5)
    state.controller_connected = True
    state.xfader = 17
    state.deck_a = {"vol": 0, "eq_low": 81, "eq_mid": 73, "eq_hi": 73, "filter": 64}
    state.deck_b = {"vol": 127, "eq_low": 78, "eq_mid": 83, "eq_hi": 89, "filter": 60}
    reply = "EQ killed the lows too aggressively when you boosted deck B's mids and highs."

    result = apply_live_claim_guard(reply, state)

    assert result.corrected is True
    assert result.policy == "mixer_contradiction"
    assert result.reason == "low_kill_not_in_mixer_state"
    assert "killed the lows" not in result.text.lower()
    assert "mixer_lows=A:boost+B:boost" in result.summary


def test_live_claim_guard_allows_low_kill_when_mixer_agrees() -> None:
    state = MusicState(audible=True, audible_deck="A", deck_confidence=0.8)
    state.controller_connected = True
    state.deck_a = {"vol": 112, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    reply = "EQ killed the lows on deck A."

    result = apply_live_claim_guard(reply, state)

    assert result.corrected is False
    assert result.text == reply


@pytest.mark.parametrize(
    "reply",
    [
        "you brought the faders up",
        "you killed the lows",
        "you cut the lows",
        "You killed the lows there.",
        "that low cut cleaned the mix",
        "that EQ move cleaned up the low end",
        "that filter sweep paid off",
        "Bring the high-pass filter back down to 12 o'clock",
        "You pulled the faders up and it got muddy.",
        "That high-frequency rise on Deck A got a bit too piercing before you pulled it back.",
    ],
)
def test_live_claim_guard_corrects_no_move_control_causality(reply: str) -> None:
    state = MusicState(controller_connected=True)

    result = apply_live_claim_guard(reply, state, [])

    assert result.corrected is True
    assert result.policy == "single_deck_control_not_grounded"
    assert result.reason == "control_causality_without_moves"
    assert "faders" not in result.text.lower()
    assert "high-pass" not in result.text.lower()


def test_live_claim_guard_salvages_sound_clause_before_no_move_control_claim() -> None:
    state = MusicState(controller_connected=True)

    result = apply_live_claim_guard(
        "That synth clashed with the pad when you brought the faders up.",
        state,
        [],
    )

    assert result.corrected is True
    assert result.policy == "single_deck_control_not_grounded"
    assert result.text == "That synth clashed with the pad."


def test_live_claim_guard_strips_no_move_controller_absence_claim() -> None:
    state = MusicState(audible=True, controller_connected=True, audible_deck="none")

    result = apply_live_claim_guard(
        (
            "That high-speed drum pattern dropped into a stripped-back synth texture. "
            "Since you didn't touch the controller, the track's own layout created the space."
        ),
        state,
        [],
        event_type="PHASE",
    )

    assert result.corrected is True
    assert result.policy == "single_deck_control_not_grounded"
    assert result.reason == "control_causality_without_moves"
    assert result.text == "That high-speed drum pattern dropped into a stripped-back synth texture."
    assert "controller" not in result.text.lower()


def test_live_claim_guard_strips_no_move_coaching_advice() -> None:
    state = MusicState(audible=True, controller_connected=True, audible_deck="none")

    result = apply_live_claim_guard(
        "That low end was heavy but the build released on the 3 — try the 1 next time.",
        state,
        [],
        event_type="PHASE",
    )

    assert should_defer_live_claim_stream(state, [], event_type="PHASE") is True
    assert result.corrected is True
    assert result.policy == "coaching_advice_not_grounded"
    assert result.reason == "advice_without_recent_move_proof"
    assert "try the 1" not in result.text.lower()
    assert "next time" not in result.text.lower()


def test_live_claim_guard_strips_sync_advice_when_decks_unresolved_even_with_moves() -> None:
    state = MusicState(audible=True, controller_connected=True, audible_deck="mix")
    moves = ["A_vol up (medium)", "B_vol up (medium)", "B_jog nudge forward"]

    result = apply_live_claim_guard(
        (
            "That heavy scratching texture was scraping over the kick, but the kicks stepped "
            "on each other for a half-bar — tighten up the sync before pushing both channel "
            "faders to the top."
        ),
        state,
        moves,
        event_type="HEARTBEAT",
    )

    assert should_defer_live_claim_stream(state, moves, event_type="HEARTBEAT") is True
    assert result.corrected is True
    assert result.policy == "transition_coaching_not_grounded"
    assert result.reason == "no_resolved_decks"
    assert "tighten" not in result.text.lower()
    assert "sync" not in result.text.lower()
    assert "kicks stepped" not in result.text.lower()


def test_live_claim_guard_blocks_harmonic_claim_when_decks_unresolved() -> None:
    state = MusicState(audible=True, controller_connected=True, audible_deck="none")

    result = apply_live_claim_guard(
        (
            "You had two separate tracks playing there with a major harmonic clash. "
            "Keep your ears on the key compatibility before you bring them up."
        ),
        state,
        [],
        event_type="HEARTBEAT",
    )

    assert result.corrected is True
    assert result.policy == "harmonic_claim_not_grounded"
    assert result.reason == "no_citable_key_clash_evidence"
    assert "clear two-deck proof" in result.text
    assert "two separate tracks" not in result.text.lower()
    assert "harmonic clash" not in result.text.lower()
    assert "key compatibility" not in result.text.lower()


def test_live_claim_guard_blocks_harmonic_claim_without_key_event() -> None:
    state = MusicState(audible=True, controller_connected=True, audible_deck="mix")
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    capture = _deck_pair_audio_capture()
    moves = ["xfader→center"]

    result = apply_live_claim_guard(
        "That was a smooth transition, but the keys had a major harmonic clash.",
        state,
        moves,
        audio_capture_context=capture,
    )

    assert result.corrected is True
    assert result.policy == "harmonic_claim_not_grounded"
    assert "harmonic clash" not in result.text.lower()


def test_live_claim_guard_allows_key_clash_event_claim() -> None:
    state = MusicState(audible=True, controller_connected=True, audible_deck="mix")
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )

    result = apply_live_claim_guard(
        "Those keys are clashing.",
        state,
        event_type="KEY_CLASH",
    )

    assert result.corrected is False
    assert result.text == "Those keys are clashing."


@pytest.mark.parametrize(
    "reply",
    [
        "The low end dropped out and the mid felt hollow.",
        "The filter sweep in the track sounded hollow.",
        "The bass got thinner for a moment.",
        "The bass kept trying to crawl under the pads.",
    ],
)
def test_live_claim_guard_preserves_pure_audio_descriptions_without_moves(reply: str) -> None:
    state = MusicState(controller_connected=True)

    result = apply_live_claim_guard(reply, state, [])

    assert result.corrected is False
    assert result.text == reply


def test_live_claim_guard_suppresses_hidden_source_detail_without_detector() -> None:
    state = MusicState(audible=True, audible_deck="A")

    result = apply_live_claim_guard(
        "The vocal opened up and the kick got tighter.",
        state,
        ["A_low: flat→killed"],
    )

    assert result.corrected is True
    assert result.policy == "audio_source_detail_not_proof"
    assert result.reason == "source_detail_without_grounded_detector"
    assert "source-level proof" in result.text
    assert "vocal opened" not in result.text.lower()
    assert should_defer_live_claim_stream(state, ["A_low: flat→killed"]) is True


def test_live_claim_guard_allows_vocal_detail_when_vocal_detector_active() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.vocal_active = True

    result = apply_live_claim_guard("The vocal came in up front.", state)

    assert result.corrected is False
    assert result.text == "The vocal came in up front."


def test_live_claim_guard_allows_kick_detail_on_grounded_kick_event() -> None:
    state = MusicState(audible=True, audible_deck="A")

    result = apply_live_claim_guard(
        "The kick came in clean.",
        state,
        event_type="REENTRY_KICK_LAND",
    )

    assert result.corrected is False
    assert result.text == "The kick came in clean."


def test_live_claim_guard_keeps_move_present_effect_policy() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    moves = ["A_low: flat->killed"]

    result = apply_live_claim_guard(
        "that EQ move cleaned up the low end",
        state,
        moves,
        audio_delta_items=["high energy fell 50% (strong)"],
    )

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"


def test_single_deck_eq_move_blocks_transition_even_with_two_loaded_decks() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )

    out = render_move_context(state, ["A_low: cut→killed (big twist)"])

    assert out is not None
    assert "scope=single_deck_move_A" in out
    assert "controls=eq_kill+low" in out
    assert "transition_block=single_deck_move" in out


def test_crossfader_move_with_two_resolved_decks_marks_mix_candidate() -> None:
    state = MusicState(audible_deck="mix")
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )

    out = render_move_context(state, ["xfader→center"])

    assert out is not None
    assert "scope=cross_deck_move" in out
    assert "controls=xfader" in out
    assert "transition_candidate=two_deck_move_audible_mix" in out


def test_crossfader_move_single_audible_is_watch_not_claim() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )

    out = render_move_context(state, ["xfader→A-side"])

    assert out is not None
    assert "transition_watch=two_deck_move_single_audible" in out


def test_live_claim_guard_corrects_multi_deck_outcome_category() -> None:
    state = MusicState(audible_deck="A")
    state.controller_connected = True
    state.xfader = 0
    state.deck_a = {"vol": 112, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_b = {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64}
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})

    result = apply_live_claim_guard("That was a great blend into the drop.", state)

    assert result.corrected is True
    assert result.policy == "blocked"
    assert result.reason == "single_resolved_deck"
    assert "clear two-deck proof" in result.text
    assert "resolved decks=A" in result.summary
    assert "second deck identity=unknown_or_suppressed" in result.summary
    assert "deck source=resolved=A unresolved=B" in result.summary
    assert "second_deck=independent_source_required" in result.summary
    assert "rule=unresolved_deck_is_not_transition_evidence" in result.summary
    assert "deck lanes=A=known:dominant / B=unknown:muted" in result.summary
    assert "deck lanes=A=known:dominant / B=unknown:muted" not in result.text
    assert "second_deck=independent_source_required" not in result.text


def test_live_claim_guard_generalizes_beyond_transition_word() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )
    moves = ["xfader→A-side"]

    policy, reason = live_claim_policy(state, moves)
    replies = [
        "Nice handoff, that bridge worked.",
        "Clean segue, that switch landed.",
        "The incoming track came in clean.",
    ]
    results = [apply_live_claim_guard(reply, state, moves) for reply in replies]

    assert policy == "watch_not_claim"
    assert reason == "two_deck_move_single_audible"
    assert should_defer_live_claim_stream(state, moves) is True
    assert all(result.corrected for result in results)
    assert all("recent control evidence: xfader→A-side" in result.summary for result in results)


def test_manual_silent_trigger_defers_stream_until_linter() -> None:
    state = MusicState(audible=False, audible_deck="none")
    state.phase = "silent"

    assert should_defer_live_claim_stream(state, [], event_type="MANUAL") is True


def test_live_claim_guard_normalizes_public_self_correction() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    reply = "I can't call that a transition; this is only one deck."

    result = apply_live_claim_guard(reply, state)

    assert result.corrected is True
    assert result.text == "I can't call that a transition until I have clear two-deck proof."


@pytest.mark.parametrize(
    "reply",
    [
        "My bad on the live read. I was wrong about what happened.",
        "I'm doing something stupid about the live read.",
        "resolved decks=none; live evidence gate: transition_block=no_resolved_decks",
    ],
)
def test_live_claim_guard_normalizes_public_diagnostic_without_outcome_claim(reply: str) -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})

    result = apply_live_claim_guard(reply, state)

    assert result.corrected is True
    lower = result.text.lower()
    assert "my bad" not in lower
    assert "wrong" not in lower
    assert "stupid" not in lower
    assert "resolved decks" not in lower
    assert "live evidence gate" not in lower
    assert "clear two-deck proof" in result.text


def test_live_claim_guard_corrects_disclaimer_with_fresh_blend_claim() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    reply = "I can't call that a transition, but that blend was clean."

    result = apply_live_claim_guard(reply, state)

    assert result.corrected is True
    assert "blend was clean" not in result.text
    assert "clear two-deck proof" in result.text


def test_live_claim_guard_defers_mix_candidate_for_verdict_check() -> None:
    state = MusicState(audible_deck="mix")
    state.deck_state = DeckState(
        decks={
            "A": _deck("OutA", camelot="8A"),
            "B": _deck("InB", camelot="9A"),
        }
    )

    result = apply_live_claim_guard("That transition is forming.", state, ["xfader→center"])

    assert should_defer_live_claim_stream(state, ["xfader→center"]) is True
    assert result.corrected is False
    assert result.policy == "candidate_not_verdict"
