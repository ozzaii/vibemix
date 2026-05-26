---
phase: 79
slug: lens-three-grounded-modes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 79 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "lens or matrix or curator or persona or citation or linter or apply_lens"` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (scoped `-k`)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> Populated by the planner. Every LENS-0x requirement maps to an automated proof — no API key. Lens→(mode,mood) mapping + shared-selection + per-lens citation-gate are all pure prompt-shape / strip-decision assertions. The "does each lens FEEL right / did the tutor teach" judgment is Phase-81 BENCH (lens dimension) + Kaan's-ear (parked, never faked, never blocks).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | — | 0 | LENS-01/02 | unit | Wave-0 test stubs | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test for LENS-01: hype/critique/tutor each map to a distinct grounded prompt over the SAME evidence; switching lens changes voice/intent, not the facts; `critique`→coach-substrate alias; `tutor` is a real new grounded voice.
- [ ] Test for default-lens byte-identity: the default (`hype`) lens prompt is byte-identical to today's co-host default; the v4 `test_matrix.py` golden stays green (matrix builder/_CELLS/MOOD_PERSONAS untouched).
- [ ] Test for LENS-02: a single shared lens-selection source (`ConfigStore.extra["lens"]` + `_apply_lens`) flows to BOTH `build_system_instruction` and `build_curator_instruction` — choose "tutor" once → both surfaces read it.
- [ ] Test for per-lens citation grounding: all three lenses go through the same gate; un-cited output strips to `<silence/>` (ack-bank retired) regardless of lens — strip decision depends only on `EvidenceRegistry` membership, not the lens.

*Existing pytest infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Each lens FEELS right in a real set (hype rides / critique coaches / tutor teaches through who you are) | LENS-01 | Subjective voice-fidelity — Phase-16 rule | Phase-81 BENCH lens dimension + KAAN-ACTION ear verdict; never auto-judged |

*All unit-level phase behaviors have automated verification (no API); the felt voice-fidelity is the Phase-81 BENCH lens dimension + Kaan's ear (parked, never blocks).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
