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
| (planner fills) | — | — | PERF-01/02/03, LIVE-05/05a | — | N/A | unit | (planner fills) | — | ⬜ pending |

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
