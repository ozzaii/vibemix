# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.intel.claims import MusicClaimLedger, claim_status_for_confidence


def test_claim_id_shape_is_packet_scoped() -> None:
    ledger = MusicClaimLedger("ctx_001")

    first = ledger.add(
        "transition_fit",
        subject_id="tr_001",
        value="compatible",
        evidence_refs=("candidate:tr_001",),
        confidence=0.82,
        scope="transition",
    )
    second = ledger.add(
        "cue_slot",
        subject_id="tr_001",
        value="A",
        evidence_refs=("cue:cue_001",),
        confidence=0.91,
        scope="cue",
    )

    assert first.claim_id == "clm_ctx_001_000"
    assert second.claim_id == "clm_ctx_001_001"
    assert ledger.claim_ids() == ("clm_ctx_001_000", "clm_ctx_001_001")


def test_claim_status_thresholds() -> None:
    assert claim_status_for_confidence(0.90) == "allowed"
    assert claim_status_for_confidence(0.60) == "hedged"
    assert claim_status_for_confidence(0.40) == "internal_only"
    assert claim_status_for_confidence(0.20) == "rejected"


def test_internal_only_claim_not_visible_to_model() -> None:
    ledger = MusicClaimLedger("ctx_003")
    ledger.add(
        "bars_until_event",
        subject_id="tr_002",
        value=None,
        evidence_refs=("packet:ctx_003",),
        confidence=0.40,
        scope="live_timing",
        allowed_phrases=("timing is not locked",),
    )

    assert ledger.allowed_for_model() == ()
    assert ledger.claim_summary() == ()


def test_claim_ledger_redacts_paths_and_vectors_from_public_trace() -> None:
    ledger = MusicClaimLedger("ctx_004")
    claim = ledger.add(
        "semantic_match",
        subject_id="tr_004",
        value="close",
        evidence_refs=("/Users/ozai/private.wav", "vector:raw_001", "candidate:tr_004"),
        confidence=0.90,
        scope="transition",
        allowed_phrases=("texture is close",),
    )

    assert claim.claim_status == "rejected"
    assert "redacted_unsafe_evidence_ref" in claim.reason_codes
    trace_text = str(ledger.trace())
    assert "/Users/ozai" not in trace_text
    assert "vector:raw_001" not in trace_text
    assert "candidate:tr_004" in trace_text
