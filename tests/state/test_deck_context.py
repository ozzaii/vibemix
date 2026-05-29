# SPDX-License-Identifier: Apache-2.0
"""Prompt-facing deck_context formatter tests."""

from __future__ import annotations

import time

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
    normalize_deck_audio_separation_context_text,
    normalize_deck_lanes_context_text,
    normalize_deck_reference_context_text,
    normalize_deck_source_context_text,
    render_audio_delta_items,
    render_audio_part_context,
    render_audio_window_context,
    render_audio_window_map,
    render_context_feed_contract,
    render_deck_audio_context,
    render_deck_audio_separation_context,
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
) -> DeckTrack:
    return DeckTrack(
        title=title,
        track_id="t1" if title else None,
        bpm=bpm,
        camelot=camelot,
        confidence=confidence,
        source="rekordbox_xml",
    )


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
    assert "per_deck_audio=not_attached" in out
    assert "duplicate_audio=same_master_not_deck_split" in out
    assert "P2=user_mic" in out
    assert "P2_role=user_speech" in out
    assert "P2_deck_audio=none" in out
    assert "P2_rule=not_deck_audio" in out
    assert "P3=source_file_lookahead" in out
    assert "P3_model_heard=true" in out
    assert "P3_audience_heard=false" in out
    assert "P3_span=0.0..+3.0" in out
    assert "P3_deck_audio=none" in out
    assert "P3_rule=forecast_only_not_current_live_evidence" in out
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
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})

    out = render_deck_lane_context(state)

    assert out is not None
    assert out.startswith("deck_lanes_context[")
    assert "A(identity=known title='Strobe' key=8A bpm=128 src=rekordbox_xml conf=0.80" in out
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
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})

    out = render_deck_reference_context(state)

    assert out is not None
    assert out.startswith("deck_reference_context[")
    assert "deck1=A" in out
    assert "identity=known" in out
    assert "title='Strobe'" in out
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
    assert "nowplaying=blocked_non_deck_owner" in out
    assert "nowplaying_owner=com.apple.webkit.gpu" in out
    assert "nowplaying_title=seen" in out
    assert "source_audible_deck=B" in out
    assert "resolution=blocked_non_deck_nowplaying" in out
    assert "source_status_rule=diagnostic_not_deck_identity" in out


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
    assert "candidate" in verdict.text


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
        }
    )

    assert "device_capacity=multichannel_available" in out
    assert "mode=multichannel_device_available_but_runtime_opened_stereo" in out
    assert "upgrade_path=multi_channel_deck_pair_capture" in out
    assert normalize_deck_audio_separation_context_text(out) == out


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
    assert "rule=dsp_delta_not_causal_proof" in out


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
    assert "[mix:move_effect=sub_energy_fell_50pct_strong]" in out
    assert render_grounding_ref_context(state, registry_snapshot={}) is None


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


def test_live_claim_guard_corrects_move_effect_causal_verdict() -> None:
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
    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert result.reason == "dsp_delta_not_causal_proof"
    assert "hold the cause/quality verdict" in result.text
    assert "sub energy fell 50% (strong)" in result.summary


def test_live_claim_guard_corrects_bare_move_effect_quality_verdict() -> None:
    state = MusicState(audible=True, audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    state.audio_delta = ["low energy fell 50% (strong)"]
    moves = ["A_low: flat→killed"]

    result = apply_live_claim_guard("That landed.", state, moves)

    assert result.corrected is True
    assert result.policy == "move_effect_not_verdict"
    assert "That landed" not in result.text
    assert "hold the cause/quality verdict" in result.text


def test_live_claim_guard_preserves_move_effect_correlation_disclaimer() -> None:
    state = MusicState(audible=True, rms=0.12, audible_deck="A")
    state.bands = {"sub": 0.12, "low": 0.16, "mid": 0.40, "high": 0.32}
    state.prev_perceive = {"sub": 0.24, "low": 0.32}
    reply = "Around the move, low energy fell; not causal proof yet."

    result = apply_live_claim_guard(reply, state, ["A_low: flat→killed"])

    assert result.corrected is False
    assert result.text == reply


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
    assert "hold the transition verdict" in result.text
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


def test_live_claim_guard_preserves_self_correction() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    reply = "I can't call that a transition; this is only one deck."

    result = apply_live_claim_guard(reply, state)

    assert result.corrected is False
    assert result.text == reply


def test_live_claim_guard_corrects_disclaimer_with_fresh_blend_claim() -> None:
    state = MusicState(audible_deck="A")
    state.deck_state = DeckState(decks={"A": _deck("Strobe")})
    reply = "I can't call that a transition, but that blend was clean."

    result = apply_live_claim_guard(reply, state)

    assert result.corrected is True
    assert "blend was clean" not in result.text
    assert "hold the transition verdict" in result.text


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
