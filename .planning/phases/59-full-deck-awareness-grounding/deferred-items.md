# Phase 59 — Deferred Items (out-of-scope discoveries)

Items discovered during execution that are NOT caused by the current plan's
changes. Per the executor SCOPE BOUNDARY rule these are logged, not fixed.

## Pre-existing full-suite failures on `live-tuning-or-brain` (discovered Plan 59-01)

These 7 tests were failing on the branch **before** Plan 59-01 touched anything.
Proven pre-existing by reverting `src/vibemix/state/music_state.py` to the
pre-plan commit `5f375c0` and re-running — all 7 fail identically with my deck-
state changes absent. None reference `deck_state` / `harmonics` / `to_camelot` /
`DeckTrack` / `DeckState`. They stem from the in-flight v4.0 WIP (`__main__.py`
orchestrator refactor, README feature-matrix not regenerated for phases 55–58,
cut-release script churn).

| Test | Pre-existing cause |
|------|--------------------|
| `tests/coach/test_main_anti_slop_wiring.py::test_wire13_anti_slop_disabled_path_passes_none_kwargs` | `__main__.py` anti-slop wiring changed by in-flight WIP (`system_instruction_body=SYSTEM_INSTRUCTION` no longer literal in `main()`) |
| `tests/repo/test_cut_release_invokes_bravoh_server.py::test_tag_regex_unchanged_in_this_plan` | `cut_release.sh` tag-regex churn (release-infra WIP) |
| `tests/repo/test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync` | README AUTO-GEN feature-matrix block not regenerated for phases 55–58 |
| `tests/repo/test_readme_feature_matrix_sync.py::test_feature_matrix_includes_all_completed_phases` | same — phases 55,56,57,58 missing from README block |
| `tests/scripts/test_cut_release_preflight.py::test_cut_release_accepts_valid_rc_tag_shape` | `cut_release.sh` preflight regex churn |
| `tests/scripts/test_cut_release_preflight.py::test_cut_release_blocks_on_missing_milestone_audit` | `cut_release.sh` milestone-audit gate churn |
| `tests/test_main_smoke.py::test_smoke_08_main_source_wires_cache_create_with_graceful_degradation` | `__main__.py` cache-create wiring changed by in-flight WIP |

**Action:** none in Plan 59-01. The README feature-matrix and cut-release/
`__main__.py` wiring belong to the v4.0 ship/branch work, not deck-state. Surface
to Kaan / a later plan that owns the `live-tuning-or-brain` finalization.

### Re-confirmed at Plan 59-02 close (2026-05-21)

Plan 59-02 (citable `key:` evidence source) ran the full suite: **7 failed, 3947
passed, 26 skipped** — the SAME 7 tests, unchanged count. 59-02 touched only the
citation/grammar surface (`evidence_registry.py`, `citation_linter.py`,
`prompts/matrix.py`, `agent/dj_cohost.py` + their 4 test files); none of the 7
failing files reference `EVIDENCE_SOURCES` / `parse_citations` /
`CITATION_GRAMMAR_BLOCK` / `_build_citation_strip` / `key:` (grep-verified empty).
No new failures introduced — these remain the in-flight `live-tuning-or-brain`
WIP debt for a later finalization plan.

### Re-confirmed at Plan 59-03 close (2026-05-21)

Plan 59-03 (event-type plumbing + DECK-05 read-only repo test) ran the full
suite: **7 failed, 3952 passed, 26 skipped** — the SAME 7 tests, unchanged
count (passing count rose 3947 → 3952 from the 5 new tests this plan added: 2
event-priority asserts + 3 repo-scrub deck-readonly cases). 59-03 touched only
`state/event.py`, `audio/constants.py`, and three test files
(`test_event_priority.py`, `test_constants.py`, `test_repo_scrub.py`); none of
the 7 failing files reference `EVENT_PRIORITY` / `MIN_EVENT_GAP_PER_TYPE` /
`KEY_CLASH` / `TRANSITION_OPPORTUNITY` / `deck_readonly` (grep-verified empty).
No new failures, no golden flips — these remain the in-flight
`live-tuning-or-brain` WIP debt for a later finalization plan.

### Re-confirmed at Plan 59-04 close (2026-05-21)

Plan 59-04 (deck-poller single-writer wiring + coach evidence_line + __main__
spawn) ran the full suite: **7 failed, 3976 passed, 26 skipped** — the SAME 7
tests, unchanged count. 59-04 touched `state/refresh.py`, `state/coach.py`,
`__main__.py`, `.planning/codebase/orphans.csv` + three test files
(`test_refresh_deck.py`, `test_coach_prompt_grounding.py` and Task-1's
`test_deck_poller.py`); none of the 7 failing files reference `deck_source` /
`deck_state.decks` / `DeckPoller` / the deck evidence_line block (grep-verified
empty). The 7 stem from the unrelated `__main__.py` WIP churn (the
`system_instruction_body=SYSTEM_INSTRUCTION` literal moved out of `main()` by
in-flight v4.0 work — NOT by my deck wiring), README feature-matrix not
regenerated for phases 55–58, and `cut_release.sh` regex churn.

**One transient 8th failure, caused by THIS plan and FIXED in-plan (not deferred):**
`tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline`
flagged `replace_decktrack` (Task-1 deck_poller helper) as a new orphan. Resolved
by a surgical single-line add to `.planning/codebase/orphans.csv` (commit 8a1527c),
leaving the two unrelated stale entries (`BlackHoleProbeResult`,
`set_device_nominal_sample_rate`) untouched. Orphan-diff green again.
