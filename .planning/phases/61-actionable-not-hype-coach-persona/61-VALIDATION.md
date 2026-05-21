---
phase: 61
slug: actionable-not-hype-coach-persona
status: draft
nyquist_compliant: false
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
- **Baseline invariant:** the 7 pre-existing `live-tuning-or-brain` failures stay at exactly 7 — no new failures.

---

## Anti-Slop / Grounding Guarantees (must be observably tested)

| Guarantee | Requirement | How it is proven |
|-----------|-------------|------------------|
| Prescriptive observed→impact→prescribe with DJ verbs (not narration) | COACH-01 | Cell-anchor tests: COACH_BEGINNER/INTERMEDIATE/PRO carry impact clause + DJ-verb vocabulary (kill/swap/cut/filter/wait/tighten); audited gaps closed. |
| No new mode; both genai + OpenRouter paths | COACH-02 | `_VALID_MODES == {"hype","coach"}` unchanged; dual-path assertion that the one `_prompt_body` feeds both `generate_content_stream` and the OpenRouter stream. |
| Hype regression-fenced (cannot cold-ify) | COACH-03 | Hype goldens (`test_matrix.py` HYPE_INTERMEDIATE byte-identity + hype anchors, `test_persona.py`, `test_hype_prompt_grounding.py`) held byte-stable; coach anchors updated in-lockstep (deliberate, hype frozen). |
| Every prescriptive note cited; warm + non-nagging | COACH-04 | Existence-only CitationLinter strips fabricated `[key:...]` (inherited); cooldown/pacing test; over-correction guard (positive-callout balance present). |

---

## Per-Task Verification Map

> Populated by the planner.

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| _TBD by planner_ | | | | | | | |
