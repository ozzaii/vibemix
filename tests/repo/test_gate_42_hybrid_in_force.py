# SPDX-License-Identifier: Apache-2.0
"""Phase 42 / Plan 42-05 — v3.0 hybrid hallucination-gate in force.

REQ-IDs: GATE-08
Decision Log: .planning/decisions/P85-OVERRIDE-RETIRED.md

This test is the v3.0 replacement for the deleted
`tests/repo/test_phase_16_override_expiry.py`. The previous test asserted that
the v2.1 P85 override expiry-clock reminders were live on every release cut.
The override is formally retired (per Plan 42-05 Decision Log entry) and the
hybrid gate replaces it.

This test pins the hybrid gate IS in force by asserting (positively):

1. `cut_release.sh` invokes `check_gate.sh` at its Gate 2b slot.
2. `check_gate.sh` reads the nightly canary scorecards from
   `.planning/eval-runs/` and invokes the ear-test gate `check_ear_test.sh`.
3. No `OVERRIDE_*` constants survive anywhere in `scripts/release/` or
   `scripts/launch/`.
4. No `[P85]` / `Phase 16 override cleanup reminder` echo lines remain on the
   success path of `cut_release.sh`.
5. `cut_release.sh` success-path references `[GATE-06]` (the v3.0 replacement
   reminder slot — see Plan 42-04).
6. The Decision Log entry exists and cites P85 + RETIRED + the wiring scripts.
7. `STATE.md` Phase 16 line is annotated RETIRED with cross-reference path.
8. The expiry test file is verifiably gone (load-bearing — catches future
   revert).
9. `check_gate.sh` is executable on disk.

Grep hygiene (load-bearing per Plan 42-05): every grep is scoped to a specific
file PATH constant declared at module top — never globbed recursively into the
test file body — so the tokens that legitimately appear in this docstring
(`[P85]`, `Phase 16 override`, `OVERRIDE_`) do not self-invalidate the tests.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CUT_RELEASE = REPO_ROOT / "scripts" / "launch" / "cut_release.sh"
CHECK_GATE = REPO_ROOT / "scripts" / "release" / "check_gate.sh"
CHECK_EAR_TEST = REPO_ROOT / "scripts" / "release" / "check_ear_test.sh"
DECISION_FILE = REPO_ROOT / ".planning" / "decisions" / "P85-OVERRIDE-RETIRED.md"
STATE_MD = REPO_ROOT / ".planning" / "STATE.md"
EXPIRY_TEST = REPO_ROOT / "tests" / "repo" / "test_phase_16_override_expiry.py"


# ───────────────────────────────────────────────────────────────────────────
# Gate-wiring contract (Plan 42-04 surface)
# ───────────────────────────────────────────────────────────────────────────


def test_cut_release_invokes_check_gate_at_gate_2b():
    """cut_release.sh must have a `[Gate 2b]` slot that invokes check_gate.sh."""
    body = CUT_RELEASE.read_text(encoding="utf-8")
    assert "[Gate 2b]" in body, (
        "cut_release.sh missing '[Gate 2b]' marker — hybrid gate "
        "(GATE-06 / Plan 42-04) not wired"
    )
    assert "check_gate.sh" in body, (
        "cut_release.sh does not invoke check_gate.sh — hybrid gate "
        "(GATE-06 / Plan 42-04) not wired"
    )


def test_check_gate_reads_nightly_eval_runs():
    """check_gate.sh must read the nightly canary output directory."""
    body = CHECK_GATE.read_text(encoding="utf-8")
    assert ".planning/eval-runs" in body, (
        "check_gate.sh does not reference .planning/eval-runs — nightly "
        "canary read path missing (GATE-06)"
    )


def test_check_gate_invokes_ear_test_gate():
    """check_gate.sh must invoke check_ear_test.sh (the ear-test slow lane)."""
    body = CHECK_GATE.read_text(encoding="utf-8")
    assert "check_ear_test.sh" in body, (
        "check_gate.sh does not invoke check_ear_test.sh — ear-test gate "
        "(GATE-05 / Plan 42-03) not chained into the hybrid gate (GATE-06)"
    )


def test_check_gate_sh_is_executable():
    """check_gate.sh must have the executable bit set so cut_release.sh's
    `bash check_gate.sh` invocation does not fall back to a no-op."""
    assert CHECK_GATE.exists(), f"{CHECK_GATE} missing"
    assert os.access(CHECK_GATE, os.X_OK), (
        f"{CHECK_GATE} is not executable — chmod +x required"
    )


# ───────────────────────────────────────────────────────────────────────────
# Override-residue contract (no OVERRIDE_* survives in release scripts)
# ───────────────────────────────────────────────────────────────────────────


def _scoped_release_shell_scripts() -> list[Path]:
    """Return only the .sh files under scripts/launch/ and scripts/release/.
    Scoped to prevent globbing into the test file itself."""
    launch = sorted((REPO_ROOT / "scripts" / "launch").glob("*.sh"))
    release = sorted((REPO_ROOT / "scripts" / "release").glob("*.sh"))
    return launch + release


def test_no_override_constants_remain_in_release_scripts():
    """No `OVERRIDE_` / `OVERRIDE =` / `OVERRIDE:` constants on non-comment
    lines in any release / launch shell script. Comments are exempt — the
    test docstring of this file legitimately mentions `OVERRIDE_*`."""
    offenders: list[tuple[str, int, str]] = []
    forbidden_patterns = ("OVERRIDE_", "OVERRIDE =", "OVERRIDE:")
    for script in _scoped_release_shell_scripts():
        for line_no, line in enumerate(script.read_text(encoding="utf-8").splitlines(), start=1):
            # Skip comment-only lines (leading whitespace + `#`)
            if re.match(r"^\s*#", line):
                continue
            for pat in forbidden_patterns:
                if pat in line:
                    offenders.append((str(script.relative_to(REPO_ROOT)), line_no, line.strip()))
                    break
    assert not offenders, (
        "Override constants leaked back into release scripts (P85 retired in "
        f"Plan 42-05): {offenders}"
    )


def test_no_p85_reminder_in_cut_release_echo_lines():
    """cut_release.sh's success-path `echo` lines must not carry the v2.1 P85
    reminder anymore. Comment lines (header docstring etc.) are exempt — the
    intent is that no user-visible output references the retired override."""
    body = CUT_RELEASE.read_text(encoding="utf-8")
    forbidden_in_echo = (
        "[P85]",
        "Phase 16 override cleanup reminder",
        "Phase 16 ear-test memory override",
    )
    offenders: list[tuple[int, str]] = []
    for line_no, line in enumerate(body.splitlines(), start=1):
        stripped = line.lstrip()
        # Only inspect echo lines (the user-visible output surface).
        if not stripped.startswith('echo "'):
            continue
        for forbidden in forbidden_in_echo:
            if forbidden in line:
                offenders.append((line_no, line.strip()))
                break
    assert not offenders, (
        "cut_release.sh still emits v2.1 P85 reminder lines on the success "
        f"path (must be retired in Plan 42-04): {offenders}"
    )


def test_cut_release_success_path_references_gate_06():
    """The v3.0 success-path replacement reminder slot is GATE-06 (per Plan
    42-04). Verify it appears in cut_release.sh's body AFTER the
    'ALL GATES PASS' marker (i.e. in the success block, not a header
    comment)."""
    body = CUT_RELEASE.read_text(encoding="utf-8")
    pass_idx = body.find("ALL GATES PASS")
    assert pass_idx != -1, (
        "cut_release.sh missing 'ALL GATES PASS' marker — success-block "
        "structure changed"
    )
    gate_06_idx = body.find("[GATE-06]", pass_idx)
    assert gate_06_idx != -1 and gate_06_idx >= pass_idx, (
        "cut_release.sh success-path does not reference [GATE-06] after "
        "'ALL GATES PASS' — Plan 42-04 reminder-slot replacement missing"
    )


# ───────────────────────────────────────────────────────────────────────────
# Decision-log + STATE.md cross-reference contract (Plan 42-05 Task 1)
# ───────────────────────────────────────────────────────────────────────────


def test_decision_log_entry_exists_and_cites_p85():
    """The Decision Log entry retiring the override must exist and reference
    P85 + RETIRED + the wiring scripts."""
    assert DECISION_FILE.exists(), f"{DECISION_FILE} missing"
    body = DECISION_FILE.read_text(encoding="utf-8")
    for token in ("P85", "RETIRED", "check_gate.sh", "check_ear_test.sh"):
        assert token in body, (
            f"Decision Log entry missing required token '{token}' — see "
            "Plan 42-05 must_haves"
        )


def test_state_md_phase_16_line_is_annotated_retired():
    """STATE.md must retain the Phase 16 override line for audit trail and
    annotate it RETIRED with a cross-reference to the Decision Log entry."""
    body = STATE_MD.read_text(encoding="utf-8")
    # Locate the line that still references the override (annotated form).
    phase_16_lines = [
        line for line in body.splitlines()
        if "Phase 16 ear-test memory override" in line
    ]
    assert phase_16_lines, (
        "STATE.md no longer contains a 'Phase 16 ear-test memory override' "
        "line — audit trail lost; Plan 42-05 spec was annotate-not-delete"
    )
    # At least one such line must contain RETIRED (annotation present).
    assert any("RETIRED" in line for line in phase_16_lines), (
        "STATE.md Phase 16 override line is not annotated RETIRED — "
        "Plan 42-05 Task 1 annotation missing"
    )
    # The file must cross-reference the Decision Log entry by relative path.
    assert "P85-OVERRIDE-RETIRED.md" in body, (
        "STATE.md missing cross-reference to .planning/decisions/"
        "P85-OVERRIDE-RETIRED.md — Plan 42-05 Task 1 cross-reference missing"
    )


def test_expiry_test_file_actually_deleted():
    """The v2.1 expiry-clock test file is gone. Load-bearing: catches a
    future revert that resurrects the override."""
    assert not EXPIRY_TEST.exists(), (
        f"{EXPIRY_TEST} reappeared — the v2.1 P85 override expiry-clock "
        "test was deleted in Plan 42-05; a revert would resurrect a stale "
        "contract that no longer matches the v3.0 hybrid gate. Investigate."
    )
