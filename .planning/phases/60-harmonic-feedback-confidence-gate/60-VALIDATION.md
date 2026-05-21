---
phase: 60
slug: harmonic-feedback-confidence-gate
status: planned
nyquist_compliant: true
wave_0_complete: true
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
- **Baseline invariant:** the 7 pre-existing `live-tuning-or-brain` failures (Phase 59 `deferred-items.md`) stay at exactly 7 — no new failures introduced by any task.

---

## Anti-Slop / Grounding Guarantees (must be observably tested)

| Guarantee | Requirement | How it is proven |
|-----------|-------------|------------------|
| Deterministic Camelot table — LLM never computes; only narrates code-confirmed clash | HARMONIC-01 | Unit-table test over `is_clash`/`compatible` (Plan 01): same-letter hour-distance ∈ {5,6,7} → clash; {0,1,2} → safe; relative major/minor + perfect-fifth → safe. Coach fragment (Plan 04) cites both deck keys + forbids key math. |
| No clash on percussive/atonal or breakdown | HARMONIC-02 | Detector tests (Plan 02): two atonal/percussive tracks → no fire; breakdown/silent/low phase → no fire; clash fires ONLY with `audible_deck=="mix"` + both melodic + energy ≥ LOW_RMS + not vocal_active. |
| Conservative by default — adjacent/low-conf/ambiguous suppressed | HARMONIC-03 | Plan 02 tests: one-step-off-Camelot → no fire; deck < `DECK_CITE_MIN_CONF` → no fire (cross-deck); unresolved 2nd deck → no fire; detector default-OFF (`harmonic_clash_enabled=False`) until the Kaan-ear veto (Plan 03). |
| Uncited harmonic claim stripped | HARMONIC-01/03 | Linter test (Plan 04): a clash fragment citing a key the registry never observed strips the whole turn (existence-only, inherited from Phase 59). |
| Transition notes only when grounded; retrospective | HARMONIC-04 | Plan 04 tests: TRANSITION fragment is past-tense, no imperative verbs; no phrase/bass-swap guess when the signal is absent (Plan 02 fires it only on groundable retrospective conditions). |
| Kaan-ear veto gate | HARMONIC-03 | Disagreed-pairs corpus + parametrized test + runnable `eval/harmonic/run_veto.py` (Plan 03); detector stays gated until Kaan confirms zero false clash on pairs he'd happily mix (KAAN-ACTION). |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 60-01-T1 | 01 | 1 | HARMONIC-01 | Predicate table-oracle (RED) | unit | `PYTHONPATH=src python3 -m pytest -q tests/state/test_harmonics.py` | planned |
| 60-01-T2 | 01 | 1 | HARMONIC-01 | is_clash/compatible/semitone_distance deterministic, never raise (GREEN) | unit | `PYTHONPATH=src python3 -m pytest -q tests/state/test_harmonics.py` | planned |
| 60-02-T1 | 02 | 2 | HARMONIC-02/03 | Suppression + cross-deck + default-off detector tests | unit | `PYTHONPATH=src python3 -m pytest -q tests/state/test_event_detector_harmonic.py` | planned |
| 60-02-T2 | 02 | 2 | HARMONIC-02/03 | `_melodic_overlap_gate` + KEY_CLASH/TRANSITION branches + flag (T-60-01/02/03) | unit | `PYTHONPATH=src python3 -m pytest -q tests/state/test_event_detector_harmonic.py` | planned |
| 60-03-T1 | 03 | 2 | HARMONIC-03 | Disagreed-pairs corpus never flags; true clashes flag | unit | `PYTHONPATH=src python3 -m pytest -q tests/state/test_kaan_ear_veto.py` | planned |
| 60-03-T2 | 03 | 2 | HARMONIC-03 | Runnable veto scorer; KAAN-ACTION ship gate exit code | cli | `PYTHONPATH=src python3 eval/harmonic/run_veto.py` | planned |
| 60-04-T1 | 04 | 3 | HARMONIC-01/04 | Cited narration + retrospective + uncited-strip tests (RED) | unit | `PYTHONPATH=src python3 -m pytest -q tests/state/test_coach_harmonic.py` | planned |
| 60-04-T2 | 04 | 3 | HARMONIC-01/04 | Real cited coach arms; grammar reconciled; goldens held (T-60-04/05/06) | unit+golden | `PYTHONPATH=src python3 -m pytest -q tests/state/test_coach_harmonic.py tests/state/test_coach_prompt_grounding.py tests/state/test_coach_prompt_diet.py` | planned |
