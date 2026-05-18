# Phase 49 Plan 04 — Summary

**Status:** complete
**Date:** 2026-05-18

## Files modified

- `installer/windows/vibemix-installer.iss` — [Files] entries for companion/ + [Run] entry for fetch_drivers.ps1 + [UninstallRun] for uninstall.ps1 + [Code] VB-CABLE license dialog
- `installer/macos/firstrun_companion.sh` (NEW) — Mac first-launch hook (BlackHole .pkg cannot be DMG-bundled legally)
- `tauri/src-tauri/src/wizard_cmds.rs` (NEW) — 3 Tauri commands: run_companion_fetch / run_audio_config / open_audio_settings
- `tauri/src-tauri/src/main.rs` — registered wizard_cmds module + 3 commands in invoke_handler
- `tauri/src-tauri/capabilities/default.json` — extended `shell:allow-execute` with 5 new arg-validators (bash, powershell, python3, open, control.exe); zero new permission identifier
- `tests/install/test_iss_companion_run.py` (NEW) — 6 tests pass
- `tests/install/test_dmg_postinstall_hook.py` (NEW) — 6 tests pass

## Requirements satisfied

- INSTALL-02 (Win EXE → companion fetch + UAC license dialog wired into Inno Setup chain)
- INSTALL-06 (MSI emerges via existing Inno Setup → SignPath chain; INSTALL_READY emit from Plan 03)

## Notes

- **Tauri MSI target**: not added to `tauri.conf.json5` `bundle.targets` — the MSI is produced by Inno Setup via the rename trick documented in the existing `.iss` (see comment at line 65-72 of vibemix-installer.iss). Adding `msi` to Tauri targets would create a parallel MSI build that conflicts with the SignPath chain. Decision: keep Inno Setup as the sole Win bundle producer. ROADMAP P49 Success #2 satisfied through the existing chain.
- **uninstall.ps1**: referenced by Inno Setup `[UninstallRun]` + `[Files]`. Body lives in Plan 06.

## Verification

`pytest tests/install/test_iss_companion_run.py tests/install/test_dmg_postinstall_hook.py` — 12/12 pass.

## Kaan-action carry-forward

None new — all flow into §INSTALL-VM-RUN.
