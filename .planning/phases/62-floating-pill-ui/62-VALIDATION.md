---
phase: 62
slug: floating-pill-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-22
---

# Phase 62 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (tauri/ui TS) + `cargo test` (tauri/src-tauri Rust) + pytest (repo-level fences) |
| **Config file** | `tauri/ui/vitest.config.ts` · `tauri/src-tauri/Cargo.toml` · `pyproject.toml` |
| **Quick run command** | `cd tauri/ui && npx vitest run <file>` / `cd tauri/src-tauri && cargo test <mod>` |
| **Full suite command** | `cd tauri/ui && npx vitest run && npx tsc --noEmit` ; `cd tauri/src-tauri && cargo test` ; `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~60–240 seconds (vitest + cargo fast; full pytest ~225s) |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (vitest file / cargo mod).
- **After every plan wave:** Run the wave's full layer suite (vitest+tsc for UI waves, cargo test for Rust waves).
- **Before `/gsd:verify-work`:** UI vitest+tsc green; cargo test green; repo pytest at the documented 7-WIP baseline (no NEW failures).
- **Max feedback latency:** ~240 seconds.

---

## Per-Task Verification Map

> Scaffold — the planner fills concrete Task IDs/commands into each PLAN's Dimension-8
> validation block; Wave-0 instantiates the test files. Maps PILL-01..04 to
> unit-testable vs KAAN-ACTION-live per RESEARCH §Validation Architecture.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 62-0x-xx | 0x | 1 | PILL-02 | — | tri-state `primary_surface` serde roundtrip + legacy-missing→`pill` default | unit (cargo) | `cargo test primary_surface` | ❌ W0 | ⬜ pending |
| 62-0x-xx | 0x | 1 | PILL-04 | — | `"pill"` window label ∈ capability allowlist (label↔capability test) | unit (cargo) | `cargo test pill_capability` | ❌ W0 | ⬜ pending |
| 62-0x-xx | 0x | 2 | PILL-03 | — | pill consumes `ipc.session.snapshot`+`cohost-reaction` frames → state map (idle/listening/speaking/expand) | unit (vitest) | `npx vitest run pill` | ❌ W0 | ⬜ pending |
| 62-0x-xx | 0x | 2 | PILL-01 | — | multi-monitor clamp-to-visible math; off-screen geometry fallback | unit (cargo/vitest) | `cargo test clamp` | ❌ W0 | ⬜ pending |
| 62-0x-xx | 0x | 2 | PILL-02 | — | mascot-audit fence stays green (pill code path-scoped, mascot.html byte-stable) | repo (pytest/CI) | `pytest -q -k mascot_audit` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tauri/ui/src/pill/*.test.ts` — pill state-machine + frame-consume + waveform/citation-strip reuse stubs (PILL-03)
- [ ] `tauri/src-tauri/src/pill_window.rs` `#[cfg(test)]` — geometry/clamp + label↔capability allowlist (PILL-01/04)
- [ ] `tauri/src-tauri/src/config.rs` `#[cfg(test)]` — `primary_surface` tri-state serde + legacy default (PILL-02)

*Existing infrastructure (vitest, cargo test, pytest) covers all phase requirements — no framework install.*

---

## Manual-Only Verifications (KAAN-ACTION — live on the built app)

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drag-on-unfocused-window FEELS right | PILL-01/04 | `startDragging` behavior on a non-activating window only observable on the built app (tauri#11605/#10767) | Build, run, drag the pill while the DJ app is focused — pill follows the cursor without a focus flash |
| Focus non-steal (keystrokes reach DJ app) | PILL-04 | NSWindow→NSPanel/Accessory residual first-click behavior is OS-runtime-only | Click the pill, then type — keystrokes must land in the DJ app, not vibemix |
| Transparency parity on the `.dmg` | PILL-01 | DMG-build transparency regression tauri#13415 is OPEN, unknowable without the build | Build the `.dmg`, open it, confirm no opaque white chrome box around the pill (mac); confirm explicit-glass renders on Windows |
| Multi-monitor felt behavior | PILL-01 | Display hot-plug behavior is hardware-dependent | Move the pill across monitors / unplug a display — pill clamps to a visible region |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags (vitest `run`, not watch)
- [ ] Feedback latency < 240s
- [ ] `nyquist_compliant: true` set in frontmatter (after Wave-0)

**Approval:** pending
