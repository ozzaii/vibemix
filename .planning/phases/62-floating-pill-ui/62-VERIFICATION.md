---
phase: 62-floating-pill-ui
verified: 2026-05-22T01:35:00Z
status: human_needed
score: 4/4 must-haves verified (engineering); 6 KAAN-ACTION live-confirm items remain
overrides_applied: 0
re_verification:
human_verification:
  - test: "Felt drag-on-unfocused-window: build + run, drag the pill while the DJ app is focused"
    expected: "The pill follows the cursor smoothly with no focus flash; startDragging() over the top 28px strip moves the window (tauri#11605/#10767)"
    why_human: "OS-runtime drag behavior on a non-activating window cannot be exercised from code/tests — only on the built app"
  - test: "Focus non-steal: click the pill, then type on the keyboard"
    expected: "Keystrokes land in the DJ app, NOT vibemix — confirms the .focused(false) + Accessory-policy floor suffices vs. needing the dropped NSPanel non-activating mask (wry#637 / tauri#14102)"
    why_human: "First-click key-window transfer on a plain NSWindow is OS-runtime-only; the NSPanel swizzle was correctly dropped (CR-01) so this floor must be felt-verified"
  - test: ".dmg transparency parity: build the .dmg (NOT tauri dev), open it, look at the pill"
    expected: "The pill renders as a floating dark-glass lozenge over the desktop — NOT an opaque white box (tauri#13415, OPEN, no upstream fix)"
    why_human: "The DMG-build transparency regression only manifests in the packaged .dmg, not in dev; the explicit --glass-3 rgba is the engineering hedge but the felt result is build-only"
  - test: "Windows transparency parity: run the built app on Windows"
    expected: "The explicit --glass-3 rgba surface renders as glass — no opaque white box from the absence of OS vibrancy"
    why_human: "Windows compositor behavior is not reachable from this macOS engineering environment"
  - test: "Multi-monitor felt clamp: drag the pill to a second display, unplug it / change resolution"
    expected: "The pill re-clamps back into the visible work area (the ScaleFactorChanged arm); it never goes 'missing' off-screen"
    why_human: "Display-topology change events fire only on real hardware; clamp_to_work_area math is unit-tested but the live re-clamp is felt-only"
  - test: "Rendered look of the 4 states on the running app"
    expected: "Compact dark-glass lozenge: idle dim dot + IDLE label; listening/speaking transitions; the waveform animates on REAL AI speech; expand grows DOWN showing reaction text + citation chips + deck chips, then collapses after ~6s"
    why_human: "Visual rendering + animation feel is not assertable from code; the state machine + waveform + chips are unit-verified but the felt render is live-only"
---

# Phase 62: Floating Pill UI Verification Report

**Phase Goal:** A small, transparent, always-on-top, draggable Super-Whisper-style pill becomes the **primary** live surface — positionable anywhere on screen, multi-monitor safe, never stealing keyboard focus mid-set or covering critical deck info. It consumes the existing ws:8765 frames (no new port, no Python delivery change), shows idle/listening/speaking/expand-on-event states with the real TTS waveform + citation strip, and demotes the Three.js mascot to opt-in/secondary without regressing it.

**Verified:** 2026-05-22T01:35:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (the 4 PILL Success Criteria)

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| PILL-01 | Small, always-on-top, transparent, draggable pill, positionable anywhere, multi-monitor safe (clamp-to-visible), mac+win parity via explicit `--glass-*` fallback | ✓ VERIFIED (engineering); felt = KAAN-ACTION | `pill_window.rs` builder has `transparent(true)` + `always_on_top(true)` + `decorations(false)` + `skip_taskbar(true)` + `focused(false)`, `resizable(false)`, NO `set_ignore_cursor_events` (interactive, not click-through). `clamp_to_work_area` + `ScaleFactorChanged` re-clamp arm; off-screen-origin fallback. `pill.css:45` `background: var(--glass-3)` explicit rgba(2,3,6,0.88), backdrop-filter as enhancement only (`:55`). `startDragging()` over top-28px strip (`index.ts:325`). Rust tests 61/61 incl. `clamp_to_work_area_keeps_visible`, `defaults_pin_context_decisions` (280×44). |
| PILL-02 | Pill is PRIMARY via tri-state `primary_surface` (pill default \| mascot \| none); mascot kept + `mascot-audit` fence green | ✓ VERIFIED | `config.rs` `PrimarySurface` enum `#[default] Pill`, lowercase serde, `load_primary_surface` → Pill default. `main.rs:162` `match load_primary_surface().unwrap_or_default()` selects pill/mascot/none branches. Tests: `primary_surface_decodes_legacy_missing_as_pill`, `primary_surface_roundtrips_via_serde_json`. mascot.html byte-stable (last touched Phase 57, no Phase-62 diff). `mascot-audit` grep gate `tests/mascot/test_ci_grep_gates.py` 7/7 green; SNAPSHOT.json lists both `mascot` + `pill`. |
| PILL-03 | Consumes existing ws:8765 frames (no new port/delivery change); idle/listening/speaking/expand with real TTS waveform (voice.rms) + citation strip + deck chips | ✓ VERIFIED | `ws_bus.py:342` additive read-only `deck_state: _serialize_deck_state(state)` on the EXISTING mascot_frame; honest-null camelot/key/bpm (`:101-108`). Pill `connectMascotBus("ws://127.0.0.1:8765")` (`index.ts:336`). Pure 4-state machine (idle/listening/speaking/expand, no wall-clock/timers, collapseAt data field). `setWaveform(el, rms, peak)` driven by REAL voice.rms (`waveform.ts`). `renderCitationStrip` imported + reused verbatim (defined ONCE in `session/components/citation-strip.ts`). Deck chips honest-unknown (`decks · unknown` fallback, amber-only-when-resolved). Tests: ws_bus deck_state 5/5; pill suite 66/66. |
| PILL-04 | Never steals keyboard focus; drag-on-unfocused-window resolved; drag-capability debt closed via `"pill"` allowlist | ✓ VERIFIED (engineering); focus-non-steal felt = KAAN-ACTION | `focused(false)` builder + pill-scoped `set_activation_policy(Accessory)` (`apply_nonactivating`, called ONLY in Pill branch — WR-01 scoped). The unsound NSPanel swizzle CORRECTLY DROPPED (CR-01: violates `set_class` subclass+ivar contract, would SIGABRT under `panic="abort"`). `"pill"` label in `capabilities/default.json:5` windows scope so `core:window:allow-start-dragging` applies; SNAPSHOT.json regenerated (capability_snapshot 7/7 green). |

**Score:** 4/4 truths verified at the engineering level. 6 felt/visual/build items are honestly classified KAAN-ACTION (status: human_needed).

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `tauri/src-tauri/src/pill_window.rs` | Pill window builder + geometry persist/debounce/off-screen + display re-clamp + macOS focus floor + tests | ✓ VERIFIED | 478 lines. `PILL_WINDOW_LABEL="pill"`. Builder flags correct; no click-through; clamp math pure + unit-tested. NSPanel swizzle removed (doc-only references remain). |
| `tauri/src-tauri/src/config.rs` | `PrimarySurface` tri-state (default Pill) + load/save + serde + legacy-decode tests | ✓ VERIFIED | Enum + `#[default] Pill` + lowercase serde + `load_primary_surface`/`save_primary_surface` (`#[allow(dead_code)]`, no v1 caller — forward scaffolding). |
| `tauri/src-tauri/src/main.rs` | `mod pill_window;` + setup() surface-selection branch | ✓ VERIFIED | `:27 mod pill_window;`; `:162` surface match → create_pill/create_mascot/none, each non-fatal (logs, no bail). |
| `tauri/src-tauri/capabilities/default.json` | `"pill"` window label in allowlist | ✓ VERIFIED | `:5 "windows": ["main","mascot","overlay-*","debrief","pill"]`; `core:window:allow-start-dragging` present; pill gets no shell/fs/process perms (least privilege). |
| `src/vibemix/runtime/ws_bus.py` | Additive read-only `deck_state` field, honest-null | ✓ VERIFIED | `_serialize_deck_state` pure read; field on mascot_frame; bpm honest-null (CR-02 fix: `:108`). Single-writer untouched. |
| `tauri/ui/pill.html` | Transparent-overlay entry (mascot.html invariant cloned), loads index.ts | ✓ VERIFIED | `background: transparent !important` + `body::before display:none`; 4 mount points; drag strip; loads `/src/pill/index.ts`. |
| `tauri/ui/src/pill/state-machine.ts` | Pure 4-state derivation | ✓ VERIFIED | `baseState`/`applyFrame`/`tickCollapse` — now-param, no timers, collapseAt data field. 18 tests. |
| `tauri/ui/src/pill/index.ts` | Boot + connectMascotBus + drag + handleFrame + waveform + citation wiring | ✓ VERIFIED | `connectMascotBus` (`:336`), `startDragging()` (`:325`), `renderCitationStrip` (`:224`), `readDeckState` replace-not-merge (WR-03), WR-06 chip shape guard. 18 tests. |
| `tauri/ui/src/pill/waveform.ts` | TTS waveform reusing meter.ts tokens, driven by voice.rms | ✓ VERIFIED | `setWaveform(el, rms, _peak)` clamps rms 0..1, real signal. 9 tests. |
| `tauri/ui/src/pill/deck-chips.ts` | deck_state → chips, honest unknown, amber-only-when-resolved | ✓ VERIFIED | `deckChipText`/`buildDeckChip` guard `bpm > 0` (CR-02), `camelot ?? "unknown"`, confidence cite-floor `--unsure` (WR-04 fix). 21 tests. |
| `tauri/ui/src/pill/pill.css` | Explicit `--glass-3` rgba surface, token-only | ✓ VERIFIED | `:45 background: var(--glass-3)`; backdrop-filter enhancement-only; no hardcoded hex. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `pill_window.rs` | `capabilities/default.json` | `PILL_WINDOW_LABEL == "pill"` in windows allowlist | ✓ WIRED | Constant = `"pill"`; allowlist contains `"pill"`; `label_constant_matches_capability_allowlist` test passes. |
| `pill_window.rs` builder | `WebviewWindowBuilder` | transparent+always_on_top+decorations(false)+focused(false), NO ignore_cursor_events | ✓ WIRED | All flags present `:190-199`; click-through deliberately absent `:201`. |
| `main.rs setup()` | `load_primary_surface` + `create_pill_window` + `create_mascot_window` | match on PrimarySurface | ✓ WIRED | `:162-196`. |
| `config.rs PrimarySurface::default()` | `PrimarySurface::Pill` | `#[default]` on Pill | ✓ WIRED | `:124-125`; legacy-decode test green. |
| `ws_bus.py mascot_frame` | `MusicState.deck_state.decks` | additive read-only per-deck serialize | ✓ WIRED | `:342` + `_serialize_deck_state` `:71-112`. |
| `deck_state` wire field | `DeckTrack.camelot/key/bpm` (honest None) | null on the wire when unresolved | ✓ WIRED | `:101-108`; bpm `>0` guard; ws_bus deck_state tests green. |
| `pill/index.ts` | `ws://127.0.0.1:8765` | `connectMascotBus` (copied client, decoupled from src/mascot) | ✓ WIRED | `:336`; ws-client.ts copies (not imports) to keep mascot-audit clean. |
| `pill/index.ts` | `citation-strip.ts renderCitationStrip` | expand renders citation strip verbatim | ✓ WIRED | import `:27`, call `:224`; renderCitationStrip defined ONCE (not reimplemented). |
| `pill/index.ts` drag | `getCurrentWindow().startDragging()` | mousedown over top 28px strip (chips data-no-drag exempt) | ✓ WIRED | `:320-326`. |
| `pill/deck-chips.ts` | 62-03 deck_state wire field | one chip per resolved deck | ✓ WIRED | `renderDeckChips` over `Object.entries(deckState)`; honest fallback chip. |
| `pill/pill.css` | visible pill surface | explicit `--glass-3` rgba (not OS vibrancy) | ✓ WIRED | `:45`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| pill waveform | `voiceRms` | `Levels.update_voice` AI-speech RMS on the existing ws:8765 frame (flat `voice` or nested `meters.voice.rms`) | Yes — real bus signal, not animation | ✓ FLOWING |
| pill citation strip | `chips` | `cohost-reaction.citation_strip` off the wire (EvidenceRegistry chips), WR-06 shape-validated | Yes — reused verbatim renderer | ✓ FLOWING |
| pill deck chips | `view.deckState` | `ws_bus._serialize_deck_state(state)` reading Phase-59 `MusicState.deck_state.decks` (registry-observed DeckTrack) | Yes — real per-deck data; honest-null when unresolved | ✓ FLOWING |
| pill base state | `cohostStatus` | `cohost_status` on the wire (IDLE/LISTENING/TALKING) | Yes — real status drives baseState | ✓ FLOWING |

### Behavioral Spot-Checks (test suites run in-process)

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Rust window/config/surface logic | `cargo test` | 61 passed; 0 failed | ✓ PASS |
| UI pill state/waveform/chips/index | `npx vitest run` | 787 passed (81 files); pill suite 66/66 | ✓ PASS |
| TypeScript types | `npx tsc --noEmit` | exit 0 | ✓ PASS |
| Python full suite | `pytest -q` | 7 failed (baseline WIP), 4090 passed, 26 skipped | ✓ PASS (baseline — see below) |
| ws_bus deck_state serialization | `pytest tests/runtime/test_ws_bus_deck_state.py` | 5 passed | ✓ PASS |
| mascot-audit grep gate | `pytest tests/mascot/test_ci_grep_gates.py` | 7 passed | ✓ PASS |
| capability snapshot in sync | `pytest -k capability_snapshot` | 7 passed | ✓ PASS |
| CR-02 honest-null bpm | pill `deck-chips.test.ts` `bpm:0 → "a · 8a · unknown"` | passes | ✓ PASS |

**Python baseline note:** The 7 failures (`test_main_anti_slop_wiring`, `test_cut_release_invokes_bravoh_server`, `test_readme_feature_matrix_sync` x2, `test_cut_release_preflight` x2, `test_main_smoke`) match the documented `live-tuning-or-brain` WIP baseline EXACTLY. Verified independently: none reference pill/ws_bus/deck_state/primary_surface (grep returned no matches), and Phase-62 changes are all-new additions (692 insertions across 4 source files, 0 deletions in shared paths). Zero NEW Phase-62 regressions.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| PILL-01 | 62-01, 62-05 | always-on-top/transparent/draggable pill, multi-monitor safe | ✓ SATISFIED | pill_window.rs builder + clamp + pill.css --glass-3; engineering green, felt = KAAN-ACTION |
| PILL-02 | 62-02 | primary via tri-state primary_surface; mascot kept, fence green | ✓ SATISFIED | config.rs enum + main.rs selection + mascot-audit 7/7 + SNAPSHOT pill/mascot |
| PILL-03 | 62-03, 62-04, 62-05 | consumes ws:8765, 4 states, real waveform + citation + deck chips | ✓ SATISFIED | additive deck_state + connectMascotBus + pure state machine + voice.rms waveform + reused citation strip + honest deck chips |
| PILL-04 | 62-01 | never steals focus; drag-on-unfocused resolved; capability debt closed | ✓ SATISFIED | focused(false) + Accessory floor (NSPanel dropped per CR-01) + "pill" allowlist + SNAPSHOT regenerated; focus-non-steal felt = KAAN-ACTION |

No orphaned requirements — all 4 PILL IDs claimed by plans and verified.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | — | No TBD/FIXME/XXX debt markers in any Phase-62 file | — | Completion is auditable |
| (none) | — | No TODO/HACK/placeholder/not-implemented in any Phase-62 file | — | No stubs |
| `pill_window.rs` | 344-356 | Geometry re-query (window_position/window_size) instead of event payload (WR-02) | ℹ️ Info | Cloned VERBATIM from shipped `mascot_window.rs` (identical structure); deferred for verbatim parity per phase decision — the mascot ships with the same code, not a Phase-62-introduced defect |
| `config.rs` | 221-233 | `save_primary_surface` dead code (no v1 caller) | ℹ️ Info | Correctly `#[allow(dead_code)]` with comment; forward scaffolding for the deferred Settings toggle |

### Code-Review Resolution Status (62-REVIEW.md)

| Finding | Severity | Status |
| ------- | -------- | ------ |
| CR-01: NSPanel swizzle unsound (set_class contract + panic=abort SIGABRT) | 🛑 Blocker | ✓ FIXED — swizzle DROPPED, Accessory floor only; only doc comments reference the removed stretch |
| CR-02: unresolved deck `bpm: 0.0` → fabricated "0" | 🛑 Blocker | ✓ FIXED — ws_bus.py:108 `bpm > 0 else None` + deck-chips.ts `bpm > 0` guard + test pin |
| WR-01: Accessory policy process-global | ⚠️ Warning | ✓ FIXED — scoped to Pill branch only (apply_nonactivating reached only from create_pill_window) |
| WR-02: geometry re-query race | ⚠️ Warning | ◷ DEFERRED — verbatim parity with mascot_window.rs (documented decision) |
| WR-03: stale deck context after unload | ⚠️ Warning | ✓ FIXED — replace-not-merge; empty `{}` clears chips; test pinned |
| WR-04: confidence rides wire but unused | ⚠️ Warning | ✓ FIXED — `--unsure` cite-floor dims low-confidence resolved key |
| WR-05: module-level memo globals | ⚠️ Warning | ✓ FIXED (per phase facts; 5/6 warnings fixed) |
| WR-06: citation chips unvalidated cast | ⚠️ Warning | ✓ FIXED — `isCitationChip` per-element shape guard |

### Human Verification Required (KAAN-ACTION on the BUILT app)

These are the felt/visual/build items honestly carved out by the phase brief — provable only on Kaan's running/packaged app, never from code or tests. The engineering substrate for each is VERIFIED above.

1. **Felt drag-on-unfocused-window** — drag the pill while the DJ app is focused; expect smooth follow, no focus flash (tauri#11605/#10767).
2. **Focus non-steal** — click the pill, then type; keystrokes must reach the DJ app, confirming the `.focused(false)` + Accessory floor suffices vs. the dropped NSPanel mask (wry#637 / tauri#14102).
3. **`.dmg` transparency parity** — open the built `.dmg` (not `tauri dev`); pill must be a dark-glass lozenge, not a white box (tauri#13415, OPEN).
4. **Windows transparency parity** — explicit `--glass-3` renders as glass on Windows (no opaque white box).
5. **Multi-monitor felt clamp** — drag to a second display, unplug/change resolution; pill re-clamps on-screen (never goes missing).
6. **Rendered look of the 4 states** — compact lozenge, real waveform on AI speech, expand grows DOWN with reaction + citation + deck chips, collapses ~6s.

### Gaps Summary

No engineering gaps. All 4 PILL success criteria are achieved in the actual codebase, not merely claimed: the pill window builds with the correct transparent/on-top/draggable/non-click-through flags; the tri-state `primary_surface` config defaults to Pill with legacy→pill decode and main.rs surface selection; the pill consumes the existing ws:8765 frame via an additive read-only `deck_state` field with end-to-end honest-null (the central anti-slop guarantee), a pure 4-state machine, a real-voice.rms waveform, the verbatim-reused citation strip, and honest deck chips; the `"pill"` capability allowlist + regenerated SNAPSHOT close the v0.1.0-rc1 drag debt; the mascot is demoted-not-deleted with the mascot-audit fence green. Both code-review BLOCKERS (CR-01 unsound swizzle dropped, CR-02 bpm honest-null) are fixed and test-pinned; 5/6 warnings fixed; WR-02 deferred for documented verbatim mascot parity. Test baselines hold: Rust 61/61, UI 787/787 + tsc 0, Python 7 baseline WIP failures (no new Phase-62 regressions).

The status is **human_needed** (not passed) solely because the phase brief deliberately carves out 6 felt/visual/build items that are unverifiable from code by design (drag feel, focus non-steal, .dmg + Windows transparency, multi-monitor clamp feel, rendered 4-state look). These are KAAN-ACTION live-confirm on the built app, not code defects.

---

_Verified: 2026-05-22T01:35:00Z_
_Verifier: Claude (gsd-verifier)_
