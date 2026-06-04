# SPDX-License-Identifier: Apache-2.0
"""README hero + footer gate.

Originally (Phase 39 / Plan 39-02) this gate also pinned an AUTO-GEN
feature-matrix block synced from .planning/ROADMAP.md. That block dumped
internal Phase numbers, commit SHAs, and REQ-IDs onto the public README
landing page, which read as internal slop to a reader skimming the repo.

Retired 2026-06-04 (partner-copy de-slop): the auto-gen Phase/SHA matrix was
removed from README.md in favor of a hand-written, user-facing capability
section ("What's inside"). The matrix-sync, AUTO-GEN-marker, and per-phase
inclusion/exclusion assertions are retired with it. `sync_feature_matrix.py`
stays on disk (unused) and is still presence-checked below.

What remains pinned:
- the Bravoh funnel footer link (with utm attribution),
- the hero <video>/poster contract,
- the hero-hash sentinel sync.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"
SYNC_SCRIPT = REPO_ROOT / "scripts" / "launch" / "sync_feature_matrix.py"


def test_sync_feature_matrix_py_exists():
    assert SYNC_SCRIPT.exists(), f"missing {SYNC_SCRIPT}"


def test_bravoh_footer_link_present_and_active():
    """Bravoh funnel link (with utm_*) must be present in the README footer."""
    body = README.read_text(encoding="utf-8")
    assert "bravoh.ai/vibemix?utm_source=github" in body, "Bravoh footer link missing"
    assert "utm_source=github" in body, (
        "Bravoh footer link missing utm_source=github attribution"
    )
    assert "utm_campaign=vibemix_launch" in body, (
        "Bravoh footer link missing utm_campaign=vibemix_launch"
    )


def test_video_tag_present_in_hero_block():
    """SHIP-02 — the hero block must keep the <video>/docs/assets/demo.mp4
    contract so the demo film drops in without a structural change."""
    body = README.read_text(encoding="utf-8")
    hero_start = body.find("<!-- vibemix:hero-start")
    hero_end = body.find("<!-- vibemix:hero-end -->")
    assert hero_start != -1 and hero_end != -1
    hero_block = body[hero_start:hero_end]
    assert "<video" in hero_block, "hero block missing <video> reference"
    assert "docs/assets/demo.mp4" in hero_block, (
        "hero <video> src must point at docs/assets/demo.mp4"
    )


def test_readme_hero_hash_sync_still_passes():
    """Defensive: ensure the Phase 35 hero hash sync is still green."""
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
