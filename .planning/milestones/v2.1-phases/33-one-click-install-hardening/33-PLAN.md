# Phase 33 — One-Click Install Hardening — PLAN

**Status:** Ready to execute
**Plans:** 9 (33-01 → 33-09)
**Mode:** `gsd-autonomous fully` — scaffold + tests in scope; VM smokes deferred via KAAN-ACTION-LEGAL.md

---

## Cross-cutting rules

1. **POC files (`cohost*.py`, `mascot.html`) UNTOUCHED.**
2. **Bundle ID `world.bravoh.vibemix` IS A LOCK — never edit `tauri.conf.json` identifier.**
3. **No API key entry surface, ever** (memory `project_one_click_install_hard_req`).
4. **Atomic commits per plan.**
5. **Tests against synthetic fixtures only.**
6. **Wizard pattern matches v2.0 Phase 11 + Phase 32 consent toggle (vanilla TS, CDJ Whisper visual).**

---

## Plan 33-01 — TCC deep-link wizard (INSTALL-01 / P50)

**REQ-IDs:** INSTALL-01

**Edits:**
- NEW `tauri/ui/src/wizard/components/tcc-permissions.ts`:
  - Export `tccDeepLinkFor(macOSMajor: number, permission: 'microphone'|'screen-recording'|'accessibility'|'automation'): string`.
  - Per-version path ladder per 33-RESEARCH.md.
  - Fallback to `x-apple.systempreferences:com.apple.preference.security` when major is unknown.
  - Export `tccCopyFor(permission)` returning the "Why we need this" string (2-3 sentences, plain English, no slop).
- NEW `tauri/ui/src/wizard/__tests__/tcc-permissions.spec.ts`:
  - `test_tcc_deep_link_macos_12_3_microphone` — returns 12.3-style URL.
  - `test_tcc_deep_link_macos_14_microphone` — returns 14-style URL.
  - `test_tcc_deep_link_macos_15_microphone` — returns 15-style URL (extension scheme).
  - `test_tcc_deep_link_unknown_version_returns_fallback`.
  - `test_tcc_copy_present_for_all_four_permissions` — non-empty + no AI slop words.

**Acceptance:** all new tests pass.

---

## Plan 33-02 — tauri-plugin-macos-permissions wire (INSTALL-02)

**REQ-IDs:** INSTALL-02

**Edits:**
- `tauri/src-tauri/Cargo.toml`:
  - Add `tauri-plugin-macos-permissions = "2.3.0"` under `[target.'cfg(target_os = "macos")'.dependencies]`.
- `tauri/src-tauri/src/lib.rs` (or `main.rs`):
  - Register plugin in `Builder::default().plugin(...)` chain, macOS-only via `#[cfg(target_os = "macos")]`.
- `tauri/src-tauri/capabilities/default.json`:
  - Allowlist `macos-permissions:default` + the two commands the wizard calls (`check_permission`, `request_permission`).
- NEW `tests/security/test_tauri_plugin_macos_permissions_wired.py`:
  - `test_cargo_toml_pins_plugin_version` — regex grep for exact pin.
  - `test_lib_rs_registers_plugin_on_macos_only` — cfg guard present.
  - `test_capabilities_allowlists_plugin_commands`.

**Acceptance:** all new tests pass; `cargo check` on macOS still parses.

---

## Plan 33-03 — BlackHole 2ch auto-detect + install button (INSTALL-03)

**REQ-IDs:** INSTALL-03

**Edits:**
- NEW `src/vibemix/install/blackhole_probe.py`:
  - `probe_blackhole() -> dict` returns `{"installed": bool, "device_name": str|None}`.
  - Uses `sounddevice.query_devices()` substring match for `"BlackHole"`.
- IPC schema add `install.blackhole_probe` (req/resp).
- NEW `tauri/ui/src/wizard/components/blackhole-step.ts`:
  - Calls IPC probe; if absent, renders "Install BlackHole 2ch" button → `open` shell command to `https://existential.audio/blackhole/`.
  - Skip-able with warning toast if user wants to advance without (Linux/Windows future-proofing — currently macOS only).
- NEW tests:
  - `tests/install/test_blackhole_probe.py` — synthetic CoreAudio mock returns absent + present cases.
  - `tauri/ui/src/wizard/__tests__/blackhole-step.spec.ts` — button surfaces when probe returns absent; hides when present.

**Acceptance:** all new tests pass.

---

## Plan 33-04 — Defender SmartScreen scaffold + KB fallback (INSTALL-04 — Phase 38 dep)

**REQ-IDs:** INSTALL-04

**Edits:**
- NEW `docs/install/windows-smartscreen.md` — user-facing "How to allow vibemix on Windows" doc with screenshots placeholder + Defender SmartScreen KB explanation.
- NEW `tauri/ui/src/wizard/components/windows-smartscreen-step.ts`:
  - Windows-only step. Detects via platform check. Shows brief explainer + "Open install doc" button.
  - When binary is SignPath-signed (Phase 38 secrets land), this step auto-skips (signed = no SmartScreen prompt).
- NEW `tests/install/test_windows_smartscreen_doc.py`:
  - `test_doc_exists_and_mentions_smartscreen`.
  - `test_doc_does_not_promise_no_warning` — honesty gate.

**Acceptance:** new tests pass; doc renders.

---

## Plan 33-05 — First-launch onboarding ≤60s scaffold + stopwatch (INSTALL-05)

**REQ-IDs:** INSTALL-05

**Edits:**
- NEW `tauri/ui/src/wizard/onboarding-flow.ts`:
  - Orchestrates TCC → audio device pick → controller probe → AI test reaction.
  - Reuses 33-01 TCC component + 33-03 BlackHole step + existing Phase 11 audio-device + Phase 23 controller probe.
- NEW `tauri/ui/src/wizard/onboarding-stopwatch.ts`:
  - Reads `performance.now()` at step start + completion.
  - Emits `onboarding.timing` IPC event with per-step + total.
- NEW `tauri/ui/src/wizard/__tests__/onboarding-flow.spec.ts`:
  - `test_onboarding_flow_visits_all_four_steps`.
  - `test_onboarding_emits_timing_event_on_completion`.
  - `test_onboarding_step_skip_propagates_warning`.

**Acceptance:** all new tests pass. Real-hardware ≤60s is Kaan-action.

---

## Plan 33-06 — TCC revoke mid-session graceful degrade (INSTALL-06 / P71)

**REQ-IDs:** INSTALL-06

**Edits:**
- NEW `tauri/ui/src/runtime/tcc-watcher.ts`:
  - Subscribes to plugin-emitted TCC change events.
  - On revoke → emits `runtime.permission_lost` IPC.
- `tauri/ui/src/session/session-loop.ts` (extend):
  - Handler for `runtime.permission_lost` → pause audio capture + toast "Microphone access lost — paused" + offer re-grant button.
- NEW `tauri/ui/src/runtime/__tests__/tcc-watcher.spec.ts`:
  - `test_tcc_revoke_event_triggers_pause`.
  - `test_tcc_revoke_renders_toast_and_re_grant_button`.
  - `test_tcc_revoke_does_not_crash_session`.

**Acceptance:** all new tests pass.

---

## Plan 33-07 — Bundle ID CI grep gate (INSTALL-07 / P63)

**REQ-IDs:** INSTALL-07

**Edits:**
- NEW `tests/security/test_bundle_id_locked.py`:
  - `test_tauri_conf_identifier_is_world_bravoh_vibemix` — reads JSON, asserts exact match.
  - `test_no_other_identifier_in_repo` — grep for any other `identifier` JSON value (excluding lockfiles).
- NEW `.github/workflows/bundle-id-lock.yml`:
  - Runs `python tests/security/test_bundle_id_locked.py` directly on every PR.
- NEW `tests/install/test_v2_0_to_v2_1_upgrade.py`:
  - Mock `~/Library/Application Support/world.bravoh.vibemix/` path; assert TCC state carries forward across mock version bump.

**Acceptance:** all new tests pass; no other bundle identifier surfaces.

---

## Plan 33-08 — Fresh-VM rehearsal scaffold + tart matrix (INSTALL-08)

**REQ-IDs:** INSTALL-08

**Edits:**
- NEW `scripts/install_rehearsal/mac_vm_setup.sh`:
  - tart spin-up commands for macOS 12.3 / 14 / 15.
  - HARD GUARD: bails out if `tart` not on PATH OR if `INSTALL_REHEARSAL_REAL=1` env not set.
- NEW `scripts/install_rehearsal/win_vm_setup.ps1`:
  - VM provisioning skeleton (placeholder URLs to ISO sources).
- NEW `scripts/install_rehearsal/rehearsal_runner.py`:
  - `argparse` orchestrator: `--matrix mac|win|all`, `--dry-run` default.
  - Without `--real`, prints what it would do.
- NEW `.github/workflows/install-rehearsal.yml`:
  - `workflow_dispatch` + nightly cron @ 03:00 UTC.
  - Calls `rehearsal_runner.py --dry-run` in CI (synthetic only).
- NEW `tests/install/test_rehearsal_scaffold.py`:
  - `test_mac_vm_setup_sh_exists_and_guards_real_runs`.
  - `test_win_vm_setup_ps1_exists`.
  - `test_rehearsal_runner_dry_run_does_not_invoke_tart`.
  - `test_workflow_yml_is_workflow_dispatch_or_nightly_only`.
- NEW `KAAN-ACTION-LEGAL.md` entries for real VM execution + macOS license disk requirements.

**Acceptance:** scaffold tests pass; real VM execution stays Kaan-action.

---

## Plan 33-09 — API-key-surface assertion + grep gate (INSTALL-09)

**REQ-IDs:** INSTALL-09

**Edits:**
- NEW `tests/security/test_no_api_key_surface.py`:
  - Glob all `tauri/ui/src/**/*.ts` + `.tsx` + `.html` + `.vue` (whatever exists).
  - Regex grep against input/label/placeholder text containing: `AIza`, `api[ _-]?key`, `gemini[ _-]?key`, `api_token`.
  - Fail with file:line if any match.
  - `test_no_api_key_input_field_in_wizard_or_settings`.
  - `test_no_api_key_label_text_anywhere_in_ui`.
- NEW `.github/workflows/no-api-key-surface.yml` — CI gate runs grep on PR.

**Acceptance:** grep returns zero matches across current UI surface; tests pass.

---

## Hard gates (collected from CONTEXT)

| Gate | Plan |
|------|------|
| TCC deep-link ladder correct for 12.3/14/15 | 33-01 |
| `tauri-plugin-macos-permissions` pinned + wired | 33-02 |
| BlackHole probe surfaces install button when absent | 33-03 |
| Defender SmartScreen doc + step scaffolded | 33-04 |
| Onboarding flow visits 4 steps + emits stopwatch | 33-05 |
| TCC revoke event → pause + toast + no crash | 33-06 |
| Bundle ID locked + grep gate | 33-07 |
| Fresh-VM rehearsal scaffold (real runs Kaan-action) | 33-08 |
| Zero API key entry surfaces anywhere | 33-09 |

Each plan = one atomic commit. Final verification runs the new test files together.
