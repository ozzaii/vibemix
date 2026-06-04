"""Static guards for the Windows app payload and installer path contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_YML = ROOT / ".github" / "workflows" / "release.yml"
RELEASE_PROCESS = ROOT / "docs" / "release-process.md"
UPDATER_DOC = ROOT / "docs" / "updater.md"
POST_LAUNCH_PLAYBOOK = ROOT / "docs" / "post-launch-playbook.md"
BUILD_LOCAL = ROOT / "scripts" / "win" / "build_local.ps1"
STAGE_SCRIPT = ROOT / "scripts" / "win" / "stage_app_payload.ps1"
PAYLOAD_CHECK = ROOT / "scripts" / "dist" / "check_windows_app_payload_ready.py"
ISS = ROOT / "installer" / "windows" / "vibemix-installer.iss"
TAURI_CONF = ROOT / "tauri" / "src-tauri" / "tauri.conf.json5"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_release_workflow_uses_staged_windows_app_payload() -> None:
    text = _read(RELEASE_YML)
    assert "scripts/win/stage_app_payload.ps1" in text
    assert "scripts/dist/check_windows_app_payload_ready.py" in text
    assert "--require-chatterbox-ref" in text
    assert "VERIFY — Windows app payload sidecar ready" in text
    assert "dist/windows-app/**" in text
    assert "cargo tauri build --no-bundle" in text
    assert '$target = "dist/windows-app"' in text
    assert "output/vibemix-installer.exe" in text
    assert "/DInstallerOutputDir=..\\..\\output" in text
    assert "/DOutputDir=..\\..\\output" not in text
    assert "vibemix-installer.msi" not in text
    assert "dist/vibemix/vibemix.exe" not in text
    assert "dist\\vibemix\\vibemix.exe" not in text


def test_release_workflow_registers_inno_signpath_tool() -> None:
    text = _read(RELEASE_YML)
    assert "HAS_SIGNPATH_SIGNTOOL_CMD" in text
    assert "SIGNPATH_SIGNTOOL_CMD: ${{ secrets.SIGNPATH_SIGNTOOL_CMD }}" in text
    assert '"/Ssignpath=$signTool"' in text
    assert "SignTool=signpath" in _read(ISS)


def test_release_workflow_authenticode_signs_tauri_windows_updater() -> None:
    text = _read(RELEASE_YML)
    assert "SIGN — Authenticode-sign Tauri NSIS updater installer" in text
    assert "SIGNPATH_SIGNTOOL_CMD: ${{ secrets.SIGNPATH_SIGNTOOL_CMD }}" in text
    assert "$signTool.Contains('$f')" in text
    assert 'Get-ChildItem -Path "tauri\\src-tauri\\target\\release\\bundle\\nsis"' in text
    assert '-Filter "*setup*.exe"' in text
    assert "$expanded = $signTool.Replace('$f', $quoted)" in text
    assert "& cmd.exe /S /C $expanded" in text


def test_local_windows_build_feeds_inno_from_staged_payload() -> None:
    text = _read(BUILD_LOCAL)
    assert "scripts\\win\\stage_app_payload.ps1" in text
    assert "scripts/dist/check_windows_app_payload_ready.py" in text
    assert "--require-chatterbox-ref" in text
    assert "cargo tauri build --no-bundle" in text
    assert "/DSourceDir=..\\..\\dist\\windows-app" in text
    assert "docs/install-rehearsal.md" in text
    assert "target under 10 minutes total" in text
    assert "target ≤60s" not in text
    assert "INSTALL-05" not in text


def test_stage_script_copies_app_exe_and_sidecar_resource_tree() -> None:
    text = _read(STAGE_SCRIPT)
    assert "dist\\windows-app" in text
    assert '"vibemix.exe"' in text
    assert "x86_64-pc-windows-msvc" in text
    assert "vibemix-core-$SidecarTriple.exe" in text
    assert '"binaries"' in text


def test_windows_app_payload_verifier_checks_exes_and_internal_tree() -> None:
    text = _read(PAYLOAD_CHECK)
    assert "vibemix.exe" in text
    assert "vibemix-core-{triple}.exe" in text
    assert "_internal" in text
    assert "placeholder-only" in text
    assert 'handle.read(2) == b"MZ"' in text
    assert "chatterbox_release_ref_ready" in text


def test_inno_default_source_dir_matches_staged_payload() -> None:
    text = _read(ISS)
    assert '#define SourceDir           "..\\..\\dist\\windows-app"' in text
    assert 'Source: "{#SourceDir}\\*"' in text
    assert "Do not rename it to `.msi`" in text


def test_inno_output_dir_is_ci_overridable() -> None:
    text = _read(ISS)
    assert "#ifndef InstallerOutputDir" in text
    assert '#define InstallerOutputDir  "output"' in text
    assert "OutputDir={#InstallerOutputDir}" in text
    assert "SignedUninstallerDir={#InstallerOutputDir}\\signed-uninstaller" in text


def test_tauri_resources_include_windows_sidecar_glob() -> None:
    text = _read(TAURI_CONF)
    assert "binaries/vibemix-core-x86_64-pc-windows-msvc/**/*" in text


def test_release_process_names_current_windows_updater_artifact() -> None:
    text = _read(RELEASE_PROCESS)
    assert "Windows Tauri NSIS `*setup*.exe`" in text
    assert "or MSI" not in text
    assert "publish-gate signed-artifact verifier" in text
    assert "Do not point `latest.json` at the\n      DMG or Inno `vibemix-installer.exe`." in text


def test_updater_docs_name_nsis_not_msi_for_windows_updater() -> None:
    for path in (UPDATER_DOC, POST_LAUNCH_PLAYBOOK):
        text = _read(path)
        assert "Windows Tauri" in text
        assert "NSIS `*setup*.exe`" in text
        assert "or MSI" not in text
        assert "NSIS/MSI" not in text
