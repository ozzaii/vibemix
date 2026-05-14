---
phase: 24-djay-pro-mac-overlay-highlight
plan: 01
wave: 0
status: pending_kaan_measurement
verdict: pending_kaan_measurement
---

# Wave-0 AX Spike — Verdict

**Status:** pending Kaan measurement on a signed bundle.
**Blocks:** nothing in v2.0 (per CONTEXT D-Wave-0 — both PASS and FAIL ship a working Plan 24-03; spike outcome only selects implementation path).
**Phase 21 dependency:** real Developer-ID sign + notarize land in Phase 21. Until then `sign-and-test.sh` runs ad-hoc (`codesign --sign -`) — adequate for the AX inheritance test on Kaan's dev rig, **insufficient** for a binding verdict against the shipping Bravoh-signed binary.

## Verdict

`pending_kaan_measurement` — fill the line below to `pass | partial | fail | inconclusive_djay_not_running` after running the harness.

```text
verdict: pending_kaan_measurement
```

## Test Setup (fill at measurement time)

| Field | Value |
|-------|-------|
| macOS version | _to-fill_ |
| djay Pro version | _to-fill_ |
| Bundle install location | `/Applications/vibemix-ax-spike.app` |
| Signing identity | ad-hoc (`-`) — Phase 21 will re-run under Developer ID |
| AX permission granted | _to-fill_ |
| Display setup (single / dual / triple) | _to-fill_ |
| djay window mode (windowed / fullscreen-Spaces) | windowed (fullscreen is Plan 24-05 scope, NOT spike scope) |

## Raw Evidence

Inline the contents of `tauri/src-tauri/spike/probe.log` here (or reference the file if longer than 100 lines).

```text
_probe.log contents — fill at measurement time_
```

## What Plan 24-03 Must Do

The directive below is selected automatically by the verdict above. Plan 24-03 reads this section to choose its implementation path:

- **PASS** → ship AX-precise knob-level positioning. Use `kCGWindowBounds` only as a fallback when AX returns null for a specific element (per-element graceful degrade, not whole-feature).
- **PARTIAL** → skip AX entirely. Ship `kCGWindowBounds` + percentage-of-window-rect coord_map. Accuracy degrades from "knob-precise" to "EQ-region-approximate" — still functional, still ships.
- **FAIL** → same as PARTIAL but additionally surface a louder note in Plan 24-05's fullscreen-Spaces toast and in Phase 26's README rewrite referencing Tauri #8329. Plan 24-03 does NOT block on FAIL.
- **INCONCLUSIVE (djay not running)** → Plan 24-03 begins with the PARTIAL path (safer default). Kaan re-runs `sign-and-test.sh` at first available djay session; verdict flip from inconclusive→pass auto-promotes 24-03 to the AX path on the next build.

Per `feedback_autonomous_no_grey_area_pause` + CONTEXT D-Wave-0: degraded ship is acceptable, do not pause for permission. The fallback IS the approved path.

## How to Run (Kaan)

1. Launch djay Pro 5 in windowed mode (NOT fullscreen — fullscreen-Spaces is Plan 24-05's separate scope).
2. From repo root: `bash tauri/src-tauri/spike/sign-and-test.sh`.
3. First run will prompt for Accessibility permission on the `vibemix-ax-spike` bundle in System Settings → Privacy & Security → Accessibility. Grant it, then re-run the script ONCE.
4. Read the last line of stdout for the verdict (`VERDICT_PASS | VERDICT_PARTIAL | VERDICT_FAIL | VERDICT_INCONCLUSIVE`).
5. Update this document's frontmatter `verdict:` line + the table in **Test Setup** + paste `probe.log` into **Raw Evidence**.
6. Flip the frontmatter `status: pending_kaan_measurement` to `status: measured`.
7. Commit: `docs(24-01): measure — wave-0 AX spike verdict <pass|partial|fail|inconclusive>`.

## Why Deferred

Phase 21 (Apple Developer ID sign + notarize) has not landed yet. The ad-hoc-signed harness is honest enough to detect AX inheritance issues against the same entitlements surface, but a binding "this works on the shipping binary" verdict requires the Developer-ID-signed bundle Phase 21 will produce. Per `feedback_autonomous_no_grey_area_pause`, this is a Kaan-action-required surface, not a workflow block — Plan 24-02 + 24-03 proceed in parallel against the PARTIAL path as the safer default.
