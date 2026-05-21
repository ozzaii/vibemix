---
phase: 56
slug: performance-live-mascot
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-21
---

# Phase 56 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python) + vitest (Tauri UI / mascot rig) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`; `tauri/ui/vitest.config.ts` |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <paths>` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (+ `cd tauri/ui && npm test` for the rig) |
| **Estimated runtime** | ~210 seconds (Python) + ~10 seconds (vitest) |

---

## Sampling Rate

- **After every task commit:** Run the quick command scoped to the touched paths
- **After every plan wave:** Run the full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~220 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-----------|--------|
| 56-01-01 | 56-01 | 1 | LIVE-05 | T-56-02 | Widened SnapshotSlice never throws on a missing/odd music/voice field (defaults to prior value) | unit | `cd tauri/ui && npm test -- state-machine-fixtures` | ✅ | ⬜ pending |
| 56-01-02 | 56-01 | 1 | LIVE-05a | T-56-01 | Music-confirmation guard: phase/music disagreement → return null (mode held); no decorative-mode default | unit | `cd tauri/ui && npm test -- state-machine` | ✅ | ⬜ pending |
| 56-01-03 | 56-01 | 1 | LIVE-05a | T-56-01 | Anti-slop trace proves a quiet phase=drop produces no mode flip (held-prior-state assertion) | unit | `cd tauri/ui && npm test -- state-machine-fixtures` | ✅ | ⬜ pending |
| 56-02-01 | 56-02 | 1 | PERF-01 | — | TTFT budget pinned as telemetry over replayed reaction traffic (no hot-path instrumentation) | unit | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/runtime/test_ttft.py -x -q` | ✅ | ⬜ pending |
| 56-02-02 | 56-02 | 1 | PERF-01 | — | Live config positive+negative pinned against the thinking-budget gate (latency lever cannot regress) | unit/e2e | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/llm/test_thinking_gate.py -x -q && PYTHONPATH=src python3 -m pytest tests/e2e/test_phase_41_latency_stack_integration.py -m e2e -x -q` | ✅ | ⬜ pending |
| 56-02-03 | 56-02 | 1 | PERF-02 | — | Zero playback underruns under simulated both-mode reaction traffic (soak stability) | slow | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/runtime/test_soak_stability.py -m slow -x -q` | ✅ | ⬜ pending |
| 56-03-01 | 56-03 | 2 | LIVE-05a | T-56-07 | Every mode entry gated to a real canonical bus event (six-mode reachability) | unit | `cd tauri/ui && npm test -- state-machine-fixtures` | ✅ | ⬜ pending |
| 56-03-02 | 56-03 | 2 | LIVE-05/05a | T-56-08 | talk_loop (prio 80) blocks lower-priority music transitions mid-talk; mood-as-tint, emotion==null no-op | unit | `cd tauri/ui && npm test -- state-machine-fixtures` | ✅ | ⬜ pending |
| 56-03-03 | 56-03 | 2 | PERF-03 | T-56-09 | Mode-transition frame keeps p95 sidecar→client < 50ms (observe, never instrument hot path); FRAME_COUNT contract held | integration | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/integration/test_mascot_dispatch_latency.py -m integration -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements — extend, don't install: `tests/runtime/test_ttft.py` (PERF-01), `runtime/soak.py` + its tests (PERF-02), `tests/integration/test_mascot_dispatch_latency.py` + `tauri/ui` vitest fixture-replay harness (PERF-03 + LIVE-05/05a). No new framework.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Felt TTFT "instant" + 60fps + zero dropouts under a real full set on Kaan's Mac | PERF-01/02/03 | Requires real hardware + Kaan's eyes/ears under real-session load | Run a real set both modes; watch for audio dropouts, frame stutter; confirm reactions feel instant |
| Mascot "feels alive" across its modes on the shipped Three.js rig during a live set | LIVE-05/05a | Felt-quality + real-event grounding is a human judgment | Run a real set; confirm the mascot visibly changes mode on real drops/builds/breakdowns + while the AI talks, no decorative flicker |

*Automated coverage proves grounding + budgets + state-machine correctness; the felt-quality + real-hardware confirmation is the Kaan-action live-drive carveout.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 220s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
</content>
