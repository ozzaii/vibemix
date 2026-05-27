---
phase: 91
slug: controller-renderer-midi-mirror
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-27
---

# Phase 91 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `91-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Frameworks** | pytest 7.x (Python) · vitest (TS unit) · playwright (TS spec/DOM) · cargo test (Rust) — all pinned in production |
| **Config files** | `pyproject.toml [tool.pytest.ini_options]` · `tauri/ui/vitest.config.ts` · `tauri/ui/playwright.config.ts` · `tauri/src-tauri/Cargo.toml` |
| **Quick run command** | `cd tauri/ui && npm test -- tests/learn/` (~3–5 s) |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q && cd tauri/ui && npm test && npx playwright test tests/learn/ && cd ../src-tauri && cargo test` |
| **Estimated runtime** | ~25–40 s total (vitest fast; pytest learn-suite small; playwright slow) |

---

## Sampling Rate

- **After every task commit:** Run `cd tauri/ui && npm test -- tests/learn/` (vitest only, ~3–5 s)
- **After every plan wave:** Run `cd tauri/ui && npm test && PYTHONPATH=src python3 -m pytest -q tests/learn/ tests/ipc/test_learn_envelope_parity.py` (~10 s)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds per-task; 40 seconds at phase gate

---

## Per-Task Verification Map

| REQ-ID | Behavior | Test Type | Automated Command | File Exists |
|--------|----------|-----------|-------------------|-------------|
| RENDER-01 | Plug FLX4 → SVG mount within 2 s | unit + integration | `cd tauri/ui && npx vitest run tests/learn/test_controller_detected_mounts_svg.test.ts` | ❌ Wave 0 |
| RENDER-01 | `controller_detected` envelope shape parity | unit | `PYTHONPATH=src python3 -m pytest tests/ipc/test_learn_envelope_parity.py::test_controller_detected_roundtrip -x` | ❌ Wave 0 |
| RENDER-01 | All 11 controllers have SVG files | unit | `cd tauri/ui && npx vitest run tests/learn/test_all_11_svgs_present.spec.ts` | ❌ Wave 0 |
| RENDER-01 | Generic fallback renders on no-match | unit | `cd tauri/ui && npx vitest run tests/learn/test_generic_fallback.spec.ts` | ❌ Wave 0 |
| RENDER-02 | Synthetic latency P95 ≤ 50 ms target | unit | `cd tauri/ui && npx vitest run tests/learn/highlight-latency.test.ts` | ❌ Wave 0 |
| RENDER-02 | Synthetic latency P95 ≤ 80 ms red guardrail | unit (hard-fail) | `cd tauri/ui && npx vitest run tests/learn/highlight-latency.test.ts` | ❌ Wave 0 |
| RENDER-02 | MidiMirror delta-suppression (no emit when steady) | unit | `PYTHONPATH=src python3 -m pytest tests/learn/test_midi_mirror_unit.py::test_no_emit_when_steady -x` | ❌ Wave 0 |
| RENDER-02 | MidiMirror first-frame emit after bind | unit | `PYTHONPATH=src python3 -m pytest tests/learn/test_midi_mirror_unit.py::test_first_frame_after_bind -x` | ❌ Wave 0 |
| RENDER-02 | 30 Hz ws_broadcast cadence under learn load | integration | `PYTHONPATH=src python3 -m pytest tests/runtime/test_ws_broadcast_30hz_under_learn_load.py -x` | ❌ Wave 0 |
| RENDER-03 | Every `<g data-control-id>` has `role="button"` + `aria-label` | unit (DOM walk) | `cd tauri/ui && npx vitest run tests/learn/test_aria_labels_present.spec.ts` | ❌ Wave 0 |
| RENDER-03 | Tab cycles through control groups in DOM order | spec (playwright) | `cd tauri/ui && npx playwright test tests/learn/test_keyboard_nav_order.spec.ts` | ❌ Wave 0 |
| RENDER-03 | Screen-reader polite announcement on detect | unit | `cd tauri/ui && npx vitest run tests/learn/test_sr_announcement.spec.ts` | ❌ Wave 0 |
| RENDER-05 | Each `<g>` has `cue-color` + `cue-shape` empty slots (stub) | unit (stub-only) | `cd tauri/ui && npx vitest run tests/learn/test_dual_cue_slots_present.spec.ts` | ❌ Wave 0 |
| RENDER-06 | Bidirectional SVG↔profile parity across all 11 files | unit (parameterized) | `cd tauri/ui && npx vitest run tests/learn/test_svg_profile_parity.spec.ts` | ❌ Wave 0 |
| RENDER-07 | Learn window opens via `open_learn_window` Tauri command | unit (Rust) | `cd tauri/src-tauri && cargo test learn_window` | ❌ Wave 0 |
| RENDER-07 | Learn window label is `learn` (lowercase, no spaces) | unit (Rust) | `cd tauri/src-tauri && cargo test learn_window_label_const_is_lowercase` | ❌ Wave 0 |
| RENDER-07 | Learn webview connects to ws:8765 (one-socket invariant) | unit (TS) + grep | `cd tauri/ui && npx vitest run tests/learn/test_ws_client_uses_8765.spec.ts` + `PYTHONPATH=src python3 -m pytest tests/learn/test_no_new_ws_port.py -x` | ❌ Wave 0 |
| **N/A — Brand-safety** | No `#FF7F00` / `#ff7f00` in `learn/**.svg.ts` | unit (regex grep) | `cd tauri/ui && npx vitest run tests/learn/test_no_pioneer_orange.spec.ts` | ❌ Wave 0 |
| **N/A — Brand-safety** | No "Pioneer DJ" string in any `learn/**.svg.ts` | unit | `PYTHONPATH=src python3 -m pytest tests/learn/test_no_pioneer_brand_marks.py -x` | ❌ Wave 0 |
| **N/A — currentColor** | No `fill="#..."` / `stroke="#..."` literals inside SVG bodies | unit (regex grep) | `cd tauri/ui && npx vitest run tests/learn/test_svg_currentcolor_only.spec.ts` | ❌ Wave 0 |
| **N/A — IPC parity** | 2 wrappers ↔ 2 oneOf entries (count parity) | unit | `python3 scripts/check_ipc_schema.py` (existing) | ✅ Existing |
| **N/A — IPC parity** | Round-trip — Python dataclass → JSON → ajv validate → Python parse | unit | `PYTHONPATH=src python3 -m pytest tests/ipc/test_learn_envelope_parity.py -x` | ❌ Wave 0 |
| **N/A — A11Y contrast** | Learn window passes axe-core contrast checks | spec (playwright) | `cd tauri/ui && npx playwright test tests/learn/test_contrast_ratios.spec.ts` | ❌ Wave 0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky — populated during execute-phase*

---

## Wave 0 Requirements

> All Wave 0 files MUST land before any RENDER feature task is verified. Wave 0 is the first wave of plan tasks (test scaffolding + IPC schema edits + capability allowlist).

- [ ] `tests/learn/__init__.py` — Python test package marker
- [ ] `tests/learn/test_midi_mirror_unit.py` — backend RENDER-02 unit tests
- [ ] `tests/learn/test_no_new_ws_port.py` — grep gate (`learn/` must have zero `websockets.serve` occurrences)
- [ ] `tests/learn/test_no_pioneer_brand_marks.py` — grep gate for "Pioneer DJ" wordmark
- [ ] `tests/ipc/test_learn_envelope_parity.py` — round-trip + count parity for `controller_detected` + `midi_position`
- [ ] `tests/runtime/test_ws_broadcast_30hz_under_learn_load.py` — 30 Hz cadence pin under MidiMirror load
- [ ] `tauri/ui/tests/learn/` directory (NEW) + the 14 spec files enumerated above
- [ ] Vite config edit: add `learn: resolve(projectRoot, "learn.html")` to `rollupOptions.input`
- [ ] `tauri/ui/learn.html` — 5th HTML entry point (mirrors `debrief.html`)
- [ ] `tauri/src-tauri/capabilities/default.json` — add `open_learn_window` if Tauri 2.x requires per-command capability gating

*Existing infrastructure covers IPC count-parity (`scripts/check_ipc_schema.py`) — no new infra needed for that single gate.*

---

## Manual-Only Verifications

| Behavior | REQ-ID | Why Manual | Test Instructions |
|----------|--------|------------|-------------------|
| Real-controller plug-in time-to-render ≤ 2 s on Kaan's Mac with DDJ-FLX4 | RENDER-01 | Live USB enumeration timing is OS-dependent and cannot be simulated in jsdom | 1. Quit vibemix. 2. Unplug FLX4. 3. Launch vibemix (`uv run python -m vibemix`). 4. Open Learn window. 5. Plug FLX4. 6. Start stopwatch when USB icon appears in macOS menu bar. 7. Stop when FLX4 SVG appears in Learn window. 8. Expect ≤ 2 s P95 over 5 trials. |
| Real-controller knob-twist mirror latency ≤ 50 ms perceived | RENDER-02 | Synthetic jsdom latency is conservative proxy; real Tauri webview should be faster | 1. Plug FLX4 + open Learn. 2. Twist EQ-HI knob deck A continuously. 3. Confirm on-screen knob tracks without perceptible lag (≤ ~1 frame at 60 fps = 16 ms). 4. If sluggish, capture via `VIBEMIX_LATENCY_LOG=1` env (if accepted in Open Decision #1) and report. |
| `Cmd+Tab` between Learn and Deck windows works | RENDER-07 | OS window-manager behavior | 1. Open Deck window. 2. Open Learn window. 3. `Cmd+Tab` — confirm both windows appear in the macOS Cmd+Tab cycle. 4. Repeat with Spaces. |
| Pioneer brand-mark sight-check on rendered FLX4 (lawyer-level) | RENDER-08 (defers to P97) | Subjective trade-dress assessment | (Defers to P98 KAAN-ACTION § LEARN-LEGAL-DISCLAIMER) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (above 11 items)
- [ ] No watch-mode flags
- [ ] Feedback latency < 10 s per-task
- [ ] `nyquist_compliant: true` set in frontmatter (flipped after plan-checker + first wave 0 green)

**Approval:** pending
