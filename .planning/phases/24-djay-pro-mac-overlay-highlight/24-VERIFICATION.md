---
status: human_needed
phase: 24
phase_name: djay Pro Mac Overlay Highlight
verified_at: 2026-05-14
mode: gsd-autonomous fully
plans_verified_auto: 2
plans_deferred_human: 1
must_haves_total: 4
must_haves_verified: 3
must_haves_human_pending: 1
---

# Phase 24 — Verification

**Mode:** Autonomous (fully). Plans 24-01 (AX spike infra) + 24-02 (overlay feature E2E) shipped. Live djay Pro visual smoke + signed-bundle AX verdict = Kaan-action.

## ROADMAP Success Criteria

| # | Criterion | Auto-test | Human-test | Notes |
|---|-----------|-----------|------------|-------|
| 1 | AX query from Rust parent (NEVER Python sidecar) | ✓ djay_ax.rs cargo test | — | macOS-only; Windows stub. |
| 2 | Amber ring overlay on AX-located UI element | ✓ overlay.rs Tauri command + frontend | ⏸ Kaan visual smoke | Currently uses percentage-of-window fallback; AX-precise via Plan 24-03 after WAVE-0 verdict. |
| 3 | Sidecar publishes `[screen:*]` citation → overlay IPC | ✓ test_overlay_publish.py (8 tests) | — | Publishes on `emit` + `bypass` actions. |
| 4 | Wave-0 AX-from-Rust-parent verdict on signed bundle | ✗ blocked on Phase 21 sign | ⏸ Kaan-action | Run `sign-and-test.sh` after Apple/SignPath approvals land. |

## Auto-test Verification

- `pytest -q`: 1911 passed (+26), 10 pre-existing failures unchanged.
- `cargo check` + `cargo test` in `tauri/src-tauri/`: clean.
- IPC schema count: 36 (was 35, +1 for overlay-highlight).

## Deferred to Kaan-Action

- **Wave-0 AX verdict on signed bundle** — Kaan runs `bash tauri/src-tauri/spike/sign-and-test.sh` after Phase 21 signing. Documented in `KAAN-ACTION.md`.
- **Visual smoke** — Kaan verifies amber ring lands on actual djay Pro UI element, fades correctly, doesn't block mouse.

## Status

✓ AX query module + overlay command + IPC + sidecar publish all shipped + tested.
⏸ Visual + signed-bundle verdict = Kaan-action.
