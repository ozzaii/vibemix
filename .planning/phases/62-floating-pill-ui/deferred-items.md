# Phase 62 — Deferred / Out-of-Scope Items

Out-of-scope discoveries logged during execution. These are NOT fixed by the
current plan (scope-boundary rule) — they pre-date this work or belong to a
sibling plan on the `live-tuning-or-brain` branch.

## Full-suite baseline at plan 62-03 close (Task 3 regression gate)

Full `pytest -q` (no markers): **9 failed, 4087 passed, 26 skipped** (221.93s).

Plan 62-03 (additive `deck_state` on the ws:8765 frame) touched ONLY
`src/vibemix/runtime/ws_bus.py` (+50 lines, pure additive) and added
`tests/runtime/test_ws_bus_deck_state.py`. None of the 9 failing tests
exercise `_serialize_deck_state` or the new flat-frame field — proven by grep
(no `deck_state` / `ws_broadcast` assertion in any failing test) and by reading
the failure detail of each. **Zero new failures introduced by deck_state.**

The documented `live-tuning-or-brain` WIP baseline was 7. It has drifted to 9
because in-flight pill-window work (plan 62-02) added `"pill"` to
`tauri/src-tauri/capabilities/default.json` without regenerating the committed
`SNAPSHOT.json` — that is the 2 extra `test_capability_snapshot.py` failures,
NOT a deck_state regression. They belong to 62-02's branch WIP, not 62-03.

| Failing test | Group | Touches ws_bus / deck_state? | Why it fails (pre-existing / sibling WIP) |
|--------------|-------|------------------------------|-------------------------------------------|
| `test_main_anti_slop_wiring.py::test_wire13_anti_slop_disabled_path_passes_none_kwargs` | anti-slop-wiring | No | Documented 7-WIP (anti-slop wiring source assertion) |
| `test_cut_release_invokes_bravoh_server.py::test_tag_regex_unchanged_in_this_plan` | cut_release | No | Documented 7-WIP (release tooling) |
| `test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync` | readme-matrix | No | Documented 7-WIP (README feature matrix sync) |
| `test_readme_feature_matrix_sync.py::test_feature_matrix_includes_all_completed_phases` | readme-matrix | No | Documented 7-WIP (README feature matrix sync) |
| `test_cut_release_preflight.py::test_cut_release_accepts_valid_rc_tag_shape` | cut_release | No | Documented 7-WIP (release preflight) |
| `test_cut_release_preflight.py::test_cut_release_blocks_on_missing_milestone_audit` | cut_release | No | Documented 7-WIP (release preflight) |
| `test_main_smoke.py::test_smoke_08_main_source_wires_cache_create_with_graceful_degradation` | main-smoke | No (asserts `__main__.py` source for `system_instruction_body=SYSTEM_INSTRUCTION`) | Documented 7-WIP (main cache wiring) |
| `test_capability_snapshot.py::test_committed_snapshot_matches_current_default` | capability-snapshot | No | Sibling 62-02 WIP: `default.json` has `"pill"`, `SNAPSHOT.json` not regenerated |
| `test_capability_snapshot.py::test_check_mode_passes_on_current_state` | capability-snapshot | No | Sibling 62-02 WIP: same `"pill"` snapshot drift |

The 4 new `test_ws_bus_deck_state.py` tests are GREEN within the full run
(counted in the 4087 passed).

**Action:** none for 62-03. The 2 capability-snapshot failures resolve when
plan 62-02 regenerates `SNAPSHOT.json` (`python scripts/dist/snapshot_capabilities.py --write`);
that is 62-02's responsibility, not this plan's (scope boundary).
