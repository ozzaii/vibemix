---
phase: 65
slug: memory-retrieval-seam
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-22
---

# Phase 65 — Validation Strategy

> Per-phase validation contract. Source: `65-RESEARCH.md` §Validation Architecture. This is the milestone's anti-slop release gate — the fabricated-`[recall:]`-strips-turn poisoning test is the headline RED.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (dev dep) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`; `--strict-markers` |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/memory tests/state/test_coach.py tests/agent/test_dj_cohost_linter.py` |
| **Full suite command** | `PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |
| **Estimated runtime** | ~sub-second targeted; full suite as baseline |

---

## Sampling Rate

- **After every task commit:** `PYTHONPATH=src python3 -m pytest -q tests/memory tests/state/test_coach.py`
- **After every plan wave:** + `tests/agent/test_dj_cohost_linter.py` + `tests/prompts/test_matrix.py` + `tests/state/test_evidence_registry.py` + the two memory gates
- **Before `/gsd:verify-work`:** full suite green at the 8-failure `live-tuning-or-brain` baseline (zero NEW failures); the byte-identical-cold golden MUST stay green
- **Max feedback latency:** < 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 65-W0 | W0 | 0 | RECALL-01..04 | — | N/A (test fences) | unit | `pytest -q tests/memory/test_retrieval.py` | ❌ W0 | ⬜ pending |
| RECALL-02a | — | 1 | RECALL-02 | — | byte-identical cold golden (recall=None == v5.0 silent string) | unit (golden) | `pytest tests/state/test_coach.py::test_evidence_line_silent_state_full_format -x` | ✅ MUST stay green | ⬜ pending |
| RECALL-02b | — | 2 | RECALL-02 | — | populated → past-tense fence + `[recall:<id>]` tokens | unit (golden) | `pytest tests/state/test_coach.py::test_evidence_line_recall_block_present -x` | ❌ W0 | ⬜ pending |
| RECALL-02c | — | 2 | RECALL-02 | — | empty/below-floor → no block (gate falsy on `[]`) | unit | `pytest tests/state/test_coach.py::test_evidence_line_recall_empty_no_block -x` | ❌ W0 | ⬜ pending |
| RECALL-01a | — | 1 | RECALL-01 | T-poison | `EVIDENCE_SOURCES` includes `recall` (count 8→9) | unit | `pytest tests/state/test_evidence_registry.py -k sources_constant -x` | ✅ UPDATE 8→9 | ⬜ pending |
| RECALL-01b | — | 1 | RECALL-01 | T-poison | `recall` matchable (regex `_SOURCE_ALT`) + writable (registry coherence) | unit | `pytest tests/state/test_evidence_registry.py -k grammar_coherence -x` | ✅ auto-iterates | ⬜ pending |
| RECALL-01c | — | 1 | RECALL-01 | T-poison | grammar block lists `[recall:` form (8→9 forms) | unit | `pytest tests/prompts/test_matrix.py -k citation_grammar_block -x` | ✅ UPDATE 8→9 | ⬜ pending |
| RECALL-01d | — | 2 | RECALL-01 | **T-poison (headline)** | **fabricated `[recall:<unregistered>]` strips the whole turn** | unit | `pytest tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn -x` | ❌ W0 | ⬜ pending |
| RECALL-01e | — | 2 | RECALL-01 | — | registered `[recall:<id>]` passes the linter | unit | `pytest tests/coach/test_citation_linter.py::test_recall_existence_only_valid -x` | ❌ W0 | ⬜ pending |
| RECALL-03a | — | 2 | RECALL-03 | T-poison | below-floor → survivors `[]` → no block | unit | `pytest tests/memory/test_retrieval.py::test_below_floor_injects_nothing -x` | ❌ W0 | ⬜ pending |
| RECALL-03b | — | 2 | RECALL-03 | T-poison | current_session_id excluded from its own retrieval | unit | `pytest tests/memory/test_retrieval.py::test_current_session_excluded -x` | ❌ W0 | ⬜ pending |
| RECALL-04a | — | 2 | RECALL-04 | — | HEARTBEAT (non-track-aware) → `on_event` `[]`, no embed call | unit | `pytest tests/memory/test_retrieval.py::test_heartbeat_never_retrieves -x` | ❌ W0 | ⬜ pending |
| RECALL-04b | — | 2 | RECALL-04 | — | **TTFT-unchanged** — retrieve off-loop; deadline-miss → `[]`, no inline `await embed_query` in llm_node | unit + static | `pytest tests/memory/test_retrieval.py::test_deadline_miss_injects_nothing -x` | ❌ W0 | ⬜ pending |
| RECALL-04c | — | 2 | RECALL-04 | T-livepath | `memory/retrieval.py` imports no live-reaction-path module | unit (static+subproc) | `pytest tests/memory/test_no_live_path_import.py -x` | ✅ globs memory/*.py | ⬜ pending |
| RECALL-04d | — | 2 | RECALL-04 | T-confab | `memory/retrieval.py` calls only `embed_query` (no generation) | unit (static) | `pytest tests/memory/test_no_extraction.py -x` | ✅ globs memory/*.py | ⬜ pending |
| RECALL-x | — | 2 | (cross) | T-confab | no hardcoded model literal in retrieval.py | unit (shipped) | `pytest tests/repo/test_model_literal_gate.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/memory/test_retrieval.py` — event-gate (HEARTBEAT→[]), below-floor→[], current-session-excluded, deadline-miss→[], embed-called-once
- [ ] `tests/state/test_coach.py` — add `test_evidence_line_recall_block_present` (populated; past-tense fence; tokens) + `test_evidence_line_recall_empty_no_block`; **confirm the existing silent-state golden stays green with the default `recall_moments=None` kwarg**
- [ ] `tests/agent/test_dj_cohost_linter.py` — `test_fabricated_recall_strips_turn` (the poisoning gate; the headline RED)
- [ ] `tests/coach/test_citation_linter.py` — `test_recall_existence_only_valid` (registered recall passes)
- [ ] **UPDATE** `tests/state/test_evidence_registry.py` sources-count test (8→9) + `tests/prompts/test_matrix.py` grammar-forms test (8→9 + `[recall:`)
- [ ] Verify shipped `tests/memory/test_no_extraction.py` / `test_no_live_path_import.py` actively cover the new `retrieval.py` (glob `memory/*.py`)
- Framework install: none

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live retrieval relevance — a recalled moment Kaan's ear says actually mattered, not a false-positive callback | RECALL-03/04 | Subjective relevance on real session corpus; the hard quality gate | **KAAN-ACTION (veto)** — mirrors the Phase 60 harmonic veto; ships behind a flag. Threshold (0.7) + cosine-vs-time blend/half-life tuned here. NOT an engineering blocker. |
| TTFT p95 unchanged feature-on vs feature-off on a real session | RECALL-04 | Requires a live recorded session + real embed latency | **KAAN-ACTION** — unit test asserts off-loop + deadline-miss-injects-nothing; live p95 confirmed on the live-ear pass. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (incl. the 4 schema-mirror updates)
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-22 (autonomous `fully` — Nyquist map from research; cosine-only conservative default; threshold/blend tuning + live relevance/TTFT parked as KAAN-ACTION veto)
