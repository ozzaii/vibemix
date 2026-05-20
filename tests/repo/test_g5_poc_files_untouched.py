# SPDX-License-Identifier: Apache-2.0
"""POC retirement gate (was Phase 37 AUDIT-06 "POC immutability gate").

History: through v2.x the root POC variants (cohost.py, cohost_v2.py,
cohost_lk.py, cohost_v3.py, cohost_v4.py, cohost.streaming.py.bak) were
TRUSTED INTUITION to port FROM and were byte-frozen against the ``v2.0``
git tag so they could never be edited.

2026-05-20: their logic has been fully lifted into ``src/vibemix/`` and the
variant zoo was PRUNED to end the recurring "which file is canonical?"
confusion. The gate is inverted accordingly — it now asserts the variants
stay GONE rather than stay byte-identical. (The filename is retained so the
CI grep-gate allowlist in mascot-audit.yml / test_ci_grep_gates.py and
cut_release.sh Gate 5 keep resolving without churn.)

``mascot.html`` is the lone survivor: it is the live overlay wired into
``vibemix.runtime.ws_bus`` + the ``mascot-audit`` workflow, not a POC, so it
must remain present (and is free to evolve).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Root-level POC variant files that were retired 2026-05-20. The gate asserts
# they stay absent from both the working tree and HEAD.
RETIRED_POC_FILES = [
    "cohost.py",
    "cohost_v2.py",
    "cohost_lk.py",
    "cohost_v3.py",
    "cohost_v4.py",
    "cohost.streaming.py.bak",
    "run.sh",
    "run_v2.sh",
    "run_lk.sh",
    "generate_bat.py",
    "test_voice.py",
]


def _tracked_at_head(path: str) -> bool:
    """True if ``path`` is tracked in the current HEAD tree."""
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", path],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )
    return result.returncode == 0


@pytest.mark.parametrize("poc", RETIRED_POC_FILES)
def test_retired_poc_variant_absent_from_worktree(poc: str) -> None:
    """Each retired POC variant must NOT exist in the working tree."""
    assert not (REPO / poc).exists(), (
        f"{poc} is back in the working tree — it was retired 2026-05-20 once "
        f"its logic landed in the vibemix package. Do not resurrect the "
        f"variant zoo (that confusion is exactly what the prune removed)."
    )


@pytest.mark.parametrize("poc", RETIRED_POC_FILES)
def test_retired_poc_variant_untracked(poc: str) -> None:
    """Each retired POC variant must NOT be tracked at HEAD."""
    assert not _tracked_at_head(poc), (
        f"{poc} is tracked at HEAD — a stray `git add` resurrected a retired "
        f"POC variant. Run `git rm {poc}`."
    )


def test_mascot_html_survives() -> None:
    """The live mascot overlay is NOT a POC and must remain present."""
    assert (REPO / "mascot.html").exists(), (
        "mascot.html is missing — it is the live overlay (vibemix.runtime."
        "ws_bus + mascot-audit CI), not a retired POC, and must survive."
    )


def test_v2_0_tag_exists() -> None:
    """Sanity: the v2.0 git tag (the old freeze baseline) still exists so the
    historical POC source remains reachable via git history."""
    result = subprocess.run(
        ["git", "tag", "-l", "v2.0"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )
    assert "v2.0" in result.stdout, (
        "v2.0 tag missing — retired POC source should stay reachable in history"
    )
