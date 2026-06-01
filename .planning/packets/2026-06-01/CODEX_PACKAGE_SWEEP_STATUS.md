# CODEX Package Sweep Status

Date: 2026-06-01
Verifier: Codex
Scope: dirty-tree package verification, durable packet archive, and fresh macOS artifact proof

## Current State

The package ledger is mechanically green:

```text
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
OK: 5569 dirty paths covered by .planning/handoffs/2026-05-31-package-checklist.md; 3 generated launch previews ignored.
OK: every dirty path is assigned to an Include/Hold lane.
```

Durable packet archive:

- Archive: `.planning/packets/2026-06-01/`
- Packet markdown docs: 39 total
- READY packets: 32
- HOLD packets: 3
- Gold structure map: 1
- Scratch `/tmp/vibemix-codex-inbox/` is no longer source of truth.

## Freshly Verified / Refreshed In This Codex Pass

- Package 0/0B-0H: `CODEX_READY-planning-control-plane.md`
- Package 0I: `CODEX_READY-product-posture-docs-cleanup.md`
- Active hold lanes: `CODEX_HOLD-open-hold-lanes.md`
- FLX4 live acceptance attempt: `CODEX_HOLD-flx4-live-acceptance-current.md`
- Package 4: `CODEX_READY-auto-anlz-hot-cue-pipeline.md`
- Package 5: `CODEX_READY-library-ui-live-read-context.md`
- Package 6: `CODEX_READY-compact-pill-polish.md`
- Package 7: `CODEX_READY-learn-operator-action-bridge.md`
- Package 8: `CODEX_READY-beatmatch-judge-honesty-boundary.md`
- Package 9: `CODEX_READY-earned-wall-live-refresh.md`
- Package 10: `CODEX_READY-live-stack-cost-pricing-model.md`
- Package 11: `CODEX_HOLD-launch-collateral.md`
- Package 12: `CODEX_READY-runtime-memory-clap-readiness.md`
- Package 13: `CODEX_READY-tauri-sidecar-bundle-freshness-guard.md`
- Package 13B: `CODEX_READY-macos-signing-notarization-flow.md`
- Package 14: `CODEX_READY-live-tts-shutdown-hygiene.md`
- Package 15: `CODEX_READY-desktop-auto-master-16ch-upgrade.md`
- Package 5E/5F follow-up: `CODEX_READY-library-staleness-replay-on-connect.md`

Previously recovered/verified packets from the same archive remain indexed in
`INDEX.md` and the package checklist.

Landed commits in this pass:

- `d93e40cf feat(library-cost): add live stack budget model` - Package 10.
  This committed the cost/pricing modules, `library budget --stack live` CLI
  hunks, router aliases/tests, pricing docs, and the Package 10 packet. The
  remaining dirty assignment for Package 10 is from shared `src/vibemix/__main__.py`
  carrying other packages' unstaged hunks, not from unlanded Package 10 code.

## Gold Structure

`CODEX_GOLD_STRUCTURE.md` now groups the packet archive into landing streams
instead of forcing future agents to reason packet-by-packet:

- Gold 0 - control plane and product truth
- Gold 1 - AI observability and eval gate
- Gold 2 - session IPC and desktop transport
- Gold 3 - library, Viber, cues, and set prep
- Gold 4 - Learn and Earned Wall
- Gold 5 - speech truth, Judge, and mascot
- Gold 6 - runtime, packaging, signing, and audio boot
- Gold 7 - economics, posture, and launch surface

The map preserves LAND/HOLD boundaries. It is a landing guide, not a license to
bundle HOLD lanes into product commits.

## Current Codex Continuation, 2026-06-01 09:17 +0300

This pass verified multiple LAND packet groups against the current dirty tree,
without staging or committing.

### Packages 4/5/6 - cues, Viber live-read, compact pill

- Package 4 hot-cue pipeline:
  `uv run pytest -q tests/library/test_ingest.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py`
  passed with 88 tests.
- Package 4 cue-agreement cross-check:
  `uv run pytest -q tests/library/test_ingest.py tests/library/test_cue_agreement.py`
  passed with 23 tests.
- Package 5 library UI live-read:
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 73 tests, and
  `uv run pytest -q tests/library/test_live_context_cli.py` passed with 40 tests.
- Package 6 compact pill:
  `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts`
  passed with 167 tests, and `npm --prefix tauri/ui run test:e2e:pill` passed
  with 16 browser tests.
- Shared proof for this group: `npm --prefix tauri/ui run build`,
  focused Ruff checks, and focused `git diff --check` passed.

### Packages 2/3 - IPC spine and contract cleanup

- Static wiring: `which_handler` reported both-end wiring for
  `ipc.status.recheck`, `ipc.profile.view`, `ipc.session.snapshot`,
  `ipc.session.citation`, `ipc.session.overlay-highlight`, and
  `ipc.library.staleness_nudge`.
- Schema and wiring gates passed:
  `uv run python scripts/check_ipc_schema.py`,
  `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`,
  and `npm --prefix tauri/ui run check:ipc`.
- Python IPC/session suite:
  `uv run pytest -q tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_mood_change_envelope.py tests/wizard/test_wizard_loop_ipc.py tests/runtime/test_session_loop.py tests/ui_bus/test_status_tick.py tests/runtime/test_ws_bus_snapshot.py`
  passed with 174 tests.
- UI session/settings suite:
  `npm --prefix tauri/ui test -- src/settings/components/profile-panel.spec.ts src/settings/components/citation-diagnostics.spec.ts tests/settings/drawer.spec.ts tests/settings/staleness-banner.spec.ts tests/mock-transfer-contract.spec.ts tests/session/components.spec.ts tests/session/render-loop.spec.ts tests/session/render-loop-actions.spec.ts tests/session/router-teardown.spec.ts tests/session/ws-bridge.recordings.spec.ts`
  passed with 146 tests.
- Rust focused tests passed separately:
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml resolve_sidecar`
  passed with 5 tests, and
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds`
  passed with 30 tests.
- Shared proof for this group: `npm --prefix tauri/ui run build`, focused Ruff,
  and focused `git diff --check` passed. `check:ipc` rewrote
  `tauri/ui/src/ipc/messages.ts` and `tauri/ui/src/ipc/validator.generated.mjs`;
  those generated files must land with Package 2/3 if staged.

### Packages 7/9 - Learn operator bridge and Earned Wall refresh

- Learn operator UI/transport:
  `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_operator_action.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  passed with 55 tests.
- Curriculum projection:
  `uv run python scripts/export_learn_curriculum_meta.py --check` passed, and
  `uv run pytest -q tests/learn/test_curriculum_projection.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py`
  passed with 45 tests.
- Learn honesty/Earned Wall companion:
  `uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py`
  passed with 37 tests.
- Shared proof for this group: `npm --prefix tauri/ui run build`, focused Ruff,
  and focused `git diff --check` passed.

Boundary preserved: Packages 7/9 prove operator-action transport and backend
Earned Wall refresh emission. They still do not prove a live desktop Earned Wall
repaint from a real cited controller/audio event.

### Packages 12/13/13B/13C/14/15 - runtime and release support

- Model readiness:
  `uv run python -m vibemix library models --json` reported CLAP ONNX installed
  and required-ready, CUE-DETR installed, `required_ready: true`, and
  `all_ready: true`.
- Runtime memory, install, binary-verifier, TTS shutdown, and desktop audio tests:
  `uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py tests/dist/test_verify_binary.py tests/test_main_smoke.py::test_close_tts_chain_closes_nested_providers_once tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams tests/test_audio_macos.py tests/audio/test_device_select.py`
  passed with 127 tests.
- Signing workflow hardening:
  `bash -n scripts/dist/sign_macos.sh` passed, and
  `uv run pytest -q tests/security/test_release_yml_signing_skips.py`
  passed with 15 tests.
- Sidecar bundle freshness:
  `uv run python scripts/dist/check_sidecar_bundle_ready.py` passed for
  `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin`.
- Binary scan:
  `uv run python -m scripts.dist.verify_binary tauri/src-tauri/target/release/bundle/macos/vibemix.app --report /tmp/vibemix-codex-checks/verify-report-current-macos-app.json`
  scanned 407 entries with 0 hits.
- Rust/package support:
  `cargo check --manifest-path tauri/src-tauri/Cargo.toml` passed.
- Shared proof for this group: focused Ruff and focused `git diff --check`
  passed.

Boundary preserved: these checks prove source/package support gates and the
currently present local app bundle verifier target. They do not re-sign,
re-notarize, or prove final audible DJ live acceptance.

### Packages 1A/1B/1C/1E/1F/1G - AI observability and eval automation

- AI-message observability spine:
  `uv run pytest -q tests/scripts/test_verify_ai_observability.py tests/runtime/test_ai_observability.py tests/eval/test_judge_pro_rubric.py tests/agent/test_dj_cohost.py::test_llm_node_logs_ai_message_observability_with_moves tests/agent/test_dj_cohost.py::test_llm_node_ai_message_uses_prompt_time_mixer_snapshot tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/bench/test_run_fake.py::test_successful_cell_records_ai_message_observability tests/bench/test_run_fake.py::test_parked_cell_records_ai_message_observability tests/state/test_deck_vision.py::test_vision_read_records_ai_message_observability tests/state/test_deck_vision.py::test_vision_error_records_parked_ai_message tests/learn/test_runtime_evidence_grounding.py::test_runtime_logs_learn_milestones_to_session_event_sink tests/learn/test_observer_boot_wiring.py::test_observer_tutor_speak_is_logged_as_ai_message tests/debrief/test_tldr_length_60_to_90s.py::test_generate_tldr_text_raises_on_gemini_exception tests/debrief/test_drill_citations_resolve.py::test_generate_drills_raises_after_retries_exhausted`
  passed with 38 tests.
- Debrief backend and UI hygiene:
  `uv run pytest -q tests/debrief` passed with 111 tests, and
  `npm --prefix tauri/ui test -- src/debrief/__tests__/drills-panel-shape.spec.ts src/debrief/__tests__/tldr-player.spec.ts src/debrief/__tests__/error-banner.spec.ts src/debrief/__tests__/stripper-roundtrip.spec.ts src/debrief/__tests__/recording-row-debrief-button.spec.ts src/debrief/__tests__/recording-row-debrief-disabled.spec.ts`
  passed with 35 tests.
- Eval report and release-wrapper tests:
  `uv run pytest -q tests/eval/test_cohost_viber_session_report.py tests/eval/test_check_cohost_viber_autopilot_sh.py tests/eval/test_check_cohost_viber_corpus_benchmark_sh.py tests/eval/test_check_cohost_viber_matrix_sh.py tests/eval/test_check_cohost_viber_live_rehearsal_sh.py tests/eval/test_check_cohost_viber_runtime_canaries_sh.py`
  passed with 79 tests.
- Static gates passed: `bash -n` across the cohost/Viber release wrappers and
  focused Ruff across the observability/eval/debrief surfaces.
- Session artifact verifier passed on both recorded sessions:
  `20260531-161228` produced 1 live-coach row, 1 artifact pair, 1 deck-mixer
  row, 8 checked artifact paths, and `ok: true`; `20260531-154932` produced
  20 live-coach rows, 20 artifact pairs, 3 move-bearing rows, 20 deck-mixer
  rows, 160 checked artifact paths, and `ok: true`.
- Global Viber/Codex verifier passed with 17 global rows, 1 artifact pair,
  35 checked artifact paths, and `ok: true`.
- `uv run python -m vibemix eval latest-session --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-161228" --no-viber --json`
  exited 0 with `ok: true`, no blocker/care issues, and two watch-only issues.
- Autopilot wrapper passed against the same session:
  `PASS check_cohost_viber_autopilot: status=clean gate_ok=True release_gate_ok=True ... blockers=0 care=0 watch=2`.
- Runtime canaries passed:
  `PASS check_cohost_viber_runtime_canaries: ok=True canaries=8 exercised=8 passed=8 failed=0 missing=0`.
- Matrix wrapper passed in automation mode with FLX4 skipped:
  `PASS check_cohost_viber_matrix: mode=automation ok=True autopilot=True corpus=True runtime=True flx4=skip`.
- Live rehearsal no-start smoke failed as expected when no live socket was
  listening:
  `FAIL check_cohost_viber_live_rehearsal: live socket missing and COHOST_VIBER_REHEARSAL_START_LIVE=never`,
  exit code 1.

Boundary preserved: this source-level bundle proves observability, debrief,
deterministic eval reporting, runtime canaries, and wrapper composition. It does
not prove live FLX4/audio acceptance, because that still requires a running app,
audible deck audio, and physical controller motion inside the proof window.

### Packages 5B/5C/5D/5E/5F - Viber freshness and library guardrail bundle

- Viber library request/live-context guard:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/library/test_codex_curate_stop_reason.py`
  passed with 144 tests.
- Freshness/status/watcher/refresh IPC stack:
  `uv run pytest -q tests/library/test_staleness.py tests/library/test_stats_cli.py tests/library/test_setprep_tools.py tests/ui_bus/test_messages_schema.py tests/ipc/test_library_schemas.py tests/runtime/test_ws_bus.py tests/test_main_smoke.py`
  passed with 194 tests.
- Focused stale set-prep and live-request guard:
  `uv run pytest -q tests/library/test_toolset.py tests/library/test_mcp_server_clarification.py tests/library/test_clap_runtime_errors.py tests/library/test_curate_unify.py tests/library/test_codex_curate.py -k 'library_request or non_live_outcome or live_context or chat_with_codex'`
  passed with 37 tests and 93 deselected.
- Settings/library UI:
  `npm --prefix tauri/ui test -- tests/settings/staleness-banner.spec.ts tests/settings/library-panel.spec.ts tests/settings/drawer.spec.ts src/library/api.test.ts src/library/chat.test.ts src/library/build.test.ts src/library/curate.test.ts`
  passed with 145 tests.
- IPC/build/Rust gates passed:
  `uv run python scripts/check_ipc_schema.py`,
  `npm --prefix tauri/ui run check:ipc`,
  `npm --prefix tauri/ui run build`, and
  `cargo check --manifest-path tauri/src-tauri/Cargo.toml`.
- Focused Ruff and focused `git diff --check` passed across the Viber
  freshness/library guardrail files.

Boundary preserved: this bundle proves the source-level Viber library request
guard, freshness status, stale-tool fail-closed behavior, UI stale banner/action
plumbing, and sticky nudge delivery tests. It does not prove the final packaged
DMG shows the stale banner after the replay fix, nor that a real Viber/Codex
turn unblocks only after a live refresh; those remain final acceptance checks.

### Packages 8B/8C/8D/8E - speech truth, Judge evidence, and mascot reactions

- Judge voice plus anti-slop prompt/runtime tests:
  `uv run pytest -q tests/intel/test_judge_voice.py tests/runtime/test_coach_live_judge_run.py tests/state/test_coach_judge_voice_prompt.py tests/state/test_judge_and_record.py tests/state/test_judge_citation_schema_mirror.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
  passed with 108 tests.
- Citation/grounding/linter regression stack:
  `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
  passed with 108 tests.
- No-spoken-fallback and live-claim guard focused stack:
  `uv run pytest -q tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py -k 'live_claim_guard or deck_audio_parts_not_attached or event_audio_capture_context' tests/state/test_deck_context.py -k 'live_claim_guard or live_claim_policy' tests/library/test_codex_curate.py -k 'library_request or live_context or chat_with_codex' tests/library/test_live_context_cli.py -k 'verify_live_reply' tests/eval/test_cohost_viber_session_report.py -k 'live_claim_guard or spoken_live_claim_guard'`
  passed with 45 tests and 285 deselected.
- Audio-vibe prompt contract:
  `uv run pytest -q tests/prompts/test_matrix.py -k 'audio_vibe or double_opt_out or grammar'`
  passed with 20 tests and 119 deselected.
- Emote/mascot bridge:
  `uv run pytest -q tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/agent/test_dj_cohost.py::test_llm_node_strips_unknown_emote_tags_without_mascot_intent tests/agent/test_dj_cohost_streaming_pipe.py tests/e2e/test_seam_p31__ws_bus.py`
  passed with 43 tests.
- Mascot UI:
  `npm --prefix tauri/ui test -- src/mascot/reaction-intent.test.ts src/mascot/event-dispatcher.test.ts`
  passed with 22 tests.
- Shared proof for this group: `uv run python -m py_compile` across the
  cohost/emote/music-state/ws-bus modules, focused Ruff, focused
  `git diff --check`, and `npm --prefix tauri/ui run build` all passed.

Boundary preserved: this source-level bundle proves the Judge evidence path,
hard no-spoken-fallback guard, prompt steering, and mascot reaction bridge. It
does not prove a live two-deck judged transition artifact or a visible Tauri
mascot reaction from a live co-host response; those remain live acceptance
checks.

### Packages 0I/10/11 - product posture, internal economics, launch collateral

- Product posture docs:
  `uv run pytest -q tests/repo/test_readme_shape.py tests/repo/test_readme_feature_matrix_sync.py tests/repo/test_oss_presence.py tests/launch/test_launch_docs.py tests/install/test_windows_smartscreen_doc.py`
  passed with 68 tests.
- Product posture grep found only bounded internal/historical wording hits in
  planning/release-prep docs, not active public false-release or old OSS-first
  positioning.
- Live-stack economics:
  `uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/llm/test_model_router.py tests/e2e/test_phase_41_latency_stack_integration.py tests/repo/test_live_spike_scaffold.py`
  passed with 62 tests.
- Hardcoded model gate passed:
  `bash scripts/release/check_no_hardcoded_model.sh`.
- Live-stack budget CLI passed:
  `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3`
  reported `0.4857 EUR/session`, `9.74 EUR/DJ-month`,
  `97,374 fleet EUR/mo`, dominant leg `TTS`, and Cartesia Sonic marked
  `! UNVERIFIED`.
- JSON budget output parsed successfully and preserved
  `Cartesia Sonic` with `verified: false`.
- Launch collateral mechanics passed: `uv run ruff check docs/launch/.build_talking.py`,
  the talking-page builder round-tripped a generated HTML file, generated launch
  previews are ignored by `.gitignore`, selected screenshots/media exist, and
  focused `git diff --check` passed.
- Package checker remains green after this grouped proof:
  `5569 dirty paths covered`, `3 generated launch previews ignored`, and every
  dirty path assigned to an Include/Hold lane.

Boundary preserved: Packages 0I and 10 are LAND. Package 11 remains HOLD
because public/partner launch copy still overclaims release posture,
free/open-source posture, cloud/privacy guarantees, cue-export GUI readiness,
Learn readiness, and absolute grounding gates.

Package 10 landing note: `d93e40cf` landed the live-stack cost model as the
first clean LAND slice. No HOLD launch collateral was staged.

## Current Release Reality

1. Package 13 sidecar freshness blocker is cleared, and a fresh Apple Silicon
   Tauri app/DMG has now been rebuilt from that sidecar. The first rebuild
   proved the packaging/signing flow:

   ```text
   uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec
   uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only
   [prepare-tauri] OK: sidecar bundle ready: .../vibemix-core-aarch64-apple-darwin
   ```

   The embedded IPC schema byte-matches source. Then:

   ```text
   bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats
   [macos-app-bundle] OK: .../vibemix.app/.../vibemix-core-aarch64-apple-darwin
   [macos-dmg-artifact] OK: /var/.../vibemix.app
   ```

   Earlier local unsigned DMG rehearsal:
   `tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg`,
   119464615 bytes, mtime `2026-06-01 07:36:28 +0300`, sha256
   `ae929e88c3ef24d092cfb915b6a01780e28353730e86a120212e5bd6724b321d`.

   Then the fresh `.app` was signed/notarized into a separate output directory:

   ```text
   ./scripts/dist/sign_macos.sh --output-dir dist/fresh-20260601 tauri/src-tauri/target/release/bundle/macos/vibemix.app
   [sign_macos] DONE: vibemix-0.0.1.dmg notarized + stapled + verified
   dist/fresh-20260601/vibemix-0.0.1.dmg
   ```

   Fresh signed/notarized DMG:
   `dist/fresh-20260601/vibemix-0.0.1.dmg`, 119953279 bytes, mtime
   `2026-06-01 07:42:22 +0300`, sha256
   `8f52423c7bdaf6a4bb9657606951532675f97239ecc857466c9721a39b26820b`.

   Independent checks passed: `xcrun stapler validate`, `spctl -a -vvv -t
   install`, `check_macos_dmg_artifact_ready.py --smoke library-stats`,
   `codesign --verify --deep --strict`, app `spctl`, and `verify_binary.py`
   (`scanned=407`, `hits=[]`).

   Important drift: later Rust/app fixes for sidecar Quit, stale output-device
   selection, mic opt-in, and CoreAudio-safe input opening were rebuilt after
   this signing pass. Therefore `dist/fresh-20260601/vibemix-0.0.1.dmg` proves
   the signing/notarization flow, but it is no longer the latest-code artifact.

2. Latest-code signed packaged launch and Quit now pass, but it now predates a
   later source fix for library staleness replay:

   Latest rebuild:

   ```text
   bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats
   [macos-app-bundle] OK: .../vibemix.app/.../vibemix-core-aarch64-apple-darwin
   [macos-dmg-artifact] OK: /var/.../vibemix.app
   ```

   Latest unsigned local DMG:
   `tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg`,
   119468447 bytes, mtime `2026-06-01 08:17:10 +0300`, sha256
   `efe673e4b0a36acd7723a650630008b8287df1a835063e556aa0c7d3c051fdfc`.

   Latest-code signing/notarization pass:

   ```text
   ./scripts/dist/sign_macos.sh --output-dir dist/fresh-20260601-latest tauri/src-tauri/target/release/bundle/macos/vibemix.app
   [sign_macos] DONE: vibemix-0.0.1.dmg notarized + stapled + verified
   ```

   Latest signed/notarized DMG:
   `dist/fresh-20260601-latest/vibemix-0.0.1.dmg`, 119957189 bytes, mtime
   `2026-06-01 08:32:00 +0300`, sha256
   `a5b56658595bbdae11e5558cdac35f266244192c5b37a51ff6361587e4566b29`.

   Independent checks passed: `xcrun stapler validate`, `spctl -a -vvv -t
   install`, `check_macos_dmg_artifact_ready.py --smoke library-stats --json`,
   `codesign --verify --deep --strict`, app `spctl`, and `verify_binary.py`
   (`scanned=407`, `hits=[]`). Notary submission log
   `8975c0c9-053b-4d95-94d0-ffa5e9044162` reports `status=Accepted`.

   Normal packaged launch from an app copied out of the latest signed DMG:

   ```text
   open -n /tmp/vibemix-signed-install.Tp4lk7/vibemix.app
   ```

   Evidence:

   - Process tree: app PID `56437`, bundled sidecar PID `56441`.
   - Listener: `vibemix-core` PID `56441` owns `127.0.0.1:8765`.
   - `sidecar_status`: `ws_reachable=true`, `dev_sidecar=false`,
     `gemini_key_present=true`.
   - UI log reached `rust bridge ws-state {"state":"connected"}`.
   - `ws_observe` captured `ipc.status.tick` frames with `livekit=ok`,
     `gemini=ok`, `midi=1`, `screen=unavailable`.

   Normal Quit:

   ```text
   osascript -e 'tell application id "world.bravoh.vibemix" to quit'
   ```

   Result: no `vibemix.app` or bundled sidecar process remained, no listener
   stayed on `127.0.0.1:8765`, and `sidecar_status` returned
   `ws_reachable=false`.

   Drift after this artifact: Codex found that the packaged sidecar emitted
   `ipc.library.staleness_nudge` before the Tauri websocket connected, so the UI
   could miss the stale-library banner. Current source now retains the latest
   nudge and replays it to late clients; focused tests passed (`128 passed`) and
   a source run captured the late-client nudge. Rebuild/re-sign before claiming
   packaged proof for Package 5E/5F.

3. Earlier signed packaged launch smoke partially passed, then exposed the
   packaged shutdown blocker that is now fixed in current source:

   Launch command:

   ```text
   VIBEMIX_INPUT_DEVICE='BlackHole 16ch' VIBEMIX_DECK_AUDIO_CHANNELS=auto VIBEMIX_DROP_DEBUG=1 tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/MacOS/vibemix
   ```

   Evidence:

   - `sidecar_status`: `ws_reachable=true`, `dev_sidecar=false`,
     `gemini_key_present=true`.
   - Process tree: app PID `41324` spawned bundled sidecar PID `41328` from
     `Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/`.
   - Session dir: `20260601-074500`.
   - `ws_observe` captured 100 `ipc.session.snapshot` frames.
   - UI log reached `rust bridge ws-state {"state":"connected"}`.
   - Status tick: `gemini=ok`, `livekit=ok`, `midi=1`, `screen=unavailable`.

   Boundary: this was a packaged boot/transport proof, not final live
   acceptance. Music meters stayed `0`, no MIDI move events were captured in
   the short snapshot window, and a direct `kill -TERM` of the app left the
   sidecar orphaned until PID `41328` was killed.

   Normal Quit was then tested via:

   ```text
   open -n tauri/src-tauri/target/release/bundle/macos/vibemix.app
   osascript -e 'tell application id "world.bravoh.vibemix" to quit'
   ```

   That also left bundled sidecar PID `41742` alive as PPID 1 and kept
   `127.0.0.1:8765` reachable until the sidecar was killed manually. This was a
   real packaged shutdown blocker; the later current-source unsigned package
   proof above verifies normal Quit now cleans up the bundled sidecar.

4. Package 11 launch collateral is HOLD:

   The media/screenshot mechanics pass, but public/partner copy still overclaims
   release posture, free/open-source posture, cloud/privacy, cue-export GUI, and
   Learn readiness.

5. Several lanes are intentionally HOLD:

   - Local code-signing certificate dumps
   - Tauri sidecar log drain
   - Tauri cohost restart recovery until the current Rust fixes are landed
     with the package
   - Local MOSS TTS ONNX runtime spike
   - Deck audio controller-weighted master context
   - Mix timing oracle / live drop timing
   - Cue export folder bridge
   - Real CLAP retrieval eval gate
   - Eval judge cross-check gate
   - FLX4 live proof artifacts and eval run archives

6. Product acceptance is not complete:

   The current tree has many verified LAND slices and latest-code signed
   packaged boot/Quit proof. A current FLX4 live acceptance attempt from the
   signed copied-DMG app reached live context and saw DDJ-FLX4 MIDI/audio
   presence, but failed release readiness because no direct MIDI motion, recent
   controller move, audible deck audio, or resolved deck identity was captured.
   Final release still needs real audible live acceptance and launch collateral
   cleanup.

## Next Execution Order

Recommended next sequence when moving from verification into landing:

1. Surgical staging/commits of LAND packages only.

   Use hunk-level staging for shared files:

   - `src/vibemix/__main__.py`
   - `src/vibemix/runtime/session_loop.py`
   - `src/vibemix/runtime/coach.py`
   - `src/vibemix/agent/dj_cohost.py`
   - IPC schema/generated TS files

2. Run final live acceptance with the latest signed artifact and current
   hardware.

   ```text
   dist/fresh-20260601-latest/vibemix-0.0.1.dmg
   ```

3. Live acceptance must prove:

   - sidecar bus online
   - UI online
   - Viber library actions grounded
   - co-host no unsupported mixer/deck causality
   - AI-message observability rows present
   - Learn progress only credits live-citable skills
   - audible deck audio and cited co-host moment captured
   - normal app Quit stops the bundled sidecar on the signed artifact

4. Rewrite or hold launch collateral until it matches the verified product
   reality.

Latest live acceptance attempt:

```text
COHOST_VIBER_FLX4_OUT_DIR=.planning/eval-runs/flx4-live-context-codex-latest-signed COHOST_VIBER_FLX4_WAIT_READY_S=5 COHOST_VIBER_FLX4_TIMEOUT_S=3 COHOST_VIBER_FLX4_FRAMES=180 COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S=3 bash scripts/release/check_flx4_live_context.sh
FAIL check_flx4_live_context: midi_port=DDJ-FLX4 audio_device=True live_ok=True live_ready=False diagnosis=missing_physical_proof frames=115 controller_connected=True recent_moves=False audio_observed=False blockers=20 direct_midi=False direct_midi_frames=0 midi_motion_diag=no_direct_midi_motion_observed
```

## Important Truths To Preserve

- Viber/Crate is not entirely unplugged. The recovered Viber packet had that
  inverted; read `viber-capability-CORRECTION.md`.
- The `ipc.library.*` websocket path is vestigial. The real product path is
  Tauri `invoke()`.
- The old signed/notarized `dist/vibemix-0.0.1.dmg` proves signing flow, not
  latest integrated product state. The signed/notarized
  `dist/fresh-20260601/vibemix-0.0.1.dmg` also predates the latest
  sidecar-Quit/CoreAudio boot-safety fixes. The latest signed proof artifact is
  `dist/fresh-20260601-latest/vibemix-0.0.1.dmg`, but it predates the
  library-staleness replay-on-connect fix.
- Beatmatch Mastered remains intentionally uncreditable until a real
  `BEATMATCH_GRADED` producer exists.
- No spoken fallback/slop is acceptable as product behavior. Guarded/eval-only
  text may be logged, but unsafe fallback text must not be voiced.
