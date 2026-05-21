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
