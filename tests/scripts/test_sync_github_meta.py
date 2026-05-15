# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-05 — sync_github_meta.sh tests.

REQ-IDs: SHIP-05

Asserts:
- The script runs in dry-run by default + does NOT call `gh api`.
- --real without GH_META_REAL=1 env exits 2.
- Description is <= 350 chars.
- Topics list contains all 10 required entries.
- Static audit: script body's only `gh api` invocations live behind the
  real-mode guard.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "launch" / "sync_github_meta.sh"
META_DOC = REPO_ROOT / "docs" / "launch" / "github-meta.md"

REQUIRED_TOPICS = [
    "dj", "ai", "gemini", "tauri", "open-source",
    "mascot", "livekit", "audio", "vibemix", "bravoh",
]


def test_script_and_meta_doc_exist():
    assert SCRIPT.exists()
    assert META_DOC.exists()
    assert os.access(SCRIPT, os.X_OK), "sync_github_meta.sh not chmod +x"


def test_sync_github_meta_dry_run_does_not_call_gh_api():
    """Default invocation is dry-run; output contains `[dry-run]` and
    NEVER hits gh api for real."""
    env = os.environ.copy()
    env.pop("GH_META_REAL", None)
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True, text=True, check=False, env=env,
    )
    assert result.returncode == 0
    assert "[dry-run]" in result.stdout
    assert "[real]" not in result.stdout
    # The output must show what WOULD be done but not actually execute.
    assert "would: gh api" in result.stdout


def test_real_mode_requires_env_flag():
    """--real without GH_META_REAL=1 must exit 2."""
    env = os.environ.copy()
    env.pop("GH_META_REAL", None)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--real"],
        capture_output=True, text=True, check=False, env=env,
    )
    assert result.returncode == 2
    assert "GH_META_REAL" in (result.stdout + result.stderr)


def test_description_under_350_chars():
    """Description (between first fenced block under '## Description') must
    be <=350 chars — GitHub's hard limit."""
    body = META_DOC.read_text(encoding="utf-8")
    m = re.search(r"^## Description.*?\n```\n(.*?)\n```", body, re.DOTALL | re.MULTILINE)
    assert m, "could not find Description fenced block"
    desc = m.group(1).strip()
    assert len(desc) <= 350, f"description is {len(desc)} chars (>350): {desc!r}"
    assert len(desc) > 50, "description suspiciously short"


def test_topics_list_includes_required_10():
    """Topics section must contain exactly the 10 required entries."""
    body = META_DOC.read_text(encoding="utf-8")
    m = re.search(r"^## Topics.*?\n```\n(.*?)\n```", body, re.DOTALL | re.MULTILINE)
    assert m, "could not find Topics fenced block"
    topics = [t.strip() for t in m.group(1).split() if t.strip()]
    assert sorted(topics) == sorted(REQUIRED_TOPICS), (
        f"topics mismatch.\n  expected: {sorted(REQUIRED_TOPICS)}\n  got:      {sorted(topics)}"
    )


def test_homepage_url_is_altidus_with_utm():
    body = META_DOC.read_text(encoding="utf-8")
    m = re.search(r"^## Homepage URL.*?\n```\n(.*?)\n```", body, re.DOTALL | re.MULTILINE)
    assert m
    url = m.group(1).strip()
    assert "altidus.world" in url
    assert "utm_source=github" in url
    assert "utm_campaign=vibemix_launch" in url


def test_static_audit_real_gh_api_calls_guarded():
    """The script body contains `gh api` calls but each one is inside
    the `if [[ "${MODE}" == "real" ]]` block. We verify by checking that
    no `gh api` line appears BEFORE the MODE=real branch."""
    body = SCRIPT.read_text(encoding="utf-8")
    lines = body.splitlines()
    # Find the index of MODE=="real" branch.
    real_branch_idx = None
    for i, line in enumerate(lines):
        if 'MODE' in line and '"real"' in line and 'then' in line:
            real_branch_idx = i
            break
    assert real_branch_idx is not None, "could not locate MODE=='real' branch"
    # Any `gh api` line before that branch is a leak (must be only inside).
    # The only acceptable mention before is in comments.
    for i, line in enumerate(lines[:real_branch_idx]):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert "gh api" not in line, (
            f"line {i+1} contains `gh api` outside the real-mode branch: {line!r}"
        )


def test_help_flag_prints_usage():
    """-h / --help prints the top comment block."""
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "SHIP-05" in result.stdout or "sync_github_meta" in result.stdout


def test_repo_slug_default_is_bravoh_vibemix():
    """Default REPO_SLUG must be bravoh/vibemix (SHIP-05 contract)."""
    body = SCRIPT.read_text(encoding="utf-8")
    assert 'REPO_SLUG:-bravoh/vibemix' in body, (
        "default REPO_SLUG must be bravoh/vibemix"
    )
