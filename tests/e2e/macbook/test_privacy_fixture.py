"""Phase 50 — self-test for the _privacy_guard fixture.

Confirms the fixture fires when the harness writes to off-limits paths AND
passes on a clean run. Uses the ``VIBEMIX_E2E_OFF_LIMITS_ROOTS`` env override
so real off-limits paths are never touched.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _run_pytest(workdir: Path, off_limits_roots: list[Path], inner_test: str) -> subprocess.CompletedProcess:
    """Run pytest inside ``workdir`` with the off-limits override pointed at
    test-owned dirs; ``inner_test`` is the test file path relative to workdir.
    """
    env = os.environ.copy()
    env["VIBEMIX_E2E_OFF_LIMITS_ROOTS"] = os.pathsep.join(str(r) for r in off_limits_roots)
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[3])
    return subprocess.run(
        [sys.executable, "-m", "pytest", inner_test, "-q", "--tb=short"],
        cwd=str(workdir),
        env=env,
        capture_output=True,
        text=True,
    )


def test_privacy_guard_fires_on_offlimits_write(tmp_path: Path) -> None:
    """Synthesize a test that intentionally writes to a fake off-limits root;
    the session-autouse _privacy_guard fixture must fail the session.
    """
    fake_root = tmp_path / "fake-hermes"
    fake_root.mkdir()

    test_file = tmp_path / "test_offender.py"
    test_file.write_text(
        f"""
from pathlib import Path
def test_writes_to_off_limits():
    p = Path({str(fake_root)!r}) / "leak.txt"
    p.write_text("oops")
"""
    )
    # Copy conftest sibling so fixture loads in tmp_path.
    conftest_src = Path(__file__).resolve().parent / "conftest.py"
    (tmp_path / "conftest.py").write_text(conftest_src.read_text())

    proc = _run_pytest(tmp_path, [fake_root], "test_offender.py")
    assert proc.returncode != 0, f"_privacy_guard did not fail on off-limits write:\n{proc.stdout}\n{proc.stderr}"
    combined = proc.stdout + proc.stderr
    assert "off-limits" in combined or "privacy" in combined.lower(), combined


def test_privacy_guard_passes_on_clean_run(tmp_path: Path) -> None:
    """Clean run that does NOT write to any off-limits root — fixture passes."""
    fake_root = tmp_path / "untouched-hermes"
    fake_root.mkdir()

    test_file = tmp_path / "test_clean.py"
    test_file.write_text(
        """
def test_no_writes():
    assert 1 + 1 == 2
"""
    )
    conftest_src = Path(__file__).resolve().parent / "conftest.py"
    (tmp_path / "conftest.py").write_text(conftest_src.read_text())

    proc = _run_pytest(tmp_path, [fake_root], "test_clean.py")
    assert proc.returncode == 0, f"_privacy_guard fired on a clean run:\n{proc.stdout}\n{proc.stderr}"
