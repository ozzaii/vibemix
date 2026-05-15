# Phase 33 Summary — One-Click Install Hardening

**Status:** SHIPPED 2026-05-15
**Mode:** gsd-autonomous fully (scaffold + tests autonomous; real-VM smokes deferred to KAAN-ACTION-LEGAL.md)
**Plans:** 9/9 (33-01 through 33-09)
**REQ-IDs satisfied:** INSTALL-01, INSTALL-02, INSTALL-03, INSTALL-04, INSTALL-05, INSTALL-06, INSTALL-07, INSTALL-08, INSTALL-09

## What shipped

| Plan | Commit | Surface | REQ / Pitfall |
|------|--------|---------|---------------|
| 33-01 | a1c46c8 | `tcc-permissions.ts` deep-link helper (12.3 / 14 / 15 ladder + fallback) | INSTALL-01 / P50 |
| 33-02 | bbbd624 | `tauri-plugin-macos-permissions = "2.3.0"` wired, macOS-only via cfg guard, capability allowlist updated, SNAPSHOT regenerated | INSTALL-02 |
| 33-03 | 544ce42 | `vibemix.install.blackhole_probe` + `blackhole-step.ts` install-affordance renderer | INSTALL-03 |
| 33-04 | 2d795e3 | `docs/install/windows-smartscreen.md` + `windows-smartscreen-step.ts` (honest, no "warning-free" promise) | INSTALL-04 (Phase 38 dep) |
| 33-05 | 321fb67 | `onboarding-flow.ts` orchestrator + `onboarding-stopwatch.ts` per-step + total timing | INSTALL-05 |
| 33-06 | 7aaf533 | `runtime/tcc-watcher.ts` + `permission-lost-handler.ts` (pause + toast + re-grant) | INSTALL-06 / P71 |
| 33-07 | b41525e | `test_bundle_id_locked.py` + `bundle-id-lock.yml` workflow + v2.0→v2.1 carryover test | INSTALL-07 / P63 |
| 33-08 | 0d908d0 | `scripts/install_rehearsal/` (mac sh + win ps1 + python runner) + workflow_dispatch+nightly CI + KAAN-ACTION-LEGAL INSTALL-VM-RUN | INSTALL-08 |
| 33-09 | dba688f | `test_no_api_key_surface.py` + `no-api-key-surface.yml` workflow — zero key-entry surfaces | INSTALL-09 |

## Hard gates green

| Gate | Plan | Test |
|------|------|------|
| TCC deep-link ladder correct for 12.3/14/15 | 33-01 | `tcc-permissions.spec.ts` (6 cases) |
| `tauri-plugin-macos-permissions` pinned + wired macOS-only | 33-02 | `test_tauri_plugin_macos_permissions_wired.py` (3 cases) |
| BlackHole probe surfaces install button when absent | 33-03 | `test_blackhole_probe.py` (5) + `blackhole-step.spec.ts` (4) |
| Defender SmartScreen doc + step scaffolded honestly | 33-04 | `test_windows_smartscreen_doc.py` (3) + `windows-smartscreen-step.spec.ts` (4) |
| Onboarding flow visits 4 steps + emits stopwatch | 33-05 | `onboarding-flow.spec.ts` (6) |
| TCC revoke event → pause + toast + no crash | 33-06 | `tcc-watcher.spec.ts` (5) |
| Bundle ID locked + grep gate | 33-07 | `test_bundle_id_locked.py` (2) + `test_v2_0_to_v2_1_upgrade.py` (3) |
| Fresh-VM rehearsal scaffold (real runs Kaan-action) | 33-08 | `test_rehearsal_scaffold.py` (6) |
| Zero API key entry surfaces anywhere | 33-09 | `test_no_api_key_surface.py` (3) |

## Test suite evidence

```
pytest tests/install/ tests/security/test_bundle_id_locked.py \
       tests/security/test_no_api_key_surface.py \
       tests/security/test_tauri_plugin_macos_permissions_wired.py -q
25 passed in 1.04s

npx vitest run src/wizard/__tests__/ src/runtime/__tests__/
25 passed (5 files)
```

50 new tests total (25 pytest + 25 vitest). No regression in pre-existing suites (Phase 38 P46 audit + capability snapshot + sec_check all still green).

## Pitfall coverage

- **P50** — macOS 15 Sequoia Settings reorg handled by version-aware deep-link ladder + root-Privacy fallback in `tcc-permissions.ts`.
- **P63** — bundle ID `world.bravoh.vibemix` is grep-gated against `tauri.conf.json5` + every other JSON/JSON5/plist/TOML in the repo. `bundle-id-lock.yml` workflow blocks divergent ids on PR.
- **P67** — telemetry default-OFF preserved (Phase 34 surface untouched); reasserted via INSTALL-09 grep covering "api_token" + "telemetry" reading paths.
- **P69** — universal2 sidecar from Phase 27 unchanged; this phase does not touch the sidecar build matrix.
- **P71** — TCC revoke graceful degrade: `tcc-watcher.ts` fires single event on granted → denied transition; `permission-lost-handler.ts` isolates each side-effect in its own try/catch so a single broken hook cannot crash the session.

## Kaan-action carveouts (KAAN-ACTION-LEGAL.md INSTALL-VM-RUN)

The following items are NEVER discharged autonomously per `gsd-autonomous fully` mode + the Phase 33 plan:

1. **INSTALL-VM-RUN** — Actual `tart` macOS VM matrix execution. Requires disk space + macOS license attached to the host.
2. **INSTALL-60S-CHECK** — Stopwatch validation of ≤60s onboarding on real hardware (post-Phase-38 signed binary).
3. **INSTALL-DEFENDER** — Defender SmartScreen reputation propagation (post-Phase-38 SignPath chain + 1-2 week waiting period).
4. **INSTALL-BLACKHOLE-PROBE** — Validate one-click install flow on a fresh Mac that doesn't have BlackHole.

Protocol + sign-off block live in `KAAN-ACTION-LEGAL.md` INSTALL-VM-RUN section.

## What's left

Engineering scaffold + tests are complete. Real-hardware validation runs against a signed binary, which means Phase 33 ships when Phase 38 secrets land + Kaan executes the INSTALL-VM-RUN protocol. The autonomous engineering surface has zero remaining work.
