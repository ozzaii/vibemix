# SPDX-License-Identifier: Apache-2.0
"""tests/launch/test_launch_rotation_ship_11.py — §SHIP-11 launch-rotation structural pin.

Phase 45 Plan 45-05: pins the structural invariants of the v3.0
``§SHIP-11 — v3.0 24h Monitoring Rotation (4 × 6h shifts, Kaan solo)``
section that ``docs/launch-rotation.md`` carries on top of the
Phase 39 v2.1 hourly rotation archive.

Why we need a grep gate at all
------------------------------
``docs/launch-rotation.md`` is the single operational source-of-truth
that ``KAAN-ACTION-LEGAL.md §SHIP-11`` (Plan 45-06) cross-references
when Kaan runs the 24h discharge live. If a future doc edit silently
drops one of:

* the 4 × 6h shift table (Kaan-solo for v3.0 — Francesco + Momo
  deferred to v3.x per CONTEXT §SHIP-11),
* the triage decision tree (comment-volume / crash-report /
  API-key-rate-limit / Bravoh-server-down → action mapping),
* the monitoring-signal sources block (GH issues triage / healthz /
  ``check_bravoh_server_ready.sh`` / Discord #bugs / star velocity /
  fresh-VM install — the highest-priority signal per memory
  ``project_one_click_install_hard_req``),
* the sign-off block (per-shift COMPLETE lines + final Sign-off-by),

…the runbook silently goes out of sync with the operational contract,
and Kaan walks into the live discharge with the wrong protocol. This
file is the CI seatbelt.

Why we also pin Phase 39 preservation
-------------------------------------
The v2.1 24-row hourly rotation table is **archived launch history**
— it documents what Kaan / Francesco / Bravoh-team actually did across
T+0 → T+24 for the v2.1 cut. We append the v3.0 §SHIP-11 section
**after** the existing ``## References`` H2; we never edit the
v2.1 table. ``test_phase_39_v21_table_preserved`` is the proof we
will not damage history.

AI-slop gate
------------
``test_ship11_section_ai_slop_clean`` imports
``AI_SLOP_BLOCKLIST`` + ``_DEEPLY_RE`` from
``scripts/launch/check_no_ai_slop.py`` (the script that owns the
single source of truth for slop tokens across the launch-check
family) and applies them to just the §SHIP-11 section text. The
upstream CLI is launch-copy-directory scoped; importing the
constants lets us reuse the canonical blocklist without inventing a
new CLI surface or duplicating the token tuple. If the constants
change, this test inherits the change automatically (correct
single-source-of-truth behavior).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.launch.check_no_ai_slop import AI_SLOP_BLOCKLIST, _DEEPLY_RE

REPO_ROOT = Path(__file__).resolve().parents[2]
ROTATION_DOC = REPO_ROOT / "docs" / "launch-rotation.md"

# Canonical anchors used to slice the §SHIP-11 section out of the full doc.
SHIP11_H2_PREFIX = "## §SHIP-11"
PHASE_39_TABLE_H2 = "## Per-hour shift (24h, all times CET)"
PHASE_39_FIRST_ROW_FRAGMENT = "| 08:00 | T-1"
EXISTING_REFERENCES_H2 = "## References"

# 4-shift canonical CET windows (CONTEXT §SHIP-11 specifics).
SHIFT_WINDOWS: tuple[tuple[str, str], ...] = (
    ("Shift 1", "08:00 – 14:00"),
    ("Shift 2", "14:00 – 20:00"),
    ("Shift 3", "20:00 – 02:00"),
    ("Shift 4", "02:00 – 08:00"),
)

# Triage decision tree branch labels (CONTEXT §SHIP-11).
TRIAGE_BRANCHES: tuple[str, ...] = (
    "Comment volume",
    "Crash report",
    "API key rate-limit",
    "Bravoh server down",
)

# Monitoring signal sources that MUST be enumerated.
MONITORING_SOURCES_KEYWORDS: tuple[str, ...] = (
    "GH issues",
    "Discord #bugs",
    "Bravoh healthz",
    "check_bravoh_server_ready",
    "Star velocity",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc_text() -> str:
    """Read the rotation doc once per test; fail clearly if it's missing."""
    if not ROTATION_DOC.exists():
        pytest.fail(f"docs/launch-rotation.md missing at {ROTATION_DOC}")
    return ROTATION_DOC.read_text(encoding="utf-8")


def _ship11_section(text: str) -> str:
    """Extract the §SHIP-11 section body (the H2 line through next H2 / EOF).

    Returns the substring starting at the §SHIP-11 H2 line and ending at
    either the next top-level H2 or the end of file — whichever is sooner.
    Returns an empty string if the §SHIP-11 H2 isn't present (used by the
    RED-phase tests to assert absence cleanly).
    """
    start = text.find(SHIP11_H2_PREFIX)
    if start < 0:
        return ""
    # Find the next H2 after the §SHIP-11 H2 line.
    next_h2 = text.find("\n## ", start + len(SHIP11_H2_PREFIX))
    if next_h2 < 0:
        return text[start:]
    return text[start:next_h2]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_doc_exists() -> None:
    """Test 1: docs/launch-rotation.md exists (sanity baseline)."""
    assert ROTATION_DOC.exists(), f"missing: {ROTATION_DOC}"


def test_phase_39_v21_table_preserved() -> None:
    """Test 2: Phase 39 v2.1 24-row hourly table preserved verbatim.

    Asserts both the H2 anchor and the canonical first row are present.
    Catches "someone replaced the v2.1 table with a v3.0 one" damage —
    the v2.1 table is archived launch history and must remain
    untouched.
    """
    text = _doc_text()
    assert PHASE_39_TABLE_H2 in text, (
        f"Phase 39 v2.1 hourly table H2 '{PHASE_39_TABLE_H2}' missing — "
        "v2.1 archive damaged."
    )
    assert PHASE_39_FIRST_ROW_FRAGMENT in text, (
        f"Phase 39 v2.1 first row fragment '{PHASE_39_FIRST_ROW_FRAGMENT}' "
        "missing — v2.1 archive damaged."
    )


def test_ship11_h2_present() -> None:
    """Test 3: §SHIP-11 v3.0 H2 section exists with canonical title."""
    text = _doc_text()
    canonical = (
        "## §SHIP-11 — v3.0 24h Monitoring Rotation "
        "(4 × 6h shifts, Kaan solo)"
    )
    assert canonical in text, (
        f"Canonical §SHIP-11 H2 missing.\n  Expected: {canonical}"
    )


def test_ship11_shift_table_has_four_canonical_windows() -> None:
    """Test 4: 4-shift table contains all 4 canonical CET windows.

    Each (Shift N, CET window) pair must coexist on the same row line
    so partial copies / re-orderings can't slip through.
    """
    section = _ship11_section(_doc_text())
    assert section, "§SHIP-11 section missing — can't pin shift table."

    table_lines = [ln for ln in section.splitlines() if ln.startswith("|")]
    assert table_lines, "§SHIP-11 section missing markdown table rows."

    missing: list[str] = []
    for shift_label, cet_window in SHIFT_WINDOWS:
        found = any(
            (shift_label in ln) and (cet_window in ln) for ln in table_lines
        )
        if not found:
            missing.append(f"{shift_label} @ {cet_window}")
    assert not missing, (
        "§SHIP-11 shift table missing canonical rows: " + ", ".join(missing)
    )


def test_ship11_triage_tree_present() -> None:
    """Test 5: ### Triage decision tree H3 + 4 categorized branches.

    Per CONTEXT §SHIP-11, the tree must categorize: comment volume,
    crash report, API key rate-limit, Bravoh server down.
    """
    section = _ship11_section(_doc_text())
    assert section, "§SHIP-11 section missing — can't pin triage tree."

    assert "### Triage decision tree" in section, (
        "§SHIP-11 missing '### Triage decision tree' H3."
    )

    missing_branches = [b for b in TRIAGE_BRANCHES if b not in section]
    assert not missing_branches, (
        "§SHIP-11 triage tree missing branch label(s): "
        + ", ".join(missing_branches)
    )


def test_ship11_monitoring_sources_enumerated() -> None:
    """Test 6: ### Monitoring signal sources H3 + ≥5 enumerated sources.

    The doc must list at least 5 numbered sources including the keywords
    in ``MONITORING_SOURCES_KEYWORDS``. Numbered items use the ``N.``
    markdown ordered-list convention.
    """
    section = _ship11_section(_doc_text())
    assert section, "§SHIP-11 section missing — can't pin monitoring block."

    assert "### Monitoring signal sources" in section, (
        "§SHIP-11 missing '### Monitoring signal sources' H3."
    )

    # Count ordered-list rows in the section (lines starting with N. ).
    numbered = re.findall(r"^\d+\.\s+", section, flags=re.MULTILINE)
    assert len(numbered) >= 5, (
        f"§SHIP-11 monitoring block expected ≥5 numbered sources; "
        f"found {len(numbered)}."
    )

    missing_kw = [
        kw for kw in MONITORING_SOURCES_KEYWORDS if kw not in section
    ]
    assert not missing_kw, (
        "§SHIP-11 monitoring sources missing keyword(s): "
        + ", ".join(missing_kw)
    )


def test_ship11_signoff_block_complete() -> None:
    """Test 7: Sign-off block has 6 SHIP-11 placeholder lines + Sign-off-by.

    Six placeholders: ENGINEERING GREEN + SHIFT 1..4 COMPLETE + T+24 HANDOFF
    + one final ``Sign-off by (Kaan):``.
    """
    section = _ship11_section(_doc_text())
    assert section, "§SHIP-11 section missing — can't pin sign-off block."

    ship11_lines = [ln for ln in section.splitlines() if "SHIP-11" in ln]
    placeholder_lines = [
        ln for ln in ship11_lines if "_____________" in ln or "____" in ln
    ]
    # Of those, count the ones that look like sign-off placeholders.
    signoff_placeholders = [
        ln
        for ln in placeholder_lines
        if ("ENGINEERING GREEN" in ln)
        or ("SHIFT" in ln and "COMPLETE" in ln)
        or ("T+24 HANDOFF" in ln)
    ]
    assert len(signoff_placeholders) >= 6, (
        f"§SHIP-11 sign-off block expected ≥6 placeholder lines "
        f"(ENGINEERING GREEN + 4 SHIFT COMPLETE + T+24 HANDOFF); "
        f"found {len(signoff_placeholders)}."
    )

    assert "Sign-off by (Kaan):" in section, (
        "§SHIP-11 sign-off block missing final 'Sign-off by (Kaan):' line."
    )


def test_ship11_section_appears_after_existing_references_h2() -> None:
    """Test 8: §SHIP-11 H2 appears AFTER the existing ## References H2.

    Append-only invariant: the v2.1 archive (ending at ``## References``)
    is never re-ordered. §SHIP-11 is the v3.0 successor and goes BELOW
    the existing References section.
    """
    text = _doc_text()
    refs_idx = text.find(EXISTING_REFERENCES_H2)
    ship11_idx = text.find(SHIP11_H2_PREFIX)
    assert refs_idx >= 0, "Phase 39 '## References' H2 missing — archive damaged."
    assert ship11_idx >= 0, "§SHIP-11 H2 missing."
    assert ship11_idx > refs_idx, (
        "§SHIP-11 H2 must appear AFTER the existing '## References' H2 "
        "(append-only invariant). "
        f"References @ char {refs_idx}, §SHIP-11 @ char {ship11_idx}."
    )


def test_ship11_section_ai_slop_clean() -> None:
    """Test 9: §SHIP-11 section text passes the AI-slop blocklist gate.

    Imports the canonical blocklist + deeply-regex from
    ``scripts/launch/check_no_ai_slop.py`` (single source of truth
    across the launch-check family) and applies them ONLY to the
    §SHIP-11 section. Token match is case-insensitive substring; the
    deeply-regex catches the ``deeply <word>`` adverb-construction
    slop class.

    Why we don't shell out to the CLI: ``check_no_ai_slop.py --dir``
    is launch-copy-directory scoped (the 5 social-channel files), not
    arbitrary-doc-scoped. Importing the constants gives us the
    canonical gate without inventing a new CLI surface.
    """
    section = _ship11_section(_doc_text())
    assert section, "§SHIP-11 section missing — can't run slop gate."
    section_lower = section.lower()

    slop_hits = [
        token for token in AI_SLOP_BLOCKLIST if token.lower() in section_lower
    ]
    assert not slop_hits, (
        "§SHIP-11 section contains AI-slop blocklist token(s): "
        + ", ".join(repr(t) for t in slop_hits)
    )

    deeply_hits = _DEEPLY_RE.findall(section)
    assert not deeply_hits, (
        "§SHIP-11 section contains 'deeply <word>' slop construction(s): "
        + ", ".join(repr(h) for h in deeply_hits)
    )
