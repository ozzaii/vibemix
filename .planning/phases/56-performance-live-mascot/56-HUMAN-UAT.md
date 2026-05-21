---
status: partial
phase: 56-performance-live-mascot
source: [56-VERIFICATION.md]
started: 2026-05-21T10:05:00Z
updated: 2026-05-21T10:05:00Z
---

## Current Test

[awaiting human testing — Kaan live-drive on real Mac hardware under live-session load]

## Tests

### 1. TTFT feels instant (PERF-01)
expected: Reactions land in-bar on the real MacBook with no perceptible thinking lag. Engineering floor `LIVE_TTFT_BUDGET_MS=1500.0` + `thinking_gate` MINIMAL are pinned; this is the felt confirmation.
why_human: Felt latency under real load is a human judgment on real hardware.
result: [pending]

### 2. No audio dropouts across a full set (PERF-02)
expected: Zero glitches/dropouts in the playback path under real-session load across a full set. Soak underrun==0 is pinned synthetically; this is the real-load confirmation.
why_human: Requires a real full-set run on Kaan's Mac with ears on the playback path.
result: [pending]

### 3. 60fps on the integrated-GPU MacBook (PERF-03)
expected: Mascot rAF loop + UI hold 60fps during a live session. Dispatch-latency p95 ~0.22ms under the 50ms budget is pinned; this is the felt frame-rate confirmation.
why_human: Real GPU frame-rate under live load needs Kaan's eyes on the real machine.
result: [pending]

### 4. Mascot feels alive across its modes (LIVE-05 / LIVE-05a)
expected: The Three.js mascot visibly tracks real drops/builds/breakdowns and speaks while the AI talks — grounded, not decorative; no mode flip without a real event. Six-mode reachability + music-confirmation anti-slop guard + speaking-override are pinned in the rig; this is the felt "feels alive" confirmation.
why_human: The "feels alive across modes" call is a felt-quality judgment on real session data (his eyes). Build target is the shipped Three.js rig (`tauri/ui/mascot.html`).
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

None — engineering is airtight (13/13 must-haves verified). These four felt-quality items are the documented Kaan-ear/eye live-drive carveout under `gsd-autonomous fully` mode. They feed the v4.0 felt-perf + "mascot feels alive" sign-off on real hardware.
