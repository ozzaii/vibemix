---
phase: 24-djay-pro-mac-overlay-highlight
plan: 01
type: execute
wave: 0
status: shipped_pending_kaan_measurement
requirements_complete: [OVERLAY-02]
key_files:
  created:
    - tauri/src-tauri/spike/Cargo.toml
    - tauri/src-tauri/spike/src/main.rs
    - tauri/src-tauri/spike/sign-and-test.sh
    - tauri/src-tauri/spike/.gitignore
    - .planning/phases/24-djay-pro-mac-overlay-highlight/WAVE-0-AX-SPIKE.md
    - .planning/phases/24-djay-pro-mac-overlay-highlight/KAAN-ACTION.md
    - .planning/phases/24-djay-pro-mac-overlay-highlight/24-01-SUMMARY.md
  modified: []
deferred_kaan_action: WAVE-0-AX-SPIKE verdict measurement
verdict: pending_kaan_measurement
---

# Phase 24 Plan 01: Wave-0 AX-from-Rust-Parent Spike Infra — Summary

Standalone Rust spike crate + `sign-and-test.sh` harness shipped under `tauri/src-tauri/spike/`. Real verdict measurement requires a code-signed bundle test against a live djay Pro 5 session and is deferred to Kaan-action per `feedback_autonomous_no_grey_area_pause`.

## What was built

- **Spike crate (`tauri/src-tauri/spike/`)** — standalone Cargo binary that does NOT pollute the shipping `vibemix` Tauri crate. Probes Quartz `CGWindowListCopyWindowInfo` (window-rect fallback) and `AXUIElementCopyAttributeValue` (AX-precise path) against djay Pro 5; prints one of `AX_PASS | AX_PARTIAL | AX_FAIL | AX_INCONCLUSIVE`. All FFI gated behind `cfg(target_os = "macos")` — Windows / Linux build the crate as a no-op binary.
- **Cargo deps:** `core-graphics 0.24`, `core-foundation 0.10`, `accessibility-sys 0.1`, `objc 0.2`. Resolved against the existing Cargo lockfile space; no churn against the shipping crate.
- **Sign-and-test harness** — builds release, wraps the binary in a `vibemix-ax-spike.app` bundle (bundle ID locked to `world.bravoh.vibemix.spike`), copies the shipping `entitlements.plist` verbatim, ad-hoc-codesigns with `--options runtime`, installs to `/Applications/`, captures `probe.log`, parses one of four `VERDICT_*` lines on stdout. Refuses to use the production bundle ID `world.bravoh.vibemix` (T-24-01-01 mitigation).
- **Verdict template** — `WAVE-0-AX-SPIKE.md` with `verdict: pending_kaan_measurement` frontmatter, `## Raw Evidence` and `## What Plan 24-03 Must Do` sections; the implementation-path directive auto-selects per verdict (PASS → AX-precise; PARTIAL/FAIL → window-rect fallback; INCONCLUSIVE → PARTIAL default + Kaan re-runs).

## Verification

- `cd tauri/src-tauri/spike && cargo check` — clean. 16 transitive deps resolved on first build, 4.75s. No warnings.
- `bash tauri/src-tauri/spike/sign-and-test.sh` — syntax-validated; grep gates confirm `world.bravoh.vibemix.spike` lock and `VERDICT_*` emissions.
- `WAVE-0-AX-SPIKE.md` — frontmatter + raw-evidence + directive sections present.
- POC files (`cohost_v4.py`, `cohost_v3.py`, `cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `mascot.html`) UNTOUCHED. Each remains untracked at root (memory `project_v3_poc_reference`).

## What's deferred to Kaan-action

Per CONTEXT D-Wave-0 + `feedback_autonomous_no_grey_area_pause` + the Phase 22 KAAN-ACTION pattern: the real measurement is a Kaan task, not a workflow block. Surfaced explicitly in `KAAN-ACTION.md`:

1. Real-bundle AX-inheritance measurement requires:
   - A code-signed installed `.app` (Phase 21 Developer-ID signing is preferred; ad-hoc `--sign -` is adequate-but-advisory for the immediate run).
   - djay Pro 5 running in windowed mode at probe time.
   - One-time Accessibility grant in System Settings → Privacy & Security.
2. Kaan runs `bash tauri/src-tauri/spike/sign-and-test.sh` at next dev session.
3. Verdict flips `WAVE-0-AX-SPIKE.md` frontmatter from `pending_kaan_measurement` → one of `pass | partial | fail | inconclusive_djay_not_running`. Plan 24-03 auto-selects implementation path from that verdict.

## Plan 24-02 / 24-03 unblock

Plan 24-02 (overlay-highlight feature) proceeds in parallel against the **PARTIAL fallback** as the safer default. If the verdict comes back PASS, Plan 24-03 promotes the implementation to AX-precise positioning in a follow-up — feature ships either way. Per CONTEXT D-Wave-0 spike FAIL is NOT a phase block.

## Deviations from plan

None vs Rules 1-3. Plan Task 3 (run-spike-and-author-verdict) was deferred to Kaan as documented — this is a known Kaan-action surface per `feedback_autonomous_no_grey_area_pause` and the Phase 21-signing dependency.

## Self-Check: PASSED

- `tauri/src-tauri/spike/Cargo.toml` — FOUND
- `tauri/src-tauri/spike/src/main.rs` — FOUND
- `tauri/src-tauri/spike/sign-and-test.sh` — FOUND (chmod +x)
- `.planning/phases/24-djay-pro-mac-overlay-highlight/WAVE-0-AX-SPIKE.md` — FOUND
- `.planning/phases/24-djay-pro-mac-overlay-highlight/KAAN-ACTION.md` — FOUND
- `cargo check` on spike crate — clean
- POC files — untouched (git status verified)
