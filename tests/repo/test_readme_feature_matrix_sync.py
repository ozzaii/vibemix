# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-02 — README feature matrix sync gate.

REQ-IDs: SHIP-02
Pitfall: P68 (README drift detection).

Asserts:
- README.md has both AUTO-GEN feature-matrix markers.
- Running `sync_feature_matrix.py --check` produces no drift (CI gate).
- Every v2.1 completed phase (27+) shows up in the rendered table.
- Bravoh-funnel footer link is present + has the expected anchor.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"
ROADMAP = REPO_ROOT / ".planning" / "ROADMAP.md"
SYNC_SCRIPT = REPO_ROOT / "scripts" / "launch" / "sync_feature_matrix.py"


def test_sync_feature_matrix_py_exists():
    assert SYNC_SCRIPT.exists(), f"missing {SYNC_SCRIPT}"


def test_readme_has_auto_gen_markers():
    body = README.read_text(encoding="utf-8")
    assert "<!-- AUTO-GEN: feature-matrix START" in body, (
        "README.md missing AUTO-GEN feature-matrix START marker"
    )
    assert "<!-- AUTO-GEN: feature-matrix END -->" in body, (
        "README.md missing AUTO-GEN feature-matrix END marker"
    )


def test_readme_feature_matrix_in_sync():
    """The README must match sync_feature_matrix.py --check output."""
    result = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"README feature matrix drift detected. Run "
        f"`python {SYNC_SCRIPT.relative_to(REPO_ROOT)} --write`.\n"
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )


def test_feature_matrix_includes_all_completed_phases():
    """Every `- [x] **Phase NN:` line in ROADMAP with NN >= 27 must
    appear as a row in the README table."""
    roadmap_text = ROADMAP.read_text(encoding="utf-8")
    completed = set()
    for line in roadmap_text.splitlines():
        m = re.match(r"^- \[x\] (?:\*\*)?Phase\s+(\d+):", line)
        if m:
            phase_no = int(m.group(1))
            if phase_no >= 27:
                completed.add(phase_no)

    readme_text = README.read_text(encoding="utf-8")
    # Extract the AUTO-GEN block.
    start = readme_text.find("<!-- AUTO-GEN: feature-matrix START")
    end = readme_text.find("<!-- AUTO-GEN: feature-matrix END -->")
    assert start != -1 and end != -1, "AUTO-GEN markers missing"
    block = readme_text[start:end]

    missing = []
    for phase_no in sorted(completed):
        if f"| {phase_no} |" not in block:
            missing.append(phase_no)
    assert not missing, (
        f"phases missing from README feature-matrix block: {missing}\n"
        f"completed set: {sorted(completed)}"
    )


def test_feature_matrix_excludes_v0_and_v2_0_phases():
    """v0.1.0 + v2.0 phases (<27) MUST NOT appear in the v2.1 block."""
    readme_text = README.read_text(encoding="utf-8")
    start = readme_text.find("<!-- AUTO-GEN: feature-matrix START")
    end = readme_text.find("<!-- AUTO-GEN: feature-matrix END -->")
    block = readme_text[start:end]
    for old in range(1, 27):
        # Match table row beginning `| <old> |`.
        assert f"| {old} |" not in block, (
            f"v0.1.0/v2.0 phase {old} leaked into v2.1 feature-matrix block"
        )


def test_bravoh_footer_link_present_and_active():
    """Bravoh funnel link (with utm_*) must be present in README footer."""
    body = README.read_text(encoding="utf-8")
    # Must contain the altidus.world link with utm campaign attribution.
    assert "altidus.world" in body, "Bravoh footer link missing"
    assert "utm_source=github" in body, (
        "Bravoh footer link missing utm_source=github attribution"
    )
    assert "utm_campaign=vibemix_launch" in body, (
        "Bravoh footer link missing utm_campaign=vibemix_launch"
    )


def test_bravoh_footer_appears_after_feature_matrix():
    """Sanity: the footer link comes after the feature matrix block."""
    body = README.read_text(encoding="utf-8")
    matrix_end = body.find("<!-- AUTO-GEN: feature-matrix END -->")
    footer_idx = body.find("altidus.world/vibemix?utm_source=github")
    assert matrix_end != -1 and footer_idx != -1
    assert footer_idx > matrix_end, (
        "Bravoh footer must appear after the feature-matrix block"
    )


def test_video_tag_present_in_hero_block():
    """SHIP-02 — hero block must include the HTML5 <video> tag pointing
    at docs/assets/demo.mp4 (with <img> fallback for stale clients)."""
    body = README.read_text(encoding="utf-8")
    hero_start = body.find("<!-- vibemix:hero-start")
    hero_end = body.find("<!-- vibemix:hero-end -->")
    assert hero_start != -1 and hero_end != -1
    hero_block = body[hero_start:hero_end]
    assert "<video" in hero_block, "hero block missing <video> tag"
    assert "docs/assets/demo.mp4" in hero_block, (
        "hero <video> src must point at docs/assets/demo.mp4"
    )


def test_readme_hero_hash_sync_still_passes():
    """Defensive: ensure the Phase 35 hero hash sync is still green
    after the SHIP-02 surgery."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest",
         str(REPO_ROOT / "tests/repo/test_readme_hero_hash_sync.py"),
         "-q", "--no-header"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"Phase 35 hero hash sync test regressed.\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
