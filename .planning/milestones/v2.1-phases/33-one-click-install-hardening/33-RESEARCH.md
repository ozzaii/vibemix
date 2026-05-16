# Phase 33 — Research

**Date:** 2026-05-15
**Mode:** gsd-autonomous fully (scaffold + tests in scope; VM smokes Kaan-action)
**Status:** Research compact — decisions are already locked in 33-CONTEXT.md. This file captures the tooling pins and reference URLs only.

## Tooling pins

| Tool | Version | Source |
|------|---------|--------|
| `tauri-plugin-macos-permissions` | `2.3.0` | Already locked in STATE.md v2.1 deps. Rust crate. macOS-only target. |
| `tart` | latest | Cirrus-Labs/Tart — macOS VM matrix runner (12.3 / 14 / 15). |
| Apple TCC deep-link scheme | `x-apple.systempreferences:` | macOS 12.3 / 14 / 15 path divergence per CONTEXT.md (P50). |
| BlackHole 2ch | system-level | `https://existential.audio/blackhole/` official installer URL. |

## P50 deep-link verification

macOS 15 (Sequoia) reorganised Settings panes. Per Apple's Settings URL schemes:

- **macOS 12.3 + 14:** `x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone`
- **macOS 15:** `x-apple.settings.PrivacySecurity.extension?Privacy_Microphone`
- **Fallback (any version):** `x-apple.systempreferences:com.apple.preference.security` → opens root Privacy pane; user manually navigates.

The wizard ladder MUST detect macOS major version (e.g. via `sw_vers -productVersion`) and pick the right URL, with the fallback always available.

## tauri-plugin-macos-permissions surface

Plugin exposes Rust + JS bridge for:
- `check_permission(name)` → `granted | denied | not_determined`
- `request_permission(name)` → triggers OS prompt
- `subscribe(callback)` → fires on permission state change (used for INSTALL-06 mid-session revoke)

Permission names of interest: `microphone`, `screen-recording`, `accessibility`, `automation`.

## BlackHole probe surface

CoreAudio enumeration via Python `sounddevice.query_devices()` already proven in v2.0 Phase 11 wizard. Probe checks for substring `"BlackHole"` in device names. Sidecar exposes this via existing `sec_check.py`-style IPC pattern.

## Tart matrix

```yaml
# scripts/install_rehearsal/tart.matrix.yml (illustrative)
mac:
  - macos-12.3
  - macos-14
  - macos-15
windows:
  - windows-10
  - windows-11
```

Real VM runs are Kaan-action (disk + macOS license).

## Pitfall coverage

- **P50** — macOS 15 reorg → version-aware URL ladder + root-Privacy fallback.
- **P63** — bundle ID `world.bravoh.vibemix` LOCKED; CI grep gate on `tauri.conf.json`.
- **P67** — telemetry default-OFF already shipped Phase 34. Re-asserted in INSTALL-09 grep.
- **P69** — universal2 sidecar already shipped Phase 27.
- **P71** — TCC revoke graceful: plugin subscribe + toast + pause, no crash.

## v2.0 → v2.1 upgrade test

Mock the TCC state file path (`~/Library/Application Support/world.bravoh.vibemix/tcc-state.json` or similar). Install v2.0 → grant TCC → bump version → assert TCC carries over (bundle ID stable per P63).

## Citation

- v2.0 Phase 11 wizard skeleton: `tauri/ui/src/wizard/`
- Phase 27 REC-09: universal2 sidecar
- Phase 32 consent toggle pattern: `tauri/ui/src/wizard/step-profile-consent.ts`
- Phase 34 sec_check.py: `runtime/sec_check.py`
- Memory `project_one_click_install_hard_req`
- Pitfalls: P50, P63, P67, P69, P71 (full text in `.planning/research/v2-1/PITFALLS.md`)

## Plan slice (preview for 33-PLAN.md)

9 atomic plans, one per REQ-ID:
1. `33-01` — TCC deep-link wizard (INSTALL-01 / P50)
2. `33-02` — tauri-plugin-macos-permissions wire (INSTALL-02)
3. `33-03` — BlackHole 2ch auto-detect + install button (INSTALL-03)
4. `33-04` — Windows Defender SmartScreen scaffold + KB fallback (INSTALL-04 — Phase 38 dep)
5. `33-05` — First-launch onboarding ≤60s scaffold + stopwatch (INSTALL-05)
6. `33-06` — TCC revoke mid-session graceful degrade (INSTALL-06 / P71)
7. `33-07` — Bundle ID CI grep gate (INSTALL-07 / P63)
8. `33-08` — Fresh-VM rehearsal scaffold + tart matrix (INSTALL-08)
9. `33-09` — API-key-surface assertion + grep gate (INSTALL-09)
