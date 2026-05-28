# Phase 99 HARDEN-RETRY — Deferred Items

Out-of-scope discoveries logged during phase execution. None of these block
phase completion; they are unrelated to the Factor-9 starvation surface and
will be addressed in their respective owner phases.

## Pre-existing repo-gate failures (discovered during Plan 99-05 regression check)

The following four tests fail on `pytest -q tests/repo/` against the
current `live-tuning-or-brain` branch (verified by rolling back to commit
`6b8e62ef` — pre-Plan-99-05 — and re-running the same suite; failures
identical, so they pre-date Phase 99 entirely).

| Test | Domain | Likely owner |
|------|--------|--------------|
| `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired` | STATE.md annotation drift | Roadmap maintenance |
| `tests/repo/test_phase20_docs.py::test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback` | Active-planning docs reference outdated Gemini-fallback wording | Phase 20 docs maintenance |
| `tests/repo/test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync` | README feature matrix lags shipped phases | README sync chore |
| `tests/repo/test_readme_feature_matrix_sync.py::test_feature_matrix_includes_all_completed_phases` | README missing phases 91-98 (v9.0 "Lesson One" milestone) | README sync chore |

All four are doc/manifest sync drift, not source-code regressions. Scope
boundary applies (only auto-fix issues caused by THIS task's changes) —
documented here per execute-plan.md's SCOPE BOUNDARY rule, NOT fixed.

## Additional pre-existing failures (discovered during Plan 99-08 full-suite run)

Adding the 11 other failures from Plan 99-08's Task 2 full-suite run for completeness. Same scope-boundary disposition — none caused by Phase 99, all owned by other subsystems / parallel sessions.

| Test | Domain | Likely owner |
|------|--------|--------------|
| `tests/audit/test_audit_md_generator.py::test_generator_is_idempotent` | Audit-MD generator | Audit chore (not library) |
| `tests/e2e/test_phase_41_latency_stack_integration.py::test_router_resolves_all_paths` | Phase 41 latency stack | Phase 41 |
| `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline` | Orphan-inventory baseline | Kaan-noted concurrent-session item ("don't refresh baselines others own") |
| `tests/scripts/test_sync_github_meta.py::test_topics_list_includes_required_10` | GitHub-meta sync | Repo meta chore |
| `tests/scripts/test_sync_github_meta.py::test_homepage_url_is_altidus_with_utm` | GitHub-meta sync | Repo meta chore |
| `tests/security/test_capability_snapshot.py::test_committed_snapshot_matches_current_default` | Tauri capability snapshot | Frontend-wiring session (parallel) |
| `tests/security/test_capability_snapshot.py::test_check_mode_passes_on_current_state` | Tauri capability snapshot | Frontend-wiring session (parallel) |
| `tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_filter_test_submodules[vibemix-core.macos.spec]` | PyInstaller spec filter | Sidecar packaging chore |
| `tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_filter_test_submodules[vibemix-core.windows.spec]` | PyInstaller spec filter | Sidecar packaging chore |
| `tests/ui_bus/test_mood_change_envelope.py::test_count_parity_holds_after_addition` | UI bus envelope count parity | ipc.session.set_mode parallel session |
| `tests/ui_bus/test_recordings_messages.py::test_count_parity_at_77` | UI bus envelope count parity | ipc.session.set_mode parallel session |

## Pre-existing collection-time ImportErrors (Plan 99-08 excluded these via `--ignore`)

| Module | Cause | Owner |
|--------|-------|-------|
| `tests/e2e/macbook` | missing `jinja2` dependency | E2E packaging chore |
| `tests/ipc/test_session_messages.py` | `SessionSetMode` import — undefined symbol | ipc.session.set_mode parallel session (commit `1c038a11` landed the sidecar but the ui_bus re-export hasn't merged yet) |
| `tests/ui_bus/test_messages_schema.py` | same `SessionSetMode` import | same parallel session |

Phase 99 verify chain (`tests/library/test_codex_curate_stop_reason.py` + `tests/library/test_toolset_starvation.py` + `tests/library/test_toolset_starvation_concurrency.py` + `tests/library/test_cli_exit_codes.py` + `tests/library/test_telegram_bridge.py` + `tests/repo/test_no_seen_relaxation.py`): **53/53 GREEN, 0 regressions.**

Phase 99 island (`tests/library/` + `tests/repo/test_no_seen_relaxation.py`): **646/646 GREEN, 0 regressions.**
