---
phase: 93-exemplar-engine-evidence-source
plan: 05
subsystem: state-evidence-citation-grammar
tags: [exemplar, evidence-source, schema-mirror, citation-grounding, invariant-2, anti-slop, 4-site-mirror, recall-precedent]

# Dependency graph
requires:
  - phase: 93-exemplar-engine-evidence-source
    provides: "Plan 93-04 — ExemplarFinder.find() pre-registers `(\"exemplar\", track_id, t_session)` against EvidenceRegistry BEFORE the LLM emits the cite; this plan closes the loop by adding `exemplar` to the 4 schema-mirror sites so parse_citations() extracts the atom and the linter gates it"
  - phase: 65-recall-callback-source
    provides: "v6 [recall:] precedent — the verbatim 4-site mirror pattern from commits 2016e36b (sites 1+2 atomic) + 977c0140 (site 3) + 0bfc8bd0 (site 4); Plan 93-05 mirrors this structure EXACTLY for [exemplar:]"
  - phase: 20-citation-linter
    provides: "CitationLinter (src/vibemix/coach/citation_linter.py) — the existing Phase 20 linter walks parse_citations output against EvidenceRegistry.has() and strips the whole turn when any cite is unmatched; [exemplar:] now flows through this gate by virtue of sites 1+2 landing together"
provides:
  - "src/vibemix/state/evidence_registry.py — EDITED: sites 1+2 atomic (EVIDENCE_SOURCES frozenset extended 9 → 10 with `exemplar`; _SOURCE_ALT regex alternation appended `|exemplar`; EBNF docstring `source` rule extended with `'exemplar'`; new `exemplar-body := <track_id>` stanza added; module docstring count updated 9 → 10)"
  - "src/vibemix/prompts/matrix.py — EDITED: site 3 (CITATION_GRAMMAR_BLOCK Forms list gains `[exemplar:<track_id>]` as the 10th entry; lock-step comment header count 9 → 10 + parenthetical chain extended with `+ exemplar Phase 93 / EXEMPLAR-05`)"
  - "src/vibemix/agent/dj_cohost.py — EDITED: site 4 (_build_citation_strip allow-list 5-tuple → 6-tuple adds `\"exemplar\"`; per-source verb-derivation switch gains `elif source == \"exemplar\": verb = \"exemplar\"` branch with the leak-prevention rationale comment)"
  - "tests/state/test_evidence_registry.py — EDITED: test_evidence_11_sources_constant_locked_GROUND02 docstring + assertion updated from 9 to 10 sources (the `exemplar` literal now appears in the frozenset assertion)"
  - "tests/learn/test_exemplar_citation_schema_mirror.py — EDITED: module-level `pytest.skip(allow_module_level=True)` removed; 6 sub-tests now PASS against the live source (site_1, site_2, site_2b, site_3, site_4, all_four_sites_lockstep)"
  - "tests/learn/test_exemplar_grounding_e2e.py — EDITED: module-level skip removed; 3 sub-tests now PASS (fabricated_exemplar_id_not_in_registry_means_unmatched, parse_citations_extracts_exemplar_atom, parse_citations_extracts_exemplar_in_multi_atom)"
affects: [93-06-cli-and-ingest-extension, 94-course-1-lessons, 95-course-2-lessons, 96-course-3-cue-source]

# Tech tracking
tech-stack:
  added: []  # Zero new deps — pure-code edit on existing modules (evidence_registry / matrix / dj_cohost)
  patterns:
    - "4-site schema mirror — the v6 [recall:] precedent's commit structure replicated EXACTLY: sites 1+2 atomic (silent-poisoning-hole pair), site 3 separate, site 4 separate. Each commit lands the minimum self-consistent change."
    - "Allow-list grammar evolution — 5-tuple → 6-tuple in _build_citation_strip with the new source's verb-derivation branch placed AFTER the previous opaque-body branch (recall) and BEFORE the default `else` (the KEY@t partition path). Mirrors the recall/key precedents above."
    - "Fixed-string verb for opaque bodies — `verb = \"exemplar\"` is a single lowercase word that trivially satisfies the locked verb-format regex `^[a-z]+( [a-z]+){0,2}$` without leaking the track_id (which may contain `:`, `-`, spaces, or `_packaged:` synthetic-namespace prefixes that would break the regex if naively partitioned)."
    - "Selective git staging via `git add --patch` — when a shared file (matrix.py) carries pre-existing sibling-session modifications, stage ONLY the Task hunks (the docstring count update + the new Form line) and leave sibling work untouched. Concurrent-session discipline."
    - "Module-level skip lift on RED-state schema-mirror test stubs: convert `pytest.skip(allow_module_level=True)` calls to direct removal once the upstream plan ships the names. Matches the pattern from Plan 93-04 for the engine-side test stubs."

key-files:
  created:
    - .planning/phases/93-exemplar-engine-evidence-source/93-05-SUMMARY.md
  modified:
    - src/vibemix/state/evidence_registry.py
    - src/vibemix/prompts/matrix.py
    - src/vibemix/agent/dj_cohost.py
    - tests/state/test_evidence_registry.py
    - tests/learn/test_exemplar_citation_schema_mirror.py
    - tests/learn/test_exemplar_grounding_e2e.py

key-decisions:
  - "Sites 1+2 land in ONE commit (c2c8aa41) — the silent-poisoning-hole pair must NEVER split across commits. The lockstep comment at evidence_registry.py:120-131 explicitly names this; the v6 [recall:] commit 2016e36b is the precedent. Splitting them across two commits creates a window where a fabricated [exemplar:<id>] is in the frozenset (so the registry would accept the write) but not in _SOURCE_ALT (so parse_citations would never extract it, the linter never sees it, it rides through un-validated). Atomic lockstep is the silent-poisoning-hole closure."
  - "Sites 3 and 4 are SEPARATE commits (2a49e0f4, 853e776a) — they don't form a silent-poisoning-hole pair with each other. Site 3 (prompt grammar) is the producer (tells Gemini the cite shape exists). Site 4 (chip strip allow-list) is the consumer (decides whether to surface a UI chip). They can land independently inside the same plan with no race window."
  - "Verb for opaque bodies is a FIXED letters-only string, not partition-derived. The track_id body shape is `<track_id>` which can include `:`, `-`, spaces, and synthetic prefixes like `_packaged:low:track_03`. The locked verb-format regex `^[a-z]+( [a-z]+){0,2}$` would reject any partition-derived verb (camelot-style or session-id-style). The fixed `\"exemplar\"` label trivially passes and ALSO prevents leaking embedding-internal track_id detail to the UI chip surface (the full track_id rides in `event_id` for click→tutor-context deep-link)."
  - "EvidenceRegistry stays at v1.0 permissive — `EVIDENCE_SOURCES` is the prompt + linter boundary contract, not a registry write-time validator. The frozenset extension is consumed by `parse_citations()` (via `_SOURCE_ALT`), by `CITATION_GRAMMAR_BLOCK` (via the Forms list), and by `_build_citation_strip` (via the allow-list tuple). The registry itself accepts any string source/key at write time so `ExemplarFinder.find()` was already legal in Plan 93-04 — this plan just makes the read-side grammar see the writes."
  - "memory/ingest.py asymmetry STAYS at 8 sources — both `recall` and `exemplar` are RETRIEVAL-time sources, never ingest-time. A stored past reaction never cited recall/exemplar itself (the agent registers retrieved record_ids / track_ids at THIS session's emit time, not at the prior session's ingest time). The ingest-time extractor's alternation must NOT whitelist either. Comment updated in evidence_registry.py:151-154 to mention both."
  - "Selective patch-staging for matrix.py — the file was in `M` state from a sibling-session edit (the `Phrase-source provenance:` paragraph at lines 24-30 referencing `hardikpandya/stop-slop`). I used `git add --patch` with `n,y,y` to stage ONLY my two hunks (the lockstep comment update + the new Form line) and left the sibling-session paragraph unstaged. Verified clean separation via `git diff --cached` + `git diff` outputs before committing Task 2."
  - "Task 1's `test_all_four_sites_lockstep` failure was EXPECTED — the test loops over EVIDENCE_SOURCES asserting every source appears in CITATION_GRAMMAR_BLOCK. After Task 1, `exemplar` is in the frozenset but not yet in the grammar block (Task 2 lands that). The failure is the lockstep contract correctly reporting a transient mismatch; Task 2 closes it. Did NOT count as a Rule 1-3 deviation."

patterns-established:
  - "4-site schema-mirror Plan-level commit structure: Task 1 lands sites 1+2 atomically + the legacy count test bump + the schema-mirror module skip lift; Task 2 lands site 3; Task 3 lands site 4 + the grounding-e2e module skip lift. Pattern reusable verbatim when adding any future evidence source (e.g. P96's conditional `[cue:<anchor_id>]` source)."
  - "Concurrent-session selective patch-staging — when a shared file carries pre-existing sibling-session modifications, `printf 'n\\ny\\ny\\n' | git add --patch <file>` selectively stages only your Task hunks and leaves the rest unstaged. Verify discipline via `git diff --cached` (your hunks only) + `git diff` (sibling work remaining). Documented as the canonical pattern in concurrent-Claude-session discipline."

requirements-completed: [EXEMPLAR-05]
# Plan 93-05 completes EXEMPLAR-05 (citation source schema-mirror lock /
# Invariant #2 binding for [exemplar:<track_id>]). The 4-site mirror is now
# closed: parse_citations() extracts exemplar atoms, CITATION_GRAMMAR_BLOCK
# teaches Gemini the shape, _build_citation_strip surfaces grounded picks as
# UI chips, and the registry pre-write from Plan 93-04 makes fabricated ids
# strip the turn via the existing Phase 20 CitationLinter.

# Metrics
duration: 11min
completed: 2026-05-28
---

# Phase 93 Plan 05: Exemplar Engine — `[exemplar:<track_id>]` Evidence Source 4-Site Mirror Summary

**4-site schema-mirror lock for `[exemplar:<track_id>]` landed atomically — EVIDENCE_SOURCES 9 → 10, _SOURCE_ALT alternation extended, CITATION_GRAMMAR_BLOCK Forms list gains the 10th entry, _build_citation_strip allow-list 5-tuple → 6-tuple; the v6 [recall:] precedent (commits 2016e36b → 977c0140 → 0bfc8bd0) mirrored EXACTLY into 3 commits c2c8aa41 / 2a49e0f4 / 853e776a. With Plan 93-04's `ExemplarFinder.find()` pre-registration write, a fabricated `[exemplar:bogus]` now strips the whole AI turn via the existing Phase 20 CitationLinter — Invariant #2 binding closed.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-05-28T04:59:15Z
- **Completed:** 2026-05-28T05:10:18Z
- **Tasks:** 3
- **Files modified:** 6 (3 src + 3 tests)
- **Files created:** 1 (this SUMMARY)

## Accomplishments

- **Site 1 — `EVIDENCE_SOURCES` frozenset extended** (`src/vibemix/state/evidence_registry.py:120-122`): added `"exemplar"` to the 9-source frozenset, taking the count to 10. Docstring stanza added between the existing `recall` block and the `SCHEMA-MIRROR:` lock-step comment, describing the new source as existence-only retrieval-time, registered by `ExemplarFinder.find()` per Plan 93-04 wiring.
- **Site 2 — `_SOURCE_ALT` regex alternation extended** (`src/vibemix/state/evidence_registry.py:155`): appended `|exemplar` to the alternation token-set. Atomic with Site 1 in a single commit — the silent-poisoning-hole pair landed together. The `_INNER_ATOM` body regex (`[^\s,\]]+`) is UNCHANGED — track_id bodies like `library:Marlon Hoffstadt - Atlas` or `_packaged:low:track_03` parse cleanly since they have no whitespace/comma/bracket; the inner colon survives as part of the body (mirroring `recall:20260520-2200:7` and `key:A:8A`).
- **EBNF docstring extended** (`src/vibemix/state/evidence_registry.py:161-176`): `source := ...` rule appended `| 'exemplar'`; new `exemplar-body := <track_id>` stanza added below the existing `recall-body` line; module count updated from "9 single-citation forms" to "10".
- **`test_evidence_11_sources_constant_locked_GROUND02` updated** (`tests/state/test_evidence_registry.py:210-224`): docstring rewritten to mention Phase 93 EXEMPLAR-05 alongside the historical DECK-03/RECALL-01 additions; literal frozenset assertion now includes `"exemplar"`. Function name DELIBERATELY preserved (`test_evidence_11_sources_constant_locked_GROUND02`) — the historical "11" prefix is load-bearing for git-grep history per the plan's `<action>` note.
- **Site 3 — `CITATION_GRAMMAR_BLOCK` Forms list extended** (`src/vibemix/prompts/matrix.py:129`): new 10th Form line `  [exemplar:<track_id>]  band-exemplar track, e.g. [exemplar:library:Marlon Hoffstadt - Atlas]` added immediately below the recall form, with the same 2-space indentation as the other entries. Lock-step comment header updated from "9 source forms" to "10 source forms" with `+ exemplar Phase 93 / EXEMPLAR-05` appended to the parenthetical chain (mirrors the existing pattern: `+ key added Phase 59 / DECK-03, + recall added Phase 65 / RECALL-01, + exemplar added Phase 93 / EXEMPLAR-05`).
- **Site 4 — `_build_citation_strip` allow-list extended** (`src/vibemix/agent/dj_cohost.py:267-268`): the 5-tuple `("ev", "mix", "midi", "key", "recall")` became the 6-tuple `("ev", "mix", "midi", "key", "recall", "exemplar")`. The above-tuple comment got a Phase 93 (EXEMPLAR-05) addition pointing to the Plan 93-04 `ExemplarFinder.find()` pre-registration that makes the defense-in-depth flow correct.
- **`elif source == "exemplar"` branch added to verb-derivation switch** (`src/vibemix/agent/dj_cohost.py:302-314`): new branch placed immediately after the `elif source == "recall":` block, before the default `else` (the KEY@t partition path). Sets `verb = "exemplar"` — a fixed letters-only string that trivially passes the locked verb-format regex `^[a-z]+( [a-z]+){0,2}$` and prevents leaking embedding-internal track_id detail (the full track_id rides in `event_id` for the click→tutor-context deep-link).
- **Module-level skip lifts on 2 RED test stubs**:
  - `tests/learn/test_exemplar_citation_schema_mirror.py` — removed `pytest.skip(allow_module_level=True)`; 6 sub-tests now PASS.
  - `tests/learn/test_exemplar_grounding_e2e.py` — removed `pytest.skip(allow_module_level=True)`; 3 sub-tests now PASS.

## Task Commits

Each task was committed atomically. The 3-commit structure mirrors v6 `[recall:]` exactly:

1. **Task 1: Sites 1+2 ATOMIC — evidence_registry.py + 11_sources count test + schema-mirror skip lift** — `c2c8aa41` (feat)
   - `src/vibemix/state/evidence_registry.py` (+~25 lines docstring + 2 lines edits across frozenset / alternation / EBNF + count comment update)
   - `tests/state/test_evidence_registry.py` (docstring + literal assertion 9 → 10 source)
   - `tests/learn/test_exemplar_citation_schema_mirror.py` (`pytest.skip(allow_module_level=True)` removed + docstring update)
   - Mirrors v6 commit `2016e36b` for `[recall:]`.

2. **Task 2: Site 3 — CITATION_GRAMMAR_BLOCK** — `2a49e0f4` (feat)
   - `src/vibemix/prompts/matrix.py` (lock-step comment count 9 → 10 + new 10th Form line)
   - **Selectively patch-staged** via `git add --patch` to exclude a pre-existing sibling-session paragraph (the `Phrase-source provenance:` stanza referencing `hardikpandya/stop-slop`). Sibling session's work left untouched in the worktree.
   - Mirrors v6 commit `977c0140` for `[recall:]`.

3. **Task 3: Site 4 — _build_citation_strip + grounding e2e green** — `853e776a` (feat)
   - `src/vibemix/agent/dj_cohost.py` (allow-list 5-tuple → 6-tuple with new comment block + new `elif source == "exemplar":` verb branch with comment block)
   - `tests/learn/test_exemplar_grounding_e2e.py` (`pytest.skip(allow_module_level=True)` removed + docstring update)
   - Mirrors v6 commit `0bfc8bd0` for `[recall:]`.

**Plan metadata commit:** Will follow this SUMMARY write — captures SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md.

## Files Created/Modified

### Created (1 file)

| File | REQ-ID | Purpose |
|---|---|---|
| `.planning/phases/93-exemplar-engine-evidence-source/93-05-SUMMARY.md` | — | This summary |

### Modified (6 files)

| File | Site | Change |
|---|---|---|
| `src/vibemix/state/evidence_registry.py` | Site 1 + Site 2 | EVIDENCE_SOURCES frozenset 9 → 10 + new docstring stanza; _SOURCE_ALT alternation appended `\|exemplar` + new lockstep-warning comment block; EBNF `source` rule extended + new `exemplar-body` stanza; module count 9 → 10 in 2 places |
| `src/vibemix/prompts/matrix.py` | Site 3 | CITATION_GRAMMAR_BLOCK Forms list gains 10th entry `[exemplar:<track_id>]`; lock-step comment count 9 → 10 + Phase 93 parenthetical |
| `src/vibemix/agent/dj_cohost.py` | Site 4 | _build_citation_strip allow-list 5-tuple → 6-tuple + new Phase 93 comment block; verb-derivation switch gains `elif source == "exemplar": verb = "exemplar"` branch with leak-prevention rationale |
| `tests/state/test_evidence_registry.py` | — | test_evidence_11_sources_constant_locked_GROUND02 docstring + literal assertion 9 → 10 sources (function name preserved per plan note) |
| `tests/learn/test_exemplar_citation_schema_mirror.py` | — | Module-level `pytest.skip(allow_module_level=True)` removed + docstring rewritten to reflect green state |
| `tests/learn/test_exemplar_grounding_e2e.py` | — | Module-level `pytest.skip(allow_module_level=True)` removed + docstring rewritten to reflect green state |

## Decisions Made

1. **Sites 1+2 ATOMIC in commit c2c8aa41** — the silent-poisoning-hole pair MUST land together. v6 `[recall:]` commit `2016e36b` is the literal precedent. The lockstep-warning comment block at `evidence_registry.py:140-154` explicitly names this asymmetry. Splitting them would create a transient window where `exemplar` is in `EVIDENCE_SOURCES` (so the registry write is contract-legal) but NOT in `_SOURCE_ALT` (so `parse_citations` never extracts the atom and the linter never sees it) — a fabricated `[exemplar:<id>]` would silently ride through un-validated. Atomic landing is the closure.
2. **Sites 3 and 4 SEPARATE commits (2a49e0f4, 853e776a)** — they don't form a silent-poisoning-hole pair with each other. Site 3 (prompt grammar) is the producer (tells Gemini the cite shape exists). Site 4 (chip strip allow-list) is the consumer (decides whether to surface a UI chip). They can land independently inside the same plan with no race window. Matches the v6 commit cadence (`977c0140` → `0bfc8bd0`).
3. **Fixed letters-only `verb = "exemplar"`** rather than a partition-derived verb (mirrors the recall/key precedents above). Track_id body shape includes `:`, `-`, spaces, and synthetic prefixes like `_packaged:low:track_03` — naive partition would either fail the locked verb-format regex `^[a-z]+( [a-z]+){0,2}$` OR leak embedding-internal track_id detail to the UI chip surface. The fixed string trivially passes and the full track_id rides in `event_id` for click→tutor-context deep-link.
4. **Test_evidence_11_sources function name preserved** — the historical "11" prefix is from Phase 11 GROUND-02 lock and is load-bearing for git-grep history. Only the docstring + literal assertion update; the function name stays `test_evidence_11_sources_constant_locked_GROUND02` even though the assertion now covers 10 sources (per the plan's `<action>` Step B note: "If a future linter complains about the '11' prefix being a phase number, ignore — the name is load-bearing for git-grep history.").
5. **Selective `git add --patch` for matrix.py** — the file was in `M` state from a sibling Codex session (the `Phrase-source provenance:` paragraph at lines 24-30 referencing the `hardikpandya/stop-slop` MIT skill). Staged ONLY the Task 2 hunks (lock-step comment count update + new Form line) and left the sibling-session paragraph unstaged. Verified clean separation via `git diff --cached` (my hunks only) + `git diff` (sibling work remaining) before committing. Concurrent-session discipline.
6. **`memory/ingest.py` ASYMMETRY stays at 8 sources** — both `recall` and `exemplar` are RETRIEVAL-time sources, never ingest-time. The ingest-time extractor's copy of the alternation must NOT whitelist either. Comment block at `evidence_registry.py:151-154` updated to mention BOTH sources explicitly so future maintainers don't "fix" the asymmetry by adding `exemplar` to the ingest path.
7. **NO cooldown wiring added** — the plan's `<action>` Task 3 note explicitly defers this: "DO NOT add `exemplar` to any cooldown-clearing logic at line 1215+ (`self._registry.clear_source(\"recall\")` etc.) — the exemplar source is registered fresh per `find()` call via `t_session=time.time()`; the registry's existing 50-turn rolling buffer self-prunes naturally. Stale-cite drift is not a concern in P93 (it might become one in P94 if a lesson re-runs over many turns; surface as `§EXEMPLAR-COOLDOWN` ride-forward IF Kaan ear-pass on Course 1.14 demonstrates the issue)." Honored verbatim; no edit to the cooldown surface.

## Deviations from Plan

None. The plan's `<action>` blocks ported verbatim into the implementation; no Rule 1/2/3 deviations were needed during execution.

Two minor stylistic / discipline choices that diverge from the literal plan text are documented decisions, not deviations:

- **Task 1's `test_all_four_sites_lockstep` failure during sites-1+2 verification was EXPECTED.** The test loops over `EVIDENCE_SOURCES` asserting every source appears in `CITATION_GRAMMAR_BLOCK`. After Task 1, `exemplar` is in the frozenset but `CITATION_GRAMMAR_BLOCK` doesn't list it yet (Task 2 lands that). The plan's Task 1 `<verify>` clause filters by `-k "site_1 or site_2 or 11_sources or lockstep"` which catches this test, but the broader plan structure explicitly anticipates: "Site_3 + Site_4 tests stay RED (will flip in Tasks 2 + 3)." Not a deviation — the lockstep failure is the lockstep contract correctly reporting a transient mismatch that Task 2 closes.
- **`git add --patch` for Task 2** instead of `git add src/vibemix/prompts/matrix.py` — necessitated by the pre-existing sibling-session modification in the same file. Documented as Decision 5 above and as a reusable pattern under `patterns-established`.

## Threat Flags

No new security-relevant surface beyond the plan's `<threat_model>`. Each STRIDE row from the plan was honored:

- **T-93-05-01 (Spoofing / Misinformation):** Sites 1+2 atomic landing in `c2c8aa41` closes the silent-poisoning-hole. A fabricated `[exemplar:bogus]` now matches the regex (`parse_citations` extracts it), gets seen by the existing Phase 20 CitationLinter, fails the registry existence check (Plan 93-04's `ExemplarFinder.find()` only pre-registers ids it actually picked), and the linter strips the whole turn. Pinned by `tests/learn/test_exemplar_grounding_e2e.py::test_fabricated_exemplar_id_not_in_registry_means_unmatched` (PASSING).
- **T-93-05-02 (Tampering — split commit):** Sites 1+2 landed in ONE commit (`c2c8aa41`). Verified via `git log --oneline -3` — Task 1 commit message + diff both confirm the atomic pair. Future rogue rebases that split them would be caught by `tests/learn/test_exemplar_citation_schema_mirror.py::test_site_1_*` + `test_site_2_*` running on every PR head.
- **T-93-05-03 (Repudiation — frozenset vs grammar block drift):** The existing auto-extending lockstep test `tests/prompts/test_matrix.py::test_r_grammar_block_cross_validated_against_evidence_sources` (verified PASSING) loops over `EVIDENCE_SOURCES` asserting `[<source>:` appears in `CITATION_GRAMMAR_BLOCK`. Auto-fails any future drift.
- **T-93-05-04 (Information Disclosure — verb-derivation leak):** The `verb = "exemplar"` fixed-string branch in `dj_cohost.py:312-314` explicitly avoids deriving a verb from the `event_id` body. Track_id internals like `_packaged:low:foo` don't leak through the chip — the comment block names this rationale verbatim.
- **T-93-05-SC (No new package installs):** Zero. Plan 93-05 is pure-code edit on 3 existing source modules + 3 existing test modules. No `pip install`, no dependency changes.

## Test Results

**Invariant #2 binding closed.** All 9 schema-mirror + grounding-e2e tests PASS:

```
tests/learn/test_exemplar_citation_schema_mirror.py::test_site_1_evidence_sources_frozenset_contains_exemplar       PASS
tests/learn/test_exemplar_citation_schema_mirror.py::test_site_2_source_alt_regex_includes_exemplar                  PASS
tests/learn/test_exemplar_citation_schema_mirror.py::test_site_2b_evidence_citation_re_matches_exemplar_atom         PASS
tests/learn/test_exemplar_citation_schema_mirror.py::test_site_3_citation_grammar_block_includes_exemplar            PASS
tests/learn/test_exemplar_citation_schema_mirror.py::test_site_4_citation_strip_allow_list_includes_exemplar         PASS
tests/learn/test_exemplar_citation_schema_mirror.py::test_all_four_sites_lockstep                                    PASS
tests/learn/test_exemplar_grounding_e2e.py::test_fabricated_exemplar_id_not_in_registry_means_unmatched              PASS
tests/learn/test_exemplar_grounding_e2e.py::test_parse_citations_extracts_exemplar_atom                              PASS
tests/learn/test_exemplar_grounding_e2e.py::test_parse_citations_extracts_exemplar_in_multi_atom                     PASS
```

**v6 recall precedent stays green** (no regression in the schema-mirror sibling system):

```
tests/agent/test_dj_cohost_linter.py                                161 collected ......
tests/coach/test_citation_linter.py                                  ...
tests/state/test_evidence_registry.py                                ...
tests/prompts/test_matrix.py                                         ...
161 passed in 1.30s
```

**`test_evidence_11_sources_constant_locked_GROUND02` asserts 10 sources** and is GREEN.

**`test_r_grammar_block_cross_validated_against_evidence_sources`** auto-extends through the frozenset loop and is GREEN with 10 sources.

**Full repo regression:** `PYTHONPATH=src python3 -m pytest -q --no-header --ignore=tests/e2e/macbook` → `5522 passed, 25 skipped, 12 deselected, 1 xfailed, 4 xpassed, 9 failed`. All 9 failures are **PRE-EXISTING repo baseline drift** from sibling-session work unrelated to Plan 93-05:

- `tests/audit/test_audit_md_generator.py::test_generator_is_idempotent` — audit MD generator drift (no evidence_registry / matrix / dj_cohost references)
- `tests/e2e/test_phase_41_latency_stack_integration.py::test_router_resolves_all_paths` — model router path baseline (Phase 41, pre-P93)
- `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired` — STATE.md Phase 16 annotation line missing (milestone v9.0 STATE rewrite removed it)
- `tests/repo/test_phase20_docs.py::test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback` — STATE.md missing "Phase 88 (UI) is now wired..." string (milestone v9.0 STATE rewrite)
- `tests/security/test_capability_snapshot.py` (2 tests) — security capability snapshot baseline drift
- `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline` — orphan baseline drift from sibling-session new files
- `tests/sidecar/test_build_sidecar_rename.py` (2 tests) — PyInstaller spec missing `"cli"` token

None reference `evidence_registry`, `prompts/matrix`, `agent/dj_cohost`, `exemplar`, or any of the 6 files this plan modified. Surfaced for transparency; out-of-scope per the executor's "auto-fix only direct task changes" rule.

## §EXEMPLAR-COOLDOWN — KAAN-ACTION ride-forward

The plan's Task 3 action note explicitly defers per-source cooldown wiring (line 346: "DO NOT add `exemplar` to any cooldown-clearing logic at line 1215+ — the exemplar source is registered fresh per `find()` call via `t_session=time.time()`; the registry's existing 50-turn rolling buffer self-prunes naturally."). If Course 1.14 ear-pass on a real lesson re-run reveals stale-cite drift (e.g. an exemplar cited in lesson 1.13 leaking into a 1.14 cite that doesn't ground), introduce a `RECALL_CALLBACK_COOLDOWN_S`-style constant for exemplar and clear the source per-lesson boundary. The cite-format and 4-site mirror would NOT need to change — only the registry-clear timing.

## Issues Encountered

- **Concurrent-session worktree:** 27 pre-existing modified files in the worktree from sibling Codex sessions (intel/prompts cleanup + frontend rocker/picker/group/performance-group + debrief + matrix.py provenance paragraph). Committed Plan 93-05 changes by named paths only (`git add src/vibemix/state/evidence_registry.py …`) or via `git add --patch` for the matrix.py case where my hunks shared a file with sibling-session work. Never `git add -A`. Cross-session files untouched.

## User Setup Required

None — this plan is pure-code edit. The 4-site mirror is closed and the Invariant #2 binding holds. Plan 93-04's `ExemplarFinder.find()` already pre-registers picks against the registry, and as of `853e776a` a fabricated `[exemplar:bogus]` strips the whole turn via the existing Phase 20 CitationLinter.

## Next Phase Readiness

- All 3 tasks executed; all committed atomically (`c2c8aa41` sites 1+2 / `2a49e0f4` site 3 / `853e776a` site 4). 3-commit structure mirrors v6 [recall:] exactly.
- 2 of 11 Plan 93-01 RED test modules flipped GREEN (`test_exemplar_citation_schema_mirror.py` + `test_exemplar_grounding_e2e.py`), bringing the cumulative count of Plan-93 flipped modules to 4 of 11 (Plans 93-02/93-04 flipped 2; this plan flips 2 more).
- **Plan 93-06** (CLI + ingest extension) is the last remaining 93-family plan. It owns the `vibemix learn exemplar <band>` CLI subcommand + the `compute_band_shares` flag on folder_ingest; the remaining stub `tests/learn/test_cli_learn_exemplar.py` flips green there.
- **Plan 94** (Course 1 lessons) and **Plan 95** (Course 2 lessons) can now emit `[exemplar:<track_id>]` cites in lesson prompts with full grounding confidence: a track_id the LLM invents will strip the turn; a track_id from `ExemplarFinder.find()`'s pre-registered set resolves cleanly.
- **Plan 96** (Course 3) can use the same 4-site pattern verbatim if it adds the conditional `[cue:<anchor_id>]` source.
- Phase 92 invariant pins remain green (`test_no_new_ws_port`, `test_runtime_invariants`, `test_tutor_system_instruction_lock`, `test_evidence_registry`).
- `EVIDENCE_SOURCES` count is now **10** (was 9). The schema-mirror source-of-truth carries `exemplar` in lock-step across all 4 sites.
- Full regression (excluding pre-existing e2e/macbook conftest collection error from missing jinja2 dep): **5522 passed, 0 new red** introduced by Plan 93-05. 9 pre-existing failures are all sibling-session repo-baseline drift, unrelated.

## Self-Check

Verifying claims before proceeding to state updates:

**1. Created files exist:**

```
FOUND: .planning/phases/93-exemplar-engine-evidence-source/93-05-SUMMARY.md
```

**2. Modified files carry the exemplar token:**

```
src/vibemix/state/evidence_registry.py    — `exemplar` appears at lines 92, 109, 111, 115, 121, 142, 144, 147, 148, 152, 154, 155, 163, 169 (14 hits)
src/vibemix/prompts/matrix.py             — `exemplar` appears at line 107 (lockstep comment) + line 129 (Forms list)
src/vibemix/agent/dj_cohost.py            — `exemplar` appears in the 6-tuple allow-list + the verb-derivation elif branch (lines 256+267-268+302-314)
tests/state/test_evidence_registry.py     — `exemplar` in the literal frozenset assertion
tests/learn/test_exemplar_citation_schema_mirror.py — module-level skip removed; 6 tests PASS
tests/learn/test_exemplar_grounding_e2e.py — module-level skip removed; 3 tests PASS
```

**3. Commits exist:**

```
FOUND: c2c8aa41 (Task 1 — sites 1+2 ATOMIC — evidence_registry.py + 11_sources count test + schema-mirror skip lift)
FOUND: 2a49e0f4 (Task 2 — site 3 — CITATION_GRAMMAR_BLOCK)
FOUND: 853e776a (Task 3 — site 4 — _build_citation_strip + grounding e2e skip lift)
```

**4. EVIDENCE_SOURCES count:**

```
$ PYTHONPATH=src python3 -c "from vibemix.state.evidence_registry import EVIDENCE_SOURCES; print(len(EVIDENCE_SOURCES), 'exemplar' in EVIDENCE_SOURCES)"
10 True
```

**5. Invariant #2 binding statement:**

A fabricated `[exemplar:bogus]` now strips the whole AI turn via the existing Phase 20 `CitationLinter`. The chain is: `parse_citations()` extracts `("exemplar", "bogus")` (sites 1+2 enable this), the linter calls `registry.has("exemplar", "bogus", t_session, tol=2.0)` (registry has no such pre-registered id, returns False), the linter raises and the whole-turn strip fires (defense-in-depth tier 1). The defense-in-depth tier 2 is the `_build_citation_strip` allow-list (site 4) — even if the upstream strip somehow misses, the chip surface drops the unresolved cite.

## TDD Gate Compliance

Plan 93-05 tasks all carried `tdd="true"` in the plan frontmatter. The flow per task:

- **Task 1 RED:** `test_exemplar_citation_schema_mirror.py` already had 6 RED tests from Plan 93-01 (module-skipped); `test_evidence_11_sources_constant_locked_GROUND02` was GREEN with the 9-source assertion before the edit.
- **Task 1 GREEN:** Edit the 4 surfaces (frozenset / regex / EBNF docstring / count test); 3 atomic-site tests + the count test PASS. Lockstep test stays RED pending Task 2 (expected).
- **Task 2 RED:** `test_site_3_citation_grammar_block_includes_exemplar` + `test_all_four_sites_lockstep` RED after Task 1; Task 2 lands site 3.
- **Task 2 GREEN:** Both site_3 + lockstep tests PASS after the matrix.py edit.
- **Task 3 RED:** `test_site_4_citation_strip_allow_list_includes_exemplar` RED after Task 2; 3 grounding e2e tests still skipped at module level.
- **Task 3 GREEN:** All 6 schema-mirror + 3 grounding e2e tests PASS after the dj_cohost.py edit + skip lift.

Each commit landed with the verification command's expected output (4 atomic-site tests + count for Task 1; site_3 + lockstep + Test R for Task 2; full 9-test green for Task 3). The TDD gate sequence committed in git history:
- `c2c8aa41` `feat(93-05): add exemplar evidence source... (sites 1+2)` — covers both RED-to-GREEN cycle for sites 1+2
- `2a49e0f4` `feat(93-05): add [exemplar:<track_id>] form... (site 3)` — covers site 3
- `853e776a` `feat(93-05): add exemplar to _build_citation_strip... (site 4)` — covers site 4

Per the v6 `[recall:]` precedent + the plan's `<action>` block, the 4-site mirror commits are bundled with the test edits (the test stubs were already RED-and-skipped from Plan 93-01; this plan flips them GREEN inside the same commits as the production edits, mirroring the v6 commits exactly). The TDD cycle was honored at the commit level: each commit's diff carries both the production edit AND the corresponding test that goes from skipped/RED to GREEN.

## Self-Check: PASSED

---
*Phase: 93-exemplar-engine-evidence-source*
*Completed: 2026-05-28*
