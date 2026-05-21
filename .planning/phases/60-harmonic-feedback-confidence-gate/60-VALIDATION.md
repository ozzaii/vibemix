---
phase: 60
slug: harmonic-feedback-confidence-gate
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-21
---

# Phase 60 — Validation Strategy

> Per-phase validation contract. Derived from 60-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python 3.12) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q tests/state -x` |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~60–120 seconds |

---

## Sampling Rate

- **After every task commit:** quick command for the touched area.
- **After every plan wave:** full suite.
- **Before `/gsd:verify-work`:** full suite green.
- **Max feedback latency:** ~120 seconds.

---

## Anti-Slop / Grounding Guarantees (must be observably tested)

| Guarantee | Requirement | How it is proven |
|-----------|-------------|------------------|
| Deterministic Camelot table — LLM never computes; only narrates code-confirmed clash | HARMONIC-01 | Unit-table test over `is_clash`/`compatible`: same-letter hour-distance ∈ {5,6,7} → clash; {0,1,2} → safe; relative major/minor + perfect-fifth → safe. Both deck keys cited in the fragment. |
| No clash on percussive/atonal or breakdown | HARMONIC-02 | Detector test: two atonal/percussive tracks → no fire; breakdown phase → no fire; clash fires ONLY with `audible_deck=="mix"` + both melodic + energy ≥ floor. |
| Conservative by default — adjacent/low-conf/ambiguous suppressed | HARMONIC-03 | Test: one-step-off-Camelot → no fire; deck below `DECK_CITE_MIN_CONF` → uncitable → stripped; unresolved 2nd deck → no fire. Detector default-OFF (`harmonic_clash_enabled=False`) until Kaan-ear veto. |
| Uncited harmonic claim stripped | HARMONIC-01/03 | Linter test: a clash fragment citing a key the registry never observed is stripped (existence-only, inherited from Phase 59). |
| Transition notes only when grounded; retrospective | HARMONIC-04 | Test: no phrase-alignment note when no phrase grid signal; notes are past-tense; no advice when signals absent. |
| Kaan-ear veto gate | HARMONIC-03 | Disagreed-pairs corpus + runnable check; detector stays gated until Kaan confirms zero false clash on pairs he'd happily mix (KAAN-ACTION). |

---

## Per-Task Verification Map

> Populated by the planner.

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| _TBD by planner_ | | | | | | | |
