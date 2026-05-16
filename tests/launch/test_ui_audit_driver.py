# SPDX-License-Identifier: Apache-2.0
"""Phase 43 / Plan 43-01 — UI audit driver contract tests.

REQ-IDs: VIS-01

Pins the Tier-1 surface allowlist + markdown-skeleton sanity guarantees
of `scripts/launch/run_ui_audit.py`. The driver MUST:

1. Expose exactly 4 Tier-1 surfaces — session / mascot-overlay / wizard /
   calibration (sourced from CONTEXT §VIS-01).
2. Refuse any surface outside that set with exit code 2 + a stderr listing
   the valid surfaces.
3. Emit a markdown skeleton with the canonical section headers per surface
   when invoked with `--dry-run` (default).
4. Be subprocess-free — no `gsd-ui-checker` / `gsd-ui-auditor` agent
   invocation during `--dry-run`; those run interactively from closure
   plans 43-02 / 43-03.
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

# Allow the test process to import the scripts.launch package without
# installing vibemix. Mirrors the precedent in tests/scripts/test_grey_area_log.py.
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from scripts.launch.run_ui_audit import (  # noqa: E402
    TIER1_SURFACES,
    main,
    write_audit_skeleton,
)


def test_tier1_surfaces_is_the_locked_set() -> None:
    """Test 1 — CONTEXT §VIS-01 fixes the Tier-1 allowlist to exactly 4 surfaces."""
    assert set(TIER1_SURFACES.keys()) == {
        "session",
        "mascot-overlay",
        "wizard",
        "calibration",
    }
    # Each entry MUST carry the closure-plan + entry-file pointers the
    # closure plans (43-02 / 43-03) consume.
    for surface, meta in TIER1_SURFACES.items():
        assert "dir" in meta, f"{surface} missing dir"
        assert "owner_plan" in meta, f"{surface} missing owner_plan"
        assert "entry" in meta, f"{surface} missing entry file"
        assert meta["owner_plan"] in {"43-02", "43-03"}, (
            f"{surface} owner_plan must be 43-02 or 43-03; got {meta['owner_plan']}"
        )


def test_write_audit_skeleton_emits_canonical_sections(tmp_path: Path) -> None:
    """Test 2 — skeleton writes UI-REVIEW-<surface>.md with the audit-loop sections."""
    written = write_audit_skeleton("session", phase_dir=tmp_path)
    assert written.name == "UI-REVIEW-session.md"
    assert written.parent == tmp_path
    text = written.read_text(encoding="utf-8")
    # Front-matter + canonical sections — Plan 43-02 grep-matches these.
    assert "## Surface: session" in text
    assert "### HIGH findings" in text
    assert "### MEDIUM findings" in text
    assert "### LOW findings" in text
    assert "### Audit Loop Log" in text
    # Methodology must reference the paired agent contract from CONTEXT §VIS-01.
    assert "gsd-ui-checker" in text
    assert "gsd-ui-auditor" in text


def test_main_rejects_unknown_surface(capsys: pytest.CaptureFixture[str]) -> None:
    """Test 3 — unknown surface exits 2 with stderr listing the 4 valid ones."""
    err_buf = io.StringIO()
    with redirect_stderr(err_buf):
        with pytest.raises(SystemExit) as excinfo:
            main(["--surface", "settings", "--dry-run"])
    assert excinfo.value.code == 2
    stderr_text = err_buf.getvalue().lower()
    assert "unknown surface" in stderr_text
    # The error MUST surface the full allowlist so the operator can self-correct.
    for valid in ("session", "mascot-overlay", "wizard", "calibration"):
        assert valid in stderr_text, f"stderr did not list valid surface '{valid}'"


def test_main_dry_run_writes_skeleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test 4 — --dry-run writes the markdown skeleton WITHOUT subprocessing agents.

    We assert no subprocess invocation by failing the test if anything tries
    to call subprocess.run / subprocess.Popen / os.system during the dry run.
    """
    import os
    import subprocess

    def _explode(*_a, **_kw):  # pragma: no cover - failure path
        raise AssertionError(
            "dry-run must not subprocess out — agents are invoked interactively"
            " by the closure plans (43-02 / 43-03)."
        )

    monkeypatch.setattr(subprocess, "run", _explode)
    monkeypatch.setattr(subprocess, "Popen", _explode)
    monkeypatch.setattr(os, "system", _explode)

    rc = main(
        ["--surface", "session", "--dry-run", "--phase-dir", str(tmp_path)]
    )
    assert rc == 0
    written = tmp_path / "UI-REVIEW-session.md"
    assert written.exists(), "dry-run did not write the skeleton"
    assert "## Surface: session" in written.read_text(encoding="utf-8")


def test_main_no_args_lists_surfaces_and_owners(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test 5 — `main([])` prints all 4 surfaces + owner plan and exits 0."""
    out_buf = io.StringIO()
    with redirect_stdout(out_buf):
        rc = main([])
    assert rc == 0
    stdout_text = out_buf.getvalue()
    for surface in ("session", "mascot-overlay", "wizard", "calibration"):
        assert surface in stdout_text, f"listing did not surface '{surface}'"
    # Owner plan IDs are part of the listing contract — Plan 43-01 done-criteria.
    assert "43-02" in stdout_text
    assert "43-03" in stdout_text
