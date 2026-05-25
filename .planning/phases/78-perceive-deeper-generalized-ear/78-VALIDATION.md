---
phase: 78
slug: perceive-deeper-generalized-ear
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 78 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "perceive or trajectory or delta or genre or prototype or centering or coach or refresh"` |
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

> Populated by the planner. Every PERCEIVE-0x requirement maps to an automated proof — €0, no API key. Genre prototypes from cached `library.db` vectors; deltas/trajectory from synthetic `MusicState` sequences. The "does it feel deeper" judgment is a Phase-81 BENCH + Kaan's-ear item (parked, never faked, never blocks).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | — | 0 | PERCEIVE-01/02/03 | unit | Wave-0 test stubs | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test for PERCEIVE-01: evidence renders delta phrasing ("kick density rose 18%") from a prior→current `MusicState` pair; below-floor confidence → fact abstained/omitted.
- [ ] Test for PERCEIVE-02: a bounded multi-scale trajectory narrative (phrase / energy-arc / recent-moves) is composed in `refresh` and rendered in `coach`; window is bounded (no unbounded growth).
- [ ] Test for PERCEIVE-03: mean-centered nearest-prototype genre over cached `library.db` vectors writes `detected_genre`/`genre_confidence` via the single-writer refresh path; confidence-floored abstain; folder-label proxy.
- [ ] Test for the confidence-reconciliation gate (the flagged risk): embedding-genre vs DSP-genre disagreement resolves through one coherent `detected_genre` per tick (pinning test).
- [ ] Cold-path byte-identity: signal below floor / trajectory cold → prompt byte-identical to v8.0 baseline (existing `test_coach.py` goldens stay green).

*Existing pytest infrastructure covers all phase requirements — no framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Reactions feel measurably deeper / less snapshot-y in a real set | PERCEIVE-01/02 | Subjective "did it click" — Phase-16 rule | Phase-81 BENCH cells + KAAN-ACTION ear verdict; never auto-judged |
| Genre lookup accuracy on Kaan's real library beyond folder-label proxy | PERCEIVE-03 | 86.5% measured on in-corpus/folder labels (A1/A2 assumptions) | KAAN-ACTION: spot-check detected_genre vs perceived genre on a live set |

*All unit-level phase behaviors have automated verification (€0, no API); the felt-depth + real-library-accuracy judgments are parked for Kaan, never block.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
