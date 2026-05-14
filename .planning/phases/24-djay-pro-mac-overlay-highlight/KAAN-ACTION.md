# KAAN-ACTION — Phase 24 Plan-01 AX spike measurement

**Status:** open — blocks `verdict:` line in `WAVE-0-AX-SPIKE.md`.
**Blocks:** nothing in v2.0 (per CONTEXT D-Wave-0 — verdict selects implementation path only, both branches ship).
**Owner:** Kaan (DJ ear-test session OR ad-hoc dev rig).
**Deferred until:** Phase 21 lands real Developer-ID signing — until then the harness runs ad-hoc and the verdict is "advisory" not "binding".

## What's deferred

The actual `sign-and-test.sh` run against a live djay Pro 5 session on a code-signed installed bundle. The harness + crate + bundle template + verdict matrix are all shipped this plan — only the measurement itself requires:
- Kaan's machine (the spike must install to `/Applications/` to mirror TCC keying).
- djay Pro 5 running in windowed mode at probe time.
- One-time Accessibility grant for `vibemix-ax-spike.app` in System Settings.

## What Claude shipped

- `tauri/src-tauri/spike/Cargo.toml` — standalone macOS-only crate, AX + Quartz deps.
- `tauri/src-tauri/spike/src/main.rs` — Rust binary that probes Quartz `CGWindowListCopyWindowInfo` + AX tree via `AXUIElementCopyAttributeValue`; prints one of four verdicts.
- `tauri/src-tauri/spike/sign-and-test.sh` — chmod +x, builds + bundle-wraps + ad-hoc-codesigns with the shipping `entitlements.plist` + installs to `/Applications/` + captures `probe.log` + emits `VERDICT_*` on stdout. Refuses to sign with the production bundle ID `world.bravoh.vibemix` (T-24-01-01 mitigation).
- `WAVE-0-AX-SPIKE.md` — verdict-pending template with `verdict: pending_kaan_measurement` frontmatter and a self-documenting **What Plan 24-03 Must Do** section that auto-selects the implementation path per verdict.

`cargo check` on the spike crate passes cleanly from a fresh `target/` (16 transitive deps resolved, 4.75s).

## What Kaan does

1. Launch djay Pro 5 in **windowed mode** (NOT fullscreen — fullscreen-Spaces is Plan 24-05's scope).
2. From repo root: `bash tauri/src-tauri/spike/sign-and-test.sh`.
3. On first run, macOS will prompt: System Settings → Privacy & Security → Accessibility → enable `vibemix-ax-spike`. Re-run the script ONCE after granting.
4. Read the last line of stdout: `VERDICT_PASS | VERDICT_PARTIAL | VERDICT_FAIL | VERDICT_INCONCLUSIVE`.
5. Update `WAVE-0-AX-SPIKE.md`:
   - Flip frontmatter `verdict:` to `pass | partial | fail | inconclusive_djay_not_running`.
   - Flip `status: pending_kaan_measurement` to `status: measured`.
   - Fill the **Test Setup** table.
   - Paste `tauri/src-tauri/spike/probe.log` into **Raw Evidence**.
6. Commit: `docs(24-01): measure — wave-0 AX spike verdict <result>`.

If Phase 21 has landed by the time you run this, re-run the harness once under the real Developer-ID identity (edit the `--sign -` argument in `sign-and-test.sh` to the production identity) — that promotes the verdict from "advisory" to "binding".

## Why deferred

Per CONTEXT D-Wave-0 + `feedback_autonomous_no_grey_area_pause`: the spike outcome is NOT a phase block. Plan 24-02 ships the overlay feature using the PARTIAL fallback as the safer default; if the verdict comes back PASS, Plan 24-03 promotes the implementation to AX-precise positioning in a follow-up. v2.0 ships either way.

The harness intentionally runs ad-hoc-signed today because Phase 21 (Developer ID + notarize) has not yet landed. A real-world AX-inheritance test against the shipping binary requires the production signing identity — that becomes a clean re-run of `sign-and-test.sh` once Phase 21 produces the identity. Until then the verdict is advisory but actionable.
