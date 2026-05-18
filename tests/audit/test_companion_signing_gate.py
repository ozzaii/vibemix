"""Behavioral tests for scripts/audit/check_companion_signing.sh.

Phase 49 Plan 02 — INSTALL-05 verifier gate behavior.

Tests cover:
  - Tag-build with unsigned artifact → exit non-zero
  - Branch-build with unsigned artifact → WARNING, exit 0
  - Signed file (sidecar .sig present) → exit 0
  - PLACEHOLDER_ SHA-256 in manifest → §INSTALL-COMPANION-SIGN warning
  - report.json shape
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "scripts" / "audit" / "check_companion_signing.sh"
COMPANION = ROOT / "installer" / "companion"


def _run_verifier(env_overrides: dict[str, str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        ["bash", str(VERIFIER)],
        env=env,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
    )


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Build a temp workspace mirroring the companion + verifier layout."""
    wd = tmp_path / "wd"
    (wd / "installer" / "companion").mkdir(parents=True)
    (wd / "scripts" / "audit").mkdir(parents=True)
    # Copy the verifier
    shutil.copy(VERIFIER, wd / "scripts" / "audit" / "check_companion_signing.sh")
    (wd / "scripts" / "audit" / "check_companion_signing.sh").chmod(0o755)
    # Stub a companion .sh file
    (wd / "installer" / "companion" / "fetch_drivers.sh").write_text("#!/bin/bash\necho stub\n")
    (wd / "installer" / "companion" / "audio_config.py").write_text("# stub\n")
    # Stub driver_manifest.json without placeholder
    (wd / "installer" / "companion" / "driver_manifest.json").write_text(
        json.dumps({"drivers": {"x": {"sha256": "deadbeef" * 8}}}, indent=2)
    )
    return wd


def test_branch_build_unsigned_exits_zero_with_warning(tmp_workspace: Path):
    """Branch build = WARNING but exit 0 (CI rehearsal mode)."""
    result = _run_verifier({"GITHUB_REF_TYPE": "branch"}, cwd=tmp_workspace)
    assert result.returncode == 0, f"branch build should exit 0\nstdout={result.stdout}\nstderr={result.stderr}"
    report = json.loads((tmp_workspace / "report-companion-signing.json").read_text())
    assert report["ref_type"] == "branch"
    assert report["exit_code"] == 0
    assert len(report["unsigned"]) >= 1  # both stub files unsigned


def test_tag_build_unsigned_exits_nonzero(tmp_workspace: Path):
    """Tag build = fail-on-unsigned."""
    result = _run_verifier({"GITHUB_REF_TYPE": "tag"}, cwd=tmp_workspace)
    assert result.returncode != 0, f"tag build with unsigned must fail\nstdout={result.stdout}\nstderr={result.stderr}"
    report = json.loads((tmp_workspace / "report-companion-signing.json").read_text())
    assert report["ref_type"] == "tag"
    assert report["exit_code"] != 0
    assert len(report["unsigned"]) >= 1


def test_signed_via_sidecar_exits_zero(tmp_workspace: Path):
    """Signed via sidecar .sig (Linux CI surrogate) → exit 0 on tag build."""
    # Create sidecar .sig for each companion script
    for f in (tmp_workspace / "installer" / "companion").iterdir():
        if f.suffix in {".sh", ".py", ".ps1"}:
            (f.parent / f"{f.name}.sig").write_text("FAKE-SIGNATURE\n")
    # Force the Linux CI branch (sidecar check)
    if sys.platform == "darwin":
        pytest.skip("Darwin uses codesign — sidecar test exercises Linux-CI branch only")
    result = _run_verifier({"GITHUB_REF_TYPE": "tag"}, cwd=tmp_workspace)
    assert result.returncode == 0, f"signed sidecar build should pass\nstdout={result.stdout}"
    report = json.loads((tmp_workspace / "report-companion-signing.json").read_text())
    assert len(report["signed"]) >= 1


def test_placeholder_sha_emits_kaan_action_warning(tmp_workspace: Path):
    """PLACEHOLDER_ in manifest → warning tagged §INSTALL-COMPANION-SIGN."""
    manifest = tmp_workspace / "installer" / "companion" / "driver_manifest.json"
    manifest.write_text(
        json.dumps({
            "drivers": {
                "blackhole_2ch": {"sha256": "PLACEHOLDER_SHA_TO_DISCHARGE_HERE"}
            }
        }, indent=2)
    )
    result = _run_verifier({"GITHUB_REF_TYPE": "branch"}, cwd=tmp_workspace)
    report = json.loads((tmp_workspace / "report-companion-signing.json").read_text())
    warnings_text = " ".join(report["warnings"])
    assert "INSTALL-COMPANION-SIGN" in warnings_text, f"expected §INSTALL-COMPANION-SIGN in warnings: {report['warnings']}"


def test_report_json_shape(tmp_workspace: Path):
    """report-companion-signing.json must have ref_type, signed, unsigned, warnings, exit_code."""
    _run_verifier({"GITHUB_REF_TYPE": "branch"}, cwd=tmp_workspace)
    report = json.loads((tmp_workspace / "report-companion-signing.json").read_text())
    for key in ("ref_type", "signed", "unsigned", "warnings", "exit_code"):
        assert key in report, f"report missing key: {key}"


def test_companion_dir_missing_exits_nonzero(tmp_path: Path):
    """If installer/companion/ is absent, verifier fails fast."""
    wd = tmp_path / "wd"
    wd.mkdir()
    (wd / "scripts" / "audit").mkdir(parents=True)
    shutil.copy(VERIFIER, wd / "scripts" / "audit" / "check_companion_signing.sh")
    (wd / "scripts" / "audit" / "check_companion_signing.sh").chmod(0o755)
    result = _run_verifier({"GITHUB_REF_TYPE": "branch"}, cwd=wd)
    assert result.returncode != 0, "missing companion dir must fail fast"
