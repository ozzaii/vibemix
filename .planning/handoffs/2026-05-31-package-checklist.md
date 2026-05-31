# Dirty Tree Package Checklist - 2026-05-31

This checklist turns the current all-over dirty tree into packages that can be reviewed,
staged, and shipped deliberately. It is derived from
`.planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md` and a fresh dirty-tree
scan on 2026-05-31.

## Guardrails

- Do not run or package GSD or the Learn beginner path unless the user explicitly asks.
- Keep mix/audio/drop-timing work isolated from the other cloud session currently digging
  into mix core. In this tree, `transition_clock` is a hold lane.
- Treat live proof as partial. Source-mode `uv run python -m vibemix --session`
  reaches `127.0.0.1:8765`, answers schema-valid diagnostic frames, normalizes
  legacy numeric-`ts` local drive frames at runtime ingress, and has local CLAP
  runtime dependencies installed. Full flagless runtime now also sees `DDJ-FLX4`
  with `livekit=ok`, `gemini=ok`, and `midi=1`. Tauri dev-source boot now reaches
  the renderer/Rust bridge/pill path and records `BlackHole 16ch` deck-pair
  capture, but audible deck route, co-host citation, and long-set pass are still
  pending.
- Make DCO-signed commits with scoped Conventional Commit-style messages.
- Before any IPC package is considered shippable, run both schema and wiring checks:
  `uv run python scripts/check_ipc_schema.py`
  `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`

## Package 0 - Shipping Inventory Docs

Suggested commit: `docs(planning): document dirty tree shipping lanes`

Include:

- `.planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md`
- `.planning/handoffs/2026-05-31-maintainability-map.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `scripts/check_dirty_package_plan.py`
- `tests/scripts/test_check_dirty_package_plan.py`

Keep out:

- Product source changes. This package exists so reviewers can orient before code
  starts moving.

Proof already run:

- Cross-checked against `git diff --name-only` and `git ls-files --others --exclude-standard`.
- Confirmed every dirty tracked/untracked path is exactly listed in this checklist:
  `(git diff --name-only; git ls-files --others --exclude-standard) | sort -u | ...`
- Earlier package-checker proof before later parallel-session drift:
  `uv run python scripts/check_dirty_package_plan.py`
  passed: 169 dirty paths exactly listed; 3 generated launch previews ignored.
- Earlier strict package-checker proof before local MOSS TTS grew:
  `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passed: 169 dirty paths exactly listed; package summary prints Include/Hold
  assignment counts and shared dirty-path assignments; strict mode confirms every
  dirty path is assigned to a package or hold lane.
- Current refresh, 2026-05-31:
  `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passes with 201 dirty paths exactly listed after Packages 0, 0B, and 1 landed and
  the future-AI routing refresh classified the latest frontend proof,
  sexiest-live screenshots, Mixxx research, cue-export bridge, Local MOSS helper,
  and `CLAUDE.md` runtime-orientation drift; 3 generated launch previews are
  ignored, and every dirty path is assigned. The checker now reads staged
  (`git diff --cached --name-only`), unstaged (`git diff --name-only`), and
  untracked paths so a half-staged tree cannot produce a false green. The live
  tree includes `.planning/singularity/2026-05-31/*.md` research/census briefs,
  nested cue-export/Mixxx research maps, and the real-CLAP fixture README; those
  are assigned to hold lanes.
  Earlier in this same planning pass, the local MOSS TTS
  wrapper/runtime/test files are no longer dirty, `uv.lock` still carries the
  residual `sentencepiece` / `tts-local` lockfile diff, and the new
  drop-prediction helper/test plus `refresh.py` integration are assigned to the
  Mix Timing Oracle hold lane. The `refresh.py` hunk then grew inside the same
  assigned path to 64 insertions with opt-in `VIBEMIX_DROP_DEBUG` countdown
  logging; path coverage stayed green, but hunk stability did not.
- `uv run pytest -q tests/scripts/test_check_dirty_package_plan.py` passed:
  5 tests.
- `uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py`
  passed.
- Package 0 commit landed as
  `5fa5d4d8 docs(planning): document dirty tree shipping lanes`, with DCO
  signoff.

Remaining gate:

- Refresh the package checklist after each staged commit, because the dirty tree shape
  will change.

Stage packet when sessions pause:

1. Pre-stage evidence:
   `git status --short`,
   `git diff --shortstat`,
   `git ls-files --others --exclude-standard | wc -l`, and
   `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`.
2. Package 0 checks:
   `uv run pytest -q tests/scripts/test_check_dirty_package_plan.py` and
   `uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py`.
3. Stage only the five Include paths above. Because all five paths are currently
   untracked, rely on cached review commands after staging rather than unstaged
   `git diff --check`.
4. Post-stage evidence:
   `git diff --cached --name-only`,
   `git diff --cached --check`,
   `git diff --cached --stat`, and
   `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`.
5. Commit as `docs(planning): document dirty tree shipping lanes` with `git commit -s`
   only if the cached diff contains no product source and no hold-lane files.

Exact staging command packet, do not run while sessions are still active:

```bash
git add -- \
  .planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md \
  .planning/handoffs/2026-05-31-maintainability-map.md \
  .planning/handoffs/2026-05-31-package-checklist.md \
  scripts/check_dirty_package_plan.py \
  tests/scripts/test_check_dirty_package_plan.py

git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
uv run pytest -q tests/scripts/test_check_dirty_package_plan.py
uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py
```

Cached-diff acceptance list:

- `.planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md`
- `.planning/handoffs/2026-05-31-maintainability-map.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `scripts/check_dirty_package_plan.py`
- `tests/scripts/test_check_dirty_package_plan.py`

If `git diff --cached --name-only` prints anything else, unstage the extra path
before committing. In particular, Package 0 must not include `pyproject.toml`,
`uv.lock`, `src/`, `tauri/`, `tests/agent/test_local_tts.py`, launch/design
assets, `.claude/skills/`, or any hold-lane path.

Current evidence bundle draft, 2026-05-31:

```text
Package: Package 0 - Shipping Inventory Docs
Commit: 5fa5d4d8 docs(planning): document dirty tree shipping lanes
Scope: planning docs plus dirty-tree package checker only
Staged files: committed; no Package 0 paths remain untracked
Shared-file hunks: none; all Package 0 paths were standalone planning/tooling files
Checks:
  git diff --shortstat -> 94 files changed, 5085 insertions, 1746 deletions
  git ls-files --others --exclude-standard | wc -l -> 80
  uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary -> 174 dirty paths listed and assigned
  uv run pytest -q tests/scripts/test_check_dirty_package_plan.py -> 5 passed
  uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py -> clean
Live proof: none required; this package is planning-only
Generated artifacts: none
Keep-outs: no product source, no hold-lane files, no dependency churn, no refactors
Residual risk: refresh this bundle immediately before staging because parallel sessions can change dirty-path counts
```

Post-Package-0 rebaseline packet:

```text
Trigger: Package 0 has landed and the ledger/checker files are now tracked
Scope: update counts and package summaries only
Precondition: Package 0 cached diff contained exactly the five acceptance-list paths
Commands:
  git status --short
  git diff --shortstat
  git ls-files --others --exclude-standard | wc -l
  uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
  uv run pytest -q tests/scripts/test_check_dirty_package_plan.py
Update:
  .planning/handoffs/2026-05-31-maintainability-map.md Current State Index
  this checklist's package summary/counts if checker totals changed
  shared dirty-path assignment list if any shared path moved
Keep-outs:
  no product source
  no dependency manifests or lockfiles
  no generated IPC artifacts
  no launch/design assets
  no hold-lane promotion
Stop if:
  checker goes red
  any Package 0 path remains untracked after the commit
  the rebaseline diff contains behavior or dependency changes
```

## Package 1 - Agent Tooling And Live Verification

Suggested commit: `chore(agent-tooling): add live verification and IPC helper tooling`

Packaging decision: this is repo developer/operator tooling, not end-user product
runtime. It belongs in the source tree so agents and maintainers can prove live
behavior, but it should not be described as a customer-facing release feature.

Landed in `05ed0b91`:

- `AGENTS.md`
- `CLAUDE.md`
- `.gitignore`
- `.claude/hooks/post_edit_codegen.py`
- `.claude/settings.json`
- `.claude/skills/drive-vibemix/SKILL.md`
- `.claude/skills/drive-vibemix/references/observe-and-logs.md`
- `.claude/skills/drive-vibemix/scripts/ws_probe.py`
- `.claude/skills/ipc-wiring-checker/SKILL.md`
- `.claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
- `.claude/skills/vibemix-grounding-review/SKILL.md`
- `.claude/skills/vibemix-grounding-review/references/invariant-checks.md`
- `src/vibemix/runtime/dev_mcp_server.py`
- `tests/runtime/test_dev_mcp_server.py`
- `tests/runtime/test_drive_vibemix_ws_probe.py`

Post-commit note:

- The Package 1 `AGENTS.md` tooling hunk landed. The remaining dirty `AGENTS.md`
  hunk is the IPC count guidance and belongs to Package 3.

Keep out:

- `.claude/worktrees/**`
- `.claude/settings.local.json`
- Any local-only skill/cache files that are ignored and not part of `git status`.

Proof already run:

- `uv run pytest -q tests/runtime/test_dev_mcp_server.py`
  passed: 23 tests.
- `uv run ruff check src/vibemix/runtime/dev_mcp_server.py tests/runtime/test_dev_mcp_server.py scripts/check_dirty_package_plan.py`
  passed.
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
- `uv run python -m vibemix --session` reached `ws://127.0.0.1:8765`; MCP
  `sidecar_status` reported `ws_reachable: true`, and MCP `ws_observe` saw
  idle `ipc.session.snapshot` frames from the current source.
- `uv run pytest -q tests/runtime/test_dev_mcp_server.py`
  passed after the `ws_trigger` typed-IPC fix; coverage now asserts ISO
  `date-time` timestamps and immediate reply capture.
- Current-source `tool_ws_trigger_async` sent `ipc.status.recheck` with an ISO
  `ts` and received an immediate `ipc.status.tick` reply from the diagnostic bus.
- `uv run pytest -q tests/runtime/test_drive_vibemix_ws_probe.py tests/runtime/test_dev_mcp_server.py`
  passed: 29 tests. This covers both MCP `ws_trigger` and the human/agent
  `ws_probe.py --ipc` frame builder.
- `uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}' --watch ipc.status.tick --seconds 3`
  reached the diagnostic bus and printed `ipc.status.tick` with `midi=1`,
  `screen=ok`, `livekit=connecting`, and `gemini=down`.
- Fresh 2026-05-31 source-mode rerun reached the bus with
  `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session`; MCP observed
  30 Hz idle `ipc.session.snapshot` frames, and the same `ws_probe.py --ipc
  ipc.status.recheck` command returned `ipc.status.tick livekit=connecting
  gemini=down midi=0 screen=ok` with no schema violation. `midi=0` is expected
  here because the DDJ/controller was not attached.
- Latest 2026-05-31 source-mode re-probe after stale sidecar cleanup returned
  `ipc.status.tick livekit=connecting gemini=down midi=1 screen=ok`, proving the
  current source diagnostic bus can see the attached controller path. A follow-up
  `ipc.profile.view` probe returned `ipc.profile.view_result`. The probe process
  was stopped afterward and `127.0.0.1:8765` was left free.
- Connected-controller check: `mido.get_input_names()` and
  `uv run python scripts/sniff_controller.py --list` both reported `DDJ-FLX4`.
  The `gemini=down` value in the diagnostic `--session` probe is the structural
  loop's conservative default; the real Tauri sidecar launch path is flagless
  `python -m vibemix`, which enters the full live runtime and emits live status
  through `ws_broadcast`.

Remaining gate:

- Restart the MCP host before relying on the `ws_trigger` tool in a long run so
  it loads the current source and can return immediate same-socket replies. Older
  already-running MCP children may still have the numeric-`ts` sender in memory,
  but Package 2's runtime ingress normalizer now prevents that stale frame from
  schema-rejecting on current source.
- Prove the full source-mode helper path through UI log and session
  `events.jsonl` once the Tauri app runtime is available.

## Package 0B - Future AI Routing Handoff

Suggested commit: `docs(planning): add future ai routing handoff`

Landed in `d433a42d`.

Include:

- `.planning/handoffs/2026-05-31-future-ai-routing.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Product source changes.
- Research/census briefs that need separate citation review.
- Any hold-lane file promoted only because it is mentioned in the routing doc.

Reason:

- This is a small planning-only router for future AI sessions. It gives one
  clean doorway into the current dirty tree and explains how to use the
  checklist, maintainability map, and handoffs without rediscovering the entire
  `.planning/` directory.
- The package-checklist hunk only classifies newly appeared dirty paths and
  assigns this routing doc. It must not carry product behavior.

Proof before staging:

- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- .planning/handoffs/2026-05-31-future-ai-routing.md .planning/handoffs/2026-05-31-package-checklist.md`

## Hold Lane - Claude Runtime Orientation Drift

Suggested commit if/when selected: `docs(runtime): capture local live-run caveats`

Hold:

- `CLAUDE.md`

Reason:

- The current hunk documents Local MOSS invocation, packaged-GUI environment
  flag behavior, and deck passthrough/live audio caveats. It is useful
  orientation, but it is a shared agent doc and should not be smuggled into the
  future-AI routing package.
- If staged later, review it with the Local MOSS TTS, live runtime, and deck
  audio owners so the claims match the accepted package state.

Remaining gate:

- Stage by hunk only and keep the cached diff limited to the accepted runtime
  orientation notes.

## Package 0C - IPC Staging Packet

Suggested commit: `docs(planning): add ipc staging packet`

Include:

- `.planning/handoffs/2026-05-31-ipc-staging-packet.md`
- `.planning/handoffs/2026-05-31-future-ai-routing.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Product source changes.
- Generated IPC files, even if the packet discusses them.
- Runtime diagnostic, sidecar-log, cue/pill/library-live-read, design, launch,
  pricing, local TTS, and `__main__.py` hold lanes.

Reason:

- This is planning-only support for the next likely staging move: the combined
  Package 2 + Package 3 IPC contract review. It records the current contract
  evidence, stage list, keep-outs, verification commands, and split rules so a
  future agent can stage deliberately instead of reconstructing the package from
  the full checklist.

Proof before staging:

- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- .planning/handoffs/2026-05-31-ipc-staging-packet.md .planning/handoffs/2026-05-31-future-ai-routing.md .planning/handoffs/2026-05-31-package-checklist.md`

## Package 0D - Dependency Modernization Packet

Suggested commit: `docs(planning): add dependency modernization packet`

Include:

- `.planning/handoffs/2026-05-31-dependency-modernization-packet.md`
- `.planning/handoffs/2026-05-31-future-ai-routing.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `pyproject.toml`, `uv.lock`, `tauri/ui/package.json`,
  `tauri/ui/package-lock.json`, `tauri/src-tauri/Cargo.toml`, and `Cargo.lock`.
- Any dependency bump, generated file, or product source edit.

Reason:

- This packet turns the "lighter, faster, latest libs, no conflicts" ask into
  modernization rings with evidence and gates. It is planning-only and should
  not be bundled with actual dependency changes.

Proof before staging:

- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- .planning/handoffs/2026-05-31-dependency-modernization-packet.md .planning/handoffs/2026-05-31-future-ai-routing.md .planning/handoffs/2026-05-31-package-checklist.md`

## Package 0E - Refactor/Wiring Session Handoff

Suggested commit: `docs(planning): add refactor wiring handoff`

Include:

- `.planning/handoffs/2026-05-31-refactor-wiring-session-handoff.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Product source changes.
- Generated IPC files, dependency manifests, and package-lock files.
- Runtime diagnostic, Tauri sidecar-log, cue/pill/library-live-read, design,
  launch, pricing, local TTS, signing/notarization, and `__main__.py` hold lanes.

Reason:

- This is planning-only support for handing a bounded refactor/wiring lane to
  another session. It makes the recommended first move explicit: combined
  Package 2 + Package 3 IPC contract review, not a broad refactor of every
  floating dirty file.

Proof before staging:

- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- .planning/handoffs/2026-05-31-refactor-wiring-session-handoff.md .planning/handoffs/2026-05-31-package-checklist.md`

## Package 2 - Session IPC And Diagnostics Wiring

Suggested commit: `fix(session-ipc): wire status recheck errors and citation telemetry`

IPC staging rule: Package 2 and Package 3 both touch the schema/codegen baseline.
If they are staged separately, keep `messages.schema.json`, `messages.ts`,
`validator.generated.mjs`, Python wrappers, and count/parity tests together with
the package that changes the IPC count. Re-run `scripts/check_ipc_schema.py` and
the IPC wiring checker after each staged IPC package.

Include:

- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/ui_bus/schemas/library.py`
- `src/vibemix/ui_bus/__init__.py`
- `src/vibemix/ui_bus/validator.py`
- `src/vibemix/runtime/ws_bus.py`
- `src/vibemix/runtime/session_loop.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/mock-transfer/contract.ts`
- `tauri/ui/src/session/SessionLayout.ts`
- `tauri/ui/src/session/render-loop.ts`
- `tauri/ui/src/session/ws-bridge.ts`
- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/src/settings/components/citation-diagnostics.ts`
- `tauri/ui/src/settings/components/citation-diagnostics.spec.ts`
- `tauri/ui/src/settings/components/profile-panel.ts`
- `tauri/ui/src/settings/components/profile-panel.spec.ts`
- `tauri/ui/tests/session/components.spec.ts`
- `tauri/ui/tests/mock-transfer-contract.spec.ts`
- `tauri/ui/tests/session/render-loop-actions.spec.ts`
- `tauri/ui/tests/session/ws-bridge.recordings.spec.ts`
- `tauri/ui/tests/settings/drawer.spec.ts`
- `tests/runtime/test_session_loop.py`
- `tests/wizard/test_wizard_loop_ipc.py`
- `tests/ipc/test_library_schemas.py`
- `tests/ui_bus/test_status_tick.py`
- `tests/ui_bus/test_messages_schema.py`
- `tests/ui_bus/test_mood_change_envelope.py`
- `tests/ui_bus/test_recordings_messages.py`

Keep out:

- Debrief citation summary and event timeline behavior. Those contracts are now
  pruned from the shippable IPC baseline; re-add them only with a real producer,
  visible consumer, and full schema/codegen/count-test package.
- Library search/similar pruning if you want smaller review units; otherwise package 3
  can be combined with this one.

Proof already run:

- `uv run python scripts/check_ipc_schema.py`
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
- `uv run pytest -q tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_mood_change_envelope.py`
- `npm --prefix tauri/ui test -- tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui test -- src/settings/components/profile-panel.spec.ts src/settings/components/citation-diagnostics.spec.ts tests/settings/drawer.spec.ts tests/settings/staleness-banner.spec.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- Source-mode `uv run python -m vibemix --session` plus a schema-valid websocket
  `ipc.status.recheck` frame for `{"component":"midi"}` produced
  `ipc.status.tick` with `midi=1`, `screen=ok`, `livekit=connecting`, and
  `gemini=down`.
- The same schema-valid websocket client sent `ipc.profile.view` and received
  `ipc.profile.view_result` with `consent=true`, `bytes=321`, and the stored
  profile payload.
- Fresh 2026-05-31 source-mode rerun used `ws_probe.py --ipc ipc.profile.view
  --payload-json '{}' --watch ipc.profile.view_result --seconds 3` and received
  `ipc.profile.view_result` with stored profile fields. This proves the sidecar
  handler path; the Tauri Settings drawer lifecycle still needs GUI proof.
- Latest 2026-05-31 re-probe after stale sidecar cleanup again received
  `ipc.profile.view_result` from the current source diagnostic bus; the same run
  also reported `midi=1` on `ipc.status.tick`, and the probe was shut down cleanly.
- Rust launch-decision tests confirmed the Tauri sidecar still launches the dev
  source path as `uv run python -m vibemix`, appends `--wizard` only for wizard
  mode, and uses the bundled sidecar path when the dev flag is absent:
  `resolve_sidecar_flag_set_default_uses_uv_module_vibemix`,
  `resolve_sidecar_wizard_arg_appended_in_both_arms`, and
  `resolve_sidecar_flag_absent_returns_bundled`.
- `uv run pytest -q tests/wizard/test_wizard_loop_ipc.py tests/runtime/test_session_loop.py tests/ui_bus/test_status_tick.py`
  passed: 46 tests after adding the runtime ingress normalizer. Legacy local numeric
  timestamps are accepted only at the websocket/session ingress, while strict
  schema parsing still rejects numeric timestamps outside that boundary.
- `uv run ruff check src/vibemix/ui_bus/validator.py src/vibemix/runtime/ws_bus.py src/vibemix/runtime/session_loop.py tests/wizard/test_wizard_loop_ipc.py tests/runtime/test_session_loop.py tests/ui_bus/test_status_tick.py`
  passed for the ingress compatibility shim and focused tests.
- A stale already-running MCP `ws_trigger` child still emitted numeric `ts` for
  `ipc.status.recheck`; current source normalized it at ingress and no longer
  logged the earlier `[wizard bus] schema violation`.

Remaining gate:

- Full Tauri live app pass for `ipc.status.recheck`, `ipc.error`, and
  `ipc.session.citation`. The diagnostic bus proves sidecar handlers, not GUI
  click/log rendering paths.
- Live Settings/Profile pass in Tauri: opening Settings should issue one
  `ipc.profile.view`; closed boot/close should not spam profile requests.
- Live Settings/Library pass in Tauri: boot/open/close should
  keep a single `ipc.library.staleness_nudge` subscription, not one per drawer refresh.

## Hold Lane - Runtime Diagnostic Output Resilience

Suggested commit if/when selected: `fix(runtime): ignore closed diagnostic stdout`

Hold:

- `src/vibemix/runtime/diag.py`

Reason:

- The current hunk catches `BrokenPipeError` / `OSError` while writing the live
  diagnostic status line. That is runtime behavior, not IPC contract work, and
  should not ride with Package 2 unless a focused diagnostic-output package is
  intentionally selected.

Remaining gate:

- Run focused runtime diagnostics tests or add one before staging. Keep this out
  of docs-only routing/rebaseline commits.

## Package 3 - IPC Contract Cleanup

Suggested commit: `fix(ipc): prune stale bus contracts`

IPC staging rule: this package is the one that intentionally changes the top-level
IPC count to 72 by pruning five stale library bus contracts and two debrief
schema-only reservations. Do not split its schema/codegen/count-test files across
another commit unless Package 2 is intentionally combined with it.

Include:

- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/ui_bus/__init__.py`
- `src/vibemix/ui_bus/schemas/debrief.py`
- `src/vibemix/ui_bus/schemas/library.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `scripts/check_ipc_schema.py`
- `.claude/skills/ipc-wiring-checker/SKILL.md`
- `.claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
- `AGENTS.md`
- `src/vibemix/library/search.py`
- `src/vibemix/library/similar.py`
- `tests/ipc/test_library_schemas.py`
- `tests/ipc/test_learn_envelope_parity.py`
- `tests/ui_bus/test_citation_schema.py`
- `tests/ui_bus/fixtures/debrief_schema_v2_1_baseline.json`
- `tests/ui_bus/test_debrief_schema_additive_only.py`
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `tests/ui_bus/test_debrief_schemas.py`
- `tests/ui_bus/test_messages_schema.py`
- `tests/ui_bus/test_mood_change_envelope.py`
- `tests/ui_bus/test_overlay_schema.py`
- `tests/ui_bus/test_recordings_messages.py`
- `tauri/src-tauri/src/library_cmds.rs`

Keep out:

- Viber live-read UI changes from package 5.
- Future debrief citation-summary/event-timeline feature work; this package only
  removes the schema-only placeholders.

Proof already run:

- `uv run python scripts/check_ipc_schema.py`
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds`
- `uv run pytest -q tests/ipc/test_learn_envelope_parity.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/ui_bus/test_citation_schema.py tests/ui_bus/test_overlay_schema.py`
  passed: 52 tests after the focused IPC/UI-bus lint hygiene cleanup.
- `uv run ruff check ... tests/ipc tests/ui_bus ...`
  passed for the current IPC/UI-bus package slice, including the four newly
  dirtied test files above.

Remaining gate:

- Keep the IPC count at 72 unless a later package deliberately changes the schema.
  Confirm with `uv run python scripts/check_ipc_schema.py` and
  `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
  after staging Package 2 or Package 3.

Current IPC split audit, 2026-05-31 11:35 +03:

- Default decision remains: combine Package 2 and Package 3 into one IPC
  contract review unless there is an explicit reason to split.
- Split risk is structural, not cosmetic. Current numstat on shared IPC paths
  includes `tauri/ui/src/ipc/messages.schema.json` at `1 / 414`,
  `tauri/ui/src/ipc/messages.ts` at `0 / 90`,
  `src/vibemix/ui_bus/messages.py` at `5 / 190`,
  `src/vibemix/ui_bus/schemas/library.py` at `3 / 76`, and
  `tests/ui_bus/test_messages_schema.py` at `28 / 103`.
- Count/parity evidence is anchored in multiple places: `scripts/check_ipc_schema.py`
  prints schema/dataclass parity, `tests/ui_bus/test_messages_schema.py`,
  `tests/ui_bus/test_mood_change_envelope.py`, and
  `tests/ui_bus/test_recordings_messages.py` assert 72 top-level `oneOf`
  entries, and the IPC wiring checker treats schema-only reservations as dead
  contracts unless explicitly allowed.
- If the IPC work must split, the split commit that changes the count owns the
  schema, generated TypeScript, generated validator, Python wrappers, and all
  count/parity tests in the same cached diff. The other split may only carry
  runtime/UI consumers that validate against that already-consistent baseline.
- Split abort condition: any staged IPC shape where
  `uv run python scripts/check_ipc_schema.py`,
  `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`,
  or `npm --prefix tauri/ui run check:ipc` fails must be unstaged or widened
  into the combined IPC bundle before review.
- Validation after this audit:
  `uv run python scripts/check_ipc_schema.py` passed with 72 dataclasses and
  72 schema `oneOf` entries; the IPC wiring checker reported 72 shell wires and
  72 sidecar wires; `npm --prefix tauri/ui run check:ipc` regenerated
  `messages.ts` / `validator.generated.mjs` and completed `tsc --noEmit`.

## Package 4 - Auto And ANLZ Hot-Cue Pipeline

Suggested commit: `fix(library-cues): preserve hot cue slots through suggestions`

Include:

- `src/vibemix/library/ingest.py`
- `src/vibemix/library/smart_cues.py`
- `src/vibemix/intel/move_grade.py`
- `tests/library/test_ingest.py`
- `tests/library/test_setprep_tools.py`
- `tests/library/test_smart_cues.py`
- `tests/library/test_next_suggestion.py`
- `tests/intel/test_move_grade.py`

Review context, not staged in the current dirty tree:

- `src/vibemix/library/setprep.py`
- `src/vibemix/library/tools.py`
- `src/vibemix/agent/next_suggestion.py`

Keep out:

- Any unrelated Learn or pricing changes.
- Product copy that implies unreviewed auto cues are fully certain.

Proof already run:

- `uv run pytest -q tests/library/test_ingest.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py`
  passed: 84 tests after locking the full semantic hot-cue slot map and making
  unknown auto labels use G/H before stealing later semantic slots such as outro F.
- `uv run ruff check tests/library/test_ingest.py src/vibemix/library/ingest.py src/vibemix/library/smart_cues.py src/vibemix/intel/move_grade.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py`
  passed.
- `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts`
  passed: 167 tests.
- `npm --prefix tauri/ui run test:e2e:pill`

Remaining gate:

- Live DDJ/Viber proof. Preserve both `CuePoint.source` and `CuePoint.number`; cue-review
  uncertainty should surface as `CARE`.

## Package 5 - Library UI Live Read Context

Suggested commit: `feat(library-ui): ground Viber live reads with deck-pair context`

Include:

- `tauri/ui/src/library/api.ts`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/api.test.ts`
- `tauri/ui/src/library/chat.test.ts`

Keep out:

- Core Viber search/tool semantics unless deliberately packaging with package 4.

Proof already run:

- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed: 73 tests after hardening `mergeLiveContext()` so raw rejected live
  deck-audio frames are ignored instead of reaching Viber chat.
- `npm --prefix tauri/ui run build`
  passed: TypeScript check plus Vite build.

Remaining gate:

- Live read with real deck-pair state available through the running app.

## Package 6 - Compact Pill Polish

Suggested commit: `feat(pill): polish next suggestion care interactions`

Include:

- `tauri/ui/package.json`
- `tauri/ui/src/pill/index.ts`
- `tauri/ui/src/pill/index.test.ts`
- `tauri/ui/src/pill/next-suggestion.ts`
- `tauri/ui/src/pill/next-suggestion.test.ts`
- `tauri/ui/src/pill/pill.css`
- `tauri/ui/tests/pill/playwright.config.ts`
- `tauri/ui/tests/pill/browser-care-hover.pw.ts`
- `tauri/ui/tests/pill/browser-demo-reactions.pw.ts`
- `.planning/handoffs/2026-05-29-pill-polish-handoff.md`

Keep out:

- Cue ingest/scoring internals if package 4 is staged separately.

Proof already run:

- `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts`
  passed: 167 tests.
- `npm --prefix tauri/ui run test:e2e:pill`
  passed: 16 Playwright tests on the current dirty tree.
- `npm --prefix tauri/ui run build`

Remaining gate:

- Optional visual pass in the live UI once sidecar is running.

Current Packages 4-6 pipeline audit, 2026-05-31 11:38 +03:

- Default review decision: treat Packages 4, 5, and 6 as one product pipeline,
  even if they land as multiple commits. The user-facing behavior is only true
  if cue provenance and slot semantics survive from library ingest through
  Viber/tool export and the compact pill.
- Code navigation evidence: the pipeline roots are `CuePoint` in
  `src/vibemix/library/rekordbox.py`, `sections_for_entry()` in
  `src/vibemix/library/section_builder.py`, and Viber's grounded
  `smart_hot_cues` tool in `src/vibemix/library/toolset.py`.
- Dirty footprint evidence: Package 4 carries `src/vibemix/library/ingest.py`
  at `177 / 31`, `src/vibemix/intel/move_grade.py` at `13 / 1`, and focused
  library/intel tests. Package 5 is larger despite only four paths:
  `tauri/ui/src/library/api.ts` at `408 / 52`,
  `tauri/ui/src/library/chat.test.ts` at `435 / 77`, and
  `tauri/ui/src/library/index.ts` at `298 / 105`. Package 6 carries pill
  behavior and visual tests, including `tauri/ui/src/pill/pill.css` at
  `118 / 15`.
- Test evidence refreshed after this audit:
  `uv run pytest -q tests/library/test_ingest.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py`
  passed with 84 tests; the focused Ruff command for Package 4 passed;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 73 tests; `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts`
  passed with 167 tests; `npm --prefix tauri/ui run test:e2e:pill` passed
  with 16 Playwright tests; `npm --prefix tauri/ui run build` completed.
- What the current proof covers: materialized auto cues use stable semantic
  hot-cue slots, smart-cue/export paths preserve A-H slot numbers, transition
  suggestions expose `cue_slot`, cue-review risk flags such as `auto_cue_review`
  and `low_cue_confidence` remain CARE-grade inputs, Viber live-read UI rejects
  raw rejected deck-audio frames, and the pill renders CARE affordances without
  stale optimistic completion.
- What remains unproven: a live DDJ/Viber run where `CuePoint.source`,
  semantic `CuePoint.number`, Viber smart-cue/export receipts, and pill CARE
  state are observed in the same runtime evidence bundle. Do not describe this
  package as live-verified until that proof exists.
- Split abort condition: if Package 4 lands without Packages 5/6, its review
  note must explicitly say "backend cue semantics only" and must not claim pill
  or Viber live-read behavior. If Package 6 lands alone, its review note must
  say "UI rendering only" and must not imply ingest/export correctness.

## Package 7 - Learn Operator Action Bridge

Suggested commit: `feat(learn): bridge route-mismatch operator actions`

Include:

- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tauri/ui/src/learn/lesson/operator-action.ts`
- `tauri/ui/src/learn/ws-client.ts`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/test_curriculum_meta.spec.ts`
- `tauri/ui/tests/learn/test_operator_action.spec.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `tauri/ui/tests/learn/test_ws_client_filters_mascot.spec.ts`
- `tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts`
- `tests/learn/test_curriculum_projection.py`
- `.planning/handoffs/2026-05-30-learn-goal-complete-style-package.md`

Keep out:

- GSD.
- Learn beginner path suites.
- Course 3 routed-audio release claims.

Proof already run:

- `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_operator_action.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  passed: 55 tests on the current dirty tree after the screen-only highlight
  cleanup, without the previous false missing-highlight warnings for
  `headphone_cue:A` and `master_vol`.
- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
  passed: 33 tests after treating `headphone_cue`, `master_vol`, and
  `lesson_continue` as screen-only shell controls. The fallback test now asserts
  no false `[learn] highlight: control_id` warning for those controls.
- `uv run python scripts/export_learn_curriculum_meta.py --check`
  passed; this proves `curriculum-meta.ts` matches the Python projection.
- `uv run pytest -q tests/learn/test_curriculum_projection.py`
  passed: 4 tests.
- `npm --prefix tauri/ui run build`

Remaining gate:

- Keep using `scripts/export_learn_curriculum_meta.py --check` after any
  curriculum/source projection edit.

## Package 8 - Beatmatch Judge Creditability

Suggested commit: `feat(learn-audio): credit beatmatching from beatmatch judge`

Include:

- `src/vibemix/learn/beatmatch_judge.py`
- `src/vibemix/learn/skill_recognizer.py`
- `src/vibemix/learn/skill_tree.py`
- `tests/learn/test_judge_credits_beatmatch.py`
- `tests/learn/test_creditability_drift.py`
- `tests/learn/test_skill_wall_what_remains.py`

Review context, not staged by the current dirty tree:

- `src/vibemix/audio/grid.py`
- `src/vibemix/audio/miniplayer.py`
- `tests/audio/test_grid.py`
- `tests/audio/test_miniplayer.py`
- `tests/learn/test_beatmatch_judge.py`

Keep out:

- Earned Wall live-refresh runtime emission from Package 9.
- Course 3 full routed-audio handoff.
- GSD and beginner-path suites.

Proof already run:

- `uv run pytest -q tests/audio/test_grid.py tests/audio/test_miniplayer.py tests/learn/test_beatmatch_judge.py tests/learn/test_judge_credits_beatmatch.py`
  passed: 28 tests.
- `uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py`
  passed: 19 tests.
- `uv run ruff check src/vibemix/learn/beatmatch_judge.py src/vibemix/learn/skill_recognizer.py src/vibemix/learn/skill_tree.py tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py`
  passed as part of the current Learn creditability lint pass.

Remaining gate:

- Wire the live practice loop to emit cited `BEATMATCH_GRADED` only from the
  owned-deck judge path before treating this as Course 3 routed-audio proof.

## Hold Lane - Learn Beatmatch Producer Moat Plan

Suggested commit if/when selected: `docs(learn): plan beatmatch graded producer`

Hold:

- `.planning/LEARN-MOAT-PLAN.md`

Reason:

- This is architecture planning for the missing `BEATMATCH_GRADED` producer,
  not a shipped Learn runtime change. Keep it separate from Package 8's already
  implemented judge/creditability work and Package 9's Earned Wall refresh until
  someone deliberately starts the beatmatch practice producer package.
- It references Course 3 routed-audio proof and live practice-loop work, so do
  not use it as permission to run excluded beginner-path suites or GSD.

Remaining gate:

- When the producer work begins, turn the plan into a real package with red
  tests first: credit shim, practice controller, audio stream, grade debounce,
  `__main__` observer wiring, and by-ear/live proof.

## Hold Lane - Singularity Research Census Briefs

Suggested commit if/when selected: `docs(research): capture singularity subsystem census`

Hold:

- `.planning/singularity/2026-05-31/census-automix-tts.md`
- `.planning/singularity/2026-05-31/census-cue-detection.md`
- `.planning/singularity/2026-05-31/census-learn-skilltree.md`
- `.planning/singularity/2026-05-31/census-semantic-engine.md`
- `.planning/singularity/2026-05-31/census-vibe-judge.md`
- `.planning/singularity/2026-05-31/census-viber.md`
- `.planning/singularity/2026-05-31/cue-export/map-cue-pipeline.md`
- `.planning/singularity/2026-05-31/cue-export/map-export-pipeline.md`
- `.planning/singularity/2026-05-31/cue-export/map-live-fusion.md`
- `.planning/singularity/2026-05-31/cue-export/PLAN-CUE-EXPORT.md`
- `.planning/singularity/2026-05-31/cue-export/research-cue-boost.md`
- `.planning/singularity/2026-05-31/cue-export/research-easy-export.md`
- `.planning/singularity/2026-05-31/mixxx/PLAN-MIXXX.md`
- `.planning/singularity/2026-05-31/mixxx/research-fit-positioning.md`
- `.planning/singularity/2026-05-31/mixxx/research-library-cues.md`
- `.planning/singularity/2026-05-31/mixxx/research-live-control.md`
- `.planning/singularity/2026-05-31/ROADMAP-SINGULARITY.md`
- `.planning/singularity/2026-05-31/research-cue-boost.md`
- `.planning/singularity/2026-05-31/research-data-flywheel.md`
- `.planning/singularity/2026-05-31/research-semantic-hotcue.md`
- `.planning/singularity/2026-05-31/research-viber-gemini-agentic.md`

Reason:

- These are broad read-only research/census briefs that cross automix/TTS,
  cue detection/export, Learn, Vibe Judge, Viber, semantic hot-cues, and
  data-flywheel strategy, plus new Mixxx positioning/library-cue/live-control
  research. Keep them out of Package 0 so the first planning commit remains an
  inventory/checker package rather than a claim-heavy research bundle.
- Several briefs contain forward-looking status language and external references.
  Use them as discovery inputs, not as shipping proof, until each cited
  `path:line`, live-status claim, and product recommendation is reviewed in the
  package that would consume it.

Remaining gate:

- If selected as a docs-only research package, validate citations and stale line
  anchors. If selected as implementation input, split the relevant brief into the
  target package's evidence/acceptance criteria first.

## Hold Lane - Cue Export Folder Bridge

Suggested commit if/when selected: `feat(library): add folder cue export bridge`

Hold:

- `src/vibemix/library/cue_folder.py`
- `tests/library/test_cue_folder.py`

Reason:

- These files appeared from the cue-export research lane as an implementation
  slice, not as part of the already mapped auto-cue/pill/Viber package.
- Keep this bridge separate from Package 4 until the CLI/export integration,
  Rekordbox XML behavior, and staging boundary are reviewed together.
- The nearby Singularity cue-export briefs can explain intent, but they are
  research inputs. They do not make these runtime/library files shippable on
  their own.

Remaining gate:

- Identify the intended CLI or Viber entry point, run the focused library tests,
  and prove the output contract before promoting this from hold to a package.

## Hold Lane - Real CLAP Retrieval Eval Gate

Suggested commit if/when selected: `test(library): add real CLAP retrieval eval gate`

Hold:

- `scripts/eval/clap_retrieval.py`
- `tests/library/fixtures/clap_real_corpus/README.md`
- `tests/library/fixtures/clap_real_corpus/manifest.json`
- `tests/library/fixtures/clap_real_corpus/vectors.npz`
- `tests/library/test_clap_real_retrieval.py`
- `tests/library/test_clap_retrieval_eval.py`

Reason:

- This is the start of the model-regression gate called out by the live-app
  reality ledger: a pure evaluator plus synthetic metric tests for recall/MRR
  and anisotropy behavior.
- It now includes a committed real-CLAP embedding fixture and offline regression
  test, so it can catch ranking/centering regressions against real 512-d music
  embeddings without needing ONNX in CI.
- The fixture README documents the honest caveat: the six-track corpus proves
  anisotropy collapse on real CLAP embeddings, but the centroid is too small and
  noisy to prove centered retrieval improvement yet.
- It is still not the final live-model proof: the regression test loads
  committed embeddings and does not instantiate `onnxruntime.InferenceSession`
  or exercise fresh text/audio embedding generation in CI.
- Keep it out of Package 4 pill/cue/product work and out of dependency
  modernization rings until the eval package can be reviewed as a model-quality
  gate on its own.

Current proof:

- `uv run python scripts/eval/clap_retrieval.py` reports six tracks, centered
  `recall@1=0.666667`, centered `recall@3=0.666667`, centered `MRR=0.741667`,
  raw `recall@3=0.833333`, and anisotropy gap `0.996892`.
- `uv run pytest -q tests/library/test_clap_retrieval_eval.py tests/library/test_clap_real_retrieval.py`
  passed: 8 tests. The real-fixture test now gates centered recall@1, recall@5,
  MRR, and anisotropy collapse; it no longer claims centered recall@3 improves
  on a six-track corpus.

Remaining gate:

- Decide whether this offline fixture is enough for Package 4 ranking claims or
  whether a separate slow/local ONNX build gate is required before dependency
  upgrades that can change the embedder.

## Package 9 - Earned Wall Live Refresh

Suggested commit: `fix(learn-runtime): refresh earned wall after live cited credits`

Include:

- `src/vibemix/runtime/coach.py`
- `tests/runtime/test_coach_skill_credit.py`
- `tests/runtime/test_coach_progress_emit.py`
- `tests/learn/test_mastered_vocal_fires_once.py`

Review context, not staged by the current dirty tree:

- `src/vibemix/learn/mastered_vocal.py`
- `src/vibemix/learn/vocals/mastered_vocals.json`

Keep out:

- Beatmatch Judge creditability from Package 8 if a smaller runtime-only review
  is desired.
- Course 3 full routed-audio handoff.
- GSD and beginner-path suites.

Proof already run:

- `uv run pytest -q tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py`
  passed: 41 tests.
- `uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py`
  passed: 36 tests.
- `uv run ruff check src/vibemix/learn/beatmatch_judge.py src/vibemix/learn/skill_recognizer.py src/vibemix/learn/skill_tree.py src/vibemix/runtime/coach.py tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/learn/test_mastered_vocal_fires_once.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py`
  passed.

Remaining gate:

- Re-run the coach credit/progress tests after any edit to `runtime/coach.py`.
- Repeat the grounding-review pass after any future co-host speech edit.
- Live UI proof is still pending; the current MCP sidecar check reports
  `ws_reachable: false` because the app is not running.

Current Learn/Earned Wall audit, 2026-05-31 11:40 +03:

- Default review decision: keep Package 7 and Package 9 adjacent in the stack
  but do not merge them with Package 8 or the Learn beatmatch producer hold.
  Package 7 proves operator-action and curriculum projection UI plumbing;
  Package 9 proves cited-credit persistence plus Earned Wall refresh emission.
- Explicit keep-outs remain active: no GSD, no named Learn beginner-path suites,
  no Course 3 routed-audio release claims, and no `BEATMATCH_GRADED` producer
  claim until the hold lane becomes a real package with red tests and live proof.
- Code navigation evidence: Package 7 roots in the Python curriculum projection
  and `tauri/ui/src/learn/lesson/curriculum-meta.ts`, then flows through
  `operator-action.ts`, `ws-client.ts`, and `learn-window.ts`. Package 9 roots
  in `src/vibemix/runtime/coach.py`, especially live cited-credit handling,
  `ipc.learn.progress_state` emission, and the once-only mastered vocal path.
- Dirty footprint evidence: Package 7 includes `tauri/ui/src/learn/learn-window.ts`
  at `76 / 3`, `operator-action.ts` at `34 / 4`, `ws-client.ts` at `42 / 4`,
  and focused Learn UI tests. Package 9 includes `src/vibemix/runtime/coach.py`
  at `45 / 4`, `tests/runtime/test_coach_skill_credit.py` at `128 / 1`,
  `tests/runtime/test_coach_progress_emit.py`, and
  `tests/learn/test_mastered_vocal_fires_once.py`.
- Test evidence refreshed after this audit:
  `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_operator_action.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  passed with 55 tests; `uv run python scripts/export_learn_curriculum_meta.py --check`
  passed; `uv run pytest -q tests/learn/test_curriculum_projection.py` passed
  with 4 tests; `uv run pytest -q tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py`
  passed with 41 tests; focused Ruff for `runtime/coach.py` and Package 9 tests
  passed; `npm --prefix tauri/ui run build` completed.
- What the current proof covers: structured operator actions reach the Learn UI,
  screen-only controller highlights do not produce false missing-highlight
  warnings, frontend curriculum metadata matches the Python projection, cited
  coach events can credit skills and emit `ipc.learn.progress_state`, uncited
  events do not credit or speak, and mastered vocals fire once without banned
  speculative/slop phrasing.
- What remains unproven: a live Learn UI pass where the Earned Wall visibly
  refreshes from a real cited runtime credit, plus the future
  `BEATMATCH_GRADED` producer path. Do not use Package 9 evidence to claim
  Course 3 routed-audio mastery or beatmatch judge live-loop completion.
- Split abort condition: if Package 7 lands alone, its review note must say
  "operator/curriculum UI only" and must not claim Earned Wall credit refresh.
  If Package 9 lands alone, its review note must say "backend refresh emission
  only" until a live UI artifact shows the shell repaint.

## Package 10 - Live Stack Cost And Pricing Model

Suggested commit: `feat(library-cost): add live stack budget model`

Include:

- `src/vibemix/library/cost.py`
- `src/vibemix/library/pricing.py`
- `src/vibemix/library/budget.py`
- `src/vibemix/__main__.py`
- `src/vibemix/llm/_router_config.py`
- `tests/library/test_cost.py`
- `tests/library/test_pricing.py`
- `tests/e2e/test_phase_41_latency_stack_integration.py`
- `tests/llm/test_model_router.py`
- `docs/pricing/live-stack-economics.en.md`
- `docs/pricing/live-stack-economics.it.md`

Keep out:

- Marketing copy that treats Cartesia `sonic-3` pricing as verified. Keep it marked
  `LEGACY_DERIVED` until billing confirms the effective rate.
- The live TTS shutdown hunk in `src/vibemix/__main__.py` and
  `tests/test_main_smoke.py`; stage those with Package 14 if this package is
  split from runtime shutdown hygiene.

Proof already run:

- `uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/llm/test_model_router.py`
- `uv run pytest -q tests/e2e/test_phase_41_latency_stack_integration.py tests/repo/test_live_spike_scaffold.py tests/llm/test_model_router.py tests/library/test_pricing.py tests/library/test_cost.py`
- `bash scripts/release/check_no_hardcoded_model.sh`
- `uv run ruff check src/vibemix/library/pricing.py tests/library/test_pricing.py`
- `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3`
- `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3 --json > /tmp/vibemix-live-budget.json && uv run python -m json.tool /tmp/vibemix-live-budget.json`

Remaining gate:

- Billing confirmation for Cartesia before external/public financial claims.
- Keep Gemini 3.1 Flash Live isolated to `spikes/` until its LAT-09 verdict is
  written; do not re-add it as a runtime router/pricing candidate.

## Package 11 - Launch Collateral

Suggested commit: `docs(launch): package launch collateral and screenshots`

Include:

- `docs/launch/.build_talking.py`
- `docs/launch/.partner-capabilities-tr-short.html`
- `docs/launch/.vibemix-pitch-en.html`
- `docs/launch/.vibemix-pitch-tr.html`
- `docs/launch/vibemix-yetenekler-tr.pdf`
- `docs/launch/vibemix-vo-charon.mp3`
- `docs/launch/screenshots/README.md`
- `docs/launch/screenshots/shell-live-moneyshot.png`
- `docs/launch/screenshots/shell-deck-final.png`
- `docs/launch/screenshots/viber-chat-elevated.png`
- `docs/launch/screenshots/crate-elevated.png`
- `docs/launch/screenshots/debrief-elevated.png`
- `docs/launch/screenshots/learn-elevated.png`
- `docs/launch/screenshots/settings-elevated.png`
- `docs/launch/screenshots/wizard-current.png`
- Optional close-up slots if needed by the deck:
  `docs/launch/screenshots/viber-chat-closeup.png`,
  `docs/launch/screenshots/settings-closeup.png`,
  `docs/launch/screenshots/rail-closeup.png`.

Keep out:

- Root scratch image `deck-after-delete-pass-silent.png`.
- Generated preview HTML: `docs/launch/.partner-capabilities.html`,
  `docs/launch/.partner-capabilities-short.html`, and
  `docs/launch/.vibemix-konusan.html`.
- Screenshot alternates not selected for the first launch package:
  `docs/launch/screenshots/shell-deck-lit.png`,
  `docs/launch/screenshots/shell-idle.png`,
  `docs/launch/screenshots/shell-lit-v1.png`,
  `docs/launch/screenshots/session-hero-v2.png`,
  `docs/launch/screenshots/session-hero-v3.png`,
  `docs/launch/screenshots/session-hero-v4.png`,
  `docs/launch/screenshots/session-idle-centered.png`,
  `docs/launch/screenshots/session-lit-v1.png`,
  `docs/launch/screenshots/session-mock.png`,
  `docs/launch/screenshots/crate.png`,
  `docs/launch/screenshots/crate-lit.png`,
  `docs/launch/screenshots/learn.png`,
  `docs/launch/screenshots/mock-contract.png`,
  `docs/launch/screenshots/mock-viewport.png`.

Proof already run:

- `uv run ruff check docs/launch/.build_talking.py`
- `uv run python docs/launch/.build_talking.py --out /tmp/vibemix-konusan.html`
- `uv run python docs/launch/.build_talking.py --out /tmp/vibemix-konusan.html --check`
- `git check-ignore -v docs/launch/.vibemix-konusan.html docs/launch/.partner-capabilities.html docs/launch/.partner-capabilities-short.html`
- `git diff --check`

Remaining gate:

- Before staging, decide whether optional close-up slots are needed. The
  canonical full-viewport subset, alternates, and generated-HTML policy are
  documented in `docs/launch/screenshots/README.md`.

Current public-claims audit, 2026-05-31 11:42 +03:

- Default review decision: keep Package 10 and Package 11 adjacent, but do not
  merge them by default. Package 10 is internal economics and reproducible CLI
  output; Package 11 is selected launch collateral. Both are public-facing, so
  both require stricter wording and asset-selection review than ordinary code.
- Package 10 split risk: `src/vibemix/__main__.py` is shared with Package 14
  and the deck-audio hold lane. The Package 10 cached diff may include only the
  `library budget --stack live` parser/handler/reporting hunks from that file.
  TTS shutdown and controller-state callback hunks must stay out.
- Package 10 claim boundary: Cartesia `sonic-3` stays `LEGACY_DERIVED` /
  `UNVERIFIED` until account billing or current public-plan conversion proves
  the effective rate. The 9.74 EUR per-DJ-month / 97,374 EUR fleet headline is
  reproducible but remains internal sensitivity copy, not external pricing copy.
- Package 11 selection boundary: stage the canonical launch screenshots and
  selected close-ups only after a content decision. Keep screenshot alternates
  in the Launch Screenshot Alternates hold lane and keep generated preview HTML
  ignored.
- Code navigation evidence: Package 10 roots in `PriceRow` from
  `src/vibemix/library/pricing.py`, `BudgetTelemetry` and budget helpers in
  `src/vibemix/library/budget.py`, and the live budget CLI in
  `src/vibemix/__main__.py`; launch collateral roots in
  `docs/launch/.build_talking.py` plus `docs/launch/screenshots/README.md`.
- Test evidence refreshed after this audit:
  `uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/llm/test_model_router.py`
  passed with 37 tests; the broader live-stack/model suite passed with 62 tests;
  `bash scripts/release/check_no_hardcoded_model.sh` passed; focused Ruff for
  pricing and the launch builder passed; `uv run python docs/launch/.build_talking.py --out /tmp/vibemix-konusan.html --check`
  passed; generated preview HTML is ignored by `.gitignore`.
- Repro evidence: `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3`
  printed `TOTAL 0.4857 EUR/session, 9.74 EUR/DJ-month, 97,374 fleet EUR/mo`,
  dominant leg `TTS`, and `Cartesia Sonic 97,374 ! UNVERIFIED`. The JSON form
  wrote `/tmp/vibemix-live-budget.json` and pretty-printed successfully.
- Split abort condition: if Package 10 lands alone, its review note must say
  "internal economics only" and must not claim launch copy is approved. If
  Package 11 lands alone, its review note must say "collateral selection only"
  and must not include cost/pricing claims unless Package 10 evidence is also
  staged and reviewed.

## Hold Lane - Launch Screenshot Alternates

Suggested commit if/when selected: `docs(launch): refresh launch screenshot alternates`

Hold:

- `docs/launch/screenshots/shell-deck-lit.png`
- `docs/launch/screenshots/shell-idle.png`
- `docs/launch/screenshots/shell-lit-v1.png`
- `docs/launch/screenshots/session-hero-v2.png`
- `docs/launch/screenshots/session-hero-v3.png`
- `docs/launch/screenshots/session-hero-v4.png`
- `docs/launch/screenshots/session-idle-centered.png`
- `docs/launch/screenshots/session-lit-v1.png`
- `docs/launch/screenshots/session-mock.png`
- `docs/launch/screenshots/crate.png`
- `docs/launch/screenshots/crate-lit.png`
- `docs/launch/screenshots/learn.png`
- `docs/launch/screenshots/mock-contract.png`
- `docs/launch/screenshots/mock-viewport.png`

Reason:

- These screenshots are intentionally not part of the first launch collateral
  package, but they are real untracked dirty files and should remain owned by a
  hold lane rather than floating as keep-out-only mentions.

## Hold Lane - Premium Enterprise Visual Audit

Suggested commit if/when selected: `docs(design): capture premium session audit`

Hold:

- `docs/design/2026-05-31-premium-enterprise-upgrade-plan.md`
- `mocks/vibemix-premium-enterprise-upgrade.html`
- `docs/design/screenshots/2026-05-31-premium-audit/bravoh-grade-pink.png`
- `docs/design/screenshots/2026-05-31-premium-audit/current-pill-idle.png`
- `docs/design/screenshots/2026-05-31-premium-audit/current-shell-compact.png`
- `docs/design/screenshots/2026-05-31-premium-audit/current-shell-desktop.png`
- `docs/design/screenshots/2026-05-31-premium-audit/locked-direction-final.png`
- `docs/design/screenshots/2026-05-31-premium-audit/mock-operator-console-desktop.png`
- `docs/design/screenshots/2026-05-31-premium-audit/mock-pill-handoff-compact.png`
- `docs/design/screenshots/2026-05-31-premium-audit/mock-pill-handoff-desktop.png`
- `docs/design/screenshots/2026-05-31-premium-audit/mock-receipt-deck-compact.png`
- `docs/design/screenshots/2026-05-31-premium-audit/mock-receipt-deck-desktop.png`
- `docs/design/screenshots/2026-05-31-premium-audit/premium-session-v3.png`

Reason:

- These appeared during the live-readiness pass as design-audit collateral, not
  production UI code. Keep them owned and reviewable, but do not mix them into
  runtime or launch-collateral commits unless the design direction is accepted.

## Hold Lane - Sexiest Live Visual Proof

Suggested commit if/when selected: `docs(design): capture sexiest live proof`

Hold:

- `docs/design/screenshots/2026-05-31-sexiest-live/00-current-deck.png`
- `docs/design/screenshots/2026-05-31-sexiest-live/00-current-proof.json`
- `docs/design/screenshots/2026-05-31-sexiest-live/00-current-settings.png`
- `docs/design/screenshots/2026-05-31-sexiest-live/01-sexified-deck.png`
- `docs/design/screenshots/2026-05-31-sexiest-live/01-sexified-proof.json`
- `docs/design/screenshots/2026-05-31-sexiest-live/01-sexified-settings.png`
- `docs/design/screenshots/2026-05-31-sexiest-live/02-sexified-deck.png`
- `docs/design/screenshots/2026-05-31-sexiest-live/02-sexified-proof.json`
- `docs/design/screenshots/2026-05-31-sexiest-live/02-sexified-settings.png`
- `docs/design/screenshots/2026-05-31-sexiest-live/03-final-deck.png`
- `docs/design/screenshots/2026-05-31-sexiest-live/03-final-proof.json`
- `docs/design/screenshots/2026-05-31-sexiest-live/03-final-settings.png`

Reason:

- These are visual proof artifacts from a later frontend/design pass. Keep them
  separate from production UI code and from the selected launch collateral until
  the design direction is accepted.

Remaining gate:

- If selected, pair the screenshots with the design note or production UI diff
  they prove, then run the relevant UI build/test/screenshot proof before any
  shipped visual claim.

## Hold Lane - Frontend Shell Settings Proof

Suggested commit if/when selected: `fix(ui-shell): keep settings drawer navigation stable`

Hold:

- `tauri/ui/src/settings/components/group.ts`
- `tauri/ui/src/session/components/picker.ts`
- `tauri/ui/src/session/components/rocker.ts`
- `tauri/ui/src/shell/app.ts`
- `tauri/ui/src/shell/shell.css`
- `docs/design/screenshots/2026-05-31-frontend-proof/actionability-proof.json`
- `docs/design/screenshots/2026-05-31-frontend-proof/after-fix-proof.json`
- `docs/design/screenshots/2026-05-31-frontend-proof/after-fix-settings-open.png`
- `docs/design/screenshots/2026-05-31-frontend-proof/shell-initial.png`
- `docs/design/screenshots/2026-05-31-frontend-proof/shell-settings-open.png`
- `docs/design/screenshots/2026-05-31-frontend-proof/shell-settings-proof.json`

Reason:

- This is production shell/settings behavior and shell visual polish plus proof
  collateral. It should not be folded into the design-only Premium Enterprise
  Visual Audit and should not ride with IPC/settings schema work unless the
  package deliberately proves both layers.
- The code diff keeps settings navigation synchronized with drawer open/close
  state, stabilizes settings-group layout, changes session picker/rocker
  styling, and changes shell chrome/sidebar CSS. That needs UI tests/build and a
  screenshot proof before it is treated as shipped polish.

Remaining gate:

- Run the focused settings/shell UI tests, `npm --prefix tauri/ui run build`,
  and keep the screenshot/JSON proof with the same package if this lane is
  promoted.

## Package 12 - Runtime Memory CLAP Readiness

Suggested commit: `fix(memory): reconcile stale sqlite-vec embedding dimensions`

Include:

- `src/vibemix/memory/index_sqlite_vec_memory.py`
- `src/vibemix/runtime/session_loop.py`
- `tests/memory/test_ingest_wiring.py`
- `tests/memory/test_store_parity.py`

Keep out:

- Library-folder ingest dimension reconciliation. That path already owns its
  `vector_dim()` / `row_count()` / `recreate_table()` policy separately.
- Mix/audio hold-lane files.

Proof already run:

- `uv sync --group dev --extra ai-local`
  installed the declared local AI runtime dependencies into the checkout without
  tracked lockfile changes: `onnxruntime`, `tokenizers`, and their support wheels.
- `uv run python -m vibemix library models --json`
  reported `required_ready: true` and `all_ready: true` for CLAP ONNX and CUE-DETR.
- `uv run pytest -q tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py`
  passed: 22 tests. New coverage recreates an empty stale 768-dim `vec_memory`
  table before the first current-dim insert, and falls back instead of wiping a
  populated stale table.
- `uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py`
  passed: 34 tests. This adds the guard that sidecar-only `--session` probes do
  not launch CLAP memory indexing on boot or close.
- `uv run ruff check src/vibemix/runtime/session_loop.py src/vibemix/memory/index_sqlite_vec_memory.py tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py`
  passed.
- `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session`
  logged the empty 768-dim `vec_memory` table being recreated at
  `EMBEDDING_DIM=512`, opened `SqliteVecMemoryStore`, and reached
  `127.0.0.1:8765`; MCP `sidecar_status` reported `ws_reachable: true` and
  `ws_observe` captured seven `ipc.session.snapshot` frames. The previous
  sqlite-vec insert error did not appear in the observed boot/close logs.
- Follow-up `--session` probe after disabling diagnostic memory ingest reached
  `127.0.0.1:8765`, MCP captured 58 `ipc.session.snapshot` frames in two seconds,
  and Ctrl-C exited cleanly with `memory ingest (boot/close) skipped: disabled`
  instead of starting CLAP indexing.

Remaining gate:

- Full Tauri/DDJ live proof still belongs to the final live gate.

## Package 13 - Tauri Sidecar Bundle Freshness Guard

Suggested commit: `fix(packaging): reject stale bundled IPC schemas`

Include:

- `scripts/dist/check_sidecar_bundle_ready.py`
- `tests/install/test_sidecar_bundle_ready.py`

Keep out:

- Ignored generated bundle output under `tauri/src-tauri/binaries/**`,
  `tauri/src-tauri/target/**`, `build/**`, and `dist/**`.

Proof already run:

- Stale source scan found the removed IPC ghosts only in ignored generated
  sidecar/Tauri outputs, not in source after excluding generated IPC files:
  `ipc.debrief.citation-summary`, `ipc.debrief.event-timeline`,
  `ipc.library.search`, `ipc.library.search_result`, `ipc.library.confidence`,
  `ipc.library.similar_request`, and `ipc.library.similar_result`.
- `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only`
  failed before the fix/rebuild because the bundled sidecar IPC schema was stale.
- `uv run pytest -q tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py`
  passed: 20 tests. New coverage fails stale or missing embedded IPC schemas
  when the source schema exists.
- `uv run ruff check scripts/dist/check_sidecar_bundle_ready.py tests/install/test_sidecar_bundle_ready.py`
  passed.
- `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec`
  rebuilt the local Apple Silicon sidecar resource and completed the bundle
  AIza-pattern scan: 402 files scanned, no leak found.
- Deleted ignored stale Tauri outputs under `tauri/src-tauri/target/release/bundle`,
  `tauri/src-tauri/target/release/binaries`,
  `tauri/src-tauri/target/debug/binaries`, and
  `tauri/src-tauri/target/release/messages.schema.json`, so opening an old
  target app cannot mask the current source wiring.
- `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only`
  now passes against the rebuilt sidecar.
- Re-running the stale IPC ghost scan across source, Tauri resources, tests,
  scripts, and remaining `target/` files produced no matches.

Remaining gate:

- A full `cargo tauri build` / signed artifact pass still belongs to release
  packaging. This package prevents a stale sidecar schema from being silently
  accepted before that build.

## Hold Lane - macOS Signing And Notarization Flow

Suggested commit if/when selected: `fix(packaging): support local notarization fallback`

Hold:

- `docs/signing-macos.md`
- `scripts/dist/sign_macos.sh`
- `tauri/src-tauri/tauri.conf.json5`

Reason:

- This is release packaging/signing behavior, not the Package 13 sidecar bundle
  freshness guard and not the refactor/wiring lane. The current hunk adds a
  local Apple-ID app-specific-password notarization fallback, an
  `APPLE_SIGNING_IDENTITY` alias, and a Tauri build-command path correction.
- Keep it separate until both dry-run and real signing/notarization evidence are
  available. Code-signing changes should prove identity selection, secret
  handling, notarization submission/log retrieval, staple verification, and the
  Tauri build hook path.

Remaining gate:

- Run a dry-run against an existing `.app` bundle, for example
  `bash scripts/dist/sign_macos.sh --dry-run <path-to-vibemix.app>`.
- Run `cargo check --manifest-path tauri/src-tauri/Cargo.toml` if the Tauri
  config hunk is staged.
- Before shipping, perform a full sign/notarize/staple/verify pass with either
  the ASC API-key path or the Apple-ID fallback, and confirm no secrets are
  echoed or committed.

## Hold Lane - Tauri Sidecar Log Drain

Suggested commit if/when selected: `fix(tauri): drain sidecar logs without line buffering`

Hold:

- `tauri/src-tauri/src/sidecar.rs`

Reason:

- This is production Tauri sidecar runtime code, not the Package 13 bundle
  freshness guard. The current hunk changes stdout/stderr draining from
  line-based reads to raw byte reads so partial sidecar output can reach the
  rotating log.
- Keep it separate until Rust formatting/checks and a focused sidecar-log proof
  are run. Do not stage it with docs-only routing or Python sidecar-bundle
  checks.

Remaining gate:

- Run `cargo fmt` / `cargo check --manifest-path tauri/src-tauri/Cargo.toml` and
  any focused sidecar tests before promoting this lane.

## Package 14 - Live TTS Shutdown Hygiene

Suggested commit: `fix(runtime): close nested live tts providers`

Packaging decision: this shares `src/vibemix/__main__.py` with Package 10. If
staging as separate commits, stage only the `_close_tts_chain()` and shutdown
cleanup hunks here, and leave `vibemix library budget --stack live` hunks with
Package 10.

Include:

- `src/vibemix/__main__.py`
- `tests/test_main_smoke.py`

Keep out:

- Live-stack budget CLI/parser/reporting changes from the same `__main__.py`
  file; those remain Package 10.

Proof already run:

- `uv run pytest -q tests/test_main_smoke.py -k close_tts_chain`
- `uv run pytest -q tests/test_main_smoke.py::test_close_tts_chain_closes_nested_providers_once tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams`
  passed: 2 tests.
- `uv run ruff check src/vibemix/__main__.py tests/test_main_smoke.py`
  passed.
- Full live rerun after the fix: `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`
  with `DDJ-FLX4` connected, `ws_probe.py --action trigger`, and Cartesia speech.
  Shutdown reached `-> bye` without the previous `Unclosed client session` warning.

Remaining gate:

- If Package 10 and Package 14 are staged separately, inspect
  `git diff --cached -- src/vibemix/__main__.py` before committing so the
  unrelated budget and shutdown hunks do not travel together accidentally.

## Hold Lane - Local MOSS TTS ONNX Runtime Spike

Suggested commit if/when it ships: `feat(tts): add wrapped local moss onnx runtime`

Hold:

- `pyproject.toml`
- `scripts/local_tts_speak.py`
- `src/vibemix/agent/local_tts.py`
- `src/vibemix/agent/moss_tts/__init__.py`
- `src/vibemix/agent/moss_tts/ort_cpu_runtime.py`
- `src/vibemix/agent/tts_chain.py`
- `tests/agent/test_local_tts.py`
- `uv.lock`

Reason:

- This local-TTS slice appeared after the package ledger was already green. It
  includes a 328-line `local_tts.py` wrapper, 871 untracked lines of vendored
  OpenMOSS / MOSS-TTS-Nano ONNX runtime code, and a tracked `tts_chain.py` diff
  (`21 / 4`) that prepends the local voice when `VIBEMIX_LOCAL_TTS` is opted in
  and the model is cached. It also now includes a 199-line focused
  `tests/agent/test_local_tts.py`. It is not part of the existing live TTS
  shutdown fix.
- The file header says it is kept byte-for-byte for upstream re-sync and should
  be wrapped rather than refactored. Treat it as third-party runtime code, not a
  normal maintainability extraction target.
- A precise search now shows integration in `src/vibemix/agent/local_tts.py`,
  `src/vibemix/agent/tts_chain.py`, and `tests/agent/test_local_tts.py`, but
  still no model-download path, CLI, or docs/NOTICE handoff for the live tree.
- `pyproject.toml` and `uv.lock` now add a `tts-local` extra and add
  `sentencepiece>=0.2` to `ai-local`, resolving the first tokenizer-dependency
  gap on paper. Treat this as part of the local-TTS hold, not as a general
  dependency modernization ring, until install/runtime proof exists.
- The runtime imports `onnxruntime`, which is already available through the
  CLAP/CUE optional inference extras, but that does not prove it is safe to
  import in the default live TTS path.

Ship path:

- Add license/NOTICE attribution and model-source documentation before staging.
- Harden the `vibemix.agent.local_tts` wrapper rather than editing the vendored
  runtime directly.
- Keep model selection config-driven; do not hardcode a new live model path in
  `__main__.py` or the TTS chain.
- Run and extend the focused local-TTS tests. Current untracked tests cover PCM
  downmixing, opt-in gating, native sample-rate probing, FallbackAdapter ordering,
  fake-engine streaming, and a guarded real-model slow path; still add/import
  proof for missing dependency/model behavior and ORT provider/sample-mode
  details if this ships.
- Prove the `tts-local` / `ai-local` install path with `uv sync` or equivalent
  before claiming the dependency decision is done.
- Add a local-model readiness/download story if this becomes a user-facing
  runtime option.
- Prove latency and bundle impact separately from Package 14 shutdown hygiene
  and Package 10 cost/pricing.
- Run grounding-review invariants before using local MOSS output in live co-host
  speech.

Current evidence, 2026-05-31 11:56 +03:

- `uv run pytest -q tests/agent/test_local_tts.py -m 'not slow'` is not green:
  10 tests passed, 1 slow test was deselected, and
  `test_synthesize_streams_all_pushed_pcm` failed because the emitted stream
  reported 9840 samples where the fake engine pushed 9600. Keep this lane on
  hold until the streaming sample accounting is understood and fixed by its
  owner.

Drift refresh, 2026-05-31 12:11 +03:

- `git status --short -- pyproject.toml src/vibemix/agent/local_tts.py src/vibemix/agent/moss_tts src/vibemix/agent/tts_chain.py tests/agent/test_local_tts.py uv.lock`
  shows only `uv.lock` still dirty from this lane. The prior wrapper, vendored
  runtime, TTS-chain, manifest, and focused test files are no longer dirty in
  the live tree.
- `git diff -- uv.lock` still adds `sentencepiece` and a `tts-local` extra to
  the lockfile. Since the matching `pyproject.toml` manifest diff is not dirty,
  keep this as a residual hold-lane lockfile hunk. Do not stage it with Package
  14 shutdown hygiene, Package 10 pricing, or dependency modernization.

Drift refresh, 2026-05-31 13:25 +03:

- `scripts/local_tts_speak.py` appeared as a local proof/smoke helper for this
  same on-device TTS lane. Keep it with the Local MOSS hold until the runtime,
  dependency, model-source, and license story is accepted.

Keep out:

- Package 14's `_close_tts_chain()` shutdown cleanup.
- Package 10's live-stack cost/pricing public claims until local-TTS pricing,
  runtime cost, and user-device requirements are measured.
- Dependency modernization rings unless the package intentionally changes
  `onnxruntime` or model-asset dependencies.

## Package 15 - Desktop Auto-Master 16ch Upgrade

Suggested commit: `fix(audio): honor explicit blackhole variants in auto-master mode`

Include:

- `src/vibemix/platform/_audio_macos.py`
- `tests/test_audio_macos.py`

Context:

- The first Tauri dev-source live proof reached the renderer and co-host, but
  session `20260531-102701` recorded `capture_device_too_few_channels` because
  Tauri sets `VIBEMIX_AUTO_MASTER_INPUT=1` and the 16ch upgrade probe was
  rerouted back through the silent auto-master fallback. Direct Python did not
  show this because it was not launched with the Tauri auto-master env default.

Proof already run:

- `uv run pytest -q tests/test_audio_macos.py::test_find_device_auto_master_input_honors_explicit_blackhole_variant tests/test_audio_macos.py::test_find_device_auto_master_input_chooses_live_48k_variant tests/test_audio_macos.py::test_find_device_auto_master_input_falls_back_to_48k_variant_when_silent tests/test_main_smoke.py::test_deck_audio_auto_upgrades_default_blackhole_input tests/test_main_smoke.py::test_deck_audio_global_default_upgrades_blackhole_without_env`
  passed: 5 tests.
- `uv run ruff check src/vibemix/platform/_audio_macos.py tests/test_audio_macos.py src/vibemix/__main__.py tests/test_main_smoke.py`
  passed.
- Post-fix Tauri dev proof: `VIBEMIX_DEV_SIDECAR=1 cargo tauri dev --no-watch`
  brought up the renderer/Rust bridge/pill path, `ws_probe.py --ipc
  ipc.status.recheck --payload-json '{"component":"midi"}'` returned
  `livekit=ok gemini=ok midi=1`, and session `20260531-103122` recorded
  `requested_device=BlackHole_16ch`, `input_channels=16`, `opened_channels=4`,
  `mode=deck_pair_capture_configured`, plus real jog-wheel MIDI evidence.

Remaining gate:

- Still needs audible deck audio and a cited co-host moment; the fixed proof is
  route/capture/controller/UI plumbing, not musical grounding.

## Hold Lane - Deck Audio Controller-Weighted Master Context

Suggested commit if/when it ships: `feat(audio): weight deck-pair master by controller posture`

Hold:

- `src/vibemix/audio/deck_capture.py`
- `src/vibemix/audio/deck_signal.py`
- `src/vibemix/midi/state.py`
- `src/vibemix/__main__.py`
- `src/vibemix/state/deck_context.py`
- `tests/audio/test_deck_capture.py`
- `tests/audio/test_deck_signal.py`
- `tests/midi/test_state.py`
- `tests/state/test_deck_context.py`

Reason:

- This changes how the captured master signal is synthesized when per-deck
  BlackHole channels and controller posture are both available. Keep it separate
  from the 16ch auto-master device-selection fix and from library/Viber UI
  context until the audible route is proven.
- `audio/deck_signal.py` belongs here for the `effective_enabled()` routing
  honesty shim: unverified auto-Rekordbox deck-pair hints should stay
  honest-null for executed-mix judge signals.
- `tests/audio/test_deck_signal.py` is the paired regression that proves those
  unverified auto-Rekordbox pairs do not expose lane bands to the Judge.
- `midi/state.py` records which physical mixer controls actually emitted MIDI in
  the current run, so deck-audio weighting can distinguish touched controls from
  boot defaults.
- `__main__.py` only belongs in this lane for the input-callback hunks that pass
  `deck_snapshot()` and `control_touched_snapshot()` into `DeckAudioCapture`.
  Keep live-budget CLI and TTS shutdown hunks with Packages 10 and 14.
- `deck_context.py` is a large clean hotspot in the broader maintainability map;
  this lane should carry only the new `deck_audio_master_source` evidence text,
  not broad deck-context refactors.

Proof already run:

- `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py -k 'deck_audio or master_source or controller_weighted'`
  passed: 26 tests, 70 deselected.
- `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/state/deck_context.py tests/audio/test_deck_capture.py tests/state/test_deck_context.py`
  passed.
- `uv run pytest -q tests/test_midi_common.py tests/audio/test_deck_capture.py tests/state/test_deck_context.py -k 'controller or deck_audio or master_source or touched or xfader'`
  passed: 32 tests, 79 deselected on the current tree.
- `uv run pytest -q tests/midi/test_state.py tests/audio/test_deck_capture.py tests/state/test_deck_context.py -k 'touched or controller or deck_audio or master_source or xfader'`
  passed: 38 tests, 81 deselected on the current tree.
- `uv run ruff check src/vibemix/midi/state.py src/vibemix/audio/deck_capture.py src/vibemix/state/deck_context.py tests/audio/test_deck_capture.py tests/state/test_deck_context.py`
  passed on the current tree.
- `uv run ruff check src/vibemix/midi/state.py tests/midi/test_state.py`
  passed on the current tree.
- `uv run pytest -q tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  passed: 120 tests after the auto-Rekordbox deck-pair verification gate.
- `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/audio/deck_signal.py src/vibemix/state/deck_context.py tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/state/test_deck_context.py`
  passed.
- Live Tauri/Rekordbox proof, session `20260531-110001`, reproduced the user's
  complaint: current-source Tauri owned `8765`/`1420`, opened `BlackHole 16ch`
  at 4 channels, but Deck 2-only prompting still produced
  `deck_audio_activity=A_active+B_silent`; raw CoreMIDI input `DDJ-FLX4`
  produced `raw_midi_count=0`, `ipc.learn.midi_position=0`, and
  `midi_events=0`.
- Patched live Tauri/Rekordbox proof, session `20260531-111154`, kept that same
  setup honest: after a `say`-prompted Deck 2-only test, frames stayed
  `mode=deck_pair_capture_unverified`, `per_deck_audio=unverified_not_attached`,
  `isolated_decks=false`, and `active_sides_seen=A` instead of treating
  channels `0/1` as verified Deck A or declaring Deck B truly silent.
- Broader non-beginner regression slice after the verification-gate patch passed:
  `uv run pytest -q tests/library tests/intel tests/ipc tests/ui_bus tests/prompts/test_filter.py tests/prompts/test_negative_dict.py tests/state/test_refresh.py tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/midi/test_state.py tests/test_audio_macos.py tests/test_main_smoke.py`
  reported 1593 passed, 1 skipped, and 1 declared xfail.
- Dirty-package Python Ruff sweep passed:
  `git status --short --untracked-files=all | awk '{print $2}' | rg '\.py$' | xargs uv run ruff check`.
- `git diff --check -- src/vibemix/audio/deck_capture.py src/vibemix/state/deck_context.py`
  passed.
- `uv run pytest -q tests/audio/test_deck_capture.py tests/midi/test_state.py::test_control_touched_snapshot_tracks_real_absolute_controls_only tests/state/test_deck_context.py::test_deck_audio_separation_context_marks_configured_deck_pair_capture tests/runtime/test_ws_bus_deck_state.py::test_payload_marks_configured_deck_pair_capture tests/runtime/test_ws_bus_deck_state.py::test_configured_deck_pair_capture_forces_audio_window_on_silent_frame`
  passed: 18 tests after adding the input-callback handoff and boot-default
  touched-control guard.
- `uv run pytest -q tests/midi/test_state.py tests/midi/test_profile_flx4_golden.py tests/test_midi_common.py tests/audio/test_deck_capture.py`
  passed: 52 tests, 6 expected deprecation warnings from the legacy string-port
  listener shim.
- `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/midi/state.py src/vibemix/__main__.py src/vibemix/state/deck_context.py tests/audio/test_deck_capture.py tests/midi/test_state.py tests/state/test_deck_context.py`
  passed.
- Fresh full source boot: `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`
  reached `127.0.0.1:8765`, selected `DDJ-FLX4`, opened `BlackHole 16ch` as 4ch,
  and MCP observed `deck_audio_separation_context[...] master_source=controller_weighted_deck_pairs`.
  No Rekordbox audio was present, so this proves runtime/callback/context health,
  not audible Deck B routing.

Remaining gate:

- Needs a full live deck-audio proof with controller posture changing the audible
  master/citation context, not only unit-level synthesized arrays.

Current runtime technical lanes audit, 2026-05-31 11:44 +03:

- Default review decision: keep Packages 12, 13, 14, and 15 as narrow technical
  commits, and keep the Deck Audio Controller-Weighted lane on hold. They can
  be reviewed early because their focused tests are green, but none of them
  replaces the final live controller/audio proof.
- Shared-file hunk boundary: Package 12 shares `src/vibemix/runtime/session_loop.py`
  with IPC Packages 2/3; Package 14 and the Deck Audio hold lane share
  `src/vibemix/__main__.py` with Package 10. Never whole-file stage either file
  while those lanes remain separate.
- Current footprint: Package 12 touches `index_sqlite_vec_memory.py` at `76 / 19`
  and `session_loop.py` at `24 / 2`; Package 13 touches
  `check_sidecar_bundle_ready.py` at `25 / 0`; Package 14 depends on
  `__main__.py` `171 / 3` but owns only TTS shutdown hunks; Package 15 touches
  `_audio_macos.py` at `2 / 1`; the Deck Audio hold lane carries the larger
  `deck_capture.py` `181 / 6`, `deck_signal.py` `7 / 3`, MIDI, and
  deck-context diffs.
- Test evidence refreshed after this audit:
  `uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py`
  passed with 34 tests; `uv run pytest -q tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py`
  passed with 20 tests; targeted `tests/test_main_smoke.py` shutdown/auto-master
  selection passed with 3 tests; targeted macOS audio auto-master selection
  passed with 3 tests; `uv run pytest -q tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 120 tests.
- Readiness evidence: focused Ruff across the runtime/memory/sidecar/audio/deck
  files passed; `uv run python -m vibemix library models --json` reported
  `required_ready: true` and `all_ready: true`; `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only`
  reported the Apple Silicon sidecar bundle ready.
- What the current proof covers: stale sqlite-vec/CLAP readiness behavior,
  diagnostic-session memory-ingest gating, sidecar bundle/schema freshness
  validation, nested TTS provider cleanup at shutdown, BlackHole 16ch
  auto-master device selection, and deterministic deck-audio/context routing
  regressions.
- What remains unproven: full Tauri/DDJ live durability for Package 12,
  release-package build/signing for Package 13, audible deck audio plus a cited
  co-host moment for Package 15, and the controller-weighted hold lane's full
  proof that controller posture changes audible master/citation context.
- Split abort condition: if Package 14 lands alone, its cached `__main__.py`
  diff must include only `_close_tts_chain()` and shutdown cleanup. If Package
  15 lands alone, its review note must say "route/device selection only" and
  must not claim musical grounding. If the Deck Audio hold lane is staged, it
  must carry the missing live proof named above or stay out of the shipping
  stack.

## Hold Lane - Mix Timing Oracle

Suggested commit if/when it ships: `feat(mix-timing): add spoken drop timing oracle`

Hold:

- `src/vibemix/agent/line_voice.py`
- `src/vibemix/audio/xfade.py`
- `src/vibemix/audio/cues.py`
- `src/vibemix/audio/voice_mix.py`
- `src/vibemix/runtime/automix_demo.py`
- `src/vibemix/runtime/drop_reaction.py`
- `src/vibemix/state/event_detector.py`
- `src/vibemix/state/refresh.py`
- `scripts/automix_demo_smoke.py`
- `tests/agent/test_line_voice.py`
- `tests/audio/test_cues.py`
- `tests/audio/test_voice_mix.py`
- `tests/audio/test_xfade.py`
- `tests/runtime/test_automix_demo.py`
- `tests/runtime/test_drop_reaction.py`
- `src/vibemix/state/transition_clock.py`
- `tests/state/test_transition_clock.py`
- `src/vibemix/state/drop_predict.py`
- `tests/state/test_event_detector_drop.py`
- `tests/state/test_drop_predict.py`

Reason:

- This is drop-timing/cohost behavior groundwork with no production integration yet.
- Another cloud session is already investigating mix/audio core, so keep related
  follow-up isolated until that work lands or gets explicitly merged.
- `xfade`, `cues`, `automix_demo`, and `transition_clock` are tracked clean in
  the current checkout, but stay documented here as the owning lane if they
  reappear dirty.
- `scripts/automix_demo_smoke.py` is a manual smoke helper for that automix lane;
  keep it with the mix investigation instead of staging it with runtime memory or
  general tooling.
- `line_voice`, `voice_mix`, and `drop_reaction` extend the same deterministic
  automix reel into spoken drop reactions. Keep them with the mix/audio hold lane
  until the lint and live-audio proof are complete.
- `drop_predict.py` is a pure section/position helper for "seconds until the
  next drop", and `refresh.py` now wires that helper into the single-writer tick
  by writing `state.predicted_drop_in_sec` from audible-deck sections with
  confidence/horizon guards. Keep both with this hold lane until lint,
  live/audio proof, and speech grounding are complete.
- `event_detector.py` now has a dormant `VIBEMIX_DROP_CALL` gate that can emit a
  `DROP` event from the predicted-drop crossing. Keep it with this hold lane; it
  is no longer only offline/demo groundwork and needs the full live/audio/
  grounding proof before promotion.
- `tests/state/test_event_detector_drop.py` is the matching unit proof for that
  dormant gate: opt-in, no default firing, crossing behavior, and no repeated
  firing while still inside the arm window.

Proof already run:

- `uv run pytest -q tests/audio/test_xfade.py tests/audio/test_cues.py tests/runtime/test_automix_demo.py tests/state/test_transition_clock.py`
  passed: 36 tests.
- `uv run python scripts/automix_demo_smoke.py --dry-run`
  passed: printed the synthetic tone transition plan and reaction reel without
  opening audio.
- `uv run python scripts/automix_demo_smoke.py --dry-run --outro-start 24 --intro-start 4`
  passed after the active mix-lane update: printed a `fade_at_outro_start`
  reaction reel without opening audio.
- `uv run ruff check scripts/automix_demo_smoke.py`
  passed.
- `uv run pytest -q tests/audio/test_cues.py tests/runtime/test_automix_demo.py`
  passed: 12 tests.
- `uv run pytest -q tests/agent/test_line_voice.py tests/audio/test_voice_mix.py tests/runtime/test_drop_reaction.py`
  passed: 19 tests on the current tree.
- Drift refresh, 2026-05-31 12:11 +03:
  `uv run pytest -q tests/state/test_drop_predict.py` passed 9 tests, and
  `uv run ruff check src/vibemix/state/drop_predict.py tests/state/test_drop_predict.py`
  passed. This proves only the pure helper, not live/audio timing or co-host
  speech grounding.
- Drift refresh, 2026-05-31 12:14 +03:
  `uv run pytest -q tests/state/test_refresh.py -k predicted_drop` passed 1
  test, proving the default predictive-drop guard still holds for that focused
  slice. `uv run ruff check src/vibemix/state/refresh.py src/vibemix/state/drop_predict.py tests/state/test_drop_predict.py`
  currently fails on import sorting in `src/vibemix/state/refresh.py`; keep this
  as a hold-lane gate rather than fixing product code in the planning session.
- Intra-path drift refresh, 2026-05-31 12:17 +03:
  `git diff --numstat -- src/vibemix/state/refresh.py` reports `64 / 0`. The
  assigned `refresh.py` hunk now also imports `os` and adds opt-in
  `VIBEMIX_DROP_DEBUG` countdown logging through `_log_drop_countdown()`. This
  remains observation-only by intent, but it is still runtime behavior and needs
  the same lint/live/audio/grounding gates before promotion.

Manual proof:

- `uv run python scripts/automix_demo_smoke.py`

Remaining gate:

- `uv run ruff check src/vibemix/agent/line_voice.py src/vibemix/audio/voice_mix.py src/vibemix/runtime/drop_reaction.py tests/agent/test_line_voice.py tests/audio/test_voice_mix.py tests/runtime/test_drop_reaction.py`
  currently fails on two small test hygiene issues in `tests/runtime/test_drop_reaction.py`
  (`zip(..., strict=...)` and unused `clean`). Fix before shipping this lane.

## Deep Work Lane - Debrief Timeline And Citations

Do not present citation-summary or raw event-timeline metrics as shipped. The old
schema-only IPC reservations have been removed from the shippable baseline.

Current state:

- `ipc.debrief.citation-summary` is absent from the IPC schema, Python wrappers,
  generated TS, and validator.
- `ipc.debrief.event-timeline` is absent from the IPC schema, Python wrappers,
  generated TS, and validator.
- The IPC wiring checker has an empty `RESERVED` set, so future schema-only ghosts
  fail instead of being silently allowlisted.
- MCP `which_handler` reports no matched IPC type for both old names.

Ship path:

- Add backend producer data.
- Add UI consumer behavior.
- Add Python schema tests.
- Add TS validator/session tests.
- Re-add the IPC types only in the same package as the producer, consumer,
  schema/codegen, and wiring checks.

## Latest Package-Wide Verification

Latest package consolidation pass on 2026-05-31:

- Current planning guardrails, 2026-05-31:
  `git diff --shortstat` reports 102 files changed, 5441 insertions, and 1872
  deletions; `git ls-files --others --exclude-standard | wc -l` reports 99.
- Current package-checker refresh after Singularity research/census,
  cue-export, frontend proof, Mixxx research, and CLAP fixture drift:
  `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passes with 201 dirty paths assigned after Packages 0, 0B, and 1 landed. This
  refresh keeps the checker honest across staged, unstaged, and untracked paths;
  keeps the residual local-MOSS `uv.lock` diff plus local helper on hold; and
  assigns Singularity/Mixxx research, cue-export, frontend proof, sexiest-live
  screenshots, and the real-CLAP eval fixture to hold lanes.
- `git diff --check -- .planning/handoffs/2026-05-31-maintainability-map.md .planning/handoffs/2026-05-31-package-checklist.md .planning/handoffs/2026-05-31-dirty-tree-shipping-inventory.md`
  passed.
- `uv run pytest -q tests/scripts/test_check_dirty_package_plan.py`
  passed: 4 tests.
- `uv run ruff check scripts/check_dirty_package_plan.py tests/scripts/test_check_dirty_package_plan.py`
  passed.
- Historical broader verification below is useful context, but it is not a
  substitute for package-specific proof after staging.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  earlier passed: 169 dirty paths exactly listed, 3 generated launch previews ignored,
  and every dirty path assigned to an Include/Hold lane.
- `uv run python scripts/check_ipc_schema.py` passed: 72 wrapper dataclasses
  validate against 72 `oneOf` schema entries; Settings enum/payload parity is OK.
- `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts src/library/api.test.ts src/library/chat.test.ts`
  passed: 4 files, 240 tests.
- `npm --prefix tauri/ui test -- tests/settings/drawer.spec.ts tests/session/components.spec.ts tests/session/render-loop-actions.spec.ts src/settings/components/profile-panel.spec.ts src/settings/components/citation-diagnostics.spec.ts`
  passed: 5 files, 94 tests.
- `uv run pytest -q tests/library tests/intel tests/ipc tests/ui_bus tests/prompts/test_filter.py tests/prompts/test_negative_dict.py tests/state/test_refresh.py tests/audio/test_deck_capture.py tests/audio/test_deck_signal.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/midi/test_state.py tests/test_audio_macos.py tests/test_main_smoke.py`
  passed: 1593 passed, 1 skipped (`transformers` audio decode dependency absent),
  and 1 xfailed declared live-stack pricing decision.
- Dirty-package Python Ruff sweep passed:
  `git status --short --untracked-files=all | awk '{print $2}' | rg '\.py$' | xargs uv run ruff check`.
- `npm --prefix tauri/ui run build` passed: TypeScript check plus Vite build,
  184 modules transformed.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` passed.
- `uv run python scripts/dist/check_sidecar_bundle_ready.py` passed.
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
  passed: all 72 IPC message types have both shell and sidecar references.
- `npm --prefix tauri/ui run check:ipc` passed after regenerating
  `tauri/ui/src/ipc/messages.ts` and `tauri/ui/src/ipc/validator.generated.mjs`.
- `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only`
  passed.
- Removed-IPC ghost scan passed in shippable paths after excluding ignored
  `.claude/worktrees/**`: no hits for `ipc.debrief.citation-summary`,
  `ipc.debrief.event-timeline`, `ipc.library.search`,
  `ipc.library.search_result`, `ipc.library.confidence`,
  `ipc.library.similar_request`, or `ipc.library.similar_result` in `src`,
  `tauri/src-tauri`, `tauri/ui/src`, `tauri/ui/tests`, `tests`, `scripts`, or
  active `.claude` tooling.
- Known lint hold: `uv run ruff check src tests` is still red with 351 older
  repo-wide findings outside the dirty package boundary, and
  `uv run ruff check src tests scripts` is red with 431 findings once legacy
  scripts are included. Do not auto-fix that broad baseline inside the shipping
  package unless the release owner explicitly accepts the churn.

## Local Shadow Audit

Latest local-machine shadow audit on 2026-05-31:

- Product runtime ports are clear: no listeners on `127.0.0.1:8765`, `8766`, or
  Tauri dev port `1420`.
- No current `cargo tauri`, `python -m vibemix`, `vibemix-core`, or installed-app
  runtime process is running. Multiple MCP helper children
  (`vibemix.runtime.dev_mcp_server` / `vibemix.library.mcp_server`) are present,
  but they are not the live app and do not own product ports; prefer repo-local
  CLI/`ws_probe.py` commands for the controller proof if MCP freshness is in
  doubt.
- `/Applications/vibemix.app` and `/Applications/Vibemix.app` are the same signed
  bundle inode `53624733` (`world.bravoh.vibemix`, Team `UK7DYFK6F8`, mtime
  `2026-05-30 20:52:30`). Its embedded sidecar hash is
  `9f19207de84b0b374a8392c7455162bdb2c6354f`; the repo sidecar hash is
  `944893788f78953da5a5063cd9379c83466e5c07`. This installed app is stale
  relative to source.
- `mdfind` sees only `/Applications/vibemix.app`; `launchctl`,
  `~/Library/LaunchAgents`, `/Library/LaunchAgents`, `/Library/LaunchDaemons`, and
  `sfltool dumpbtm` produced no Vibemix/Bravoh auto-start hits. The remaining
  risk is manual opening of the installed app.
- `git worktree prune --expire now` removed stale metadata for the missing
  `/private/tmp/sv-100-reviewfix-pi5Z2Y` worktree.
- `.claude/worktrees/` contains 22 registered agent worktrees, 7.8 GB total,
  locked to dead PIDs `22077` / `30357`. Every `agent-*` worktree is dirty and
  still contains the removed IPC contracts in 7 files. These paths are ignored by
  normal Git status and normal `rg`, so they do not ship, but broad
  `rg --no-ignore` audits must exclude `.claude/worktrees/**`. Do not delete them
  unless the owner accepts losing or separately archiving uncommitted agent work.

## Final Live Proof Gate

Current probe on 2026-05-31: source-mode `uv run python -m vibemix --session`
reached `ws://127.0.0.1:8765`, streamed idle `ipc.session.snapshot` frames, and
answered schema-valid `ipc.status.recheck` / `ipc.profile.view` requests. A later
flagless full-live run with `DDJ-FLX4` connected reached `livekit=ok`,
`gemini=ok`, `midi=1`, opened `BlackHole 16ch` as 4-channel deck-pair capture,
and wrote session evidence under
`~/Library/Application Support/vibemix/recordings/20260531-102305/`. Manual
trigger produced a spoken line and voice-meter activity. Because deck audio was
silent, `grounded=False`, `citation_count:0`, and `deck_audio_parts_skipped:
deck_audio_silent` are the expected honest state, not missing-key brain-mute.

Latest pre-controller cleanup on 2026-05-31: a stale packaged sidecar at
`/Applications/vibemix.app/Contents/Resources/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin`
was holding `127.0.0.1:8765` as PID `16329`; it ignored `SIGTERM`, was stopped
with `SIGKILL`, and ports `8765`, `8766`, and `1420` were left clear. A fresh
source-mode probe, session `20260531-105418`, then reached `8765`, streamed 58
`ipc.session.snapshot` frames in two seconds, answered `ipc.status.recheck` with
`midi=1 screen=ok livekit=connecting gemini=down`, and shut down cleanly with
all three ports clear again.

Installed-app caution: `/Applications/vibemix.app` and `/Applications/Vibemix.app`
are the same signed app bundle (`world.bravoh.vibemix`, version `0.0.1`), but
its embedded sidecar hash differs from the repo bundle. It is not registered as
a LaunchAgent and it is not pinned in the Dock, so it should not auto-respawn;
do not open it during the live proof. Launch current source with
`VIBEMIX_DEV_SIDECAR=1 cargo tauri dev --no-watch` or
`VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`.

Tauri dev-source proof initially found a real split: session `20260531-102701`
booted the renderer/Rust bridge but stayed on `BlackHole 2ch` because
`VIBEMIX_AUTO_MASTER_INPUT=1` hijacked the explicit 16ch upgrade probe. Package
15 fixes that. The post-fix Tauri rerun, session `20260531-103122`, records
`BlackHole_16ch`, `input_channels=16`, `opened_channels=4`,
`deck_pair_capture_configured`, `livekit=ok`, `gemini=ok`, `midi=1`, renderer
`ipc.learn.midi_position` frames, pill reaction/expand frames, and real jog/play
MIDI evidence.

Latest Rekordbox/controller proof: session `20260531-110001` reproduced the
reported live shape in current-source Tauri: `BlackHole 16ch` opened with 4
channels, but Rekordbox audio arrived only on channels `0/1`
(`deck_audio_activity=A_active+B_silent`). Raw CoreMIDI input `DDJ-FLX4` emitted
zero mixer/control messages (`raw_midi_count=0`), and websocket frames also showed
`ipc.learn.midi_position=0` / `midi_events=0` while the status badge still showed
`midi=1` because the port was merely present. Session `20260531-111154` proves the
patched behavior is honest under that bad live route: auto Rekordbox deck-pair
capture stays `mode=deck_pair_capture_unverified`,
`per_deck_audio=unverified_not_attached`, `isolated_decks=false`, and
`active_sides_seen=A` rather than declaring Deck B truly silent. Actual Deck B
isolation and mixer/EQ/crossfader state remain blocked until Rekordbox routes Deck
2 to BlackHole channels 3/4 and the controller emits MIDI/HID/control state the
app can observe.

Latest readiness probe before the next controller run:
`uv run python scripts/learn_live_readiness.py --require none --loopback-signal-seconds 1 --capture-matrix-seconds 1 --out /tmp/vibemix-live-readiness-now.json`
reported DDJ-FLX4 present, Rekordbox running, BlackHole 16ch present at 48 kHz,
and product port `8765` not listening, but current Rekordbox audio settings had
`audio_output_device_name=DDJ-FLX4` / `audio_input_device_name=DDJ-FLX4`.
Direct BlackHole 16ch capture was silent (`rms=0.0`, `peak=0.0`) and the capture
matrix found all sampled DJ/loopback inputs below the signal floor. The next
human-side action is to set Rekordbox Audio output to BlackHole 16ch or the
intended aggregate route, with Deck 1 on channels 1/2 and Deck 2 on 3/4, then
start playback before launching the final Vibemix proof.

Live source-app proof after the route fix, session `20260531-113240`: launched
current source via
`VIBEMIX_DEV_SIDECAR=1 VIBEMIX_INPUT_DEVICE='BlackHole 16ch' VIBEMIX_DECK_AUDIO_CHANNELS=auto cargo tauri dev --no-watch`.
The app opened `BlackHole 16ch @ 48000Hz (4ch)`, selected `DDJ-FLX4`
(`profile=pioneer_ddj_flx4`), and exposed the Tauri UI at `127.0.0.1:1420` with
sidecar bus `127.0.0.1:8765`. `ipc.status.tick` stayed
`livekit=ok gemini=ok midi=1 screen=unavailable`; `ipc.session.snapshot` streamed
grounded music frames with BPM `153.8` and track owner `mix`; `ipc.learn.midi_position`
showed live controller positions including EQ, volume, play, tempo, and `xfader`.
A raw CoreMIDI probe against `DDJ-FLX4` captured 162 messages in 12 seconds,
including note events and many `control_change` messages on channels 0/1.
Most importantly, `events.jsonl` moved from the honest unverified state
`deck_audio_activity=A_active+B_silent` to verified
`mode=deck_pair_capture_configured`, `per_deck_audio=captured_not_attached`,
`isolated_decks=runtime_capture_available`, and
`deck_audio_activity=A_active+B_active`. The cohost produced a PHASE reaction with
`citation_count=2`; the live-claim guard correctly blocked overclaiming deck
identity (`reason=no_resolved_decks`) and replaced the raw deck-specific claim
with the safer line: `I caught the live move. The useful note is the sound change
right there.` A later heartbeat carried a cited audio response
`[aud:rms@68.0]`. This proves the current product path is wired for source Tauri,
websocket UI, BlackHole 16ch deck-pair capture, MIDI controls, grounded cohost,
and pill reaction; the remaining limitation is deck identity/source resolution,
not audio/control wiring.

Tooling update: current-source `ws_trigger` typed IPC now uses an ISO `date-time`
`ts` and returns an immediate reply when a handler answers on the same socket.
The documented `drive-vibemix` `ws_probe.py --ipc` path now builds the same
schema-valid typed frame. Runtime ingress also normalizes finite numeric `ts`
values from older local drive clients, so stale MCP children no longer
schema-reject solely because of the timestamp shape. Restart the MCP host before
the long run anyway so the callable tool process loads the current immediate
reply behavior.

Dev-environment caveat: the missing local CLAP runtime dependency gap was closed
with `uv sync --group dev --extra ai-local`, and `uv run python -m vibemix library
models --json` reports CLAP ONNX plus CUE-DETR ready. The follow-up source-mode
boot exposed a stale empty `memory.db` sqlite-vec table pinned at 768 dimensions;
Package 12 self-heals that empty-table case before current 512-d CLAP inserts.
The first bounded rerun proved the self-heal and bus reachability, then exposed
that diagnostic `--session` could accidentally run CLAP memory indexing on close.
Package 12 now disables memory ingest for that sidecar-only probe; the follow-up
rerun exited cleanly after Ctrl-C.

Still pending before calling the release train product-ready: audible deck-audio
proof, a cited co-host moment, and a longer controller set pass.

Run this when the DDJ, Tauri app runtime, and audible deck route are available:

1. Launch current source:
   `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`
2. Attach as a client to `127.0.0.1:8765`.
3. Drive at least one safe control, such as
   `.claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}' --watch ipc.status.tick --seconds 3`
   or a manual co-host trigger.
4. Inspect UI log:
   `~/Library/Application Support/world.bravoh.vibemix/vibemix/logs/ui.log`
5. Inspect session `events.jsonl`.
6. Confirm no brain-mute signature: repeated `citation_count:0` plus empty
   `transcript_delta`.
7. Do a long-set pass with the controller plugged in before calling the release train
   product-ready.
