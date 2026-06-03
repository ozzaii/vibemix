# SPDX-License-Identifier: Apache-2.0
"""Codex curate wrapper — every guard branch, no Codex installed.

The subprocess runner is injected (``_runner``) so these tests exercise the
spawn → timeout → parse → degrade → grounding-revalidation logic without the
``codex`` binary. ``codex_path`` is pointed at a real existing file so
``find_codex`` resolves; the fake runner stands in for ``codex exec``.
"""

from __future__ import annotations

import importlib
import inspect
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.library import codex_curate as codex_mod
from vibemix.library.auto_crate import AutoCrateResult
from vibemix.library.codex_curate import (
    BUILD_SET_TIMEOUT_S,
    CHAT_TIMEOUT_S,
    CodexChatResult,
    build_argv,
    build_prompt,
    build_set_prompt,
    build_set_with_codex,
    build_subprocess_env,
    chat_prompt,
    chat_with_codex,
    curate_with_codex,
    find_codex,
    verify_live_reply_for_viber,
)
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry


def _track(tid: str) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"T{tid}",
        artist="A",
        album="X",
        bpm=124.0,
        key="8A",
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


def _fresh_live_transport() -> dict:
    return {
        "live_context_schema_version": 2,
        "live_context_capabilities": [
            "deck_state",
            "deck_source_status",
            "audio_part_context",
            "deck_audio_separation_context",
            "deck_audio_features_context",
            "deck_audio_delta_context",
            "deck_audio_window_context",
            "audio_window_map",
            "audio_delta",
            "live_evidence",
        ],
    }


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
        "deck_audio_activity=A_active+B_active "
        "rule=separation_capability_not_outcome]"
    )


def _deck_audio_features_context() -> str:
    return (
        "deck_audio_features_context[source=deck_pair_capture window=latest_callback "
        "per_deck_audio=captured_features A_activity=active A_rms=0.024 "
        "A_peak=0.120 A_zcr=0.030 B_activity=active B_rms=0.031 "
        "B_peak=0.140 B_zcr=0.034 rule=deck_audio_features_not_outcome_verdict]"
    )


def _deck_audio_delta_context() -> str:
    return (
        "deck_audio_delta_context[source=deck_pair_capture window=latest_callback "
        "per_deck_delta=captured_feature_delta A_delta=rms_rose_60pct_strong "
        "B_delta=rms_fell_20pct_slight rule=deck_audio_delta_not_causal_proof]"
    )


def _deck_audio_window_context() -> str:
    return (
        "deck_audio_window_context[source=deck_pair_capture "
        "timeline=pre_action_current pre=-6.0..-1.0 current=-1.0..0.0 "
        "action=-1.0..0.0 per_deck_audio=captured_window_features "
        "A_pre=active_rms_0.015_peak_0.090_flux_0.003 "
        "A_current=active_rms_0.024_peak_0.120_flux_0.006 "
        "A_delta=rms_rose_60pct_strong "
        "B_pre=active_rms_0.039_peak_0.160_flux_0.006 "
        "B_current=active_rms_0.031_peak_0.140_flux_0.004 "
        "B_delta=rms_fell_20pct_slight "
        "rule=deck_audio_window_not_causal_or_quality_verdict]"
    )


def _deck_audio_window_evidence() -> str:
    return (
        "deck_audio_window=A_active_pre_0.015_current_0.024+"
        "B_active_pre_0.039_current_0.031"
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
    return {
        "p1": "master_global_mix",
        "p1_heard": True,
        "timeline": "past_action_future",
        "together_audio": "P1_global_mix",
        "decks_together": True,
        "deckA_audio": deck_a,
        "deckB_audio": deck_b,
        "per_deck_audio": "deck_pair_parts",
        "duplicate_audio": "separate_deck_pair_parts",
        "deck_separation": "deck_lanes_context",
        "deck_audio_separation": "deck_audio_separation_context",
        "deck_part_span_s": [-3.0, 0.0],
        "deck_part_activity": {"A": "active", "B": "active"},
        "lane_aliases": "deck1:A,deck2:B",
        "pre_s": [-6.0, -1.0],
        "current_s": [-1.0, 0.0],
        "action_s": [-1.0, 0.0],
        "move_anchors": [],
        "future": {"heard": False, "span": "not_attached"},
        "rule": "time_alignment_not_outcome_verdict",
    }


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _track(f"t{i:03d}") for i in range(5)}
    return lib


def _out_path_from_argv(argv: list[str]) -> str:
    return argv[argv.index("-o") + 1]


def _runner_writing(payload, *, returncode=0, stderr="", raw=None):
    """Build a fake subprocess.run that writes ``payload`` to the -o path."""

    def runner(argv, **kw):
        out_path = _out_path_from_argv(argv)
        text = raw if raw is not None else json.dumps(payload)
        Path(out_path).write_text(text, encoding="utf-8")
        return subprocess.CompletedProcess(argv, returncode, stdout="", stderr=stderr)

    return runner


def _write_memory_db(path: Path, signatures: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE moments ("
            "record_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, "
            "ts REAL NOT NULL, kind TEXT NOT NULL, signature TEXT NOT NULL)"
        )
        for idx, signature in enumerate(signatures):
            conn.execute(
                "INSERT INTO moments VALUES (?, ?, ?, ?, ?)",
                (
                    f"20260520-220000:{idx}",
                    "20260520-220000",
                    float(idx),
                    "coach_line",
                    signature,
                ),
            )
        conn.commit()
    finally:
        conn.close()


# -- pure helpers ----------------------------------------------------------- #


def test_build_prompt_has_grounding_rules():
    p = build_prompt("hypnotic warm-up")
    assert "hypnotic warm-up" in p
    assert "ONLY put a track" in p  # grounding rule present


def test_build_set_prompt_has_set_prep_workflow():
    p = build_set_prompt(
        "dark warehouse",
        curve="peak_time",
        name="Peak Set",
        n_slots=3,
        export=True,
    )
    assert "dark warehouse" in p
    assert "prefer the 'peak_time' energy curve" in p
    assert "name the set 'Peak Set'" in p
    assert "target exactly 3 slots" in p
    assert "export requested" in p
    assert "discover_pool" in p
    assert "sequence_set" in p
    assert "expected tool tape is discover_pool" in p
    assert "choose the first/best sequence_set candidate" in p
    assert "Do NOT inspect every candidate one by one" in p
    assert "inspect_candidates ONCE" in p
    assert "metadata_warnings" in p
    assert "do not treat that BPM/key range as verified" in p
    assert "sequence_set already resolves BPM, key, stored vectors" in p
    assert "get_track_sections" in p
    assert "transition_slate" in p
    assert "smart_hot_cues" in p
    assert "export_smart_cues" in p
    assert "export_set" in p


def test_chat_timeout_is_interactive():
    assert CHAT_TIMEOUT_S == BUILD_SET_TIMEOUT_S
    assert inspect.signature(chat_with_codex).parameters["timeout_s"].default == BUILD_SET_TIMEOUT_S
    assert BUILD_SET_TIMEOUT_S >= 180.0


def test_codex_mcp_tool_timeout_allows_batched_candidate_inspection(tmp_path):
    argv = build_argv(
        "/bin/echo",
        mcp_command="python",
        mcp_args=["-m", "vibemix.library.mcp_server"],
        schema_path=str(tmp_path / "schema.json"),
        out_path=str(tmp_path / "out.json"),
        prompt="curate",
    )

    assert codex_mod._MCP_TOOL_TIMEOUT_S >= 120
    assert any(arg == "mcp_servers.vibemix_library.tool_timeout_sec=120" for arg in argv)


def test_chat_prompt_threads_history_and_rules():
    p = chat_prompt(
        "what bridges from this?",
        history=[
            {"role": "you", "text": "playing 124 bpm"},
            {"role": "viber", "text": "keep it tight"},
        ],
    )

    assert "CHAT" in p
    assert "DJ: playing 124 bpm" in p
    assert "Viber: keep it tight" in p
    assert "DJ: what bridges from this?" in p
    assert "Never invent a track" in p
    assert "metadata_warnings" in p
    assert "do not treat that BPM/key range as verified" in p
    assert "transition_slate" in p
    assert "compile_musical_context" in p
    assert "smart_hot_cues" in p
    assert "export_smart_cues" in p
    assert "never raw cue payloads" in p


def test_chat_prompt_omits_stale_viber_live_outcome_from_history():
    p = chat_prompt(
        "what actually happened?",
        history=[
            {"role": "you", "text": "was that good?"},
            {"role": "viber", "text": "Great transition, that blend was clean."},
        ],
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.9}},
        },
    )

    assert "Great transition" not in p
    assert "blend was clean" not in p
    assert "prior Viber live outcome claim omitted" in p
    assert "CHAT HISTORY RULE" in p
    assert "multi_deck_outcome=blocked" in p


def test_chat_prompt_omits_viber_self_correction_from_history():
    p = chat_prompt(
        "ok, what should I do now?",
        history=[
            {
                "role": "viber",
                "text": "I saw a deck A low move, but I can't call it a transition.",
            },
        ],
        live_context={
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.9}},
        },
    )

    assert "I saw a deck A low move" not in p
    assert "can't call it a transition" not in p
    assert "prior Viber live outcome claim omitted" in p


def test_chat_prompt_does_not_advertise_gemini_youtube_tool():
    p = chat_prompt("any external references?")

    assert "ingest_youtube" not in p
    assert "YouTube claim" not in p


def test_chat_prompt_includes_bounded_live_deck_context_guard():
    p = chat_prompt(
        "was that transition good?",
        live_context={
            "live_context_schema_version": 2,
            "live_context_capabilities": [
                "deck_state",
                "deck_source_status",
                "audio_part_context",
                "deck_audio_separation_context",
                "deck_audio_features_context",
                "deck_audio_delta_context",
                "deck_audio_window_context",
                "audio_window_map",
                "audio_delta",
                "live_evidence",
            ],
            "deck": "A",
            "audible": True,
            "phase": "groove",
            "bpm": 128.0,
            "detected_genre": "psytrance",
            "genre_confidence": 0.82,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "t000",
                    "camelot": "8A",
                    "bpm": 128.0,
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
            "deck_source_status": {
                "controller": "present",
                "controller_connection": "connected",
                "nowplaying": "blocked_non_deck_owner",
                "nowplaying_owner": "com.apple.WebKit.GPU",
                "resolution": "blocked_non_deck_nowplaying",
            },
            "deck_audio_features_context": (
                "deck_audio_features_context[source=deck_pair_capture "
                "window=latest_callback per_deck_audio=captured_features "
                "A_activity=active A_rms=0.020 B_activity=silent B_rms=0.000 "
                "rule=deck_audio_features_not_outcome_verdict]"
            ),
            "deck_audio_delta_context": (
                "deck_audio_delta_context[source=deck_pair_capture "
                "window=latest_callback per_deck_delta=captured_feature_delta "
                "A_delta=rms_rose_100pct_strong B_delta=rms_fell_50pct_strong "
                "rule=deck_audio_delta_not_causal_proof]"
            ),
            "audio_window_map": {
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
                        "label": "A_low: flat->killed",
                        "token": "A_low:_flat-_killed",
                        "age_s": 1.5,
                        "relation": "inside_P1",
                    }
                ],
                "future": {"heard": False, "span": "not_attached"},
                "rule": "time_alignment_not_outcome_verdict",
            },
        },
    )

    assert "CURRENT LIVE DECK CONTEXT" in p
    assert "live_context[" in p
    assert "genre=psytrance" in p
    assert "live_context_transport[" in p
    assert "schema=2" in p
    assert (
        "capabilities=deck_state,deck_source_status,audio_part_context,"
        "deck_audio_separation_context,deck_audio_features_context,"
        "deck_audio_delta_context,deck_audio_window_context,audio_window_map,"
        "audio_delta,live_evidence"
    ) in p
    assert "status=fresh_schema_v2" in p
    assert "rule=transport_receipt_not_musical_evidence" in p
    assert "deck_context[" in p
    assert "deck_lanes_context[" in p
    assert "deck_reference_context[" in p
    assert "deck1=A" in p
    assert "deck2=B" in p
    assert "audio=P1_global_mix" in p
    assert "per_deck_audio=not_attached" in p
    assert "deck_source_context[" in p
    assert "controller_connection=connected" in p
    assert "nowplaying=blocked_non_deck_owner" in p
    assert "nowplaying_owner=com.apple.webkit.gpu" in p
    assert "resolution=blocked_non_deck_nowplaying" in p
    assert "source_status_rule=diagnostic_not_deck_identity" in p
    assert "second_deck=independent_source_required" in p
    assert "rule=unresolved_deck_is_not_transition_evidence" in p
    assert "mixer_context[" in p
    assert "deck_audio_context[" in p
    assert "deck_audio_separation_context[" in p
    assert "deck_audio_features_context[" in p
    assert "deck_audio_features_not_outcome_verdict" in p
    assert "deck_audio_delta_context[" in p
    assert "deck_audio_delta_not_causal_proof" in p
    assert "deckA_audio=not_captured" in p
    assert "deckB_audio=not_captured" in p
    assert "source=global_mix" in p
    assert "isolated_decks=false" in p
    assert "audio_part_context[" in p
    assert "surface=viber_live_context" in p
    assert "P1=live_global_mix" in p
    assert "P1_model_heard=false" in p
    assert "P1_runtime_observed=true" in p
    assert "P1_deck_audio=global_mix_not_stems" in p
    assert "audio_window_context[" in p
    assert "P1=master_global_mix" in p
    assert "future=not_attached" in p
    assert "audio_window_map[" in p
    assert "old=pre_s" in p
    assert "current=current_s" in p
    assert "anchors=A_low:_flat-_killed@-1.5s:inside_P1" in p
    assert "deckA_audio=not_attached" in p
    assert "deckB_audio=not_attached" in p
    assert "duplicate_audio=same_master_not_deck_split" in p
    assert "lane_aliases=deck1:A,deck2:B" in p
    assert "A(vol=open low=killed" in p
    assert "B(vol=mid low=flat" in p
    assert "deck=A" in p
    assert "resolved=A" in p
    assert "src=rekordbox_xml" in p
    assert "second_deck_identity=unknown_or_suppressed" in p
    assert "identity_rule=do_not_invent_unresolved_decks" in p
    assert "B(identity=unknown" in p
    assert "transition_block=single_resolved_deck" in p
    assert "claim_policy[" in p
    assert "multi_deck_outcome=blocked" in p
    assert "control_to_music_outcome=do_not_infer" in p
    assert "do not praise or claim a transition/blend" in p


def test_chat_prompt_preserves_deck_pair_audio_window_map():
    p = chat_prompt(
        "what changed on each deck?",
        live_context={
            **_fresh_live_transport(),
            "deck": "mix",
            "audible": True,
            "deck_state": {
                "A": {"title": "Strobe", "track_id": "t000", "confidence": 0.82},
                "B": {"title": "Pulse", "track_id": "t001", "confidence": 0.8},
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 64,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 96, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "audio_part_context": (
                "audio_part_context[surface=gemini_parts P1=live_global_mix "
                "P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true "
                "P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B "
                "together_audio=P1 part_order=P1,P2,P3 per_deck_audio=deck_pair_parts "
                "duplicate_audio=separate_deck_pair_parts deckA_part=P2 "
                "P2=deckA_configured_capture P2_model_heard=true P2_audience_heard=false "
                "P2_span=-3.0..0.0 P2_deck_audio=deckA_configured_capture "
                "P2_rule=deck_pair_capture_reference_not_quality_verdict deckB_part=P3 "
                "P3=deckB_configured_capture P3_model_heard=true P3_audience_heard=false "
                "P3_span=-3.0..0.0 P3_deck_audio=deckB_configured_capture "
                "P3_rule=deck_pair_capture_reference_not_quality_verdict "
                "rule=part_labels_not_outcome_verdict]"
            ),
            "audio_window_context": (
                "audio_window_context[P1=master_global_mix P1_heard=true "
                "timeline=past_action_future together_audio=P1_global_mix decks_together=true "
                "deckA_audio=P2 deckB_audio=P3 per_deck_audio=deck_pair_parts "
                "duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context "
                "deck_audio_separation=deck_audio_separation_context "
                "deck_part_span=-3.0..0.0 deckA_activity=active deckB_activity=silent "
                "lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 "
                "action=-1.0..0.0 rule=time_alignment_not_outcome_verdict "
                "move_anchor=none future_heard=false future=not_attached]"
            ),
            "audio_window_map": {
                "p1": "master_global_mix",
                "p1_heard": True,
                "timeline": "past_action_future",
                "together_audio": "P1_global_mix",
                "decks_together": True,
                "deckA_audio": "P2",
                "deckB_audio": "P3",
                "per_deck_audio": "deck_pair_parts",
                "duplicate_audio": "separate_deck_pair_parts",
                "deck_separation": "deck_lanes_context",
                "deck_audio_separation": "deck_audio_separation_context",
                "deck_part_span_s": [-3.0, 0.0],
                "deck_part_activity": {"A": "active", "B": "silent"},
                "lane_aliases": "deck1:A,deck2:B",
                "pre_s": [-6.0, -1.0],
                "current_s": [-1.0, 0.0],
                "action_s": [-1.0, 0.0],
                "move_anchors": [],
                "future": {"heard": False, "span": "not_attached"},
                "rule": "time_alignment_not_outcome_verdict",
            },
        },
    )

    assert "audio_part_context[" in p
    assert "per_deck_audio=deck_pair_parts" in p
    assert "audio_window_context[" in p
    assert "deckA_audio=P2" in p
    assert "deckB_audio=P3" in p
    assert "duplicate_audio=separate_deck_pair_parts" in p
    assert "audio_window_map[" in p
    assert "deckA_audio=P2 deckB_audio=P3" in p


def test_chat_prompt_recomputes_audio_window_when_part_labels_disagree():
    p = chat_prompt(
        "what changed on each deck?",
        live_context={
            **_fresh_live_transport(),
            "deck": "mix",
            "audible": True,
            "deck_state": {
                "A": {"title": "Strobe", "track_id": "t000", "confidence": 0.82},
                "B": {"title": "Pulse", "track_id": "t001", "confidence": 0.8},
            },
            "audio_part_context": (
                "audio_part_context[surface=gemini_parts P1=live_global_mix "
                "P1_model_heard=true P1_runtime_observed=true P1_audience_heard=true "
                "P1_span=-6.0..0.0 P1_deck_audio=global_mix_not_stems deck1=A deck2=B "
                "together_audio=P1 part_order=P1,P2,P3,P4,P5 per_deck_audio=deck_pair_parts "
                "duplicate_audio=separate_deck_pair_parts deckA_part=P4 "
                "P4=deckA_configured_capture P4_model_heard=true P4_audience_heard=false "
                "P4_span=-3.0..0.0 P4_deck_audio=deckA_configured_capture "
                "P4_rule=deck_pair_capture_reference_not_quality_verdict "
                "P4_activity=deckA_active deckB_part=P5 "
                "P5=deckB_configured_capture P5_model_heard=true P5_audience_heard=false "
                "P5_span=-3.0..0.0 P5_deck_audio=deckB_configured_capture "
                "P5_rule=deck_pair_capture_reference_not_quality_verdict "
                "P5_activity=deckB_silent P2=user_mic P2_model_heard=true "
                "P2_role=user_speech P2_deck_audio=none P2_rule=not_deck_audio "
                "P3=source_file_lookahead P3_model_heard=true P3_audience_heard=false "
                "P3_span=0.0..+3.0 P3_deck_audio=none "
                "P3_rule=forecast_only_not_current_live_evidence "
                "rule=part_labels_not_outcome_verdict]"
            ),
            "audio_window_context": (
                "audio_window_context[P1=master_global_mix P1_heard=true "
                "timeline=past_action_future together_audio=P1_global_mix decks_together=true "
                "deckA_audio=P2 deckB_audio=P3 per_deck_audio=deck_pair_parts "
                "duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context "
                "deck_audio_separation=deck_audio_separation_context "
                "deck_part_span=-3.0..0.0 lane_aliases=deck1:A,deck2:B "
                "pre=-6.0..-1.0 current=-1.0..0.0 action=-1.0..0.0 "
                "rule=time_alignment_not_outcome_verdict move_anchor=none "
                "future_heard=false future=not_attached]"
            ),
            "audio_window_map": {
                "p1": "master_global_mix",
                "p1_heard": True,
                "timeline": "past_action_future",
                "together_audio": "P1_global_mix",
                "decks_together": True,
                "deckA_audio": "P2",
                "deckB_audio": "P3",
                "per_deck_audio": "deck_pair_parts",
                "duplicate_audio": "separate_deck_pair_parts",
                "deck_separation": "deck_lanes_context",
                "deck_audio_separation": "deck_audio_separation_context",
                "deck_part_span_s": [-3.0, 0.0],
                "lane_aliases": "deck1:A,deck2:B",
                "pre_s": [-6.0, -1.0],
                "current_s": [-1.0, 0.0],
                "action_s": [-1.0, 0.0],
                "move_anchors": [],
                "future": {"heard": False, "span": "not_attached"},
                "rule": "time_alignment_not_outcome_verdict",
            },
        },
    )

    assert "deckA_part=P4" in p
    assert "deckB_part=P5" in p
    assert "deckA_audio=P4" in p
    assert "deckB_audio=P5" in p
    assert "deckA_audio=P2 deckB_audio=P3" not in p
    assert "audio_window_map[" not in p


def test_chat_prompt_rejects_colliding_deck_pair_audio_window_map():
    p = chat_prompt(
        "what changed on each deck?",
        live_context={
            **_fresh_live_transport(),
            "deck": "mix",
            "audible": True,
            "audio_window_context": (
                "audio_window_context[P1=master_global_mix P1_heard=true "
                "timeline=past_action_future together_audio=P1_global_mix decks_together=true "
                "deckA_audio=P2 deckB_audio=P2 per_deck_audio=deck_pair_parts "
                "duplicate_audio=separate_deck_pair_parts deck_separation=deck_lanes_context "
                "deck_audio_separation=deck_audio_separation_context "
                "lane_aliases=deck1:A,deck2:B pre=-6.0..-1.0 current=-1.0..0.0 "
                "action=-1.0..0.0 rule=time_alignment_not_outcome_verdict "
                "move_anchor=none future_heard=false future=not_attached]"
            ),
            "audio_window_map": {
                "p1": "master_global_mix",
                "p1_heard": True,
                "timeline": "past_action_future",
                "together_audio": "P1_global_mix",
                "decks_together": True,
                "deckA_audio": "P2",
                "deckB_audio": "P2",
                "per_deck_audio": "deck_pair_parts",
                "duplicate_audio": "separate_deck_pair_parts",
                "deck_separation": "deck_lanes_context",
                "deck_audio_separation": "deck_audio_separation_context",
                "lane_aliases": "deck1:A,deck2:B",
                "pre_s": [-6.0, -1.0],
                "current_s": [-1.0, 0.0],
                "action_s": [-1.0, 0.0],
                "move_anchors": [],
                "future": {"heard": False, "span": "not_attached"},
                "rule": "time_alignment_not_outcome_verdict",
            },
        },
    )

    assert "audio_window_map[" not in p
    assert "deckA_audio=P2 deckB_audio=P2" not in p


def test_chat_prompt_marks_stale_live_transport_as_partial_for_active_questions():
    p = chat_prompt(
        "was that a transition?",
        live_context={
            "deck": "B",
            "audible": False,
            "deck_state": {},
            "deck_mixer": {
                "connected": True,
                "A": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 127, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "live_evidence": {
                "mix": [
                    "transition_block=no_resolved_decks",
                    "deck_reference=deck1_A_unknown_route_muted+deck2_B_unknown_route_dominant",
                ]
            },
        },
    )

    assert "CURRENT LIVE DECK CONTEXT" in p
    assert "live_context_transport[" in p
    assert "schema=missing" in p
    assert (
        "missing=audio_delta,audio_part_context,audio_window_map,"
        "deck_audio_delta_context,deck_audio_features_context,"
        "deck_audio_separation_context,deck_audio_window_context,"
        "deck_source_status,live_evidence"
    ) in p
    assert "status=stale_or_pre_schema_v2" in p
    assert "Transport is stale_or_pre_schema_v2" in p
    assert "must be restarted/resampled before a reliable live verdict" in p


def test_chat_prompt_marks_library_request_live_context_as_silent_guard():
    p = chat_prompt(
        "find me dark rolling hypnotic techno",
        live_context={
            "deck": "mix",
            "audible": True,
            "deck_state": {},
            "deck_mixer": {"connected": True},
        },
    )

    assert "CURRENT LIVE DECK CONTEXT" in p
    assert "LIVE CONTEXT USE: silent_guard" in p
    assert "do not mention live_context" in p
    assert "resolved decks" in p
    assert "answer the requested library job with grounded tool results" in p
    assert "If no grounded library tool result is available, say that plainly" in p
    assert "never fill the turn by describing a live move" in p


def test_chat_prompt_marks_current_live_question_as_active_context():
    p = chat_prompt(
        "was that a transition?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.9}},
        },
    )

    assert "LIVE CONTEXT USE: active_live_context" in p
    assert "asking about the current live deck/move/audio moment" in p
    assert "LIVE AUDIO CONTRACT" in p
    assert "listener/vibe evidence for texture, energy" in p
    assert "not proof of track identity, deck identity, hidden sources" in p
    assert "EQ/fader/filter/cue causality" in p
    assert "the low end got hollow for a moment" in p
    assert "never credit or blame the control from audio alone" in p


def test_chat_prompt_preserves_last_known_deck_as_unverified_context_only():
    p = chat_prompt(
        "what changed on each deck?",
        live_context={
            **_fresh_live_transport(),
            "deck": "B",
            "audible": True,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "t000",
                    "camelot": "8A",
                    "bpm": 128,
                    "confidence": 0.29,
                    "source": "last_known",
                },
                "B": {
                    "title": "Signal",
                    "track_id": "t001",
                    "camelot": "9A",
                    "bpm": 130,
                    "confidence": 0.8,
                    "source": "rekordbox_xml",
                },
            },
            "deck_source_status": {
                "last_known_sides": "A",
                "last_known_rule": "context_only_not_current_identity_proof",
            },
        },
    )

    assert "A(identity=last_known_unverified" in p
    assert "src=last_known" in p
    assert "last_title='Strobe'" in p
    assert "resolved=B" in p
    assert "transition_block=single_resolved_deck" in p
    assert "last_known_rule=context_only_not_current_identity_proof" in p


def test_chat_prompt_marks_two_loaded_single_audible_as_watch_not_claim_without_moves():
    p = chat_prompt(
        "did I do a good transition?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {"title": "Left", "confidence": 0.9},
                "B": {"title": "Right", "confidence": 0.9},
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 32,
                "deck_confidence": 0.82,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
        },
    )

    assert "deck_audio_context[" in p
    assert "support=single_deck_A" in p
    assert "transition_watch=two_resolved_decks_single_audible_A" in p
    assert "multi_deck_outcome=watch_not_claim" in p


def test_chat_prompt_lets_live_evidence_block_override_candidate_route():
    p = chat_prompt(
        "did I do a good transition?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {"title": "Left", "confidence": 0.9},
                "B": {"title": "Right", "confidence": 0.9},
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 64,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 72, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "live_evidence": {
                "mix": ["transition_block=single_deck_move"],
                "refs": ["mix:transition_block=single_deck_move"],
            },
        },
    )

    assert "transition_candidate=two_resolved_decks_mixing" in p
    assert "live_evidence[" in p
    assert "mix:transition_block=single_deck_move" in p
    assert "multi_deck_outcome=blocked" in p


def test_chat_prompt_prioritizes_live_evidence_safety_refs_under_cap():
    p = chat_prompt(
        "what happened?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "track-1",
                    "camelot": "8A",
                    "confidence": 0.82,
                    "source": "rekordbox_xml",
                }
            },
            "live_evidence": {
                "mix": [
                    *(f"noise_{index}=kept" for index in range(8)),
                    "deck_lanes=A_known_route_dominant+B_unknown_route_muted",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted",
                    "transition_block=single_resolved_deck",
                ],
                "refs": [
                    *(f"mix:noise_{index}=kept" for index in range(8)),
                    "midi:A_low_cut_to_killed@42.0",
                ],
            },
        },
    )

    assert "deck_lanes=A_known_route_dominant+B_unknown_route_muted" in p
    assert "deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted" in p
    assert "transition_block=single_resolved_deck" in p
    assert "mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted" in p
    assert "mix:deck_reference=deck1_A_known_route_dominant+deck2_B_unknown_route_muted" in p
    assert "mix:transition_block=single_resolved_deck" in p
    assert "multi_deck_outcome=blocked" in p


def test_chat_prompt_includes_recent_move_context_guard():
    p = chat_prompt(
        "did I blend?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {"title": "Strobe", "confidence": 0.82},
                "B": {"title": "Ghost", "confidence": 0.82},
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 64,
                "A": {"vol": 110, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 8},
                "B": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "audio_delta": [
                "sub energy fell 50% (strong)",
                "low energy fell 50% (strong)",
            ],
            "live_evidence": {
                "mix": [
                    "deck_audio_support=single_deck_A",
                    "transition_block=single_deck_move",
                    "move_effect=sub_energy_fell_50pct_strong",
                ],
                "midi": [{"key": "A_low_cut_to_killed", "t": 42.0}],
                "refs": [
                    "midi:A_low_cut_to_killed@42.0",
                    "mix:transition_block=single_deck_move",
                ],
            },
            "recent_moves": ["A_low: cut->killed", "A_filter: open->closed"],
        },
    )

    assert "recent_moves[A_low: cut->killed | A_filter: open->closed]" in p
    assert "move_context[" in p
    assert "scope=single_deck_move_A" in p
    assert "controls=eq_kill+filter+low" in p
    assert "transition_block=single_deck_move" in p
    assert "deck_change_context[" in p
    assert "audio_window_context[" in p
    assert "move_anchor=A_low:_cut-_killed@age_unknown" in p
    assert "support=single_deck_A" in p
    assert "A_low(now=killed route=dominant)" in p
    assert "move_effect_context[" in p
    assert "sub energy fell 50% (strong)" in p
    assert "rule=move_effect_prediction_and_measurement_agree" in p
    assert "live_evidence[" in p
    assert "refs=midi:A_low_cut_to_killed@42.0,mix:transition_block=single_deck_move" in p
    assert "mix:move_scope=single_deck_move_A" in p
    assert "rule=evidence_categories_not_quality_verdict" in p
    assert "multi_deck_outcome=blocked" in p


def test_chat_prompt_recomputes_untrusted_audio_window_context():
    p = chat_prompt(
        "what happened on deck one?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.9}},
            "recent_moves": ["A_low: flat->killed"],
            "audio_window_context": (
                "audio_window_context[P1=master_global_mix "
                "deckA_audio=attached deckB_audio=stem isolated_decks=true]"
            ),
        },
    )

    assert "deckA_audio=attached" not in p
    assert "deckB_audio=stem" not in p
    assert "isolated_decks=true" not in p
    assert "audio_window_context[" in p
    assert "deckA_audio=not_attached" in p
    assert "deckB_audio=not_attached" in p
    assert "duplicate_audio=same_master_not_deck_split" in p
    assert "lane_aliases=deck1:A,deck2:B" in p


def test_chat_prompt_marks_crossfader_mix_as_watch_not_claim_when_single_audible():
    p = chat_prompt(
        "was that a transition?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {"title": "Left", "confidence": 0.9},
                "B": {"title": "Right", "confidence": 0.9},
            },
            "recent_moves": ["xfader->center"],
        },
    )

    assert "move_context[" in p
    assert "scope=cross_deck_move" in p
    assert "transition_watch=two_deck_move_single_audible" in p
    assert "multi_deck_outcome=watch_not_claim" in p
    assert "transition_candidate=two_deck_move_audible_mix" not in p


def test_chat_prompt_sanitizes_live_context_and_keeps_master_music_scalar():
    p = chat_prompt(
        "what is loaded?",
        live_context={
            "deck": "B",
            "music": 0.9,
            "mic": 0.7,
            "recording_path": "/Users/ozai/private/take.wav",
            "deck_state": {
                "A": {
                    "title": "Left",
                    "source": "/Users/ozai/private/injected",
                    "filepath": "/Users/ozai/private/left.mp3",
                    "confidence": 0.9,
                },
                "Z": {"title": "Injected", "confidence": 1.0},
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 200,
                "deck_confidence": 2.0,
                "A": {"vol": 999, "eq_low": -10, "play": True, "secret": "drop me"},
                "Z": {"vol": 127},
            },
            "live_evidence": {
                "mix": ["transition_block=single_resolved_deck", "/Users/ozai/private/take.wav"],
                "midi": [
                    {"key": "A_low_cut_to_killed", "t": 7.25},
                    {"key": "bad key with spaces / path", "t": 8.0},
                ],
                "refs": ["mix:transition_block=single_resolved_deck", "bad ref with spaces"],
            },
        },
    )

    assert "Left" in p
    assert "mixer_context[" in p
    assert "xfader=full-B" in p
    assert "A(vol=full low=killed" in p
    assert "Injected" not in p
    assert "recording_path" not in p
    assert "/Users/ozai/private" not in p
    assert "injected" not in p
    assert "music=0.900" in p
    assert "mic=0.7" not in p
    assert "secret" not in p
    assert "live_evidence[" in p
    assert "mix:transition_block=single_resolved_deck" in p
    assert "A_low_cut_to_killed@7.2" in p
    assert "bad key" not in p
    assert "bad_ref" not in p


def test_chat_prompt_omits_low_confidence_live_genre():
    p = chat_prompt(
        "what style is this?",
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "audible": True,
            "phase": "groove",
            "bpm": 146.0,
            "detected_genre": "psytrance",
            "genre_confidence": 0.42,
            "deck_state": {},
            "deck_mixer": {},
        },
    )

    assert "CURRENT LIVE DECK CONTEXT" in p
    assert "genre=psytrance" not in p
    assert "genre=unknown" not in p


def test_chat_prompt_preserves_explicit_empty_live_deck_clear():
    p = chat_prompt(
        "what is loaded now?",
        live_context={
            **_fresh_live_transport(),
            "deck": "none",
            "audible": False,
            "deck_state": {},
            "deck_mixer": {},
        },
    )

    assert "CURRENT LIVE DECK CONTEXT" in p
    assert "live_context[deck=none audible=false resolved=none" in p
    assert "context_feed_contract[" in p
    assert "surface=viber_text" in p
    assert "history=past_comparison_not_live_proof" in p
    assert "cache=static_persona_rules_only" in p
    assert "per_turn=small_text_live_context" in p
    assert "speed=no_extra_model_pass" in p
    assert "transition_block=no_resolved_decks" in p
    assert "audio_window_context[" in p
    assert "P1=master_global_mix" in p
    assert "deckA_audio=not_attached" in p
    assert "deckB_audio=not_attached" in p
    assert "lane_aliases=deck1:A,deck2:B" in p
    assert "decks[" not in p
    assert "multi_deck_outcome=blocked" in p


def test_chat_with_codex_corrects_outcome_after_empty_live_deck_clear(library):
    runner = _runner_writing(
        {
            "reply": "Great transition.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "none",
            "audible": False,
            "deck_state": {},
            "deck_mixer": {},
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert "resolved decks=none" not in res.reply
    assert "won't call that a transition" not in res.reply


def test_chat_with_codex_blocks_stale_transport_outcome_claim(library):
    runner = _runner_writing(
        {
            "reply": "Great transition, that blend was clean.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {"title": "Left", "confidence": 0.9},
                "B": {"title": "Right", "confidence": 0.9},
            },
            "recent_moves": ["xfader->center"],
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" not in res.reply
    assert "blend was clean" not in res.reply
    assert "Refresh the live session first" in res.reply
    assert "stale_or_pre_schema_v2" not in res.reply
    assert "schema-v2 deck/source/audio lanes" not in res.reply


def test_codex_chat_result_to_dict_matches_chat_shape():
    out = CodexChatResult(
        reply="try t000 next",
        tools_used=["search_vibe"],
        track_ids=["t000"],
    ).to_dict()

    assert out == {
        "reply": "try t000 next",
        "tool_trace": [{"name": "search_vibe", "arg": "", "ok": True}],
        "playlist": None,
        "export_path": None,
        "seen_track_ids": ["t000"],
        "move_grades": [],
        "iterations": 1,
        "stop_reason": "model_done",
    }


def test_codex_chat_result_to_dict_surfaces_live_verification():
    verification = {
        "ok": True,
        "violations": [],
        "reply": (
            "I caught the live move. The useful note is the sound change right there."
        ),
        "corrected": False,
        "corrected_reply": None,
        "claim_policy": "blocked",
        "transport_status": "fresh_schema_v2",
        "move_grades_allowed": False,
        "move_grades_seen": 0,
        "guard_applied": True,
        "guard_violations": ["unsupported_live_outcome_claim"],
    }
    out = CodexChatResult(
        reply=(
            "I caught the live move. The useful note is the sound change right there."
        ),
        live_verification=verification,
    ).to_dict()

    assert out["live_verification"] == verification


def test_codex_chat_result_to_dict_prefers_rich_tool_trace():
    out = CodexChatResult(
        reply="saved",
        tools_used=["search_vibe", "create_playlist"],
        tool_trace=[
            {"name": "search_vibe", "arg": "dark peak techno", "ok": True},
            {"name": "create_playlist", "arg": "Dark Fuse", "ok": True},
        ],
    ).to_dict()

    assert out["tool_trace"] == [
        {"name": "search_vibe", "arg": "dark peak techno", "ok": True},
        {"name": "create_playlist", "arg": "Dark Fuse", "ok": True},
    ]
    assert out["iterations"] == 2


def test_codex_chat_result_to_dict_surfaces_move_grade_receipts():
    grade = {
        "candidate_id": "tr_001",
        "track_id": "t000",
        "title": "Tt000",
        "slug": "lit_aff",
        "label": "LIT AFF",
        "xp": 100,
        "reason": "everything clicks",
        "overdrive": True,
        "streak": 4,
        "total_xp": 288,
        "level": 2,
        "level_xp": 38,
        "next_level_xp": 250,
        "level_up": True,
        "levels_gained": 1,
    }
    out = CodexChatResult(
        reply="this one is lit",
        tools_used=["transition_slate"],
        track_ids=["t000"],
        move_grades=[grade],
    ).to_dict()

    assert out["move_grades"] == [grade]


def test_codex_chat_result_to_dict_surfaces_terminal_artifacts(tmp_path):
    playlist = {
        "name": "Dark Fuse",
        "track_ids": ["t000", "t001"],
        "m3u_path": str(tmp_path / "dark-fuse.m3u8"),
        "json_path": str(tmp_path / "dark-fuse.json"),
        "dropped_ids": [],
    }

    out = CodexChatResult(
        reply="saved it",
        tools_used=["search_vibe", "create_playlist"],
        track_ids=["t000", "t001"],
        playlist=playlist,
        stop_reason="created",
    ).to_dict()

    assert out["playlist"] == playlist
    assert out["iterations"] == 2
    assert out["stop_reason"] == "created"


def test_chat_with_codex_not_installed(library, tmp_path):
    res = chat_with_codex(
        "hello",
        library,
        codex_path=str(tmp_path / "missing-codex"),
    )

    assert res.stop_reason == "codex_not_installed"
    assert "Codex CLI not found" in (res.error or "")


def test_chat_with_codex_live_question_without_context_fails_closed(library, tmp_path):
    def runner(*_args, **_kw):
        raise AssertionError("live context guard should not call Codex")

    res = chat_with_codex(
        "was that transition good?",
        library,
        codex_path=str(tmp_path / "missing-codex"),
        _runner=runner,
    )

    assert (
        res.reply == "Start live monitoring first, then I'll read the live move from the decks."
    )
    assert res.stop_reason == "live_context_required"
    assert res.tool_trace == [
        {"name": "live_context_required", "arg": "waiting for live deck feed", "ok": False}
    ]
    assert res.live_verification is not None
    assert res.live_verification["ok"] is True
    assert res.live_verification["transport_status"] == "missing_live_context"
    assert res.live_verification["claim_policy"] == "requires_more_evidence"
    assert res.live_verification["move_grades_allowed"] is False
    assert res.live_verification["guard_applied"] is False


def test_chat_with_codex_passes_live_context_into_codex_prompt(library):
    captured: dict[str, str] = {}

    def runner(argv, **kw):
        captured["prompt"] = argv[-1]
        Path(_out_path_from_argv(argv)).write_text(
            json.dumps(
                {
                    "reply": "That is one deck, not a transition.",
                    "tools_used": [],
                    "tool_trace": [],
                    "track_ids": [],
                    "playlist": None,
                    "export_path": None,
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    res = chat_with_codex(
        "did I blend?",
        library,
        live_context={
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.8}},
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "model_done"
    assert "CURRENT LIVE DECK CONTEXT" in captured["prompt"]
    assert "transition_block=single_resolved_deck" in captured["prompt"]


def test_chat_with_codex_adds_historical_move_context_from_memory(library, tmp_path, monkeypatch):
    import vibemix.library.codex_curate as codex_mod

    memory_db = tmp_path / "memory.db"
    _write_memory_db(
        memory_db,
        [
            (
                "coach_line | track=Strobe | phase=groove | deck=A | event=MIX_MOVE "
                "| move=move_context[scope=single_deck_move_A] "
                "| audio_window=audio_window_context[P1=master_global_mix "
                "move_anchor=A_low:_flat-_killed@age_unknown deckA_audio=not_attached] "
                "| move_effect=move_effect_context[rule=dsp_delta_not_causal_proof] "
                "| audio_delta=low energy fell 50% (strong) "
                "| said: heard the low cut thin out"
            ),
            "coach_line | track=Other | phase=build | deck=B | event=PHASE | said: not a move",
        ],
    )
    monkeypatch.setattr(codex_mod, "_memory_db_candidates", lambda: [memory_db])
    captured: dict[str, str] = {}

    def runner(argv, **kw):
        captured["prompt"] = argv[-1]
        Path(_out_path_from_argv(argv)).write_text(
            json.dumps(
                {
                    "reply": "I see the low cut evidence, not a transition.",
                    "tools_used": [],
                    "tool_trace": [],
                    "track_ids": [],
                    "playlist": None,
                    "export_path": None,
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    res = codex_mod.chat_with_codex(
        "what did that low cut do?",
        library,
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.9}},
            "recent_moves": ["A_low: flat->killed"],
            "audio_delta": ["low energy fell 50% (strong)"],
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "model_done"
    assert "HISTORICAL MOVE CONTEXT" in captured["prompt"]
    assert "history_move[id=20260520-220000:0" in captured["prompt"]
    assert "low energy fell 50% (strong)" in captured["prompt"]
    assert "audio_window_context[P1=master_global_mix" in captured["prompt"]
    assert "not live proof" in captured["prompt"]
    assert "cannot upgrade the current live claim policy" in captured["prompt"]


def test_chat_prompt_prefers_historical_move_with_same_deck_lane_context(tmp_path, monkeypatch):
    import vibemix.library.codex_curate as codex_mod

    memory_db = tmp_path / "memory.db"
    _write_memory_db(
        memory_db,
        [
            (
                "coach_line | track=Strobe | phase=groove | deck=A | event=MIX_MOVE "
                "| live_evidence=live_evidence[mix=deck_lanes=A_known_route_dominant+B_unknown_route_muted] "
                "| audio_window=audio_window_context[P1=master_global_mix "
                "move_anchor=A_low:_flat-_killed@age_unknown deckA_audio=not_attached] "
                "| move=move_context[scope=single_deck_move_A] "
                "| move_effect=move_effect_context[rule=dsp_delta_not_causal_proof] "
                "| audio_delta=low energy fell 50% (strong) | said: same lane posture"
            ),
            (
                "coach_line | track=Strobe | phase=groove | deck=A | event=MIX_MOVE "
                "| live_evidence=live_evidence[mix=deck_lanes=A_known_route_muted+B_unknown_route_dominant] "
                "| audio_window=audio_window_context[P1=master_global_mix "
                "move_anchor=A_low:_flat-_killed@-9.0s:before_P1 deckA_audio=not_attached] "
                "| move=move_context[scope=single_deck_move_A] "
                "| move_effect=move_effect_context[rule=dsp_delta_not_causal_proof] "
                "| audio_delta=low energy fell 50% (strong) | said: different lane posture"
            ),
        ],
    )
    monkeypatch.setattr(codex_mod, "_memory_db_candidates", lambda: [memory_db])

    prompt = codex_mod.chat_prompt(
        "what did that low cut do?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.9}},
            "deck_mixer": {
                "connected": True,
                "xfader": 32,
                "A": {"vol": 110, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "recent_moves": ["A_low: flat->killed"],
            "audio_delta": ["low energy fell 50% (strong)"],
            "live_evidence": {
                "mix": ["deck_lanes=A_known_route_dominant+B_unknown_route_muted"],
                "refs": ["mix:deck_lanes=A_known_route_dominant+B_unknown_route_muted"],
            },
        },
    )

    assert "HISTORICAL MOVE CONTEXT" in prompt
    assert prompt.index("history_move[id=20260520-220000:0") < prompt.index(
        "history_move[id=20260520-220000:1"
    )


def test_chat_prompt_prefers_historical_move_with_same_deck_source_context(tmp_path, monkeypatch):
    import vibemix.library.codex_curate as codex_mod

    memory_db = tmp_path / "memory.db"
    _write_memory_db(
        memory_db,
        [
            (
                "coach_line | track=Strobe | phase=groove | deck=A | event=MIX_MOVE "
                "| deck_source=deck_source_context[identity_state=MusicState.deck_state "
                "resolved=A unresolved=B sources=folder_cache "
                "second_deck=independent_source_required "
                "rule=unresolved_deck_is_not_transition_evidence] "
                "| audio_delta=low energy fell 50% (strong) | said: same source ladder"
            ),
            (
                "coach_line | track=Strobe | phase=groove | deck=A | event=MIX_MOVE "
                "| deck_source=deck_source_context[identity_state=MusicState.deck_state "
                "resolved=A unresolved=B sources=screen_vision "
                "second_deck=independent_source_required "
                "rule=unresolved_deck_is_not_transition_evidence] "
                "| audio_delta=low energy fell 50% (strong) | said: different source ladder"
            ),
        ],
    )
    monkeypatch.setattr(codex_mod, "_memory_db_candidates", lambda: [memory_db])

    prompt = codex_mod.chat_prompt(
        "what did that low cut do?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {
                    "title": "Strobe",
                    "track_id": "track-1",
                    "confidence": 0.9,
                    "source": "folder_cache",
                }
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 32,
                "A": {"vol": 110, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "recent_moves": ["A_low: flat->killed"],
            "audio_delta": ["low energy fell 50% (strong)"],
        },
    )

    assert "HISTORICAL MOVE CONTEXT" in prompt
    assert prompt.index("history_move[id=20260520-220000:0") < prompt.index(
        "history_move[id=20260520-220000:1"
    )


def test_chat_prompt_sanitizes_historical_move_memory_stem_and_outcome_claims(
    tmp_path,
    monkeypatch,
):
    import vibemix.library.codex_curate as codex_mod

    memory_db = tmp_path / "memory.db"
    _write_memory_db(
        memory_db,
        [
            (
                "coach_line | event=MIX_MOVE "
                "| audio_window=audio_window_context[P1=master_global_mix "
                "deckA_audio=attached deckB_audio=stem isolated_decks=true] "
                "| audio_delta=low energy fell 50% (strong) "
                "| said: That was a great transition."
            )
        ],
    )
    monkeypatch.setattr(codex_mod, "_memory_db_candidates", lambda: [memory_db])

    prompt = codex_mod.chat_prompt(
        "what did that low cut do?",
        live_context={
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.9}},
            "recent_moves": ["A_low: flat->killed"],
            "audio_delta": ["low energy fell 50% (strong)"],
        },
    )

    assert "HISTORICAL MOVE CONTEXT" in prompt
    assert "deckA_audio=attached" not in prompt
    assert "deckB_audio=stem" not in prompt
    assert "isolated_decks=true" not in prompt
    assert "great transition" not in prompt.lower()
    assert "audio_window=omitted_untrusted_audio_window" in prompt
    assert "said: omitted_past_live_outcome_claim" in prompt
    assert "cannot upgrade the current live claim policy" in prompt


def test_chat_prompt_skips_historical_move_context_without_audio_delta(tmp_path, monkeypatch):
    import vibemix.library.codex_curate as codex_mod

    memory_db = tmp_path / "memory.db"
    _write_memory_db(
        memory_db,
        [
            (
                "coach_line | track=Strobe | phase=groove | deck=A | event=MIX_MOVE "
                "| audio_delta=low energy fell 50% (strong) | said: low cut"
            )
        ],
    )
    monkeypatch.setattr(codex_mod, "_memory_db_candidates", lambda: [memory_db])

    prompt = codex_mod.chat_prompt(
        "what happened?",
        live_context={
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.9}},
            "recent_moves": ["A_low: flat->killed"],
        },
    )

    assert "CURRENT LIVE DECK CONTEXT" in prompt
    assert "HISTORICAL MOVE CONTEXT" not in prompt


def test_chat_with_codex_corrects_unsupported_multi_deck_outcome_claim(library):
    runner = _runner_writing(
        {
            "reply": "Great transition, that blend was clean.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.8}},
            "recent_moves": ["A_low: cut->killed"],
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert "I need to correct that live read" not in res.reply
    assert "resolved decks=A" not in res.reply
    assert "deck lanes=A=known" not in res.reply
    assert "second_deck=independent_source_required" not in res.reply
    assert "rule=unresolved_deck_is_not_transition_evidence" not in res.reply
    assert "won't call that a transition" not in res.reply
    assert res.live_verification is not None
    assert res.live_verification["ok"] is True
    assert res.live_verification["transport_status"] == "fresh_schema_v2"
    assert res.live_verification["claim_policy"] == "blocked"
    assert res.live_verification["guard_applied"] is True
    assert "unsupported_live_outcome_claim" in res.live_verification["guard_violations"]
    assert res.to_dict()["live_verification"]["ok"] is True


def test_chat_with_codex_suppresses_live_correction_for_library_request(library):
    runner = _runner_writing(
        {
            "reply": (
                "I need to correct the live read: I only have audible deck mix; "
                "resolved decks=none; live evidence gate: transition_block=no_resolved_decks, "
                "so I won't call that a transition."
            ),
            "tools_used": ["discover_pool", "search_vibe", "sequence_set"],
            "tool_trace": [
                {"name": "discover_pool", "arg": "dark rolling hypnotic techno", "ok": True},
                {"name": "search_vibe", "arg": "dark rolling hypnotic techno", "ok": True},
                {"name": "sequence_set", "arg": "peak_time", "ok": True},
            ],
            "track_ids": ["t000", "t001"],
            "move_grades": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "find me dark rolling hypnotic techno",
        library,
        live_context={
            "deck": "mix",
            "audible": True,
            "deck_state": {},
            "deck_mixer": {"connected": True},
            "live_evidence": {
                "mix": ["transition_block=no_resolved_decks"],
                "refs": ["mix:transition_block=no_resolved_decks"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "correct the live read" not in res.reply
    assert "resolved decks" not in res.reply
    assert "won't call that a transition" not in res.reply
    assert res.reply == "Found 2 grounded library candidates for that vibe."
    assert res.track_ids == ["t000", "t001"]
    assert res.tools_used == ["discover_pool", "search_vibe", "sequence_set"]


def test_chat_with_codex_suppresses_plain_live_leak_for_library_request(library):
    runner = _runner_writing(
        {
            "reply": "I caught the live move. The useful note is the sound change right there.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "find me dark rolling hypnotic techno",
        library,
        live_context={
            "deck": "mix",
            "audible": True,
            "deck_state": {},
            "deck_mixer": {"connected": True},
            "live_evidence": {
                "mix": ["transition_block=no_resolved_decks"],
                "refs": ["mix:transition_block=no_resolved_decks"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "live move" not in res.reply
    assert "sound change" not in res.reply
    assert res.reply == "I kept that as a library request, but I do not have grounded results to show yet."
    assert res.live_verification is not None
    assert res.live_verification["ok"] is True
    assert res.live_verification["guard_applied"] is True
    assert "library_request_live_leak" in res.live_verification["guard_violations"]


def test_chat_with_codex_uses_shared_guard_for_transition_synonyms(library):
    runner = _runner_writing(
        {
            "reply": "Nice switch; the incoming track came in clean.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "deck_state": {
                "A": {"title": "Left", "confidence": 0.9},
                "B": {"title": "Right", "confidence": 0.9},
            },
            "recent_moves": ["xfader->A-side"],
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Nice switch" not in res.reply
    assert "incoming track came in clean" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert "recent control evidence: xfader->A-side" not in res.reply


def test_chat_with_codex_corrects_candidate_quality_verdict(library):
    runner = _runner_writing(
        {
            "reply": "That was a great transition.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {"title": "Left", "confidence": 0.9},
                "B": {"title": "Right", "confidence": 0.9},
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 64,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 72, "eq_low": 8, "eq_mid": 64, "eq_hi": 64, "filter": 92},
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "great transition" not in res.reply.lower()
    assert "transition candidate" in res.reply
    assert "clear two-deck proof" in res.reply


def test_chat_with_codex_live_evidence_block_overrides_candidate_correction(library):
    runner = _runner_writing(
        {
            "reply": "That was a great transition.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "audible": True,
            "deck_state": {
                "A": {"title": "Left", "confidence": 0.9},
                "B": {"title": "Right", "confidence": 0.9},
            },
            "deck_mixer": {
                "connected": True,
                "xfader": 64,
                "A": {"vol": 110, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 72, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "live_evidence": {
                "mix": ["transition_block=single_deck_move"],
                "refs": ["mix:transition_block=single_deck_move"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "great transition" not in res.reply.lower()
    assert "transition or blend candidate" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert "live evidence gate: transition_block=single_deck_move" not in res.reply


def test_chat_with_codex_live_evidence_candidate_blocks_quality_grade(library):
    runner = _runner_writing(
        {
            "reply": "Great transition, clean handoff.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [
                {
                    "candidate_id": "tr_001",
                    "track_id": "t000",
                    "title": "Tt000",
                    "slug": "lit_aff",
                    "label": "LIT AFF",
                    "xp": 100,
                    "reason": "not enough live proof",
                    "overdrive": True,
                }
            ],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "live_evidence": {
                "mix": ["transition_candidate=two_deck_move_audible_mix"],
                "refs": ["mix:transition_candidate=two_deck_move_audible_mix"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" not in res.reply
    assert "transition candidate" in res.reply
    assert "clear two-deck proof" in res.reply
    assert "live evidence gate: transition_candidate=two_deck_move_audible_mix" not in res.reply
    assert res.move_grades == []
    assert res.track_ids == []


def test_chat_with_codex_allows_quality_grade_with_strong_deck_pair_proof(library):
    runner = _runner_writing(
        {
            "reply": "Great transition, clean handoff.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [
                {
                    "candidate_id": "tr_001",
                    "track_id": "t000",
                    "title": "Tt000",
                    "slug": "lit_aff",
                    "label": "LIT AFF",
                    "xp": 100,
                    "reason": "both decks are locked",
                    "overdrive": True,
                }
            ],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "mix",
            "audible": True,
            "deck_state": {
                "A": {
                    "title": "Left",
                    "track_id": "t000",
                    "confidence": 0.9,
                    "source": "rekordbox_xml",
                },
                "B": {
                    "title": "Right",
                    "track_id": "t001",
                    "confidence": 0.88,
                    "source": "rekordbox_xml",
                },
            },
            "recent_moves": ["xfader->center"],
            "audio_delta": ["sub energy rose 20% (slight)"],
            "deck_audio_separation_context": _deck_pair_audio_separation_context(),
            "deck_audio_features_context": _deck_audio_features_context(),
            "deck_audio_delta_context": _deck_audio_delta_context(),
            "deck_audio_window_context": _deck_audio_window_context(),
            "audio_part_context": _deck_pair_audio_part_context(),
            "audio_window_context": _deck_pair_audio_window_context(),
            "audio_window_map": _deck_pair_audio_window_map(),
            "live_evidence": {
                "mix": [
                    "transition_candidate=two_deck_move_audible_mix",
                    "deck_lanes=A_known_route_dominant+B_known_route_present",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_known_src_rekordbox_xml",
                    "deck_audio_capture=A_active+B_active",
                    "deck_audio_features=A_active_rms_0.024+B_active_rms_0.031",
                    "deck_audio_delta=A_rms_rose_60pct_strong+B_rms_fell_20pct_slight",
                    _deck_audio_window_evidence(),
                ],
                "refs": [
                    "mix:transition_candidate=two_deck_move_audible_mix",
                    "mix:deck_audio_capture=A_active+B_active",
                    "mix:deck_audio_features=A_active_rms_0.024+B_active_rms_0.031",
                    "mix:deck_audio_delta=A_rms_rose_60pct_strong+B_rms_fell_20pct_slight",
                    "mix:" + _deck_audio_window_evidence(),
                ],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" in res.reply
    assert "clean handoff" in res.reply
    assert len(res.move_grades) == 1
    assert res.live_verification is not None
    assert res.live_verification["claim_policy"] == "supported_verdict"


def test_chat_with_codex_requires_consistent_audio_parts_for_quality_grade(library):
    runner = _runner_writing(
        {
            "reply": "Great transition, clean handoff.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [
                {
                    "candidate_id": "tr_001",
                    "track_id": "t000",
                    "title": "Tt000",
                    "slug": "lit_aff",
                    "label": "LIT AFF",
                    "xp": 100,
                    "reason": "mismatched parts should not score",
                    "overdrive": True,
                }
            ],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "mix",
            "audible": True,
            "deck_state": {
                "A": {
                    "title": "Left",
                    "track_id": "t000",
                    "confidence": 0.9,
                    "source": "rekordbox_xml",
                },
                "B": {
                    "title": "Right",
                    "track_id": "t001",
                    "confidence": 0.88,
                    "source": "rekordbox_xml",
                },
            },
            "recent_moves": ["xfader->center"],
            "audio_delta": ["sub energy rose 20% (slight)"],
            "deck_audio_separation_context": _deck_pair_audio_separation_context(),
            "deck_audio_features_context": _deck_audio_features_context(),
            "deck_audio_delta_context": _deck_audio_delta_context(),
            "deck_audio_window_context": _deck_audio_window_context(),
            "audio_part_context": _deck_pair_audio_part_context("P4", "P5"),
            "audio_window_context": _deck_pair_audio_window_context("P2", "P3"),
            "audio_window_map": _deck_pair_audio_window_map("P2", "P3"),
            "live_evidence": {
                "mix": [
                    "transition_candidate=two_deck_move_audible_mix",
                    "deck_lanes=A_known_route_dominant+B_known_route_present",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_known_src_rekordbox_xml",
                    "deck_audio_capture=A_active+B_active",
                    "deck_audio_features=A_active_rms_0.024+B_active_rms_0.031",
                    "deck_audio_delta=A_rms_rose_60pct_strong+B_rms_fell_20pct_slight",
                    _deck_audio_window_evidence(),
                ],
                "refs": [
                    "mix:transition_candidate=two_deck_move_audible_mix",
                    "mix:deck_audio_capture=A_active+B_active",
                    "mix:deck_audio_features=A_active_rms_0.024+B_active_rms_0.031",
                    "mix:deck_audio_delta=A_rms_rose_60pct_strong+B_rms_fell_20pct_slight",
                    "mix:" + _deck_audio_window_evidence(),
                ],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" not in res.reply
    assert "transition candidate" in res.reply
    assert res.move_grades == []
    assert res.live_verification is not None
    assert res.live_verification["claim_policy"] == "candidate_not_verdict"
    assert res.live_verification["guard_applied"] is True


def test_chat_with_codex_requires_trusted_sources_for_quality_grade(library):
    runner = _runner_writing(
        {
            "reply": "Great transition, clean handoff.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "move_grades": [
                {
                    "candidate_id": "tr_001",
                    "track_id": "t000",
                    "title": "Tt000",
                    "slug": "lit_aff",
                    "label": "LIT AFF",
                    "xp": 100,
                    "reason": "untrusted source should not score",
                    "overdrive": True,
                }
            ],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "mix",
            "audible": True,
            "deck_state": {
                "A": {
                    "title": "Left",
                    "track_id": "t000",
                    "confidence": 0.9,
                    "source": "rekordbox_xml",
                },
                "B": {
                    "title": "Right",
                    "track_id": "t001",
                    "confidence": 0.88,
                    "source": "beatport_scrape",
                },
            },
            "recent_moves": ["xfader->center"],
            "audio_delta": ["sub energy rose 20% (slight)"],
            "live_evidence": {
                "mix": [
                    "transition_candidate=two_deck_move_audible_mix",
                    "deck_lanes=A_known_route_dominant+B_known_route_present",
                    "deck_reference=deck1_A_known_route_dominant+deck2_B_known_route_present",
                    "deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_known_src_beatport_scrape",
                    "deck_audio_capture=A_active+B_active",
                    "deck_audio_features=A_active_rms_0.024+B_active_rms_0.031",
                    "deck_audio_delta=A_rms_rose_60pct_strong+B_rms_fell_20pct_slight",
                    _deck_audio_window_evidence(),
                ],
                "refs": [
                    "mix:transition_candidate=two_deck_move_audible_mix",
                    "mix:deck_audio_capture=A_active+B_active",
                    "mix:deck_audio_features=A_active_rms_0.024+B_active_rms_0.031",
                    "mix:deck_audio_delta=A_rms_rose_60pct_strong+B_rms_fell_20pct_slight",
                    "mix:" + _deck_audio_window_evidence(),
                ],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" not in res.reply
    assert "transition candidate" in res.reply
    assert res.move_grades == []
    assert res.live_verification is not None
    assert res.live_verification["claim_policy"] == "candidate_not_verdict"


def test_chat_with_codex_drops_move_grade_when_live_policy_blocks_current_claim(library):
    runner = _runner_writing(
        {
            "reply": "Great transition, that bridge was clean.",
            "tools_used": ["transition_slate", "compile_musical_context"],
            "tool_trace": [
                {"name": "transition_slate", "arg": "current live move", "ok": True},
                {"name": "compile_musical_context", "arg": "tr_001", "ok": True},
            ],
            "track_ids": [],
            "move_grades": [
                {
                    "candidate_id": "tr_001",
                    "track_id": "t000",
                    "title": "Tt000",
                    "slug": "lit_aff",
                    "label": "LIT AFF",
                    "xp": 100,
                    "reason": "everything clicks",
                    "overdrive": True,
                }
            ],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.8}},
            "recent_moves": ["A_low: cut->killed"],
            "live_evidence": {
                "mix": ["transition_block=single_resolved_deck"],
                "refs": ["mix:transition_block=single_resolved_deck"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert res.move_grades == []
    assert res.track_ids == []


def test_chat_with_codex_licenses_grounded_move_effect_causal_verdict(library):
    runner = _runner_writing(
        {
            "reply": "Your low cut cleaned the mix.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "did that low cut fix it?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Left", "confidence": 0.9}},
            "deck_mixer": {
                "connected": True,
                "xfader": 32,
                "A": {"vol": 110, "eq_low": 2, "eq_mid": 64, "eq_hi": 64, "filter": 64},
                "B": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, "filter": 64},
            },
            "audio_delta": ["sub energy fell 50% (strong)", "low energy fell 50% (strong)"],
            "recent_moves": ["A_low: flat->killed"],
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.reply == "Your low cut cleaned the mix."
    assert res.live_verification["ok"] is True
    assert res.live_verification["guard_violations"] == []
    assert "sub energy fell 50% (strong)" not in res.reply


def test_verify_live_reply_rejects_eq_audio_song_detail_verdict() -> None:
    verdict = verify_live_reply_for_viber(
        "That EQ move made the vocal open up and the kick got tighter.",
        {
            **_fresh_live_transport(),
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Left", "confidence": 0.9}},
            "audio_delta": ["low energy fell 50% (strong)"],
            "recent_moves": ["A_low: flat->killed"],
        },
    )

    assert verdict["ok"] is False
    assert "unsupported_audio_source_detail_claim" in verdict["violations"]
    assert "vocal" not in str(verdict["corrected_reply"]).lower()
    assert "kick" not in str(verdict["corrected_reply"]).lower()


def test_verify_live_reply_rejects_audio_source_detail_without_control_claim() -> None:
    verdict = verify_live_reply_for_viber(
        "The vocal opened up and the kick got tighter.",
        {
            **_fresh_live_transport(),
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Left", "confidence": 0.9}},
            "audio_delta": ["low energy fell 50% (strong)"],
            "recent_moves": ["A_low: flat->killed"],
        },
    )

    assert verdict["ok"] is False
    assert "unsupported_audio_source_detail_claim" in verdict["violations"]
    assert "vocal" not in str(verdict["corrected_reply"]).lower()
    assert "kick" not in str(verdict["corrected_reply"]).lower()
    assert "source-level proof" in str(verdict["corrected_reply"])


def test_verify_live_reply_allows_broad_audio_listener_read() -> None:
    verdict = verify_live_reply_for_viber(
        "The low end got hollow for a moment.",
        {
            **_fresh_live_transport(),
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Left", "confidence": 0.9}},
            "audio_delta": ["low energy fell 50% (strong)"],
            "recent_moves": ["A_low: flat->killed"],
        },
    )

    assert verdict["ok"] is True
    assert verdict["violations"] == []
    assert verdict["corrected"] is False
    assert verdict["transport_status"] == "fresh_schema_v2"


def test_chat_with_codex_blocks_audio_source_detail_without_control_claim(library):
    runner = _runner_writing(
        {
            "reply": "The vocal opened up and the kick got tighter.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "did that low cut fix it?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "audible": True,
            "deck_state": {"A": {"title": "Left", "confidence": 0.9}},
            "audio_delta": ["low energy fell 50% (strong)"],
            "recent_moves": ["A_low: flat->killed"],
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "vocal" not in res.reply.lower()
    assert "kick" not in res.reply.lower()
    assert "source-level proof" in res.reply
    assert res.live_verification["guard_applied"] is True
    assert "unsupported_audio_source_detail_claim" in res.live_verification["guard_violations"]


def test_chat_with_codex_normalizes_self_corrected_transition_disclaimer(library):
    runner = _runner_writing(
        {
            "reply": "I saw a deck A low move, but I can't call it a transition.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.8}},
            "recent_moves": ["A_low: cut->killed"],
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "I saw a deck A low move" not in res.reply
    assert res.reply == "I can't call that a transition until I have clear two-deck proof."


def test_chat_with_codex_normalizes_public_live_diagnostics_without_transition_claim(library):
    runner = _runner_writing(
        {
            "reply": (
                "I need to correct the live read: resolved decks=none; "
                "live evidence gate: transition_block=no_resolved_decks; "
                "claim_policy=blocked."
            ),
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "what happened?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "none",
            "deck_state": {},
            "live_evidence": {
                "mix": ["transition_block=no_resolved_decks"],
                "refs": ["mix:transition_block=no_resolved_decks"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "correct the live read" not in res.reply
    assert "resolved decks" not in res.reply
    assert "live evidence gate" not in res.reply
    assert "claim_policy" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert res.live_verification is not None
    assert res.live_verification["guard_applied"] is True
    assert "unsupported_live_outcome_claim" in res.live_verification["guard_violations"]


def test_chat_with_codex_normalizes_public_live_self_confession(library):
    runner = _runner_writing(
        {
            "reply": (
                "My mistake on the live read. I'm not sure what happened from this live read yet."
            ),
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "what happened there?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.8}},
            "recent_moves": ["A_low: cut->killed"],
            "live_evidence": {
                "mix": ["transition_block=single_resolved_deck"],
                "refs": ["mix:transition_block=single_resolved_deck"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "mistake" not in res.reply
    assert "not sure" not in res.reply
    assert "live move" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert res.live_verification is not None
    assert res.live_verification["ok"] is True
    assert res.live_verification["guard_applied"] is True
    assert "unsupported_live_outcome_claim" in res.live_verification["guard_violations"]


@pytest.mark.parametrize(
    "bad_reply",
    [
        "My bad on the live read. I was wrong about the live moment.",
        "I messed up on the live read and gave you a bad live read.",
        "I shouldn't have called that a transition. That was dumb from the live read.",
        "I overclaimed from the live proof and got this wrong in the live read.",
        "I'm doing something stupid about the live read.",
    ],
)
def test_chat_with_codex_normalizes_public_live_self_diagnosis_variants(library, bad_reply):
    runner = _runner_writing(
        {
            "reply": bad_reply,
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "what happened there?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.8}},
            "recent_moves": ["A_low: cut->killed"],
            "live_evidence": {
                "mix": ["transition_block=single_resolved_deck"],
                "refs": ["mix:transition_block=single_resolved_deck"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    lower = res.reply.lower()
    assert "my bad" not in lower
    assert "wrong" not in lower
    assert "messed up" not in lower
    assert "shouldn't have" not in lower
    assert "dumb" not in lower
    assert "stupid" not in lower
    assert "overclaimed" not in lower
    assert "live move" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert res.live_verification is not None
    assert res.live_verification["ok"] is True
    assert res.live_verification["guard_applied"] is True
    assert "unsupported_live_outcome_claim" in res.live_verification["guard_violations"]


def test_chat_with_codex_replaces_non_live_outcome_hallucination_with_library_result(library):
    runner = _runner_writing(
        {
            "reply": "Great transition, and I found a few dark tracks.",
            "tools_used": ["search_vibe"],
            "tool_trace": [{"name": "search_vibe", "arg": "dark rolling techno", "ok": True}],
            "track_ids": ["t000", "t001"],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "find me dark rolling techno",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "none",
            "deck_state": {},
            "live_evidence": {
                "mix": ["transition_block=no_resolved_decks"],
                "refs": ["mix:transition_block=no_resolved_decks"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "Great transition" not in res.reply
    assert res.reply == "Found 2 grounded library candidates for that vibe."
    assert res.track_ids == ["t000", "t001"]
    assert res.live_verification is not None
    assert res.live_verification["guard_applied"] is True


def test_chat_with_codex_keeps_library_request_from_empty_live_fallback(library):
    runner = _runner_writing(
        {
            "reply": "Great transition.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "find me dark rolling hypnotic techno",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "none",
            "deck_state": {},
            "live_evidence": {
                "mix": ["transition_block=no_resolved_decks"],
                "refs": ["mix:transition_block=no_resolved_decks"],
            },
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.reply == "I kept that as a library request, but I do not have grounded results to show yet."
    assert "live move" not in res.reply
    assert "sound change" not in res.reply
    assert res.live_verification is not None
    assert res.live_verification["ok"] is True
    assert res.live_verification["guard_applied"] is True
    assert "unsupported_live_outcome_claim" in res.live_verification["guard_violations"]


def test_chat_with_codex_corrects_disclaimer_with_fresh_blend_claim(library):
    runner = _runner_writing(
        {
            "reply": "I can't call that a transition, but that blend was clean.",
            "tools_used": [],
            "tool_trace": [],
            "track_ids": [],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "was that good?",
        library,
        live_context={
            **_fresh_live_transport(),
            "deck": "A",
            "deck_state": {"A": {"title": "Strobe", "confidence": 0.8}},
            "recent_moves": ["A_low: cut->killed"],
        },
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert "blend was clean" not in res.reply
    assert "clear two-deck proof" in res.reply
    assert "I need to correct that live read" not in res.reply
    assert "deck lanes=A=known" not in res.reply
    assert "won't call that a transition" not in res.reply


def test_chat_with_codex_surfaces_created_playlist_artifact(library, tmp_path):
    m3u = tmp_path / "dark-fuse.m3u8"
    json_path = tmp_path / "dark-fuse.json"
    m3u.write_text("#EXTM3U\n/tmp/t000.mp3\n", encoding="utf-8")
    json_path.write_text("{}", encoding="utf-8")
    runner = _runner_writing(
        {
            "reply": "Saved Dark Fuse.",
            "tools_used": ["search_vibe", "create_playlist"],
            "tool_trace": [
                {"name": "search_vibe", "arg": "dark peak techno", "ok": True},
                {"name": "create_playlist", "arg": "Dark Fuse", "ok": True},
            ],
            "track_ids": ["t000"],
            "playlist": {
                "name": "Dark Fuse",
                "track_ids": ["t000", "GHOST"],
                "m3u_path": str(m3u),
                "json_path": str(json_path),
                "dropped_ids": ["GHOST"],
            },
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "save this as a playlist",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "created"
    assert res.to_dict()["tool_trace"] == [
        {"name": "search_vibe", "arg": "dark peak techno", "ok": True},
        {"name": "create_playlist", "arg": "Dark Fuse", "ok": True},
    ]
    assert res.track_ids == ["t000"]
    assert res.playlist == {
        "name": "Dark Fuse",
        "track_ids": ["t000"],
        "m3u_path": str(m3u),
        "json_path": str(json_path),
        "dropped_ids": ["GHOST"],
    }
    assert res.to_dict()["playlist"]["m3u_path"] == str(m3u)


def test_chat_with_codex_prefers_authoritative_tool_tape(library):
    def runner(argv, **kw):
        event_path = kw["env"]["VIBEMIX_TOOL_EVENTS_FILE"]
        Path(event_path).write_text(
            json.dumps(
                {
                    "tool": "search_vibe",
                    "arg": "dark rolling techno; k=5",
                    "ok": True,
                    "summary": "4 tracks",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        Path(_out_path_from_argv(argv)).write_text(
            json.dumps(
                {
                    "reply": "I found a grounded lane.",
                    "tools_used": [],
                    "tool_trace": [
                        {"name": "made_up_tool", "arg": "model self-report", "ok": True}
                    ],
                    "track_ids": [],
                    "move_grades": [],
                    "playlist": None,
                    "export_path": None,
                }
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    res = chat_with_codex(
        "find me something dark",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.tools_used == ["search_vibe"]
    assert res.tool_trace == [
        {"name": "search_vibe", "arg": "dark rolling techno; k=5; 4 tracks", "ok": True}
    ]


def test_chat_with_codex_drops_phantom_playlist_artifact(library):
    runner = _runner_writing(
        {
            "reply": "I tried but no saved file came back.",
            "tools_used": ["search_vibe", "create_playlist"],
            "tool_trace": [
                {"name": "search_vibe", "arg": "peak tracks", "ok": True},
                {"name": "create_playlist", "arg": "Phantom", "ok": True},
            ],
            "track_ids": ["t000"],
            "playlist": {
                "name": "Phantom",
                "track_ids": ["t000"],
                "m3u_path": "/nonexistent/phantom.m3u8",
                "json_path": "/nonexistent/phantom.json",
                "dropped_ids": [],
            },
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "save this as a playlist",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "model_done"
    assert res.playlist is None
    assert res.track_ids == ["t000"]


def test_chat_with_codex_surfaces_export_path_when_file_exists(library, tmp_path):
    export_xml = tmp_path / "set.xml"
    export_xml.write_text("<DJ_PLAYLISTS/>", encoding="utf-8")
    runner = _runner_writing(
        {
            "reply": "Exported the set.",
            "tools_used": ["discover_pool", "sequence_set", "export_set"],
            "tool_trace": [
                {"name": "discover_pool", "arg": "two track set", "ok": True},
                {"name": "sequence_set", "arg": "peak_time", "ok": True},
                {"name": "export_set", "arg": "set.xml", "ok": True},
            ],
            "track_ids": ["t000", "t001"],
            "playlist": None,
            "export_path": str(export_xml),
        }
    )

    res = chat_with_codex(
        "export a two track set",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.stop_reason == "exported"
    assert res.export_path == str(export_xml)
    assert res.to_dict()["tool_trace"][2]["arg"] == "set.xml"
    assert res.to_dict()["export_path"] == str(export_xml)


def test_chat_with_codex_surfaces_grounded_move_grade_receipts(library):
    runner = _runner_writing(
        {
            "reply": "That bridge is LIT AFF.",
            "tools_used": ["transition_slate", "compile_musical_context"],
            "tool_trace": [
                {"name": "transition_slate", "arg": "bridge candidates", "ok": True},
                {"name": "compile_musical_context", "arg": "tr_001", "ok": True},
            ],
            "track_ids": [],
            "move_grades": [
                {
                    "candidate_id": "tr_001",
                    "track_id": "t000",
                    "title": "Tt000",
                    "slug": "lit_aff",
                    "label": "LIT AFF",
                    "xp": 100,
                    "reason": "everything clicks",
                    "overdrive": True,
                    "streak": 4,
                    "total_xp": 288,
                    "level": 2,
                    "level_xp": 38,
                    "next_level_xp": 250,
                    "level_up": True,
                    "levels_gained": 1,
                },
                {
                    "candidate_id": "tr_999",
                    "track_id": "GHOST",
                    "title": "Ghost",
                    "slug": "lit_aff",
                    "label": "LIT AFF",
                    "xp": 100,
                    "reason": "not grounded",
                    "overdrive": True,
                    "streak": 99,
                    "total_xp": 999,
                    "level": 4,
                    "level_xp": 249,
                    "next_level_xp": 250,
                    "level_up": True,
                    "levels_gained": 2,
                },
            ],
            "playlist": None,
            "export_path": None,
        }
    )

    res = chat_with_codex(
        "what bridges from this?",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )

    assert res.track_ids == ["t000"]
    assert res.move_grades == [
        {
            "candidate_id": "tr_001",
            "track_id": "t000",
            "title": "Tt000",
            "slug": "lit_aff",
            "label": "LIT AFF",
            "xp": 100,
            "reason": "everything clicks",
            "overdrive": True,
            "streak": 4,
            "total_xp": 288,
            "level": 2,
            "level_xp": 38,
            "next_level_xp": 250,
            "level_up": True,
            "levels_gained": 1,
        }
    ]
    assert res.to_dict()["move_grades"][0]["label"] == "LIT AFF"
    assert res.to_dict()["move_grades"][0]["level_up"] is True


def test_build_argv_injects_mcp_config_and_schema(tmp_path):
    argv = build_argv(
        "/usr/bin/codex",
        mcp_command="python",
        mcp_args=["-m", "vibemix.library.mcp_server"],
        schema_path=str(tmp_path / "s.json"),
        out_path=str(tmp_path / "o.json"),
        prompt="hi",
    )
    assert argv[0] == "/usr/bin/codex" and argv[1] == "exec"
    assert "--output-schema" in argv and "--sandbox" in argv
    joined = " ".join(argv)
    assert "mcp_servers.vibemix_library.command=" in joined
    assert f"mcp_servers.vibemix_library.tool_timeout_sec={codex_mod._MCP_TOOL_TIMEOUT_S}" in joined
    assert '"-m", "vibemix.library.mcp_server"' in joined.replace("'", '"') or any(
        "vibemix.library.mcp_server" in a for a in argv
    )
    assert "read-only" in argv  # tools write, not the shell


def test_find_codex_override_missing(tmp_path):
    assert find_codex(str(tmp_path / "nope")) is None


def test_find_codex_env_override(monkeypatch, tmp_path):
    codex = tmp_path / "codex"
    codex.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("VIBEMIX_CODEX_BIN", str(codex))

    assert find_codex() == str(codex)


def test_build_subprocess_env_adds_codex_and_node_paths(monkeypatch, tmp_path):
    codex = tmp_path / "codex-bin" / "codex"
    node = tmp_path / "node-bin" / "node"
    codex.parent.mkdir()
    node.parent.mkdir()
    codex.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    node.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("VIBEMIX_NODE_BIN", str(node))

    env = build_subprocess_env(str(codex))
    parts = env["PATH"].split(":")

    assert parts[0] == str(codex.parent)
    assert str(node.parent) in parts[:3]
    assert "/usr/bin" in parts


# -- guard branches --------------------------------------------------------- #


def test_not_installed(library, tmp_path):
    res = curate_with_codex("theme", library, codex_path=str(tmp_path / "nope-codex"))
    assert res.stop_reason == "codex_not_installed"
    assert "codex login" in (res.error or "")


def test_timeout(library):
    def runner(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw.get("timeout", 1))

    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, timeout_s=5, _runner=runner
    )
    assert res.stop_reason == "timeout"


def test_build_set_timeout_before_tools_uses_auto_crate_fallback(library, monkeypatch):
    def runner(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw.get("timeout", 1))

    def fake_auto_crate(**kwargs):
        assert kwargs["query"].startswith("peak-time")
        assert kwargs["curve"] == "peak_time"
        assert kwargs["n_slots"] == 3
        assert kwargs["bpm_min"] == 128.0
        assert kwargs["bpm_max"] == 138.0
        return AutoCrateResult(
            name="Fallback Set",
            stop_reason="created",
            curve=kwargs["curve"],
            n_slots=kwargs["n_slots"],
            track_ids=["t000", "t001", "t002"],
            rationale="3 tracks selected from 12 discovered candidates on curve peak_time.",
            playlist={
                "name": "Fallback Set",
                "track_ids": ["t000", "t001", "t002"],
                "m3u_path": "/tmp/fallback.m3u8",
                "json_path": "/tmp/fallback.json",
                "dropped_ids": [],
            },
            tool_trace=[
                {"name": "discover_pool", "ok": True, "summary": "12 candidates"},
                {"name": "sequence_set", "ok": True, "summary": "4 sequences"},
                {"name": "create_playlist", "ok": True, "summary": "/tmp/fallback.m3u8"},
            ],
        )

    monkeypatch.setattr("vibemix.library.auto_crate.build_auto_crate", fake_auto_crate)

    res = build_set_with_codex(
        "peak-time 3 tracks 128-138 bpm",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        timeout_s=5,
        _runner=runner,
    )

    assert res.stop_reason == "created"
    assert res.track_ids == ["t000", "t001", "t002"]
    assert res.playlist_name == "Fallback Set"
    assert "auto-crate engine" in res.rationale


def test_chat_set_timeout_before_tools_uses_auto_crate_fallback(library, monkeypatch):
    def runner(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw.get("timeout", 1))

    def fake_auto_crate(**kwargs):
        assert kwargs["curve"] == "peak_time"
        assert kwargs["n_slots"] == 3
        return AutoCrateResult(
            name="Viber Draft",
            stop_reason="created",
            curve=kwargs["curve"],
            n_slots=kwargs["n_slots"],
            track_ids=["t000", "t001", "t002"],
            rationale="3 tracks selected from 9 discovered candidates on curve peak_time.",
            playlist={
                "name": "Viber Draft",
                "track_ids": ["t000", "t001", "t002"],
                "m3u_path": "/tmp/viber.m3u8",
                "json_path": "/tmp/viber.json",
                "dropped_ids": [],
            },
            tool_trace=[
                {"name": "discover_pool", "ok": True, "summary": "9 candidates"},
                {"name": "sequence_set", "ok": True, "summary": "3 sequences"},
            ],
        )

    monkeypatch.setattr("vibemix.library.auto_crate.build_auto_crate", fake_auto_crate)

    res = chat_with_codex(
        "build me a 3 track peak-time set",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        timeout_s=5,
        _runner=runner,
    )

    assert res.stop_reason == "created"
    assert res.track_ids == ["t000", "t001", "t002"]
    assert res.playlist is not None
    assert res.tool_trace[0]["name"] == "codex_exec"
    assert res.tool_trace[0]["ok"] is False
    assert "grounded auto-crate engine" in res.reply


def test_chat_candidate_timeout_fallback_inspects_once(library, monkeypatch):
    calls: list[tuple[str, dict]] = []

    class FakeToolset:
        def dispatch(self, name, args):
            calls.append((name, args))
            if name == "discover_pool":
                return {
                    "pool": [
                        {"track_id": "t000", "title": "One", "artist": "A"},
                        {"track_id": "t001", "title": "Two", "artist": "B"},
                    ]
                }
            if name == "inspect_candidates":
                return {
                    "candidates": [
                        {
                            "track_id": "t000",
                            "features": {
                                "track_id": "t000",
                                "title": "One",
                                "artist": "A",
                                "bpm": 130.0,
                                "key": "8A",
                            },
                        },
                        {
                            "track_id": "t001",
                            "features": {
                                "track_id": "t001",
                                "title": "Two",
                                "artist": "B",
                                "bpm": None,
                                "key": None,
                            },
                        },
                    ]
                }
            return {"error": "unexpected"}

    def runner(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw.get("timeout", 1))

    monkeypatch.setattr(
        "vibemix.library.auto_crate.build_default_toolset",
        lambda with_embedder=True: FakeToolset(),
    )

    res = chat_with_codex(
        "find fast hardgroove candidates and inspect their BPM and key",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        timeout_s=5,
        _runner=runner,
    )

    assert [name for name, _args in calls] == ["discover_pool", "inspect_candidates"]
    assert calls[1][1]["track_ids"] == ["t000", "t001"]
    assert res.stop_reason == "model_done"
    assert res.track_ids == ["t000", "t001"]
    assert "one batch" in res.reply


def test_plain_chat_timeout_stays_timeout(library):
    def runner(argv, **kw):
        raise subprocess.TimeoutExpired(argv, kw.get("timeout", 1))

    res = chat_with_codex(
        "yo",
        library,
        codex_path=sys.executable,
        allow_shell=True,
        timeout_s=5,
        _runner=runner,
    )

    assert res.stop_reason == "timeout"
    assert res.tool_trace == []


def test_auth_required(library):
    runner = _runner_writing(None, returncode=1, stderr="Error: please run codex login first")
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "codex_auth_required"
    assert "codex login" in (res.error or "")


def test_generic_error(library):
    runner = _runner_writing(None, returncode=3, stderr="internal explosion")
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "error"
    assert "exit 3" in (res.error or "")


def test_empty_output(library):
    runner = _runner_writing(None, returncode=0, raw="")
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "empty_output"


def test_garbage_output(library):
    runner = _runner_writing(None, returncode=0, raw="not json {{{")
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "empty_output"


def test_no_track_ids(library):
    runner = _runner_writing({"name": "P", "track_ids": [], "rationale": "meh"})
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "no_playlist"
    assert res.rationale == "meh"


def test_created_with_grounding_revalidation(library, monkeypatch, tmp_path):
    # Codex returns one real id + one bogus id → bogus dropped at the boundary,
    # then the WRAPPER persists the survivors (codex SELECTS, wrapper WRITES).
    # Redirect the persist into tmp via PLAYLISTS_DIR.
    cp_mod = importlib.import_module("vibemix.library.create_playlist")
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)
    runner = _runner_writing(
        {
            "name": "Warm-Up",
            "track_ids": ["t000", "GHOST-999", "t001"],
            "rationale": "hypnotic build",
        }
    )
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "created"
    assert res.track_ids == ["t000", "t001"]  # GHOST dropped
    assert "GHOST-999" not in res.track_ids
    assert res.playlist_name == "Warm-Up"
    assert res.rationale == "hypnotic build"
    # The wrapper persisted a real M3U + JSON (the single validated write).
    assert res.m3u_path is not None and Path(res.m3u_path).exists()
    assert res.json_path is not None and Path(res.json_path).exists()


def test_created_all_bogus_is_no_playlist(library):
    runner = _runner_writing({"name": "P", "track_ids": ["X", "Y"], "rationale": "r"})
    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "no_playlist"  # nothing survived grounding


def test_build_set_codex_exported_with_export_and_grounding(library, monkeypatch, tmp_path):
    """Set-prep over Codex: discover→sequence→export. The wrapper re-validates the
    sequenced ids (grounding) and surfaces the export_set Rekordbox XML path — but
    ONLY when the path actually exists on disk (honest)."""
    from vibemix.library.codex_curate import build_set_with_codex

    cp_mod = importlib.import_module("vibemix.library.create_playlist")
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)
    # The export_set tool would have written this XML during the run.
    export_xml = tmp_path / "set.xml"
    export_xml.write_text("<DJ_PLAYLISTS/>", encoding="utf-8")
    runner = _runner_writing(
        {
            "name": "Peak Set",
            "track_ids": ["t002", "GHOST", "t003"],
            "export_path": str(export_xml),
            "rationale": "controlled tension → plateau",
        }
    )
    res = build_set_with_codex(
        "dark warehouse",
        library,
        curve="peak_time",
        codex_path=sys.executable,
        allow_shell=True,
        _runner=runner,
    )
    assert res.stop_reason == "exported"
    assert res.track_ids == ["t002", "t003"]  # GHOST dropped (grounding)
    assert res.playlist_name == "Peak Set"
    assert res.export_path == str(export_xml)  # surfaced (file exists)
    assert res.m3u_path is not None and Path(res.m3u_path).exists()


def test_build_set_cli_treats_codex_exported_as_success(library, monkeypatch, capsys, tmp_path):
    """Regression: exported is the successful set-prep terminal.

    The Codex wrapper returns ``stop_reason="exported"`` when export_set wrote a
    Rekordbox XML. The CLI bridge must put that JSON on stdout and return zero,
    otherwise Tauri treats a successful exported set as a failed command.
    """
    import argparse

    import vibemix.__main__ as main_mod
    import vibemix.library.codex_curate as codex_mod

    export_xml = tmp_path / "set.xml"
    export_xml.write_text("<DJ_PLAYLISTS/>", encoding="utf-8")

    def fake_build_set_with_codex(*args, **kwargs):
        assert kwargs["n_slots"] == 3
        assert kwargs["export"] is True
        return codex_mod.CodexCurateResult(
            theme="dark warehouse",
            stop_reason="exported",
            playlist_name="Peak Set",
            track_ids=["t002", "t003"],
            rationale="controlled tension",
            export_path=str(export_xml),
        )

    monkeypatch.setattr(codex_mod, "build_set_with_codex", fake_build_set_with_codex)
    rc = main_mod._cmd_library_build_set_codex(
        argparse.Namespace(
            brief="dark warehouse",
            curve="peak_time",
            name=None,
            n_slots=3,
            export="rekordbox",
        ),
        library,
    )

    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["stop_reason"] == "exported"
    assert payload["export_path"] == str(export_xml)
    assert "exported" in captured.err


def test_build_set_codex_export_path_nulled_when_missing(library, monkeypatch, tmp_path):
    """A returned export_path that does NOT exist on disk is treated as no export
    (never trust the model's claim of a file that isn't there)."""
    from vibemix.library.codex_curate import build_set_with_codex

    cp_mod = importlib.import_module("vibemix.library.create_playlist")
    monkeypatch.setattr(cp_mod, "PLAYLISTS_DIR", tmp_path)
    runner = _runner_writing(
        {
            "name": "Set",
            "track_ids": ["t000"],
            "export_path": "/nonexistent/phantom.xml",
            "rationale": "r",
        }
    )
    res = build_set_with_codex(
        "brief", library, codex_path=sys.executable, allow_shell=True, _runner=runner
    )
    assert res.stop_reason == "created"
    assert res.export_path is None  # phantom path dropped


def test_blocked_without_opt_in(library):
    """Default (no VIBEMIX_CODEX_ALLOW_SHELL): the upstream MCP-cancel bug means
    we don't even spawn — surface the honest blocked result + the opt-in path.
    The runner is NEVER called."""
    called = {"n": 0}

    def runner(argv, **kw):
        called["n"] += 1
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    res = curate_with_codex(
        "theme", library, codex_path=sys.executable, allow_shell=False, _runner=runner
    )
    assert res.stop_reason == "codex_mcp_blocked"
    assert "VIBEMIX_CODEX_ALLOW_SHELL" in (res.error or "")
    assert "16685" in (res.error or "")  # cites the upstream bug
    assert called["n"] == 0  # never spawned


def test_build_argv_bypass_uses_dangerous_flag(tmp_path):
    argv = build_argv(
        "/usr/bin/codex",
        mcp_command="python",
        mcp_args=["-m", "x"],
        schema_path=str(tmp_path / "s.json"),
        out_path=str(tmp_path / "o.json"),
        prompt="hi",
        bypass_sandbox=True,
    )
    assert "--dangerously-bypass-approvals-and-sandbox" in argv
    assert "--sandbox" not in argv  # bypass replaces the read-only sandbox
