---
phase: 102
slug: skill-tree-engine-data-model-competent-stage
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-29
---

# Phase 102 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Test surface is enumerated in `102-RESEARCH.md` § Validation Architecture; the per-task map below is filled.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q tests/learn/test_skill_tree.py tests/learn/test_skill_tree_invariants.py tests/learn/test_skill_tree_migration.py` |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q tests/learn` |
| **Estimated runtime** | ~3–8 seconds (pure-logic, no audio/API) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (new `tests/learn/test_skill_tree*.py`).
- **After every plan wave:** Run the full `tests/learn` suite (must stay green — disjoint from agent/ + tauri/ in-flight work).
- **Before `/gsd:verify-work`:** Full `tests/learn` suite green + full suite (`PYTHONPATH=src python3 -m pytest -q`) green for the SCHEMA_VERSION-bump cross-tree check.
- **Max feedback latency:** ~8 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| P02-01 schema v2 + migration | 102-01 | 1 | DATA-01, DATA-02 | unit | `PYTHONPATH=src python3 -m pytest -q tests/learn/test_skill_tree_migration.py` | ⬜ pending |
| P02-02 migration suite + guard rewrite + reset clear | 102-01 | 1 | DATA-02, DATA-03 | unit + cli | `PYTHONPATH=src python3 -m pytest -q tests/learn/test_skill_tree_migration.py tests/learn/test_progress_persistence.py` | ⬜ pending |
| P02-eng manifest + SkillProgress + compute + Competent gate | 102-02 | 2 | SKILL-01, SKILL-02, SKILL-03, COMP-01, COMP-02 | unit | `PYTHONPATH=src python3 -m pytest -q tests/learn/test_skill_tree.py` | ⬜ pending |
| P02-eng invariant pins (#1, #4, privacy) | 102-02 | 2 | SKILL-02, DATA-01 | static-grep | `PYTHONPATH=src python3 -m pytest -q tests/learn/test_skill_tree_invariants.py` | ⬜ pending |

### Headline anti-slop assertion (the product spine)
`tests/learn/test_skill_tree.py::test_full_clickthrough_without_recital_not_competent` — fill=1.0, gating recital flag False → `.competent is False` and `.stage == "locked"`.

### The 3 invariant pins
- `test_skill_tree_invariants.py::test_skill_tree_never_mutates_musicstate` (Invariant #1)
- `test_skill_tree_invariants.py::test_no_new_ws_port` (Invariant #4)
- `test_skill_tree_invariants.py::test_skills_never_in_profile_json` (privacy contract)

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/learn/test_skill_tree.py` — fill-math + Competent recital-gate + the headline `test_full_clickthrough_without_recital_not_competent` (COMP-01/02, SKILL-01/03) — written test-first in Plan 102-02
- [ ] `tests/learn/test_skill_tree_invariants.py` — `test_skill_tree_never_mutates_musicstate` (#1), `test_no_new_ws_port` (#4), `test_skills_never_in_profile_json` (privacy) (SKILL-02) — Plan 102-02
- [ ] `tests/learn/test_skill_tree_migration.py` — v1→v2 back-fill, idempotency, corrupt-recovery, reset (DATA-01/02/03) — Plan 102-01
- [ ] Existing `test_schema_version_mismatch_returns_fresh_empty` rewrite to v3 (SCHEMA_VERSION bump makes v2 a real version — RESEARCH finding #1; a rewrite, not a regression) — Plan 102-01

*Shared fixtures: monkeypatch `progress_path()` to a tmp dir (mandatory — never touch the real `learn-progress.json`), synthetic `LearnProgress` builders for first-try / with-strikes / recital-passed states.*

---

## Manual-Only Verifications

*None — Phase 102 is pure-logic and fully offline-unit-testable. No UI, no audio, no live hardware. (Live "Mastered" grounding ear-pass + FLX4 verify are Phase 103/104 KAAN-ACTION, not this phase.)*

---

## Validation Sign-Off

- [x] All tasks have automated verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 8s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
