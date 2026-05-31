# 2026-05-31 Dirty Tree Shipping Inventory

Branch: `live-tuning-or-brain`

Purpose: document the scattered dirty-tree work with exact current line anchors
so it can be split into clean, reviewable, shippable packages again.

Line reference note: line numbers are from the dirty worktree on 2026-05-31,
after the IPC triage, Learn screen-only highlight fixes, and runtime ingress
timestamp compatibility shim recorded below. If a file is reformatted,
regenerate the line anchors before using this as a PR checklist.

Verification note: the first inventory pass read and mapped the code. The
2026-05-31 audit update below records the targeted verification that was run
afterward, plus the low-risk IPC fixes landed during triage.

Packaging checklist: use
`.planning/handoffs/2026-05-31-package-checklist.md` as the current staging map.
It cross-checks every tracked and untracked dirty-tree path into a package,
hold lane, or deep-work lane.

## Worktree Shape

Tracked modifications: 97 files, 5181 insertions, 1756 deletions
(`git diff --shortstat`).

Untracked source/test/docs/assets: 86 paths (`git ls-files --others --exclude-standard`),
including:

- `.claude/hooks/`, `.claude/settings.json`, and three `.claude/skills/*`
  skill bundles.
- New untracked Python modules and helpers: `src/vibemix/library/cost.py`,
  `src/vibemix/library/pricing.py`, `src/vibemix/runtime/dev_mcp_server.py`,
  and `scripts/check_dirty_package_plan.py`.
- New tests: `tests/library/test_cost.py`, `tests/library/test_pricing.py`,
  `tests/runtime/test_coach_progress_emit.py`,
  `tests/runtime/test_dev_mcp_server.py`,
  `tests/runtime/test_drive_vibemix_ws_probe.py`,
  `tests/scripts/test_check_dirty_package_plan.py`, and `tauri/ui/tests/pill/*`.
- Launch/pricing docs and launch assets under `docs/launch/` and `docs/pricing/`.
- Launch screenshots now owned under `docs/launch/screenshots/` with a manifest.
- Premium visual-audit collateral now appears under `docs/design/` and
  `docs/design/screenshots/2026-05-31-premium-audit/`.
- The no-code cleanup plan now has a dedicated maintainability map at
  `.planning/handoffs/2026-05-31-maintainability-map.md`.
- `.planning/LEARN-MOAT-PLAN.md` is an untracked Learn architecture plan for
  the missing beatmatch-grade producer path; keep it in a hold lane until it is
  converted into a red-test-first implementation package.
- `.planning/singularity/2026-05-31/*.md` now contains read-only research/census
  briefs; keep them in a separate hold lane until citations/status language are
  reviewed or the briefs are split into package-specific work orders.

## Recommended Package Lanes

Package these as separate commits or PRs. Several lanes are product features,
not cleanup, and should not be buried in one "misc dirty tree" change.

0. Shipping inventory docs.
1. Agent/dev tooling and live verification helpers.
2. Session IPC and diagnostics wiring.
3. Library IPC contract cleanup.
4. Auto/ANLZ hot-cue materialization through pill and Viber.
5. Library/Viber live-read deck-pair audio context.
6. Pill next-suggestion interaction and browser polish.
7. Learn operator-action route mismatch bridge.
8. Beatmatch Judge creditability.
9. Earned Wall live refresh.
10. Live-stack cost/pricing CLI and docs.
11. Launch docs, pitch assets, and screenshots.
12. Runtime memory CLAP store readiness.
13. Tauri sidecar bundle freshness guard.
14. Live TTS shutdown hygiene.
15. Desktop auto-master 16ch upgrade.
16. Hold: premium enterprise visual-audit collateral.
17. Hold: controller-weighted deck-audio master context.
18. Hold: transition-clock / xfade / spoken-drop mix timing oracle.
19. Pruned: debrief timeline and citation summary IPC reservations.
20. Hold: Learn beatmatch producer moat plan.
21. Hold: Singularity research and subsystem census briefs.

## Audit Update: 2026-05-31 IPC Triage

### Checks Run

| Command | Result |
|---|---|
| `uv run python scripts/check_ipc_schema.py` | Pass: 72 dataclasses validate, 72 `oneOf` entries match 72 wrapper dataclasses, settings enum/payload parity OK. |
| `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py` | Pass: 72 message types; no dead/one-ended or reserved types remain. |
| MCP `which_handler` for `ipc.session.citation` and `ipc.status.recheck` | Pass: both report `WIRED (both ends)`. |
| `uv run python -m vibemix --session` plus MCP `sidecar_status` / `ws_observe` | Partial live pass: current source reached `ws://127.0.0.1:8765`, advertised 12 wizard-bus handlers, and streamed idle `ipc.session.snapshot` frames. This proves the diagnostic bus is reachable, not the full Tauri/DDJ/co-host path. |
| Schema-valid websocket `ipc.status.recheck` for `{"component":"midi"}` | Partial live pass: sidecar returned `ipc.status.tick` with `midi=1`, `screen=ok`, `livekit=connecting`, and `gemini=down`. |
| Schema-valid websocket `ipc.profile.view` | Partial live pass: sidecar returned `ipc.profile.view_result` with `consent=true`, `bytes=321`, and the stored profile payload. |
| Current-source `tool_ws_trigger_async` for typed `ipc.status.recheck` | Pass after tooling fix: helper sent an ISO `date-time` `ts` and returned the immediate `ipc.status.tick` reply with `midi=1`, `screen=ok`, `livekit=connecting`, and `gemini=down`. |
| `uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}' --watch ipc.status.tick --seconds 3` | Pass: the documented drive helper sent schema-valid typed IPC and printed `ipc.status.tick livekit=connecting gemini=down midi=1 screen=ok`. |
| Stale already-running MCP `ws_trigger` for typed `ipc.status.recheck` | Pass after runtime ingress compatibility fix: the child still sent numeric `ts`, current source normalized it before validation, and the diagnostic bus did not log the earlier `[wizard bus] schema violation`. |
| MCP `which_handler` for `ipc.learn.start_course` / `learn.start_course` | Pass: both resolve to `ipc.learn.start_course`, wired from `tauri/ui/src/learn/learn-window.ts` to `src/vibemix/learn/ipc_handlers.py` and `src/vibemix/ui_bus/learn_messages.py`. |
| MCP `which_handler` for `ipc.debrief.citation-summary` and `ipc.debrief.event-timeline` | Pass after prune: both report no matched IPC type, so they no longer ship as schema-looking ghosts. |
| `npm --prefix tauri/ui test -- tests/session/render-loop-actions.spec.ts tests/session/components.spec.ts tests/session/ws-bridge.recordings.spec.ts` | Pass: 3 files, 57 tests. |
| `npm --prefix tauri/ui test -- src/settings/components/citation-diagnostics.spec.ts tests/session/ws-bridge.recordings.spec.ts tests/settings/drawer.spec.ts` | Pass: 3 files, 40 tests. |
| `npm --prefix tauri/ui test -- src/settings/components/profile-panel.spec.ts src/settings/components/citation-diagnostics.spec.ts tests/settings/drawer.spec.ts tests/settings/staleness-banner.spec.ts tests/mock-transfer-contract.spec.ts` | Pass after Settings/Profile + staleness lifecycle fixes: 5 files, 68 tests. Confirms closed Settings boot/close no longer emits `ipc.profile.view`, open emits one request, stale profile replies are ignored after disposal, and `ipc.library.staleness_nudge` keeps one subscription across drawer refreshes. |
| `uv run pytest -q tests/runtime/test_dev_mcp_server.py tests/runtime/test_coach_progress_emit.py tests/runtime/test_coach_skill_credit.py` | Pass: 39 tests. |
| `uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py` | Pass: 36 tests after package-checklist cross-check; covers the previously unbundled creditability and Earned Wall refresh tests. |
| `uv run pytest -q tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py` | Pass: 41 tests for the mastered-vocal fixed-text path, no-speculative Learn imports, slop blocklist, citation-gated credit, and earned-wall refresh. |
| `uv run ruff check src/vibemix/runtime/coach.py src/vibemix/learn/mastered_vocal.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py` | Pass after sorting the mastered-vocal test imports. |
| `uv run pytest -q tests/library/test_ingest.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py` | Pass: 84 tests after locking the full semantic hot-cue slot map and the fallback slot order for unknown auto labels. |
| `uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/llm/test_model_router.py tests/audio/test_grid.py tests/audio/test_miniplayer.py tests/learn/test_beatmatch_judge.py` | Pass: 56 tests. |
| `uv run pytest -q tests/library/test_pricing.py tests/library/test_cost.py tests/llm/test_model_router.py` | Pass after 2026-05-31 source-audit cleanup: 37 tests. |
| `uv run pytest -q tests/e2e/test_phase_41_latency_stack_integration.py tests/repo/test_live_spike_scaffold.py tests/llm/test_model_router.py tests/library/test_pricing.py tests/library/test_cost.py` | Pass after spike-boundary cleanup: 62 tests. Confirms the 3.1 Flash Live model literal stays spike-only while router/pricing/cost retain the two shippable non-Live brain candidates. |
| `bash scripts/release/check_no_hardcoded_model.sh` | Pass: no hardcoded Gemini model literals in scanned paths outside `_router_config.py`. |
| `uv run ruff check src/vibemix/library/pricing.py tests/library/test_pricing.py` | Pass after pricing note/test cleanup. |
| `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3` | Pass: CLI prints the chosen live stack, TTS as dominant leg, €0.4857/session, €9.74/DJ-month, and €97,374 fleet/month. |
| `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3 --json > /tmp/vibemix-live-budget.json && uv run python -m json.tool /tmp/vibemix-live-budget.json` | Pass: JSON report parses cleanly and includes stack/assumptions/legs/totals/sensitivity. |
| `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts` | Pass: 2 files, 73 tests after hardening live-context merge against raw rejected deck-audio frames. |
| `uv run pytest -q tests/library/test_search.py tests/library/test_similar.py tests/scripts/test_cli_library_search.py tests/scripts/test_cli_library_similar.py` | Pass: 27 tests, covering the library command/CLI path that replaces the removed search/similar IPC shapes. |
| `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds` | Pass: 30 tests for the Rust library command bridge. |
| `uv run pytest -q tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_mood_change_envelope.py tests/ui_bus/test_citation_schema.py tests/ui_bus/test_overlay_schema.py` | Pass: 144 tests after pruning stale library/search IPC wrappers and debrief schema-only reservations. |
| `uv run ruff check src/vibemix/ui_bus/schemas/debrief.py src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/__init__.py scripts/check_ipc_schema.py tests/ui_bus/test_debrief_schemas.py tests/ui_bus/test_debrief_schema_additive_only.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_mood_change_envelope.py .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py` | Pass. |
| `uv run pytest -q tests/ui_bus/test_debrief_schemas.py tests/ui_bus/test_debrief_schema_additive_only.py tests/debrief/test_ws_server_progressive_emit.py` | Pass: 19 tests; confirms the shippable debrief schema baseline excludes the pruned reservations and the current server emits the implemented progressive frames plus tooltip/error behavior. |
| `npm --prefix tauri/ui run check:ipc` | Pass: regenerated IPC TS/validator and `tsc --noEmit` accepted the 72-type schema. |
| Source-only stale IPC ghost scan | Pass: no removed library/debrief IPC names, old 78-count sentinel, or old 79-count sentinel remain in compiled source, Tauri shell, scripts, repo guidance, or `.claude/skills`. The only remaining string hits are documentation and absence-guard tests. |
| `uv run pytest -q tests/ipc/test_learn_envelope_parity.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/ui_bus/test_citation_schema.py tests/ui_bus/test_overlay_schema.py` | Pass: 52 tests after focused IPC/UI-bus lint hygiene cleanup. |
| Targeted `uv run ruff check ... tests/ipc tests/ui_bus ...` | Pass after fixing the focused IPC/UI-bus test hygiene issues that the current package slice exposed. |
| `cargo check --manifest-path tauri/src-tauri/Cargo.toml` | Pass: Rust desktop shell still type-checks against the current IPC/library command surface. |
| `uv run python scripts/dist/check_sidecar_bundle_ready.py` | Pass: current bundled sidecar exists and carries a fresh embedded IPC schema. |
| `npm --prefix tauri/ui test -- tests/session/ws-bridge.recordings.spec.ts src/pill/index.test.ts src/pill/next-suggestion.test.ts src/library/api.test.ts src/library/chat.test.ts` | Pass: 5 files, 247 tests for websocket bridge, pill, and library UI surfaces. |
| `npm --prefix tauri/ui test -- tests/settings/drawer.spec.ts tests/session/components.spec.ts tests/session/render-loop-actions.spec.ts src/settings/components/profile-panel.spec.ts src/settings/components/citation-diagnostics.spec.ts` | Pass: 5 files, 94 tests for Settings, session components, diagnostics, and profile panel surfaces. |
| `uv run pytest -q tests/library tests/intel tests/ipc tests/ui_bus tests/prompts/test_filter.py tests/prompts/test_negative_dict.py tests/state/test_refresh.py tests/audio/test_deck_capture.py tests/midi/test_state.py tests/test_audio_macos.py tests/test_main_smoke.py` | Pass: 1487 passed, 1 skipped (`transformers` audio decode dependency absent), 1 xfailed (declared live-stack pricing decision). |
| `npm --prefix tauri/ui test -- src/debrief/__tests__/timeline-regions-click-seek.spec.ts src/debrief/__tests__/chapter-list.spec.ts src/debrief/__tests__/tldr-player.spec.ts src/debrief/__tests__/drills-panel-shape.spec.ts` | Pass: 4 files, 15 tests for the current chapter-list/timeline, TL;DR player, and drill-panel consumers. |
| `npm --prefix tauri/ui test -- tests/mock-transfer-contract.spec.ts` | Pass after contract refresh: 18 tests. The pre-fix failure showed `settings.group.diagnostics` and `ipc.error` / `ipc.session.citation` / `ipc.status.recheck` were missing from the mock-transfer registry. |
| `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts` | Pass: 1 file, 7 tests; confirms the generated Learn course projection exposes Course 2 `library_suggestions`. |
| `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts` | Pass: 2 files, 167 tests. |
| `npm --prefix tauri/ui run test:e2e:pill` | Pass on current dirty tree: 16 Playwright tests covering `DJ KNOWS`/`CARE` hover, keyboard completion, face-click completion, demo reactions, and reduced-motion reaction readability. |
| `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_operator_action.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts` | Pass after Learn screen-only highlight cleanup: 5 files, 55 tests; no false missing-highlight warnings for `headphone_cue:A` or `master_vol`. |
| `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts` | Pass after `ipc.learn.start_course` sender fix and Learn screen-only highlight cleanup: 1 file, 33 tests; the fallback test now asserts no false `[learn] highlight: control_id` warning for `headphone_cue:A` or `master_vol`. |
| `uv run ruff check docs/launch/.build_talking.py` | Pass after parameterizing the launch HTML helper. |
| `uv run python docs/launch/.build_talking.py --out /tmp/vibemix-konusan.html` | Pass: generated a 652 KB standalone Turkish talking-launch HTML without writing into the repo or `~/Downloads`. |
| `uv run python docs/launch/.build_talking.py --out /tmp/vibemix-konusan.html --check` | Pass: confirms the generated launch HTML is reproducible against the explicit output path. |
| `git check-ignore -v docs/launch/.vibemix-konusan.html docs/launch/.partner-capabilities.html docs/launch/.partner-capabilities-short.html` | Pass: generated launch preview HTML is ignored; source collateral stays stageable. |
| `npm --prefix tauri/ui run build` | Pass: TypeScript check and Vite build, 184 modules transformed. |
| `(git diff --name-only; git ls-files --others --exclude-standard) \| sort -u \| while ... rg -Fq ...` | Pass: every dirty tracked/untracked path is represented in `.planning/handoffs/2026-05-31-package-checklist.md`. |
| `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary` | Latest package-map pass after classifying `.planning/LEARN-MOAT-PLAN.md`, `src/vibemix/audio/deck_signal.py`, and `tests/audio/test_deck_signal.py`: 169 dirty paths are exactly listed as backticked paths in the package checklist; 3 generated launch previews are ignored; every dirty path is assigned to an Include/Hold lane. |
| `uv run pytest -q tests/scripts/test_check_dirty_package_plan.py` | Pass: 4 tests for package assignment parsing, shared assignments, Keep-out mentions, and strict assignment gaps. |
| `uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py` | Pass. |
| `uv run pytest -q tests/runtime/test_dev_mcp_server.py` | Pass after Package 1 `ws_trigger` fix: 23 tests; typed IPC now asserts ISO `date-time` timestamps and immediate reply capture. |
| `uv run ruff check src/vibemix/runtime/dev_mcp_server.py tests/runtime/test_dev_mcp_server.py scripts/check_dirty_package_plan.py` | Pass after replacing timeout aliases, import spacing, and the typed-IPC timestamp fix in Package 1. |
| `uv run pytest -q tests/runtime/test_drive_vibemix_ws_probe.py tests/runtime/test_dev_mcp_server.py` | Pass: 29 tests for the MCP helper and the `drive-vibemix` websocket probe helper. |
| `uv run ruff check .claude/skills/drive-vibemix/scripts/ws_probe.py tests/runtime/test_drive_vibemix_ws_probe.py src/vibemix/runtime/dev_mcp_server.py tests/runtime/test_dev_mcp_server.py` | Pass after adding schema-valid `ws_probe.py --ipc` support. |
| `uv run pytest -q tests/wizard/test_wizard_loop_ipc.py tests/runtime/test_session_loop.py tests/ui_bus/test_status_tick.py` | Pass: 46 tests after the runtime ingress compatibility shim; legacy numeric timestamps are normalized only at runtime ingress, while strict schema parsing still rejects numeric `ts`. |
| `uv run ruff check src/vibemix/ui_bus/validator.py src/vibemix/runtime/ws_bus.py src/vibemix/runtime/session_loop.py tests/wizard/test_wizard_loop_ipc.py tests/runtime/test_session_loop.py tests/ui_bus/test_status_tick.py` | Pass for the runtime ingress compatibility shim and focused tests. |
| `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session` plus MCP `sidecar_status` / `ws_observe` | Earlier 2026-05-31 source-mode pass: bus reachable on `127.0.0.1:8765`, MCP observed 30 Hz `ipc.session.snapshot` frames with idle zero-meter state. This was before installing local AI deps, so its missing `onnxruntime`/`tokenizers` warnings are superseded by the later ai-local proof below. |
| `uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}' --watch ipc.status.tick --seconds 3` | Fresh source-mode pass on 2026-05-31: schema-valid ISO `ts` frame returned `ipc.status.tick livekit=connecting gemini=down midi=0 screen=ok` with no schema violation in the sidecar log. MIDI is 0 because the DDJ/controller was not attached for this run. |
| `uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.profile.view --payload-json '{}' --watch ipc.profile.view_result --seconds 3` | Fresh source-mode pass on 2026-05-31: schema-valid profile request returned `ipc.profile.view_result` with stored profile fields. This proves the sidecar handler path, not the Tauri Settings drawer lifecycle. |
| Latest `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session` plus repo-local `ws_probe.py` after stale sidecar cleanup | Pass: current source diagnostic bus returned `ipc.status.tick livekit=connecting gemini=down midi=1 screen=ok`, then `ipc.profile.view_result`; the probe process was stopped and `127.0.0.1:8765` was left clear. |
| Connected-controller check | Pass: direct `mido.get_input_names()` and `uv run python scripts/sniff_controller.py --list` both reported `DDJ-FLX4`. The diagnostic `gemini=down` is the standalone `--session` loop's conservative default, not a missing-key proof for the flagless full live runtime. |
| `uv sync --group dev --extra ai-local` | Pass: installed declared local AI runtime wheels in the checkout (`onnxruntime`, `tokenizers`, `filelock`, `flatbuffers`, `fsspec`, `hf-xet`, `huggingface-hub`) with no tracked lockfile changes. |
| `uv run python -m vibemix library models --json` | Pass: CLAP ONNX and CUE-DETR are installed and `required_ready` / `all_ready` are both true. |
| `uv run pytest -q tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py` | Pass: 22 tests after the memory sqlite-vec dim reconciliation fix. |
| `uv run ruff check src/vibemix/memory/index_sqlite_vec_memory.py tests/memory/test_store_parity.py` | Pass. |
| `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session` after Package 12 | Bounded pass: boot logged the empty 768-dim `vec_memory` table being recreated at current `EMBEDDING_DIM=512`, opened `SqliteVecMemoryStore`, reached `127.0.0.1:8765`, and MCP observed seven `ipc.session.snapshot` frames. The previous sqlite-vec insert error did not recur. The close-time memory ingest kept running for about two minutes and was manually killed rather than left as a background process. |
| `uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py` | Pass: 34 tests after disabling CLAP memory ingest for sidecar-only `--session` probes. |
| `uv run ruff check src/vibemix/runtime/session_loop.py src/vibemix/memory/index_sqlite_vec_memory.py tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py` | Pass. |
| Follow-up `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session` after disabling diagnostic ingest | Pass: bus reached `127.0.0.1:8765`, MCP observed 58 `ipc.session.snapshot` frames in two seconds, Ctrl-C exited with `memory ingest (boot/close) skipped: disabled`, and no `--session` process remained. |
| `git diff --check` | Pass after package-checklist and runtime ingress documentation updates. |
| `uv run pytest -q tests/audio/test_xfade.py tests/audio/test_cues.py tests/runtime/test_automix_demo.py tests/state/test_transition_clock.py` | Pass: 36 tests for the tracked-clean mix/audio lane while leaving that lane isolated. |
| `uv run python scripts/automix_demo_smoke.py --dry-run` | Pass: printed the synthetic tone transition plan and reaction reel without opening audio. |
| `uv run python scripts/automix_demo_smoke.py --dry-run --outro-start 24 --intro-start 4` | Pass: after the active mix-lane update, the smoke helper printed a `fade_at_outro_start` reaction reel without opening audio. |
| `uv run ruff check scripts/automix_demo_smoke.py` | Pass. |
| `uv run pytest -q tests/audio/test_cues.py tests/runtime/test_automix_demo.py` | Pass: 12 tests. |
| Stale IPC ghost scan across source/Tauri/tests/scripts plus `tauri/src-tauri/target` | Initial fail: removed IPC ghosts only survived in ignored generated sidecar/Tauri outputs, including `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/_internal/tauri/ui/src/ipc/messages.schema.json`, old target app resources, and `tauri/src-tauri/target/release/messages.schema.json`. |
| `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only` | Initial fail after adding the guard: the bundled Apple Silicon sidecar IPC schema was stale; after rebuilding the sidecar it passed. |
| `uv run pytest -q tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py` | Pass: 20 tests after adding stale/missing embedded IPC schema checks to the sidecar package-readiness gate. |
| `uv run ruff check scripts/dist/check_sidecar_bundle_ready.py tests/install/test_sidecar_bundle_ready.py` | Pass. |
| `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec` | Pass: rebuilt `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/` and scanned 402 bundled files with no AIza-pattern leak. |
| Re-run stale IPC ghost scan after sidecar rebuild and deleting ignored old target outputs | Pass: no stale `ipc.debrief.citation-summary`, `ipc.debrief.event-timeline`, `ipc.library.search`, `ipc.library.search_result`, `ipc.library.confidence`, `ipc.library.similar_request`, or `ipc.library.similar_result` strings remain in source, Tauri resource inputs, tests, scripts, or remaining target outputs. |
| Tauri sidecar launch-decision tests | Pass: `cargo test --manifest-path tauri/src-tauri/Cargo.toml resolve_sidecar_flag_set_default_uses_uv_module_vibemix`, `resolve_sidecar_wizard_arg_appended_in_both_arms`, and `resolve_sidecar_flag_absent_returns_bundled` each passed. This confirms the full live app path is flagless `python -m vibemix`, with `--wizard` appended only for wizard mode. |
| `uv run pytest -q tests/test_main_smoke.py::test_close_tts_chain_closes_nested_providers_once tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams` | Pass: 2 tests. The shutdown regression now covers nested TTS providers plus a shared owned HTTP session, closing each exactly once. |
| `uv run ruff check src/vibemix/__main__.py tests/test_main_smoke.py` | Pass after the live TTS shutdown cleanup. |
| Full flagless live runtime with DDJ connected, session `20260531-102305` | Pass: `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix` reached `127.0.0.1:8765`, loaded `SqliteVecStore`, selected `DDJ-FLX4` with `profile=pioneer_ddj_flx4`, opened `BlackHole 16ch` as 4-channel deck-pair capture, and `ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}'` returned `ipc.status.tick livekit=ok gemini=ok midi=1 screen=unavailable`. A manual trigger produced `AI_SPOKE="I'm not hearing anything right now, booth's quiet."`, `cohost=TALKING`, voice-meter activity, and `events.jsonl` lines with `controller_connection=connected`, `deck_audio_activity=A_silent+B_silent`, `deck_audio_parts_skipped` reason `deck_audio_silent`, `citation_count:0`, and `llm_to_tts_delta_ms=1977`. Shutdown reached `-> bye` with no `Unclosed client session` warning after the `_close_tts_chain()` fix. |
| First Tauri dev-source proof, session `20260531-102701` | Found a real split: `VIBEMIX_DEV_SIDECAR=1 cargo tauri dev --no-watch` brought up the renderer/Rust bridge/pill path and `livekit=ok gemini=ok midi=1`, but `events.jsonl` recorded `capture_device=BlackHole_2ch`, `opened_channels=2`, `capture_device_too_few_channels`, and `deck_audio_parts_skipped: no_deck_audio_buffers`. Cause: Tauri's default `VIBEMIX_AUTO_MASTER_INPUT=1` made the explicit 16ch upgrade probe route through auto-master fallback. |
| `uv run pytest -q tests/test_audio_macos.py::test_find_device_auto_master_input_honors_explicit_blackhole_variant tests/test_audio_macos.py::test_find_device_auto_master_input_chooses_live_48k_variant tests/test_audio_macos.py::test_find_device_auto_master_input_falls_back_to_48k_variant_when_silent tests/test_main_smoke.py::test_deck_audio_auto_upgrades_default_blackhole_input tests/test_main_smoke.py::test_deck_audio_global_default_upgrades_blackhole_without_env` | Pass: 5 tests after making auto-master honor explicit `BlackHole 16ch` lookup. |
| `uv run ruff check src/vibemix/platform/_audio_macos.py tests/test_audio_macos.py src/vibemix/__main__.py tests/test_main_smoke.py` | Pass. |
| Post-fix Tauri dev-source proof, session `20260531-103122` | Pass: renderer/Rust bridge/pill booted, UI log received `ipc.status.tick livekit=ok gemini=ok midi=1`, `ipc.learn.midi_position`, `ipc.session.cohost-reaction`, pill reaction/expand, and voice-meter frames. Sidecar log showed `deck audio auto: upgraded input device 'BlackHole 2ch' -> 'BlackHole 16ch' (4ch)` and `listening to BlackHole 16ch @ 48000Hz (4ch)`. `events.jsonl` recorded `requested_device=BlackHole_16ch`, `input_channels=16`, `opened_channels=4`, `mode=deck_pair_capture_configured`, `deck_audio_parts_skipped: deck_audio_silent`, and real jog/play MIDI evidence. Ports `1420`, `8765`, and `8766` were clear after shutdown. |
| `uv run pytest -q tests/audio/test_deck_capture.py tests/midi/test_state.py::test_control_touched_snapshot_tracks_real_absolute_controls_only tests/state/test_deck_context.py::test_deck_audio_separation_context_marks_configured_deck_pair_capture tests/runtime/test_ws_bus_deck_state.py::test_payload_marks_configured_deck_pair_capture tests/runtime/test_ws_bus_deck_state.py::test_configured_deck_pair_capture_forces_audio_window_on_silent_frame` | Pass: 18 tests after adding controller-weighted deck-pair master synthesis, boot-default touched-control handling, and `master_source=controller_weighted_deck_pairs` evidence. |
| `uv run pytest -q tests/midi/test_state.py tests/midi/test_profile_flx4_golden.py tests/test_midi_common.py tests/audio/test_deck_capture.py` | Pass: 52 tests, 6 expected deprecation warnings from legacy string-port listener shims. Confirms `ControllerState.deck_snapshot()` golden behavior stayed byte-compatible while `control_touched_snapshot()` was added. |
| `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/midi/state.py src/vibemix/__main__.py src/vibemix/state/deck_context.py tests/audio/test_deck_capture.py tests/midi/test_state.py tests/state/test_deck_context.py` | Pass. |
| Fresh full flagless runtime after controller-weighted deck-pair patch, session `20260531-104819` | Pass: `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix` reached `127.0.0.1:8765`, selected `DDJ-FLX4`, opened `BlackHole 16ch` as 4ch, and MCP `ws_observe` saw live frames with `deck_audio_separation_context[...] master_source=controller_weighted_deck_pairs ... deck_audio_activity=A_silent+B_silent`. No Rekordbox audio was present in the run, so this proves boot/callback/context health but not audible Deck B routing. Shutdown reached `-> bye`. |
| Stale packaged sidecar cleanup plus clean source-mode probe, session `20260531-105418` | Pass: found `/Applications/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin` still holding `127.0.0.1:8765` as PID `16329`; normal `SIGTERM` did not stop it, `SIGKILL` did, and ports `8765`, `8766`, and `1420` were clear. A fresh `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session` then owned `8765`, MCP observed 58 `ipc.session.snapshot` frames in two seconds, `ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}' --watch ipc.status.tick --seconds 3` returned `ipc.status.tick livekit=connecting gemini=down midi=1 screen=ok`, and Ctrl-C shutdown left all three ports clear again. |
| Installed-app shadow audit | Pass with caution: `/Applications/vibemix.app` and `/Applications/Vibemix.app` resolve to the same bundle inode (`53624733`), signed as `world.bravoh.vibemix` version `0.0.1`, timestamped 2026-05-30 20:58:55. Its embedded sidecar hash is `9f19207de84b0b374a8392c7455162bdb2c6354f`, while the repo sidecar bundle is `944893788f78953da5a5063cd9379c83466e5c07`, so opening the installed app can run stale sidecar logic. `launchctl list` and `~/Library/LaunchAgents` / system LaunchAgents / LaunchDaemons had no Vibemix/Bravoh entries, and Dock persistent apps had no Vibemix entry, so the remaining risk is manual app launch rather than auto-start. |
| Current-source Tauri/Rekordbox probe, session `20260531-110001` | Found the live complaint shape. `VIBEMIX_DEV_SIDECAR=1 cargo tauri dev --no-watch` owned `127.0.0.1:8765`/`1420`, opened `BlackHole 16ch` with `opened_channels=4`, and heard Rekordbox audio only on channels `0/1`: `deck_audio_activity=A_active+B_silent`. Two `say`-prompted raw-MIDI probes against CoreMIDI input `DDJ-FLX4` produced `raw_midi_count=0`; the websocket also produced `ipc.learn.midi_position=0` and `midi_events=0` while the bus badge still said `midi=1`. Conclusion: the Rekordbox setup exposes a MIDI port but is not sending mixer/EQ/crossfader messages to CoreMIDI, and the auto Rekordbox route hint was not live proof of isolated Deck A/B audio. |
| `uv run pytest -q tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py` | Pass: 120 tests after adding the auto-Rekordbox deck-pair verification gate. |
| `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/audio/deck_signal.py src/vibemix/state/deck_context.py tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/state/test_deck_context.py` | Pass after the same verification-gate patch. |
| Patched Tauri/Rekordbox proof, session `20260531-111154` | Pass for the new honesty behavior: fresh current-source Tauri run booted on `8765`/`1420`; idle frames showed `mode=deck_pair_capture_unverified`, `per_deck_audio=unverified_not_attached`, `isolated_decks=false`, and `active_sides_seen=none`. A `say`-prompted Deck 2-only probe then saw audio on the first pair only (`A_active+B_silent`) but kept `mode=deck_pair_capture_unverified`, `isolated=false`, and `active_sides_seen=A` rather than treating channels `0/1` as verified Deck A or calling Deck B truly silent. Raw `DDJ-FLX4` MIDI remained `0`, so mixer/EQ/crossfader control still needs a Rekordbox/controller input solution. |
| `git diff --check` | Latest pass after the Rekordbox honesty patch and package documentation refresh. |
| `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary` | Latest pass: 169 dirty paths exactly listed in the package checklist, 3 generated launch previews ignored, and every dirty path assigned to an Include/Hold lane. |
| `uv run python scripts/check_ipc_schema.py` | Latest pass: 72 wrapper dataclasses validate against 72 `oneOf` schema entries; Settings enum/payload parity remains OK. |
| `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts src/library/api.test.ts src/library/chat.test.ts` | Latest pass: 4 files, 240 tests for pill and library UI surfaces. |
| `npm --prefix tauri/ui test -- tests/settings/drawer.spec.ts tests/session/components.spec.ts tests/session/render-loop-actions.spec.ts src/settings/components/profile-panel.spec.ts src/settings/components/citation-diagnostics.spec.ts` | Latest pass: 5 files, 94 tests for Settings, session components/actions, diagnostics, and profile panel surfaces. |
| `uv run pytest -q tests/library tests/intel tests/ipc tests/ui_bus tests/prompts/test_filter.py tests/prompts/test_negative_dict.py tests/state/test_refresh.py tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/midi/test_state.py tests/test_audio_macos.py tests/test_main_smoke.py` | Latest pass: 1593 passed, 1 skipped (`transformers` audio decode dependency absent), 1 xfailed (declared live-stack pricing decision). |
| Dirty-package Python Ruff sweep: `git status --short --untracked-files=all \| awk '{print $2}' \| rg '\\.py$' \| xargs uv run ruff check` | Pass: every dirty Python file in the current package set is Ruff-clean. |
| `npm --prefix tauri/ui run build` | Latest pass: TypeScript check and Vite build, 184 modules transformed. |
| `cargo check --manifest-path tauri/src-tauri/Cargo.toml` | Latest pass: Rust desktop shell type-checks against the current Tauri command and sidecar bridge surface. |
| `uv run python scripts/dist/check_sidecar_bundle_ready.py` | Latest pass: bundled Apple Silicon sidecar is present and carries the expected embedded IPC schema. |
| `uv run ruff check src tests` | Known repo-wide lint debt, not green: 351 existing findings across older source/tests, mostly import/noqa/unused cleanup plus a clean-source `src/vibemix/library/codex_curate.py` return-annotation issue. The dirty-package Python sweep above is the current shippable package boundary. |
| `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py` | Latest pass: 72 message types declared; 72 shell references, 72 sidecar references, 6 Rust passthrough references; no one-ended IPC type. |
| `npm --prefix tauri/ui run check:ipc` | Latest pass: regenerated `tauri/ui/src/ipc/messages.ts` and `tauri/ui/src/ipc/validator.generated.mjs`, then `tsc --noEmit` passed. |
| `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only` | Latest pass: packaged sidecar preflight accepted the current Apple Silicon bundle. |
| Narrow removed-IPC ghost scan over shippable paths | Latest pass: no `ipc.debrief.citation-summary`, `ipc.debrief.event-timeline`, `ipc.library.search`, `ipc.library.search_result`, `ipc.library.confidence`, `ipc.library.similar_request`, or `ipc.library.similar_result` hits in `src`, `tauri/src-tauri`, `tauri/ui/src`, `tauri/ui/tests`, `tests`, `scripts`, or `.claude` after excluding ignored `.claude/worktrees/**`. |
| Ignored Claude worktree shadow scan | Found local-only stale logic: 22 registered `.claude/worktrees/agent-*` worktrees, 7.8 GB total, locked to dead PIDs `22077` / `30357`, all dirty, and each still contains 7 files with removed IPC contracts. They are ignored by normal Git/rg and are not shippable inputs, but broad `rg --no-ignore` scans must exclude `.claude/worktrees/**`; do not delete without accepting loss of uncommitted agent work. `git worktree prune --expire now` removed the missing `/private/tmp/sv-100-reviewfix-pi5Z2Y` metadata. |
| Latest local runtime shadow scan | No listeners on `8765`, `8766`, or `1420`; no `cargo tauri`, `python -m vibemix`, `vibemix-core`, or installed-app runtime process. Multiple `vibemix.runtime.dev_mcp_server` / `vibemix.library.mcp_server` helper children exist but are not the live app and do not own those product ports. |
| Latest installed-app shadow scan | `mdfind` sees only `/Applications/vibemix.app`; `/Applications/Vibemix.app` is the same inode `53624733`. Installed sidecar hash is still `9f19207de84b0b374a8392c7455162bdb2c6354f` vs repo bundle `944893788f78953da5a5063cd9379c83466e5c07`; LaunchAgents, LaunchDaemons, `launchctl`, and `sfltool dumpbtm` had no Vibemix/Bravoh hits. Do not open the installed app for live proof. |
| `uv run python scripts/learn_live_readiness.py --require none --loopback-signal-seconds 1 --capture-matrix-seconds 1 --out /tmp/vibemix-live-readiness-now.json` | Latest pre-controller-readiness pass with blockers: DDJ-FLX4 visible, Rekordbox running, BlackHole 16ch present at 48 kHz, but current Rekordbox audio settings report `audio_output_device_name=DDJ-FLX4` and `audio_input_device_name=DDJ-FLX4`; BlackHole 16ch direct capture was silent (`rms=0.0`, `peak=0.0`), and all sampled capture-matrix rows were below signal floor. Human-side route change required before the final proof. |
| `uv run python scripts/export_learn_curriculum_meta.py --check` | Pass. |
| `uv run pytest -q tests/learn/test_curriculum_projection.py` | Pass: 4 tests; confirms the frontend curriculum metadata is generated from the Python projection. |

### Low-Risk Fixes Landed During Triage

| Area | Files and lines | Result |
|---|---|---|
| `ipc.status.recheck` | `tauri/ui/src/session/SessionLayout.ts:42`, `tauri/ui/src/session/SessionLayout.ts:94-103`, `tauri/ui/src/session/SessionLayout.ts:623-641`, `tauri/ui/src/session/SessionLayout.ts:917-921`, `tauri/ui/src/session/SessionLayout.ts:986-999`, `tauri/ui/src/session/SessionLayout.ts:1151-1158`, `tauri/ui/src/session/SessionLayout.ts:1202-1211`; `tauri/ui/src/session/render-loop.ts:64-74`, `tauri/ui/src/session/render-loop.ts:359-367`, `tauri/ui/src/session/render-loop.ts:556-560`; tests at `tauri/ui/tests/session/render-loop-actions.spec.ts:45-52` and `tauri/ui/tests/session/components.spec.ts:761-783`. | The live deck status row now exposes real down-state recheck buttons for audio, AI, screen, and MIDI, and routes them to the existing sidecar status probe. |
| Runtime ingress legacy timestamp compatibility | `src/vibemix/ui_bus/validator.py:37-60`, `src/vibemix/runtime/ws_bus.py:45-48`, `src/vibemix/runtime/ws_bus.py:1288-1293`, `src/vibemix/runtime/session_loop.py:82`, `src/vibemix/runtime/session_loop.py:1320-1324`; tests at `tests/wizard/test_wizard_loop_ipc.py:183-223`, `tests/runtime/test_session_loop.py:395-415`, and `tests/ui_bus/test_status_tick.py:116-121`. | Runtime websocket/session ingress now converts finite numeric `ts` values from older local drive tools into ISO `date-time` strings before schema validation. The strict parser and generated schema still reject numeric timestamps outside that ingress boundary. |
| `ipc.error` | `tauri/ui/src/session/ws-bridge.ts:33-43`, `tauri/ui/src/session/ws-bridge.ts:108-111`, `tauri/ui/src/session/ws-bridge.ts:223-230`, `tauri/ui/src/session/ws-bridge.ts:483-490`; test at `tauri/ui/tests/session/ws-bridge.recordings.spec.ts:77-86`. | Sidecar error broadcasts now land in the `[vmx:error]` operator log instead of disappearing. |
| `ipc.session.citation` | `tauri/ui/src/session/ws-bridge.ts:33-45`, `tauri/ui/src/session/ws-bridge.ts:115-119`, `tauri/ui/src/session/ws-bridge.ts:242-245`, `tauri/ui/src/session/ws-bridge.ts:507-517`; `tauri/ui/src/settings/components/citation-diagnostics.ts:1-24`, `tauri/ui/src/settings/components/citation-diagnostics.ts:182-219`; `tauri/ui/src/settings/SettingsDrawer.ts:61`, `tauri/ui/src/settings/SettingsDrawer.ts:1094-1105`; tests at `tauri/ui/src/settings/components/citation-diagnostics.spec.ts:234-263`, `tauri/ui/tests/session/ws-bridge.recordings.spec.ts:101-116`, and `tauri/ui/tests/settings/drawer.spec.ts:96-100`. | Co-host anti-slop telemetry now reaches a live Settings diagnostics row without routing 0.5Hz updates through full drawer rebuilds. |
| Settings/Profile lifecycle | `tauri/ui/src/settings/SettingsDrawer.ts:647-659`, `tauri/ui/src/settings/SettingsDrawer.ts:694-700`, `tauri/ui/src/settings/SettingsDrawer.ts:762-815`, `tauri/ui/src/settings/SettingsDrawer.ts:1108-1120`; `tauri/ui/src/settings/components/profile-panel.ts:45-50`, `tauri/ui/src/settings/components/profile-panel.ts:382-392`; tests at `tauri/ui/src/settings/components/profile-panel.spec.ts:103-145` and `tauri/ui/tests/settings/drawer.spec.ts:191-202`. | The Settings drawer no longer emits `ipc.profile.view` while closed, open/recordings refresh does not duplicate the profile request, and disposed profile views ignore late replies instead of rewriting stale detached DOM. This turns the UI-log `ipc.profile.view_result` timeouts into an honest "bus down while opened" signal instead of boot/close spam. |
| Settings/Library staleness lifecycle | `tauri/ui/src/settings/SettingsDrawer.ts:762-815`, `tauri/ui/src/settings/SettingsDrawer.ts:1073-1082`; test at `tauri/ui/tests/settings/drawer.spec.ts:205-218`. | The library staleness banner keeps one `ipc.library.staleness_nudge` subscription for the drawer lifetime, so boot/open/close refreshes can still catch a stale-library nudge without multiplying subscriptions in the UI log. |
| Mock-transfer contract refresh | `tauri/ui/src/mock-transfer/contract.ts:327-340`, `tauri/ui/src/mock-transfer/contract.ts:406-423`; test at `tauri/ui/tests/mock-transfer-contract.spec.ts:313-369`. | The mock-transfer registry now contracts the live Settings diagnostics group and the session runtime `ipc.error`, `ipc.session.citation`, and `ipc.status.recheck` channels, keeping visual-transfer gates in sync with the new session diagnostics wiring. |
| IPC count guidance | `AGENTS.md:101-106`; `.claude/skills/ipc-wiring-checker/SKILL.md:10-13`; `.claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py:6-9`. | The repo guidance now reflects the verified current IPC count: 72. |
| `ipc.learn.start_course` | `tauri/ui/src/learn/learn-window.ts:225-237`, `tauri/ui/src/learn/learn-window.ts:624-642`, `tauri/ui/src/learn/learn-window.ts:751-754`, `tauri/ui/src/learn/learn-window.ts:1354-1383`; test at `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts:545-567`. | The Learn shell now has a narrow `learn.start_course` automation hook that normalizes canonical curriculum IDs into schema-valid course aliases and emits `ipc.learn.start_course`; the stale comment now matches the real sender. |
| Learn screen-only fallback controls | `tauri/ui/src/learn/learn-window.ts:220-224`, `tauri/ui/src/learn/learn-window.ts:588-595`, `tauri/ui/src/learn/learn-window.ts:1247-1249`; test at `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts:1597-1629`. | `headphone_cue`, `master_vol`, and `lesson_continue` are now treated as explicit screen-only lesson controls in the shell, so they show the fallback action without emitting false missing-SVG highlight warnings. |
| Stale library search/similar IPC pruning | `tauri/ui/src/ipc/messages.schema.json:151-164`, `tauri/ui/src/ipc/messages.schema.json:2414-2595`; generated TS at `tauri/ui/src/ipc/messages.ts:55-59`, `tauri/ui/src/ipc/messages.ts:641-656`; Python payloads at `src/vibemix/ui_bus/schemas/library.py:14-16`, `src/vibemix/ui_bus/schemas/library.py:24-89`; wrappers/imports at `src/vibemix/ui_bus/messages.py:50-56`, `src/vibemix/ui_bus/messages.py:1823-1858`; exports at `src/vibemix/ui_bus/__init__.py:102-112`, `src/vibemix/ui_bus/__init__.py:307-316`; count/schema tests at `tests/ipc/test_library_schemas.py:23-29`, `tests/ipc/test_library_schemas.py:47-63`, `tests/ipc/test_library_schemas.py:158-178`, `tests/ui_bus/test_messages_schema.py:77-81`, `tests/ui_bus/test_messages_schema.py:436-442`, `tests/ui_bus/test_messages_schema.py:689-720`, `tests/ui_bus/test_recordings_messages.py:267-328`, and `tests/ui_bus/test_mood_change_envelope.py:172-175`; command-path docs at `src/vibemix/library/search.py:93-99`, `src/vibemix/library/similar.py:4-12`, and `src/vibemix/library/budget.py:9-14`. | Removed the five false `ipc.library.search/search_result/confidence/similar_request/similar_result` contracts instead of wiring a second search stack. The shippable library search/similar path remains the existing Tauri command bridge. |
| Stale sidecar IPC schema guard | `scripts/dist/check_sidecar_bundle_ready.py:20-22`, `scripts/dist/check_sidecar_bundle_ready.py:71-76`, and `scripts/dist/check_sidecar_bundle_ready.py:137-151`; tests at `tests/install/test_sidecar_bundle_ready.py:19-49` and `tests/install/test_sidecar_bundle_ready.py:61-90`. | The local Tauri package-readiness gate now compares the bundled sidecar's embedded IPC schema with `tauri/ui/src/ipc/messages.schema.json` and fails stale/missing embedded schemas, forcing a sidecar rebuild before a Tauri package can ship stale bus contracts. |
| Live TTS shutdown hygiene | `src/vibemix/__main__.py:210-241`, `src/vibemix/__main__.py:2366-2373`; test at `tests/test_main_smoke.py:673-704`. | Shutdown now closes the live TTS adapter, nested provider instances, and provider-owned HTTP sessions such as Cartesia's supplied `aiohttp.ClientSession`. The first full live rerun reproduced `Unclosed client session`; the post-fix full live rerun with Cartesia speech exited cleanly. |
| Auto-master explicit BlackHole variant | `src/vibemix/platform/_audio_macos.py:598-607`; test at `tests/test_audio_macos.py:383-412`. | Tauri's `VIBEMIX_AUTO_MASTER_INPUT=1` no longer hijacks an explicit `BlackHole 16ch` lookup. This lets the runtime's deck-pair auto-upgrade probe resolve the real 16ch input even when the startup master probe falls back to silent `BlackHole 2ch`. |
| Controller-weighted and verified deck-pair master | `src/vibemix/audio/deck_capture.py:93`, `src/vibemix/audio/deck_capture.py:119-181`, `src/vibemix/audio/deck_capture.py:183-195`, `src/vibemix/audio/deck_signal.py:31-39`, `src/vibemix/state/deck_context.py:175-197`, `src/vibemix/state/deck_context.py:886-902`, and `src/vibemix/state/deck_context.py:955-974`; callback wiring at `src/vibemix/__main__.py:505-545` and `src/vibemix/__main__.py:2336-2347`; touched-control tracking at `src/vibemix/midi/state.py:169-170`, `src/vibemix/midi/state.py:327`, `src/vibemix/midi/state.py:345`, and `src/vibemix/midi/state.py:435-447`; tests at `tests/audio/test_deck_capture.py:116-181`, `tests/audio/test_deck_capture.py:293-412`, `tests/audio/test_deck_signal.py:23-70`, `tests/midi/test_state.py:105-115`, and `tests/state/test_deck_context.py:1356-1410`. | Rekordbox deck-pair capture no longer treats raw Deck A+B channels as a real post-mixer master once controller posture is observed. Auto-read Rekordbox deck-pair hints also stay unverified until live audio has shown activity on both configured pairs at least once; until then the Judge and prompt context stay honest-null for isolated lanes, while manual `VIBEMIX_DECK_AUDIO_CHANNELS=A=...;B=...` maps remain operator-trusted. |
| IPC/UI-bus lint hygiene | `tests/ipc/test_learn_envelope_parity.py:53-55`, `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py:27-29`, `tests/ui_bus/test_citation_schema.py:150-159`, and `tests/ui_bus/test_overlay_schema.py:212-220`. | The current IPC/UI-bus package slice is Ruff-clean: late validator imports keep the expected spacing, and frozen dataclass mutation assertions catch the concrete `AttributeError` instead of a blind `Exception`. |

IPC staging note: Package 2 and Package 3 share schema/codegen/count-test files.
If staged separately, the schema/generated TS/Python wrapper/count-test set must
travel with the package that changes the IPC baseline. The intentional current
baseline is 72 top-level IPC message types.

### Pruned Wiring Pain Point

| Type(s) | Evidence | Packaging decision needed |
|---|---|---|
| Former `ipc.debrief.citation-summary`, `ipc.debrief.event-timeline` | Removed from Python payloads at `src/vibemix/ui_bus/schemas/debrief.py:2-18`, Python wrapper imports and dataclasses at `src/vibemix/ui_bus/messages.py:37-47` and `src/vibemix/ui_bus/messages.py:1501-1540`, package exports at `src/vibemix/ui_bus/__init__.py:84-92`, `src/vibemix/ui_bus/__init__.py:188-198`, and `src/vibemix/ui_bus/__init__.py:281-298`, schema `oneOf`/definitions at `tauri/ui/src/ipc/messages.schema.json:124-144` and `tauri/ui/src/ipc/messages.schema.json:2110-2185`, generated TS at `tauri/ui/src/ipc/messages.ts:46-52` and `tauri/ui/src/ipc/messages.ts:491-524`, schema parity examples at `scripts/check_ipc_schema.py:47-54` and `scripts/check_ipc_schema.py:316-345`, absence guard at `tests/ui_bus/test_debrief_schema_additive_only.py:23-28` and `tests/ui_bus/test_debrief_schema_additive_only.py:131-139`, shippable debrief wrapper tests at `tests/ui_bus/test_debrief_schemas.py:25-72`, and empty reservation allowlist at `.claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py:76-79`. MCP `which_handler` now reports no matched IPC type for both old names. | Treat citation-summary/event-timeline as future product work, not an exported IPC contract. Re-add only with producer data, renderer behavior, schema/codegen/count tests, and wiring proof in the same package. |

### Next Live Verification Path

MCP readiness probe on 2026-05-31:

- First `sidecar_status` found no listener on `ws://127.0.0.1:8765`.
- A source-mode diagnostic launch with `uv run python -m vibemix --session`
  then reached `127.0.0.1:8765`, advertised 12 wizard-bus handlers, and streamed
  idle `ipc.session.snapshot` frames observed by MCP `ws_observe`.
- A schema-valid websocket client proved two handler paths: `ipc.status.recheck`
  for MIDI returned an `ipc.status.tick`, and `ipc.profile.view` returned
  `ipc.profile.view_result` with consent/profile data.
- A stale already-running MCP `ws_trigger` child still emitted numeric `ts`; current
  source normalized it at runtime ingress, and the diagnostic bus did not log the
  previous schema violation.
- Current-source `tool_ws_trigger_async` now sends typed IPC with an ISO
  `date-time` `ts` and returns immediate same-socket replies. A live diagnostic
  probe sent `ipc.status.recheck` for MIDI and received `ipc.status.tick`.
  Restart the MCP host before the long run so the callable `ws_trigger` tool
  process loads this fixed implementation and reports immediate replies.
- Fresh 2026-05-31 rerun: source-mode `--session` reached `127.0.0.1:8765`;
  MCP `ws_observe` saw idle `ipc.session.snapshot` frames; repo-local
  `ws_probe.py --ipc ipc.status.recheck` received
  `ipc.status.tick livekit=connecting gemini=down midi=0 screen=ok`; and
  `ws_probe.py --ipc ipc.profile.view` received `ipc.profile.view_result`.
  The DDJ was not attached, so `midi=0` is expected for this proof.
- Latest 2026-05-31 re-probe after stale sidecar cleanup: repo-local
  `ws_probe.py --ipc ipc.status.recheck` received
  `ipc.status.tick livekit=connecting gemini=down midi=1 screen=ok`, so the
  diagnostic bus now sees the controller path; `ipc.profile.view` also returned
  `ipc.profile.view_result`. The probe process was stopped and port `8765` was
  clear afterward.
- Connected-controller proof: direct Python MIDI enumeration and
  `scripts/sniff_controller.py --list` both reported `DDJ-FLX4`.
- Diagnostic `gemini=down` is scoped to the standalone `--session` probe. The
  Tauri sidecar launch-decision tests confirm the real post-wizard live path is
  flagless `uv run python -m vibemix`, which enters `main()` and uses
  `ws_broadcast` for live status.
- The callable MCP `ws_trigger` process still emitted a numeric `ts` in this
  already-running Codex session. Current source normalized it without a schema
  violation, but restart the MCP host before treating the callable tool as the
  fixed ISO-sender implementation.
- The documented `drive-vibemix` `ws_probe.py --ipc` path now sends schema-valid
  typed IPC too; a live diagnostic probe for MIDI status printed
  `ipc.status.tick livekit=connecting gemini=down midi=1 screen=ok`.
- The missing local CLAP runtime gap is closed: `uv sync --group dev --extra
  ai-local` installed `onnxruntime` and `tokenizers`, and `uv run python -m
  vibemix library models --json` reports CLAP ONNX plus CUE-DETR ready.
- The first post-dependency source boot exposed a real stale-store blocker:
  durable `memory.db` had an empty `vec_memory` table declared as
  `embedding FLOAT[768]`, while current CLAP emits 512-d vectors. Package 12
  fixes the empty-table self-heal path and falls back instead of wiping a
  populated stale table.
- The Package 12 bounded rerun proved the self-heal in source mode: boot logged
  stale-table recreation, opened `SqliteVecMemoryStore`, and served snapshot
  frames on `127.0.0.1:8765` without the earlier dimension-mismatch insert error.
  The same run exposed that diagnostic `--session` could accidentally start CLAP
  memory indexing on close. Package 12 now disables memory ingest for that
  sidecar-only probe, and the follow-up MCP run exited cleanly after Ctrl-C.
- `GEMINI_API_KEY` was present via the project `.env`; this removes the most
  common brain-mute cause for the next full live run.
- The MCP child's own `VIBEMIX_DEV_SIDECAR` flag was false; this reflects the
  MCP server environment, not the launched diagnostic process.
- `which_handler("ipc.learn.start_course")`: now reports `WIRED (both ends)`
  with shell code in `tauri/ui/src/learn/learn-window.ts` and sidecar code in
  `src/vibemix/learn/ipc_handlers.py` /
  `src/vibemix/ui_bus/learn_messages.py`.
- `which_handler("ipc.library.search")`: now returns no matched IPC type,
  confirming the stale library search bus shape was removed. The product path
  remains the Tauri command bridge tested by UI, CLI, and Rust command tests.
- Full flagless runtime proof with the connected DDJ is now covered by session
  `20260531-102305`: the runtime reported `DDJ-FLX4`, `profile=pioneer_ddj_flx4`,
  `livekit=ok`, `gemini=ok`, `midi=1`, and `screen=unavailable`; manual trigger
  produced a spoken response and `events.jsonl` recorded `controller_connection=connected`.
  The deck feed was silent, so `citation_count:0`, `deck_audio_parts_skipped:
  deck_audio_silent`, and `grounded=False` are the expected honest state, not a
  brain-mute signature. Shutdown after Cartesia speech exited without the earlier
  `Unclosed client session` warning.
- Tauri dev-source proof is now covered by session `20260531-103122`: the webview
  mounted, Rust bridge connected, pill received status/reaction frames, Learn
  received `ipc.learn.midi_position`, and the sidecar upgraded from `BlackHole 2ch`
  to `BlackHole 16ch` before opening a 4-channel capture. The earlier Tauri
  session `20260531-102701` is the regression artifact for the now-fixed
  auto-master/16ch split.

Use the project `drive-vibemix` skill once hardware is available: launch with
`VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`, attach as a client to
`127.0.0.1:8765`, drive a status recheck and a co-host reaction, then inspect
the UI log and session `events.jsonl`. No actual in-window click interaction,
co-host citation, `ipc.error` rendering, audible-deck route, or DDJ/controller
long-set run was performed in this audit pass.

## Lane 0: Shipping Inventory Docs

Purpose: make the dirty-tree split reviewable and enforceable before staging
product packages.

### Code And Docs Line Map

| File | Lines | What changed |
|---|---:|---|
| `.planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md` | 1-20 | Top-level inventory purpose, line-anchor caveat, and pointer to the package checklist. |
| `.planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md` | 64-195 | Audit update, partial diagnostic bus proof, schema-valid handler checks, `ws_trigger`/`ws_probe` fix proof, runtime ingress shim proof, and remaining full-live gate. |
| `.planning/handoffs/2026-05-31-package-checklist.md` | 1-20 | Guardrails for non-GSD, non-beginner, non-mix packaging, partial live proof, runtime ingress compatibility, and IPC checks. |
| `.planning/handoffs/2026-05-31-package-checklist.md` | 22-48 | Package 0 docs package and checklist-refresh proof. |
| `.planning/handoffs/2026-05-31-package-checklist.md` | 50-112 | Package 1 agent tooling, partial diagnostic bus proof, and typed-IPC helper fix gate. |
| `.planning/handoffs/2026-05-31-package-checklist.md` | 114-198 | Package 2 IPC diagnostics wiring, runtime ingress shim, schema-valid handler proof, and remaining Tauri live gates. |
| `.planning/handoffs/2026-05-31-package-checklist.md` | 564-602 | Final live proof gate for full Tauri/DDJ/co-host validation. |
| `scripts/check_dirty_package_plan.py` | 1-27 | Script purpose, package-checklist path, generated launch preview allow-list, exact backtick-token matcher, and package-heading matcher. |
| `scripts/check_dirty_package_plan.py` | 30-64 | Reads tracked/untracked dirty paths and verifies generated preview ignores. |
| `scripts/check_dirty_package_plan.py` | 67-134 | Builds the optional package summary from Include/Hold assignments, shared dirty-path assignments, dirty paths represented only outside assignment sections, and strict assignment gaps. |
| `scripts/check_dirty_package_plan.py` | 137-188 | CLI entry point, missing-path failure output, strict assignment failure output, OK summary, and optional `--summary` report. |
| `tests/scripts/test_check_dirty_package_plan.py` | 1-151 | Unit coverage for per-section assignment parsing, shared dirty-path assignments, Keep-out mentions staying out of staging assignments, and strict assignment gaps. |

### Packaging Notes

- Run `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary` before staging any
  package. It catches forgotten files as the dirty tree shrinks, and it requires
  exact backticked path entries rather than loose substring matches. Strict mode
  requires each dirty path to sit under an Include or Hold section, so staging
  does not accidentally follow documentation-only mentions.
- This lane is documentation/tooling only; do not mix product behavior changes
  into the same commit.

## Lane 1: Agent/Dev Tooling And Repo Guidance

Purpose: make live verification and IPC wiring discoverable for agents, and add
a Codex-facing MCP server for runtime observe/drive work.

### Code And Docs Line Map

| File | Lines | What changed |
|---|---:|---|
| `.gitignore` | 225-235 | Ignores agent scratch dirs, `.codegraph/`, `.serena/`, and root `node_modules`. |
| `AGENTS.md` | 48-72 | Adds shared Supercharge Tooling notes for `drive-vibemix`, `ipc-wiring-checker`, `vibemix-grounding-review`, MCP servers, and LSP tooling. |
| `AGENTS.md` | 101-106 | IPC parity note says the current top-level IPC count is 72 and points to `uv run python scripts/check_ipc_schema.py`. |
| `CLAUDE.md` | 112-116 | Retires mandatory GSD flow and allows direct edits, while keeping TDD and atomic staging expectations. |
| `.claude/hooks/post_edit_codegen.py` | 1-18 | Documents the PostToolUse schema-codegen guard. |
| `.claude/hooks/post_edit_codegen.py` | 28-54 | Parses hook payloads, detects `messages.schema.json`, runs `npm run codegen:ipc`, and fail-softs. |
| `.claude/settings.json` | 1-15 | Wires the hook for `Edit`, `Write`, and `MultiEdit`. |
| `.claude/skills/drive-vibemix/SKILL.md` | 1-18 | Defines the live-app verification skill and when to use it. |
| `.claude/skills/drive-vibemix/SKILL.md` | 31-58 | Documents source-mode launches and the single-socket invariant on `127.0.0.1:8765`. |
| `.claude/skills/drive-vibemix/SKILL.md` | 62-87 | Documents `ws_probe.py` client attachment, manual trigger frames, and schema-valid typed IPC drive frames. |
| `.claude/skills/drive-vibemix/SKILL.md` | 93-138 | Gives the UI log/events.jsonl evidence checklist for grounded live verification. |
| `.claude/skills/drive-vibemix/references/observe-and-logs.md` | 21-37 | Inbound frame grammar now points typed IPC probes to `ws_probe.py --ipc` for an ISO `date-time` timestamp. |
| `.claude/skills/drive-vibemix/scripts/ws_probe.py` | 1-29 | Probe purpose and examples, including a typed `ipc.status.recheck` command. |
| `.claude/skills/drive-vibemix/scripts/ws_probe.py` | 126-160 | Payload parsing and frame builder for `--trigger`, bare `--action`, and schema-valid typed `--ipc`. |
| `.claude/skills/drive-vibemix/scripts/ws_probe.py` | 163-200 | Client-only websocket send/watch loop and fail-soft connection errors. |
| `.claude/skills/drive-vibemix/scripts/ws_probe.py` | 203-253 | CLI flags for `--action`, `--ipc`, and `--payload-json`. |
| `.claude/skills/ipc-wiring-checker/SKILL.md` | 10-20 | Defines "both ends wired" and states 72 schema const types. |
| `.claude/skills/ipc-wiring-checker/SKILL.md` | 31-40 | Main run command and nonzero exit behavior. |
| `.claude/skills/ipc-wiring-checker/SKILL.md` | 77-93 | Explains stale IPC codegen as a separate failure mode. |
| `.claude/skills/vibemix-grounding-review/SKILL.md` | 1-18 | Defines reaction/prompt/event grounding review triggers. |
| `.claude/skills/vibemix-grounding-review/SKILL.md` | 62-101 | Details the citation-grounding invariant and related tests. |
| `src/vibemix/runtime/dev_mcp_server.py` | 1-46 | New MCP server purpose: observe/drive running app, tail logs, resolve IPC, never bind a second socket. |
| `src/vibemix/runtime/dev_mcp_server.py` | 61-79 | Uses loopback `ws://127.0.0.1:8765` and bundle-id log root. |
| `src/vibemix/runtime/dev_mcp_server.py` | 107-136 | Resolves default data/log/repo roots. |
| `src/vibemix/runtime/dev_mcp_server.py` | 144-170 | Loads the `.claude` IPC checker by path instead of duplicating scanner logic. |
| `src/vibemix/runtime/dev_mcp_server.py` | 178-215 | Bounded log tail and latest session lookup helpers. |
| `src/vibemix/runtime/dev_mcp_server.py` | 223-279 | `ws_observe` client attach, filtering, and fail-soft connection errors. |
| `src/vibemix/runtime/dev_mcp_server.py` | 251-254 | Uses built-in `TimeoutError` around bounded websocket reads. |
| `src/vibemix/runtime/dev_mcp_server.py` | 292-339 | `ws_trigger` sends one inbound frame as a client, captures immediate same-socket replies when present, and returns send confirmation. |
| `src/vibemix/runtime/dev_mcp_server.py` | 354-488 | Tool implementations for `tail_ui_log`, `tail_events`, and `which_handler`. |
| `src/vibemix/runtime/dev_mcp_server.py` | 508-535 | Async `ws_observe`, `ws_trigger`, and sidecar status entry points; typed IPC uses ISO `date-time` timestamps. |
| `src/vibemix/runtime/dev_mcp_server.py` | 533-542 | Sidecar status catches malformed/unreachable websocket URIs with built-in `TimeoutError`. |
| `src/vibemix/runtime/dev_mcp_server.py` | 611-662 | FastMCP tool registration for six tools, including the updated `ws_trigger` reply contract. |
| `src/vibemix/runtime/dev_mcp_server.py` | 665-722 | CLI args and STDIO server entry point. |

### Tests

| File | Lines | Coverage |
|---|---:|---|
| `tests/runtime/test_dev_mcp_server.py` | 38-53 | Path defaults and CLI override resolution. |
| `tests/runtime/test_dev_mcp_server.py` | 69-92 | FastMCP tool registration and missing UI log behavior. |
| `tests/runtime/test_dev_mcp_server.py` | 100-160 | UI log and events tail behavior. |
| `tests/runtime/test_dev_mcp_server.py` | 178-206 | IPC checker reuse, substring matching, and missing checker errors. |
| `tests/runtime/test_dev_mcp_server.py` | 231-335 | WebSocket observe/trigger, ISO typed-IPC timestamps, immediate reply capture, refused socket, fake bus, and malformed URI fail-soft behavior. |
| `tests/runtime/test_dev_mcp_server.py` | 350-389 | Sidecar status and `GEMINI_API_KEY` presence detection. |
| `tests/runtime/test_drive_vibemix_ws_probe.py` | 17-25 | Imports the repo-local skill helper without touching the real websocket bus. |
| `tests/runtime/test_drive_vibemix_ws_probe.py` | 28-62 | Manual trigger, typed IPC, and bare action frame builders. |
| `tests/runtime/test_drive_vibemix_ws_probe.py` | 65-98 | Guardrails for wrong `ipc.*` action shape, non-object payload JSON, and payload without sender. |

### Packaging Notes

- IPC count drift from the first inventory pass is resolved:
  `AGENTS.md:101-106` now says 72, matching
  `.claude/skills/ipc-wiring-checker/SKILL.md:10-13` and
  `uv run python scripts/check_ipc_schema.py`.
- Decide whether `.claude/*` is repo product tooling or development-only. If it
  ships, run the checker and include it in docs.
- `dev_mcp_server.py` is runtime developer tooling; it should not be presented
  as end-user functionality or release-facing product behavior.
- Package 1 is classified as repo developer/operator tooling. It is shippable as
  source-tree maintenance infrastructure, but customer release notes should not
  describe it as a new user-visible feature.

## Lane 2: Earned Wall Live Refresh

Purpose: when a cited live coach event credits a skill or flips Mastered, push
`ipc.learn.progress_state` immediately so the shell SkillWall/Earned Wall updates
without a reload.

### Code Line Map

| File | Lines | What changed |
|---|---:|---|
| `src/vibemix/runtime/coach.py` | 214-247 | New `_emit_earned_wall_refresh()` builds a `LearnProgressState` snapshot and emits it through `ipc_bus`, fail-soft. |
| `src/vibemix/runtime/coach.py` | 250-267 | `_make_mastered_speak()` routes the fixed text through `session.say(..., add_to_chat_ctx=False)` so the heard-once line is not fed back into later LLM chat context. |
| `src/vibemix/runtime/coach.py` | 607-621 | Coach loop stores credited skill IDs from `_credit_live_skill_demo()` and calls `_emit_earned_wall_refresh()`. |
| `src/vibemix/learn/mastered_vocal.py` | 57-70 | Hand-authored fixed-text selector returns a line only on the not-mastered-to-mastered flip. |
| `tests/runtime/test_coach_skill_credit.py` | 258-265 | Helper sets a skill one demo below Mastered. |
| `tests/runtime/test_coach_skill_credit.py` | 268-281 | Mastered fixed-text speech is called with `add_to_chat_ctx=False`. |
| `tests/runtime/test_coach_skill_credit.py` | 284-315 | Mastered flip speaks exactly once via injected `speak`. |
| `tests/runtime/test_coach_skill_credit.py` | 318-335 | Non-flip cited credit stays silent. |
| `tests/runtime/test_coach_skill_credit.py` | 338-353 | Uncited event never speaks. |
| `tests/runtime/test_coach_skill_credit.py` | 356-375 | A failing `speak` hook does not wedge credit or persistence. |

### Tests

| File | Lines | Coverage |
|---|---:|---|
| `tests/runtime/test_coach_progress_emit.py` | 1-10 | Documents the Earned Wall live-refresh regression. |
| `tests/runtime/test_coach_progress_emit.py` | 20-36 | Fake bus/progress objects. |
| `tests/runtime/test_coach_progress_emit.py` | 47-59 | Stubs `LearnProgressState` to test wiring without schema coupling. |
| `tests/runtime/test_coach_progress_emit.py` | 62-70 | Emits progress state on credit. |
| `tests/runtime/test_coach_progress_emit.py` | 73-83 | No emit with no credit or no bus. |
| `tests/runtime/test_coach_progress_emit.py` | 86-91 | Snapshot failure is fail-soft. |
| `tests/learn/test_mastered_vocal_fires_once.py` | 28-65 | Selector fires on the flip, stays silent after mastery, and falls back for unknown skill IDs. |
| `tests/learn/test_mastered_vocal_fires_once.py` | 69-90 | Every mastered-vocal line passes slop/dash gates and mirrors the hand-authored JSON fixture. |

### Packaging Notes

- This is a runtime behavior change. Before claiming done, use the live
  verification loop from `.claude/skills/drive-vibemix/SKILL.md:86-130`.
- If shipping with reaction/speech changes, run the grounding review tests
  referenced in `.claude/skills/vibemix-grounding-review/SKILL.md:76-84`.
- Grounding review pass on 2026-05-31 confirmed this path is fixed text, no
  LLM generation, citation-gated through `_credit_live_skill_demo()`, and
  covered by the 41-test mastered-vocal/no-speculation bundle above.
- Current proof on 2026-05-31:
  `uv run pytest -q tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py`
  passed 41 tests. The wider cross-check
  `uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py`
  passed 36 tests.

## Lane 3: Auto/ANLZ Hot-Cue Materialization Through Pill And Viber

Purpose: preserve cue provenance and semantic hot-cue slot numbers across ingest,
cached `TrackEntry.cues`, `sections_for_entry`, next-suggestion payloads,
move-grade care states, smart-cue proposals, and Viber export.

This lane should be kept end-to-end. Splitting only ingest, only pill tests, or
only Viber export risks losing the product contract.

### Code Line Map

| File | Lines | What changed |
|---|---:|---|
| `src/vibemix/library/ingest.py` | 88-103 | Adds materialized-cue limits, semantic slot map, and G/H-first fallback order so unknown labels do not steal later semantic slots such as outro F. |
| `src/vibemix/library/ingest.py` | 256-264 | Adds auto-cue cache strategy tag and structural cue detector. |
| `src/vibemix/library/ingest.py` | 267-291 | Materializes ANLZ anchors into provenance-tagged `CuePoint`s when no DJ structural cues exist. |
| `src/vibemix/library/ingest.py` | 294-315 | Materializes auto-cue anchors from `detect_cues_auto()`. |
| `src/vibemix/library/ingest.py` | 318-339 | Builds `CuePoint(name,type,start,end,number,source,confidence)` for usable anchors. |
| `src/vibemix/library/ingest.py` | 343-355 | Maps cue labels into stable hot-cue numbers and fallback slots. |
| `src/vibemix/library/ingest.py` | 357-388 | Sanitizes anchor source, finite times, confidence, ordering, and max cue count. |
| `src/vibemix/library/ingest.py` | 391-404 | Hashes cue geometry/provenance into cache keys. |
| `src/vibemix/library/ingest.py` | 560-607 | `_embed_track_cue_anchored()` accepts `precomputed_anchors` so materialized auto cues are not redetected. |
| `src/vibemix/library/ingest.py` | 776-787 | Ingest cache flow materializes ANLZ first, then auto cues if no structural cues, and updates strategy tag. |
| `src/vibemix/library/ingest.py` | 795-824 | Cached and newly embedded rows use `working_track`, preserving materialized cue metadata into store/sections. |
| `src/vibemix/library/smart_cues.py` | 169-175 | Existing cues only occupy slots when human authored; auto/materialized cues become proposal candidates. |
| `src/vibemix/library/smart_cues.py` | 324-336 | `_is_human_authored_cue()` recognizes DJ/Rekordbox/user cue sources. |
| `src/vibemix/intel/move_grade.py` | 56-73 | Adds cue-review and cue-confidence flags to CARE risks. |
| `src/vibemix/intel/move_grade.py` | 75-92 | Maps those risk flags to human-readable reasons, prioritizing `auto cue needs review`. |
| `src/vibemix/intel/move_grade.py` | 163-194 | Blocks `bomb`/`sexy` positive grades when any CARE risk is present. |

### Test Line Map

| File | Lines | Coverage |
|---|---:|---|
| `tests/library/test_ingest.py` | 514-572 | ANLZ ingest now asserts materialized cue source, name, number, confidence, section source, and slots A/D. |
| `tests/library/test_ingest.py` | 589-653 | Auto cues materialize into cache, feed cue-anchored slices, and become sections with slots A/D. |
| `tests/library/test_ingest.py` | 656-696 | Full semantic slot regression: intro A, build B, breakdown C, drop D, secondary drop E, bridge fallback G, and outro F while preserving `source="auto"`. |
| `tests/library/test_setprep_tools.py` | 268-315 | `get_track_sections` preserves auto cue roles, slots, source, and source detail. |
| `tests/library/test_setprep_tools.py` | 466-525 | `smart_hot_cues` and export path carry materialized auto cues. |
| `tests/library/test_smart_cues.py` | 60-75 | Cue helper accepts `source` and `confidence`. |
| `tests/library/test_smart_cues.py` | 117-137 | Auto materialized cues are proposals, not preserved human hot-cue slots. |
| `tests/library/test_next_suggestion.py` | 197-231 | Next suggestion preserves auto cue provenance, confidence, CARE risk, and move grade. |
| `tests/library/test_next_suggestion.py` | 234-263 | Auto `DROP` cue uses semantic hot cue slot D. |
| `tests/intel/test_move_grade.py` | 70-81 | `auto_cue_review` remains `mid`/CARE even with strong scores. |
| `tests/intel/test_move_grade.py` | 84-94 | `low_cue_confidence` uses the transition-scorer flag name and stays undeserved. |

### Packaging Notes

- This lane is the highest coupling risk. Keep ingest, sections, move-grade,
  next-suggestion tests, smart-cue tests, and Viber export tests together.
- Preserve both `CuePoint.source` and `CuePoint.number`; provenance without slot
  number is not enough for pill/Viber compatibility.
- The visible compact UI should say `CARE` for cue review/low confidence rather
  than presenting an auto cue as a fully earned positive move.

## Lane 4: Library/Viber Live-Read Deck-Pair Audio Context

Purpose: make Viber/library chat understand richer live deck-pair audio context
while keeping claims grounded as "live read" rather than "proof".

### Code Line Map

| File | Lines | What changed |
|---|---:|---|
| `tauri/ui/src/library/api.ts` | 230-246 | Adds `LibraryAudioWindowDeckAudio` and expands `LibraryAudioWindowMap` for deck-pair audio parts. |
| `tauri/ui/src/library/api.ts` | 257-281 | Adds `deck_audio_features_context`, `deck_audio_delta_context`, and `deck_audio_window_context` to live context. |
| `tauri/ui/src/library/api.ts` | 548-573 | Prioritizes deck-audio capture/features/delta/window evidence tokens. |
| `tauri/ui/src/library/api.ts` | 596-630 | Normalizes live evidence and derived refs. |
| `tauri/ui/src/library/api.ts` | 849-927 | Accepts global-only or deck-pair audio windows; validates distinct P labels and forbids attached/stem claims. |
| `tauri/ui/src/library/api.ts` | 929-1021 | Normalizes Gemini audio part labels and validates deck-pair part maps. |
| `tauri/ui/src/library/api.ts` | 1054-1176 | Normalizes audio window maps for global or deck-pair audio plus optional separation/span/activity. |
| `tauri/ui/src/library/api.ts` | 1179-1208 | Checks audio-window map labels match audio-part labels. |
| `tauri/ui/src/library/api.ts` | 1299-1328 | Deck audio separation accepts global-only and deck-pair capture contexts. |
| `tauri/ui/src/library/api.ts` | 1331-1393 | Normalizes deck audio features, delta, and pre/current window descriptors, rejecting verdict-y language. |
| `tauri/ui/src/library/api.ts` | 1395-1412 | Expands live source status keys. |
| `tauri/ui/src/library/api.ts` | 1452-1607 | Threads all contexts through `normalizeLiveContextPayload()` and only keeps audio windows/maps when labels match. |
| `tauri/ui/src/library/index.ts` | 150-160 | Adds new deck audio context keys to text-context clearing/merging. |
| `tauri/ui/src/library/index.ts` | 186-208 | Mirrors evidence priority for UI-side merging. |
| `tauri/ui/src/library/index.ts` | 210-269 | Merges evidence tokens, refs, and MIDI evidence under caps. |
| `tauri/ui/src/library/index.ts` | 288-363 | `mergeLiveContext()` re-runs the live-context normalizer, ignores rejected raw frames, and clears stale deck source/text/window/evidence when a later valid frame omits it. |
| `tauri/ui/src/library/index.ts` | 1044-1128 | `liveProofStatus()` now requires schema v2, deck-pair capabilities, active deck-pair receipts, and both decks active before armed. |
| `tauri/ui/src/library/index.ts` | 1130-1162 | UI row says "live read" and scope text says "live read armed". |
| `tauri/ui/src/library/index.ts` | 1192-1212 | Supported verdicts render as "scoring grounded". |
| `tauri/ui/src/library/index.ts` | 1215-1255 | Live verification/tool rows and hidden internal failure labels use "live read" copy. |
| `tauri/ui/src/library/index.ts` | 1330-1400 | Chat artifact labels and move-scoring copy use "live read". |
| `tauri/ui/src/library/index.ts` | 2021-2031 | Live deck/move contexts update `latestLiveContext` for chat. |

### Tests

| File | Lines | Coverage |
|---|---:|---|
| `tauri/ui/src/library/api.test.ts` | 261-301 | Keeps supported verdict receipts and new capability names before UI render. |
| `tauri/ui/src/library/api.test.ts` | 581-646 | Clears stale deck payloads and rejects attached/stem deck audio contexts. |
| `tauri/ui/src/library/api.test.ts` | 646-699 | Accepts deck-pair separation, features, delta, and window descriptors. |
| `tauri/ui/src/library/api.test.ts` | 703-838 | Accepts/rejects Gemini deck-pair audio part labels. |
| `tauri/ui/src/library/api.test.ts` | 857-986 | Accepts matching Deck A/B audio windows and rejects missing/mismatched/colliding labels. |
| `tauri/ui/src/library/chat.test.ts` | 51-63 | Adds deck-pair fixture strings for separation/features/delta/window and audio parts/windows. |
| `tauri/ui/src/library/chat.test.ts` | 475-661 | Live read status stays partial until deck-pair audio is active, resolved, and receipt-backed. |
| `tauri/ui/src/library/chat.test.ts` | 584-631 | Passes Deck A/B audio-window labels to Viber chat and clears stale context. |
| `tauri/ui/src/library/chat.test.ts` | 1181-1190 | Rejects raw attached/deck-pair-looking live context when the normalizer would drop it, so Viber chat does not receive untrusted deck-audio claims. |
| `tauri/ui/src/library/chat.test.ts` | 701-854 | Renders live read verifier and supported live verdicts as grounded scoring. |

### Packaging Notes

- Keep this separate from cue work even though both touch Viber. This lane is
  live audio context and chat grounding; cue work is section/cue provenance.
- The copy deliberately says "live read", not "proof". Do not regress to a
  stronger claim unless a verifier proves the evidence is causal.

## Lane 5: Pill Next-Suggestion Interaction And Browser Polish

Purpose: make the compact pill action truthful and usable: `DJ KNOWS` exposes
the grounded next suggestion, risky moves complete as `CARE`, focus returns to
the pill root when surfaces disappear, demo reactions work in browser E2E, and
visual polish stays in the established token system.

### Code Line Map

| File | Lines | What changed |
|---|---:|---|
| `tauri/ui/package.json` | 13-16 | Adds `test:e2e:pill`. |
| `tauri/ui/src/pill/index.ts` | 67-70 | Adds constants for feedback and reaction echo durations. |
| `tauri/ui/src/pill/index.ts` | 1082-1092 | `syncPillRootActionability()` adds/removes `aria-keyshortcuts`, `aria-controls`, and `aria-expanded`. |
| `tauri/ui/src/pill/index.ts` | 1113-1120 | Adds focus-return predicate for removed suggestion surfaces. |
| `tauri/ui/src/pill/index.ts` | 1395-1404 | Reaction echo yields to hover peek when a grounded next suggestion is available. |
| `tauri/ui/src/pill/index.ts` | 1918-1923 | Reaction echo uses the duration constant. |
| `tauri/ui/src/pill/index.ts` | 2162-2185 | Full next-suggestion mount restores root focus after replacing a focused surface. |
| `tauri/ui/src/pill/index.ts` | 2200-2227 | Peek card mount restores root focus after replacing a focused surface. |
| `tauri/ui/src/pill/index.ts` | 2230-2243 | Clearing the peek card restores root focus when needed. |
| `tauri/ui/src/pill/index.ts` | 2384-2407 | Feedback receipt duration is constant and clears stale next/peek DOM with focus restoration. |
| `tauri/ui/src/pill/next-suggestion.ts` | 629-655 | Splits full action text from compact peek action text. |
| `tauri/ui/src/pill/next-suggestion.ts` | 666-690 | Peek ARIA label includes hidden full-detail action text. |
| `tauri/ui/src/pill/next-suggestion.ts` | 1068-1089 | Interactive peek card is a button-like control and stops key propagation. |
| `tauri/ui/src/pill/next-suggestion.ts` | 1143-1150 | Compact transition line title carries the full grounded transition. |
| `tauri/ui/src/pill/pill.css` | 735-742 | Actionable face rail stays in the rose/brand system, not gold. |
| `tauri/ui/src/pill/pill.css` | 2290-2313 | Negative reaction lead gets warning-badge styling. |
| `tauri/ui/src/pill/pill.css` | 2403-2415 | Negative reaction keyframe animation. |
| `tauri/ui/src/pill/pill.css` | 2867-2925 | `DJ KNOWS`/`CARE` peek action renders as a hardware capsule. |
| `tauri/ui/src/pill/pill.css` | 2999-3028 | CARE/negative grade reasons render as readable warning chips. |
| `tauri/ui/src/pill/pill.css` | 3380-3382 | Demo controls drop under the open pill. |
| `tauri/ui/src/pill/pill.css` | 3947-3964 | Mobile demo controls become a two-row, three-column pad bank. |

### Tests

| File | Lines | Coverage |
|---|---:|---|
| `tauri/ui/src/pill/index.test.ts` | 108-153 | CSS checks for no-gold face rail, hardware capsule, readable risky reasons, and demo control z-index. |
| `tauri/ui/src/pill/index.test.ts` | 1365-1396 | Focus continuity predicate. |
| `tauri/ui/src/pill/index.test.ts` | 1416-1430 | ARIA controls/expanded shortcut affordance. |
| `tauri/ui/src/pill/next-suggestion.test.ts` | 1025-1040 | Peek density compact text retains full transition in title and ARIA detail. |
| `tauri/ui/src/pill/next-suggestion.test.ts` | 1055-1081 | Risky moves keep care reason in peek density. |
| `tauri/ui/src/pill/next-suggestion.test.ts` | 1083-1112 | Full grounded transition survives compact peek. |
| `tauri/ui/src/pill/next-suggestion.test.ts` | 1277-1311 | CSS/token gates for no hex, no raw rgba, mono token, and 20/80 amber. |
| `tauri/ui/tests/pill/playwright.config.ts` | 5-27 | Browser E2E config starts Vite pill preview on `127.0.0.1:5190`. |
| `tauri/ui/tests/pill/browser-care-hover.pw.ts` | 133-180 | Risky hover/click ownership with overlapping demo controls. |
| `tauri/ui/tests/pill/browser-care-hover.pw.ts` | 253-292 | CARE click completes task and suppresses stale suggestions until retimed. |
| `tauri/ui/tests/pill/browser-care-hover.pw.ts` | 397-440 | Focused `DJ KNOWS` completes KEEP and clears shortcuts. |
| `tauri/ui/tests/pill/browser-care-hover.pw.ts` | 492-535 | Focused peek card completes CARE with Space. |
| `tauri/ui/tests/pill/browser-care-hover.pw.ts` | 579-618 | Focused risky `DJ KNOWS` completes CARE with Space. |
| `tauri/ui/tests/pill/browser-demo-reactions.pw.ts` | 5-12 | Defines six demo reaction pads. |
| `tauri/ui/tests/pill/browser-demo-reactions.pw.ts` | 14-51 | Every pad opens full reaction with canvas FX. |
| `tauri/ui/tests/pill/browser-demo-reactions.pw.ts` | 108-157 | Compact two-row pad bank, `LIT AFF` no-wrap, negative warning styling. |
| `tauri/ui/tests/pill/browser-demo-reactions.pw.ts` | 159-180 | Full reaction collapses into durable face echo. |
| `tauri/ui/tests/pill/browser-demo-reactions.pw.ts` | 202-243 | Reduced motion keeps reaction copy readable while suppressing canvas FX pixels and lead animation. |
| `.planning/handoffs/2026-05-29-pill-polish-handoff.md` | 1-29 | Existing detailed pill handoff scope and boundaries. |
| `.planning/handoffs/2026-05-29-pill-polish-handoff.md` | 360-407 | Existing detailed browser coverage list, 16 E2E checks. |
| `.planning/handoffs/2026-05-29-pill-polish-handoff.md` | 408-430 | Existing recorded whitespace/browser smoke notes. |

### Packaging Notes

- This lane is UI-visible. Ship with screenshots/recording, not just unit tests.
- The E2E suite now has current dirty-tree proof: `npm --prefix tauri/ui run test:e2e:pill`
  passed 16 Playwright tests on 2026-05-31.
- Keep demo controls as inspection tooling unless a product surface explicitly
  needs them.

## Lane 6: Learn Operator-Action Route Mismatch Bridge

Purpose: carry grounded operator-action route mismatch hints from flat frames and
Tauri events into Learn UI prompts, especially Rekordbox route/capture mismatch.

### Code Line Map

| File | Lines | What changed |
|---|---:|---|
| `src/vibemix/learn/curriculum.py` | 113-124 | Source of truth for Course 2 now declares `library_suggestions`, not `library_exemplars`. |
| `src/vibemix/learn/curriculum_projection.py` | 35-47 | The frontend course projection copies each course's `capabilities` from `COURSE_REGISTRY`. |
| `src/vibemix/learn/curriculum_projection.py` | 70-95 | The TypeScript renderer emits the sorted `CourseCapability` union and per-course capability arrays. |
| `scripts/export_learn_curriculum_meta.py` | 37-57 | `--check` compares the generated projection against `tauri/ui/src/learn/lesson/curriculum-meta.ts` without writing. |
| `tauri/ui/src/learn/lesson/curriculum-meta.ts` | 1-4 | File declares itself generated from `src/vibemix/learn/curriculum.py`. |
| `tauri/ui/src/learn/lesson/curriculum-meta.ts` | 8-24 | Adds `library_suggestions` capability to Course 2. |
| `tauri/ui/src/learn/lesson/operator-action.ts` | 9-18 | Adds `current_rekordbox_route`, `target_capture_route`, and `route_mismatch` to operator-action payloads. |
| `tauri/ui/src/learn/lesson/operator-action.ts` | 20-50 | Normalizes those new fields. |
| `tauri/ui/src/learn/lesson/operator-action.ts` | 53-60 | Compact label says "route Rekordbox to ..." for mismatches. |
| `tauri/ui/src/learn/lesson/operator-action.ts` | 83-101 | ARIA label includes current route, target route, and mismatch. |
| `tauri/ui/src/learn/lesson/operator-action.ts` | 117-130 | Preserves BlackHole channel count and compacts target route labels. |
| `tauri/ui/src/learn/ws-client.ts` | 64-68 | Adds shared operator-action event names. |
| `tauri/ui/src/learn/ws-client.ts` | 220-246 | Tauri bridge listens for `learn-operator-action`. |
| `tauri/ui/src/learn/ws-client.ts` | 264-282 | Dispatches operator-action frames before dropping non-`ipc.learn.*` shared-bus frames. |
| `tauri/ui/src/learn/ws-client.ts` | 313-341 | Extracts `learn_operator_action`, `operator_action`, bare prompt frames, and explicit clears. |
| `tauri/ui/src/learn/learn-window.ts` | 220-224 | Declares `headphone_cue`, `lesson_continue`, and `master_vol` as explicit screen-only lesson controls. |
| `tauri/ui/src/learn/learn-window.ts` | 588-595 | Routes screen-only highlight payloads to the fallback action and clears stale SVG highlight state instead of warning about absent physical controls. |
| `tauri/ui/src/learn/learn-window.ts` | 1247-1249 | Central helper used by the highlight painter to distinguish intentional screen-only controls from real missing SVG anchors. |

### Tests

| File | Lines | Coverage |
|---|---:|---|
| `tauri/ui/tests/learn/test_curriculum_meta.spec.ts` | 41-57 | Course capability contract distinguishes Course 1 `library_exemplars`, Course 2 `library_suggestions`, and Course 3 live-mode capabilities. |
| `tauri/ui/tests/learn/test_operator_action.spec.ts` | 11-25 | BlackHole 2ch route label. |
| `tauri/ui/tests/learn/test_operator_action.spec.ts` | 79-89 | Route mismatch fields and compact label. |
| `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts` | 334-366 | Structured Course 3 operator action collapses to one booth prompt. |
| `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts` | 422-468 | Route mismatch prompt stays a single precise booth fix. |
| `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts` | 470-497 | Generic operator-action event dispatch and explicit clear. |
| `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts` | 1597-1629 | Screen fallback for `headphone_cue:A` and `master_vol` emits click acks without false missing-highlight warnings. |
| `tauri/ui/tests/learn/test_ws_client_filters_mascot.spec.ts` | 150-199 | Flat Course 3 frame preserves new operator-action fields. |
| `tauri/ui/tests/learn/test_ws_client_filters_mascot.spec.ts` | 204-240 | Generic grounded operator-action bridge. |
| `tauri/ui/tests/learn/test_ws_client_filters_mascot.spec.ts` | 245-258 | Explicit generic operator-action clear. |
| `tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts` | 99-210 | Tauri bridge listener/unlistener and dispatch assertions. |

### Packaging Notes

- `tauri/ui/src/learn/lesson/curriculum-meta.ts` is not a hand patch. The source
  of truth already has Course 2 `library_suggestions` at
  `src/vibemix/learn/curriculum.py:113-124`, and
  `uv run python scripts/export_learn_curriculum_meta.py --check` passes. Package
  this as a generated metadata refresh in the Learn operator-action lane.
- Current proof on 2026-05-31:
  `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_operator_action.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  passed 55 tests, and
  `uv run python scripts/export_learn_curriculum_meta.py --check && uv run pytest -q tests/learn/test_curriculum_projection.py`
  passed with 4 Python projection tests.
- Keep this out of the excluded beginner-path suites unless explicitly asked.
- The untracked `.planning/handoffs/2026-05-30-learn-goal-complete-style-package.md`
  is a Learn RC handoff, not a release-ready claim: lines 3-9 say not to mark the
  goal complete, and lines 62-80 name the remaining routed-audio gate.

## Lane 7: Live-Stack Cost/Pricing CLI And Docs

Purpose: add a reproducible live co-host cost model and CLI path for brain/TTS/STT
/Viber/LiveKit economics.

### Code Line Map

| File | Lines | What changed |
|---|---:|---|
| `src/vibemix/library/pricing.py` | 1-28 | Source-audited pricing table contract and source list, rechecked 2026-05-31. |
| `src/vibemix/library/pricing.py` | 54-81 | `PriceRow` and Gemini row builder resolve Gemini IDs through model router. |
| `src/vibemix/library/pricing.py` | 84-119 | Live-brain and Gemini TTS pricing rows; runtime pricing excludes the spike-only 3.1 Flash Live model. |
| `src/vibemix/library/pricing.py` | 120-142 | DeepSeek Viber rows cite the official one-quarter-price adjustment and the V4 Flash compatibility alias note. |
| `src/vibemix/library/pricing.py` | 143-197 | TTS vendor rows: Hume note is Business-tier `$0.05/1k`, Cartesia `sonic-3` stays `verified=False` / `LEGACY_DERIVED`, and OpenAI TTS rows use model-specific source pages. |
| `src/vibemix/library/pricing.py` | 198-225 | Dedicated STT rows. |
| `src/vibemix/library/pricing.py` | 230-243 | `price_for_model()` and `price_for_path()`. |
| `src/vibemix/library/cost.py` | 33-44 | Audio token, chars/sec, and LiveKit reference constants. |
| `src/vibemix/library/cost.py` | 47-126 | Brain, TTS, and listen per-reaction cost functions. |
| `src/vibemix/library/cost.py` | 132-190 | Stack, turn, usage, leg, and breakdown dataclasses. |
| `src/vibemix/library/cost.py` | 193-271 | `_price_any()` and `compute_live_cost()` compose brain/listen/TTS/Viber/LiveKit legs. |
| `src/vibemix/library/cost.py` | 274-356 | Sensitivity rows across TTS, STT, brain, cache hit, and Viber burst axes; brain options stay to production-safe non-Live aliases. |
| `src/vibemix/library/cost.py` | 358-421 | JSON-serializable `live_budget_report()`. |
| `src/vibemix/llm/_router_config.py` | 46-59 | Adds candidate live brain aliases: `live_coach_cand_25flash` and `live_coach_cand_3flash`; the 3.1 Flash Live model remains absent from runtime router paths. |
| `src/vibemix/__main__.py` | 2741-2784 | `vibemix library budget` parser adds `--stack live` and live-stack knobs. |
| `src/vibemix/__main__.py` | 5456-5525 | `_cmd_library_budget_live()` prints or JSON-dumps live stack report and handles unknown rows cleanly. |
| `src/vibemix/__main__.py` | 5528-5531 | Dispatches to live budget mode when `args.stack == "live"`. |

### Docs And Tests

| File | Lines | Coverage |
|---|---:|---|
| `docs/pricing/live-stack-economics.en.md` | 1-9 | Status now says source-audited internal model, not external pricing copy while Cartesia remains unverified. |
| `docs/pricing/live-stack-economics.en.md` | 11-36 | Per-DJ/session cost breakdown. |
| `docs/pricing/live-stack-economics.en.md` | 38-53 | Voice sensitivity narrative now labels Cartesia cost as legacy-derived/unverified while preserving the live reliability finding. |
| `docs/pricing/live-stack-economics.en.md` | 63-87 | Cache assumption and source-audited price table; DeepSeek uses the official one-quarter note and Cartesia is explicitly not a confirmed per-character SKU. |
| `docs/pricing/live-stack-economics.en.md` | 89-104 | Assumptions and caveats; caveat blocks external use of the €9.74/€97k Cartesia headline until billing is confirmed. |
| `docs/pricing/live-stack-economics.it.md` | 3-10 | Italian status mirrors the internal/source-audited and Cartesia-unverified warning. |
| `docs/pricing/live-stack-economics.it.md` | 39-55 | Italian voice sensitivity narrative mirrors the Cartesia reliability vs unverified-cost distinction. |
| `docs/pricing/live-stack-economics.it.md` | 69-89 | Italian source-audited price table removes the stale Bloomberg/Engadget permanence claim. |
| `docs/pricing/live-stack-economics.it.md` | 99-106 | Italian caveats block external use of the Cartesia headline until billing is confirmed. |
| `tests/library/test_pricing.py` | 18-34 | Live coach price row and router resolution. |
| `tests/library/test_pricing.py` | 35-64 | All rows carry source/date and concrete rates. |
| `tests/library/test_pricing.py` | 65-86 | Cartesia `LEGACY_DERIVED`/unverified flag and DeepSeek V4 Pro official one-quarter price. |
| `tests/library/test_pricing.py` | 89-104 | Cheapest Gemini tier and unknown-model error. |
| `tests/library/test_cost.py` | 16-40 | Brain cache blend and cache sensitivity. |
| `tests/library/test_cost.py` | 41-103 | TTS and listening cost shapes. |
| `tests/library/test_cost.py` | 125-170 | Leg totals, direct-mode LiveKit zero, Cloud LiveKit leg, dominant TTS leg. |
| `tests/library/test_cost.py` | 173-210 | DAU scaling and premium TTS vs premium brain lever. |
| `tests/library/test_cost.py` | 213-254 | Sensitivity axes, unverified flag, cache-hit ordering, JSON report. |
| `tests/llm/test_model_router.py` | 97-117 | Router path count is 12 and includes only the two non-Live live-brain candidate aliases. |
| `tests/e2e/test_phase_41_latency_stack_integration.py` | 99-124 | Phase-41 router integration table includes the two source-audited non-Live candidates and keeps the 3.1 Flash Live spike model out of runtime paths. |

### Packaging Notes

- 2026-05-31 source audit: Gemini and DeepSeek official pages support the current
  Gemini/DeepSeek rows; Hume's `$50/1M` row is Business-tier, not Pro-tier;
  Deepgram/OpenAI rows still match their official pages.
- Cartesia remains the blocker for public pricing copy: the current public page
  lists Sonic-3.5 plan minutes and plan prices but not an exact per-character SKU.
  Keep `sonic-3` as an internal, unverified sensitivity placeholder until account
  billing confirms the effective rate.
- Keep model literals out of pricing rows for Gemini paths; the code intentionally
  resolves through `model_router`.
- Keep the Gemini 3.1 Flash Live model isolated under `spikes/` until the LAT-09
  verdict is written. It is not a runtime router/pricing/cost candidate.

## Lane 7b: Live TTS Shutdown Hygiene

Purpose: close nested live TTS provider sessions during runtime shutdown without
mixing that lifecycle fix into the live-stack budget CLI package.

### Code And Test Line Map

| File | Lines | What changed |
|---|---:|---|
| `src/vibemix/__main__.py` | 210-226 | Adds `_close_tts_chain()` to close the live TTS adapter plus nested `_tts_instances` once each. |
| `src/vibemix/__main__.py` | 2351-2358 | Main shutdown now best-effort closes the TTS chain after the LiveKit session closes. |
| `tests/test_main_smoke.py` | 673-691 | Covers duplicate nested provider references so child providers close once. |

### Packaging Notes

- This shares `src/vibemix/__main__.py` with the live-stack budget work. If
  Package 10 and Package 14 are staged separately, inspect the cached hunk for
  `__main__.py` before committing.

## Lane 8: Beatmatch Judge Creditability

Purpose: make beatmatching honestly Mastered-creditable now that the
learning-module owned-deck Judge can grade phase and tempo from known deck state.

### Code Line Map

| File | Lines | What changed |
|---|---:|---|
| `src/vibemix/audio/grid.py` | 1-17 | New constant-tempo beatgrid module and design notes. |
| `src/vibemix/audio/grid.py` | 24-34 | `BeatGrid` validates BPM, floors anchor frame, and computes beat length. |
| `src/vibemix/audio/grid.py` | 36-63 | Beat position, continuous index, phase distance, and closest beat. |
| `src/vibemix/audio/miniplayer.py` | 1-20 | New owned-deck mini-player design notes. |
| `src/vibemix/audio/miniplayer.py` | 29-67 | `_do_scale_block()` linear resampler with fractional cursor and silence past end. |
| `src/vibemix/audio/miniplayer.py` | 69-79 | Equal-power crossfader gains. |
| `src/vibemix/audio/miniplayer.py` | 82-97 | Immutable `DeckState`. |
| `src/vibemix/audio/miniplayer.py` | 99-145 | `MiniDeck` renders A/B blocks and exposes state. |
| `src/vibemix/learn/beatmatch_judge.py` | 1-15 | New Judge design notes and Mixxx-derived math references. |
| `src/vibemix/learn/beatmatch_judge.py` | 24-34 | Phase/tempo tolerance constants. |
| `src/vibemix/learn/beatmatch_judge.py` | 37-60 | Phase error and octave-fold helpers. |
| `src/vibemix/learn/beatmatch_judge.py` | 63-80 | `BeatmatchGrade` dataclass. |
| `src/vibemix/learn/beatmatch_judge.py` | 83-142 | `grade_beatmatch()` exact tempo/phase grading. |
| `src/vibemix/learn/beatmatch_judge.py` | 145-166 | `grade_to_event_extra()` emits the canonical `BEATMATCH_GRADED` payload the recognizer reads. |
| `src/vibemix/learn/skill_recognizer.py` | 93-109 | Honest-uncreditable list is now empty because beatmatching has a citable Judge signal. |
| `src/vibemix/learn/skill_recognizer.py` | 158-175 | Cited, non-abstain, tempo-matched and phase-locked `BEATMATCH_GRADED` events resolve to `beatmatching`; drift/trainwreck/tempo-off abstain. |
| `src/vibemix/learn/skill_recognizer.py` | 258-292 | Existing citation gate, dedup, and Competent-before-Mastered rules remain the credit arbiter. |
| `src/vibemix/learn/skill_tree.py` | 92-106 | `live_creditable` documentation now states all six v11.0 skills have live paths. |
| `src/vibemix/learn/skill_tree.py` | 145-152 | `beatmatching` uses the default `live_creditable=True`, tied to the Judge signal. |
| `src/vibemix/learn/skill_tree.py` | 359-383 | `what_remains` keeps the anti-slop uncreditable branch for future skills, but beatmatching now gets the ordinary cited-demo countdown. |
| `scripts/miniplayer_smoke.py` | 1-21 | Manual hardware smoke-test script purpose and run commands. |
| `scripts/miniplayer_smoke.py` | 35-52 | Tone generator and output device resolver. |
| `scripts/miniplayer_smoke.py` | 55-72 | Demo automation for rate ramp and crossfade. |
| `scripts/miniplayer_smoke.py` | 74-126 | Sounddevice output stream and callback. |

### Tests

| File | Lines | Coverage |
|---|---:|---|
| `tests/audio/test_grid.py` | 18-59 | Constant-tempo beat positions, closest beat midpoint, beat distance, anchor/BPM validation. |
| `tests/audio/test_miniplayer.py` | 25-91 | Resampler interpolation, silence past end, cursor continuity, exact passthrough. |
| `tests/audio/test_miniplayer.py` | 92-136 | Equal-power crossfade and MiniDeck cursor/state behavior. |
| `tests/learn/test_beatmatch_judge.py` | 33-60 | Phase error and octave-fold behavior. |
| `tests/learn/test_beatmatch_judge.py` | 63-104 | Perfect match, octave-apart match, tempo-off, and stopped-deck abstain. |
| `tests/learn/test_beatmatch_judge.py` | 111-132 | Small phase drift and recoverable late deck. |
| `tests/learn/test_judge_credits_beatmatch.py` | 1-17 | Documents the anti-proxy creditability contract: only a cited locked owned-deck grade proves beatmatching. |
| `tests/learn/test_judge_credits_beatmatch.py` | 70-77 | Cited locked grade credits beatmatching. |
| `tests/learn/test_judge_credits_beatmatch.py` | 80-113 | Trainwreck, drift, tempo-off, and abstain grades credit nothing. |
| `tests/learn/test_judge_credits_beatmatch.py` | 116-134 | Uncited or not-yet-Competent locked grades credit nothing. |
| `tests/learn/test_judge_credits_beatmatch.py` | 137-171 | Real `grade_beatmatch()` output round-trips through `grade_to_event_extra()` into recognizer credit or refusal. |
| `tests/learn/test_creditability_drift.py` | 24-33 | Manifest `live_creditable` flags and recognizer uncreditable list both prove no uncreditable v11.0 skills remain. |
| `tests/learn/test_skill_wall_what_remains.py` | 78-88 | Competent beatmatching now promises the real cited-live-demo path to Mastered. |

### Packaging Notes

- This is learning-module owned-deck groundwork, not live co-host observer logic.
  It should not write `MusicState`.
- The smoke script depends on real audio output and should stay manual/hardware
  marked, not CI.
- Current proof on 2026-05-31:
  `uv run pytest -q tests/audio/test_grid.py tests/audio/test_miniplayer.py tests/learn/test_beatmatch_judge.py tests/learn/test_judge_credits_beatmatch.py`
  passed 28 tests, and
  `uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py`
  passed 19 tests.

## Lane 9: Launch Docs, Pitch Assets, Screenshots

Purpose: launch collateral and visual evidence. Treat this as assets/docs, not
product runtime code.

### Files

| File | Lines / facts | Notes |
|---|---:|---|
| `docs/launch/.build_talking.py` | 1-11 | Imports, repo-relative `DEFAULT_AUDIO`, and repo-relative default output `.vibemix-konusan.html`; no `/Users/ozai/...` paths remain. |
| `docs/launch/.build_talking.py` | 206-209 | `render()` embeds the selected MP3 as a base64 data URI. |
| `docs/launch/.build_talking.py` | 212-266 | CLI supports `--audio`, `--out`, `--check`, and `--print`; writes only to the requested output path. |
| `docs/launch/.partner-capabilities-tr-short.html` | 425 lines | Turkish partner capabilities HTML. |
| `docs/launch/.vibemix-pitch-en.html` | 227 lines | English pitch HTML. |
| `docs/launch/.vibemix-pitch-tr.html` | 227 lines | Turkish pitch HTML. |
| `docs/launch/vibemix-vo-charon.mp3` | 96 kbps, 24 kHz, mono | Voice/audio launch asset. |
| `docs/launch/vibemix-yetenekler-tr.pdf` | PDF 1.7 | Turkish capabilities PDF. |
| `docs/launch/screenshots/README.md` | 1-62 | Manifest for the launch screenshot bundle; records generated-HTML policy, the canonical launch subset, optional closeups, and alternates. |
| `docs/launch/screenshots/*.png` | 25 PNGs | Moved out of repo root. Canonical first package: `shell-live-moneyshot`, `shell-deck-final`, `viber-chat-elevated`, `crate-elevated`, `learn-elevated`, `debrief-elevated`, `settings-elevated`, and `wizard-current`; closeups are optional. |
| `docs/launch/screenshots/rail-closeup.png` | 1262x64 PNG | Pill rail close-up. |
| `docs/launch/screenshots/settings-closeup.png` | 447x900 PNG | Settings close-up. |
| `docs/launch/screenshots/viber-chat-closeup.png` | 429x740 PNG | Viber chat close-up. |
| `.gitignore` | 271-274 | Keeps generated launch preview HTML out of package staging, including `.vibemix-konusan.html`. |

### Packaging Notes

- Root launch screenshots are now under `docs/launch/screenshots/`; the manifest
  names the canonical first-package subset and alternates.
- `.build_talking.py` is parameterized and reproducible. The generated
  `.vibemix-konusan.html` output remains a local generated artifact; source
  inputs are `.build_talking.py` plus `vibemix-vo-charon.mp3`.
- The launch screenshot alternates are now an explicit hold lane in
  `.planning/handoffs/2026-05-31-package-checklist.md`, not keep-out-only dirty
  files. Strict package checking can therefore prove every dirty path is assigned
  to a package or hold lane.

## Lane 10: Runtime Memory CLAP Readiness

Purpose: make source-mode boot and post-session memory ingest compatible with
the current 512-d CLAP embedding stack when an older durable `memory.db` still
contains an empty sqlite-vec table declared at 768 dimensions.

### Code Line Map

| File | Lines | What changed |
|---|---:|---|
| `src/vibemix/memory/index_sqlite_vec_memory.py` | 74-108 | Constructor now creates vec/moments schema and immediately reconciles the declared `FLOAT[N]` dim before any insert can hit sqlite-vec. |
| `src/vibemix/memory/index_sqlite_vec_memory.py` | 115-137 | Shared helpers create the current-dim `vec_memory` table and the colocated `moments` metadata table on the same connection. |
| `src/vibemix/memory/index_sqlite_vec_memory.py` | 139-159 | Empty stale tables are recreated and unbacked `moments` rows are cleared; populated stale tables raise so `open_memory_store()` falls back instead of silently wiping old data. |
| `src/vibemix/memory/index_sqlite_vec_memory.py` | 203-223 | New `vector_dim()`, `row_count()`, and `recreate_table()` helpers mirror the library-store inspection seam for memory.db. |
| `src/vibemix/runtime/session_loop.py` | 163-192 | `SessionLoop` now carries a `memory_ingest_enabled` switch so diagnostic loops can keep retention live while skipping CLAP ingest. |
| `src/vibemix/runtime/session_loop.py` | 755-784 | Boot and close lifecycle methods skip memory ingest when the switch is disabled, while retaining the retention sweep. |
| `src/vibemix/runtime/session_loop.py` | 902-904 | Direct `_fire_ingest()` calls also honor the disabled switch, so tests and future callers cannot bypass it accidentally. |
| `src/vibemix/runtime/session_loop.py` | 1454-1462 | `run_session()` passes `memory_ingest_enabled=False`; the sidecar-only MCP/diagnostic bus probe no longer launches CLAP indexing. |
| `tests/memory/test_ingest_wiring.py` | 205-219 | Regression: disabling memory ingest prevents both boot and close ingest entrypoints from running. |
| `tests/memory/test_ingest_wiring.py` | 319-325 | Source guard: the diagnostic `run_session()` path explicitly passes `memory_ingest_enabled=False`. |
| `tests/memory/test_store_parity.py` | 57-106 | Test helper builds a synthetic stale sqlite-vec `memory.db` with a non-current `FLOAT[N]` declaration. |
| `tests/memory/test_store_parity.py` | 123-149 | Regression: an empty stale table self-heals, clears unbacked metadata, accepts a current-dim vector, and remains queryable. |
| `tests/memory/test_store_parity.py` | 151-169 | Regression: a populated stale table is not wiped; the store uses the numpy fallback and only returns fresh current-dim records. |

### Packaging Notes

- This is product runtime readiness, not agent tooling: `session_loop` opens
  `MemoryStore(db_path=None)` during boot/close memory ingest, so a stale durable
  `memory.db` can block live verification even when the bus itself is healthy.
- The observed local durable store on 2026-05-31 was empty but stale:
  `vec_memory ... embedding FLOAT[768]` with zero vector rows and zero moments rows.
  That case is safe to recreate automatically.
- Do not fold this into the mix/audio hold lane. It only touches memory storage
  and parity tests.
- Current proof:
  `uv sync --group dev --extra ai-local`,
  `uv run python -m vibemix library models --json`,
  `uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py`,
  `uv run ruff check src/vibemix/runtime/session_loop.py src/vibemix/memory/index_sqlite_vec_memory.py tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py`,
  and a follow-up MCP-observed `--session` probe that exits cleanly after Ctrl-C.

## Cross-Lane Risks Before Shipping

1. Generated Learn metadata is classified, not blocking: package
   `tauri/ui/src/learn/lesson/curriculum-meta.ts:21-24` as the generated refresh
   of `src/vibemix/learn/curriculum.py:113-124`, with
   `scripts/export_learn_curriculum_meta.py:37-57` as the reproducibility gate.
2. Debrief citation-summary/event-timeline is now future product work, not a
   shipped contract. The old schema-only reservations were pruned; re-add them
   only with producer data, visible consumers, schema/codegen updates, and wiring
   proof in the same package.
3. Pricing is source-audited but not public-copy-ready: Cartesia's live voice cost
   remains legacy-derived/unverified until account billing confirms the effective
   Sonic rate; do not market the €9.74/€97k headline as verified.
4. Launch screenshots are owned under `docs/launch/screenshots/`; the canonical
   first-package subset is curated in that manifest. Do not stage alternates by
   accident.
5. Runtime behavior has partial source-mode diagnostic proof, but still needs
   full Tauri/DDJ live proof. Unit tests and `--session` handler checks do not
   prove GUI click paths, UI-log rendering, co-host citations, or long-set behavior;
   use the `drive-vibemix` loop before claiming runtime fixes.
6. Dev checkout CLAP/library-AI proof needs `uv sync --group dev --extra ai-local`
   if boot logs warn about missing `onnxruntime` and `tokenizers`.
7. Learn completion handoff is explicitly not release-ready:
   `.planning/handoffs/2026-05-30-learn-goal-complete-style-package.md:3-9`
   and lines 62-80 keep Course 3 routed audio as the honest gate.
8. Browser proof is partial by design: the UI build and pill Playwright suite
   now pass, but Learn browser E2E and macbook visual E2E remain unrun here.
9. Avoid the excluded GSD and beginner-path suites unless explicitly requested.
10. The `xfade`, `cues`, `automix_demo`, and `transition_clock` mix/audio files
    are tracked clean in this checkout, but still mark the owning lane if future
    edits reappear while the parallel mix investigation is active.
11. Mix/automix material is currently tracked clean in this checkout. Keep the
    lane isolated if future edits reappear while the parallel mix investigation
    is active.
12. Memory ingest live proof depends on Package 12: local CLAP deps and model
    assets are ready, but a stale durable `memory.db` can still trip sqlite-vec
    before any UI/DDJ path is exercised unless the empty-table reconciliation
    ships with the runtime.

## Suggested Verification Matrix

Run these by lane after packaging. This list avoids the explicitly excluded
beginner-path suite names from the sweep notes.

```bash
# Repo hygiene
git diff --check
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
git status --short --untracked-files=all | awk '{print $2}' | rg '\.py$' | xargs uv run ruff check
# Known repo-wide lint debt as of 2026-05-31:
# uv run ruff check src tests

# Runtime memory / CLAP readiness
uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py
uv run ruff check src/vibemix/runtime/session_loop.py src/vibemix/memory/index_sqlite_vec_memory.py tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py

# Runtime Earned Wall
uv run pytest -q tests/runtime/test_coach_progress_emit.py tests/runtime/test_coach_skill_credit.py
uv run pytest -q tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py

# Cue materialization -> pill/Viber
uv run pytest -q tests/library/test_ingest.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py

# Viber/library live read
npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts

# Pill polish
npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts
npm --prefix tauri/ui run test:e2e:pill

# Learn operator action, not beginner-path suites
npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_operator_action.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts

# Pricing/cost/router
uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/llm/test_model_router.py

# Live TTS shutdown hygiene
uv run pytest -q tests/test_main_smoke.py -k close_tts_chain

# Owned-deck mini-player and judge
uv run pytest -q tests/audio/test_grid.py tests/audio/test_miniplayer.py tests/learn/test_beatmatch_judge.py
uv run pytest -q tests/audio/test_grid.py tests/audio/test_miniplayer.py tests/learn/test_beatmatch_judge.py tests/learn/test_judge_credits_beatmatch.py

# Dev MCP server
uv run pytest -q tests/runtime/test_dev_mcp_server.py

# IPC/tooling checks before shipping schema/handler work
uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py
uv run python scripts/check_ipc_schema.py

# Source-mode diagnostic bus, partial live proof
uv run python -m vibemix --session
# In another shell, use current-source ws_trigger/tool_ws_trigger_async for
# ipc.status.recheck and ipc.profile.view. Restart the MCP host first if testing
# through the callable MCP tool process.

# Webview and desktop shell
npm --prefix tauri/ui run build
cargo check --manifest-path tauri/src-tauri/Cargo.toml
```

## Hold Lane: Mix/Audio Work Owned Elsewhere

Purpose: keep timing/crossfade/mix-core experiments out of the shippable packages
until the parallel mix investigation lands or explicitly hands them back.

Current scan note: the mix/audio files below are tracked clean at this point in
the checkout. Keep this hold lane as ownership guidance if future edits reappear
while the parallel mix investigation is active.

| File | Status |
|---|---|
| `src/vibemix/audio/cues.py` | Hold; new cue/audio helper work appeared during Package 12. |
| `tests/audio/test_cues.py` | Hold with `cues.py`; do not fold into Package 12. |
| `src/vibemix/runtime/automix_demo.py` | Hold; new automix demo/mix work appeared during Package 12. |
| `scripts/automix_demo_smoke.py` | Hold with `automix_demo.py`; manual smoke helper for the mix investigation. |
| `tests/runtime/test_automix_demo.py` | Hold with `automix_demo.py`; do not fold into runtime memory readiness. |
| `src/vibemix/audio/xfade.py` | Hold; new audio/mix work appeared after the first package split. |
| `tests/audio/test_xfade.py` | Hold with `xfade.py`; do not fold into Package 8 without explicit review. |
| `src/vibemix/state/transition_clock.py` | Hold; drop-timing/cohost behavior groundwork with no production integration yet. |
| `tests/state/test_transition_clock.py` | Hold with `transition_clock.py`. |

## Suggested Commit Order

1. `docs(planning): document dirty tree shipping lanes`
2. `chore(agent-tooling): add live verification and IPC helper tooling`
3. `fix(session-ipc): wire status recheck errors and citation telemetry`
4. `fix(ipc): prune stale bus contracts`
5. `fix(library-cues): materialize auto and anlz hot cues end to end`
6. `feat(library-ui): ground Viber live read with deck-pair context`
7. `feat(pill): polish next-suggestion care interactions`
8. `feat(learn): bridge route-mismatch operator actions`
9. `feat(learn-audio): credit beatmatching from beatmatch judge`
10. `fix(learn-runtime): refresh earned wall after live cited credits`
11. `feat(library-cost): add live-stack budget model`
12. `docs(launch): package launch collateral and screenshots`
13. `fix(memory): reconcile stale sqlite-vec embedding dimensions`

Every commit should be DCO signed (`git commit -s`) per repo guidelines.
