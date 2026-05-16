# SPDX-License-Identifier: Apache-2.0
"""Plan 40-03 Task 1 — Part-aware prompt suffix builder unit tests.

Pins the locked CONTEXT.md decisions Q1 (3-Part additive contract) + Q2
("NOT YET HEARD BY AUDIENCE" explicit labeling) + AUDIO-04 requirement.

The builder returns one of 4 deterministic strings keyed by the boolean
permutations of (has_mic_part, has_lookahead_part):

  (False, False) → 1-Part baseline (no mic, no future).
  (False, True)  → P1 mix + P2 lookahead (lookahead occupies the P2 slot
                    when no mic is in the way — contiguous slot numbering
                    keeps the label semantics tight per CONTEXT Q2).
  (True,  False) → P1 mix + P2 mic.
  (True,  True)  → P1 mix + P2 mic + P3 lookahead.

The lookahead-present variants MUST contain the literal
"NOT YET HEARD BY AUDIENCE" substring AND an anti-prediction phrase
matching the pattern "do NOT describe Part [23] as if it has played".

All variants end with the v4 anti-slop refrain
"Your ears are the referee — the evidence above is grounded context."
(carried over from the Plan 40-01 prompt-suffix wording).

Reference: 40-03-PLAN.md `<interfaces>` block lines 122-127 (locked strings).
"""

from __future__ import annotations

import re

from vibemix.prompts.matrix import build_parts_description


# ---------------------------------------------------------------------------
# 4 scenarios — one per boolean permutation of (has_mic_part, has_lookahead_part).
# ---------------------------------------------------------------------------


def test_1_part_baseline() -> None:
    """has_mic_part=False, has_lookahead_part=False → 1-Part baseline.

    Suffix contains "P1 =" only. Must NOT mention P2, P3, or any
    "NOT YET HEARD" labeling (no lookahead Part present).
    """
    out = build_parts_description(7, False, False)
    assert "P1 =" in out
    assert "P2" not in out
    assert "P3" not in out
    assert "NOT YET HEARD" not in out
    # v4 anti-slop refrain preserved.
    assert "Your ears are the referee" in out


def test_lookahead_only_at_p2() -> None:
    """has_mic_part=False, has_lookahead_part=True → 1-Part + lookahead.

    Lookahead occupies the P2 slot (not P3) when no mic is in the way —
    keeps the label semantics tight per CONTEXT Q2 (contiguous slot
    numbering). The "NOT YET HEARD BY AUDIENCE" label MUST be present.
    """
    out = build_parts_description(7, False, True)
    assert "P1 =" in out
    assert "P2 =" in out
    assert "P3" not in out
    assert "NOT YET HEARD BY AUDIENCE" in out
    # Anti-prediction guard language applies to whichever slot
    # lookahead lands in (P2 in this scenario).
    assert re.search(r"do NOT describe Part 2 as if it has played", out)


def test_mic_only_at_p2() -> None:
    """has_mic_part=True, has_lookahead_part=False → 2-Part (mic).

    Mic labeled P2; no P3; no "NOT YET HEARD" (no lookahead present).
    """
    out = build_parts_description(7, True, False)
    assert "P1 =" in out
    assert "P2 =" in out
    assert "P3" not in out
    assert "NOT YET HEARD" not in out
    # Mic-specific phrasing — "mic" + "your voice as Kaan".
    assert "mic" in out.lower()


def test_full_3part() -> None:
    """has_mic_part=True, has_lookahead_part=True → 3-Part full contract.

    P1 mix + P2 mic + P3 lookahead. Lookahead labeled "P3 =" with the
    explicit "NOT YET HEARD BY AUDIENCE" label AND the anti-prediction
    guard "do NOT describe Part 3 as if it has played".
    """
    out = build_parts_description(7, True, True)
    assert "P1 =" in out
    assert "P2 =" in out
    assert "P3 =" in out
    assert "NOT YET HEARD BY AUDIENCE" in out
    assert re.search(r"do NOT describe Part 3 as if it has played", out)


# ---------------------------------------------------------------------------
# Anti-prediction phrase pin (T-40-03-01 mitigation gate).
# ---------------------------------------------------------------------------


def test_anti_prediction_phrase_in_lookahead_variants() -> None:
    """Both lookahead-present variants contain
    "do NOT describe Part [23] as if it has played" — the load-bearing
    anti-prediction guard locked by CONTEXT Q2 + threat-register entry
    T-40-03-01.
    """
    pattern = re.compile(r"do NOT describe Part [23] as if it has played")
    out_lookahead_only = build_parts_description(7, False, True)
    out_full_3part = build_parts_description(7, True, True)
    assert pattern.search(out_lookahead_only), (
        f"anti-prediction phrase missing from lookahead-only variant: {out_lookahead_only!r}"
    )
    assert pattern.search(out_full_3part), (
        f"anti-prediction phrase missing from 3-Part variant: {out_full_3part!r}"
    )


# ---------------------------------------------------------------------------
# v4 anti-slop refrain pin (carry-over from Plan 40-01).
# ---------------------------------------------------------------------------


def test_ears_are_the_referee_in_all_variants() -> None:
    """All 4 variants end with "Your ears are the referee — the evidence
    above is grounded context." — the v4 anti-slop refrain preserved from
    Plan 40-01's prompt-suffix wording.
    """
    refrain = (
        "Your ears are the referee — the evidence above is grounded context."
    )
    for has_mic, has_look in [(False, False), (False, True), (True, False), (True, True)]:
        out = build_parts_description(7, has_mic, has_look)
        assert out.rstrip().endswith(refrain), (
            f"variant (mic={has_mic}, look={has_look}) missing refrain: ...{out[-100:]!r}"
        )
