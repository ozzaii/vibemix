---
phase: 66
slug: visible-copilot-move
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-22
updated: 2026-05-22
---

# Phase 66 — Validation Strategy

> Per-phase validation contract. Source: `66-RESEARCH.md` §Validation Architecture +
> `66-01-PLAN.md` / `66-02-PLAN.md` `<verify>` blocks. This is the visible-copilot
> phase on top of the Phase 65 anti-slop release gate — the RED-first contract
> pins 9 new tests + 1 negative-control stripper test BEFORE any source edit.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (dev dep) + pytest-mock (existing in `pyproject.toml`) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]`; `--strict-markers` |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_linter.py tests/state/test_coach.py tests/repo/test_no_recall_antifeatures.py -q` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |
| **Estimated runtime** | ~5s targeted; full suite ~30s |

---

## Sampling Rate

- **After every task commit:** `PYTHONPATH=src python3 -m pytest -q tests/agent/test_citation_strip_emit.py tests/state/test_coach.py tests/agent/test_dj_cohost_linter.py tests/repo/test_no_recall_antifeatures.py`
- **After every plan wave:** + `tests/coach/test_citation_linter.py` + `tests/memory/test_retrieval.py` + `tests/state/test_evidence_registry.py` + `tests/prompts/test_matrix.py` (covers the Phase 65 regression surface)
- **Before `/gsd:verify-work`:** full suite green at the documented 8-failure `live-tuning-or-brain` baseline (zero NEW failures); the v5.0 byte-identity goldens MUST stay green
- **Max feedback latency:** < 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 66-01-01 | 01 | 0 | COPILOT-01, COPILOT-02 | T-66-01-02, T-66-01-03 | RED contract: chip + fragment + byte-identity tests collect cleanly and FAIL for the right structural reason (missing allow-list / missing helper symbol) | unit | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/agent/test_citation_strip_emit.py tests/state/test_coach.py -q --no-header` | ❌ W0 — 7 new tests added | ⬜ pending |
| 66-01-02 | 01 | 0 | COPILOT-02, COPILOT-03 | T-66-01-01 | RED contract: cooldown tests fail with ImportError on `RECALL_CALLBACK_COOLDOWN_S`; NEW `tests/repo/test_no_recall_antifeatures.py` collects cleanly; negative-control stripper test PASSES; main scan PASSES (vacuous — pre-grep of TARGET_FILES confirms zero forbidden phrases today) | unit + static-gate | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/agent/test_dj_cohost_linter.py tests/repo/test_no_recall_antifeatures.py -q --no-header` | ❌ W0 — 2 new cooldown tests + 1 NEW file | ⬜ pending |
| 66-02-01 | 02 | 1 | COPILOT-01, COPILOT-02 | T-66-02-01, T-66-02-02, T-66-02-03, T-66-02-05, T-66-02-06 | GREEN: `recall` in chip allow-list at `_build_citation_strip:215`; fixed-verb `"recall"` branch; `RECALL_CALLBACK_COOLDOWN_S=120.0` at module scope; `self._last_recall_callback_at` field; cooldown gate in llm_node; cooldown ARM in `else:` branch on bus-emit success (strict "REACHED the audience" semantic per CONTEXT.md Area 1 Q3 + RESEARCH §Pitfall 2 + §Open Q5) | unit + integration | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_linter.py -q --no-header` | ✅ exists | ⬜ pending |
| 66-02-02 | 02 | 1 | COPILOT-01, COPILOT-02, COPILOT-03 | T-66-02-04 | GREEN: TRANSITION_SHAPE_RECALL_FRAGMENT_TPL + VOCABULARY_RECALL_FRAGMENT_TPL at module scope; `recall_fragment_for_event(ev, recall_moments)` with falsy gate + TRACK_CHANGE/MIX_MOVE/LAYER_ARRIVAL → transition / PHASE → vocabulary; `build_prompt` appends fragment in non-diet path only | unit | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/state/test_coach.py tests/repo/test_no_recall_antifeatures.py -q --no-header` | ✅ exists | ⬜ pending |
| 66-02-03 | 02 | 1 | COPILOT-01, COPILOT-02, COPILOT-03 | — | Documentation tier: `66-HUMAN-UAT.md` scaffold + `KAAN-ACTION-LEGAL.md` §RECALL-EAR entry land per the Phase 60 / Phase 65 KAAN-ACTION carry-forward precedent | manual review | `ls .planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md && grep -n "§RECALL-EAR" KAAN-ACTION-LEGAL.md` | ❌ Wave 1 — NEW file + APPEND | ⬜ pending |
| 66-W1-FULL | 02 | 1 | (all) | (all) | Full-suite regression: zero NEW failures vs documented 8-WIP `live-tuning-or-brain` baseline; all Phase 65 floor goldens stay GREEN | full-suite | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q 2>&1 \| tail -15` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COPILOT-01 | Grounded `[recall:<id>]` citation in a reaction yields a chip with verb="recall", source-routed via allow-list at `dj_cohost.py:215` | unit | `pytest tests/agent/test_citation_strip_emit.py::test_recall_citation_yields_chip_with_registry_timestamp_COPILOT01 -x` | ❌ W0 |
| COPILOT-01 | Fabricated `[recall:<id>]` yields NO chip (mirrors Phase 65 turn-strip; the chip CANNOT surface because the whole turn strips upstream) | unit | `pytest tests/agent/test_citation_strip_emit.py::test_fabricated_recall_yields_no_chip_COPILOT01 -x` | ❌ W0 |
| COPILOT-01 | TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL with non-empty `recall_moments` → transition-shape fragment is appended to `build_prompt` output | unit | `pytest tests/state/test_coach.py::test_transition_recall_fragment_appears -x` | ❌ W0 |
| COPILOT-01 | Empty `recall_moments` → fragment NOT appended → byte-identical to v5.0 baseline (load-bearing regression floor) | unit | `pytest tests/state/test_coach.py::test_task_for_event_byte_identical_v5_baseline_no_recall -x` | ❌ W0 |
| COPILOT-02 | PHASE event with non-empty `recall_moments` → vocabulary fragment is appended | unit | `pytest tests/state/test_coach.py::test_vocabulary_recall_fragment_appears -x` | ❌ W0 |
| COPILOT-02 | Two back-to-back recall-eligible turns within 120s → only the first emits a chip (cooldown active for the second) | integration | `pytest tests/agent/test_dj_cohost_linter.py::test_cooldown_suppresses_back_to_back_recalls_COPILOT02 -x` | ❌ W0 |
| COPILOT-02 | Single turn with multiple survivors → ONLY the strongest survivor's `record_id` is interpolated into the fragment (structural max-1-per-turn property) | unit | `pytest tests/state/test_coach.py::test_only_strongest_survivor_record_id_in_fragment -x` | ❌ W0 |
| COPILOT-02 | TRACK_CHANGE overlap: transition WINS over vocabulary (§Pitfall 5 + §Open Q1 lock) | unit | `pytest tests/state/test_coach.py::test_transition_wins_track_change_overlap -x` | ❌ W0 |
| COPILOT-02 | Single turn with 3 survivors → at most ONE `[recall:<id>]` token in the built prompt | integration | `pytest tests/agent/test_dj_cohost_linter.py::test_max_one_recall_per_turn_COPILOT02 -x` | ❌ W0 |
| COPILOT-03 | No forbidden anti-feature phrases ("you tend to", "you usually", "next track", "you should play", etc.) reach the coach/prompt surface | static-gate | `pytest tests/repo/test_no_recall_antifeatures.py::test_no_recall_antifeatures_in_coach_surface_COPILOT03 -x` | ❌ W0 (NEW file) |
| COPILOT-03 | Negative-control: the tokenize-stripper correctly removes string contents + docstrings (proves the gate's stripping mechanism, not vacuity) | unit | `pytest tests/repo/test_no_recall_antifeatures.py::test_strip_comments_and_docstrings_removes_string_content -x` | ❌ W0 (NEW file) |

---

## Wave 0 Requirements

- [ ] `tests/agent/test_citation_strip_emit.py` — APPEND 2 new tests (`test_recall_citation_yields_chip_with_registry_timestamp_COPILOT01` + `test_fabricated_recall_yields_no_chip_COPILOT01`) after line 203, mirroring the `key` precedent at :164-203
- [ ] `tests/state/test_coach.py` — APPEND 5 new tests under new section header `# ---- Phase 66 — recall_fragment_for_event tests (COPILOT-01/02) ----` (fragment appearance × 2, byte-identity baseline, strongest-survivor only, TRACK_CHANGE overlap resolution)
- [ ] `tests/agent/test_dj_cohost_linter.py` — APPEND 2 new cooldown tests (per-test-body import of `RECALL_CALLBACK_COOLDOWN_S` with pytest.fail-on-ImportError; do NOT add a top-of-file import that would break collection)
- [ ] `tests/repo/test_no_recall_antifeatures.py` — CREATE new file mirroring `tests/memory/test_no_extraction.py` (clone `_strip_comments_and_docstrings` verbatim with lock-step comment; FORBIDDEN_RECALL_PHRASES + TARGET_FILES = (state/coach.py, prompts/matrix.py); main scan + negative-control stripper test)
- [ ] Framework install: none (pytest + pytest-mock already in `pyproject.toml`)

**Pre-grep evidence (executed during planning, 2026-05-22):** `grep -nE "you tend to|you usually|you always|next track|you should play|your tendency|based on your past|I recommend|my recommendation|you should try" src/vibemix/state/coach.py src/vibemix/prompts/matrix.py` returns **zero hits**. The static-gate main scan is therefore vacuous-green at Plan 02 land; any future hit is a finding to surface, NOT a runtime carve-out.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live transition-shape callback feels grounded (compares NOW to THEN, not scripted) | COPILOT-01 | Subjective tone judgment on real session corpus | **KAAN-ACTION (veto)** — mirrors Phase 65 §RECALL + Phase 60 §HARMONIC-VETO; flip `VIBEMIX_RECALL_ENABLED=1` and run a live set. See `66-HUMAN-UAT.md` Test 1. |
| Live vocabulary callback echoes Kaan's prior phrasing in HIS voice (not Gemini-paraphrased — §Pitfall 4) | COPILOT-02 | Voice/register subjective; requires a real session with prior phrasing in the survivor list | **KAAN-ACTION** — `66-HUMAN-UAT.md` Test 2. |
| Cooldown verified by ear (no more than ~1 recall callback per ~2 minutes; never two in succession) | COPILOT-02 | Multi-turn pacing requires a live session, not a unit test | **KAAN-ACTION** — `66-HUMAN-UAT.md` Test 3. The 120s gate has a unit test; the *felt* rhythm is the ear-pass. |
| Anti-feature absence by ear (no "you tend to" / "next track" / "you usually" in Gemini's actual emitted reactions even if static gate is green) | COPILOT-03 | The static gate scans SOURCE; the ear catches Gemini drift at runtime | **KAAN-ACTION** — `66-HUMAN-UAT.md` Test 4. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (9 new tests + 1 negative-control across 4 files)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter
- [x] Pre-grep evidence recorded for static-gate vacuous-green declaration

**Approval:** approved 2026-05-22 (autonomous `fully` — Nyquist map from research; cooldown-arm at emit-success per CONTEXT.md Area 1 Q3 + RESEARCH §Pitfall 2 + §Open Q5; live relevance/TTFT parked as KAAN-ACTION veto via §RECALL-EAR)
