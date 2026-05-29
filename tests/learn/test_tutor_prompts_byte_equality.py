# SPDX-License-Identifier: Apache-2.0
"""tests/learn/test_tutor_prompts_byte_equality.py — TONE-01 iconic dialog lock.

Phase 94 / Plan 94-02 Task 2: pins the 4-line opening dialog in
``src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json``
(``tutor_speak[0..3].text``) to a verbatim source-of-truth tuple. CI red
on any single-character drift — whitespace, capitalization,
smart-quote / curly-quote substitution, lost period, extra space.

The 4-line dialog IS the v9.0 brand surface (per CONTEXT.md §iconic-dialog
+ REQUIREMENTS.md TONE-01 + STATE.md "Pre-Milestone Direction"). Drift is
a brand-defacement vector — a future planner / self-improving agent
"cleaning up" the wording silently changes Kaan's product brand.

Changing any of these 4 strings requires Kaan-action ratification (see
the in-file note above ``_ICONIC_DIALOG_LINES``). The test pins both the
single source of truth in this file AND the fixture-side string; drift in
EITHER direction surfaces as a red CI test with an actionable failure
message.

The "Let's go." closer in line 4 is the ONE permitted exclamation-equivalent
in v9.0 — the preview-tic blocklist in ``check_no_tutor_slop.py`` is
designed with multi-word tokens specifically so this exception path does
not require a special-case skip.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# THE LOCK. CHANGING ANY OF THESE 4 STRINGS REQUIRES KAAN-ACTION
# RATIFICATION. The 4-line opening dialog is the v9.0 brand surface.
# Sources of truth in declining priority:
#   1. .planning/REQUIREMENTS.md TONE-01
#   2. .planning/STATE.md "Pre-Milestone Direction"
#   3. .planning/phases/94-course-1-anatomy/94-CONTEXT.md §iconic-dialog
# Any divergence between this tuple and a higher-priority source above
# is a bug in this file — restore from the higher-priority source.
# ---------------------------------------------------------------------------

_ICONIC_DIALOG_LINES: tuple[str, ...] = (
    "Hello vibemix, what are you?",
    "I'm the best DJ app in the world.",
    "If you are the best, then who the fuck am I?",
    "Oh bestie, don't worry. You know why? "
    "Because I'm the beginner module of vibemix. Let's go.",
)

_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_L1_01_FIXTURE: Path = (
    _REPO_ROOT
    / "src" / "vibemix" / "learn" / "transcripts"
    / "course_1_anatomy" / "01_welcome.json"
)


# ---------------------------------------------------------------------------
# Existence + parseability — guard the fixture itself before pinning text.
# ---------------------------------------------------------------------------


def test_l1_01_fixture_exists() -> None:
    """L1.01 carries the iconic 4-line opening dialog. Plan 94-01 Task 1
    landed this file; if it disappears, surface that loudly here rather
    than letting the byte-equality test fail with a confusing JSONDecodeError.
    """
    assert _L1_01_FIXTURE.exists(), (
        f"missing fixture: {_L1_01_FIXTURE} — Plan 94-01 Task 1 should "
        "have landed this file; check the iconic-dialog fixture was not "
        "deleted or renamed."
    )


def test_l1_01_parses_as_json() -> None:
    """The fixture file is valid JSON (gates a corrupt-write regression
    separately from the byte-equality content gate)."""
    json.loads(_L1_01_FIXTURE.read_text(encoding="utf-8"))


def test_l1_01_tutor_speak_has_four_beats() -> None:
    """The iconic dialog is exactly 4 lines — the L1.01 fixture must carry
    at least 4 tutor_speak entries (>= so a future planner may add a 5th
    'tap to continue' silent beat without breaking the lock; the 4
    iconic lines remain pinned by index)."""
    data = json.loads(_L1_01_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(data.get("tutor_speak"), list), (
        "L1.01 tutor_speak must be a JSON array of beat dicts"
    )
    assert len(data["tutor_speak"]) >= 4, (
        f"iconic dialog has 4 lines; L1.01 has only "
        f"{len(data['tutor_speak'])} tutor_speak entries"
    )


def test_iconic_dialog_lines_tuple_has_four_entries() -> None:
    """Sanity gate on the in-file source of truth — if a future editor
    accidentally trims the tuple while updating one line, this test red.
    """
    assert len(_ICONIC_DIALOG_LINES) == 4, (
        f"_ICONIC_DIALOG_LINES must be exactly 4 entries; got "
        f"{len(_ICONIC_DIALOG_LINES)} — restore from REQUIREMENTS.md TONE-01"
    )


# ---------------------------------------------------------------------------
# THE LOCK — byte-equality between the L1.01 fixture and the in-file tuple.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "idx,expected",
    list(enumerate(_ICONIC_DIALOG_LINES)),
    ids=["L1.01.beat0", "L1.01.beat1", "L1.01.beat2", "L1.01.beat3"],
)
def test_l1_01_line_byte_equal(idx: int, expected: str) -> None:
    """TONE-01 binding. CI red on ANY single-character drift — whitespace,
    capitalization, smart-quote / curly-quote substitution, lost period,
    extra space, lost contraction apostrophe.

    Failure message includes both the expected and actual ``repr()`` so
    the offending character is obvious (e.g. ``'\\u2018'`` vs ``"'"``).
    """
    data = json.loads(_L1_01_FIXTURE.read_text(encoding="utf-8"))
    actual = data["tutor_speak"][idx]["text"]
    assert actual == expected, (
        f"TONE-01 byte-equality violation at L1.01 beat {idx}.\n"
        f"  expected: {expected!r}\n"
        f"  actual:   {actual!r}\n"
        f"The iconic 4-line opening dialog is verbatim-locked. Changing "
        f"any character requires Kaan-action ratification and an update "
        f"to _ICONIC_DIALOG_LINES at the top of this file. Until then, "
        f"restore the original wording in the L1.01 fixture."
    )


# ---------------------------------------------------------------------------
# Self-consistency — the iconic 4th line ends in "Let's go." and only the
# 4th line carries the closer (anti-creep gate so a future planner doesn't
# accidentally let the closer leak into a different line).
# ---------------------------------------------------------------------------


def test_iconic_closer_is_only_on_beat_3() -> None:
    """``Let's go.`` is the v9.0-permitted closer — it must appear only on
    line 4, and nowhere else in L1.01's tutor_speak. Guards against a
    self-improving agent "fixing" the dialog by spreading the closer."""
    data = json.loads(_L1_01_FIXTURE.read_text(encoding="utf-8"))
    beats = [b["text"] for b in data["tutor_speak"][:4]]
    closer = "Let's go."
    assert closer in beats[3], f"line 4 must end with {closer!r}"
    for i in (0, 1, 2):
        assert closer not in beats[i], (
            f"line {i} must NOT contain the closer {closer!r}; "
            f"got {beats[i]!r}"
        )


def test_iconic_dialog_uses_straight_apostrophes_not_curly() -> None:
    """The fixture must use ASCII apostrophe ``'`` (U+0027), not curly
    ``’`` (U+2019). An auto-formatter ("smart quotes") silently converting
    one to the other is the single most likely drift vector — pin it
    explicitly here so the error message is clear when (not if) it happens.
    """
    data = json.loads(_L1_01_FIXTURE.read_text(encoding="utf-8"))
    for idx, _expected in enumerate(_ICONIC_DIALOG_LINES):
        actual = data["tutor_speak"][idx]["text"]
        assert "‘" not in actual, (
            f"line {idx} contains a curly opening single quote (U+2018) — "
            f"fixture must use ASCII U+0027; got {actual!r}"
        )
        assert "’" not in actual, (
            f"line {idx} contains a curly closing single quote (U+2019) — "
            f"fixture must use ASCII U+0027; got {actual!r}"
        )
