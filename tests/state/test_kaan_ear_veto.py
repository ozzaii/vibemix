# SPDX-License-Identifier: Apache-2.0
"""Phase 60 (HARMONIC-03) — the Kaan-ear veto, the ship gate for the clash detector.

Over-flagging is the failure mode that trips release: a false clash on a pair Kaan
would happily mix. This corpus is Kaan's editable record of pairs he rides cleanly
(``verdict: "safe"`` — MUST NOT flag) plus a small control set of true clashes
(``verdict: "clash"`` — SHOULD flag, proving the gate isn't vacuously suppressing
everything).

The detector's runtime ``harmonic_clash_enabled`` flag (Plan 60-02) stays **False**
until Kaan runs this corpus against his real disagreed pairs and signs off — mirroring
the Phase-59 ``DeckPoller._vision_enabled`` default-off ship-gate precedent. The
runnable scorer ``eval/harmonic/run_veto.py`` is the KAAN-ACTION surface; this test is
the always-on regression that keeps the corpus honest.

Mirrors the table-oracle idiom of ``tests/state/test_harmonics.py``: a module-level
loader feeds ``@pytest.mark.parametrize`` and the assertions run straight against the
shipped ``is_clash`` predicate.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibemix.state.harmonics import is_clash

# Resolve the fixture relative to THIS test file (never an absolute path) so the
# corpus moves with the repo and the suite stays CWD-independent.
_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "kaan_disagreed_pairs.json"


def load_disagreed_pairs() -> list[dict]:
    """Load the editable Kaan-ear corpus (the disagreed pairs + true-clash control)."""
    return json.loads(_FIXTURE.read_text())


_CORPUS = load_disagreed_pairs()
_SAFE = [p for p in _CORPUS if p["verdict"] == "safe"]
_CLASH = [p for p in _CORPUS if p["verdict"] == "clash"]


def _label(p: dict) -> str:
    return f"{p['a']}/{p['b']}"


def test_corpus_is_non_trivial():
    """The corpus must hold BOTH safe pairs (the veto) and clash pairs (the
    non-vacuous control) — an empty either side would make the gate meaningless."""
    assert _SAFE, "corpus has no 'safe' (must-not-flag) pairs"
    assert _CLASH, "corpus has no 'clash' (must-flag) control pairs"


@pytest.mark.parametrize("pair", _SAFE, ids=[_label(p) for p in _SAFE])
def test_disagreed_pairs_never_flag(pair):
    """Every pair Kaan would happily mix MUST NOT flag as a clash. A False here is
    a false clash = the failure mode that trips the release gate. Symmetric — order
    must not matter."""
    assert is_clash(pair["a"], pair["b"]) is False, f"{_label(pair)} false-flagged: {pair['note']}"
    assert is_clash(pair["b"], pair["a"]) is False, f"{_label(pair)} false-flagged (reversed): {pair['note']}"


@pytest.mark.parametrize("pair", _CLASH, ids=[_label(p) for p in _CLASH])
def test_corpus_true_clashes_do_flag(pair):
    """Every declared true clash in the corpus SHOULD flag — proves the gate is not
    vacuously suppressing everything. Symmetric."""
    assert is_clash(pair["a"], pair["b"]) is True, f"{_label(pair)} failed to flag: {pair['note']}"
    assert is_clash(pair["b"], pair["a"]) is True, f"{_label(pair)} failed to flag (reversed): {pair['note']}"


def test_true_clashes_do_flag():
    """The RESEARCH-cited anchors, asserted directly as a smoke gate (mirrors the
    verbatim shape in 60-RESEARCH §Code Examples)."""
    assert is_clash("8A", "3A") is True
    assert is_clash("8A", "1A") is True
