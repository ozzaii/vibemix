"""Phase 20 docs + workflow + script gate — Plan 20.

Validates that every artifact Phase 20 Plan 20 promised exists in the
shape future readers expect. No live network calls; pure file shape.
"""

from __future__ import annotations

import os
import stat
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


# --- Task 1: issue-triage workflow ---------------------------------------

def test_issue_triage_workflow_exists():
    assert (REPO_ROOT / ".github/workflows/issue-triage.yml").is_file()


def test_issue_triage_is_valid_yaml():
    parsed = yaml.safe_load(_read(".github/workflows/issue-triage.yml"))
    # PyYAML parses `on:` as Python `True` (boolean). Both spellings must work.
    assert "name" in parsed
    trigger = parsed.get("on") or parsed.get(True)
    assert trigger is not None, "no `on:` trigger present"
    assert "issues" in trigger
    assert "opened" in trigger["issues"]["types"]


def test_issue_triage_has_triage_label():
    body = _read(".github/workflows/issue-triage.yml")
    assert '"triage"' in body, "the 'triage' label must always be applied"


def test_issue_triage_maps_severity():
    body = _read(".github/workflows/issue-triage.yml")
    for level in ("critical", "major", "minor"):
        assert f"severity:{level}" in body


# --- Task 2: day-zero-rota.md --------------------------------------------

def test_day_zero_rota_exists():
    assert (REPO_ROOT / "docs/day-zero-rota.md").is_file()


def test_rota_lists_three_named_owners():
    body = _read("docs/day-zero-rota.md")
    for name in ("Kaan", "Francesco", "Musa"):
        assert name in body, f"{name} missing from rota doc"


def test_rota_covers_first_72h():
    body = _read("docs/day-zero-rota.md")
    assert "T+72" in body or "72 hours" in body.lower() or "72h" in body.lower()


# --- Task 3: install-rehearsal.md ----------------------------------------

def test_install_rehearsal_exists():
    assert (REPO_ROOT / "docs/install-rehearsal.md").is_file()


def test_rehearsal_covers_both_platforms():
    body = _read("docs/install-rehearsal.md")
    assert "## macOS rehearsal checklist" in body
    assert "## Windows rehearsal checklist" in body


def test_rehearsal_has_stopwatch_table():
    body = _read("docs/install-rehearsal.md")
    # Both checklists have a Step | Target | Actual | Pass column header.
    assert body.count("| Step | Target | Actual | Pass? |") >= 2


def test_rehearsal_has_failure_taxonomy():
    body = _read("docs/install-rehearsal.md")
    for cls in ("signing", "notarization", "dep-install", "audio-route", "midi-detect"):
        assert f"`{cls}`" in body


# --- Task 4: post-launch-playbook.md -------------------------------------

def test_post_launch_playbook_exists():
    assert (REPO_ROOT / "docs/post-launch-playbook.md").is_file()


def test_playbook_covers_t0_through_t72():
    body = _read("docs/post-launch-playbook.md")
    for stamp in ("T+0:00", "T+0:30", "T+0:45", "T+1:00", "T+24:00", "T+48:00", "T+72:00"):
        assert stamp in body, f"missing time stamp: {stamp}"


def test_playbook_has_hotfix_process():
    body = _read("docs/post-launch-playbook.md")
    assert "Hotfix process" in body


def test_playbook_has_retro_template():
    body = _read("docs/post-launch-playbook.md")
    assert "Retro template" in body or "retro" in body.lower()


# --- Task 5: README Discord link placeholder -----------------------------

def test_readme_has_discord_line():
    body = _read("README.md")
    assert "Discord:" in body, "README must have a Discord line (TBD or real)"


# --- Task 6: pretag_check.sh ---------------------------------------------

def test_pretag_check_exists_and_executable():
    p = REPO_ROOT / "scripts/dist/pretag_check.sh"
    assert p.is_file()
    mode = p.stat().st_mode
    assert mode & stat.S_IXUSR, "pretag_check.sh must be executable (chmod +x)"


def test_pretag_check_has_all_seven_steps():
    body = _read("scripts/dist/pretag_check.sh")
    for i in range(1, 8):
        assert f"[{i}/7]" in body, f"step {i}/7 missing"


def test_pretag_check_uses_required_secrets_list():
    body = _read("scripts/dist/pretag_check.sh")
    for s in ("APPLE_APP_PASSWORD", "SIGNPATH_API_TOKEN", "TAURI_UPDATER_PRIVATE_KEY"):
        assert s in body
