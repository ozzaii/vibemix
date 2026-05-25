---
phase: 78
slug: perceive-deeper-generalized-ear
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-26
planned: 2026-05-26
---

# Phase 78 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "perceive or trajectory or delta or genre or prototype or centering or coach or refresh or reconcile or normalize"` |
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

> Every PERCEIVE-0x requirement maps to an automated proof — €0, no API key. Genre prototypes from cached `library.db` vectors; deltas/trajectory from synthetic `MusicState` sequences. The "does it feel deeper" judgment is a Phase-81 BENCH + Kaan's-ear item (parked, never faked, never blocks).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 78-01-T1 | 01 | 1 | PERCEIVE-01/02 | unit (scaffold) | `pytest tests/state/test_coach_perceive.py tests/state/test_coach.py -q` | ⬜ pending |
| 78-01-T2 | 01 | 1 | PERCEIVE-01/02/03 | unit (scaffold) | `pytest tests/state/test_refresh_perceive.py tests/library/test_genre_prototypes.py -q` | ⬜ pending |
| 78-02-T1 | 02 | 2 | PERCEIVE-01 | unit (tdd) | `pytest tests/state/test_coach.py -q` + render_delta cold/abstain/rendered assertion | ⬜ pending |
| 78-02-T2 | 02 | 2 | PERCEIVE-01/02 | unit (tdd) | `pytest tests/state/test_coach_perceive.py tests/state/test_refresh_perceive.py tests/state/test_coach.py -q` + single-writer grep gate | ⬜ pending |
| 78-03-T1 | 03 | 2 | PERCEIVE-03 | unit (tdd) | `pytest tests/library/test_genre_prototypes.py -q` + no-duplicate-math grep gate | ⬜ pending |
| 78-03-T2 | 03 | 2 | PERCEIVE-03 | unit | `pytest tests/library/test_genre_prototypes.py -q` + no-MusicState-write + no-API grep gates | ⬜ pending |
| 78-04-T1 | 04 | 3 | PERCEIVE-03 | unit (tdd) | `pytest tests/state/ -k "reconcile or normalize" -q` + known-cosine→render-band pin (the flagged risk) | ⬜ pending |
| 78-04-T2 | 04 | 3 | PERCEIVE-03 | unit (tdd) | `pytest tests/state/test_refresh_perceive.py tests/state/test_coach.py -q` + single-writer grep gate | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test for PERCEIVE-01: evidence renders delta phrasing ("kick density rose 18%") from a prior→current `MusicState` pair; below-floor confidence → fact abstained/omitted. (Plan 01 Task 1 — xfail-strict scaffold; flips green in Plan 02 Task 2.)
- [ ] Test for PERCEIVE-02: a bounded multi-scale trajectory narrative (phrase / energy-arc / recent-moves) is composed in `refresh` and rendered in `coach`; window is bounded (no unbounded growth). (Plan 01 Tasks 1+2 — scaffold; flips green in Plan 02 Task 2.)
- [ ] Test for PERCEIVE-03: mean-centered nearest-prototype genre over cached `library.db` vectors writes `detected_genre`/`genre_confidence` via the single-writer refresh path; confidence-floored abstain; folder-label proxy. (Plan 01 Task 2 — scaffold; mechanism flips green in Plan 03, wiring in Plan 04 Task 2.)
- [ ] Test for the confidence-reconciliation gate (the flagged risk): embedding-genre vs DSP-genre disagreement resolves through one coherent `detected_genre` per tick, and a known centered cosine maps to an above/below `>= 0.5` render decision (pinning test). (Plan 01 Task 2 — scaffold; flips green in Plan 04 Tasks 1+2.)
- [ ] Cold-path byte-identity: signal below floor / trajectory cold → prompt byte-identical to v8.0 baseline (existing `test_coach.py` goldens stay green). (Plan 01 Task 1 — REAL GREEN pin now; held green by Plans 02 + 04.)

*Existing pytest infrastructure covers all phase requirements — no framework install needed. Wave 0 = Plan 01 (xfail-strict scaffolds + the cold-path byte-identity REAL GREEN pin).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Reactions feel measurably deeper / less snapshot-y in a real set | PERCEIVE-01/02 | Subjective "did it click" — Phase-16 rule | Phase-81 BENCH cells + KAAN-ACTION ear verdict; never auto-judged |
| Genre lookup accuracy on Kaan's real library beyond folder-label proxy | PERCEIVE-03 | 86.5% measured on in-corpus/folder labels (A1/A2 assumptions) | KAAN-ACTION: spot-check detected_genre vs perceived genre on a live set |

*All unit-level phase behaviors have automated verification (€0, no API); the felt-depth + real-library-accuracy judgments are parked for Kaan, never block.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (the 9 Wave-0-gap tests from RESEARCH → Plan 01 scaffolds)
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-signed 2026-05-26 (Phase 78). `wave_0_complete` flips true once Plan 01 lands.
