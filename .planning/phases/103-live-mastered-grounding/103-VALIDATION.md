---
phase: 103
slug: live-mastered-grounding
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-29
---

# Phase 103 — Validation Strategy

> Per-phase validation contract. Test surface enumerated in `103-RESEARCH.md` § Validation Architecture. Engine-level, fully offline (synthetic cited/un-cited event streams) — no live hardware (that's the deferred `§EARNED-LIVE-MASTERED-VERIFY` KAAN-ACTION).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/learn/test_skill_recognizer.py tests/learn/test_skill_tree.py` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/learn` |
| **Estimated runtime** | ~4–9 seconds (pure-logic, synthetic events, no audio/API/hardware) |

---

## Sampling Rate

- **After every task commit:** quick run command.
- **After every plan wave:** full `tests/learn` (disjoint from concurrent agent/state/tauri in-flight work).
- **Before verify:** full `tests/learn` green.
- **Max feedback latency:** ~9 seconds.

---

## Per-Task Verification Map

*Filled by planner. Coverage: MAST-01/02/03/04 + the 3 headline assertions. The live-firing call-site is OUT of this phase (deferred KAAN-ACTION); everything here is offline-verifiable with synthetic events.*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| _(planner-filled)_ | | | MAST-01..04 | unit | `pytest -q tests/learn/test_skill_recognizer.py` | ⬜ pending |

### Headline anti-slop assertions (the phase spine)
- `test_uncited_event_grants_zero_mastery_credit` — a fabricated/un-cited event MUST NOT advance Mastered (MAST-03, Invariants #2+#3).
- `test_live_demo_noop_when_not_competent` — a not-yet-Competent skill ignores all live events (MAST-01).
- `test_first_mastered_at_idempotent` — `first_mastered_at` stamped exactly once; later demos never overwrite (MAST-04).
- `test_unsignalled_skills_never_auto_master` — `beatmatching` + `harmonic_mixing` never reach Mastered from any event in v11.0 (no proxy-slop; honest uncreditable).

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/learn/test_skill_recognizer.py` — reverse event→skill map (4 creditable skills via real event constants), citation-required credit, dedup, the 2 unsignalled-skills guard (MAST-02/03)
- [ ] extend `tests/learn/test_skill_tree.py` — `record_live_demo` count increment, N-threshold Mastered flip, locked-until-Competent no-op, first_mastered_at idempotency (MAST-01/04)

*Shared fixtures: monkeypatch `progress_path()` to tmp; synthetic event objects + a synthetic citation predicate (cited=lambda→True, uncited=lambda→False) so the engine is exercised without live `state/`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real live event actually advances Mastered in a played set | MAST-02 (live firing) | The live-firing call-site lives in `runtime/coach.py`/`__main__.py` (concurrent session's island — out of P103 scope) | `§EARNED-LIVE-MASTERED-VERIFY` KAAN-ACTION: once the learn↔coach wiring lands, play a set on the FLX4 and confirm a cited MIX_MOVE advances eq_mixing toward Mastered |

*The ENGINE (recognizer + record_live_demo + map) is fully automated offline; only the real-hardware live firing is deferred.*

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity OK
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 9s
- [x] `nyquist_compliant: true`

**Approval:** planned
