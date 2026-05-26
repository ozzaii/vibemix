---
phase: 81
slug: bench-the-validation-instrument
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 81 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "bench or cell or matrix or eval or groundedness or specificity or review"` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (scoped `-k`)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## The offline / parked split (READ FIRST)

- **OFFLINE-TESTABLE (the phase test gate):** BENCH-01 harness logic (dimension sweep, per-cell prompt assembly from the real seams, results recording) with a FAKE genai client → zero API; BENCH-02 eval scorers (groundedness via `CitationLinter`, specificity, lens/mode-fidelity) on FIXTURE cells → deterministic, zero API; the BENCH-03 review-surface GENERATION (from fixture cells + scores).
- **PARKED (KAAN-ACTION, never auto-judged, never faked):** the bounded real-cell RUN on the funded key (the produce step — fail-safe parks on API error, never fabricates); the BENCH-03 VERDICT (Kaan's ear picks the winning architecture + model); the final taste-rubric wording (Kaan's IP).

---

## Per-Task Verification Map

> Populated by the planner. Every BENCH requirement's CODE is offline-provable (fake client + fixture cells); the live run + Kaan's verdict are parked KAAN-ACTION.

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | — | 0 | BENCH-01/02/03 | unit | Wave-0 test stubs | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test for BENCH-01: the harness sweeps the 6 dimensions and assembles a per-cell prompt from the REAL seams (model_router/evidence/build_system_instruction flags/MusicState trajectory/build_lens_instruction/taste-rubric); a fake genai client records each cell — zero API. Includes the `no-audio`/`dsp_only` cell.
- [ ] Test for BENCH-01 fail-safe: a per-cell API error (e.g. 429) parks the cell as `{"error": ...}` — never fabricated, never aborts the sweep.
- [ ] Test for BENCH-02: groundedness via `CitationLinter.check(output, cell_snapshot)` (a cell citing an event absent from its snapshot scores ungrounded); specificity + lens/mode-fidelity heuristics are deterministic on fixture cells — zero API.
- [ ] Test for BENCH-03: the review-surface generator produces a ranked, human-readable KAAN-ACTION artifact from fixture cells + scores; it RANKS but records NO verdict (the verdict field is empty/“pending Kaan”).
- [ ] Model-axis uses `model_router.resolve(alias)` only — `test_model_literal_gate.py` stays green (no literal in `bench/`).

*Existing pytest infrastructure covers all offline phase requirements — no framework install needed. The `.mp3` excerpts live under `tests/bench/data/` (outside `src/`, not in the wheel).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The bounded real-cell RUN produces honest cells on the funded key | BENCH-01 | Needs the funded key + real Gemini calls (cost) | KAAN-ACTION: run the documented bench command; the run is cost-bounded + fail-safe (parks on API error, never fabricates) |
| Kaan's-ear verdict — "did it click / is it slop / which architecture + model wins" | BENCH-03 | THE HARD HUMAN GATE — subjective, Phase-16 rule | KAAN-ACTION: read the review surface, judge the cells, pick the winner. Autonomous NEVER fills this in. |
| Final taste-rubric wording ("what 'clicked' means") | BENCH-01 (taste axis) | Kaan's authored IP (like HYPE_INTERMEDIATE) | KAAN-ACTION: replace the placeholder rubric with Kaan's own wording |

*All BENCH code is offline-verified (fake client + fixture cells); the real run, Kaan's verdict, and the taste-rubric wording are parked KAAN-ACTION — never faked, never block the autonomous run.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
