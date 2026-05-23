# Phase 67 Plan 67P02 — Per-Marker Triage Record

**Triaged:** 2026-05-23 on Kaan's Mac (darwin, BlackHole 2ch installed, FLX4 NOT plugged at triage time)
**Baseline:** 4186 collected · 65 deselected by default opt-in marker filter
**Default suite:** 4160 passed · 26 skipped · 0 failed (Wave 0 invariant — verified before triage)

## Classification Rubric (per 67-CONTEXT.md `### Failure-Mode Triage`)

- **Tier A** — passes on real hardware AND would pass on hosted CI runners → no work (CI-greenable as-is).
- **Tier B** — fails on hosted CI runners but explainable by an environmental constraint (BlackHole kext / Win 11 desktop SKU / FLX4 USB / live env var) → `xfail(strict=False)` + `# reason:` adjacent + §V7-LIVE-NN cluster entry in KAAN-ACTION-LEGAL.md.
- **Tier C** — non-deterministic on local hardware → defer to Wave 4 quarantine (do NOT add `@pytest.mark.flaky` here).

Default per CONTEXT D-TRIAGE: "Tier B over Tier C" — trust the audio (and the real hardware) more than retries.

## Cluster Map (Tier-B environmental constraints)

| Cluster | Constraint | Tests covered | Fix-path owner |
| ------- | ---------- | ------------- | -------------- |
| §V7-LIVE-01 | BlackHole 2ch kext cannot load on hosted macOS runners (kext requires reboot; ephemeral runners don't reboot mid-job — actions/runner-images#11746) | `tests/test_audio_macos_live.py` (3 tests, all module-level `pytestmark = pytest.mark.macos_audio`) | Kaan's Mac (BlackHole already installed) |
| §V7-LIVE-02 | `windows-latest` GitHub-hosted runner is Windows Server 2022, NOT Windows 11 desktop SKU — some WASAPI / SMTC / COM device-change paths behave differently | `tests/test_audio_windows_live.py` (1), `tests/test_midi_windows_live.py` (2), `tests/test_screen_windows_live.py` (1), `tests/test_track_windows_live.py` (1) — 5 tests total | Kaan's Parallels/UTM Win 11 VM (+ real DDJ-FLX4 USB for the MIDI cases) |
| §V7-LIVE-03 | Real Pioneer DDJ-FLX4 must be plugged over USB — no hardware on any hosted runner | `tests/test_midi_macos_live.py::test_flx4_live_resolves_and_decodes` (1) | Kaan's Mac + plugged FLX4 |
| §V7-LIVE-04 | Live full-stack smoke — needs `VIBEMIX_LIVE_SMOKE=1` env (Kaan-only manual gate) and/or binds real port 8765 (not a CI gate per the test's own docstring) | `tests/test_main_live.py::test_live_startup_shutdown` (1), `tests/sidecar/test_wizard_entrypoint.py::test_wizard_starts_and_terminates_cleanly` (1) — 2 tests total | Kaan's Mac, manual one-shot |

**Total Tier-B tests:** 11 (across 4 clusters)
**Total Tier-A tests:** 54 (8 integration + 4 slow + 23 e2e + 17 cli + 2 network)
**Total Tier-C tests:** 0 (no non-determinism observed in this triage pass)
**Sum check:** 11 + 54 + 0 = 65 ✓ (matches the deselected baseline)

---

## Per-Marker Triage Tables

### `macos_audio` (6 tests collected)

Observed on Kaan's Mac (`uv run pytest -m "macos_audio" --tb=line`): **4 passed · 2 skipped · 0 failed**.

The 2 skips are runtime-gated (`pytest.skip(...)` inside the test body — NOT module-level decorators) — they degrade to skip cleanly when hardware/env is missing.

| test_id | observed on Kaan's Mac | tier | fix_path_id | rationale |
| ------- | ---------------------- | ---- | ----------- | --------- |
| `tests/test_audio_macos_live.py::test_blackhole_device_present_at_48khz_or_raises` | PASSED | **B** | §V7-LIVE-01 | Passes on Kaan's Mac (BlackHole installed); would FAIL on `macos-13/14` hosted runners (kext can't load — actions/runner-images#11746) |
| `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device` | PASSED | **B** | §V7-LIVE-01 | Same module-level `pytestmark = pytest.mark.macos_audio`; CoreAudio surface needs real driver presence on the runner |
| `tests/test_audio_macos_live.py::test_blackhole_input_is_48k_for_live_capture` | PASSED | **B** | §V7-LIVE-01 | Same module-level pytestmark; sample-rate inspection requires real BlackHole device |
| `tests/test_midi_macos_live.py::test_flx4_live_resolves_and_decodes` | SKIPPED (no FLX4 plugged) | **B** | §V7-LIVE-03 | Runtime `pytest.skip` when no FLX4 enumerable; would PASS with FLX4 plugged. Cluster = real DDJ-FLX4 USB |
| `tests/test_main_live.py::test_live_startup_shutdown` | SKIPPED (no `VIBEMIX_LIVE_SMOKE=1`) | **B** | §V7-LIVE-04 | Runtime env-var gate — Kaan-only opt-in per test docstring. Live full-stack smoke (subprocess + recordings/ dir) |
| `tests/sidecar/test_wizard_entrypoint.py::test_wizard_starts_and_terminates_cleanly` | PASSED | **B** | §V7-LIVE-04 | Binds real port 8765 (live integration test, per test docstring "not a CI gate" — clusters with live full-stack) |

**Verdict:** All 6 → Tier B (BlackHole cluster ×3, FLX4 cluster ×1, live full-stack cluster ×2).

---

### `windows_only` (5 tests collected)

Observed on Kaan's Mac: **0 passed · 5 skipped · 0 failed**. All five carry a module-level `pytestmark = pytest.mark.skipif(sys.platform != 'win32', ...)` so they skip cleanly on darwin (correct gating — the firewall test sees the file but bodies never execute on Mac).

Cannot run on Kaan's Mac. Per RESEARCH.md Assumption A6, all 5 are Tier-B-pending-Win-VM-confirmation. The constraint cluster is the Win Server 2022 (hosted) vs Win 11 desktop (real-VM) SKU split (RESEARCH.md Pitfall 2) — the MIDI cases additionally require real DDJ-FLX4 USB.

| test_id | observed on Kaan's Mac | tier | fix_path_id | rationale |
| ------- | ---------------------- | ---- | ----------- | --------- |
| `tests/test_audio_windows_live.py::test_audio_windows_can_open_real_loopback` | SKIPPED (skipif darwin) | **B** | §V7-LIVE-02 | Real WASAPI loopback against actual desktop audio device — `windows-latest` (Server 2022) lacks the desktop audio session shape |
| `tests/test_midi_windows_live.py::test_midi_windows_opens_real_ddj_flx4` | SKIPPED (skipif darwin) | **B** | §V7-LIVE-02 | Needs real DDJ-FLX4 over USB (no hardware on hosted runners) AND Win 11 desktop SKU |
| `tests/test_midi_windows_live.py::test_midi_windows_listener_thread_starts_and_stops` | SKIPPED (skipif darwin) | **B** | §V7-LIVE-02 | Same — listener spawns against real FLX4; cluster owns both hardware + SKU constraints |
| `tests/test_screen_windows_live.py::test_screen_windows_captures_real_window` | SKIPPED (skipif darwin) | **B** | §V7-LIVE-02 | Real Win11 window enumeration + capture — Server 2022 has no desktop window manager surface |
| `tests/test_track_windows_live.py::test_track_windows_reads_real_smtc` | SKIPPED (skipif darwin) | **B** | §V7-LIVE-02 | SMTC (System Media Transport Controls) is a Win10/11 desktop API — Server 2022 hosts skip it |

**Verdict:** All 5 → Tier B (Win 11 desktop SKU cluster).

---

### `integration` (8 tests collected)

Observed on Kaan's Mac: **8 passed · 0 skipped · 0 failed** in 6.50s. No skips, no errors. None require external hardware or live network.

| test_id | observed | tier | fix_path_id | rationale |
| ------- | -------- | ---- | ----------- | --------- |
| `tests/integration/test_mascot_dispatch_latency.py::test_mascot_dispatch_latency_p95_under_50ms` | PASSED | **A** | — | Pure in-process latency check; no external deps |
| `tests/integration/test_mascot_dispatch_latency.py::test_mascot_dispatch_latency_helpers_well_formed` | PASSED | **A** | — | Helper shape verification |
| `tests/integration/test_mascot_event_taxonomy_e2e.py::test_event_taxonomy_fixture_well_formed_structure` | PASSED | **A** | — | Fixture-only |
| `tests/integration/test_mascot_event_taxonomy_e2e.py::test_event_taxonomy_fixture_uses_canonical_subtypes_only` | PASSED | **A** | — | Fixture-only |
| `tests/integration/test_mascot_event_taxonomy_e2e.py::test_event_taxonomy_fixture_expected_states_are_canonical` | PASSED | **A** | — | Fixture-only |
| `tests/integration/test_mascot_event_taxonomy_e2e.py::test_event_taxonomy_fixture_covers_roadmap_criterion_5` | PASSED | **A** | — | Fixture-only |
| `tests/runtime/test_ws_bus_empty_frames.py::test_ws_broadcast_emits_no_empty_frames` | PASSED | **A** | — | In-process WS bus contract — no port binding |
| `tests/runtime/test_ws_bus_empty_frames.py::test_boot_smoke_reaches_phase_silent_cleanly` | PASSED | **A** | — | In-process boot smoke |

**Verdict:** All 8 → Tier A (no xfail, no §V7-LIVE entry, ready for CI).

---

### `slow` (4 tests collected)

Observed on Kaan's Mac: **4 passed · 0 skipped · 0 failed** in 5.27s. Despite the "slow" marker, none of these are actually 60-min soaks — the `slow` marker tags the *opt-in* slot but the implementations are synthetic-short variants.

| test_id | observed | tier | fix_path_id | rationale |
| ------- | -------- | ---- | ----------- | --------- |
| `tests/recording/test_60min_soak.py::test_60min_soak_wav_jsonl_session_json_invariants` | PASSED | **A** | — | Invariant check on synthetic short soak |
| `tests/runtime/test_soak_stability.py::test_short_synthetic_soak_bounded_rss_zero_underruns` | PASSED | **A** | — | Bounded RSS check on short synthetic soak |
| `tests/runtime/test_soak_stability.py::test_both_mode_reaction_traffic_zero_underruns` | PASSED | **A** | — | Reaction traffic under-run check |
| `tests/runtime/test_soak_stability.py::test_both_mode_run_soak_steady_state_zero_underruns` | PASSED | **A** | — | Steady-state under-run check |

**Verdict:** All 4 → Tier A.

---

### `e2e` (23 tests collected)

Observed on Kaan's Mac: **23 passed · 0 skipped · 0 failed** in 2.87s. End-to-end debrief lifecycle + cross-phase seam tests; all mocked or fixture-based, no external services.

| test_id | observed | tier | fix_path_id | rationale |
| ------- | -------- | ---- | ----------- | --------- |
| `tests/e2e/test_debrief_e2e_cache_hit.py::test_cache_hit_returns_within_1s` | PASSED | **A** | — | Mocked cache lookup |
| `tests/e2e/test_debrief_e2e_cache_hit.py::test_cache_invalidation_on_modified_mp3` | PASSED | **A** | — | Fixture-based |
| `tests/e2e/test_debrief_e2e_open_close_cycle.py::test_progressive_frames_arrive_in_order[asyncio]` | PASSED | **A** | — | Async loop deterministic |
| `tests/e2e/test_debrief_e2e_open_close_cycle.py::test_no_tmp_leftovers_after_cycle[asyncio]` | PASSED | **A** | — | Cleanup invariant |
| `tests/e2e/test_debrief_e2e_short_session_disabled.py::test_120s_session_raises_session_too_short` | PASSED | **A** | — | Guard test |
| `tests/e2e/test_debrief_e2e_short_session_disabled.py::test_missing_events_jsonl_raises_events_missing` | PASSED | **A** | — | Guard test |
| `tests/e2e/test_phase_41_latency_stack_integration.py::test_agent_validates_live_config` | PASSED | **A** | — | Config validation |
| `tests/e2e/test_phase_41_latency_stack_integration.py::test_thinking_gate_rejects_flex_on_live` | PASSED | **A** | — | Latency gate logic |
| `tests/e2e/test_phase_41_latency_stack_integration.py::test_thinking_gate_rejects_higher_than_minimal_thinking` | PASSED | **A** | — | Latency gate logic |
| `tests/e2e/test_phase_41_latency_stack_integration.py::test_perf01_live_config_latency_leg_positive_and_negative` | PASSED | **A** | — | Latency leg verification |
| `tests/e2e/test_seam_p18__p20.py::test_real_citation_passes_live_linter` | PASSED | **A** | — | Citation linter seam |
| `tests/e2e/test_seam_p18__p20.py::test_fake_citation_blocked_by_live_linter` | PASSED | **A** | — | Citation linter seam |
| `tests/e2e/test_seam_p19__agent.py::test_real_cache_padded_body_passes_token_floor` | PASSED | **A** | — | Cache padding seam |
| `tests/e2e/test_seam_p19__agent.py::test_real_cache_create_then_current_name_round_trip` | PASSED | **A** | — | Cache create/name seam |
| `tests/e2e/test_seam_p19__agent.py::test_real_cache_invalidate_clears_name_for_agent_fallback` | PASSED | **A** | — | Cache invalidate seam |
| `tests/e2e/test_seam_p25__p28.py::test_rekordbox_library_registers_into_evidence_and_clears_linter` | PASSED | **A** | — | Library→evidence seam |
| `tests/e2e/test_seam_p25__p28.py::test_unregistered_track_id_blocked_by_linter` | PASSED | **A** | — | Unregistered-id linter seam |
| `tests/e2e/test_seam_p27__eval_gate.py::test_replay_harness_produces_required_artifacts` | PASSED | **A** | — | Eval gate seam |
| `tests/e2e/test_seam_p27__eval_gate.py::test_eval_yml_calls_replay_harness_with_contract_flags` | PASSED | **A** | — | Eval gate seam |
| `tests/e2e/test_seam_p27__eval_gate.py::test_eval_yml_judges_values_match_harness_dispatcher` | PASSED | **A** | — | Eval gate seam |
| `tests/e2e/test_seam_p31__ws_bus.py::test_ws_bus_emits_layer_3_fields_priority_stack_consumes` | PASSED | **A** | — | WS bus seam |
| `tests/e2e/test_seam_p31__ws_bus.py::test_priority_stack_4_layer_names_match_ws_bus_contract` | PASSED | **A** | — | WS bus seam |
| `tests/e2e/test_seam_p31__ws_bus.py::test_ws_bus_frame_is_json_serialisable` | PASSED | **A** | — | WS bus seam |

**Verdict:** All 23 → Tier A.

---

### `cli` (17 tests collected)

Observed on Kaan's Mac: **17 passed · 0 skipped · 0 failed** in 31.63s. Subprocess CLI invocations — slow because each spawns Python — but deterministic.

| test_id | observed | tier | fix_path_id | rationale |
| ------- | -------- | ---- | ----------- | --------- |
| `tests/library/test_budget.py::test_cli_library_budget_returns_projection` | PASSED | **A** | — | Subprocess CLI; deterministic projection |
| `tests/library/test_budget.py::test_cli_library_budget_human_readable` | PASSED | **A** | — | Subprocess CLI |
| `tests/repo/test_cut_release_dry_run.py::test_dry_run_exits_zero` | PASSED | **A** | — | Dry-run cut_release.sh |
| `tests/repo/test_cut_release_dry_run.py::test_dry_run_stubs_signature_gate` | PASSED | **A** | — | Signature gate stub check |
| `tests/repo/test_cut_release_dry_run.py::test_dry_run_prints_green_summary` | PASSED | **A** | — | Output shape check |
| `tests/repo/test_cut_release_dry_run.py::test_dry_run_logs_kaan_gated_2b_pending` | PASSED | **A** | — | Gate-2b log line |
| `tests/repo/test_cut_release_dry_run.py::test_dry_run_uses_v4_audit_and_v0_tag` | PASSED | **A** | — | v4.0 audit + v0.1.0 tag pin |
| `tests/repo/test_cut_release_dry_run.py::test_dry_run_never_executes_publish` | PASSED | **A** | — | Publish hard-guard |
| `tests/runtime/test_soak_stability.py::test_soak_cli_runs_short_and_exits_zero` | PASSED | **A** | — | Short soak CLI |
| `tests/scripts/test_cli_library_search.py::test_cli_does_not_break_help` | PASSED | **A** | — | CLI help survives |
| `tests/scripts/test_cli_library_search.py::test_cli_search_help` | PASSED | **A** | — | CLI search --help |
| `tests/scripts/test_cli_library_search.py::test_cli_no_jwt_exits_with_json_error` | PASSED | **A** | — | No-JWT error path |
| `tests/scripts/test_cli_library_search.py::test_cli_no_library_cache_exits_clean` | PASSED | **A** | — | No-cache error path |
| `tests/scripts/test_cli_library_search.py::test_top_level_help_still_works` | PASSED | **A** | — | Top-level help survives |
| `tests/scripts/test_cli_library_similar.py::test_cli_similar_help` | PASSED | **A** | — | Similar --help |
| `tests/scripts/test_cli_library_similar.py::test_cli_similar_no_jwt_exits_clean` | PASSED | **A** | — | No-JWT clean exit |
| `tests/scripts/test_cli_library_similar.py::test_cli_similar_no_library_exits_clean` | PASSED | **A** | — | No-cache clean exit |

**Verdict:** All 17 → Tier A.

---

### `network` (2 tests collected)

Observed on Kaan's Mac: **2 passed · 0 skipped · 0 failed** in 3.40s. The GitHub org-readiness checker hits a well-known endpoint that should be cacheable; if CI hits rate limits in the future, this would deserve `xfail(strict=False)` then — for now, Tier A.

| test_id | observed | tier | fix_path_id | rationale |
| ------- | -------- | ---- | ----------- | --------- |
| `tests/launch/test_check_bravoh_org_ready.py::test_well_known_org_returns_exit_zero` | PASSED | **A** | — | Well-known GH org probe (anthropic) — public endpoint, no auth required |
| `tests/launch/test_check_bravoh_org_ready.py::test_missing_org_returns_exit_one` | PASSED | **A** | — | Definitely-non-existent org probe — deterministic 404 path |

**Verdict:** All 2 → Tier A.

---

## Summary

| Marker | Total | Tier A | Tier B | Tier C |
| ------ | ----- | ------ | ------ | ------ |
| `macos_audio` | 6 | 0 | 6 | 0 |
| `windows_only` | 5 | 0 | 5 | 0 |
| `integration` | 8 | 8 | 0 | 0 |
| `slow` | 4 | 4 | 0 | 0 |
| `e2e` | 23 | 23 | 0 | 0 |
| `cli` | 17 | 17 | 0 | 0 |
| `network` | 2 | 2 | 0 | 0 |
| **TOTAL** | **65** | **54** | **11** | **0** |

**Cluster count:** 4 (§V7-LIVE-01 BlackHole · §V7-LIVE-02 Win11 SKU · §V7-LIVE-03 FLX4 USB · §V7-LIVE-04 live full-stack)

Task 2 will create the matching 4 `### §V7-LIVE-NN` sub-entries in `KAAN-ACTION-LEGAL.md`'s new `## §V7-LIVE` section, and apply `xfail(strict=False, reason=...)` to all 11 Tier-B tests with adjacent `# reason:` comments.

---
*Phase: 67-all-tests-pass*
*Plan: 67P02*
*Triage date: 2026-05-23*
