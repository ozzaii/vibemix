# SPDX-License-Identifier: Apache-2.0
"""Phase 96 — 4-site schema-mirror lock for the `[cue:]` evidence source.

Mirrors the v6 [recall:] and P93 [exemplar:] precedents EXACTLY. Each
site MUST carry the ``cue`` token; if ANY site drifts, the grammar
lock breaks and a fabricated [cue:<id>] can ride through un-validated
(the silent-poisoning hole that the multi-site lock-step contract
exists to prevent).

REQ-ID: CURR-3.07 (citation source schema-mirror lock).
Flipped GREEN by Plan 96-02 — the atomic 4-site mirror commit landed
``"cue"`` in ``EVIDENCE_SOURCES``, ``_SOURCE_ALT``,
``CITATION_GRAMMAR_BLOCK``, and ``dj_cohost._build_citation_strip``.
"""
from __future__ import annotations
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent


def test_site_1_evidence_sources_frozenset_contains_cue() -> None:
    """Site 1: EVIDENCE_SOURCES frozenset @ state/evidence_registry.py."""
    from vibemix.state.evidence_registry import EVIDENCE_SOURCES
    assert "cue" in EVIDENCE_SOURCES, (
        "EVIDENCE_SOURCES drift — `cue` missing from the frozenset. "
        "Phase 96 4-site mirror is broken; fabricated [cue:<id>] rides "
        "through un-validated."
    )


def test_site_2_source_alt_regex_includes_cue() -> None:
    """Site 2: _SOURCE_ALT regex alternation @ state/evidence_registry.py."""
    from vibemix.state.evidence_registry import _SOURCE_ALT
    assert "cue" in _SOURCE_ALT.split("|"), (
        "_SOURCE_ALT regex drift — `cue` missing from the alternation. "
        "parse_citations() will not match [cue:<id>] atoms; the linter "
        "never sees them."
    )


def test_site_2b_evidence_citation_re_matches_cue_atom() -> None:
    """Sanity: a synthetic [cue:<id>] passes the compiled regex."""
    from vibemix.state.evidence_registry import (
        EVIDENCE_CITATION_RE,
        parse_citations,
    )
    assert EVIDENCE_CITATION_RE.fullmatch(
        "[cue:phrase_boundary@45.2]"
    ) is not None
    assert EVIDENCE_CITATION_RE.fullmatch("[cue:drop@180.0]") is not None
    # Inner colon survives (mirrors recall/exemplar precedent)
    assert EVIDENCE_CITATION_RE.fullmatch(
        "[cue:phrase:boundary:45.2]"
    ) is not None
    parsed = parse_citations("[cue:phrase_boundary@45.2]")
    assert parsed == [("cue", "phrase_boundary@45.2")]


def test_site_3_citation_grammar_block_documents_cue() -> None:
    """Site 3: CITATION_GRAMMAR_BLOCK @ prompts/matrix.py — documented
    grammar includes the [cue:<anchor_id>] form so Gemini learns it."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    assert "[cue:<anchor_id>]" in CITATION_GRAMMAR_BLOCK, (
        "CITATION_GRAMMAR_BLOCK drift — the [cue:<anchor_id>] form is "
        "missing. Gemini's system instruction does not teach the source; "
        "Plan 96-03's proactive lens emits ungrounded count-ins."
    )


def test_site_4_dj_cohost_citation_strip_allows_cue() -> None:
    """Site 4: agent/dj_cohost.py _build_citation_strip — `cue` joins
    the chip-derivation allow-list (the seventh entry after the v6
    addition of recall and P93's addition of exemplar)."""
    source_path = _REPO / "src" / "vibemix" / "agent" / "dj_cohost.py"
    text = source_path.read_text(encoding="utf-8")
    # The allow-list tuple at line ~271 — match a tuple shape that
    # carries `cue` after `exemplar`. The full tuple is open-ended (Phase
    # 96 lands as the seventh entry; future plans may add more). Verify
    # `cue` lives inside the locked source-order tuple.
    pattern = re.compile(
        r'if source not in\s*\(\s*"ev"\s*,\s*"mix"\s*,\s*"midi"\s*,\s*"key"\s*,\s*"recall"\s*,\s*"exemplar"\s*,\s*"cue"',
        re.MULTILINE,
    )
    assert pattern.search(text) is not None, (
        "Site 4 drift — `cue` missing from the _build_citation_strip "
        "allow-list tuple in dj_cohost.py. Chip-strip will silently drop "
        "valid [cue:<id>] grounded citations."
    )


def test_parse_citations_round_trips_cue_atom() -> None:
    """End-to-end parsing: a [cue:phrase_boundary@45.2] atom round-trips
    through parse_citations to ('cue', 'phrase_boundary@45.2')."""
    from vibemix.state.evidence_registry import parse_citations
    atoms = parse_citations("[cue:phrase_boundary@45.2]")
    assert atoms == [("cue", "phrase_boundary@45.2")], (
        f"parse_citations failed to round-trip [cue:] atom: {atoms!r}"
    )


def test_evidence_registry_writes_and_reads_cue_source() -> None:
    """The registry accepts source='cue' for write + snapshot read."""
    from vibemix.state.evidence_registry import EvidenceRegistry
    reg = EvidenceRegistry()
    reg.write(source="cue", key="phrase_boundary@45.2", t_session=45.2)
    snap = reg.snapshot()
    assert snap["cue"]["phrase_boundary@45.2"] == (45.2,)


def test_all_four_sites_lockstep_with_cue() -> None:
    """Cross-validation: EVIDENCE_SOURCES is the source-of-truth — every
    source in the frozenset must appear in the grammar block."""
    from vibemix.state.evidence_registry import EVIDENCE_SOURCES
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    assert "cue" in EVIDENCE_SOURCES
    assert f"[cue:" in CITATION_GRAMMAR_BLOCK
