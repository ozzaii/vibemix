---
phase: 66-visible-copilot-move
plan: 01
subsystem: tests (agent / state / repo static-gate)
tags: [phase-66, copilot, recall, anti-slop, citation-strip, prompt-fragment, cooldown, static-gate, wave-0, red-first]

# Dependency graph
requires:
  - phase: 65-memory-retrieval-seam (Plan 04)
    provides: "Live-path wiring + gated PAST-TENSE recall block + anti-poisoning gate (4/4 RECALL-01..04 closed)"
provides:
  - "Wave 0 RED contract — 9 new tests + 1 negative-control stripper test pinning the COPILOT-01/02/03 surface BEFORE any source edit"
  - "Substring-uniqueness locks on the transition + vocabulary fragment templates ('in the live audio' / 'echo your own past words')"
  - "Pre-grep vacuous-green declaration for the anti-feature static gate (TARGET_FILES = state/coach.py + prompts/matrix.py, zero forbidden phrases)"
affects: [66-02-PLAN.md (Wave 1 GREEN implementation)]

# Tech tracking
tech-stack:
  added: []  # pure test-only phase — zero net-new deps
  patterns:
    - "Per-test-body import wrapped in pytest.fail-on-ImportError — keeps file collection clean while the symbol does not yet exist"
    - "Substring-uniqueness lock on fragment templates — pre-grep evidence recorded in module comment + the RED test pins the substring"
    - "Negative-control stripper test substituting the memory-gate's positive-control (Phase 66 forbidden phrases are HUMAN ENGLISH PROSE — no NAME-token form possible, so vacuity-broken protection is the stripper-correctness assertion)"
    - "Vacuous-green declaration for anti-feature static gates — pre-grep evidence recorded in 66-VALIDATION.md + module docstring; future hit must surface a finding (no runtime carve-outs)"

key-files:
  created:
    - "tests/repo/test_no_recall_antifeatures.py — NEW static-gate file (267 lines: FORBIDDEN_RECALL_PHRASES + TARGET_FILES + _strip_comments_and_docstrings verbatim clone + negative-control stripper test + main scan)"
  modified:
    - "tests/agent/test_citation_strip_emit.py — +97 lines, 2 new recall-chip tests cloning the test_key_citation_*_DECK03 precedent"
    - "tests/state/test_coach.py — +303 lines, 5 new tests under '# ---- Phase 66 — recall_fragment_for_event tests (COPILOT-01/02) ----' section header"
    - "tests/agent/test_dj_cohost_linter.py — +260 lines, 2 new cooldown tests under '# ---- Phase 66 — coach-tier cooldown tests (COPILOT-02) ----' section header"

key-decisions:
  - "Per-test-body imports for recall_fragment_for_event AND RECALL_CALLBACK_COOLDOWN_S — wrapped in pytest.fail-on-ImportError so file collection stays clean. NO top-of-file import that would break sibling tests."
  - "Substring-uniqueness check executed BEFORE committing: grep -F 'in the live audio' src/vibemix/state/coach.py src/vibemix/prompts/matrix.py → zero hits; same for 'echo your own past words'. Evidence recorded in tests/state/test_coach.py module comment."
  - "Phase 66 static-gate divergence from memory-gate template: positive-control replaced with NEGATIVE-CONTROL stripper test because Phase 66 forbidden phrases (human English prose with spaces) cannot exist as NAME-token sequences in Python source (multi-word identifiers are syntactically forbidden). Documented in the new file's module docstring."
  - "Stripped source .lower()-ed before substring-matching against FORBIDDEN_RECALL_PHRASES (case-insensitive English prose vs the memory-gate's case-sensitive Python identifiers) — also documented as the second divergence."
  - "Static-gate main scan declared VACUOUS-GREEN at land per the pre-grep evidence (executed 2026-05-22 during planning, re-verified at commit time — zero hits in TARGET_FILES). Re-verified again here."
  - "The 'test_fabricated_recall_yields_no_chip_COPILOT01' test is GREEN today via allow-list exclusion + GREEN after Plan 02 via registry-existence check — same final state, different enforcement path. Documented in test docstring; pins the contract regardless of which path enforces it."

# Metrics
duration: ~25min
completed: 2026-05-22
---

# Phase 66 Plan 01: Visible Copilot Move — Wave 0 RED Contract Summary

**9 new RED tests + 1 negative-control stripper test land across 4 files (3 modified + 1 created), pinning the COPILOT-01/02/03 surface BEFORE any source edit. Every RED test fails for the right structural reason (missing allow-list entry / missing helper symbol / missing cooldown constant / missing static-gate file). The cold-memory v5.0 byte-identity goldens stay GREEN (the load-bearing regression floor); existing Phase 65 anti-poisoning gates stay GREEN; the new static-gate's negative-control stripper test PASSES (vacuity-broken protection); the main static scan PASSES vacuously per the pre-grep evidence. Zero NEW failures vs the documented 8-WIP live-tuning-or-brain baseline.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-05-22
- **Tasks:** 2 (1 chip+fragment+byte-identity RED contract + 1 cooldown RED contract + new static-gate file with negative-control)
- **Files modified/created:** 4 (3 modified + 1 new)

## The 9 New Tests + 1 Negative-Control Stripper Test

### tests/agent/test_citation_strip_emit.py — 2 new tests (appended after :203)

1. **`test_recall_citation_yields_chip_with_registry_timestamp_COPILOT01`** — RED today. Pins the grounded recall chip contract (allow-list at dj_cohost.py:215 + fixed `"recall"` verb + registry-write timestamp). Fails because `recall` is excluded from the allow-list tuple → `continue` at :216 → `strip == []`. Anti-hallucination invariant: `timestamp_s` MUST come from the registry write (current turn's `t_session`), not a past Record's `.ts` (Pitfall 3).
2. **`test_fabricated_recall_yields_no_chip_COPILOT01`** — GREEN today (trivially, via allow-list exclusion); GREEN after Plan 02 (via registry-existence check). Pins the fabricated-id-yields-no-chip contract regardless of which path enforces it. Documented in test docstring.

### tests/state/test_coach.py — 5 new tests (appended under `# ---- Phase 66 — recall_fragment_for_event tests (COPILOT-01/02) ----`)

3. **`test_transition_recall_fragment_appears`** — RED today. Drives `AICoach.build_prompt(ev, recall_moments=[...])` for each of `{TRACK_CHANGE, MIX_MOVE, LAYER_ARRIVAL}`; asserts both the Phase 65 `"FROM A PAST SESSION"` fence AND the transition fragment unique substring `"in the live audio"` appear. Fails on per-test-body `from vibemix.state.coach import recall_fragment_for_event` ImportError (helper does not exist yet).
4. **`test_vocabulary_recall_fragment_appears`** — RED today. Drives with `ev.type="PHASE"`; asserts vocabulary unique substring `"echo your own past words"` appears. Same per-test-body ImportError shape.
5. **`test_task_for_event_byte_identical_v5_baseline_no_recall`** — GREEN today (no helper to break it); MUST stay GREEN after Plan 02. The LOAD-BEARING regression floor. Asserts `build_prompt(ev)` == `build_prompt(ev, recall_moments=None)` == `build_prompt(ev, recall_moments=[])` across the FULL event-type set `{KAAN_SPOKE, MANUAL, TRACK_CHANGE, PHASE, LAYER_ARRIVAL, MIX_MOVE, HEARTBEAT, KEY_CLASH, TRANSITION_OPPORTUNITY}`. Triple-equality contract pins the cold-path byte-identity invariant.
6. **`test_only_strongest_survivor_record_id_in_fragment`** — RED today. Builds three Record stubs (DESC by cosine), drives `build_prompt(ev_TRACK_CHANGE, recall_moments=survivors)`, asserts:
   - All three record_ids appear in the FULL output (the PAST-tense evidence_line block carries every survivor — Phase 65 contract).
   - The fragment portion (everything after `"in the live audio"`) contains the STRONGEST record_id exactly once AND does NOT contain the weaker ones (structural max-1-per-turn cap).
   - Fails because the fragment portion does not exist (no helper).
7. **`test_transition_wins_track_change_overlap`** — RED today. On a TRACK_CHANGE turn (in BOTH event gates per CONTEXT Q1+Q2), transition-shape WINS (Pitfall 5 + Open Q1). Asserts `"in the live audio"` appears AND `"echo your own past words"` does NOT. Same per-test-body ImportError shape.

### tests/agent/test_dj_cohost_linter.py — 2 new tests (appended under `# ---- Phase 66 — coach-tier cooldown tests (COPILOT-02) ----`)

8. **`test_cooldown_suppresses_back_to_back_recalls_COPILOT02`** — RED today. Two consecutive `TRACK_CHANGE` turns with the wall clock mocked (t=100.0 then t=180.0 — 80s gap inside the 120s window). Stub `_StubRecall.get_latest()` returns non-empty survivors on both turns. Asserts: turn N emits a `[recall:<id>]` token; turn N+1 does NOT (cooldown active). Per-test-body import of `RECALL_CALLBACK_COOLDOWN_S` wrapped in pytest.fail-on-ImportError → fails on the missing symbol.
9. **`test_max_one_recall_per_turn_COPILOT02`** — RED today. Single turn, three survivors from the stub. Spies on `AICoach.build_prompt` to capture the prompt string. Asserts: full prompt contains all three record_ids (Phase 65 contract), fragment portion (after `"in the live audio"` marker) contains the strongest record_id EXACTLY ONCE and NEITHER of the weaker ones. Same per-test-body ImportError shape.

### tests/repo/test_no_recall_antifeatures.py — NEW file (1 negative-control test + 1 main scan)

10. **`test_strip_comments_and_docstrings_removes_string_content`** — GREEN (negative control). Feeds the cloned stripper a docstring source AND a string-literal source each containing the forbidden phrase `"you tend to"`. Asserts both are removed by the stripper. Also asserts NAME-token anchors (`x`, `foo`) survive (the stripper is not pathologically blanking). Covers both stripper failure modes (false positive from non-removed strings + false negative from blanket blanking).

11. **`test_no_recall_antifeatures_in_coach_surface_COPILOT03`** — GREEN VACUOUSLY. Scans TARGET_FILES (state/coach.py + prompts/matrix.py), strips comments+docstrings, lowercases, asserts no FORBIDDEN_RECALL_PHRASES present. Declared vacuous-green per the pre-grep evidence recorded in the module docstring + the 66-VALIDATION.md §Wave 0 Requirements section.

## Fragment-Unique Substring Locks

Verified absent from current source at land time:

```
$ grep -F "in the live audio" src/vibemix/state/coach.py src/vibemix/prompts/matrix.py
(zero hits)

$ grep -F "echo your own past words" src/vibemix/state/coach.py src/vibemix/prompts/matrix.py
(zero hits)
```

These two substrings are the structural anchors that make tests 3, 4, 6, 7, and 9 RED for the RIGHT reason today. Plan 02's fragment templates MUST emit these substrings (66-RESEARCH.md Pattern 1 + Pattern 2 supply the full templates).

## Pre-Grep Evidence for Vacuous-Green Static Gate

Executed during planning (2026-05-22) AND re-verified at commit time:

```
$ grep -nE "you tend to|you usually|you always|next track|you should play|your tendency|based on your past|I recommend|my recommendation|you should try" \
    src/vibemix/state/coach.py src/vibemix/prompts/matrix.py
(zero hits)
```

Recorded in `tests/repo/test_no_recall_antifeatures.py` module docstring + in 66-VALIDATION.md §Wave 0 Requirements.

## v5.0 Byte-Identity Floor — STAYS GREEN

Verified targeted before and after the Wave 0 commits:

```
$ pytest tests/state/test_coach.py::test_evidence_line_audible_no_recall_byte_identical_v5_baseline \
         tests/state/test_coach.py::test_evidence_line_silent_state_full_format -v
2 passed in 0.07s
```

Both goldens stay byte-identical. The new `test_task_for_event_byte_identical_v5_baseline_no_recall` is the second-tier reinforcement (catches a broken falsy-gate in the future Plan 02 helper across all 9 event types).

## Task Commits

1. **Task 1: chip + fragment + byte-identity RED tests (test_citation_strip_emit.py + test_coach.py)** — `4d2ae49` (test)
2. **Task 2: cooldown RED tests + new tests/repo anti-feature static gate (test_dj_cohost_linter.py + test_no_recall_antifeatures.py)** — `b8a5e1a` (test)

## Files Created/Modified

- `tests/agent/test_citation_strip_emit.py` — +97 lines (2 new tests after :203, with section header)
- `tests/state/test_coach.py` — +303 lines (5 new tests + `_phase_66_record_stubs` helper + section header)
- `tests/agent/test_dj_cohost_linter.py` — +260 lines (2 new tests + section header)
- `tests/repo/test_no_recall_antifeatures.py` — NEW, 267 lines (FORBIDDEN_RECALL_PHRASES + TARGET_FILES + verbatim stripper clone + negative-control + main scan)

## Decisions Made

- **Per-test-body imports, NOT top-of-file imports.** Both `recall_fragment_for_event` (in test_coach.py) and `RECALL_CALLBACK_COOLDOWN_S` (in test_dj_cohost_linter.py) are imported INSIDE each new test function, wrapped in `try/except ImportError: pytest.fail(...)`. This keeps file COLLECTION clean — sibling tests in both files stay collectable and pass while the new symbols do not yet exist. A top-of-file import would have broken collection.
- **Substring-uniqueness pre-flight executed BEFORE committing Task 1.** `grep -F "in the live audio" ...` and `grep -F "echo your own past words" ...` both returned zero hits on src/vibemix/state/coach.py and src/vibemix/prompts/matrix.py. Evidence recorded in the test module comment (the substrings are the structural anchors for tests 3, 4, 6, 7, 9 — they MUST be unique to fragment templates Plan 02 lands).
- **Pre-grep vacuous-green re-verified at commit time.** The 11-pattern anti-feature scan was run once at planning (2026-05-22 in 66-VALIDATION.md) and re-run before committing Task 2 — still zero hits in TARGET_FILES. The main static scan is declared vacuous-green at land; its lifetime role is sentinel against future regressions.
- **Negative-control stripper test substitutes the memory-gate positive control.** Phase 66 forbidden phrases are human English prose with embedded spaces; Python syntax forbids multi-word identifiers; therefore no NAME-token form can survive stripping. The substitution + rationale is documented in the new file's module docstring (~80 lines of divergence documentation, the longest module docstring in tests/repo/).
- **Stripped source lowercased before substring matching.** Phase 66's forbidden phrases are case-insensitive English prose (vs the memory-gate's case-sensitive Python identifiers); the `.lower()` is the second documented divergence from the analog.
- **The `test_fabricated_recall_yields_no_chip_COPILOT01` test is GREEN today AND GREEN after Plan 02.** Two enforcement paths converge on the same final state (`strip == []`): today via allow-list exclusion (`continue` at :216), after Plan 02 via registry-existence check (`if not timestamps: continue` at :220). Documented in the test docstring; pins the contract regardless of which path enforces it.

## Deviations from Plan

**None — plan executed exactly as written.**

The plan's `<action>` blocks specified every test name, every assertion shape, every section header, every section-comment, every pre-grep verification step, and the exact per-test-body import pattern. Each was followed verbatim. No deviations under Rules 1–4 fired. The substring-uniqueness pre-grep was already part of Task 1's `<action>` block; the executor re-ran it both at planning AND at commit time and recorded both results.

## Threat Surface

Wave 0 has zero production-code changes — only test additions. The only Wave-0-applicable threats are the testing-quality ones in 66-01-PLAN.md `<threat_model>`:

- **T-66-01-01 (vacuous static gate):** mitigated. `Path.read_text` errors on missing TARGET_FILES (not silently passes); the negative-control stripper test catches both stripper failure modes (over-stripping and under-stripping).
- **T-66-01-02 (fragment substring collides with unrelated prose):** mitigated. Both substring choices were pre-grepped against `src/vibemix/state/coach.py` + `src/vibemix/prompts/matrix.py` AT PLAN TIME AND AT COMMIT TIME — both returned zero hits. Recorded in the test module comment.
- **T-66-01-03 (byte-identity test as tautology):** mitigated. The test asserts triple-equality across THREE distinct call shapes (`recall_moments=None`, `recall_moments=[]`, no-kwarg call) — none of them have the same syntactic form, so a tautology bug would require a 3-way coincidence. Documented in test docstring.
- **T-66-01-SC (slopcheck):** N/A. Zero net-new dependencies (pure test-only phase).

## Verification

- **Task 1 targeted:** `pytest tests/agent/test_citation_strip_emit.py tests/state/test_coach.py -q --no-header` → 5 failed (the intentional REDs: 1 grounded chip + 4 fragment tests) / 50 passed (incl. the byte-identity floor + the trivially-green fabricated_recall test).
- **Task 2 targeted:** `pytest tests/agent/test_dj_cohost_linter.py tests/repo/test_no_recall_antifeatures.py -q --no-header` → 2 failed (the intentional REDs: 2 cooldown ImportError tests) / 11 passed (incl. the negative-control stripper test + the vacuous-green main scan + 9 existing Phase 65 linter tests).
- **Combined Wave 0 sample:** `pytest tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_linter.py tests/state/test_coach.py tests/repo/test_no_recall_antifeatures.py -q` → **7 failed / 61 passed** (7 RED = 5 fragment-side + 2 cooldown-side; 61 GREEN incl. v5.0 byte-identity goldens + Phase 65 anti-poisoning gates + the new static-gate's negative-control + main scan).
- **Full suite:** `pytest -q` → **15 failed / 4142 passed / 26 skipped**. 7 = intentional Phase 66 REDs (above); 8 = the documented `live-tuning-or-brain` baseline (test_wire13_anti_slop_disabled_path_passes_none_kwargs, test_tag_regex_unchanged_in_this_plan, test_state_md_phase_16_line_is_annotated_retired, test_readme_feature_matrix_in_sync × 2, test_cut_release_accepts_valid_rc_tag_shape, test_cut_release_blocks_on_missing_milestone_audit, test_smoke_08_main_source_wires_cache_create_with_graceful_degradation). **ZERO NEW non-Phase-66 failures.**
- **v5.0 byte-identity goldens:** `pytest tests/state/test_coach.py::test_evidence_line_audible_no_recall_byte_identical_v5_baseline tests/state/test_coach.py::test_evidence_line_silent_state_full_format -v` → 2 passed (the load-bearing regression floor holds).
- **Fragment-unique substring uniqueness (re-verified):** `grep -F "in the live audio" ...` → zero hits; `grep -F "echo your own past words" ...` → zero hits.
- **Anti-feature pre-grep (re-verified):** `grep -nE "you tend to|you usually|you always|next track|you should play|your tendency|based on your past|I recommend|my recommendation|you should try" ...` → zero hits.

## Next Phase Readiness

- **Plan 02 (Wave 1 GREEN)** can now land the production-code edits with the RED contract as a structural compass:
  - The chip allow-list edit at `dj_cohost.py:215` (add `"recall"`) + the fixed-verb branch flips test 1 GREEN.
  - The `recall_fragment_for_event` helper + `TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` + `VOCABULARY_RECALL_FRAGMENT_TPL` constants in `state/coach.py` + the `build_prompt` integration flip tests 3, 4, 6, 7 GREEN.
  - The `RECALL_CALLBACK_COOLDOWN_S` constant + `self._last_recall_callback_at` field + the cooldown gate + the EMIT-path arm in `agent/dj_cohost.py` flip tests 8, 9 GREEN.
  - The byte-identity floor (test 5) MUST stay GREEN throughout — Plan 02's falsy-gate (`if not recall_moments: return ""` in the helper) is the structural guarantee.
  - The anti-feature static gate (test 11) MUST stay vacuous-green — Plan 02's fragment templates contain none of the forbidden phrases (66-RESEARCH.md Pattern 1 + Pattern 2 confirmed by manual review).

## Self-Check: PASSED

- `tests/agent/test_citation_strip_emit.py` — FOUND, contains `test_recall_citation_yields_chip_with_registry_timestamp_COPILOT01` + `test_fabricated_recall_yields_no_chip_COPILOT01`.
- `tests/state/test_coach.py` — FOUND, contains the `# ---- Phase 66 — recall_fragment_for_event tests (COPILOT-01/02) ----` section header + all five new tests + `_phase_66_record_stubs` helper.
- `tests/agent/test_dj_cohost_linter.py` — FOUND, contains the `# ---- Phase 66 — coach-tier cooldown tests (COPILOT-02) ----` section header + both cooldown tests + per-test-body imports of `RECALL_CALLBACK_COOLDOWN_S` wrapped in pytest.fail-on-ImportError.
- `tests/repo/test_no_recall_antifeatures.py` — FOUND, contains `FORBIDDEN_RECALL_PHRASES` + `TARGET_FILES` + `_strip_comments_and_docstrings` (verbatim clone with lock-step comment) + `test_strip_comments_and_docstrings_removes_string_content` (negative control) + `test_no_recall_antifeatures_in_coach_surface_COPILOT03` (main scan).
- Commit `4d2ae49` — FOUND in `git log` (Task 1).
- Commit `b8a5e1a` — FOUND in `git log` (Task 2).

---

*Phase: 66-visible-copilot-move*
*Completed: 2026-05-22*
