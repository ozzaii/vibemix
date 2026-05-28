# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — TONE-04 binding.

The tutor system instruction MUST carry the four-forbidden-moves lock as
its LAST block (strongest recency for an LLM instruction). The four
forbidden tutor moves are:

1. NO complimenting the user ("Great question!", "Nice job!")
2. NO summarizing what just happened
3. NO previewing what's next
4. NO closing with an upbeat hook

These rules are the v9.0 "Lesson One" tone contract — the AI tutor is
proprioceptive scaffolding, not an edtech mascot. The runtime-side
``check_no_tutor_slop.py`` blocklist with ≥20 tokens lands in Plan 94;
this file pins the SYSTEM INSTRUCTION FIXTURE (the prompt that
discourages those moves up-front).

Two test functions — both gated on ``vibemix.learn.prompts``
importing successfully (Plan 92-03 lands that module).

REQ-ID: TONE-04.

Sampling: per-wave commit (~10 ms — single function call + 4 substring
asserts).
"""
from __future__ import annotations

import pytest

try:
    from vibemix.learn.prompts import build_tutor_system_instruction
except ImportError:
    pytest.skip(
        "tests/learn/test_tutor_system_instruction_lock.py awaits Plan "
        "92-03 (LESSON-05 build_tutor_system_instruction). When prompts.py "
        "lands, this module-level skip flips to live assertions.",
        allow_module_level=True,
    )


# The four forbidden-move tokens that MUST appear in the lock text. If a
# planner edits the lock's wording, update this list — these tokens ARE
# the gate. The lock string itself lives in ``learn/prompts.py`` as
# ``_FORBIDDEN_TUTOR_MOVES_LOCK``.
REQUIRED_LOCK_TOKENS: tuple[str, ...] = (
    "COMPLIMENT",        # rule 1 — no praise
    "SUMMARIZE",         # rule 2 — no rehash
    "PREVIEW",           # rule 3 — no "next we'll do X"
    "CLOSE with an upbeat hook",  # rule 4 — verbatim phrase
)


def test_tutor_system_instruction_includes_all_four_locks() -> None:
    """``build_tutor_system_instruction(...)`` MUST emit a string carrying
    all 4 REQUIRED_LOCK_TOKENS. Missing any one → TONE-04 violation."""
    instruction = build_tutor_system_instruction(
        course_id="course_0",
        lesson_id="L0.00-press-play",
        controller_id="pioneer_ddj_flx4",
    )
    assert isinstance(instruction, str) and instruction, (
        "build_tutor_system_instruction returned non-string or empty"
    )
    for token in REQUIRED_LOCK_TOKENS:
        assert token in instruction, (
            f"TONE-04 violation: {token!r} missing from tutor system "
            "instruction. The four-forbidden-moves lock has drifted; "
            "either the lock string was edited or a planner removed a "
            "rule — restore the missing rule before merging."
        )


def test_lock_is_last_block_for_strongest_recency() -> None:
    """The lock must appear AFTER the COURSE_FRAMES / controller /
    addendum frames. LLMs weight the END of a system instruction more
    heavily (the COACH_CLOSING_BLOCK pattern from v8.1 LENS-03)."""
    instruction = build_tutor_system_instruction(
        course_id="course_0",
        lesson_id="L0.00-press-play",
        controller_id="pioneer_ddj_flx4",
    )
    # The fixture per Plan 92-03's curriculum.py marks the addendum with
    # "HELLO WORLD ADDENDUM" (see 92-RESEARCH §Code Example 4).
    addendum_idx = instruction.find("HELLO WORLD ADDENDUM")
    assert addendum_idx >= 0, (
        "addendum sentinel ``HELLO WORLD ADDENDUM`` not found — Plan "
        "92-03 curriculum.py L0.00-press-play addendum must contain "
        "that substring as the locator anchor for this gate."
    )
    # The lock starts with a known sentinel; we look for any of the four
    # required tokens AFTER the addendum frame (the strongest assertion
    # we can make without coupling to the exact lock heading wording).
    for token in REQUIRED_LOCK_TOKENS:
        token_idx = instruction.find(token)
        assert token_idx > addendum_idx, (
            f"TONE-04 / recency violation: lock token {token!r} appears "
            f"at idx {token_idx}, before the addendum at idx "
            f"{addendum_idx}. The four-forbidden-moves lock MUST come "
            "LAST in the system instruction (strongest recency)."
        )
