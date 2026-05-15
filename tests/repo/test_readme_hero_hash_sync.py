# SPDX-License-Identifier: Apache-2.0
"""Phase 35 Plan 35-03 — README hero hash sync gate tests.

Pitfall P68: hero asset drift detection.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_readme_hero_hash.py"
REPO_README = REPO_ROOT / "README.md"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_readme_block(
    readme: Path,
    sha256: str,
    path: str,
    body: str = "<video src=\"docs/assets/demo.mp4\" controls></video>",
) -> None:
    readme.write_text(
        f"# test\n\n"
        f"<!-- vibemix:hero-start sha256={sha256} path={path} -->\n"
        f"{body}\n"
        f"<!-- vibemix:hero-end -->\n",
        encoding="utf-8",
    )


def test_repo_readme_passes_today() -> None:
    """The current real README must pass — drives Phase 35 ship readiness."""
    result = _run("--readme", str(REPO_README))
    assert result.returncode == 0, (
        f"current README hero block fails sync check.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


def test_placeholder_sentinel_passes(tmp_path: Path) -> None:
    """sha256=PLACEHOLDER means asset is pending Kaan-action — exit 0."""
    readme = tmp_path / "README.md"
    _write_readme_block(readme, "PLACEHOLDER", "docs/assets/demo.mp4")
    result = _run("--readme", str(readme), "--repo-root", str(tmp_path))
    assert result.returncode == 0
    assert "PLACEHOLDER" in result.stdout or "pending" in result.stdout


def test_drift_detected(tmp_path: Path) -> None:
    """README expects hash X, asset hashes Y -> exit 1 with both shown."""
    asset = tmp_path / "docs" / "assets" / "demo.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"hello world v1")
    wrong_hash = "0" * 64
    readme = tmp_path / "README.md"
    _write_readme_block(readme, wrong_hash, "docs/assets/demo.mp4")
    result = _run("--readme", str(readme), "--repo-root", str(tmp_path))
    assert result.returncode == 1
    assert "drift" in result.stderr.lower()
    assert wrong_hash in result.stderr
    actual = hashlib.sha256(b"hello world v1").hexdigest()
    assert actual in result.stderr


def test_asset_missing_with_real_hash_fails(tmp_path: Path) -> None:
    """Non-PLACEHOLDER hash + missing asset -> exit 1."""
    readme = tmp_path / "README.md"
    _write_readme_block(
        readme, "abc123" + "0" * 58, "docs/assets/demo.mp4"
    )
    result = _run("--readme", str(readme), "--repo-root", str(tmp_path))
    assert result.returncode == 1
    assert "does not exist" in result.stderr


def test_matching_hash_passes(tmp_path: Path) -> None:
    """Real hash + matching asset -> exit 0."""
    asset = tmp_path / "docs" / "assets" / "demo.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"some real bytes")
    real_hash = hashlib.sha256(b"some real bytes").hexdigest()
    readme = tmp_path / "README.md"
    _write_readme_block(readme, real_hash, "docs/assets/demo.mp4")
    result = _run("--readme", str(readme), "--repo-root", str(tmp_path))
    assert result.returncode == 0
    assert "matches" in result.stdout


def test_readme_with_no_hero_block_fails(tmp_path: Path) -> None:
    """Missing block -> exit 1 (so accidental removal is caught)."""
    readme = tmp_path / "README.md"
    readme.write_text("# test no hero\n", encoding="utf-8")
    result = _run("--readme", str(readme), "--repo-root", str(tmp_path))
    assert result.returncode == 1
    assert "no" in result.stderr.lower() and "hero" in result.stderr.lower()


def test_missing_attrs_fails(tmp_path: Path) -> None:
    """Comment with no sha256= attr -> exit 1."""
    readme = tmp_path / "README.md"
    readme.write_text(
        "# test\n<!-- vibemix:hero-start path=foo.mp4 -->\n",
        encoding="utf-8",
    )
    result = _run("--readme", str(readme), "--repo-root", str(tmp_path))
    assert result.returncode == 1
    assert "sha256" in result.stderr.lower() or "missing" in result.stderr.lower()


@pytest.mark.parametrize("variant", ["PLACEHOLDER", "placeholder"])
def test_placeholder_case_sensitivity(tmp_path: Path, variant: str) -> None:
    """Sentinel must be ALL-CAPS (avoid accidental match on the word
    'placeholder' in prose). Lowercase variant should NOT trigger the
    sentinel; it should be treated as a (very wrong) hash -> fail."""
    readme = tmp_path / "README.md"
    _write_readme_block(readme, variant, "docs/assets/demo.mp4")
    result = _run("--readme", str(readme), "--repo-root", str(tmp_path))
    if variant == "PLACEHOLDER":
        assert result.returncode == 0
    else:
        # Lowercase 'placeholder' is treated as a real (invalid) hash
        # + missing asset -> exit 1.
        assert result.returncode == 1
