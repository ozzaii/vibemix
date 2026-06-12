"""The evidence-license prompt block (C.1, free Sven).

Configure-at-source: the license tells the model what the evidence allows,
computed from the SAME constants the result-boundary guards check. These
tests pin the structural promises: constant-by-reference drift, positive
framing, the machine token, and the size budget.
"""

from __future__ import annotations

import re

import pytest

import vibemix.state.deck_context as dc
from vibemix.state.deck_state import DeckState
from vibemix.state.deck_context import render_evidence_license
from vibemix.state.music_state import MusicState


def _state(
    *,
    bands: dict | None = None,
    vocal: bool = False,
) -> MusicState:
    state = MusicState()
    state.rms = 0.05
    state.audible = True
    state.bands = bands or {"sub": 0.6, "low": 0.3, "mid": 0.05, "high": 0.02}
    state.vocal_active = vocal
    state.deck_state = DeckState(decks={})
    return state


def test_license_token_reflects_state() -> None:
    text = render_evidence_license(
        _state(), ("A eq low cut",), policy="blocked", reason="no_resolved_decks"
    )
    assert "evidence_license[decks=unresolved deck_words=reserved" in text
    assert "bands_live=sub,low" in text
    assert "bands_open=mid,high" in text
    assert "vocal=unconfirmed" in text
    assert "hands=1]" in text


def test_license_vocal_and_supported_verdict_variants() -> None:
    text = render_evidence_license(
        _state(vocal=True), (), policy="supported_verdict", reason=None
    )
    assert "decks=resolved deck_words=open" in text
    assert "vocal=confirmed" in text
    assert "name it freely" in text


def test_license_rose_delta_unlocks_below_floor_band() -> None:
    text = render_evidence_license(
        _state(),
        (),
        policy="blocked",
        reason="no_resolved_decks",
        audio_delta_items=["mid energy rose 44% (clear)"],
    )
    assert "The mid rise the deltas show is yours to call" in text


def test_license_positive_framing_lint() -> None:
    """HARD RULE: positive framing — no imperative bans in any variant."""
    for policy in ("blocked", "watch_not_claim", "candidate_not_verdict", "supported_verdict"):
        for vocal in (False, True):
            for compact in (False, True):
                text = render_evidence_license(
                    _state(vocal=vocal),
                    ("A eq low cut",),
                    policy=policy,
                    reason=None,
                    compact=compact,
                )
                lowered = text.lower()
                assert "do not" not in lowered, text
                assert "don't" not in lowered, text
                assert "never" not in lowered, text
                assert not re.search(r"\bNOT\b", text), text


def test_license_size_budget() -> None:
    full = render_evidence_license(
        _state(), ("A eq low cut",), policy="blocked", reason="no_resolved_decks"
    )
    # ~4 chars/token heuristic: the full block must stay a small rider, not a
    # second prompt (<= ~150 tokens), and compact a single line.
    assert len(full) <= 1100, len(full)
    compact = render_evidence_license(
        _state(), (), policy="blocked", reason=None, compact=True
    )
    assert len(compact) <= 260
    assert compact.startswith("evidence_license[")


def test_license_floor_moves_by_reference(monkeypatch: pytest.MonkeyPatch) -> None:
    """The live/open split must read SPECTRAL_CLAIM_BAND_FLOOR at call time —
    a copied literal would let prompt and guard drift apart silently."""
    state = _state(bands={"sub": 0.6, "low": 0.3, "mid": 0.15, "high": 0.02})
    before = render_evidence_license(state, (), policy="blocked", reason=None)
    assert "bands_live=sub,low,mid" in before
    monkeypatch.setattr(dc, "SPECTRAL_CLAIM_BAND_FLOOR", 0.25)
    after = render_evidence_license(state, (), policy="blocked", reason=None)
    assert "bands_live=sub,low" in after
    assert "bands_open=mid,high" in after


def test_license_token_is_a_leak_trigger() -> None:
    """C.4: a model echoing the machine token is caught by the public
    diagnostic guard."""
    assert dc._LIVE_PUBLIC_DIAGNOSTIC_RE.search(
        "evidence_license[decks=unresolved] says I keep this in sound terms"
    )
    assert dc._LIVE_PUBLIC_DIAGNOSTIC_RE.search("my bands_live=sub,low right now")


def test_license_block_cannot_defang_the_vocal_witness_rule() -> None:
    """C.3 (the verified defanging flaw): the license block's own 'vocals'
    token must never license a fabricated vocal event. The boundary passes
    only the EXTRACTED machine evidence sections as offered text — the
    license prose, task text, and persona never enter."""
    state = _state()
    license_text = render_evidence_license(
        state, (), policy="blocked", reason="no_resolved_decks"
    )
    assert "vocals" in license_text  # the bait is real
    prompt = (
        "You are Sven. React to the live read.\n"
        "hearing[rms=0.050 sub=0.60 low=0.30 mid=0.05 high=0.02 bpm=0]\n"
        "Live deltas: low energy rose 20% (clear).\n"
        f"{license_text}\n"
        "Speak one short line."
    )
    offered = dc.extract_offered_evidence_text(prompt)
    assert "vocal" not in offered.casefold()
    assert "hearing[" in offered and "Live deltas:" in offered
    result = dc.apply_live_claim_guard(
        "The vocals just came in, huge moment.",
        state,
        (),
        event_type="PHASE",
        offered_evidence_text=offered,
    )
    assert result.corrected is True
    assert result.speakable is False
    # The contrast at the EW layer itself: the unextracted full prompt WOULD
    # defang the witness rule (its license prose contains 'vocals'), the
    # extracted offered text keeps it armed. (The full guard stack still
    # holds the line either way via the state-based source-detail layer —
    # defense in depth — so the pin lives at the EW-rule level.)
    assert (
        dc._unsupported_event_witness_reason(
            "The vocals just came in, huge moment.",
            state,
            event_type="PHASE",
            offered_evidence_text=prompt,
        )
        is None
    )
    assert (
        dc._unsupported_event_witness_reason(
            "The vocals just came in, huge moment.",
            state,
            event_type="PHASE",
            offered_evidence_text=offered,
        )
        == "vocal_event_without_witness"
    )
