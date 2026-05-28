# Plan 91-07 — SUMMARY (DEFERRED to KAAN-ACTION queue)

**Status:** `kaan_action_deferred` — Plan 91-07 is a `checkpoint:human-verify` task that cannot be discharged by an automated executor. Per `/gsd-autonomous fully` mode (CLAUDE.md `feedback_autonomous_no_grey_area_pause`), this is parked to the KAAN-ACTION queue rather than blocking phase advancement.

## What this plan is

The Kaan ear-pass checkpoint on real DDJ-FLX4 hardware. The deliverable for Phase 91 is "plug controller → see knob move <50ms (P95). Standalone-verifiable; NO lessons yet." Plans 91-01 through 91-06 SHIPPED the engineering work; Plan 91-07 is the live-hardware verification step that proves it.

## Why deferred (not blocking)

- Plans 91-01 through 91-06 are CODE-COMPLETE + TEST-GREEN. The shipped state is verifiable.
- The verification this plan asks for needs a human + physical USB-MIDI hardware that the autonomous run does not have access to.
- Per `/gsd-autonomous fully` rules: "blockedda da defer et" — defer human-required gates to the KAAN-ACTION queue, continue the rest of the autonomous run.
- The §LEARN-CONTROLLER-EAR carveout in SUMMARY.md §2 already establishes that controller ear-passes are KAAN-ACTION work — Plan 07 is the FLX4 entry in that queue.

## What needs to happen (Kaan-side, when ready)

Plug in a DDJ-FLX4 over USB, launch vibemix with the Learn window, and walk the live verification recipe:

### Live verification recipe (FLX4 only)

```bash
# 1. From repo root, ensure clean state
git status                     # confirm working tree state
uv sync                        # ensure deps current
cd tauri/ui && npm install     # frontend deps if needed
cd ../src-tauri && cargo build # rust shell builds

# 2. Launch with the dev-source sidecar (NOT the frozen bundled binary —
#    per CLAUDE.md feedback_stale_sidecar_verify_current_source)
VIBEMIX_DEV_SIDECAR=1 cd tauri && cargo tauri dev

# 3. In the Learn window (NOT the main deck window):
#    - Verify the FLX4 schematic mounts within 2 seconds of USB plug-in
#    - Twist EQ-HI knob deck A — verify on-screen knob mirrors with no perceptible lag
#    - Move the crossfader — verify the rendered fader tracks
#    - Press play deck A — verify the rendered play button highlights
#    - Tab through controls with keyboard — verify focus rings appear on every <g>
#    - Cmd+Tab to the deck window and back — verify Learn window persists

# 4. Sanity checks
#    - Check `tail -50 ~/Library/Application\ Support/world.bravoh.vibemix/vibemix/logs/ui.log`
#      for [vmx:ipc<] ipc.learn.midi_position frames at ~30 Hz
#    - Verify the status bar shows real latency P95 (target ≤50 ms, red guardrail 80 ms)
```

### Pass / fail criteria

**PASSED if:**
- FLX4 schematic mounts < 2 s after plug-in (RENDER-01)
- Knob/fader/transport position mirroring is perceptually instantaneous (RENDER-02 — synthetic P95 was 0.66 ms in Plan 05; real-hardware P95 should be < 50 ms with comfortable headroom)
- Tab cycles through controls in DOM order (RENDER-03)
- Cmd+Tab between Learn and main deck windows works (RENDER-07)
- No Pioneer logo / orange / faceplate art visible (Apache-clean)

**FAILED if:**
- Latency > 80 ms P95 → trigger §LEARN-LATENCY-CONTINGENCY (Rust-direct midir path; new follow-up plan)
- SVG mounts > 2 s → investigate dynamic-import chunk loading
- Any rendered control fails to track → check `data-control-id` ↔ profile `field` parity for that specific control

## Out of scope for this plan (KAAN-ACTION queue items already parked)

- **§LEARN-CONTROLLER-EAR** — Live ear-pass on the 9 non-FLX4 SKUs (FLX6, FLX10, 400, 1000, SX3, XDJ-RX3, Numark Party Mix Live, Hercules Inpulse 300, 500). These ride forward to P98 per the SUMMARY.md §2 LOCKED decision.
- **§LEARN-LATENCY-CONTINGENCY** — Rust-direct midir MIDI listener if the FLX4 ear-pass measures > 80 ms P95.
- **§LEARN-MK2-DETECTION** — Hercules Inpulse 300-MK2 vs 300 port-name discrimination.
- **§LEARN-FIRMWARE-VARIANTS** — DDJ-FLX4 v1.07 firmware variant detection.

## Engineering provenance (what 91-01 through 91-06 shipped)

| Plan | Wave | What landed | Commits | Tests |
|------|------|-------------|---------|-------|
| 91-01 | 1 | IPC envelopes + Vite multi-entry + Tauri capability windows-scope + Python dataclasses | 905e1550, e6b94619, de4808ce, d8890110 | 223 ui_bus/ipc tests pass |
| 91-02 | 1 | Test scaffolding — 5 Python + 14 TS test stubs (RED-state) | da2aa70c, 10c4fcfc, e3725400 | 5 grep gates green day-one |
| 91-03 | 2 | `MidiMirror` (30 Hz delta-coalesced + thread-safe controller_detected queue) + ws_bus.py drain-then-snapshot + __main__.py wiring | 63d5c7f2, e572a8a7, c02d437b | 4 SKIP → PASS, 4450/0 wider suite |
| 91-04 | 2 | `tauri/src-tauri/src/learn_window.rs` (trimmed mirror of debrief_window.rs) + main.rs registration | 4136f72f, 508ef572, 9a850d56 | 92/92 cargo test |
| 91-05 | 3 | Learn webview entry + ws-client + 5 components + FLX4 SVG (25 hit regions) + generic fallback + _aria-labels lookup + styles | bfa01b80, 71d218cd, cd8eebea | 966/0 vitest, **0.66ms P95 latency** in jsdom |
| 91-06 | 4 | 9 non-FLX4 controller SVGs (FLX6/FLX10/400/1000/SX3/XDJ-RX3/Numark Party Mix Live/Hercules Inpulse 300/500) — 251 total hit regions, all parity-clean | 89f378a1, 909d1166, 51ff5f00, 6368f3e5, f4fd9747, 726c0deb, cab0811d, d048d39a, e85fae9d, 2747c634 | 1002/0 UI suite, 10 lazy chunks |

**Total Phase 91 commits:** 31 across 6 plans (plus this stub).
**Total new files:** 7 Python + 14 TS test scaffolds + 11 controller SVGs + 1 ARIA lookup + 1 ws-client + 5 components + 1 styles + 1 Rust mod + 1 HTML entry + 2 Python (learn/__init__.py, midi_mirror.py) + 1 Python (ui_bus/learn_messages.py).

## REQ-ID coverage at deferral

| REQ-ID | Plans | Verification |
|--------|-------|-------------|
| RENDER-01 (mount in <2s, 10+1 controllers) | 01, 03, 05, 06 | Synthetic green (controller_detected envelope round-trip + SVG mount smoke test). Real-hardware live verify = THIS deferred item. |
| RENDER-02 (≤50ms P95) | 02, 03, 05 | Synthetic green (0.66ms P95 in jsdom). Real-hardware live verify = THIS deferred item. |
| RENDER-03 (ARIA + keyboard nav) | 02, 05 | Synthetic green (aria-labels + keyboard nav order tests). Real-hardware live verify = THIS deferred item. |
| RENDER-05 (dual-channel cue scaffolding) | 02, 05 | Synthetic green (cue-color + cue-shape attribute slot tests). Highlight paint defers to P92. |
| RENDER-06 (SVG↔profile parity bidirectional) | 02, 05, 06 | Synthetic green ALL 11 controllers parity-clean. |
| RENDER-07 (separate WebviewWindow, same ws:8765) | 01, 04, 05 | Synthetic green (cargo test + ws_client_uses_8765 + no_new_ws_port). Real-hardware Cmd+Tab = THIS deferred item. |

## Next steps

1. **Kaan**: when DDJ-FLX4 is plugged in next, run the verification recipe above. Report PASS/FAIL.
2. **If PASS**: append "PASSED 2026-MM-DD" to this file's frontmatter status and to the §LEARN-CONTROLLER-EAR FLX4 entry in the v9.0 KAAN-ACTION queue.
3. **If FAIL**: open a new plan documenting the specific failure mode; if latency >80ms, that triggers §LEARN-LATENCY-CONTINGENCY (Rust-direct midir).
4. **Phase 91 advances**: even with this deferred, Phase 91 verification can proceed (Plans 01-06 satisfy the goal-backward verification; the live ear-pass is a hard gate for v9.0 ship, not for phase close).

---

*Generated by `/gsd-autonomous` overnight run. Plan 91-07 owes Kaan a real-FLX4 ear-pass.*
