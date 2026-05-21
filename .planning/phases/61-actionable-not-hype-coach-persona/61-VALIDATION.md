---
phase: 61
slug: actionable-not-hype-coach-persona
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-21
---

# Phase 61 — Validation Strategy

> Per-phase validation contract. Derived from 61-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (Python 3.12) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/state tests/prompts -x` |
| **Full suite command** | `PYTHONPATH=src .venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~60–240 seconds |

> NOTE: use `.venv/bin/python` — system python3.14 lacks livekit/google.genai (64 false collection errors).

---

## Sampling Rate

- **After every task commit:** quick command for the touched area.
- **After every plan wave:** full suite.
- **Before `/gsd:verify-work`:** full suite green.
- **Baseline invariant:** the 7 pre-existing `live-tuning-or-brain` failures stay at exactly 7 — no new failures. (Confirmed 2026-05-21: 7 failed / 4069 passed / 26 skipped; failures are `tests/scripts/test_cut_release_preflight.py` x2 + `tests/test_main_smoke.py` x1 — unrelated to coach/prompt code.)

---

## Anti-Slop / Grounding Guarantees (must be observably tested)

| Guarantee | Requirement | How it is proven |
|-----------|-------------|------------------|
| Prescriptive observed→impact→prescribe with DJ verbs (not narration) | COACH-01 | `test_prompt_61_coach_*` cell-contract asserts (verb vocab + prescribe "same line" clause) for all 3 coach skills; KEY_CLASH coach test asserts a DJ-verb move + both keys cited. |
| No new mode; both genai + OpenRouter paths | COACH-02 | `test_dispatch_61_coach_prompt_body_feeds_both_paths`: `_gen_cfg.system_instruction == _prompt_body` AND `_VALID_MODES == {"hype","coach"}` unchanged. |
| Hype regression-fenced (cannot cold-ify) | COACH-03 | Hype goldens (`test_matrix.py` HYPE_INTERMEDIATE byte-identity + hype anchors, `test_persona.py`, `test_hype_prompt_grounding.py`) held byte-stable; coach anchors updated in-lockstep (deliberate, hype frozen). |
| Every prescriptive note cited; warm + non-nagging | COACH-04 | Existence-only CitationLinter strips fabricated `[key:...]` (`test_coach_grounding_61_fabricated_key_strips`); positive-callout balance rule asserted per coach skill (`test_prompt_61_coach_*` balance); calm-only tag routing asserted; cooldown/pacing inherited (no new mechanism). |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 61-01-T1 | 61-01 | 1 | COACH-01, COACH-04 | Coach-cell contract (DJ verbs + prescribe-clause + balance + calm-tag) asserted for all 3 skills (RED spec) | unit | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/prompts/test_matrix.py -k 61_coach` | planned |
| 61-01-T2 | 61-01 | 1 | COACH-01, COACH-04 | KEY_CLASH/TRANSITION coach voice fenced (DJ-verb move + both keys cited + no-invent + past-tense) | unit | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/state/test_coach.py -k "key_clash or transition"` | planned |
| 61-01-T3 | 61-01 | 1 | COACH-02, COACH-04 | Dual-path `_prompt_body` equality + no-new-mode invariant; coach-context fabricated-key strip | integration | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/agent/test_dj_cohost_matrix_dispatch.py tests/agent/test_coach_prompt_grounding.py -k 61` | planned |
| 61-02-T1 | 61-02 | 2 | COACH-01, COACH-03, COACH-04 | COACH_PRO verb-list + COACH_INTERMEDIATE balance rule + same-line prescribe-clause + verbs; hype byte-stable | unit | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/prompts/test_matrix.py -k "61_coach or hype_intermediate or anchor"` | planned |
| 61-02-T2 | 61-02 | 2 | COACH-01, COACH-03, COACH-04 | COACH_BEGINNER impact clause + verb vocab + deck/harmonic path; lockstep anchors; hype + persona + harmonic green | unit | `PYTHONPATH=src .venv/bin/python -m pytest -q tests/prompts/test_matrix.py tests/state/test_coach.py tests/agent/test_persona.py tests/agent/test_hype_prompt_grounding.py` | planned |
