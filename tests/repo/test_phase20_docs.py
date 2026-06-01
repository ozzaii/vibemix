"""Phase 20 docs + workflow + script gate — Plan 20.

Validates that every artifact Phase 20 Plan 20 promised exists in the
shape future readers expect. No live network calls; pure file shape.
"""

from __future__ import annotations

import stat
from pathlib import Path

import yaml

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
    for cls in (
        "signing",
        "notarization",
        "dep-install",
        "model-setup",
        "viber-setup",
        "library-agent",
        "audio-route",
        "midi-detect",
    ):
        assert f"`{cls}`" in body


def test_rehearsal_covers_local_models_and_library_agent_smoke():
    body = _read("docs/install-rehearsal.md")
    for phrase in (
        "Required models ready",
        "CLAP ready",
        "codex login",
        "Library search returns real local-library results without Gemini key",
        "Library chat sends one Viber message",
        "Build-a-set creates",
    ):
        assert phrase in body


def test_windows_source_setup_doc_points_to_current_installer_docs():
    body = _read("docs/windows-setup.md")
    for phrase in (
        "before the installer exists",
        "Out of scope: end-user installer",
        "SignPath MSI",
    ):
        assert phrase not in body
    for phrase in (
        "SignPath-signed Inno EXE",
        "vibemix-installer.exe",
        "installer/windows/README.md",
        "docs/release-process.md",
    ):
        assert phrase in body


def test_windows_user_facing_docs_do_not_name_old_msi_installer():
    for rel in (
        "docs/install/windows-smartscreen.md",
        "docs/threat-model.md",
    ):
        body = _read(rel)
        assert "vibemix.msi" not in body
        assert "vibemix-setup.msi" not in body
        assert "vibemix-installer.exe" in body


def test_release_process_does_not_treat_old_autonomous_rc_as_current_path():
    body = _read("docs/release-process.md")
    stale = (
        "v7.0",
        "OSS-04",
        "WITHOUT blocking on the external signature clock",
        "v0.1.0-rc1",
    )
    for phrase in stale:
        assert phrase not in body
    for phrase in (
        "historical pre-stage contract, not permission to publish",
        "fresh-machine install rehearsal pass",
        "friend-installable",
    ):
        assert phrase in body


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


def test_pretag_check_has_all_eight_steps():
    body = _read("scripts/dist/pretag_check.sh")
    for i in range(1, 9):
        assert f"[{i}/8]" in body, f"step {i}/8 missing"
    assert "scripts/dist/check_sidecar_bundle_ready.py" in body


def test_pretag_check_uses_required_secrets_list():
    body = _read("scripts/dist/pretag_check.sh")
    for s in (
        "APPLE_DEVELOPER_ID",
        "APPLE_DEVELOPER_ID_PASSWORD",
        "APPLE_DEVELOPER_ID_KEYCHAIN_PASSWORD",
        "APPLE_API_KEY_ID",
        "APPLE_API_KEY_ISSUER",
        "APPLE_API_KEY_P8",
        "SIGNPATH_API_TOKEN",
        "SIGNPATH_SIGNTOOL_CMD",
        "TAURI_UPDATER_PRIVATE_KEY",
        "TAURI_UPDATER_KEY_PASSWORD",
    ):
        assert s in body
    assert "APPLE_APP_PASSWORD" not in body
    assert "APPLE_ID" not in body
    assert "APPLE_DEVELOPER_ID_P12_PASSWORD" not in body
    assert "TAURI_UPDATER_PRIVATE_KEY_PASSWORD" not in body


def test_workflow_readme_uses_current_release_secret_inventory():
    body = _read(".github/workflows/README.md")
    for s in (
        "APPLE_DEVELOPER_ID",
        "APPLE_DEVELOPER_ID_P12_BASE64",
        "APPLE_DEVELOPER_ID_PASSWORD",
        "APPLE_DEVELOPER_ID_KEYCHAIN_PASSWORD",
        "APPLE_TEAM_ID",
        "APPLE_API_KEY_ID",
        "APPLE_API_KEY_ISSUER",
        "APPLE_API_KEY_P8",
        "SIGNPATH_API_TOKEN",
        "SIGNPATH_ORGANIZATION_ID",
        "SIGNPATH_PROJECT_SLUG",
        "SIGNPATH_SIGNING_POLICY_SLUG",
        "SIGNPATH_SIGNTOOL_CMD",
        "TAURI_UPDATER_PRIVATE_KEY",
        "TAURI_UPDATER_KEY_PASSWORD",
        "BRAVOH_MANIFEST_UPLOAD_TOKEN",
    ):
        assert s in body
    assert "16-secret inventory" in body
    assert "Total: **16 secrets**" in body
    assert "14-secret inventory" not in body


def test_ship_runbook_uses_canonical_updater_password_secret():
    body = _read("docs/ship-runbook.md")
    assert "TAURI_UPDATER_KEY_PASSWORD" in body
    assert "TAURI_UPDATER_PRIVATE_KEY_PASSWORD" not in body


def test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback():
    docs = (
        "CLAUDE.md",
        ".planning/codebase/STACK.md",
        ".planning/PROJECT.md",
        ".planning/ROADMAP.md",
        ".planning/REQUIREMENTS.md",
        ".planning/phases/v8.2-STATUS.md",
    )
    forbidden = (
        "explicit Gemini fallback",
        "Gemini fallback",
        "explicit fallback",
        "local Codex default, Gemini fallback",
        "Gemini as the built-in fallback",
        "Gemini remains the live/TTS brain and fallback",
        "Gemini live/TTS brain + fallback",
        "Gemini conversational brain/fallback",
        "Gemini stays for live/TTS and fallback",
        "fallback for Viber",
        "Gemini is fallback",
        "Gemini + Codex/MCP + Telegram inherit",
        "built-in fn-calling fallback",
        "runs the Gemini agent",
        "--backend codex|gemini",
        "`--backend gemini|codex`",
        "`--backend codex|gemini`",
    )
    for rel in docs:
        body = _read(rel)
        for phrase in forbidden:
            assert phrase not in body, f"{rel} still has stale Viber backend wording: {phrase}"

    state_head = "\n".join(_read(".planning/STATE.md").splitlines()[:320])
    state_forbidden = (
        *forbidden,
        "Phase 88 (UI) DEFERRED",
        "Next: live app/UI wiring verification",
    )
    for phrase in state_forbidden:
        assert phrase not in state_head, (
            f"STATE head still has stale Viber backend wording: {phrase}"
        )

    # The two v8.2-era STATE.md-head pins ("Phase 88 (UI) is now wired…", "Next:
    # packaged fresh-install/updater rehearsal") were removed — STATE.md has
    # legitimately advanced to milestone v11.0 "Earned". The enduring contract this
    # test protects (Viber pinned to local Codex, no Gemini fallback) is still
    # enforced by the forbidden-phrase scan above + the source-doc pins below.
    assert "Library/Viber uses local Codex" in _read(".planning/codebase/STACK.md")
    assert "local Codex is the current Viber set-prep/chat path" in _read(".planning/PROJECT.md")
    assert "Viber set-prep/chat uses local Codex" in _read(".planning/ROADMAP.md")
    assert "local Codex (Viber)" in _read(".planning/REQUIREMENTS.md")  # v11.0 wording
    assert "local Codex for set-prep/chat demo/test" in _read(".planning/phases/v8.2-STATUS.md")


def test_active_surfaces_separate_viber_agent_from_sven_cohost():
    docs = (
        "README.md",
        "AGENTS.md",
        "src/vibemix/__main__.py",
        "src/vibemix/library/codex_curate.py",
        "tauri/ui/library.html",
        "tauri/ui/src/library/api.ts",
        "tauri/ui/src/library/library.css",
    )
    forbidden = (
        "Set-Prep Co-Host Flow",
        "set-prep co-host",
        "conversational co-host",
        "Viber co-host",
        "tool-using DJ co-host",
        "Viber (the co-host",
        "co-host's voice",
        "Gemini-TTS-streamed voice",
        "Gemini path for grounded reactions and TTS",
    )
    for rel in docs:
        body = _read(rel)
        for phrase in forbidden:
            assert phrase not in body, f"{rel} blurs the Viber/Sven product boundary: {phrase}"
