---
phase: 56-performance-live-mascot
verified: 2026-05-21T07:10:00Z
status: human_needed
score: 13/13 engineering must-haves verified
overrides_applied: 0
human_verification:
  - test: "Live-drive both modes on Kaan's MacBook — TTFT feels instant (trigger → first audio out)"
    expected: "Reactions land in-bar; first audio out feels instant, no perceptible 'thinking' lag. Numeric live-path TTFT measured on real hardware confirms the budget."
    why_human: "Felt latency on real hardware + real Gemini stream. The engineering floor (LIVE_TTFT_BUDGET_MS=1500ms regression floor + MINIMAL-thinking gate pinned in CI) is in place; the felt 'instant' confirmation is the intentional Kaan-action carveout per 56-CONTEXT deferred items and gsd-autonomous fully mode."
  - test: "Run a full real set, both modes — listen for any audio glitch/dropout in the playback path"
    expected: "Zero audible dropouts/glitches across a full-set run under real-session load."
    why_human: "Audible playback quality on real CoreAudio + BlackHole under real load. The zero-underrun soak floor (PERF-02) is pinned in CI on a real PlaybackQueue under simulated both-mode traffic; the ≥30-min real-hardware soak + felt confirmation is Kaan-action."
  - test: "Watch the mascot + UI during a live session — confirm 60fps on the integrated-GPU MacBook"
    expected: "Mascot rAF loop + UI hold 60fps with no visible jank during mode transitions across a live session."
    why_human: "Rendered frame rate on the actual integrated-GPU MacBook. The webview-side dispatch-latency floor (PERF-03, p95<50ms with a mode-transition frame, measured ~0.22ms) is pinned in CI; the felt 60fps under real GPU load is Kaan-action."
  - test: "Drive a real set and watch the mascot — does it visibly track real drops/builds/breakdowns and switch to a speaking mode while the AI talks, feeling alive and grounded (no decorative/random flips)?"
    expected: "Mascot state visibly changes mode on real musical events (drop/build/breakdown), enters a speaking mode while the AI talks, and never flips on a contradictory/quiet frame. Feels like a present co-host, not AI slop."
    why_human: "Felt 'mascot feels alive across its modes under a real set' is a visual/UX judgment on real hardware. The grounded engineering — 6 reachable modes each gated to a real bus event, music-confirmation anti-slop guard, speaking-overrides-music, mood/emotion tint discipline — is fully pinned in tests; the felt sign-off is Kaan's eyes (live-drive UAT carveout)."
---

# Phase 56: Performance + Live Mascot Verification Report

**Phase Goal:** On the real machine under live-session load, the co-host hits peak performance — reactions fast (TTFT within budget), audio never glitches, UI + mascot hold 60fps — and the Neon Rebel mascot is a live, correct feedback surface that telegraphs what the system saw from real audio/MIDI events across its many modes.

**Verified:** 2026-05-21T07:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

This was an EXTEND-AND-PIN phase on an already-shipped Three.js mascot rig + existing Python perf substrates. The engineering deliverables (the music-confirmation anti-slop guard, the six reachable modes, speaking-override, the TTFT/thinking-gate/soak/dispatch-latency regression floors) are all present, substantive, wired, and green. The four felt-quality success criteria (TTFT instant / 60fps / no-dropout / mascot feels alive under a real set on Kaan's Mac) are the **intentional Kaan-action live-drive carveout** — surfaced as human verification, NOT engineering gaps. Per the Step-9 decision tree, a non-empty human-verification section forces `status: human_needed` even though all engineering truths verified at 13/13.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A `phase=drop` frame with `music < PEAK_RMS` does NOT trigger peak/dance mode (held — anti-slop) | ✓ VERIFIED | `event-dispatcher.ts:149` `stateForPhase` returns `dance_hard` only when `music >= PEAK_RMS (0.11)` else `null`; PHASE case (`:242`) returns null → mode held. Pinned by `anti_slop_drop_quiet` fixture + discriminating held-mode test (verified RED if guard removed). |
| 2 | A `phase=breakdown` frame with `music >= LOW_RMS` does NOT trigger breakdown mode (held) | ✓ VERIFIED | `event-dispatcher.ts:152` returns `idle_breathe` only when `music < LOW_RMS (0.04)` else `null`. |
| 3 | The mascot reads music + voice off the bus snapshot, not just bpm/mood/downbeat | ✓ VERIFIED | `SnapshotSlice` gains `music`/`voice` (`event-dispatcher.ts:80-82`); `index.ts:208-217` threads flat `m.music`/`m.voice` off the live ws frame; fixture harness reads nested `{rms}`. `currentSnapshot.music` thread count = 2. |
| 4 | Hysteresis / a single contradictory frame does not flip the mode | ✓ VERIFIED | Contradiction → `return null` → current mode persists (`event-dispatcher.ts:242`); pre-existing `planTransition`/`schedule_for_downbeat` hysteresis untouched and pure. |
| 5 | The multi-mode trace silent→build→drop→breakdown→voice>0 enters the correct mode at each step | ✓ VERIFIED | `multi_mode_sequence` (criterion 5) present in `event-traces.json`; auto-replayed green by the trace-iterating runner (vitest 703 passed). |
| 6 | All six contract modes are reachable from real bus events | ✓ VERIFIED | `six_mode_reachability` trace + explicit assertion (`state-machine-fixtures.test.ts:342`) asserts idle/vibing/building/drop/breakdown reachable and `talk_loop` (speaking) reached. Maps to existing `idle_breathe`/`idle_bop_to_beat_mellow`/`idle_bop_to_beat_energetic`/`dance_hard`/`talk_loop`. |
| 7 | The speaking path (talk_loop, priority 80) overrides every music mode mid-talk | ✓ VERIFIED | `speaking_overrides_music` trace + held assertion (`state-machine-fixtures.test.ts:376`): a `PHASE->groove` during talk is `blocked_by_talk` (`state-machine.ts:166-170`, talk class denies lower priority); talk_loop persists. Priority ladder talk=80 > dance=40 (`types.ts:12`). |
| 8 | mood tints the same mode (variant), emotion is a finer nudge, emotion==null is a no-op | ✓ VERIFIED | mood-is-a-tint assertion (`:413`, mood-only snapshot → no transition; same target regardless of mood) + emotion==null no-op assertion (`:449`). mood/emotion never branch the FSM. |
| 9 | Replayed reaction traffic keeps TTFTMeter rolling-avg ≤ a named budget (PERF-01) | ✓ VERIFIED | `LIVE_TTFT_BUDGET_MS = 1500.0` (`test_ttft.py:24`); in-budget replay asserts `rolling_avg_ms() <= budget` + `samples_count() >= 8`; over-budget negative control proves teeth. `should_fire` literal count = 0 (no resurrected gate). 31 passed. |
| 10 | The production live `_gen_cfg` passes `validate_live_config`; MEDIUM/HIGH/FLEX rejected (PERF-01 lever) | ✓ VERIFIED | Production `_gen_cfg` uses `thinking_level="minimal"` + re-runs `validate_live_config` (`dj_cohost.py:415,427`); gate enforces MINIMAL + non-FLEX (`thinking_gate.py:40,43`). Tests: positive pin + MEDIUM/HIGH/FLEX negative pins raising `LiveCoachConfigError`; e2e leg green (4 passed, marker fix landed). |
| 11 | A real PlaybackQueue under simulated both-mode traffic records zero underruns (PERF-02) | ✓ VERIFIED | `test_soak_stability.py:182,194` `assert_healthy(..., max_underruns=0)` over `run_soak` on a real `PlaybackQueue` under both-mode traffic; reuses Phase-51 soak counter (no new counter). 3 passed (slow). |
| 12 | A synthetic mode-transition frame keeps dispatch p95 sidecar→client < 50ms (PERF-03 floor) | ✓ VERIFIED | `test_mascot_dispatch_latency.py`: `MODE_TRANSITION_FRAME = FRAME_COUNT//2` REPLACES one seq frame (`:153`, still carries seq + t_emit_ns); both loops bound to `range(FRAME_COUNT)` (`:151,:181`); sanity gate ≥95 samples (`:224`); `P95_BUDGET_MS=50.0` unchanged; no mascot.html ref. 2 passed; measured p95 ~0.22ms. |
| 13 | FSM purity preserved (no Date.now/setTimeout/three imports in dispatcher/state-machine) | ✓ VERIFIED | Purity grep on `event-dispatcher.ts` + `state-machine.ts` returns zero real-code matches; tsc --noEmit exit 0. |

**Score:** 13/13 engineering truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tauri/ui/src/mascot/event-dispatcher.ts` | music/voice SnapshotSlice + PEAK_RMS/LOW_RMS guard | ✓ VERIFIED | Guard at `:144-164`; named consts `:62,:64`; PHASE case threads `snapshot.music` `:240`. Committed clean. |
| `tauri/ui/src/mascot/index.ts` | thread flat music/voice off live ws frame | ✓ VERIFIED | `:208-217` reads `m.music`/`m.voice`; default object `:173-174`. |
| `tauri/ui/src/mascot/__fixtures__/event-traces.json` | 4 new traces (multi_mode, anti_slop, six_mode, speaking_overrides) | ✓ VERIFIED | All present; each criterion 5; cross-language taxonomy pin green. |
| `tauri/ui/src/mascot/state-machine-fixtures.test.ts` | nested-rms reader + new assertions | ✓ VERIFIED | Six-mode, speaking-override-held, mood-tint, emotion-null assertions present + green. |
| `tests/runtime/test_ttft.py` | named budget assertion + negative control | ✓ VERIFIED | `LIVE_TTFT_BUDGET_MS`, in-budget + over-budget cases. |
| `tests/llm/test_thinking_gate.py` | positive prod-config pin + MEDIUM/HIGH/FLEX negatives | ✓ VERIFIED | `validate_live_config` count 23; negative pins raise. |
| `tests/e2e/test_phase_41_latency_stack_integration.py` | e2e PERF-01 leg (now @e2e-marked) | ✓ VERIFIED | 4 passed -m e2e. |
| `tests/runtime/test_soak_stability.py` | both-mode zero-underrun scenario | ✓ VERIFIED | `max_underruns=0` count 4; both-mode soak green. |
| `tests/integration/test_mascot_dispatch_latency.py` | mode-transition frame, FRAME_COUNT held, budget 50.0 | ✓ VERIFIED | MODE_TRANSITION_FRAME replaces a seq frame; p95<50ms holds. |

### Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| index.ts live ws frame | event-dispatcher SnapshotSlice | `currentSnapshot.music`/`.voice` threaded from flat frame | ✓ WIRED (`index.ts:208-217`) |
| event-dispatcher PHASE case | stateForPhase music guard | `stateForPhase(to, snapshot.music)` | ✓ WIRED (`:240`) |
| test_thinking_gate.py | production `_gen_cfg` via validate_live_config | positive pin on real minimal config + negative pins | ✓ WIRED |
| test_soak_stability.py | soak.run_soak / real PlaybackQueue | both-mode drive → assert_healthy(max_underruns=0) | ✓ WIRED |
| test_mascot_dispatch_latency.py | MASCOT-08 50ms sidecar-side budget | emit mode-transition frame, assert p95 < P95_BUDGET_MS | ✓ WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| event-dispatcher.ts mode select | `snapshot.music`/`.voice` | live ws frame (`levels.snapshot()` flat floats) via index.ts → currentSnapshot | ✓ real bus levels; thresholds mirror Python source-of-truth `constants.py` (PEAK_RMS=0.110, LOW_RMS=0.040 — confirmed unchanged by WIP) | ✓ FLOWING |
| test pins (PERF) | TTFTMeter samples / PlaybackQueue pulls / gen config | real TTFTMeter, real PlaybackQueue, production `_gen_cfg` | ✓ exercises real substrates, not mocks | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Mascot rig (LIVE-05/05a + PERF-03 webview) | `cd tauri/ui && npm test` | 75 files, 703 passed | ✓ PASS |
| TS typecheck | `npx tsc --noEmit` | exit 0, no errors | ✓ PASS |
| TTFT + thinking-gate (PERF-01) | `pytest -q tests/runtime/test_ttft.py tests/llm/test_thinking_gate.py` | 31 passed | ✓ PASS |
| Soak both-mode zero underruns (PERF-02) | `pytest -q -m slow tests/runtime/test_soak_stability.py` | 3 passed, 7 deselected | ✓ PASS |
| e2e latency stack (PERF-01) | `pytest -q -m e2e tests/e2e/test_phase_41_latency_stack_integration.py` | 4 passed, 12 deselected | ✓ PASS |
| Dispatch-latency mode-transition (PERF-03) | `pytest -q -m integration tests/integration/test_mascot_dispatch_latency.py` | 2 passed | ✓ PASS |
| Cross-language fixture taxonomy pin | `pytest -q -m integration tests/integration/test_mascot_event_taxonomy_e2e.py` | 4 passed | ✓ PASS |

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` probes declared or implied for this phase. The phase-declared verification is the marker-scoped pytest + vitest suites above — all executed in-process and green. N/A.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PERF-01 | 56-02 | TTFT meets live-path latency budget | ✓ SATISFIED (engineering floor); felt confirmation → human | LIVE_TTFT_BUDGET_MS floor + MINIMAL-thinking gate pinned (positive + MEDIUM/HIGH/FLEX negatives). |
| PERF-02 | 56-02 | No audio glitches/dropouts under load | ✓ SATISFIED (engineering floor); felt confirmation → human | Zero-underrun soak on real PlaybackQueue, both-mode traffic. |
| PERF-03 | 56-03 | Mascot + UI hold 60fps | ✓ SATISFIED (webview floor); felt 60fps → human | Dispatch p95<50ms with mode-transition frame (~0.22ms). |
| LIVE-05 | 56-01, 56-03 | Mascot reacts off rich bus signals | ✓ SATISFIED | SnapshotSlice carries music/voice + phase/bpm/mood/downbeat; mood/emotion tint discipline pinned. |
| LIVE-05a | 56-01, 56-03 | Mascot has many distinct modes, each grounded | ✓ SATISFIED (engineering); felt-alive → human | 6 reachable modes each gated to a real bus event; music-confirmation anti-slop guard; speaking-overrides-music. |

All 5 phase requirement IDs (PERF-01/02/03, LIVE-05, LIVE-05a) appear in REQUIREMENTS.md mapped to Phase 56, are claimed by the plans, and are accounted for. No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | none | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER in any of the 9 modified files. No stubs (all changes are real guard logic, real test assertions over real substrates). |

Note: the `event-dispatcher.ts` doc-comment intentionally token-splits the purity-gate strings (lines 24-27) so the verifier grep stays clean — this is by-design, not an anti-pattern.

### Human Verification Required

These are the four **felt-quality success criteria** — the intentional Kaan-action live-drive carveout per 56-CONTEXT deferred items and `gsd-autonomous fully` mode. The engineering floors are all in place and green in CI; the felt confirmation needs Kaan's eyes/ears on real hardware. They are NOT engineering gaps.

1. **TTFT feels instant (live-drive both modes)** — reactions land in-bar, no perceptible thinking lag; numeric live-path TTFT measured on the real MacBook meets budget.
2. **No audio dropouts across a full set** — listen for any glitch/dropout in the playback path under real-session load.
3. **60fps on the integrated-GPU MacBook** — mascot rAF + UI hold 60fps with no visible jank during mode transitions in a live session.
4. **Mascot feels alive across its modes** — visibly tracks real drops/builds/breakdowns, enters a speaking mode while the AI talks, never flips on a contradictory frame; feels grounded, not AI slop.

### Deferred Items

None routed to later phases. (Per-mode art/animation polish may land in Phase 57 Sexify, but the mode/treatment mapping itself is fully proven here and is not a gap.)

### Gaps Summary

No engineering gaps. All 13 engineering must-haves are VERIFIED with codebase evidence: the music-confirmation anti-slop guard, music/voice SnapshotSlice + live-frame threading, the six reachable modes, speaking-overrides-music via the existing block rule, mood/emotion tint discipline, FSM purity, the TTFT telemetry budget + MINIMAL-thinking gate positive/negative pins, the zero-underrun both-mode soak, and the dispatch-latency mode-transition floor (FRAME_COUNT held, budget 50ms unchanged). All 9 task commits are in git history; all 9 phase-56 files are committed clean. Phase-scoped suites match the orchestrator's post-merge confirmation exactly (vitest 703, ttft+thinking_gate 31, soak 3, e2e 4, dispatch-latency 2, taxonomy 4); tsc --noEmit clean; no debt markers/stubs.

The four felt-quality success criteria are the intentional Kaan-action live-drive carveout (his eyes/ears on real hardware) and are surfaced as human verification — this is correct for the project's `gsd-autonomous fully` mode and forces `status: human_needed` per the decision tree. The parallel uncommitted WIP (persona/prompt tuning in `__main__.py`/`dj_cohost.py`/`constants.py`/`matrix.py`/agent tests/Tauri src) is out of Phase-56 scope, does not overlap any phase-56 file, and was confirmed not to alter the load-bearing RMS thresholds or the thinking-gate lever this phase depends on.

---

_Verified: 2026-05-21T07:10:00Z_
_Verifier: Claude (gsd-verifier)_
