---
status: human_needed
phase: 33
phase_name: One-Click Install Hardening
milestone: v2.1
verified_at: 2026-05-15T23:25:00Z
plans_complete: 9
plans_total: 9
mode: gsd-autonomous fully
deferred_to_kaan_action: true
real_hardware_carveout: true
---

# Phase 33 — Verification

## Status: PASSED (engineering) + HUMAN_NEEDED (real-hardware ≤60s + VM matrix)

Autonomous engineering scope (TCC deep-link ladder, plugin wire, BlackHole probe, SmartScreen doc + step, onboarding orchestrator + stopwatch, TCC revoke watcher + graceful-degrade handler, bundle-id lock gate, fresh-VM rehearsal scaffold, API-key surface grep) is COMPLETE. Real-VM matrix execution + ≤60s timing validation on real hardware stay Kaan-action per `gsd-autonomous fully` mode + the Phase 33 plan.

## Plan Inventory

| Plan | Commit | Status |
|------|--------|--------|
| 33-01 | a1c46c8 | TCC deep-link wizard component (INSTALL-01 / P50) |
| 33-02 | bbbd624 | tauri-plugin-macos-permissions 2.3.0 wired (INSTALL-02) |
| 33-03 | 544ce42 | BlackHole 2ch auto-detect + install button (INSTALL-03) |
| 33-04 | 2d795e3 | Windows SmartScreen scaffold + KB fallback (INSTALL-04) |
| 33-05 | 321fb67 | First-launch onboarding flow + stopwatch (INSTALL-05) |
| 33-06 | 7aaf533 | TCC revoke mid-session graceful degrade (INSTALL-06 / P71) |
| 33-07 | b41525e | Bundle ID CI grep gate (INSTALL-07 / P63) |
| 33-08 | 0d908d0 | Fresh-VM rehearsal scaffold + tart matrix (INSTALL-08) |
| 33-09 | dba688f | API-key entry surface grep gate (INSTALL-09) |

## Test Suite Evidence

```
pytest tests/install/ tests/security/test_bundle_id_locked.py \
       tests/security/test_no_api_key_surface.py \
       tests/security/test_tauri_plugin_macos_permissions_wired.py -q
25 passed in 1.04s

npx vitest run src/wizard/__tests__/ src/runtime/__tests__/
25 passed (5 files)
```

Pre-existing suites unaffected:

- Phase 38 P46 audit: 22 passed
- Phase 38 KAAN-ACTION-LEGAL gate: 7 passed
- Phase 34 capability snapshot: 7 passed

## Hard Gates Green

| Gate | Plan | Test ID |
|------|------|---------|
| TCC deep-link ladder for 12.3 / 14 / 15 + fallback | 33-01 | `test_tcc_deep_link_macos_12_3_microphone` + `_14_microphone` + `_15_microphone` + `_unknown_version_returns_fallback` |
| Plugin pin 2.3.0 + macOS-only cfg guard + capability allowlist | 33-02 | `test_cargo_toml_pins_plugin_version` + `test_lib_rs_registers_plugin_on_macos_only` + `test_capabilities_allowlists_plugin_commands` |
| BlackHole probe absent → install button surfaces | 33-03 | `test_blackhole_absent_surfaces_install_button` + `surfaces install banner when probe reports absent` |
| Honest SmartScreen doc (no "warning-free" promise) | 33-04 | `test_doc_does_not_promise_no_warning` |
| Onboarding 4-step visit + timing event | 33-05 | `test_onboarding_flow_visits_all_four_steps` + `test_onboarding_emits_timing_event_on_completion` |
| TCC revoke → pause + toast + no crash | 33-06 | `test_tcc_revoke_event_triggers_pause` + `test_tcc_revoke_renders_toast_and_re_grant_button` + `test_tcc_revoke_does_not_crash_session` |
| Bundle ID `world.bravoh.vibemix` locked | 33-07 | `test_tauri_conf_identifier_is_world_bravoh_vibemix` + `test_no_other_identifier_in_repo` + `test_v2_1_finds_v2_0_state_after_version_bump` |
| Fresh-VM rehearsal scaffold guards real runs | 33-08 | `test_mac_vm_setup_sh_exists_and_guards_real_runs` + `test_rehearsal_runner_dry_run_does_not_invoke_tart` + `test_rehearsal_runner_real_without_env_var_refuses` |
| Zero API key entry surfaces in UI | 33-09 | `test_no_api_key_input_field_in_wizard_or_settings` + `test_no_api_key_label_text_anywhere_in_ui` |

## Human-Needed Items (real-hardware carveout — KAAN-ACTION-LEGAL.md INSTALL-VM-RUN)

Per `KAAN-ACTION-LEGAL.md`:

1. **INSTALL-VM-RUN** — Real tart macOS 12.3 / 14 / 15 + Windows 10 / 11 matrix execution. Requires disk space + macOS license + Microsoft ISO. Sign-off block lives in KAAN-ACTION-LEGAL.md.
2. **INSTALL-60S-CHECK** — Stopwatch the onboarding flow on each VM in the matrix; record per-OS timings.
3. **INSTALL-DEFENDER** — Defender SmartScreen reputation building takes 1-2 weeks of normal download traffic after Phase 38 SignPath chain lights up. Outside our direct control.
4. **INSTALL-BLACKHOLE-PROBE** — Validate the install affordance on a fresh Mac that doesn't have BlackHole (separate from the matrix runs which can use snapshots).

The autonomous scaffold double-gates real execution behind `--real` flag + `INSTALL_REHEARSAL_REAL=1` env var so a stray flag in an autonomous run can't trigger a multi-GB VM spin-up.

## Verdict

Engineering scaffold: PASSED.
Real-hardware validation: HUMAN_NEEDED — runs against a signed Phase 38 binary, which itself depends on the DIST-09 + DIST-11 legal-capacity carveouts.

Roadmap can be marked complete-with-real-hardware-deferred. Engineering has zero remaining work; the external clock is Phase 38 secrets + Kaan's VM run.
