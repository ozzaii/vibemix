# SPDX-License-Identifier: Apache-2.0
"""Phase 69 Plan 69-04 — anti-rot presence test for the Homebrew + Scoop
packaging scaffolds + the CI audit workflow + the sync helper.

OSS-05 invariant: the v7.0 milestone ships the scaffolds + audit; the
actual tap/bucket publish is a future milestone (see
docs/release-process.md "Homebrew + Scoop publish — split rationale").
This gate ensures the 4 scaffold artifacts + the doc section + the
workflow job names don't silently drift between v7.0 and the future
publish milestone.
"""
from __future__ import annotations

import json
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_homebrew_formula_present() -> None:
    """packaging/homebrew/Formula/vibemix.rb exists with correct class +
    URL shape — pin lifted directly from Plan 69-04 Task 1."""
    path = REPO_ROOT / "packaging" / "homebrew" / "Formula" / "vibemix.rb"
    assert path.exists(), (
        f"Missing required brew Formula at {path.relative_to(REPO_ROOT)}. "
        "v7.0 OSS-05 requires this file. See Plan 69-04 Task 1."
    )
    text = path.read_text(encoding="utf-8")
    assert "class Vibemix < Formula" in text, (
        "packaging/homebrew/Formula/vibemix.rb must declare "
        "`class Vibemix < Formula` (capitalized). brew audit pins the class "
        "name to the filename. See Plan 69-04 Task 1."
    )
    assert "bravoh-ai/vibemix/releases/download" in text, (
        "packaging/homebrew/Formula/vibemix.rb must reference "
        "https://github.com/bravoh-ai/vibemix/releases/download/... in its "
        "url line so the future tap publish resolves the real asset. "
        "See Plan 69-04 Task 1."
    )


def test_scoop_manifest_present() -> None:
    """packaging/scoop/vibemix.json exists as valid JSON with correct
    bin + version — pin lifted directly from Plan 69-04 Task 2."""
    path = REPO_ROOT / "packaging" / "scoop" / "vibemix.json"
    assert path.exists(), (
        f"Missing required Scoop manifest at {path.relative_to(REPO_ROOT)}. "
        "v7.0 OSS-05 requires this file. See Plan 69-04 Task 2."
    )
    # json.loads raises on invalid JSON — that IS the assertion.
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "vibemix.exe" in data.get("bin", []), (
        "packaging/scoop/vibemix.json must list `vibemix.exe` in the bin "
        "array (matches the Tauri-built Windows executable name). "
        "See Plan 69-04 Task 2."
    )
    assert data.get("version") == "0.1.0-rc1", (
        "packaging/scoop/vibemix.json must pin version `0.1.0-rc1` "
        "(matches cut_release.sh TAG_REGEX). See Plan 69-04 Task 2."
    )


def test_packaging_audit_workflow_present() -> None:
    """.github/workflows/packaging-audit.yml exists with both required
    job names — pin lifted directly from Plan 69-04 Task 4."""
    path = REPO_ROOT / ".github" / "workflows" / "packaging-audit.yml"
    assert path.exists(), (
        f"Missing required CI workflow at {path.relative_to(REPO_ROOT)}. "
        "v7.0 OSS-05 requires this file. See Plan 69-04 Task 4."
    )
    text = path.read_text(encoding="utf-8")
    assert "brew-audit:" in text, (
        ".github/workflows/packaging-audit.yml must declare the "
        "`brew-audit:` job (runs-on macos-14, invokes brew audit --new). "
        "See Plan 69-04 Task 4."
    )
    assert "scoop-checkver:" in text, (
        ".github/workflows/packaging-audit.yml must declare the "
        "`scoop-checkver:` job (runs-on windows-latest, invokes "
        "scoop checkver -d). See Plan 69-04 Task 4."
    )


def test_sync_packaging_helper_present() -> None:
    """scripts/launch/sync_packaging.sh exists with executable bit set —
    pin lifted directly from Plan 69-04 Task 3."""
    path = REPO_ROOT / "scripts" / "launch" / "sync_packaging.sh"
    assert path.exists(), (
        f"Missing required helper at {path.relative_to(REPO_ROOT)}. "
        "v7.0 OSS-05 requires this file. See Plan 69-04 Task 3."
    )
    mode = path.stat().st_mode
    assert mode & stat.S_IXUSR, (
        f"scripts/launch/sync_packaging.sh must have the user-executable "
        f"bit set (got mode {oct(mode)}). A stray "
        "`git update-index --chmod=-x` flips this gate red — that is "
        "intentional. See Plan 69-04 Task 3."
    )


def test_release_process_doc_has_split_rationale() -> None:
    """docs/release-process.md carries the OSS-05 split-rationale H2 —
    pin lifted directly from Plan 69-04 Task 5."""
    path = REPO_ROOT / "docs" / "release-process.md"
    assert path.exists(), (
        f"Missing required doc at {path.relative_to(REPO_ROOT)}. "
        "v7.0 OSS-05 references this file. See Plan 69-04 Task 5."
    )
    text = path.read_text(encoding="utf-8")
    header = "## Homebrew + Scoop publish — split rationale"
    count = text.count(header)
    assert count == 1, (
        f"docs/release-process.md must contain the H2 header {header!r} "
        f"exactly once (found {count}). Duplicates signal a stale draft; "
        "removal signals OSS-05 doc rot. See Plan 69-04 Task 5."
    )
