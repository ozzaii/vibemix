# SPDX-License-Identifier: Apache-2.0
"""Plan 20-02 — locks for IM_LISTENING_FRAGMENT + FAIL_SOFT_EXAMPLES.

Pins the prompt-side mitigation copy + anti-prompt-injection invariant. The
fragment is a fixed module constant; these tests guarantee:
- canonical anchor phrase is present (paraphrase-detection),
- section header matches Phase 18 convention (downstream grep audits),
- length sanity (catches accidental blanking),
- no template-syntax characters (anti-prompt-injection — T-20-02-01),
- the FAIL_SOFT_EXAMPLES tuple is shape-locked + subset of the fragment body
  (Plan 20-03 replay harness reads the tuple to recognize fail-soft replies).

All imports go via the package boundary (``vibemix.coach``) so the re-export
contract is part of the lock.
"""

from __future__ import annotations

from vibemix.coach import FAIL_SOFT_EXAMPLES, IM_LISTENING_FRAGMENT


def test_im_listening_fragment_contains_locked_phrase() -> None:
    """Canonical anchor — paraphrasing the rule must break the test."""
    assert "I'm listening" in IM_LISTENING_FRAGMENT


def test_im_listening_fragment_starts_with_section_header() -> None:
    """Phase 18 section-header convention — required for downstream grep audits."""
    assert "FAIL-SOFT RULE (live mode)" in IM_LISTENING_FRAGMENT


def test_im_listening_fragment_is_str() -> None:
    """Sanity bound — the fragment is ~700 chars; <100 means it got blanked."""
    assert isinstance(IM_LISTENING_FRAGMENT, str)
    assert len(IM_LISTENING_FRAGMENT) > 100


def test_im_listening_fragment_no_user_input_interpolation() -> None:
    """Anti-prompt-injection (T-20-02-01) — no template syntax, no shell substitution.

    Mirrors T-13-05-06 (MOOD_PERSONAS) + T-18-03-01 (CITATION_GRAMMAR_BLOCK)
    invariant: a fixed string constant cannot embed runtime input.
    """
    assert "{" not in IM_LISTENING_FRAGMENT
    assert "%" not in IM_LISTENING_FRAGMENT
    assert "$" not in IM_LISTENING_FRAGMENT


def test_fail_soft_examples_tuple() -> None:
    """Shape lock for FAIL_SOFT_EXAMPLES — tuple of 4 strs, includes canonical line."""
    assert isinstance(FAIL_SOFT_EXAMPLES, tuple)
    assert len(FAIL_SOFT_EXAMPLES) == 4
    assert all(isinstance(p, str) for p in FAIL_SOFT_EXAMPLES)
    assert "I'm listening." in FAIL_SOFT_EXAMPLES


def test_fail_soft_examples_subset_of_fragment() -> None:
    """Plan 20-03 harness reads FAIL_SOFT_EXAMPLES to recognize fail-soft replies.

    Each example MUST also live inside IM_LISTENING_FRAGMENT — keeps the
    machine-readable surface in lock-step with the prompt body Gemini sees.
    """
    for example in FAIL_SOFT_EXAMPLES:
        assert example in IM_LISTENING_FRAGMENT, (
            f"FAIL_SOFT_EXAMPLES drift: {example!r} not in IM_LISTENING_FRAGMENT"
        )
