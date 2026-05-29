# SPDX-License-Identifier: Apache-2.0
"""Phase 93 — 4-site schema-mirror lock for the `[exemplar:]` evidence source.

Mirrors the v6 [recall:] precedent EXACTLY. Each site MUST carry the
``exemplar`` token; if ANY site drifts, the grammar lock breaks and a
fabricated [exemplar:<id>] can ride through un-validated (the silent-poisoning
hole that the multi-site lock-step contract exists to prevent).

REQ-ID: EXEMPLAR-05 (citation source schema-mirror lock).
Flipped GREEN by Plan 93-05 — the atomic 4-site mirror commit landed
``"exemplar"`` in ``EVIDENCE_SOURCES``, ``_SOURCE_ALT``,
``CITATION_GRAMMAR_BLOCK``, and ``dj_cohost._build_citation_strip``.
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent


def test_site_1_evidence_sources_frozenset_contains_exemplar() -> None:
    """Site 1: EVIDENCE_SOURCES frozenset @ state/evidence_registry.py:111."""
    from vibemix.state.evidence_registry import EVIDENCE_SOURCES
    assert "exemplar" in EVIDENCE_SOURCES, (
        "EVIDENCE_SOURCES drift — `exemplar` missing from the frozenset. "
        "Phase 93 4-site mirror is broken; fabricated [exemplar:<id>] rides "
        "through un-validated."
    )


def test_site_2_source_alt_regex_includes_exemplar() -> None:
    """Site 2: _SOURCE_ALT regex alternation @ state/evidence_registry.py:137."""
    from vibemix.state.evidence_registry import _SOURCE_ALT
    assert "exemplar" in _SOURCE_ALT.split("|"), (
        "_SOURCE_ALT regex drift — `exemplar` missing from the alternation. "
        "parse_citations() will not match [exemplar:<id>] atoms; the linter "
        "never sees them."
    )


def test_site_2b_evidence_citation_re_matches_exemplar_atom() -> None:
    """Sanity: a synthetic [exemplar:<id>] passes the compiled regex."""
    from vibemix.state.evidence_registry import EVIDENCE_CITATION_RE, parse_citations
    assert EVIDENCE_CITATION_RE.fullmatch("[exemplar:library:Marlon-Atlas]") is not None
    # Inner colon survives as part of the body (mirrors recall: behavior)
    parsed = parse_citations("[exemplar:library:Marlon-Atlas]")
    assert parsed == [("exemplar", "library:Marlon-Atlas")]


def test_site_3_citation_grammar_block_includes_exemplar() -> None:
    """Site 3: CITATION_GRAMMAR_BLOCK @ prompts/matrix.py."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    assert "[exemplar:" in CITATION_GRAMMAR_BLOCK, (
        "CITATION_GRAMMAR_BLOCK drift — `[exemplar:` form missing from the "
        "system instruction. Gemini will not know the citation shape exists."
    )


def test_site_4_citation_strip_allow_list_includes_exemplar() -> None:
    """Site 4: _build_citation_strip allow-list @ agent/dj_cohost.py:255.

    AST/grep parity test — reads the source file directly and asserts the
    allow-list tuple contains "exemplar". The runtime `_build_citation_strip`
    can't be unit-tested without standing up a full agent; this static test
    pins the source-of-truth membership.
    """
    src = (_REPO / "src" / "vibemix" / "agent" / "dj_cohost.py").read_text()
    # The allow-list tuple at line ~271 — match a tuple shape that
    # carries `exemplar` (Phase 93). The full tuple is open-ended (Phase 96
    # adds `cue` as the seventh entry; future plans may add more). Verify
    # `exemplar` lives inside a tuple that starts with `"ev"` and follows
    # the locked source order.
    pattern = re.compile(
        r'if source not in\s*\(\s*"ev"\s*,\s*"mix"\s*,\s*"midi"\s*,\s*"key"\s*,\s*"recall"\s*,\s*"exemplar"',
        re.MULTILINE,
    )
    assert pattern.search(src) is not None, (
        "Site 4 drift — `exemplar` missing from the _build_citation_strip "
        "allow-list tuple in dj_cohost.py. Chip-strip will silently drop "
        "valid [exemplar:<id>] grounded citations."
    )


def test_all_four_sites_lockstep() -> None:
    """Cross-validation: EVIDENCE_SOURCES is the source-of-truth — every
    source in the frozenset must appear in the grammar block."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    from vibemix.state.evidence_registry import EVIDENCE_SOURCES
    for source in EVIDENCE_SOURCES:
        assert f"[{source}:" in CITATION_GRAMMAR_BLOCK, (
            f"EVIDENCE_SOURCES drift: source {source!r} not in prompt grammar block"
        )
