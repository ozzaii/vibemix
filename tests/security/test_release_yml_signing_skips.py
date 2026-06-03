# SPDX-License-Identifier: Apache-2.0
"""Phase 38 / DIST-15 + DIST-16 — release.yml empty-secret skip annotations.

Confirms that the Apple notarytool + SignPath legs of release.yml carry the
empty-secret skip pattern (CONTEXT §Apple notarytool wiring + §SignPath wiring).

The actual sign steps are gated on `SIGNING_AVAILABLE == 'true'`. Phase 38 adds
EXPLICIT annotation steps that fire on the inverse condition and emit
`::warning::` lines pointing at KAAN-ACTION-LEGAL.md.

These tests parse the workflow YAML and assert structure — no `act`/`gh`
execution required.
"""

from __future__ import annotations

import json
import os
import re
import stat
import subprocess
from pathlib import Path

import pytest

try:
    import yaml  # PyYAML — listed as a test-time dep in conftest
except ImportError:  # pragma: no cover
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_YML = REPO_ROOT / ".github/workflows/release.yml"


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return RELEASE_YML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow_yaml(workflow_text: str):
    if yaml is None:
        pytest.skip("PyYAML not installed")
    # The workflow has the GitHub Actions `on:` key which YAML coerces to True.
    return yaml.safe_load(workflow_text)


# ---------------------------------------------------------------------------
# 38-01 — Apple notarytool wiring annotation
# ---------------------------------------------------------------------------

def test_release_yml_apple_skip_step_exists(workflow_text: str):
    """The Apple-leg empty-secret annotation step must exist by name."""
    assert "SIGN — Apple notarytool wiring annotation (empty-secret skip)" in workflow_text


def test_release_yml_notarytool_invocation_present(workflow_text: str):
    """The actual notarytool invocation must still be wired (via sign_macos.sh)."""
    # sign_macos.sh is the canonical entrypoint; the comment header in release.yml
    # explicitly names notarytool.
    assert "notarytool" in workflow_text
    assert "scripts/dist/sign_macos.sh" in workflow_text


def test_release_yml_apple_sign_step_guarded_by_signing_available(workflow_yaml):
    """The SIGN+PACKAGE step on macOS MUST be guarded by SIGNING_AVAILABLE."""
    build_macos = workflow_yaml["jobs"]["build-macos"]
    steps = build_macos["steps"]
    sign_step = next(
        (s for s in steps if "SIGN + PACKAGE" in s.get("name", "")),
        None,
    )
    assert sign_step is not None, "SIGN + PACKAGE step not found"
    assert sign_step["if"] == "env.SIGNING_AVAILABLE == 'true' && env.DRY_RUN != 'true'"


def test_release_yml_macos_build_does_not_pre_sign_before_sidecar_codesign(workflow_yaml):
    """Tauri must not notarize before sign_macos.sh signs PyInstaller sidecar contents."""
    build_macos = workflow_yaml["jobs"]["build-macos"]
    steps = build_macos["steps"]
    build_step = next(
        (s for s in steps if s.get("name") == "BUILD — Tauri app (cargo tauri build)"),
        None,
    )
    assert build_step is not None, "macOS Tauri build step not found"
    run = build_step["run"]
    assert "cargo tauri build" in run
    assert "--bundles app" in run
    assert "--no-sign" in run
    assert "--ci" in run
    assert "--bundles dmg" not in run


def test_release_yml_detects_complete_apple_secret_group(workflow_text: str):
    """Full-release mode must not start with a partial Apple signing setup."""
    for secret in (
        "APPLE_DEVELOPER_ID",
        "APPLE_DEVELOPER_ID_P12_BASE64",
        "APPLE_DEVELOPER_ID_PASSWORD",
        "APPLE_DEVELOPER_ID_KEYCHAIN_PASSWORD",
        "APPLE_TEAM_ID",
        "APPLE_API_KEY_ID",
        "APPLE_API_KEY_ISSUER",
        "APPLE_API_KEY_P8",
    ):
        assert f"secrets.{secret} != ''" in workflow_text
    assert "HAS_APPLE:" not in workflow_text


def test_sign_macos_materializes_ci_signing_secrets():
    script = (REPO_ROOT / "scripts/dist/sign_macos.sh").read_text(encoding="utf-8")
    assert "APPLE_DEVELOPER_ID_P12_BASE64" in script
    assert "APPLE_DEVELOPER_ID_PASSWORD" in script
    assert "APPLE_DEVELOPER_ID_KEYCHAIN_PASSWORD" in script
    assert "APPLE_API_KEY_P8" in script
    assert 'APPLE_API_KEY_PATH="$CI_TMP_DIR/AuthKey.p8"' in script
    assert "security create-keychain" in script
    assert "security import" in script
    assert "security set-key-partition-list" in script
    assert "Developer ID identity not imported into CI keychain" in script


def test_macos_signing_repairs_sidecar_symlinks_before_codesign():
    script = (REPO_ROOT / "scripts/dist/sign_macos.sh").read_text(encoding="utf-8")
    repair = "repair_macos_app_sidecar_symlinks.py"
    stage2 = 'stage 2 "force-sign every nested Mach-O'
    assert repair in script
    assert stage2 in script
    assert script.index(repair) < script.index(stage2)


def test_sign_macos_asserts_developer_id_resource_seal():
    script = (REPO_ROOT / "scripts/dist/sign_macos.sh").read_text(encoding="utf-8")
    assert "assert_developer_id_signature()" in script
    assert "Authority=Developer ID Application:" in script
    assert "TeamIdentifier=$APPLE_TEAM_ID" in script
    assert "Contents/_CodeSignature/CodeResources" in script
    assert 'assert_developer_id_signature "$APP" ".app bundle"' in script
    assert 'assert_developer_id_signature "$DMG_OUT" "DMG"' in script


def test_sign_macos_assesses_stapled_dmg_not_source_app():
    script = (REPO_ROOT / "scripts/dist/sign_macos.sh").read_text(encoding="utf-8")
    assert "Gatekeeper acceptance for stapled DMG" in script
    assert "--type open --context context:primary-signature" in script
    assert 'spctl --assess --type open --context context:primary-signature --verbose=4 "$DMG_OUT"' in script
    assert "Gatekeeper acceptance for signed .app" in script


def test_release_yml_skip_on_empty_apple_secret(workflow_yaml):
    """The Apple annotation step fires on the inverse condition."""
    build_macos = workflow_yaml["jobs"]["build-macos"]
    steps = build_macos["steps"]
    skip_step = next(
        (s for s in steps if "Apple notarytool wiring annotation" in s.get("name", "")),
        None,
    )
    assert skip_step is not None, "Apple notarytool wiring annotation step missing"
    assert skip_step["if"] == "env.SIGNING_AVAILABLE != 'true'"
    # The step must reference KAAN-ACTION-LEGAL.md so operators can find the runbook.
    assert "KAAN-ACTION-LEGAL.md" in skip_step["run"]
    assert "DIST-09" in skip_step["run"]


def test_release_yml_repairs_macos_sidecar_symlinks_before_signing(workflow_yaml):
    build_macos = workflow_yaml["jobs"]["build-macos"]
    steps = build_macos["steps"]
    names = [step.get("name", "") for step in steps]
    repair_index = names.index("PACKAGE — Repair macOS app sidecar symlinks")
    verify_index = names.index("VERIFY — macOS app bundle sidecar ready")
    sign_index = names.index("SIGN + PACKAGE — codesign / create-dmg / notarytool / stapler")
    dmg_verify_index = names.index("VERIFY — macOS DMG drag-install sidecar ready")
    updater_index = names.index("PACKAGE — Create Tauri macOS updater artifact (.app.tar.gz)")
    updater_verify_index = names.index("VERIFY — macOS updater artifact extracts to ready app")
    assert repair_index < verify_index < sign_index
    assert sign_index < dmg_verify_index < updater_index
    assert updater_index < updater_verify_index
    assert "repair_macos_app_sidecar_symlinks.py" in steps[repair_index]["run"]
    assert "check_macos_app_bundle_ready.py" in steps[verify_index]["run"]
    assert "--smoke version" in steps[verify_index]["run"]
    assert "--require-moss-source" in steps[verify_index]["run"]
    assert "check_macos_dmg_artifact_ready.py" in steps[dmg_verify_index]["run"]
    assert "-name 'vibemix-*.dmg'" in steps[dmg_verify_index]["run"]
    assert "--require-moss-source" in steps[dmg_verify_index]["run"]
    assert "--require-developer-id" in steps[dmg_verify_index]["run"]
    assert "check_macos_updater_artifact_ready.py" in steps[updater_verify_index]["run"]
    assert "-name '*.app.tar.gz'" in steps[updater_verify_index]["run"]
    assert "--require-moss-source" in steps[updater_verify_index]["run"]
    assert "--require-developer-id" in steps[updater_verify_index]["run"]


# ---------------------------------------------------------------------------
# 38-02 — SignPath wiring annotation (filled in by Plan 38-02)
# ---------------------------------------------------------------------------

def test_release_yml_signpath_skip_step_exists(workflow_text: str):
    assert "SIGN — SignPath wiring annotation (empty-secret skip)" in workflow_text


def test_release_yml_signpath_action_pinned_version(workflow_text: str):
    """The SignPath GH Action must be SHA-pinned (post-DEPS-07 discharge)."""
    m = re.search(
        r"uses:\s*signpath/github-action-submit-signing-request@(\S+)",
        workflow_text,
    )
    assert m is not None, "SignPath GH Action reference not found"
    ref = m.group(1)
    # Post-DEPS-07: refs are 40-char SHA, version tag carried in trailing comment.
    assert re.fullmatch(r"[0-9a-f]{40}", ref), (
        f"SignPath action must be SHA-pinned (got {ref!r}); see pinact discharge"
    )
    assert re.search(
        r"signpath/github-action-submit-signing-request@[0-9a-f]{40}\s+#\s+v\d",
        workflow_text,
    ), "SignPath action SHA must carry a trailing `# vN.N` version comment"


def test_release_yml_signpath_sign_step_guarded_by_signing_available(workflow_yaml):
    build_windows = workflow_yaml["jobs"]["build-windows"]
    steps = build_windows["steps"]
    sign_step = next(
        (s for s in steps if "Submit signing request to SignPath" in s.get("name", "")),
        None,
    )
    assert sign_step is not None, "SignPath submission step missing"
    assert sign_step["if"] == "env.SIGNING_AVAILABLE == 'true' && env.DRY_RUN != 'true'"


def test_release_yml_skip_on_empty_signpath_secret(workflow_yaml):
    """The SignPath annotation step fires on the inverse condition."""
    build_windows = workflow_yaml["jobs"]["build-windows"]
    steps = build_windows["steps"]
    skip_step = next(
        (s for s in steps if "SignPath wiring annotation" in s.get("name", "")),
        None,
    )
    assert skip_step is not None, "SignPath wiring annotation step missing"
    assert skip_step["if"] == "env.SIGNING_AVAILABLE != 'true'"
    assert "KAAN-ACTION-LEGAL.md" in skip_step["run"]
    assert "DIST-11" in skip_step["run"]


# ---------------------------------------------------------------------------
# Updater manifest signing contract
# ---------------------------------------------------------------------------

def test_release_yml_manifest_signer_uses_tauri_updater_artifacts(workflow_text: str):
    """latest.json must point at Tauri updater artifacts, not first-install media."""
    assert "VIBEMIX_DMG_NAME: vibemix-${{ github.ref_name }}-${{ matrix.arch }}.dmg" in workflow_text
    assert "scripts/dist/create_macos_updater_artifact.sh" in workflow_text
    assert "cargo tauri build --bundles nsis --no-sign" in workflow_text
    assert "tauri/src-tauri/target/${{ matrix.rust_target }}/release/bundle/macos/*.app.tar.gz" in workflow_text
    assert "tauri/src-tauri/target/release/bundle/nsis/*setup*.exe" in workflow_text
    assert "DMG=$(find release-artifacts/macos-artifacts-arm64 -type f -name 'vibemix-*.dmg'" in workflow_text
    assert "WIN_INSTALLER=$(find release-artifacts/windows-artifacts -type f -name 'vibemix-installer.exe'" in workflow_text
    assert "Verify Windows updater — DIST-17 require-signed gate" in workflow_text
    assert "WIN_UPDATER=$(find release-artifacts/windows-artifacts -type f -name '*setup*.exe' ! -name 'vibemix-installer.exe'" in workflow_text
    assert "MACOS_ARM64_UPDATER=$(find release-artifacts/macos-artifacts-arm64 -type f" in workflow_text
    assert "MACOS_X86_64_UPDATER=$(find release-artifacts/macos-artifacts-x86_64 -type f" in workflow_text
    assert "-name '*.app.tar.gz'" in workflow_text
    assert "WIN_UPDATER=$(find release-artifacts/windows-artifacts -type f" in workflow_text
    assert "-name '*setup*.exe'" in workflow_text
    assert "-name '*.msi'" not in workflow_text
    assert "! -name 'vibemix-installer.exe'" in workflow_text
    assert "not the DMG" in workflow_text
    assert "not the Inno vibemix-installer.exe" in workflow_text
    assert "or MSI" not in workflow_text
    assert '--macos-artifact "$MACOS_ARM64_UPDATER"' in workflow_text
    assert '--macos-x86_64-artifact "$MACOS_X86_64_UPDATER"' in workflow_text
    assert "--macos-x86_64-url" in workflow_text
    assert '--windows-artifact "$WIN_UPDATER"' in workflow_text
    assert "PUBLISH — Stage flat GitHub Release assets" in workflow_text
    assert "release-artifacts/upload/*" in workflow_text
    assert "release-artifacts/macos-artifacts-arm64/vibemix-*.dmg" not in workflow_text
    assert "-maxdepth 1 -type f -name '*.app.tar.gz'" not in workflow_text


def test_sign_manifest_script_rejects_first_install_artifacts():
    script = (REPO_ROOT / "scripts/dist/sign_manifest.sh").read_text(encoding="utf-8")
    assert "--macos-artifact" in script
    assert "--macos-x86_64-artifact" in script
    assert "--windows-artifact" in script
    assert '"$artifact" 2>/dev/null' in script
    assert '"$url" 2>/dev/null' not in script
    assert ".app.tar.gz" in script
    assert "must not be the Inno first-install EXE" in script
    assert "Tauri MSI" not in script
    assert "*setup*.exe" in script
    assert "darwin-x86_64" in script
    assert "TAURI_UPDATER_KEY_PASSWORD:?" not in script
    assert "${TAURI_UPDATER_KEY_PASSWORD+x}" in script


def test_sign_manifest_script_writes_all_shipped_platform_targets(tmp_path, monkeypatch):
    script = REPO_ROOT / "scripts/dist/sign_manifest.sh"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_npx = fake_bin / "npx"
    fake_npx.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
artifact="${@: -1}"
case "$artifact" in
  *arm64.app.tar.gz) echo "sig-arm64" ;;
  *x86_64.app.tar.gz) echo "sig-x86_64" ;;
  *setup.exe) echo "sig-windows" ;;
  *) echo "unexpected artifact: $artifact" >&2; exit 9 ;;
esac
""",
        encoding="utf-8",
    )
    fake_npx.chmod(fake_npx.stat().st_mode | stat.S_IXUSR)

    mac_arm64 = tmp_path / "vibemix-0.1.0-arm64.app.tar.gz"
    mac_x86_64 = tmp_path / "vibemix-0.1.0-x86_64.app.tar.gz"
    windows = tmp_path / "vibemix_0.1.0_x64-setup.exe"
    for artifact in (mac_arm64, mac_x86_64, windows):
        artifact.write_bytes(b"artifact")

    output = tmp_path / "latest.json"
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    env["TAURI_UPDATER_PRIVATE_KEY"] = "ZmFrZS1rZXk="
    env["TAURI_UPDATER_KEY_PASSWORD"] = ""

    subprocess.run(
        [
            str(script),
            "--version",
            "0.1.0",
            "--macos-artifact",
            str(mac_arm64),
            "--macos-url",
            "https://example.test/vibemix-0.1.0-arm64.app.tar.gz",
            "--macos-x86_64-artifact",
            str(mac_x86_64),
            "--macos-x86_64-url",
            "https://example.test/vibemix-0.1.0-x86_64.app.tar.gz",
            "--windows-artifact",
            str(windows),
            "--windows-url",
            "https://example.test/vibemix_0.1.0_x64-setup.exe",
            "--notes",
            "Release v0.1.0",
            "--output",
            str(output),
        ],
        check=True,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert set(manifest["platforms"]) == {
        "darwin-aarch64",
        "darwin-x86_64",
        "windows-x86_64",
    }
    assert manifest["platforms"]["darwin-aarch64"]["signature"] == "sig-arm64"
    assert manifest["platforms"]["darwin-x86_64"]["signature"] == "sig-x86_64"
    assert manifest["platforms"]["windows-x86_64"]["signature"] == "sig-windows"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
