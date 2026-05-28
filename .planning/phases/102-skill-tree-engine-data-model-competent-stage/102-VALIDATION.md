---
phase: 102
slug: skill-tree-engine-data-model-competent-stage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-29
---

# Phase 102 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Test surface is enumerated in `102-RESEARCH.md` § Validation Architecture; the per-task map below is filled during planning/execution.

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
- **Before `/gsd:verify-work`:** Full `tests/learn` suite green.
- **Max feedback latency:** ~8 seconds.

---

## Per-Task Verification Map

*Filled during planning — every task maps to a named `tests/learn/test_skill_tree*` case per `102-RESEARCH.md` § Validation Architecture. Coverage targets: SKILL-01/02/03, COMP-01/02, DATA-01/02/03 + the 3 invariant pins + the headline anti-slop assertion.*

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| _(planner-filled)_ | | | | unit | `PYTHONPATH=src python3 -m pytest -q tests/learn/test_skill_tree*.py` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/learn/test_skill_tree.py` — fill-math + Competent recital-gate + the headline `test_full_clickthrough_without_recital_not_competent` (COMP-01/02, SKILL-01/03)
- [ ] `tests/learn/test_skill_tree_invariants.py` — AST/static gates: `test_skill_tree_never_mutates_musicstate` (#1), `test_no_new_ws_port` (#4), `test_skills_never_in_profile_json` (privacy contract) (SKILL-02)
- [ ] `tests/learn/test_skill_tree_migration.py` — v1→v2 deterministic back-fill, idempotency, corrupt-read recovery seeds empty v2 skills block, reset path (DATA-01/02/03)
- [ ] Existing `test_schema_version_mismatch_returns_fresh_empty` rewrite (SCHEMA_VERSION bump makes v2 a real version — per RESEARCH finding, this is a rewrite not a regression)

*Shared fixtures: monkeypatch `progress_path()` to a tmp dir (mandatory — never touch the real `learn-progress.json`), synthetic `LearnProgress` builders for first-try / with-strikes / recital-passed states.*

---

## Manual-Only Verifications

*None — Phase 102 is pure-logic and fully offline-unit-testable. No UI, no audio, no live hardware. (Live "Mastered" grounding ear-pass + FLX4 verify are Phase 103/104 KAAN-ACTION, not this phase.)*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 8s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
