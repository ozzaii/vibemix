# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-06 — POC immutability gate (AUDIT-06).

Memory `feedback_poc_is_reference` + `project_v3_poc_reference` +
`project_v4_canonical_baseline`: the POC files (cohost.py, cohost_v2.py,
cohost_lk.py, mascot.html, cohost.streaming.py.bak) are TRUSTED
INTUITION to port FROM, never edit. This test asserts byte-for-byte
identity against the v2.0 git tag baseline.

Phase 37 ALLOWLIST extension: v2.1 paths that intentionally diverge
from v2.0 (new wizard / mascot layer / day-zero artifacts). The
allowlist NEVER contains cohost*.py or mascot.html — that's the load-
bearing safety check (``test_allowlist_does_not_contain_poc_patterns``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# POC reference files — MUST match v2.0 byte-for-byte.
PROTECTED_POC_PATTERNS = [
    "cohost.py",
    "cohost_v2.py",
    "cohost_lk.py",
    "cohost.streaming.py.bak",
    "mascot.html",
]

# v2.1 modified-files allowlist — paths that intentionally diverge
# from v2.0. NEVER contains the protected POC patterns above.
MODIFIED_FILES_ALLOWLIST = frozenset({
    # Phase 27 — eval harness + carry-forward close-out
    "scripts/eval/replay_harness.py",
    ".github/workflows/eval.yml",
    "eval/THRESHOLD-LOCK.md",
    # Phase 28 — library intelligence v1
    "src/vibemix/library/grounding.py",
    "src/vibemix/library/embed.py",
    "src/vibemix/library/index_sqlite_vec.py",
    "src/vibemix/library/index_numpy.py",
    "src/vibemix/library/similar.py",
    "src/vibemix/library/staleness.py",
    "src/vibemix/library/search.py",
    "src/vibemix/library/budget.py",
    "src/vibemix/library/store.py",
    "src/vibemix/library/importer.py",
    # Phase 29 — post-session debrief MVP UI
    "src/vibemix/debrief/",
    # Phase 30 — Hard Tek detectors
    "src/vibemix/state/detectors/",
    # Phase 31 — 4-layer mascot
    "tauri/ui/src/mascot/priority-stack.ts",
    "tauri/ui/src/mascot/layers/",
    # Phase 32 — long-term DJ profile
    "src/vibemix/profile/cache_render.py",
    # Phase 33 — one-click install hardening
    "src/vibemix/install/",
    "src/vibemix/wizard/",
    # Phase 34 — open-source security pass
    "SECURITY.md",
    ".github/workflows/secret-scan.yml",
    ".github/workflows/python-cve.yml",
    ".github/workflows/rust-cve.yml",
    ".github/workflows/sbom.yml",
    # Phase 35 — real GLB animations + viral demo
    "scripts/demo_film/",
    "scripts/reaction_reel/",
    # Phase 36 — day-zero ops
    "scripts/dayzero/",
    # Phase 37 — this phase
    "scripts/integration_audit.py",
    "tests/e2e/test_seam_p18__p20.py",
    "tests/e2e/test_seam_p19__agent.py",
    "tests/e2e/test_seam_p25__p28.py",
    "tests/e2e/test_seam_p27__eval_gate.py",
    "tests/e2e/test_seam_p31__ws_bus.py",
    "tests/scripts/test_integration_audit_v2_1.py",
    "tests/scripts/test_orphan_inventory.py",
    "tests/scripts/test_kaan_action_rollup.py",
    "tests/scripts/test_grey_area_log.py",
    "tests/repo/test_g5_poc_files_untouched.py",
    ".github/workflows/orphan-inventory.yml",
    ".planning/codebase/orphans.csv",
    ".planning/v2.1-MILESTONE-AUDIT.md",
    # Phase 38 — signing pipeline
    ".github/workflows/release.yml",
    ".github/workflows/verify-signed.yml",
    "scripts/sign_windows.ps1",
    "KAAN-ACTION-LEGAL.md",
})


def _git_blob_hash(ref: str, path: str) -> str | None:
    """Return the git blob hash for ``path`` at ``ref``, or None if absent."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", f"{ref}:{path}"],
            capture_output=True,
            text=True,
            cwd=str(REPO),
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _current_blob_hash(path: str) -> str | None:
    """Hash the working-tree contents of ``path`` using git hash-object."""
    full = REPO / path
    if not full.exists():
        return None
    result = subprocess.run(
        ["git", "hash-object", str(full)],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


@pytest.mark.parametrize("poc", ["cohost.py", "cohost_v2.py", "cohost_lk.py", "mascot.html"])
def test_poc_file_untouched_since_v2_0(poc: str) -> None:
    """Each POC reference file MUST hash-match its v2.0 tag blob."""
    v20_hash = _git_blob_hash("v2.0", poc)
    if v20_hash is None:
        pytest.skip(f"v2.0 tag has no {poc} blob (test cannot run)")
    current = _current_blob_hash(poc)
    assert current == v20_hash, (
        f"{poc} has been modified since v2.0!\n"
        f"  v2.0 blob:  {v20_hash}\n"
        f"  current:    {current}\n"
        f"POC files are TRUSTED INTUITION TO PORT FROM, never edit. "
        f"Revert to the v2.0 version: git checkout v2.0 -- {poc}"
    )


def test_cohost_streaming_bak_untouched_since_v2_0() -> None:
    """The archived streaming prototype is also frozen."""
    v20_hash = _git_blob_hash("v2.0", "cohost.streaming.py.bak")
    if v20_hash is None:
        pytest.skip("v2.0 tag has no cohost.streaming.py.bak")
    current = _current_blob_hash("cohost.streaming.py.bak")
    assert current == v20_hash, (
        "cohost.streaming.py.bak has drifted from v2.0 — revert it"
    )


def test_allowlist_does_not_contain_poc_patterns() -> None:
    """The v2.1 modified-files allowlist NEVER permits cohost*.py / mascot.html.

    This is the LOAD-BEARING safety check — if a future developer adds
    one of the POC patterns to the allowlist, this test fails loud.
    """
    for entry in MODIFIED_FILES_ALLOWLIST:
        for poc in PROTECTED_POC_PATTERNS:
            assert poc not in entry, (
                f"allowlist entry {entry!r} matches protected POC pattern {poc!r} — "
                f"REMOVE IT. POC files are byte-frozen at v2.0."
            )


def test_v2_0_tag_exists() -> None:
    """Sanity: the v2.0 git tag exists in the repo."""
    result = subprocess.run(
        ["git", "tag", "-l", "v2.0"],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        check=False,
    )
    assert "v2.0" in result.stdout, "v2.0 tag missing — POC drift gate cannot run"
