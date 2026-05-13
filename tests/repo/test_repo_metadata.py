# SPDX-License-Identifier: Apache-2.0
"""Phase 19 Plan 19-01 — Repo metadata CI gate (GH-17).

Locks the shape + values of:
- ``.github/repo-config.yml`` (description, homepage, topics,
  default_branch, enable_issues, enable_projects, enable_wiki,
  delete_branch_on_merge, allow_squash_merge, allow_merge_commit,
  allow_rebase_merge).
- ``scripts/dist/configure_repo.sh`` (idempotent gh-repo-edit wrapper,
  ``--apply`` safety gate).
- ``scripts/hooks/pre-commit-no-binaries.sh`` (>1 MB rejection,
  LFS-aware via ``git lfs ls-files``).

Both shell scripts must be ``bash -n`` syntax-clean and executable.

YAML loader: ``yaml.safe_load`` (PyYAML — already a transitive dep of
livekit-agents via ``ruamel.yaml``? actually not; the test xfails with a
clear message if PyYAML missing so the developer knows to ``pip install
pyyaml`` once. See test_yaml_dependency_available).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REPO_CONFIG = REPO_ROOT / ".github" / "repo-config.yml"
CONFIGURE_REPO = REPO_ROOT / "scripts" / "dist" / "configure_repo.sh"
PRE_COMMIT_HOOK = REPO_ROOT / "scripts" / "hooks" / "pre-commit-no-binaries.sh"

REQUIRED_KEYS: set[str] = {
    "description",
    "homepage",
    "topics",
    "default_branch",
    "enable_issues",
    "enable_projects",
    "enable_wiki",
    "delete_branch_on_merge",
    "allow_squash_merge",
    "allow_merge_commit",
    "allow_rebase_merge",
}

LOCKED_TOPICS: set[str] = {
    "dj",
    "livekit",
    "gemini",
    "ai-assistant",
    "audio",
    "midi",
    "pioneer-ddj",
    "realtime-ai",
    "tauri",
    "open-source",
}


def _load_config() -> dict:
    """Load .github/repo-config.yml; skip cleanly if PyYAML unavailable."""
    yaml = pytest.importorskip(
        "yaml",
        reason="PyYAML required for repo-config.yml validation — `pip install pyyaml`",
    )
    assert REPO_CONFIG.exists(), f"{REPO_CONFIG} missing"
    return yaml.safe_load(REPO_CONFIG.read_text())


# -----------------------------------------------------------------------
# repo-config.yml shape tests (5)
# -----------------------------------------------------------------------


def test_repo_config_yaml_parses() -> None:
    """``.github/repo-config.yml`` parses as a YAML mapping."""
    cfg = _load_config()
    assert isinstance(cfg, dict), (
        f"repo-config.yml root must be a mapping, got {type(cfg).__name__}"
    )


def test_repo_config_has_required_keys() -> None:
    """All 11 required keys present at top level."""
    cfg = _load_config()
    missing = REQUIRED_KEYS - set(cfg.keys())
    assert not missing, f"repo-config.yml missing required keys: {missing}"


def test_repo_config_topics_are_locked_set() -> None:
    """Topics is a list ≥10 long and is a superset of the locked set."""
    cfg = _load_config()
    topics = cfg["topics"]
    assert isinstance(topics, list), "topics must be a YAML list"
    assert len(topics) >= 10, (
        f"topics must have ≥10 entries (GitHub display limit is 20), got "
        f"{len(topics)}"
    )
    missing = LOCKED_TOPICS - set(topics)
    assert not missing, f"topics missing locked-set entries: {missing}"


def test_repo_config_description_under_350_chars_and_anchored() -> None:
    """description ≤350 chars and references core anchors."""
    cfg = _load_config()
    desc = cfg["description"]
    assert isinstance(desc, str), "description must be a string"
    assert len(desc) <= 350, (
        f"description {len(desc)} chars exceeds GitHub 350 limit"
    )
    # Required anchors per CONTEXT Area 6 + product positioning.
    for anchor in ("AI co-host", "DJ", "Mac", "Windows"):
        assert anchor in desc, (
            f"description must reference {anchor!r} per CONTEXT Area 6"
        )


def test_repo_config_merge_and_feature_switches_locked() -> None:
    """Merge policy + issues/projects/wiki switches match CONTEXT Area 6."""
    cfg = _load_config()
    assert cfg["enable_issues"] is True, "issues must be enabled"
    assert cfg["enable_projects"] is False, "projects must be disabled"
    assert cfg["enable_wiki"] is False, "wiki must be disabled"
    assert cfg["delete_branch_on_merge"] is True, (
        "delete_branch_on_merge must be true (clean branch list)"
    )
    assert cfg["allow_squash_merge"] is True, "squash-only policy"
    assert cfg["allow_merge_commit"] is False, "no merge commits"
    assert cfg["allow_rebase_merge"] is False, "no rebase merges"


# -----------------------------------------------------------------------
# Shell script tests (6)
# -----------------------------------------------------------------------


def test_configure_repo_script_exists_and_executable() -> None:
    """``scripts/dist/configure_repo.sh`` exists, is executable."""
    assert CONFIGURE_REPO.exists(), f"{CONFIGURE_REPO} missing"
    assert os.access(CONFIGURE_REPO, os.X_OK), (
        f"{CONFIGURE_REPO} must be executable (chmod +x)"
    )


def test_pre_commit_hook_exists_and_executable() -> None:
    """``scripts/hooks/pre-commit-no-binaries.sh`` exists, is executable."""
    assert PRE_COMMIT_HOOK.exists(), f"{PRE_COMMIT_HOOK} missing"
    assert os.access(PRE_COMMIT_HOOK, os.X_OK), (
        f"{PRE_COMMIT_HOOK} must be executable (chmod +x)"
    )


def test_configure_repo_script_is_bash_syntax_clean() -> None:
    """``bash -n`` finds no syntax errors in configure_repo.sh."""
    result = subprocess.run(
        ["bash", "-n", str(CONFIGURE_REPO)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"configure_repo.sh has bash syntax errors:\n{result.stderr}"
    )


def test_pre_commit_hook_is_bash_syntax_clean() -> None:
    """``bash -n`` finds no syntax errors in pre-commit-no-binaries.sh."""
    result = subprocess.run(
        ["bash", "-n", str(PRE_COMMIT_HOOK)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"pre-commit-no-binaries.sh has bash syntax errors:\n{result.stderr}"
    )


def test_configure_repo_wraps_gh_repo_edit_and_reads_yaml() -> None:
    """``configure_repo.sh`` invokes ``gh repo edit`` and reads repo-config.yml."""
    text = CONFIGURE_REPO.read_text()
    assert "gh repo edit" in text, (
        "configure_repo.sh must wrap `gh repo edit`"
    )
    assert "repo-config.yml" in text, (
        "configure_repo.sh must reference .github/repo-config.yml"
    )
    # --apply safety gate (idempotent dry-run by default per CONTEXT Area 6).
    assert "--apply" in text, (
        "configure_repo.sh must implement --apply safety gate "
        "(default = dry-run print)"
    )


def test_pre_commit_hook_enforces_one_mb_with_lfs_exemption() -> None:
    """``pre-commit-no-binaries.sh`` checks 1 MB threshold + LFS-aware."""
    # Strip comment lines so the constant has to live in real code.
    body = "\n".join(
        ln
        for ln in PRE_COMMIT_HOOK.read_text().splitlines()
        if not ln.lstrip().startswith("#")
    )
    assert "1048576" in body, (
        "pre-commit hook must enforce 1048576 byte (1 MB) threshold "
        "in executable code (not just a comment)"
    )
    assert "git lfs ls-files" in body, (
        "pre-commit hook must consult `git lfs ls-files` to exempt "
        "LFS-tracked blobs"
    )
