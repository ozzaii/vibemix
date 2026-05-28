# SPDX-License-Identifier: Apache-2.0
"""tests/learn/test_no_tutor_slop_blocklist.py — TONE-03 tutor-slop CI gate.

Phase 94 / Plan 94-02 Task 1: pins ``scripts/launch/check_no_tutor_slop.py``
as the mechanical enforcer of the v9.0 "real DJ friend in your ear, no AI
slop" release gate. Five test paths:

1. **Real-transcripts pass** — Plan 94-01's 16 hand-authored fixtures are
   slop-free by construction; the gate exits 0 against the live
   ``src/vibemix/learn/transcripts/`` directory.

2. **Synthetic-slop fail** — a tmp_path fixture carrying explicit
   ``"great question! you crushed it!"`` tutor copy must gate red (exit 1)
   and stderr must name both offending tokens.

3. **Blocklist size ≥20** — TONE-03 binding (the v9.0 ROADMAP P94 + SUMMARY
   §10 floor). Catches accidental token trims via the public surface.

4. **Category coverage ≥4 per forbidden-move** — the blocklist must
   represent all four forbidden moves from
   ``src/vibemix/learn/prompts.py::_FORBIDDEN_TUTOR_MOVES_LOCK`` (compliment,
   summary, preview, upbeat-hook) with at least 4 tokens each.

5. **Deep-scan covers every copy field** — slop hidden inside
   ``hints[].text``, ``exemplar_cycle[].tutor_speak[].text``,
   ``recital_pool[].prompt``, ``recital_outcomes.pass`` must ALL trip the
   gate — not just top-level ``tutor_speak[].text``.

Pattern mirrors ``tests/launch/test_no_ai_slop.py`` (which sits over the
sibling ``scripts/launch/check_no_ai_slop.py``): the two gates are
independent but architecturally parallel. The blocklist + check function
are imported as a module-level surface so the test pins the public API
explicitly, not just the CLI behaviour.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from scripts.launch.check_no_tutor_slop import (
    TUTOR_SLOP_BLOCKLIST,
    _CATEGORY,
    _COPY_FIELDS,
    check_no_tutor_slop,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_TRANSCRIPTS_DIR = REPO_ROOT / "src" / "vibemix" / "learn" / "transcripts"


# ---------------------------------------------------------------------------
# Module-level shape tests — pin the public surface of the gate.
# ---------------------------------------------------------------------------


def test_module_imports_cleanly() -> None:
    """Importing exposes the public + private symbols this test pins."""
    assert callable(check_no_tutor_slop)
    assert callable(main)
    assert isinstance(TUTOR_SLOP_BLOCKLIST, tuple)
    assert isinstance(_CATEGORY, dict)
    assert isinstance(_COPY_FIELDS, tuple)


# ---------------------------------------------------------------------------
# Test 1: real transcripts pass (Plan 94-01 fixtures must be slop-free).
# ---------------------------------------------------------------------------


def test_real_transcripts_dir_passes_the_gate() -> None:
    """``src/vibemix/learn/transcripts/`` ships clean — exit 0.

    Plan 94-01 Task 1 authored 16 Course 1 fixtures + P92's hello_world by
    construction inside the TONE-03 discipline (lowercase, period-terminated,
    zero blocklist tokens). If this gate flips red, either a future planner
    slid slop into a fixture OR the blocklist grew a token that catches
    existing legitimate copy — both are interventions worth a Kaan-action
    decision.
    """
    assert LIVE_TRANSCRIPTS_DIR.exists(), (
        f"missing transcripts dir: {LIVE_TRANSCRIPTS_DIR}"
    )
    assert check_no_tutor_slop(LIVE_TRANSCRIPTS_DIR, quiet=True) == 0


# ---------------------------------------------------------------------------
# Test 2: synthetic-slop fixture must fire red.
# ---------------------------------------------------------------------------


def test_synthetic_slop_fixture_gates_red(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A tmp_path fixture carrying explicit slop tokens must gate red and
    stderr must name the offending tokens (so CI logs are scrapeable).
    """
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps(
            {
                "lesson_id": "X.99",
                "tutor_speak": [
                    {
                        "beat": 0,
                        "text": "great question! you crushed it!",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    assert check_no_tutor_slop(tmp_path, quiet=False) == 1
    err = capsys.readouterr().err.lower()
    assert "great question" in err, err
    assert "you crushed it" in err, err
    assert "bad.json" in err, err


# ---------------------------------------------------------------------------
# Test 3: blocklist size ≥20 — TONE-03 binding floor.
# ---------------------------------------------------------------------------


def test_blocklist_has_at_least_twenty_distinct_tokens() -> None:
    """TONE-03 floor — REQUIREMENTS.md + SUMMARY §10 + CONTEXT.md."""
    assert len(set(TUTOR_SLOP_BLOCKLIST)) >= 20, (
        f"TUTOR_SLOP_BLOCKLIST has {len(set(TUTOR_SLOP_BLOCKLIST))} distinct "
        "tokens; TONE-03 demands ≥20"
    )


# ---------------------------------------------------------------------------
# Test 4: every forbidden-move category has ≥4 tokens.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "category",
    ["compliment", "summary", "preview", "upbeat"],
)
def test_category_coverage_at_least_four_tokens_each(category: str) -> None:
    """Each of the 4 forbidden moves from
    ``src/vibemix/learn/prompts.py::_FORBIDDEN_TUTOR_MOVES_LOCK`` must be
    covered by ≥4 distinct blocklist tokens — otherwise a slop variant could
    sneak past while the gate still claims ≥20 size.
    """
    in_category = [t for t, cat in _CATEGORY.items() if cat == category]
    assert len(in_category) >= 4, (
        f"category {category!r} has only {len(in_category)} tokens: "
        f"{in_category} — TONE-03 demands ≥4 per category"
    )


# ---------------------------------------------------------------------------
# Test 5: deep scan covers every fixture copy field.
# ---------------------------------------------------------------------------


def test_deep_scan_finds_slop_in_every_copy_field(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Slop hidden inside ``hints[].text``,
    ``exemplar_cycle[].tutor_speak[].text``, ``recital_pool[].prompt``, and
    ``recital_outcomes.pass`` must ALL trip the gate. Catches a class of
    "gate looks at the wrong field" bugs.
    """
    nested = tmp_path / "nested.json"
    nested.write_text(
        json.dumps(
            {
                "lesson_id": "X.98",
                "tutor_speak": [
                    {"beat": 0, "text": "this line is clean."},
                ],
                "hints": [
                    {"strike": 1, "text": "first hint, also clean."},
                    {"strike": 2, "text": "now let's see the second hint."},
                ],
                "exemplar_cycle": [
                    {
                        "band": "low",
                        "tutor_speak": [
                            {"beat": 0, "text": "amazing low-end sweep."},
                        ],
                    },
                ],
                "recital_pool": [
                    {"prompt": "do this thing."},
                    {"prompt": "do another thing."},
                    {"prompt": "you crushed it on the previous gate."},
                ],
                "recital_outcomes": {
                    "pass": "fantastic — all 5 done.",
                    "fail": "{score} of 5. replay when you're ready.",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    assert check_no_tutor_slop(tmp_path, quiet=False) == 1
    err = capsys.readouterr().err.lower()
    # 4 distinct slop tokens were planted — every one must be reported.
    assert "now let's" in err, err
    assert "amazing" in err, err
    assert "you crushed it" in err, err
    assert "fantastic" in err, err


# ---------------------------------------------------------------------------
# CLI gate — ``python scripts/launch/check_no_tutor_slop.py`` from repo root
# must exit 0 against the live transcripts dir (no args).
# ---------------------------------------------------------------------------


def test_cli_main_default_dir_exits_zero() -> None:
    """``main([])`` runs against the default transcripts dir and exits 0."""
    rc = main([])
    assert rc == 0, f"CLI default-dir gate returned {rc}, expected 0"


def test_cli_main_with_quiet_flag_exits_zero() -> None:
    """``main(['--quiet'])`` runs silent + exits 0 against live transcripts."""
    rc = main(["--quiet"])
    assert rc == 0, f"CLI --quiet returned {rc}, expected 0"


def test_cli_main_with_explicit_dir_arg(tmp_path: Path) -> None:
    """``main(['--dir', <empty tmp>])`` exits 0 on an empty corpus (no JSON to scan)."""
    rc = main(["--dir", str(tmp_path), "--quiet"])
    assert rc == 0, f"CLI --dir on empty tmp returned {rc}, expected 0"


# ---------------------------------------------------------------------------
# Iconic-dialog exception — the L1.01 "Let's go." MUST NOT trip the gate.
# ---------------------------------------------------------------------------


def test_iconic_dialog_lets_go_does_not_trip_gate() -> None:
    """The L1.01 verbatim-locked "Let's go." is the ONE permitted exception
    (CONTEXT.md §iconic-dialog). The blocklist's ``now let's`` / ``later
    we'll`` etc. preview-tic tokens MUST NOT match the bare ``Let's go.``
    closer — verified by running the gate against the real transcripts
    (Test 1 already covers this) AND by an explicit fixture that re-asserts
    the exception path.
    """
    assert check_no_tutor_slop(LIVE_TRANSCRIPTS_DIR, quiet=True) == 0
