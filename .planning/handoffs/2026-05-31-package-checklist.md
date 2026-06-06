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

## Package 0K - Integration Audit Ruff Hygiene

Suggested commit: `chore(tooling): clean integration audit imports`

Include:

- `scripts/integration_audit.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Product source changes, generated audit outputs, and orphan baseline refreshes.

Reason:

- `scripts/integration_audit.py` carried two stale imports (`field`, `Any`) that
  make the focused orphan-inventory tooling lint gate fail even though the audit
  behavior is unchanged.
- This is a tooling-only hygiene package so future baseline refreshes can run
  the script's focused ruff gate without unrelated lint noise.

Proof before staging:

- `uv run ruff check scripts/integration_audit.py tests/scripts/test_orphan_inventory.py`
- `uv run pytest -q tests/scripts/test_orphan_inventory.py`
- `git diff --check -- scripts/integration_audit.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0L - Model Literal Gate Test Ruff Hygiene

Suggested commit: `test(repo): clean model literal gate lint`

Include:

- `tests/repo/test_model_literal_gate.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Model-router source, LLM runtime code, prompts, and generated files.

Reason:

- The model-literal gate test intentionally unpacks a source line number but
  only asserts the offending path and line text. Prefixing the unused binding
  keeps the focused repo-test ruff gate clean without changing gate behavior.

Proof before staging:

- `uv run ruff check tests/repo/test_model_literal_gate.py`
- `uv run pytest -q tests/repo/test_model_literal_gate.py`
- `git diff --check -- tests/repo/test_model_literal_gate.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0M - Live Spike Scaffold Test Ruff Hygiene

Suggested commit: `test(repo): clean live spike scaffold lint`

Include:

- `tests/repo/test_live_spike_scaffold.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Spike runtime scripts, model-router source, prompts, and live app runtime files.

Reason:

- The live-spike scaffold guard imported `re` and `pytest` without using either.
  Removing the dead imports keeps the focused repo-test ruff gate clean without
  changing the scaffold assertions or the spike entry point.

Proof before staging:

- `uv run ruff check tests/repo/test_live_spike_scaffold.py`
- `uv run pytest -q tests/repo/test_live_spike_scaffold.py`
- `git diff --check -- tests/repo/test_live_spike_scaffold.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0N - Tauri Activation Policy Test Ruff Hygiene

Suggested commit: `test(repo): clean tauri activation policy lint`

Include:

- `tests/repo/test_tauri_activation_policy.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Tauri Rust source, generated UI files, release signing assets, and app runtime files.

Reason:

- The activation-policy guard had a stale extra blank line in its import block.
  Removing it keeps the focused repo-test ruff gate clean without changing the
  static assertions about foregroundable app behavior.

Proof before staging:

- `uv run ruff check tests/repo/test_tauri_activation_policy.py`
- `uv run pytest -q tests/repo/test_tauri_activation_policy.py`
- `git diff --check -- tests/repo/test_tauri_activation_policy.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0O - Kaan Action V4 Surface Test Ruff Hygiene

Suggested commit: `test(repo): clean kaan action v4 surface lint`

Include:

- `tests/repo/test_kaan_action_v4_surface.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Launch copy, release scripts, signing/notarization assets, and app runtime files.

Reason:

- The v4 surface guard loads the canonical launch slop checker dynamically, then
  reads a constant with `getattr`. Direct attribute access satisfies Ruff's
  constant-getattr rule while keeping the same drift-check behavior.

Proof before staging:

- `uv run ruff check tests/repo/test_kaan_action_v4_surface.py`
- `uv run pytest -q tests/repo/test_kaan_action_v4_surface.py`
- `git diff --check -- tests/repo/test_kaan_action_v4_surface.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0P - Cut Release Guard Test Ruff Hygiene

Suggested commit: `test(repo): clean cut release guard lint`

Include:

- `tests/repo/test_cut_release_invokes_bravoh_server.py`
- `tests/repo/test_cut_release_invokes_check_gate.py`
- `tests/repo/test_cut_release_no_autonomous_publish.py`
- `tests/repo/test_cut_release_tag_regex.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Cut-release scripts, signing/notarization assets, packaged artifacts, and app
  runtime files.

Reason:

- The cut-release guard tests had stale extra blank lines after their import
  blocks. Removing them keeps the focused repo-test ruff gate clean without
  changing any release-proof assertions.

Proof before staging:

- `uv run ruff check tests/repo/test_cut_release_invokes_bravoh_server.py tests/repo/test_cut_release_invokes_check_gate.py tests/repo/test_cut_release_no_autonomous_publish.py tests/repo/test_cut_release_tag_regex.py`
- `uv run pytest -q tests/repo/test_cut_release_invokes_bravoh_server.py tests/repo/test_cut_release_invokes_check_gate.py tests/repo/test_cut_release_no_autonomous_publish.py tests/repo/test_cut_release_tag_regex.py`
- `git diff --check -- tests/repo/test_cut_release_invokes_bravoh_server.py tests/repo/test_cut_release_invokes_check_gate.py tests/repo/test_cut_release_no_autonomous_publish.py tests/repo/test_cut_release_tag_regex.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0Q - Cut Release Preflight Test Ruff Hygiene

Suggested commit: `test(scripts): clean cut release preflight lint`

Include:

- `tests/scripts/test_cut_release_preflight.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Cut-release scripts, signing/notarization assets, packaged artifacts, and app
  runtime files.

Reason:

- The cut-release preflight test imported `pytest` without using it. Removing
  the dead import keeps the focused scripts-test ruff gate clean without
  changing any release gate assertions.

Proof before staging:

- `uv run ruff check tests/scripts/test_cut_release_preflight.py`
- `uv run pytest -q tests/scripts/test_cut_release_preflight.py`
- `git diff --check -- tests/scripts/test_cut_release_preflight.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0R - Grey Area Log Test Ruff Hygiene

Suggested commit: `test(scripts): clean grey area log lint`

Include:

- `tests/scripts/test_grey_area_log.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Integration audit source, planning phase archives, and app runtime files.

Reason:

- The grey-area log contract test imported `pytest` without using it. Removing
  the dead import keeps the focused scripts-test ruff gate clean without
  changing the integration-audit assertions.

Proof before staging:

- `uv run ruff check tests/scripts/test_grey_area_log.py`
- `uv run pytest -q tests/scripts/test_grey_area_log.py`
- `git diff --check -- tests/scripts/test_grey_area_log.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0S - Integration Audit V2 Test Ruff Hygiene

Suggested commit: `test(scripts): clean integration audit v2 lint`

Include:

- `tests/scripts/test_integration_audit_v2_1.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Integration audit source, planning archives, and app runtime files.

Reason:

- The v2.1 integration-audit contract test imported `pytest` without using it.
  Removing the dead import keeps the focused scripts-test ruff gate clean
  without changing audit-generation assertions.

Proof before staging:

- `uv run ruff check tests/scripts/test_integration_audit_v2_1.py`
- `uv run pytest -q tests/scripts/test_integration_audit_v2_1.py`
- `git diff --check -- tests/scripts/test_integration_audit_v2_1.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0T - Changelog Test Ruff Hygiene

Suggested commit: `test(scripts): clean changelog test lint`

Include:

- `tests/scripts/test_populate_changelog.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Changelog generator source, generated changelog files, release scripts, and
  app runtime files.

Reason:

- The changelog dry-run test assigned the default output path but intentionally
  did not assert on it. Removing the dead local keeps the focused scripts-test
  ruff gate clean without changing the dry-run contract.

Proof before staging:

- `uv run ruff check tests/scripts/test_populate_changelog.py`
- `uv run pytest -q tests/scripts/test_populate_changelog.py`
- `git diff --check -- tests/scripts/test_populate_changelog.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0U - Dayzero Test Ruff Hygiene

Suggested commit: `test(scripts): clean dayzero test lint`

Include:

- `tests/scripts/test_dayzero.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Dayzero scripts, release/proxy runtime files, and app runtime files.

Reason:

- The Day-Zero dry-run script tests imported `pytest` without using it.
  Removing the dead import keeps the focused scripts-test ruff gate clean
  without changing dry-run coverage.

Proof before staging:

- `uv run ruff check tests/scripts/test_dayzero.py`
- `uv run pytest -q tests/scripts/test_dayzero.py`
- `git diff --check -- tests/scripts/test_dayzero.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0V - Demo Film No-AI-VO Test Ruff Hygiene

Suggested commit: `test(scripts): clean demo film no-ai-vo lint`

Include:

- `tests/scripts/test_demo_film_no_ai_vo.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Demo-film scripts, policy docs, launch assets, TTS code, and app runtime files.

Reason:

- The no-AI-VO demo-film guard had a placeholder-free f-string and an ambiguous
  loop variable in its violation message builder. Cleaning those keeps the
  focused scripts-test ruff gate clean without changing the forbidden-token scan.

Proof before staging:

- `uv run ruff check tests/scripts/test_demo_film_no_ai_vo.py`
- `uv run pytest -q tests/scripts/test_demo_film_no_ai_vo.py`
- `git diff --check -- tests/scripts/test_demo_film_no_ai_vo.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0W - Kaan Action Rollup Test Ruff Hygiene

Suggested commit: `test(scripts): clean kaan action rollup lint`

Include:

- `tests/scripts/test_kaan_action_rollup.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Integration audit source, Kaan action docs, signing/legal artifacts, and app
  runtime files.

Reason:

- The Kaan-action rollup contract test had a dead `pytest` import, ambiguous
  row variable names, and a single-item list slice. Cleaning those keeps the
  focused scripts-test ruff gate clean without changing rollup semantics.

Proof before staging:

- `uv run ruff check tests/scripts/test_kaan_action_rollup.py`
- `uv run pytest -q tests/scripts/test_kaan_action_rollup.py`
- `git diff --check -- tests/scripts/test_kaan_action_rollup.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0X - CLI Library Similar Test Ruff Hygiene

Suggested commit: `test(scripts): clean library similar cli lint`

Include:

- `tests/scripts/test_cli_library_similar.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- CLI implementation, library cache code, app runtime files, and generated files.

Reason:

- The library-similar CLI test had a stale extra blank line between its marker
  import and module-level `pytestmark`. Removing it keeps the focused
  scripts-test ruff gate clean without changing CLI coverage.

Proof before staging:

- `uv run ruff check tests/scripts/test_cli_library_similar.py`
- `uv run pytest -q tests/scripts/test_cli_library_similar.py`
- `git diff --check -- tests/scripts/test_cli_library_similar.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0Y - Gemini Text Ordering Spike Test Ruff Hygiene

Suggested commit: `test(scripts): clean gemini text ordering spike lint`

Include:

- `tests/scripts/test_spike_gemini_text_ordering.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Spike harness source, Gemini/cohost prompts, live runtime files, and generated
  spike artifacts.

Reason:

- The Gemini text-ordering spike test had a stale extra blank line after its
  `pytest` import. Removing it keeps the focused scripts-test ruff gate clean
  without changing dry-run spike coverage.

Proof before staging:

- `uv run ruff check tests/scripts/test_spike_gemini_text_ordering.py`
- `uv run pytest -q tests/scripts/test_spike_gemini_text_ordering.py`
- `git diff --check -- tests/scripts/test_spike_gemini_text_ordering.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0Z - CLI Library Search Test Ruff Hygiene

Suggested commit: `test(scripts): clean library search cli lint`

Include:

- `tests/scripts/test_cli_library_search.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- CLI implementation, `src/vibemix/__main__.py`, library cache code, app runtime
  files, and generated files.

Reason:

- The library-search CLI test had a stale extra blank line before `pytestmark`
  and an unnecessary explicit UTF-8 argument on a string encode. Cleaning those
  keeps the focused scripts-test ruff gate clean without changing cached-query
  behavior.

Proof before staging:

- `uv run ruff check tests/scripts/test_cli_library_search.py`
- `uv run pytest -q tests/scripts/test_cli_library_search.py`
- `git diff --check -- tests/scripts/test_cli_library_search.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AQ - Overnight QA Sven Quality Layer

Suggested commit: `feat(eval): attach Sven quality to overnight findings`

Include:

- `scripts/eval/replay_harness.py`
- `scripts/eval/respan_sven_heartbeat_judge.py`
- `tests/eval/test_replay_harness.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Hold:

- `scripts/eval/respan_sven_sim.py`

Keep out:

- Live runtime, co-host say/when code, UI surfaces, package/release scripts,
  unrelated Respan simulation experiments, and any app-launch proof artifacts.

Reason:

- The overnight replay harness already emits keyless findings. This package wires
  the existing Respan Sven real-line judge as an optional Layer-B quality payload
  behind `--quality-respan`, keeping `quality: null` when credentials or
  invocation rows are absent.

Proof before staging:

- `uv run pytest -q tests/eval/test_replay_harness.py`
- `uv run pytest -q tests/eval/test_replay_harness.py tests/eval/test_replay_harness_cooldowns.py tests/eval/test_replay_harness_phase_41.py`
- `uv run ruff check scripts/eval/replay_harness.py scripts/eval/respan_sven_heartbeat_judge.py tests/eval/test_replay_harness.py`
- `RESPAN_API_KEY= uv run python -m scripts.eval.replay_harness --corpus tests/eval/fixtures --judges noop --output "$tmpdir/out" --use-detector-predictions --findings-json "$tmpdir/findings.json" --quality-respan`
- `git diff --cached --check`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AA - Replay Linter Test Ruff Hygiene

Suggested commit: `test(scripts): clean replay linter test lint`

Include:

- `tests/scripts/test_replay_linter.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Replay linter source, replay fixtures, session artifacts, and app runtime files.

Reason:

- The replay-linter contract test had a stale extra blank line after `pytest`
  and used a manual adjacent-pair `zip`. Using `itertools.pairwise` keeps the
  focused scripts-test ruff gate clean without changing monotonicity coverage.

Proof before staging:

- `uv run ruff check tests/scripts/test_replay_linter.py`
- `uv run pytest -q tests/scripts/test_replay_linter.py`
- `git diff --check -- tests/scripts/test_replay_linter.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AB - Transition Judge Test Ruff Hygiene

Suggested commit: `test(intel): clean transition judge test lint`

Include:

- `tests/intel/test_transition_judge.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Intel source, live signal source, cohost/runtime files, and generated files.

Reason:

- The transition-judge test import block drifted from Ruff ordering. Sorting
  the imported names keeps the focused intel-test ruff gate clean without
  changing judge assertions.

Proof before staging:

- `uv run ruff check tests/intel/test_transition_judge.py`
- `uv run pytest -q tests/intel/test_transition_judge.py`
- `git diff --check -- tests/intel/test_transition_judge.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AC - Library Centering Test Ruff Hygiene

Suggested commit: `test(library): clean centering test lint`

Include:

- `tests/library/test_centering.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Library centering source, index implementations, runtime files, and generated files.

Reason:

- The centering test zips ids and vectors with equal expected lengths. Adding
  `strict=True` keeps the focused library-test ruff gate clean while preserving
  the test's batch input contract.

Proof before staging:

- `uv run ruff check tests/library/test_centering.py`
- `uv run pytest -q tests/library/test_centering.py`
- `git diff --check -- tests/library/test_centering.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AD - Cue Export Test Ruff Hygiene

Suggested commit: `test(library): clean cue export test lint`

Include:

- `tests/library/test_cue_export.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Cue export source, Viber/library tool code, runtime files, and generated files.

Reason:

- The cue-export test had a stale extra blank line and zips marks/cues with
  equal expected lengths. Cleaning both keeps the focused library-test ruff gate
  clean without changing cue mapping assertions.

Proof before staging:

- `uv run ruff check tests/library/test_cue_export.py`
- `uv run pytest -q tests/library/test_cue_export.py`
- `git diff --check -- tests/library/test_cue_export.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AE - Library CLI Exit Codes Test Ruff Hygiene

Suggested commit: `test(library): clean cli exit codes test lint`

Include:

- `tests/library/test_cli_exit_codes.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- CLI implementation, `src/vibemix/__main__.py`, library curate source, runtime
  files, and generated files.

Reason:

- The CLI exit-code tests imported `io` and `sys` without using them and had a
  stale extra blank line in the import block. Removing the dead imports keeps
  the focused library-test ruff gate clean without changing exit-code coverage.

Proof before staging:

- `uv run ruff check tests/library/test_cli_exit_codes.py`
- `uv run pytest -q tests/library/test_cli_exit_codes.py`
- `git diff --check -- tests/library/test_cli_exit_codes.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AF - Store Parity Test Ruff Hygiene

Suggested commit: `test(library): clean store parity test lint`

Include:

- `tests/library/test_store_parity.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Store implementations, vector fixtures, runtime files, and generated files.

Reason:

- The store-parity tests had an obsolete import-only `noqa` and several equal
  length zip operations. Removing the stale `noqa` and adding `strict=True`
  keeps the focused library-test ruff gate clean without changing parity checks.

Proof before staging:

- `uv run ruff check tests/library/test_store_parity.py`
- `uv run pytest -q tests/library/test_store_parity.py`
- `git diff --check -- tests/library/test_store_parity.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AG - Pyrekordbox Install Test Ruff Hygiene

Suggested commit: `test(library): clean pyrekordbox smoke lint`

Include:

- `tests/library/test_pyrekordbox_install.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Pyrekordbox dependency declarations, installer/release files, runtime export code,
  and generated files.

Reason:

- The pyrekordbox install smoke test now reads `pyrekordbox.__version__`, so its
  import-only `noqa` is stale. Removing the directive keeps the focused
  library-test ruff gate clean without changing the smoke assertions.

Proof before staging:

- `uv run ruff check tests/library/test_pyrekordbox_install.py`
- `uv run pytest -q tests/library/test_pyrekordbox_install.py`
- `git diff --check -- tests/library/test_pyrekordbox_install.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AH - Toolset Starvation Concurrency Test Ruff Hygiene

Suggested commit: `test(library): clean starvation concurrency lint`

Include:

- `tests/library/test_toolset_starvation_concurrency.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Library toolset implementation, Viber/cohost speech paths, runtime files, and
  generated files.

Reason:

- The concurrency acid test intentionally captures worker exceptions for later
  assertion, but the `BLE001` suppression is stale because that rule is not
  enabled here. Removing the obsolete directive keeps the focused ruff gate
  clean without changing concurrency behavior.

Proof before staging:

- `uv run ruff check tests/library/test_toolset_starvation_concurrency.py`
- `uv run pytest -q tests/library/test_toolset_starvation_concurrency.py`
- `git diff --check -- tests/library/test_toolset_starvation_concurrency.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AI - Library Grounding Test Ruff Hygiene

Suggested commit: `test(library): clean grounding test lint`

Include:

- `tests/library/test_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Grounding implementation, cohost speech paths, runtime files, audio capture,
  and generated files.

Reason:

- The library grounding tests had an unused `SimpleNamespace` import and a
  stale annotation `noqa` on a local race-test shim. Removing both keeps the
  focused ruff gate clean without changing grounding decisions or assertions.

Proof before staging:

- `uv run ruff check tests/library/test_grounding.py`
- `uv run pytest -q tests/library/test_grounding.py`
- `git diff --check -- tests/library/test_grounding.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AJ - Library Discovery Test Ruff Hygiene

Suggested commit: `test(library): clean discovery test lint`

Include:

- `tests/library/test_discovery.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Discovery implementation, library stores, Viber/cohost paths, runtime files,
  and generated files.

Reason:

- The discovery test import block had an extra separator blank before the local
  section comment. Removing it keeps the focused ruff gate clean without
  changing discovery assertions.

Proof before staging:

- `uv run ruff check tests/library/test_discovery.py`
- `uv run pytest -q tests/library/test_discovery.py`
- `git diff --check -- tests/library/test_discovery.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AK - Library Energy Test Ruff Hygiene

Suggested commit: `test(library): tighten energy frozen assertion`

Include:

- `tests/library/test_energy.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Energy implementation, audio decode/runtime files, live audio/controller files,
  and generated files.

Reason:

- `EnergyScore` is a frozen dataclass. Replacing a blind `Exception` assertion
  with `FrozenInstanceError` keeps the focused ruff gate clean while preserving
  the frozen-slot regression check.

Proof before staging:

- `uv run ruff check tests/library/test_energy.py`
- `uv run pytest -q tests/library/test_energy.py`
- `git diff --check -- tests/library/test_energy.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AL - Embedding GA Probe Test Ruff Hygiene

Suggested commit: `test(library): clean embedding ga probe lint`

Include:

- `tests/library/test_embedding_ga_probe.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Embedding implementation, Gemini/model routing behavior, runtime files, cache
  migrations, and generated files.

Reason:

- The GA probe tests had an unused `numpy` import and an extra import-block
  separator blank. Removing both keeps the focused ruff gate clean without
  changing mocked probe behavior.

Proof before staging:

- `uv run ruff check tests/library/test_embedding_ga_probe.py`
- `uv run pytest -q tests/library/test_embedding_ga_probe.py`
- `git diff --check -- tests/library/test_embedding_ga_probe.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AM - Library Embed Test Ruff Hygiene

Suggested commit: `test(library): clean embed test lint`

Include:

- `tests/library/test_embed.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Embedding implementation, Gemini/model routing behavior, runtime files, cache
  migrations, and generated files.

Reason:

- The embed tests had an unused `patch` import and an extra import-block
  separator blank. Removing both keeps the focused ruff gate clean without
  changing mocked embed behavior.

Proof before staging:

- `uv run ruff check tests/library/test_embed.py`
- `uv run pytest -q tests/library/test_embed.py`
- `git diff --check -- tests/library/test_embed.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AN - Folder Ingest Test Ruff Hygiene

Suggested commit: `test(library): clean folder ingest test lint`

Include:

- `tests/library/test_folder_ingest.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Folder ingest implementation, stores/index backends, embedder behavior,
  runtime files, and generated files.

Reason:

- The folder ingest tests had stale annotation `noqa`s, an extra import-block
  separator blank, and one intentionally ignored loaded-vector value. Cleaning
  those keeps the focused ruff gate green without changing ingest assertions.

Proof before staging:

- `uv run ruff check tests/library/test_folder_ingest.py`
- `uv run pytest -q tests/library/test_folder_ingest.py`
- `git diff --check -- tests/library/test_folder_ingest.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AO - Folder Ingest Band-Share Test Ruff Hygiene

Suggested commit: `test(library): clean folder ingest band-share lint`

Include:

- `tests/library/test_folder_ingest_band_shares.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Folder ingest implementation, band-share/exemplar implementation, stores,
  runtime files, and generated files.

Reason:

- The folder ingest band-share tests had stale annotation `noqa`s and import
  order/spacing drift. Cleaning those keeps the focused ruff gate green without
  changing side-car band-share assertions.

Proof before staging:

- `uv run ruff check tests/library/test_folder_ingest_band_shares.py`
- `uv run pytest -q tests/library/test_folder_ingest_band_shares.py`
- `git diff --check -- tests/library/test_folder_ingest_band_shares.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 0AP - Codex Curate Stop-Reason Test Ruff Hygiene

Suggested commit: `test(library): clean codex curate stop-reason lint`

Include:

- `tests/library/test_codex_curate_stop_reason.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/__main__.py`, library curate/toolset implementation, Viber/cohost
  behavior, runtime files, and generated files.

Reason:

- The stop-reason seal tests had import ordering/spacing drift in local import
  blocks. Cleaning those keeps the focused ruff gate green without changing the
  CLI seal assertions or production entry point.

Proof before staging:

- `uv run ruff check tests/library/test_codex_curate_stop_reason.py`
- `uv run pytest -q tests/library/test_codex_curate_stop_reason.py`
- `git diff --check -- tests/library/test_codex_curate_stop_reason.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Hold Lane - Cohost Reaction Schema Drift

Suggested commit if/when selected: `fix(ui-bus): reconcile cohost reaction schema`

Include:

- `src/vibemix/ui_bus/schemas/cohost_reaction.py`

Keep out:

- Cohost speech/prompt logic, TTS provider code, runtime coach files, live audio
  controller files, and generated files unless a schema package owns codegen.

Reason:

- Concurrent work left this cohost-adjacent schema dirty while this lane is
  restricted to proof/test cleanup. Track it as a hold lane so the strict dirty
  package guard remains useful without Codex C changing cohost behavior.

Proof before staging:

- Re-run the schema owner tests/codegen checks chosen by the package owner.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Hold Lane - Claude Runtime Orientation Drift

Suggested commit if/when selected: `docs(runtime): capture local live-run caveats`

Hold:

- `.cp_probe.txt`
- `CLAUDE.md`

Reason:

- The current hunk documents Local MOSS invocation, packaged-GUI environment
  flag behavior, and deck passthrough/live audio caveats. It is useful
  orientation, but it is a shared agent doc and should not be smuggled into the
  future-AI routing package.
- `.cp_probe.txt` is a local copy/probe scratch containing CLAUDE guidance text.
  Keep it out of source packages; review/delete only during intentional planning
  scratch cleanup.
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

## Package 0F - Whole Rebuild Brief

Suggested commit: `docs(planning): add whole rebuild brief`

Include:

- `.planning/handoffs/2026-05-31-rebuild-brief.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Product source changes.
- Dependency manifests, generated files, launch/design assets, and release
  packaging code.
- Any attempt to rewrite old packages as the rebuild destination.

Reason:

- The user clarified that a whole rebuild is coming. This package changes the
  planning posture: the package checklist and existing handoffs become
  carry-forward evidence and migration-risk controls, not a mandate to polish
  the old tree into its final shape.

Proof before staging:

- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- .planning/handoffs/2026-05-31-rebuild-brief.md .planning/handoffs/2026-05-31-package-checklist.md`

## Package 0G - Claude Workflow Fanout And Capability Ledger

Suggested commit: `docs(planning): add claude workflow dispatch`

Include:

- `.planning/handoffs/2026-05-31-claude-workflow-dispatch.md`
- `.planning/handoffs/2026-05-31-capability-integration-ledger.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/`

Keep out:

- Product source changes.
- Dependency manifests, generated files, launch/design assets, and release
  packaging code.
- Any claim that a capability is complete without Codex verifier acceptance.

Reason:

- Claude Code can fan out many sub-agents. This planning packet turns that
  breadth into a controlled rebuild workflow: read-only scouts first, one slice
  per implementation team, capability ledger coverage, and a required Codex
  verifier packet before any milestone is trusted.
- It also makes Learn a first-class integration beneficiary. Learn must reuse
  live evidence, cue/judge data, debrief drills, AI-message observability, and
  IPC discipline; it must not remain a siloed curriculum surface.
- The 2026-06-01 packet archive is recovery/coordination data, not product
  code. Keep the recovered Claude workflow docs and the Viber correction in the
  repo tree so `/tmp` cleanup cannot erase the evidence again. The recovered
  Viber packet has a known corrected P0; read
  `.planning/packets/2026-06-01/viber-capability-CORRECTION.md` over the raw
  recovered packet.

Proof before staging:

- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- .planning/handoffs/2026-05-31-claude-workflow-dispatch.md .planning/handoffs/2026-05-31-capability-integration-ledger.md .planning/handoffs/2026-05-31-package-checklist.md .planning/packets/2026-06-01`

## Package 0H - Final Acceptance Contract

Suggested commit: `docs(planning): add final acceptance contract`

Include:

- `.planning/handoffs/2026-05-31-final-acceptance-contract.md`
- `.planning/handoffs/2026-05-31-capability-integration-ledger.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Product source changes.
- Dependency manifests, generated files, launch/design assets, and release
  packaging code.
- Any final-complete claim before Codex verifier acceptance.

Reason:

- This contract defines the true finish line for the rebuild: frontend,
  runtime, Learn, judge voice, local TTS, packaging, one-click install,
  monetized-product posture, docs, and old-hand-off sweep all integrated or
  explicitly deferred. It also requires final accepted work to land on `main`
  only after verification.
- It updates the capability ledger so Claude's fanout and Codex verification
  track commercial/product posture rather than preserving an outdated "fully
  open-source" constraint.

Proof before staging:

- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- .planning/handoffs/2026-05-31-final-acceptance-contract.md .planning/handoffs/2026-05-31-capability-integration-ledger.md .planning/handoffs/2026-05-31-package-checklist.md`

## Package 0I - Product Posture Docs Cleanup

Suggested commit: `docs(product): align public posture with managed service`

Include:

- `README.md`
- `PRODUCT.md`
- `.planning/PROJECT.md`
- `.planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md`
- `docs/code-signing-policy.md`
- `docs/landing/index.html`
- `docs/launch-prep/LAUNCH-SEQUENCE.md`
- `docs/launch-prep/OUTREACH-CALENDAR.md`
- `docs/launch-prep/SHOT-LIST.md`
- `docs/launch/github-meta.md`
- `docs/launch/nda-meturavers.md`
- `docs/launch/partner-brief-meturavers.md`
- `docs/launch/partner-brief.md`
- `docs/launch/partner-capabilities-short.md`
- `docs/launch/partner-capabilities.md`
- `docs/release-process.md`
- `docs/setup-github-repo.md`
- `docs/signing-windows.md`
- `docs/signpath-application.md`

Keep out:

- Product source changes.
- Historical milestone archives unless they are being presented as current
  product posture.
- Any new pricing promise that is not backed by the current billing/control
  plane.

Reason:

- `CODEX_VERDICT-docs-planning-synthesis.md` accepted the monetized-product
  posture and found stale public/open-source-first claims in README, product,
  launch, signing, and KNOWBOOK material. This package narrows "open source" to
  the Apache-licensed client and replaces permanent-free/OSS-first wording with
  Bravoh-managed commercial service language.
- Legitimate license disclosure remains. Hosted proxy, signing route, pricing,
  and Bravoh product services should no longer be constrained by an old
  fully-open-source claim.

Proof already run:

- `rg -n "free, open-source|free open-source|free/open-source|Free, open-source|free · open-source|free · open source|open-source warm-up|open source warm-up|first open-source release|first OSS|Bravoh's first OSS|Bravoh's first open-source|SignPath OSS|OSS-program|OSS launch|Open source under Apache|Open-source AI co-host|open-source AI co-host|open source AI co-host|absorbed by Bravoh|50 €/month|free code signing|OSS eligibility" README.md PRODUCT.md docs/landing docs/launch docs/launch-prep docs/signpath-application.md docs/code-signing-policy.md docs/release-process.md docs/signing-windows.md docs/setup-github-repo.md .planning/PROJECT.md .planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md`
  returns no matches after the cleanup.
- `uv run pytest -q tests/repo/test_readme_shape.py tests/repo/test_readme_feature_matrix_sync.py tests/repo/test_oss_presence.py tests/launch/test_launch_docs.py tests/install/test_windows_smartscreen_doc.py`
  passed: 68 tests.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passed with 286 dirty paths exactly listed and every dirty path assigned; this
  package owns 19 dirty paths.
- `git diff --check -- README.md PRODUCT.md .planning/PROJECT.md .planning/handoffs/2026-05-30-VIBEMIX-KNOWBOOK.md .planning/handoffs/2026-05-31-package-checklist.md docs/code-signing-policy.md docs/landing/index.html docs/launch-prep/LAUNCH-SEQUENCE.md docs/launch-prep/OUTREACH-CALENDAR.md docs/launch-prep/SHOT-LIST.md docs/launch/github-meta.md docs/launch/nda-meturavers.md docs/launch/partner-brief-meturavers.md docs/launch/partner-brief.md docs/launch/partner-capabilities-short.md docs/launch/partner-capabilities.md docs/release-process.md docs/setup-github-repo.md docs/signing-windows.md docs/signpath-application.md`
  passed.

Codex refresh, 2026-05-31 21:56 +03:

- Classification: LAND as public/product posture cleanup, not as release proof.
- Current public wording now says macOS distribution is gated on producing and
  verifying a fresh signed/notarized DMG; Windows targets v0.1.0 stable. The
  remaining "one-click install" grep hits are historical/internal notes, not
  active release claims.
- `uv run pytest -q tests/repo/test_readme_shape.py tests/repo/test_readme_feature_matrix_sync.py tests/repo/test_oss_presence.py tests/launch/test_launch_docs.py tests/install/test_windows_smartscreen_doc.py`
  passed: 68 tests.
- `rg -n "shipping today|signed and notarized, shipping|ships signed|macOS .*today|Windows ships|current signed/notarized|current signed and notarized|current signed \+ notarized|runs local on macOS today|What's already shipping|ingest shipping|one-click install" ...`
  has no active public false-release hits; remaining matches are historical or
  internal "one-click installer" references.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passed with 341 dirty paths exactly listed, every path assigned, and Package
  0I still owning 19 dirty paths.
- `git diff --check --` the docs/posture slice passed after the latest wording
  cleanup.

Remaining gate:

- Run `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  and `git diff --check` across the docs posture slice before staging.

## Package 0J - Retired Scripted Demo Mode

Suggested commit: `fix(demo): retire scripted launch sequencer`

Include:

- `src/vibemix/runtime/demo_mode.py`
- `tests/runtime/test_demo_mode_sequence.py`
- `docs/launch-prep/DEMO-MODE-CONFIG.md`
- `docs/launch-prep/README.md`
- `docs/launch-prep/AUDIO-CAPTURE.md`
- `docs/launch-prep/SHOT-LIST.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live app driving, controller/audio runtime files, cohost speech, prompts,
  DROP-call wiring, and TTS providers.
- Launch screenshots or broader launch collateral.

Reason:

- The queue marks the deterministic demo sequencer as SAFE_NOW because it has no
  runtime importers and conflicts with the live-audio-is-authoritative
  invariant. Removing the module and its pins prevents scripted playback from
  being mistaken for launch proof.
- The launch-prep docs now require each capture take to name the source SHA or
  packaged artifact plus recorded session evidence, rather than citing a retired
  `--demo-mode` flow.

Proof before staging:

- `rg -n "demo_mode|DEMO_SEQUENCE|DEMO-MODE-CONFIG|--demo-mode" src tests docs/launch-prep`
- `uv run pytest -q tests/launch/test_launch_docs.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/runtime/demo_mode.py tests/runtime/test_demo_mode_sequence.py docs/launch-prep/DEMO-MODE-CONFIG.md docs/launch-prep/README.md docs/launch-prep/AUDIO-CAPTURE.md docs/launch-prep/SHOT-LIST.md .planning/handoffs/2026-05-31-package-checklist.md`

## Hold Lane - Demo Source-Run Ship Plan

Suggested commit if/when selected: `docs(demo): capture source-run demo plan`

Hold:

- `.planning/handoffs/2026-05-31-DEMO-SHIP-PLAN.md`

Reason:

- This is a demo-night source-run plan that explicitly says to avoid the stale
  packaged app and run current source with environment flags. It is useful
  operational evidence, but it conflicts with the whole-rebuild posture if read
  as architectural truth.
- Keep it separate from the rebuild brief. Demo readiness and rebuild design are
  different decisions.

Remaining gate:

- If promoted, verify its live-source claims against current source and runtime
  logs. Do not treat the demo note as proof by itself.

## Hold Lane - Rebuild Intake Digests

Suggested commit if/when selected: `docs(rebuild): add intake digest pack`

Hold:

- `.planning/.tmp_filelist.txt`
- `.planning_ls_scratch.txt`
- `.planning/singularity/2026-05-31/whats-next/ingest-dirty-tree-inventory.md`
- `.planning/singularity/2026-05-31/whats-next/ingest-future-ai-routing.md`
- `.planning/singularity/2026-05-31/whats-next/ingest-maintainability-map.md`
- `.planning/singularity/2026-05-31/whats-next/ingest-package-checklist.md`
- `.planning/singularity/2026-05-31/whats-next/ingest-session-census.md`

Reason:

- These are Claude/team digest artifacts and generated file-list scratchpads
  that summarize the existing planning stack for what comes next. They are
  useful rebuild intake material, not source code and not shippable proof.

Remaining gate:

- Review for claim drift against current files before using them as rebuild
  requirements. If they conflict with the package checklist, prefer current
  source plus the checklist.

## Package 1A - AI Message Observability Spine

Suggested commit if/when selected: `feat(observability): persist ai message evidence rows`

Include:

- `src/vibemix/runtime/ai_observability.py`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/bench/run.py`
- `src/vibemix/debrief/drills.py`
- `src/vibemix/debrief/tldr.py`
- `src/vibemix/state/deck_vision.py`
- `src/vibemix/learn/observability.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/__main__.py`
- `src/vibemix/library/codex_curate.py`
- `scripts/eval/judge.py`
- `.planning/handoffs/2026-05-31-ai-message-observability-handoff.md`
- `scripts/verify_ai_observability.py`
- `tests/runtime/test_ai_observability.py`
- `tests/agent/test_dj_cohost.py`
- `tests/bench/test_run_fake.py`
- `tests/scripts/test_verify_ai_observability.py`
- `tests/state/test_deck_vision.py`
- `tests/debrief/test_tldr_length_60_to_90s.py`
- `tests/debrief/test_drill_citations_resolve.py`
- `tests/eval/test_judge_pro_rubric.py`
- `tests/learn/test_observer_boot_wiring.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/repo/test_no_seen_relaxation.py`
- `.planning/packets/2026-06-01/CODEX_READY-ai-message-observability-spine.md`

Reason:

- This package adds the shared AI-message ledger and wires the assistant-facing
  engines into a single inspectable row shape: live co-host, bench, deck vision,
  debrief TLDR/TTS/drills, Viber/Codex curate, eval judges, and Learn tutor
  speech. Rows preserve what the AI said, which model/surface said it, prompt
  and response artifacts where available, and the deck/move/lesson evidence that
  framed the turn.
- Debrief is not an orphaned candidate feature here: `python -m vibemix --debrief
  <session>` dispatches to `vibemix.debrief.main.run()`, which generates cited
  drills and TLDR audio, persists them, and serves them to the Tauri debrief
  window. The current `drills.py` / `tldr.py` dirty hunks are the observability
  layer on that existing product path.
- Deck Vision is also not being promoted as a live deck-identity source in this
  package. `DeckVisionReader` exists and `DeckPoller` has a gated
  `vision_reader` leg, but `vision_enabled` defaults off and
  `_latest_screen_jpeg()` is deliberately a no-op until the real screenshot
  eval/source lands. The current `deck_vision.py` dirty hunk only records
  success/error AI-message artifacts for the reader.
- Shared-file caution: `dj_cohost.py`, `__main__.py`, `codex_curate.py`, and
  `scripts/eval/judge.py` carry other package work too. If this package is split
  from those lanes, stage by hunk and keep only the observability hunks here.
- Repo-gate follow-up: `tests/repo/test_no_seen_relaxation.py` still guards the
  original four-file Viber tool-starvation propagation seam, but Package 1A
  authorizes the generic AI-message `stop_reason` field in the named ledger
  producers/consumers. New producers must still be added explicitly with a
  package justification; the gate is not a free-form escape hatch.

Proof already run:

- `uv run pytest -q tests/scripts/test_verify_ai_observability.py tests/runtime/test_ai_observability.py tests/eval/test_judge_pro_rubric.py tests/agent/test_dj_cohost.py::test_llm_node_logs_ai_message_observability_with_moves tests/agent/test_dj_cohost.py::test_llm_node_ai_message_uses_prompt_time_mixer_snapshot tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/bench/test_run_fake.py::test_successful_cell_records_ai_message_observability tests/bench/test_run_fake.py::test_parked_cell_records_ai_message_observability tests/state/test_deck_vision.py::test_vision_read_records_ai_message_observability tests/state/test_deck_vision.py::test_vision_error_records_parked_ai_message tests/learn/test_runtime_evidence_grounding.py::test_runtime_logs_learn_milestones_to_session_event_sink tests/learn/test_observer_boot_wiring.py::test_observer_tutor_speak_is_logged_as_ai_message tests/debrief/test_tldr_length_60_to_90s.py::test_generate_tldr_text_raises_on_gemini_exception tests/debrief/test_drill_citations_resolve.py::test_generate_drills_raises_after_retries_exhausted`
  passed: 38 tests.
- `uv run ruff check src/vibemix/runtime/ai_observability.py src/vibemix/agent/dj_cohost.py src/vibemix/bench/run.py src/vibemix/state/deck_vision.py src/vibemix/learn/observability.py src/vibemix/learn/runtime.py src/vibemix/__main__.py src/vibemix/debrief/tldr.py src/vibemix/debrief/drills.py scripts/eval/judge.py scripts/verify_ai_observability.py tests/runtime/test_ai_observability.py tests/agent/test_dj_cohost.py tests/eval/test_judge_pro_rubric.py tests/bench/test_run_fake.py tests/state/test_deck_vision.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_observer_boot_wiring.py tests/debrief/test_tldr_length_60_to_90s.py tests/debrief/test_drill_citations_resolve.py tests/scripts/test_verify_ai_observability.py`
  passed.
- `uv run pytest -q tests/state/test_deck_vision.py tests/state/test_deck_poller.py -k 'vision or DeckVision or screen'`
  passed: 17 tests, 22 deselected. This proves the current observability hunk
  and the existing default-off/no-screen-source gate; it does not prove deck
  vision is a live product source.
- `uv run python scripts/verify_ai_observability.py --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-161228" --require-artifacts --require-deck-mixer --require-engine live_coach --require-surface session --json`
  passed: 1 live-coach row, 1 artifact pair, 1 deck-mixer row, 8 checked artifact
  paths.
- `uv run python scripts/verify_ai_observability.py --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-154932" --require-artifacts --require-move-context --require-deck-mixer --require-engine live_coach --require-surface session --json`
  passed: 20 live-coach rows, 20 artifact pairs, 3 move-bearing rows, 20
  deck-mixer rows, 160 checked artifact paths.
- `uv run python scripts/verify_ai_observability.py --skip-session --require-global --require-artifacts --json`
  passed: 17 global Codex/Viber rows, 1 artifact pair, 35 checked artifact
  paths.
- `uv run pytest -q tests/debrief`
  passed: 111 tests.
- `npm --prefix tauri/ui test -- src/debrief/__tests__/drills-panel-shape.spec.ts src/debrief/__tests__/tldr-player.spec.ts src/debrief/__tests__/error-banner.spec.ts src/debrief/__tests__/stripper-roundtrip.spec.ts src/debrief/__tests__/recording-row-debrief-button.spec.ts src/debrief/__tests__/recording-row-debrief-disabled.spec.ts`
  passed: 35 tests across 6 files.
- 2026-06-01 repo-gate closure: `uv run pytest -q tests/repo/test_no_seen_relaxation.py::test_stop_reason_writes_confined_to_toolset`
  passed: 1 test. The gate now matches Package 1A's cross-engine AI-message
  row shape while still failing any unassigned `stop_reason` source file.

Remaining gate:

- Before release packaging, rerun the session verifier against the final
  rebuilt app/source after staging. The DDJ-FLX4 is now plugged back in, but
  controller-specific move proof has not been refreshed in this package yet, so
  keep the 20260531-154932 move-bearing proof as historical evidence until the
  live verifier is rerun.

## Package 1B - Debrief Test Hygiene

Suggested commit if/when selected: `test(debrief): clean lint hygiene`

Include:

- `tests/debrief/conftest.py`
- `tests/debrief/test_ear_test_capture.py`
- `tests/debrief/test_main_dispatch.py`
- `tests/debrief/test_no_uncited_critique_in_debrief_e2e.py`
- `tests/debrief/test_stripper_integration_with_drills.py`
- `.planning/packets/2026-06-01/CODEX_READY-debrief-test-hygiene.md`

Reason:

- While classifying the debrief path, the product tests were green but
  `uv run ruff check tests/debrief` found old fixable lint in clean test files.
  The changes are mechanical: remove unused imports, sort one import block, and
  drop f-string prefixes that have no placeholders. This keeps the final broad
  lint gate from failing on unrelated debrief test hygiene.

Proof already run:

- `uv run ruff check tests/debrief --fix`
  fixed 9 issues.
- `uv run ruff check tests/debrief`
  passed.
- `uv run pytest -q tests/debrief`
  passed: 111 tests.
- `git diff --check -- tests/debrief/conftest.py tests/debrief/test_ear_test_capture.py tests/debrief/test_main_dispatch.py tests/debrief/test_no_uncited_critique_in_debrief_e2e.py tests/debrief/test_stripper_integration_with_drills.py`
  passed.

Remaining gate:

- Include this package with the final debrief/observability staging batch or as
  its own small test-hygiene commit; do not mix it into product runtime hunks.

## Package 1B4 - Debrief Cached Profile Write-Back

Suggested commit: `fix(debrief): write profile on cached reviews`

Include:

- `src/vibemix/debrief/main.py`
- `tests/debrief/test_main_dispatch.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Free-text drill mining, debrief prompt rewrites, Learn UI changes, live co-host
  speech/timing surfaces, and `src/vibemix/__main__.py`.

Reason:

- First-time debrief generation already feeds structured session events +
  grounded evidence back into the long-term DJ profile. Cache-hit reviews skipped
  that loop, so older generated debriefs stayed a review-only dead end. This
  slice keeps the no-Gemini cache fast path while still updating the profile from
  structured evidence when the DJ reviews a cached debrief.

Proof before staging:

- `uv run pytest -q tests/debrief/test_main_dispatch.py tests/debrief/test_profile_writeback.py`
- `uv run ruff check src/vibemix/debrief/main.py tests/debrief/test_main_dispatch.py tests/debrief/test_profile_writeback.py`
- `git diff --check -- src/vibemix/debrief/main.py tests/debrief/test_main_dispatch.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 1C - Debrief MOSS-Only TLDR Narration

Suggested commit: `fix(debrief): use moss for tldr narration`

Include:

- `src/vibemix/debrief/tldr.py`
- `src/vibemix/debrief/__init__.py`
- `src/vibemix/debrief/ws_server.py`
- `src/vibemix/llm/_router_config.py`
- `src/vibemix/llm/model_router.py`
- `src/vibemix/library/budget.py`
- `tests/debrief/conftest.py`
- `tests/debrief/test_main_dispatch.py`
- `tests/debrief/test_no_uncited_critique_in_debrief_e2e.py`
- `tests/debrief/test_tldr_length_60_to_90s.py`
- `tests/debrief/test_tldr_model_dispatch.py`
- `tests/debrief/test_tldr_mp3_codec.py`
- `tests/e2e/test_phase_41_latency_stack_integration.py`
- `tests/library/test_session_meter.py`
- `tests/llm/test_model_router.py`
- `tests/llm/test_tts_3_1.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live co-host speech / timing surfaces (`src/vibemix/runtime/coach.py`,
  `src/vibemix/state/event_detector.py`, `src/vibemix/state/drop_predict.py`).
- FLX4/deck-capture proof files; this package is source/test-only and does not
  claim Deck B or controller behavior.
- Legacy live-coach TTS compatibility constants and cost-study docs; this slice
  only removes the debrief product's hidden Gemini TTS route.

Reason:

- Product voice policy is MOSS-only. Debrief TLDR text may still use the Gemini
  `debrief` text route, but narration audio must share the local MOSS voice
  provider instead of making a second Gemini TTS call or retaining a
  `debrief_tts` router/cost lane.

Proof already run:

- `uv run pytest -q tests/debrief`
  passed: 109 tests.
- `uv run pytest -q tests/llm/test_model_router.py tests/e2e/test_phase_41_latency_stack_integration.py tests/library/test_session_meter.py`
  passed: 42 tests.
- `uv run pytest -q tests/llm/test_tts_3_1.py tests/agent/test_config.py tests/library/test_cost.py`
  passed: 40 tests, 1 skipped.
- `uv run ruff check src/vibemix/debrief/tldr.py src/vibemix/debrief/__init__.py src/vibemix/debrief/ws_server.py src/vibemix/llm/_router_config.py src/vibemix/library/budget.py tests/debrief/test_tldr_mp3_codec.py tests/debrief/test_tldr_model_dispatch.py tests/debrief/test_main_dispatch.py tests/debrief/test_no_uncited_critique_in_debrief_e2e.py tests/debrief/test_tldr_length_60_to_90s.py tests/debrief/conftest.py tests/llm/test_model_router.py tests/e2e/test_phase_41_latency_stack_integration.py tests/library/test_session_meter.py`
  passed.

Remaining gate:

- Packaged debrief playback still needs the normal rebuilt-DMG smoke after the
  release artifact is cut. This package proves the source route and offline
  MP3 encoding seam only.

## Package 1B2 - Retire Python Ear-Test Writer

Suggested commit: `refactor(debrief): remove duplicate python ear-test writer`

Include:

- `src/vibemix/debrief/ear_test_capture.py`
- `tests/debrief/test_ear_test_capture.py`
- `eval/EAR-TEST-PROTOCOL.md`
- `KAAN-ACTION-LEGAL.md`
- `tauri/ui/src/debrief/components/ear-test-toggle.ts`
- `tauri/ui/debrief.html`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `tauri/src-tauri/src/ear_test_cmds.rs`; the live Rust Tauri writer remains
  unchanged and covered by its existing tests.
- Generated `tauri/ui/dist/**` assets.
- Debrief model, TLDR, drill, or websocket behavior.

Reason:

- The debrief UI's live sign-off path writes through the Rust
  `write_ear_test_log` Tauri command. The Python `write_ear_test_log`
  duplicate had no production caller and made proof readers chase the wrong
  writer.
- The Python module still pins payload/schema validation, while source comments
  now point at the Rust command that actually persists logs.
- Follow-up cleanup updates the remaining protocol/legal docs that still named
  the deleted Python writer; the authoritative live writer is the Rust Tauri
  command.

Proof before staging:

- `rg -n "vibemix.debrief.ear_test_capture|from vibemix.debrief.ear_test_capture" src tests`
  returned no production/test importers.
- `npm --prefix tauri/ui test -- src/debrief/__tests__/ear-test-toggle.spec.ts`
  passed: 2 tests.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml ear_test`
  passed: 3 tests.
- `uv run pytest -q tests/debrief/test_main_dispatch.py tests/debrief/test_no_uncited_critique_in_debrief_e2e.py`
  passed: 7 tests.
- `git diff --check -- src/vibemix/debrief/ear_test_capture.py tests/debrief/test_ear_test_capture.py .planning/handoffs/2026-05-31-package-checklist.md`
  passed.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passed.
- Follow-up proof for the stale-anchor cleanup:
  - `rg -n "src/vibemix/debrief/ear_test_capture.py::write_ear_test_log|vibemix.debrief.ear_test_capture|debrief/ln\\.py" eval KAAN-ACTION-LEGAL.md docs README.md src tests tauri/ui --glob '!tauri/ui/node_modules/**'`
    returns no live/protocol anchors.
  - `git diff --check -- eval/EAR-TEST-PROTOCOL.md KAAN-ACTION-LEGAL.md .planning/handoffs/2026-05-31-package-checklist.md`
    passed.

## Package 1B3 - Retire Transformers Audio Feature Test Oracle

Suggested commit: `test(library): pin audio features without transformers`

Include:

- `tests/library/test_audio_decode.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/library/audio_decode.py`; the runtime decoder is already PyAV/numpy-only.
- `src/vibemix/library/audio_features.py`; this is a test-oracle cleanup, not a DSP rewrite.
- Sidecar specs or dependency files; Transformers is already excluded from frozen builds.

Reason:

- `audio_decode.py` no longer has a Transformers runtime path, but
  `tests/library/test_audio_decode.py` still used
  `pytest.importorskip("transformers.audio_utils")` as its DSP reference. On
  normal local/CI installs that silently skipped the mel/spectrogram regression
  instead of proving it.
- Replace the optional external oracle with deterministic numpy regression
  anchors from the existing local implementation, keeping the no-Transformers
  packaging posture testable without installing a dead dependency.

Proof before staging:

- `uv run pytest -q tests/library/test_audio_decode.py`
- `uv run ruff check tests/library/test_audio_decode.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Hold Lane - Deck Vision Live Source Gate

Suggested commit if/when selected: `feat(state): enable evaluated deck vision source`

Hold: no currently dirty files; tracked as a future gate.

Reason:

- `DeckVisionReader` exists and `DeckPoller` has a structurally wired
  `vision_reader` slot, but it is intentionally dormant: `vision_enabled`
  defaults false, `_latest_screen_jpeg()` always returns `None`, and the poller
  logs a one-shot diagnostic if a developer flips the flag without wiring a real
  screen source.
- Do not claim screen/deck identity is live until the real screenshot buffer,
  per-app eval, and uncertainty surface land together. Vision-sourced keys must
  remain below XML confidence and must never outrank live audio/Rekordbox proof.

Remaining gate:

- Add the real screenshot source, run the documented real-screenshot accuracy
  eval, decide the per-app enable matrix, and then prove the poller can fill a
  missing deck without overwriting XML-resolved decks. Keep `vision_enabled`
  default-off until that proof exists.

## Package 13C - Release Binary Verification Hardening

Suggested commit: `fix(dist): harden release binary verification`

Include:

- `scripts/dist/verify_binary.py`
- `tests/dist/test_verify_binary.py`
- `.planning/packets/2026-06-01/CODEX_READY-release-binary-verification-hardening.md`

Reason:

- This is release/rebuild packaging infrastructure, adjacent to sidecar
  freshness and signing, but it is now grounded by the current rebuilt macOS
  `.app` path and should land as a narrow hardening package.
- The current hunk prevents false positives from generated code-signature
  manifests, native blobs, and embedded `sk-` substrings while preserving strict
  scans for branded key shapes across binaries and source/config payloads.

Proof already run:

- `uv run pytest -q tests/dist/test_verify_binary.py` passed: 25 tests.
- `uv run ruff check scripts/dist/verify_binary.py tests/dist/test_verify_binary.py`
  passed.
- `uv run python -m scripts.dist.verify_binary tauri/src-tauri/target/release/bundle/macos/vibemix.app --report /tmp/vibemix-codex-checks/verify-report-current-macos-app.json`
  passed against the current rebuilt macOS `.app`: `scanned=407`, `hits=0`,
  `status=clean`.
- Existing release wiring already calls this verifier from `.github/workflows/release.yml`
  on macOS and Windows artifacts, and `scripts/dist/sign_macos.sh` runs it in
  Stage 8 after signing.

Remaining gate:

- Rerun this verifier after the final settled source state is rebuilt and
  signed. This package hardens the gate; it does not by itself make a later
  artifact current.

## Package 13D - Clean-Room Attribution Notice

Suggested commit: `docs(legal): attribute clean-room mixxx references`

Include:

- `NOTICE`
- `NOTICE.md`
- `THIRD_PARTY_LICENSES.md`
- `scripts/dist/gen_notice.py`
- `src/vibemix/learn/beatmatch_judge.py`
- `tests/learn/test_beatmatch_judge.py`
- `tests/repo/test_third_party_attribution.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Reason:

- This is the SAFE_NOW legal/proof slice from
  `.planning/packets/2026-06-01/CLAUDE_META_AUDIT_NEXT_BOARD.md`: the product
  had clean-room Mixxx references in source comments but no durable third-party
  attribution map.
- The package is documentation and static-proof only. It does not copy, bundle,
  link, or redistribute Mixxx source, and it does not change runtime behavior.
- The `beatmatch_judge.py` wording now says the behavior was reimplemented from
  clean-room facts instead of "ported verbatim", matching the actual boundary
  the attribution file records.

Proof to run:

- `uv run pytest -q tests/repo/test_third_party_attribution.py`
- `uv run pytest -q tests/repo/test_oss_hygiene.py::test_notice_passes_gen_notice_check tests/repo/test_third_party_attribution.py`
- `uv run ruff check tests/repo/test_third_party_attribution.py`
- `python3 -m scripts.dist.gen_notice --check`
- `git diff --check -- NOTICE NOTICE.md THIRD_PARTY_LICENSES.md scripts/dist/gen_notice.py src/vibemix/learn/beatmatch_judge.py tests/learn/test_beatmatch_judge.py tests/repo/test_third_party_attribution.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 13F - GPL/LGPL Dependency Policy Allowance

Suggested commit: `fix(audit): allow gpl and lgpl dependencies`

Include:

- `tauri/src-tauri/deny.toml`
- `tests/audit/test_deny_toml_policy.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Adding new GPL/LGPL dependencies or vendored source in this policy slice.
- Runtime Mixxx-derived implementation work.
- AGPL allowance; keep AGPL as an explicit release/legal gate.
- Co-host speech, prompt, DROP-call, or live deck behavior.

Reason:

- Product direction now allows GPL/Mixxx-derived work when the value is real.
  The old static audit gate still encoded "GPL family is forbidden", which would
  block useful GPL or LGPL Rust dependencies even when their attribution/source
  obligations are accepted.
- This package updates the gate from "GPL is prohibited" to "GPL/LGPL are
  deliberate and visible; AGPL remains denied by default." It clears the false
  blocker without landing any new copyleft code.

Proof to run:

- `uv run pytest -q tests/audit/test_deny_toml_policy.py`
- `uv run ruff check tests/audit/test_deny_toml_policy.py`
- `git diff --check -- tauri/src-tauri/deny.toml tests/audit/test_deny_toml_policy.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Hold Lane - Rebuild Carry-Forward Serato Cue Carrier

Suggested commit if/when selected: `feat(library): export cues as serato markers`

Hold:

- `pyproject.toml`
- `docs/mixxx.md`
- `src/vibemix/library/export_serato.py`
- `tests/library/test_export_serato.py`

Reason:

- This adds a Serato Markers2 cue carrier plus a `serato` optional dependency
  for `mutagen`. It is a high-value rebuild candidate for universal cue export,
  but it carries a GPL runtime dependency boundary and needs golden-vector /
  real-app proof before broad claims.
- `pyproject.toml` is now a shared path with the Local MOSS hold lane. Stage it
  by hunk if either lane is promoted.

Remaining gate:

- Add real Serato/Mixxx/Rekordbox import proof or a golden Markers2 vector before
  claiming app-level compatibility. Regenerate or validate the lockfile only in
  the selected dependency/export lane.

## Package 5B - Viber Library Request Live Guard

Suggested commit: `fix(library): keep Viber library requests grounded`

Include:

- `src/vibemix/library/codex_curate.py`
- `tests/library/test_codex_curate.py`
- `.planning/packets/2026-06-01/CODEX_READY-viber-library-request-live-guard.md`

Reason:

- This is a concrete Viber/Codex no-slop fix, not a broad curation rewrite.
  When a live-context packet is attached but the DJ asks for crate/library/set
  help, `chat_with_codex` must not replace an unsupported model live outcome
  claim with empty live-move fallback text.
- The source path is shared with Package 1A because `codex_curate.py` also
  carries AI-message observability wrappers. Stage by hunk: Package 5B owns the
  library-request detection/fallback guard and its regression tests; Package 1A
  owns the observability row emission.

Proof already run:

- Codegraph/current-source inspection confirms `chat_with_codex` is the Viber
  chat path, and `python -m vibemix library chat` dispatches through
  `_cmd_library_chat()` into that function.
- `uv run pytest -q tests/library/test_codex_curate.py` passed: 88 tests.
- `uv run pytest -q tests/library/test_codex_curate.py -k 'library_request or non_live_outcome or live_context or chat_with_codex'`
  passed: 37 tests, 51 deselected.
- `uv run pytest -q tests/library/test_live_context_cli.py -k 'chat or verify_live_reply'`
  passed: 8 tests, 32 deselected.
- `uv run pytest -q tests/library/test_codex_curate_stop_reason.py` passed: 16 tests.
- `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  passed.
- `git diff --check -- src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  passed.

Remaining gate:

- Real Viber/Codex CLI or Tauri chat proof with Codex logged in and a live-context
  artifact attached before claiming the packaged app's Viber behavior is fully
  release-proven. Controller hardware is not required for the library-request
  fallback proof, but live deck/controller claims remain out of scope here.

## Package 5C - Viber Library Freshness Status

Suggested commit: `fix(library): surface Viber freshness status`

Include:

- `src/vibemix/library/staleness.py`
- `src/vibemix/__main__.py`
- `tests/library/test_staleness.py`
- `tests/library/test_stats_cli.py`
- `tauri/src-tauri/src/library_cmds.rs`
- `tauri/ui/src/library/api.ts`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/api.test.ts`
- `.planning/packets/2026-06-01/CODEX_READY-viber-library-freshness-status.md`

Reason:

- This is the first landable slice of the Viber freshness P0. It does not claim
  to be a long-running watcher. It gives the product a truthful source-aware
  freshness status for `library.pkl`: missing cache, unreadable cache, missing
  source, source newer than cache, older-than-30-days cache, or fresh.
- The status now travels through `python -m vibemix library stats --json`, the
  Rust Tauri command `library_stats`, and the library UI stats normalizer/header.
  That means Viber/set-prep surfaces can stop treating an old catalog as current
  in later packages instead of rediscovering this state.
- This package is safe without the controller plugged in. It is library/cache
  truth, not deck/live-control truth.

Proof already run:

- `uv run pytest -q tests/library/test_staleness.py tests/library/test_stats_cli.py`
  passed: 29 tests.
- `uv run ruff check src/vibemix/library/staleness.py src/vibemix/__main__.py tests/library/test_staleness.py tests/library/test_stats_cli.py`
  passed.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts src/library/build.test.ts src/library/curate.test.ts`
  passed: 102 tests.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` passed.

Remaining gate:

- The full P0 watcher is still not complete. Add the actual file watcher,
  debounce, incremental ingest/re-embed offer, stale badge affordance, and Viber
  refusal/qualification behavior before claiming set generation is freshness-safe.
- Run a source or packaged app proof that changes a resolved `collection.xml`
  after indexing and shows the stale status in the UI before calling this
  product-visible.

## Package 5D - Viber Stale Set-Prep Tool Guard

Suggested commit: `fix(library): block stale Viber set-prep tools`

Include:

- `src/vibemix/library/toolset.py`
- `src/vibemix/library/mcp_server.py`
- `tests/library/test_setprep_tools.py`
- `.planning/packets/2026-06-01/CODEX_READY-viber-stale-setprep-tool-guard.md`

Reason:

- This is the fail-closed half of the Viber freshness P0. The MCP product path
  now gives `LibraryToolset` a source-aware freshness provider, and the direct
  MCP proxy checks it before local-library tools run.
- When the library index is stale/missing/unreadable/source-missing, local Viber
  set-prep tools return a deterministic `blocked_by: library_freshness` error
  with the freshness payload instead of searching, sequencing, exporting, or
  citing stale catalog facts.
- The guard is tool-side, not prompt-only. It applies before `search_vibe`,
  `discover_pool`, `sequence_set`, `create_playlist`, smart-cue, transition,
  feature, quote, and export surfaces can ground an answer from stale library
  state.

Proof already run:

- `uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_staleness.py tests/library/test_stats_cli.py`
  passed: 57 tests.
- `uv run pytest -q tests/library/test_toolset.py tests/library/test_mcp_server_clarification.py tests/library/test_clap_runtime_errors.py`
  passed: 35 tests.
- `uv run pytest -q tests/library/test_curate_unify.py tests/library/test_codex_curate.py -k 'library_request or non_live_outcome or live_context or chat_with_codex'`
  passed: 37 tests, 58 deselected.
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/mcp_server.py src/vibemix/library/staleness.py tests/library/test_setprep_tools.py tests/library/test_staleness.py tests/library/test_stats_cli.py`
  passed.

Remaining gate:

- Add the actual file watcher and UI freshness badge/action. This guard refuses
  stale tool use once the status says stale; it does not yet watch the source
  and update that status while the app is already running.
- Run a real Viber/Codex MCP turn with a stale test cache before claiming
  packaged-app behavior, because these tests exercise the product MCP proxy and
  wrapper seams but not the whole installed Codex binary loop.

## Package 5E - Library Freshness Watcher Pulse

Suggested commit: `fix(library): watch freshness during live sessions`

Include:

- `src/vibemix/library/watcher.py`
- `src/vibemix/library/staleness.py`
- `src/vibemix/library/rekordbox.py`
- `src/vibemix/__main__.py`
- `src/vibemix/runtime/ws_bus.py`
- `tests/library/test_rekordbox.py`
- `tests/library/test_staleness.py`
- `tests/runtime/test_ws_bus.py`
- `.planning/packets/2026-06-01/CODEX_READY-library-freshness-watcher-pulse.md`
- `.planning/packets/2026-06-01/CODEX_READY-library-staleness-replay-on-connect.md`

Reason:

- The app already had a Settings staleness banner and a live IPC action path,
  but the runtime only emitted the old boot-time 30-day nudge. This package
  adds a source-aware polling pulse that reuses the existing closed
  `ipc.library.staleness_nudge` schema.
- The watcher observes `library_freshness_status()` while the session is live
  and emits a nudge when the freshness signature changes into a stale state.
  It skips fresh installs and respects snooze state.
- Codex maintainability follow-up, 2026-06-01: the live watcher mechanics live
  in `src/vibemix/library/watcher.py`; `staleness.py` keeps the freshness
  policy, snooze state, and backward-compatible import wrappers.
- This is deliberately smaller than a full auto-ingest daemon: it tells the app
  and user that the local library context is stale now, while Package 5D blocks
  stale Viber tools.

Proof already run:

- `uv run pytest -q tests/library/test_staleness.py tests/library/test_stats_cli.py tests/library/test_setprep_tools.py`
  passed: 57 tests.
- `uv run ruff check src/vibemix/library/staleness.py src/vibemix/__main__.py tests/library/test_staleness.py`
  passed.
- `uv run pytest -q tests/test_main_smoke.py` passed: 30 tests.
- `npm --prefix tauri/ui test -- tests/settings/staleness-banner.spec.ts tests/settings/library-panel.spec.ts src/library/api.test.ts`
  passed: 59 tests.
- Codex replay-on-connect follow-up, 2026-06-01: a packaged app run proved the
  sidecar emitted `-> staleness nudge emitted (5d stale)` before the bus was
  available, while the UI subscribed later and `ws_observe` saw zero
  `ipc.library.staleness_nudge` frames. `IpcRouterBus` now retains the latest
  nudge and replays it to late clients; dismiss/snooze clears the retained
  status. Focused proof passed:
  `uv run pytest -q tests/runtime/test_ws_bus.py tests/library/test_staleness.py
  tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py` (128
  tests), `uv run ruff check src/vibemix/runtime/ws_bus.py
  src/vibemix/__main__.py tests/runtime/test_ws_bus.py`, and a current-source
  `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix` run where a late
  `ws_observe(seconds=4, type_filter="ipc.library.staleness_nudge")` captured
  one nudge with `reason=source_newer_than_cache` and
  `source_path=tests/library/fixtures/synthetic_collection.xml`.
- Codex watcher extraction follow-up, 2026-06-01:
  `uv run pytest -q tests/library/test_staleness.py tests/library/test_stats_cli.py
  tests/library/test_setprep_tools.py tests/runtime/test_ws_bus.py` passed with
  76 tests, and `uv run ruff check src/vibemix/library/staleness.py
  src/vibemix/library/watcher.py tests/library/test_staleness.py` passed.
- Codex user-file discovery follow-up, 2026-06-01: a live local probe found the
  current user cache pointing at `tests/library/fixtures/synthetic_collection.xml`.
  The follow-up rejects production-shaped `~/.cache/vibemix/library.pkl` caches
  whose recorded source is a repo test fixture, while keeping pytest's isolated
  fixture caches usable. Focused proof passed:
  `uv run pytest -q tests/library/test_rekordbox.py tests/library/test_staleness.py
  tests/library/test_stats_cli.py tests/library/test_setprep_tools.py
  tests/runtime/test_ws_bus.py::test_ws_broadcast_replays_staleness_nudge_to_late_client`.

Remaining gate:

- Rebuild/re-sign before claiming packaged behavior; the existing signed DMG
  predates the replay fix.
- Finish the Package 5F acceptance loop: click/trigger refresh from the stale
  banner, verify importer progress, and show Viber set-prep unblocks only after
  freshness returns current.

## Package 5F - Stale Library Refresh Action

Suggested commit: `fix(settings): refresh stale library source`

Include:

- `src/vibemix/library/staleness.py`
- `src/vibemix/__main__.py`
- `src/vibemix/runtime/ws_bus.py`
- `src/vibemix/ui_bus/schemas/library.py`
- `src/vibemix/ui_bus/messages.py`
- `tests/runtime/test_ws_bus.py`
- `tests/library/test_staleness.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/settings/components/staleness-banner.ts`
- `tauri/ui/src/settings/components/library-panel.ts`
- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/tests/settings/staleness-banner.spec.ts`
- `tauri/ui/tests/settings/library-panel.spec.ts`
- `.planning/packets/2026-06-01/CODEX_READY-stale-library-refresh-action.md`
- `.planning/packets/2026-06-01/CODEX_READY-library-staleness-replay-on-connect.md`

Reason:

- This closes the next user-facing gap in the Viber freshness P0. Package 5E
  could tell the app that the source-backed library cache was stale, but it left
  the user at "go re-import somehow." This package threads a refreshable
  Rekordbox XML `source_path` through the existing nudge and adds a restrained
  `Refresh library` action.
- The action reuses the existing `ipc.library.import` path and, when the full
  library panel is mounted, delegates to the panel handle so progress/error
  state stays in one place. It does not add a competing backend command.
- When the stale source is not refreshable from the current machine, the banner
  stays honest: no action button, and the copy asks the user to drop the
  Rekordbox XML below.
- The IPC widening is additive only: `ipc.library.staleness_nudge` gained
  optional `source_path` and `reason`, and generated validator/TS files were
  regenerated.

Proof already run:

- `uv run pytest -q tests/library/test_staleness.py tests/library/test_stats_cli.py tests/library/test_setprep_tools.py tests/ui_bus/test_messages_schema.py tests/ipc/test_library_schemas.py`
  passed: 148 tests.
- `npm --prefix tauri/ui test -- tests/settings/staleness-banner.spec.ts tests/settings/library-panel.spec.ts tests/settings/drawer.spec.ts src/library/api.test.ts`
  passed: 87 tests.
- `uv run ruff check src/vibemix/library/staleness.py src/vibemix/__main__.py src/vibemix/ui_bus/schemas/library.py src/vibemix/ui_bus/messages.py tests/library/test_staleness.py`
  passed.
- `npm --prefix tauri/ui run check:ipc` passed.
- `uv run python scripts/check_ipc_schema.py` passed: 72 dataclasses / 72
  schema wrappers.
- `uv run pytest -q tests/test_main_smoke.py tests/ui_bus/test_messages_schema.py tests/ipc/test_library_schemas.py`
  passed: 121 tests.
- Codex replay-on-connect follow-up, 2026-06-01: a current-source late websocket
  client now receives the boot-time stale-library nudge. Focused proof passed:
  `uv run pytest -q tests/runtime/test_ws_bus.py tests/library/test_staleness.py
  tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py` (128
  tests), `uv run ruff check src/vibemix/runtime/ws_bus.py
  src/vibemix/__main__.py tests/runtime/test_ws_bus.py`, and live
  `ws_observe(seconds=4, type_filter="ipc.library.staleness_nudge")` captured
  `reason=source_newer_than_cache` with refreshable fixture XML.

Remaining gate:

- Packaged proof is still required before release claim because the existing
  signed DMG predates the replay fix.
- Trigger the refresh action from the stale banner, verify importer progress,
  and show Viber set-prep unblocks only after freshness returns current.

## Package 5J - Folder Stale Re-index Action

Suggested commit: `fix(settings): reindex stale folder libraries`

Include:

- `src/vibemix/library/staleness.py`
- `src/vibemix/library/watcher.py`
- `src/vibemix/ui_bus/schemas/library.py`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/__main__.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/settings/components/staleness-banner.ts`
- `tauri/ui/src/settings/components/library-panel.ts`
- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/tests/settings/staleness-banner.spec.ts`
- `tauri/ui/tests/settings/library-panel.spec.ts`
- `tests/runtime_closeouts/test_register_library_invoked.py`
- `tests/library/test_staleness.py`
- `tests/ipc/test_library_schemas.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Reason:

- Package 5F made stale Rekordbox XML sources refreshable, but folder-backed
  libraries still showed the nudge without a working remediation. This closes
  H8 from `CLAUDE_LAND_QUEUE.md`: when the recorded source is a folder, the
  nudge carries `source_kind="folder"`, the Settings banner says "Re-index
  folder", and the backend runs `ingest_folder` from the recorded freshness
  source instead of trusting a renderer-supplied path.
- The action reuses `ipc.library.staleness_action` with a new
  `reindex_folder` action and reuses `ipc.library.import_progress` for visible
  progress. XML refresh keeps the existing `ipc.library.import` path.
- Consent stays intact: folders are not auto-detected on fresh install. A
  folder re-index appears only for a folder source already stored in the
  user's library cache.
- The Settings drop target may also accept an explicitly dropped music folder;
  the backend routes directory imports to `ingest_folder` before the Rekordbox
  XML parser so first-time no-Rekordbox setup is not a dead end.

Proof to run:

- `uv run pytest -q tests/library/test_staleness.py tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py tests/runtime/test_ws_bus.py::test_ws_broadcast_replays_staleness_nudge_to_late_client`
- `npm --prefix tauri/ui test -- tests/settings/staleness-banner.spec.ts tests/settings/library-panel.spec.ts tests/settings/drawer.spec.ts`
- `npm --prefix tauri/ui run check:ipc`
- `uv run python scripts/check_ipc_schema.py`
- `uv run ruff check src/vibemix/library/staleness.py src/vibemix/library/watcher.py src/vibemix/ui_bus/schemas/library.py src/vibemix/ui_bus/messages.py src/vibemix/__main__.py tests/library/test_staleness.py tests/ipc/test_library_schemas.py`
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`

Remaining gate:

- Source-level only until a live Settings click proves a folder stale nudge
  starts folder re-index progress in the Tauri app.

## Package 5R - Library Native Source Picker

Suggested commit: `feat(settings): pick library sources natively`

Include:

- `tauri/ui/src/settings/components/library-panel.ts`
- `tauri/ui/tests/settings/library-panel.spec.ts`
- `tauri/ui/package.json`
- `tauri/ui/package-lock.json`
- `tauri/src-tauri/src/main.rs`
- `tauri/src-tauri/Cargo.toml`
- `tauri/src-tauri/Cargo.lock`
- `tauri/src-tauri/capabilities/default.json`
- `tauri/src-tauri/capabilities-snapshot/SNAPSHOT.json`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/__main__.py`, `src/vibemix/runtime/coach.py`, and any co-host
  speech / DROP-call timing hunks.
- Library backend importer semantics; this package only lets the user choose a
  source path and reuses the existing `ipc.library.import` path.

Reason:

- The Settings library panel had a visible `Choose file` button that did not
  open a picker; it only told the user to drag files. That made first-run
  library setup look interactive while the click path was fake.
- This package adds the official Tauri dialog plugin, grants only
  `dialog:allow-open`, registers the plugin in the shell, and wires native
  `Choose file` / `Choose folder` actions into the existing import progress
  flow.
- It also accepts Traktor `.nml` drops now that the backend can route Traktor
  imports. Single audio-file drops stay rejected so a stray track is not
  silently treated as a library.

Proof to run:

- `npm --prefix tauri/ui test -- tests/settings/library-panel.spec.ts`
- `npm --prefix tauri/ui run build`
- `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check`
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml`
- `uv run pytest -q tests/security/test_capability_snapshot.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/settings/components/library-panel.ts tauri/ui/tests/settings/library-panel.spec.ts tauri/ui/package.json tauri/ui/package-lock.json tauri/src-tauri/src/main.rs tauri/src-tauri/Cargo.toml tauri/src-tauri/Cargo.lock tauri/src-tauri/capabilities/default.json tauri/src-tauri/capabilities-snapshot/SNAPSHOT.json .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- Live Tauri click proof should be captured before release notes claim the
  packaged picker works on a clean install.

## Package 5K - Viber Library Setup Operator Action

Suggested commit: `fix(viber): surface missing library setup action`

Include:

- `src/vibemix/__main__.py`
- `tests/library/test_live_context_cli.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Automatic recursive user-folder scanning.
- Live Rekordbox `master.db` reads; SQLCipher stays diagnostic-only/off.
- Settings UI redesign; the existing Settings drop target is reused.

Reason:

- A current FLX4/Rekordbox source proof heard live music and saw the controller,
  but `library_cache` was missing, so Viber/Sven could not resolve deck identity.
  The existing operator action list named deck identity generically but did not
  tell the user how to fix the missing library substrate.
- The new `index_library` action is content-light and consent-preserving: it
  names the already-supported setup surfaces (Settings drop target,
  `library ingest`, and `library embed-folder`) and explicitly says that
  Vibemix does not read the live SQLCipher `master.db`.

Proof to run:

- `uv run pytest -q tests/library/test_live_context_cli.py`
- `uv run ruff check src/vibemix/__main__.py tests/library/test_live_context_cli.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/__main__.py tests/library/test_live_context_cli.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- Source-level action only. A live proof still needs a real indexed user library
  cache plus controller movement and, for per-deck claims, deck-pair audio
  capture configuration.

## Package 5L - Viber Library Setup Discovery Candidates

Suggested commit: `feat(viber): discover local library setup candidates`

Include:

- `src/vibemix/library/setup_discovery.py`
- `src/vibemix/__main__.py`
- `tests/library/test_setup_discovery.py`
- `tests/library/test_live_context_cli.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Automatic ingest/re-embed.
- Recursive whole-disk scanning or hidden-folder traversal.
- Live Rekordbox `master.db` reads.
- Any co-host speech or prompt changes.

Reason:

- Package 5K made missing library state machine-readable, but its guidance was
  still generic. A fresh install needs Viber to help the DJ choose a concrete
  setup source without guessing or mutating files.
- This slice adds a bounded, content-light discovery pass: standard Rekordbox
  `collection.xml` export locations plus shallow music-folder candidates under
  common user-owned roots. The live-context proof includes these candidates in
  the `index_library` operator action so Viber can guide setup while preserving
  consent.

Proof to run:

- `uv run pytest -q tests/library/test_setup_discovery.py tests/library/test_live_context_cli.py`
- `uv run ruff check src/vibemix/library/setup_discovery.py src/vibemix/__main__.py tests/library/test_setup_discovery.py tests/library/test_live_context_cli.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/library/setup_discovery.py src/vibemix/__main__.py tests/library/test_setup_discovery.py tests/library/test_live_context_cli.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- Source/live-context proof only. A future product slice can add an explicit
  one-click "Use this folder/XML" action, but this package only discovers and
  reports candidates.

## Package 5M - Library Doctor Setup Candidates

Suggested commit: `feat(library): show setup candidates in doctor`

Include:

- `src/vibemix/library/doctor.py`
- `tests/library/test_doctor.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- CLI ingest execution.
- Settings UI changes.
- Viber/cohost speech or live-context claim changes.

Reason:

- Package 5L exposes setup candidates in live-context JSON, but users and app
  preflight surfaces still need a stable cheap command that says what to import
  before Viber can search/set-prep.
- `library doctor` now includes a `library_setup` check. It reports "already
  indexed" when the cache loads, otherwise it surfaces bounded local candidates
  from `setup_discovery` without indexing them.

Proof to run:

- `uv run pytest -q tests/library/test_doctor.py tests/library/test_setup_discovery.py`
- `uv run ruff check src/vibemix/library/doctor.py tests/library/test_doctor.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/library/doctor.py tests/library/test_doctor.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- Source-level setup visibility only. A future explicit action may start an
  ingest/re-embed run, but this package remains read-only.

## Package 5M2 - Rekordbox Source Cache Boundary Regression

Suggested commit: `test(library): pin rekordbox source cache boundary`

Include:

- `tests/library/test_sources_rekordbox.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/library/rekordbox.py`; the fixture-poison quarantine code is
  already implemented.
- `src/vibemix/library/sources/rekordbox.py`; this package adds coverage only.
- Ingest CLI, setup discovery, Settings UI, or Viber/cohost behavior.

Reason:

- The primary cache quarantine is already covered at
  `RekordboxLibrary.try_load_cache`, and `RekordboxSource.iter_tracks` already
  recovers from a repo-fixture-poisoned user cache.
- The remaining edge is a real user library whose relative path contains
  `tests/fixtures`. That must remain accepted through `RekordboxSource` too,
  because DJs can name folders anything. The test pins that source iteration
  uses the accepted warm cache instead of quarantining it as repo test data.

Proof to run:

- `uv run pytest -q tests/library/test_sources_rekordbox.py tests/library/test_rekordbox.py`
- `uv run ruff check tests/library/test_sources_rekordbox.py tests/library/test_rekordbox.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tests/library/test_sources_rekordbox.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 5N - Traktor NML Library Source

Suggested commit: `feat(library): add traktor nml source`

Include:

- `src/vibemix/library/sources/traktor.py`
- `src/vibemix/library/sources/__init__.py`
- `tests/library/test_sources_traktor.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/__main__.py` CLI/source-selection hooks.
- Live co-host speech, prompts, event timing, or deck-identity changes.
- Native Traktor runtime/database dependencies; this slice is exported
  `collection.nml` XML only.

Reason:

- Universal Library Ingest needs more than Rekordbox so Viber can help DJs
  whose crates live elsewhere. A Traktor `.nml` reader is a clean source-island
  proof: stdlib XML in, existing `TrackEntry` rows out, no audio/model/runtime
  side effects.
- The first slice intentionally proves the source seam before touching the
  shared `__main__.py` orchestration file, which is active in other lanes.

Proof to run:

- `uv run pytest -q tests/library/test_sources_traktor.py tests/library/test_sources_rekordbox.py`
- `uv run ruff check src/vibemix/library/sources/traktor.py src/vibemix/library/sources/__init__.py tests/library/test_sources_traktor.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/library/sources/traktor.py src/vibemix/library/sources/__init__.py tests/library/test_sources_traktor.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- CLI/UI selection and automatic setup discovery for Traktor are separate
  follow-up packages. This package proves parser correctness and the shared
  LibrarySource contract only.

## Package 5O - Traktor Ingest CLI and Setup Discovery

Suggested commit: `feat(library): wire traktor ingest setup path`

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/library/setup_discovery.py`
- `tests/library/test_setup_discovery.py`
- `tests/library/test_ingest_cli_anlz.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live co-host speech, prompts, EventDetector timing, or DROP-call paths.
- Automatic ingest/re-embed from discovery candidates.
- Settings UI redesign; the existing Library setup surfaces consume candidates.
- Serato/Engine/Rekordbox `master.db` readers.

Reason:

- Package 5N made Traktor `.nml` parseable, but discovery must not surface a
  fake command. This slice makes `library ingest --source traktor <collection.nml>`
  real, then lets Viber/library doctor recommend that exact command when a
  standard Traktor export exists.
- Rekordbox ANLZ enrichment remains Rekordbox-only and is skipped explicitly for
  Traktor so the command is honest about what metadata it can add.

Proof to run:

- `uv run pytest -q tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py tests/library/test_sources_traktor.py`
- `uv run ruff check src/vibemix/__main__.py src/vibemix/library/setup_discovery.py tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/__main__.py src/vibemix/library/setup_discovery.py tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- GUI one-click source selection remains a follow-up. This package gives the
  CLI and Viber setup candidate a truthful, runnable Traktor import path.

## Package 5P - VirtualDJ Database XML Library Source

Suggested commit: `feat(library): add virtualdj database source`

Include:

- `src/vibemix/library/sources/virtualdj.py`
- `src/vibemix/library/sources/__init__.py`
- `src/vibemix/library/sources/base.py`
- `tests/library/test_sources_virtualdj.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/__main__.py` CLI/source-selection hooks.
- Live co-host speech, prompts, event timing, or deck-identity changes.
- VirtualDJ write-back or direct modification of the user's `database.xml`.

Reason:

- Universal Library Ingest should not stop at Rekordbox and Traktor. VirtualDJ
  uses a read-only XML `database.xml`, so this source is another clean
  stdlib-only parser island that feeds existing `TrackEntry`, cue, and beatgrid
  rows without touching audio/model/runtime code.
- VirtualDJ's scanned BPM value is seconds per beat, not displayed BPM. This
  package pins that conversion in tests so future parsers do not silently
  corrupt tempo-dependent search, suggestions, or Earned signals.

Proof to run:

- `uv run pytest -q tests/library/test_sources_virtualdj.py tests/library/test_sources_traktor.py tests/library/test_sources_rekordbox.py`
- `uv run ruff check src/vibemix/library/sources/virtualdj.py src/vibemix/library/sources/__init__.py src/vibemix/library/sources/base.py tests/library/test_sources_virtualdj.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/library/sources/virtualdj.py src/vibemix/library/sources/__init__.py src/vibemix/library/sources/base.py tests/library/test_sources_virtualdj.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- CLI/setup discovery for VirtualDJ is a separate follow-up package. This
  package proves parser correctness and the shared LibrarySource contract only.

## Package 5Q - VirtualDJ Ingest CLI and Setup Discovery

Suggested commit: `feat(library): wire virtualdj ingest setup path`

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/library/setup_discovery.py`
- `tests/library/test_setup_discovery.py`
- `tests/library/test_ingest_cli_anlz.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live co-host speech, prompts, EventDetector timing, or DROP-call paths.
- Automatic ingest/re-embed from discovery candidates.
- Settings UI redesign; the existing Library setup surfaces consume candidates.
- Serato/Engine/Rekordbox `master.db` readers.

Reason:

- Package 5P made VirtualDJ `database.xml` parseable, but discovery must not
  surface a fake command. This slice makes
  `library ingest --source virtualdj <database.xml>` real, then lets Viber and
  `library doctor` recommend that exact command when a standard VirtualDJ
  database exists.
- Rekordbox ANLZ enrichment remains Rekordbox-only and is skipped explicitly
  for VirtualDJ so the command is honest about what metadata it can add.

Proof to run:

- `uv run pytest -q tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py tests/library/test_sources_virtualdj.py`
- `uv run ruff check src/vibemix/__main__.py src/vibemix/library/setup_discovery.py tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/__main__.py src/vibemix/library/setup_discovery.py tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- GUI one-click source selection remains a follow-up. This package gives the
  CLI and Viber setup candidate a truthful, runnable VirtualDJ import path.

## Package 5S - Engine DJ m.db Library Source

Suggested commit: `feat(library): add engine dj database source`

Include:

- `src/vibemix/library/sources/engine.py`
- `src/vibemix/library/sources/__init__.py`
- `tests/library/test_sources_engine.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/__main__.py` CLI/source-selection hooks.
- `src/vibemix/library/setup_discovery.py` setup-candidate wiring.
- Live co-host speech, prompts, event timing, or deck-identity changes.
- Engine DJ write-back or opaque `PerformanceData` blob decoding.

Reason:

- Universal Library Ingest should cover Engine DJ / Denon Prime users without
  making the live app guess from stale or missing Rekordbox XML. Engine DJ
  exposes a plain SQLite `m.db`, so the first honest slice is a stdlib-only,
  read-only source parser that feeds existing `TrackEntry`, cue, and beatgrid
  rows when those rows are relationally available.
- This deliberately mirrors Package 5N/5P: prove the source seam first, then
  wire CLI/setup discovery in a separate package so the shared `__main__.py`
  file is not swept into a parser commit.

Proof to run:

- `uv run pytest -q tests/library/test_sources_engine.py tests/library/test_sources_traktor.py tests/library/test_sources_virtualdj.py tests/library/test_sources_rekordbox.py`
- `uv run ruff check src/vibemix/library/sources/engine.py src/vibemix/library/sources/__init__.py tests/library/test_sources_engine.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/library/sources/engine.py src/vibemix/library/sources/__init__.py tests/library/test_sources_engine.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- CLI/setup discovery for Engine DJ is a separate follow-up package. This
  package proves parser correctness and the shared `LibrarySource` contract
  only. A real Engine library capture remains the LIVE proof before claiming
  full Engine DJ import parity.

## Package 5T - Engine DJ Ingest CLI and Setup Discovery

Suggested commit: `feat(library): wire engine dj ingest setup path`

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/library/setup_discovery.py`
- `tests/library/test_setup_discovery.py`
- `tests/library/test_ingest_cli_anlz.py`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/chat.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live co-host speech, prompts, EventDetector timing, or DROP-call paths.
- Automatic ingest/re-embed from discovery candidates.
- Engine DJ write-back or opaque `PerformanceData` blob decoding.
- Full Settings UI redesign; this slice uses the existing setup candidate card.

Reason:

- Package 5S made Engine DJ `m.db` parseable, but discovery must not surface a
  dead or unlabeled action. This slice makes
  `library ingest --source engine <m.db>` real, lets setup discovery recommend
  that command when a standard Engine DJ `Database2/m.db` exists, and lets the
  Library/Viber setup card label it as an Engine DJ database.
- Rekordbox ANLZ enrichment remains Rekordbox-only and is skipped explicitly
  for Engine DJ so the command is honest about what metadata it can add.

Proof to run:

- `uv run pytest -q tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py tests/library/test_sources_engine.py`
- `uv run ruff check src/vibemix/__main__.py src/vibemix/library/setup_discovery.py tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py`
- `npm --prefix tauri/ui test -- src/library/chat.test.ts`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/__main__.py src/vibemix/library/setup_discovery.py tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py tauri/ui/src/library/index.ts tauri/ui/src/library/chat.test.ts .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- A real Engine DJ library capture remains the LIVE proof before claiming full
  Engine import parity. This package proves the existing app/CLI setup path can
  reach the source without changing live/cohost behavior.

## Package 5U - Serato Database Library Source and Setup Path

Suggested commit: `feat(library): add serato database source`

Include:

- `src/vibemix/library/sources/serato.py`
- `src/vibemix/library/sources/__init__.py`
- `src/vibemix/__main__.py`
- `src/vibemix/library/setup_discovery.py`
- `tests/library/test_sources_serato.py`
- `tests/library/test_setup_discovery.py`
- `tests/library/test_ingest_cli_anlz.py`
- `tauri/ui/src/library/index.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Serato write-back, crate mutation, or audio-file tag writes.
- Live co-host speech, prompts, EventDetector timing, or DROP-call paths.
- Automatic ingest/re-embed from discovery candidates.
- Any new dependency; Markers2 cues use the existing Serato tag reader.

Reason:

- Universal Library Ingest should cover the last major DJ-library island.
  Serato exposes a documented `_Serato_/database V2` plus `.crate` chunk
  format, while vibemix already owns the Markers2 cue decoder. This package
  parses the read-only database/crate metadata into `TrackEntry`, routes
  `library ingest --source serato`, and lets first-run setup discovery surface a
  labeled Serato database candidate.

Proof to run:

- `uv run pytest -q tests/library/test_sources_serato.py tests/library/test_sources_traktor.py tests/library/test_sources_virtualdj.py tests/library/test_sources_engine.py tests/library/test_ingest_cli_anlz.py tests/library/test_setup_discovery.py`
- `uv run ruff check src/vibemix/library/sources/serato.py src/vibemix/library/sources/__init__.py src/vibemix/library/setup_discovery.py src/vibemix/__main__.py tests/library/test_sources_serato.py tests/library/test_ingest_cli_anlz.py tests/library/test_setup_discovery.py`
- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/library/sources/serato.py src/vibemix/library/sources/__init__.py src/vibemix/__main__.py src/vibemix/library/setup_discovery.py tests/library/test_sources_serato.py tests/library/test_setup_discovery.py tests/library/test_ingest_cli_anlz.py tauri/ui/src/library/index.ts .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- A real Serato library capture remains the LIVE proof before claiming full
  Serato import parity. This package proves the source/CLI/setup path, and it
  reads cues only where existing Markers2 tags are available.

## Package 5G - Shell Library Freshness Badge

Suggested commit: `feat(tauri-ui): show library freshness in shell`

Include:

- `tauri/ui/src/shell/LibraryFreshnessBadge.ts`
- `tauri/ui/src/shell/app.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/library-freshness-badge.spec.ts`
- `.planning/packets/2026-06-01/CODEX_READY-library-freshness-badge.md`

Reason:

- Packages 5C through 5F made library freshness source-aware, actionable, and
  replayed to late UI clients. This package makes the same truth glanceable in
  the main shell footer so the DJ does not need to open Settings or Crate to
  know whether Viber/set-prep is reading fresh library context.
- The badge is display-only. It consumes `libraryStats()` and renders
  `library fresh`, `library stale`, `library not indexed`, or `library unknown`
  with an honest state dot. It does not add a backend command, watcher, or
  automatic ingest loop.
- Backend failures degrade to `library unknown`, not a fake green state.

Proof already run:

- `npm --prefix tauri/ui test -- tests/shell/library-freshness-badge.spec.ts tests/shell/shell.spec.ts`
  passed: 15 tests.
- `npm --prefix tauri/ui test -- tests/shell/library-freshness-badge.spec.ts src/library/api.test.ts`
  passed: 47 tests.
- `npm --prefix tauri/ui run build` passed.
- `git diff --check -- tauri/ui/src/shell/LibraryFreshnessBadge.ts tauri/ui/src/shell/app.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/library-freshness-badge.spec.ts`
  passed.

Remaining gate:

- Eye-check the badge inside a live or packaged shell before screenshot or
  release copy claims. This package proves the UI contract and build, not final
  visual acceptance on the signed artifact.

## Package 5G.1 - Library UI Fixture Skeleton Sync

Suggested commit: `test(library-ui): sync Viber fixture skeletons`

Include:

- `tauri/ui/src/library/chat.test.ts`
- `tauri/ui/src/library/curate.test.ts`

Keep out:

- `tauri/ui/src/library/index.ts`
- `tauri/ui/library.html`
- Backend/Rust/Python library commands.

Reason:

- Claude's capability inventory flagged stale jsdom fixtures, not a live app
  gap. The real library markup and `build.test.ts` already contain the cue mode,
  cue folder, curve segment classes, and cue export controls that
  `mountLibrary()` queries.
- This package only keeps the chat and curate test skeletons aligned with the
  current window contract so fixture drift does not masquerade as a Viber
  backend failure.

Proof already run:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/curate.test.ts`
  passed: 40 tests.
- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/curate.test.ts src/library/build.test.ts`
  passed: 60 tests.
- `git diff --check -- tauri/ui/src/library/chat.test.ts tauri/ui/src/library/curate.test.ts`
  passed.

Remaining gate:

- None. This is a test-fixture sync only and does not change product behavior.

## Package 5G.2 - Shell Command Palette Honest Live State

Suggested commit: `fix(tauri-ui): remove fake live palette actions`

Include:

- `tauri/ui/src/shell/DesktopShell.ts`
- `tauri/ui/tests/shell/command-palette.spec.ts`

Keep out:

- Runtime activation bridges, websocket/session state, and backend live-status
  plumbing.
- Any co-host speech, prompt, DROP-call, TTS, or deck-audio capture changes.

Reason:

- The meta-audit found two shipped command-palette actions, `sim.live` and
  `sim.idle`, that directly mutated shell activation and connection state. A
  user could open Cmd+K, run "Go live", and make the shell paint live/connected
  without a runtime session, audio evidence, or websocket state. That violates
  the product honesty rule: visible live status must come from the runtime, not
  a simulation control in the shipped palette.
- The real shell activation path already exists outside the palette. This slice
  removes only the fake controls and adds a regression test so simulation
  actions do not return as product commands.

Proof for this UI honesty slice:

- `npm --prefix tauri/ui test -- tests/shell/command-palette.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/shell/DesktopShell.ts tauri/ui/tests/shell/command-palette.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- None for source behavior. A packaged screenshot/live shell pass can still
  confirm the palette visually, but this package removes an explicitly fake
  shipped action and does not claim runtime live proof.

## Package 5G.3 - Shell Status Footer Honest Live State

Suggested commit: `fix(tauri-ui): make shell status read-only`

Include:

- `tauri/ui/src/shell/StatusFooter.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime activation bridges, websocket/session state, and backend live-status
  plumbing.
- Any co-host speech, prompt, DROP-call, TTS, or deck-audio capture changes.

Reason:

- Package 5G.2 removed the fake command-palette live controls, but the footer
  still carried the same demo-only state mutation through a click handler. A
  user could click the quiet status readout and make the shell paint
  listening/live plus connected without any runtime session, audio evidence, or
  websocket state.
- This package makes the footer a read-only status group. Activation remains
  owned by the live activation bridge, not by UI simulation.

Proof for this UI honesty slice:

- `npm --prefix tauri/ui test -- tests/shell/shell.spec.ts tests/shell/command-palette.spec.ts tests/shell/activation-bridge.spec.ts tests/shell/library-freshness-badge.spec.ts`
  passed: 25 tests.
- `git diff --check -- tauri/ui/src/shell/StatusFooter.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
  passed.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- None for source behavior. This removes a simulation control; it does not claim
  a live-runtime activation proof.

## Package 5G.4 - Shell Grounding Panel Honest Empty State

Suggested commit: `fix(tauri-ui): stop faking shell grounding receipts`

Include:

- `tauri/ui/src/shell/GroundingPanel.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/grounding-panel.spec.ts`
- `tauri/ui/tests/shell/shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime citation IPC, websocket/session state, and backend suggestion plumbing.
- Any co-host speech, prompt, DROP-call, TTS, deck-audio capture, or pill surface
  changes.

Reason:

- The shell panel opened on a real live activation, but it rendered a lit
  "Cited" slot and "Listening for the next move" even though the panel has no
  citation or next-suggestion feed. That made a real activation look like a
  fake receipt.
- This package keeps the panel as an honest empty state: live activation can
  open it, but it says no cited move or suggestion exists yet until a real data
  writer is added.

Proof for this UI honesty slice:

- `npm --prefix tauri/ui test -- tests/shell/grounding-panel.spec.ts tests/shell/shell.spec.ts tests/shell/activation-bridge.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/shell/GroundingPanel.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/grounding-panel.spec.ts tauri/ui/tests/shell/shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- Wiring this panel to actual citation/suggestion data is a separate product
  package and should go through grounding review. This package only removes the
  fake receipt claim.

## Package 5H - Viber Raw Cue Export Boundary

Suggested commit: `fix(library): drop raw cue export from Viber tools`

Include:

- `src/vibemix/library/toolset.py`
- `src/vibemix/library/mcp_server.py`
- `tests/library/test_toolset.py`
- `tests/library/test_mcp_server_clarification.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/library/cue_export.py` and the cue-folder/GUI exporters. The
  pure cue exporter remains available to trusted CLI/Rust/GUI code.
- Any new cue-writing UX claim. This slice only removes an unsafe agent-facing
  tool surface.

Reason:

- The recovered Viber capability packet and `viber-capability-CORRECTION.md`
  both kept one live grounding hole: the MCP/toolset `export_cues` wrapper
  accepted raw cue payloads plus arbitrary `track_path` and did not prove the
  track or cues came from this run's grounded seen/proposal set.
- `export_smart_cues` already provides the safe cue-write path: the proposal
  must have been issued by `smart_hot_cues` in the same run, the track is
  revalidated against the live library and seen set, and selected cue ids must
  be part of that proposal.
- Removing the raw agent tool is more honest than trying to infer grounding
  from a filesystem path. It makes Viber/Codex cue writes proposal-id based
  only.

Proof for this source slice:

- `uv run pytest -q tests/library/test_toolset.py tests/library/test_mcp_server_clarification.py`
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/mcp_server.py tests/library/test_toolset.py tests/library/test_mcp_server_clarification.py`
- `git diff --check -- src/vibemix/library/toolset.py src/vibemix/library/mcp_server.py tests/library/test_toolset.py tests/library/test_mcp_server_clarification.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- None for the agent-facing boundary. Any future single-track cue write tool
  must be proposal-id or track-id grounded before it is exposed to Viber/Codex.

## Package 8J - Heartbeat Golden Test Refresh

Suggested commit: `test(coach): refresh heartbeat grounding golden`

Include:

- `tests/state/test_coach.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/state/coach.py` and any cohost speech/prompt source changes.
- `src/vibemix/runtime/coach.py`, DROP-call files, TTS, and live runtime files.

Reason:

- The HEARTBEAT task source was already hardened to forbid coaching advice
  without recent move evidence and to require exact grounding refs for citations.
  The test still asserted the older shorter golden string.
- `tests/learn/test_progress_snapshot_skill_wall.py::test_mastered_demo_reaches_the_envelope_wall`
  is already refreshed at current HEAD and passes, so this package only updates
  the remaining stale S4 golden.

Proof before staging:

- `uv run pytest -q tests/state/test_coach.py::test_task_heartbeat_LOAD_BEARING_anti_silence_clause`
- `uv run pytest -q tests/learn/test_progress_snapshot_skill_wall.py::test_mastered_demo_reaches_the_envelope_wall`
- `uv run ruff check tests/state/test_coach.py`
- `git diff --check -- tests/state/test_coach.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 5I - Folder Cache Source Docstring

Suggested commit: `docs(library): clarify folder cache source path`

Include:

- `src/vibemix/library/folder_ingest.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/library/rekordbox.py`, which is active in the fixture-reject
  lane.
- Folder re-index UI, IPC/schema, `__main__.py`, or freshness watcher behavior.

Reason:

- `folder_ingest._write_library_cache` writes a resolved folder path to
  `_CacheBlob.xml_path`, not a `folder:<root>` marker. The marker belongs in
  folder-backed `track_id` values.
- Keeping the comment honest prevents a future "fix" from breaking
  `try_load_cache` source-folder staleness detection, which depends on being
  able to stat the folder path.

Proof before staging:

- `uv run pytest -q tests/library/test_folder_ingest.py`
- `uv run ruff check src/vibemix/library/folder_ingest.py`
- `git diff --check -- src/vibemix/library/folder_ingest.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Hold Lane - Rebuild Carry-Forward Cue Agreement Flywheel

Suggested commit if/when selected: `feat(library): record cue agreement weak labels`

Hold:

- `src/vibemix/library/cue_agreement.py`
- `tests/library/test_cue_agreement.py`

Reason:

- This is a deterministic producer for auto-cue versus DJ-cue agreement, useful
  for the rebuild's feedback/flywheel story. It is not a model and not yet an
  ingest/runtime integration.
- Keep it separate from cue export and smart-cue runtime work until the privacy,
  storage, and ingest call-site decisions are accepted.

Remaining gate:

- Run focused cue-agreement tests, then decide where weak-label JSONL or
  telemetry belongs. Do not claim a learning flywheel until an accepted producer
  and consumer both exist.

## Package 8B - Judge Voice Evidence Runtime Wire

Suggested commit if/when selected: `feat(intel): voice transition judge evidence`

Include:

- `src/vibemix/intel/judge_voice.py`
- `src/vibemix/state/transition_judge_runtime.py`
- `src/vibemix/runtime/coach.py`
- `src/vibemix/state/coach.py`
- `tests/intel/test_judge_voice.py`
- `tests/runtime/test_coach_live_judge_run.py`
- `tests/state/test_coach_judge_voice_prompt.py`
- `.planning/packets/2026-06-01/CODEX_READY-judge-voice-runtime-wire.md`

Reason:

- This package wires measured Vibe Judge verdict evidence into the next
  `TRACK_CHANGE` prompt only when the Judge returns a judged verdict. Abstains
  inject nothing. The line carries the grounded `[judge:transition@t]` citation
  and the prompt tells the model to keep the citation exactly and avoid adding
  unsupported fader/EQ/deck-control causes.
- It does not claim every live rig can produce a Judge verdict. On master-only or
  unresolved deck-audio rigs the Judge still abstains by construction.

Proof already run:

- `uv run pytest -q tests/intel/test_judge_voice.py tests/runtime/test_coach_live_judge_run.py tests/state/test_coach_judge_voice_prompt.py tests/state/test_judge_and_record.py tests/state/test_judge_citation_schema_mirror.py`
  passed: 24 tests.
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
  passed: 84 tests.
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
  passed: 108 tests.
- `uv run ruff check src/vibemix/intel/judge_voice.py src/vibemix/state/transition_judge_runtime.py src/vibemix/runtime/coach.py src/vibemix/state/coach.py tests/intel/test_judge_voice.py tests/runtime/test_coach_live_judge_run.py tests/state/test_coach_judge_voice_prompt.py`
  passed.
- `git diff --check` across the Judge voice runtime slice passed.

Remaining gate:

- A full source/Tauri live pass should confirm a real two-deck judged transition
  produces a prompt/response artifact carrying the Judge evidence line. This is
  not controller-dependent, but it does require resolved two-deck audio/routing;
  without that, abstention is the correct live result.

Codex refresh, 2026-05-31 21:40 +03:

- Classification: LAND as conservative source/runtime wire. Live two-deck
  artifact proof remains required before product acceptance.
- Current code flow verified: `judge_and_record(...)` exposes
  `judge:transition@t` through `verdict_citation_id(...)`; `_run_live_judge(...)`
  appends a `verdict_evidence_line(...)` only for judged verdicts; `coach_loop`
  attaches the line to `ev.extra["judge_evidence_line"]`; `AICoach` injects it
  into the `TRACK_CHANGE` task with exact-citation and no-unsupported-cause
  instructions.
- `uv run pytest -q tests/intel/test_judge_voice.py tests/runtime/test_coach_live_judge_run.py tests/state/test_coach_judge_voice_prompt.py tests/state/test_judge_and_record.py tests/state/test_judge_citation_schema_mirror.py`
  passed: 24 tests.
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
  passed: 84 tests.
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
  passed: 108 tests.
- `uv run ruff check src/vibemix/intel/judge_voice.py src/vibemix/state/transition_judge_runtime.py src/vibemix/runtime/coach.py src/vibemix/state/coach.py tests/intel/test_judge_voice.py tests/runtime/test_coach_live_judge_run.py tests/state/test_coach_judge_voice_prompt.py`
  passed.
- `CODEX_READY-judge-voice-runtime-wire.md` refreshed with current dirty-count
  checker proof.

## Hold Lane - Judge Score Overpraise Clamp

Suggested commit if/when selected: `fix(coach): clamp judge overpraise to measured score`

Hold:

- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/state/deck_context.py`
- `tests/state/test_deck_context.py`

Reason:

- This is the second half of the Judge voice safety path. The Judge evidence
  line can reach the prompt, but the post-stream live-claim guard also needs the
  measured blend score so a weak or mid Judge verdict cannot be spoken as
  "bomb", "great", "perfect", or similar hype.
- Keep this hunk separate from the broader AI observability edits in
  `dj_cohost.py` and from deck-audio capture work in `deck_context.py`.

Proof already run:

- `uv run pytest -q tests/state/test_deck_context.py -k 'live_claim_guard or live_claim_policy'`
  passed: 33 tests.
- `uv run pytest -q tests/agent/test_dj_cohost.py -k 'live_claim_guard or deck_audio_parts_not_attached or event_audio_capture_context'`
  passed: 2 tests.
- `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/agent/dj_cohost.py tests/state/test_deck_context.py`
  passed.
- `git diff --check -- src/vibemix/state/deck_context.py src/vibemix/agent/dj_cohost.py tests/state/test_deck_context.py`
  passed.

Remaining gate:

- Needs source/Tauri live proof with a judged two-deck transition artifact to
  show the clamp is reachable after the model produces an overpraised response.
  The DDJ-FLX4 is now plugged back in, but no two-deck judged live event has
  been rerun for this package, so unit/agent proof is still the current ceiling.

## Package 8D - No Spoken Fallbacks Live Guard

Suggested commit if/when selected: `fix(cohost): strip unsafe live-claim fallbacks`

Include:

- `.planning/handoffs/2026-05-31-no-spoken-fallbacks-invariant.md`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/eval/session_report.py`
- `src/vibemix/state/deck_context.py`
- `tests/agent/test_dj_cohost.py`
- `tests/agent/test_dj_cohost_linter.py`
- `tests/eval/test_cohost_viber_session_report.py`
- `tests/state/test_deck_context.py`
- `tests/library/test_codex_curate.py`
- `tests/library/test_live_context_cli.py`
- `.planning/packets/2026-06-01/CODEX_READY-no-spoken-fallbacks-live-guard.md`

Reason:

- Product invariant: if the live co-host guard catches unsupported live/deck/EQ
  causality, Sven must not speak a canned fallback. A guard hit means "unsafe
  turn"; the live audio path should strip/log/repair rather than replace one
  hallucination with a softer one.
- The observed bad phrase existed in both Viber/global rows and live-cohost
  recordings. Source review shows no direct Viber -> Sven TTS bridge; the shared
  failure was the held-reply copy and `dj_cohost.py` emitting guard-corrected
  text.
- Viber may still show honest text for explicit library/chat turns. This package
  specifically forbids spoken live-cohost fallback behavior after a guard hit.

Proof already run:

- `uv run pytest -q tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py -k 'live_claim_guard or deck_audio_parts_not_attached or event_audio_capture_context'`
- passed: 8 tests, 62 deselected.
- `uv run pytest -q tests/state/test_deck_context.py -k 'live_claim_guard or live_claim_policy'`
- passed: 37 tests, 69 deselected.
- `uv run pytest -q tests/library/test_codex_curate.py -k 'library_request or live_context or chat_with_codex' tests/library/test_live_context_cli.py -k 'verify_live_reply'`
- passed: 9 tests, 119 deselected.
- `uv run pytest -q tests/eval/test_cohost_viber_session_report.py -k 'live_claim_guard or spoken_live_claim_guard'`
- passed: 1 test, 24 deselected.
- Current-source live proof, 2026-06-01: `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`,
  then websocket manual trigger with no live evidence. Runtime emitted
  `manual_silence_short_circuit` with `reason=manual_no_live_evidence`, recorded
  an `ai_message` row for `engine=live_coach event=MANUAL` with `message=""`,
  `response_chars=0`, `suppression=manual_no_evidence`,
  `citation.action=skip`, `extra.pre_llm_short_circuit=true`,
  `extra.audio_tokens_est=0`, and `extra.avoided_audio_tokens_est=1920`.
  `invocations/0001_085547_MANUAL/response.txt` and
  `ai_messages/artifacts/0001_085547/response.txt` were both 0 bytes, and
  websocket `ipc.session.snapshot` observations kept `transcript_delta=[]`.
  Proof session:
  `~/Library/Application Support/vibemix/recordings/20260601-085534/`.
- `uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py src/vibemix/eval/session_report.py tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/eval/test_cohost_viber_session_report.py`
- passed.
- `git diff --check -- src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py src/vibemix/eval/session_report.py tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/eval/test_cohost_viber_session_report.py .planning/handoffs/2026-05-31-no-spoken-fallbacks-invariant.md`
- passed.

Remaining gate:

- Run `vibemix eval latest-session` against final recordings and fail release
  if any guard-corrected live co-host turn produced spoken audio/transcript or
  `ipc.session.cohost-reaction`. Controller hardware is not required for the
  deterministic strip/no-evidence tests; a final two-deck hardware recording is
  still needed before a release claim.

## Package 8E - Audio Vibe Contract Prompt Guard

Suggested commit: `fix(prompts): keep audio vibe separate from control proof`

Include:

- `src/vibemix/prompts/matrix.py`
- `tests/agent/test_coach_prompt_grounding.py`
- `tests/prompts/test_matrix.py`

Reason:

- This is the prompt-side companion to Package 8D. The hard runtime guard strips
  unsupported live claims before speech; this package reduces how often the
  model tries to turn audio texture into fake EQ/fader/filter causality in the
  first place.
- The prompt contract preserves the magic of live audio as a listening signal
  for texture, energy, motion, density, mood, and silence/music presence, while
  explicitly forbidding track identity, deck identity, hidden-source detail, or
  control causality unless structured live evidence supplied it.
- The 2026-06-01 live FLX4 proof found a narrower prompt failure too: a valid
  PHASE citation still let "try the 1 next time" advice through with no recent
  move or resolved deck proof. This package now also covers the coach task tail
  and its prompt-grounding pin.
- Keep this separate from the runtime guard package when staging: Package 8D is
  the enforcement/silence backstop, Package 8E is prompt steering. Either can be
  reviewed without pretending the other proves a live model cannot regress.

Proof already run:

- `uv run pytest -q tests/prompts/test_matrix.py -k 'audio_vibe or double_opt_out or grammar'`
  passed: 20 tests, 76 deselected.
- `uv run ruff check src/vibemix/prompts/matrix.py tests/prompts/test_matrix.py`
  passed.
- 2026-06-01 follow-up: `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py tests/prompts/test_matrix.py tests/agent/test_coach_prompt_grounding.py tests/state/test_coach_anti_slop.py`
  passed: 248 tests. `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/agent/dj_cohost.py src/vibemix/prompts/matrix.py src/vibemix/state/coach.py tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py tests/prompts/test_matrix.py tests/agent/test_coach_prompt_grounding.py`
  passed.
- 2026-06-01 live source smoke with DDJ-FLX4 + Rekordbox + `VIBEMIX_INPUT_DEVICE='BlackHole 16ch'`
  produced session `20260601-144052`: app booted, MIDI status ok, live audio
  observed (`music` RMS around 0.04-0.06), MOSS spoke English, and the PHASE
  prompt carried the new no-advice rule. The PHASE response was sound-only
  ("A metallic, resonant sweep filter...") with no "try next time" advice.
  Honest caveat: `VIBEMIX_CITATION_LINT` was off in that source run, so this
  proves live boot/audio/MOSS/prompt behavior, not the final citation-lint gate.
- `.planning/packets/2026-06-01/CODEX_READY-audio-vibe-contract-prompt-guard.md`
  records the current proof.
- 2026-06-01 Codex follow-up from live FLX4/Rekordbox probe session
  `20260601-154514`: Gemini emitted `[aud:bpm@158]`, incorrectly using the BPM
  value as a citation timestamp while citation lint was off. This package now
  tells the model to copy exact `grounding_refs[...]` brackets verbatim and
  explicitly says `@158` means 158 seconds, not 158 BPM. Focused proof passed:
  `uv run pytest -q tests/prompts/test_matrix.py::test_o_citation_grammar_block_contains_eight_source_forms_and_multi_cite tests/prompts/test_matrix.py::test_s_grammar_block_has_v1_no_enforcement_wording tests/agent/test_coach_prompt_grounding.py::test_build_prompt_uses_real_evidence_registry_not_mocks`;
  broader prompt proof passed:
  `uv run pytest -q tests/agent/test_coach_prompt_grounding.py tests/prompts/test_matrix.py`;
  Ruff passed for the touched prompt/test files.

Remaining gate:

- Before final product acceptance, run the cohost/Viber matrix or runtime
  canaries against a fresh source session and confirm no EQ/control causality
  claim is spoken without structured move evidence.

## Package 8E2 - No-Move Control Praise Guard

Suggested commit: `fix(cohost): require proof for control-praise phrases`

Include:

- `src/vibemix/state/deck_context.py`
- `tests/state/test_deck_context.py`
- `src/vibemix/prompts/matrix.py`
- `tests/prompts/test_matrix.py`

Reason:

- Clean FLX4/Rekordbox source proof at session `20260601-161123` showed the
  guard still allowed no-move/no-citation control praise such as "filter sweep
  paid off" and "Deck A got piercing before you pulled it back". That is not a
  pure audio description; it credits an operator/control result without recent
  move proof.
- The runtime guard now treats terse control-praise phrases ("that filter sweep
  paid off", "you pulled it back") as unsupported no-move control causality.
  Pure audio texture remains allowed, for example "The filter sweep in the track
  sounded hollow."
- The prompt keeps pro-DJ anchor phrases, but explicitly says EQ/fader/filter/
  transition praise requires `recent_moves` or `live_evidence`/`grounding_refs`.

Proof already run:

- `uv run pytest -q tests/state/test_deck_context.py -k 'live_claim_guard or live_claim_policy'`
  passed: 41 tests, 69 deselected.
- `uv run pytest -q tests/prompts/test_matrix.py -k 'control_praise or anchor or audio_vibe or grammar'`
  passed: 26 tests, 75 deselected.
- `uv run pytest -q tests/state/test_deck_context.py tests/prompts/test_matrix.py`
  passed: 211 tests.
- `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/prompts/matrix.py tests/state/test_deck_context.py tests/prompts/test_matrix.py`
  passed.
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  passed with every dirty path assigned.

Remaining gate:

- Re-run a fresh cohost source session when convenient and confirm PHASE/MANUAL
  no-move turns do not speak control praise. This package is still useful
  without hardware because the failure is result-boundary deterministic.

## Package 8F - Internal Voice Tag Sanitizer

Suggested commit: `fix(cohost): strip internal voice tags from speech`

Include:

- `src/vibemix/agent/emote_parser.py`
- `tests/agent/test_emote_parser.py`
- `tests/agent/test_dj_cohost.py`
- `tests/agent/test_dj_cohost_streaming_pipe.py`

Reason:

- MOSS is now the single TTS source, but the live prompt can still make the
  model emit legacy Gemini-TTS delivery tags such as `[chill]` and `[excited]`.
  The 2026-06-01 FLX4 source smoke observed `[chill]` leaking into `ai_text` /
  `ai_message.message`. Those tags are internal control residue; they must not
  be spoken, shown in transcript, or counted as spoken response characters.
- Keep citation brackets intact for the grounding linter. This package strips
  only known delivery tags plus `[emote:*]`, preserving `[aud:...]` /
  `[ev:...]` citations for the existing validation path.

Proof already run:

- `uv run pytest -q tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_streaming_pipe.py`
  passed: 95 tests.
- `uv run ruff check src/vibemix/agent/emote_parser.py tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_streaming_pipe.py`
  passed.

Remaining gate:

- A future prompt-shaping package should remove obsolete delivery-tag prompting
  entirely for MOSS-only sessions. This package is the runtime backstop: even if
  the model emits a legacy tag, user-facing speech/log rows stay clean.

## Package 8G - MOSS Live Prompt Delivery Tag Opt-Out

Suggested commit: `fix(cohost): stop prompting moss voice tags`

Include:

- `src/vibemix/prompts/matrix.py`
- `src/vibemix/agent/dj_cohost.py`
- `tests/prompts/test_matrix.py`
- `tests/agent/test_dj_cohost.py`

Reason:

- Package 8F strips leaked delivery tags after model output. This companion
  package prevents the live co-host from inviting those tags in the first place:
  `DJCoHostAgent` asks for the audio-vibe grounding contract, but opts out of
  the legacy Gemini-TTS `[chill]` / `[excited]` DSL because MOSS is the only
  voice source.
- Backward-compatible prompt builders still keep the old `include_tag_dsl=True`
  default for legacy DSL tests/tools. The live MOSS path uses the new explicit
  combination: `include_tag_dsl=False`, `include_audio_vibe_contract=True`,
  `include_coach_closing=True`.

Proof already run:

- `uv run pytest -q tests/prompts/test_matrix.py tests/agent/test_dj_cohost.py tests/agent/test_emote_parser.py tests/agent/test_dj_cohost_streaming_pipe.py`
  passed: 195 tests.
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_dj_cohost_linter.py tests/prompts/test_negative_dict.py`
  passed: 52 tests.
- `uv run ruff check src/vibemix/prompts/matrix.py src/vibemix/agent/dj_cohost.py src/vibemix/agent/emote_parser.py tests/prompts/test_matrix.py tests/agent/test_dj_cohost.py tests/agent/test_emote_parser.py tests/agent/test_dj_cohost_streaming_pipe.py`
  passed.

Remaining gate:

- Final live source/packaged runs should confirm the prompt no longer causes
  bracket delivery tags in `ai_text` under real model output. Package 8F remains
  the hard backstop if a model still emits one.

## Package 8H - English-Only Runtime Speech Guard

Suggested commit: `fix(cohost): enforce english-only spoken output`

Include:

- `src/vibemix/agent/language_guard.py`
- `src/vibemix/agent/dj_cohost.py`
- `tests/agent/test_language_guard.py`
- `tests/agent/test_dj_cohost.py`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-english-only-runtime-guard.md`

Reason:

- The live prompt asks the model to stay in English, but prompt text is not a
  product boundary. Claude's co-host verifier accepted the MOSS tag cleanup and
  still found the real remaining hole: a non-English model response could pass
  through `strip_emote_tags`, reach MOSS, and be logged as spoken `ai_text`.
- This package adds a narrow runtime backstop at the co-host emission chokepoint:
  obvious Turkish DJ-chat is suppressed before speech/transcript/UI emission,
  while raw response artifacts remain saved for observability. English responses
  with grounding citations and Turkish-character artist names remain allowed.

Keep out:

- No prompt/persona rewrite beyond the already-landed MOSS tag opt-out.
- No DROP-call speech.
- No deck/controller inference changes.
- No new language-detection dependency.

Proof to run:

- `uv run pytest -q tests/agent/test_language_guard.py tests/agent/test_dj_cohost.py::test_llm_node_suppresses_non_english_spoken_text_but_keeps_raw_artifact tests/agent/test_dj_cohost.py::test_llm_node_english_only_guard_preserves_grounded_english_response tests/agent/test_dj_cohost.py::test_llm_node_strips_legacy_voice_tags_from_speech_and_ai_message tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/agent/test_dj_cohost_streaming_pipe.py`
- `uv run pytest -q tests/prompts/test_matrix.py tests/agent/test_dj_cohost_linter.py tests/state/test_coach_anti_slop.py`
- `uv run ruff check src/vibemix/agent/language_guard.py src/vibemix/agent/dj_cohost.py tests/agent/test_language_guard.py tests/agent/test_dj_cohost.py`

## Package 8I - TTS Citation Sanitizer

Suggested commit: `fix(cohost): keep citation atoms out of tts`

Include:

- `src/vibemix/agent/tts_sanitizer.py`
- `src/vibemix/agent/dj_cohost.py`
- `tests/agent/test_tts_sanitizer.py`
- `tests/agent/test_dj_cohost.py`
- `tests/agent/test_dj_cohost_streaming_pipe.py`
- `tests/agent/test_dj_cohost_linter.py`
- `tests/agent/test_overlay_publish.py`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-tts-citation-sanitizer.md`

Reason:

- Citation atoms are product receipts, not voice copy. They must stay in raw
  artifacts, linter input, `ai_text`, and `ai_message.message`, but MOSS should
  not vocalize bracket text such as `[aud:rms@12.0]`.
- This package adds a TTS-only sanitizer under the same co-host chokepoint:
  yielded chunks lose citation atoms, while visible/logged text keeps them.

Keep out:

- No citation-linter policy changes.
- No prompt/persona rewrite.
- No Viber/library changes.
- No DROP-call speech/timing.

Proof to run:

- `uv run pytest -q tests/agent/test_tts_sanitizer.py tests/agent/test_dj_cohost.py::test_llm_node_english_only_guard_preserves_grounded_english_response tests/agent/test_dj_cohost.py::test_AE_citation_count_event_written_per_turn tests/agent/test_dj_cohost.py::test_AJ_no_registry_path_writes_recorder_event_only tests/agent/test_dj_cohost_streaming_pipe.py`
- `uv run pytest -q tests/agent/test_dj_cohost_linter.py tests/agent/test_citation_strip_emit.py tests/coach/test_citation_linter.py`
- `uv run ruff check src/vibemix/agent/tts_sanitizer.py src/vibemix/agent/dj_cohost.py tests/agent/test_tts_sanitizer.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_streaming_pipe.py tests/agent/test_dj_cohost_linter.py`
- 2026-06-01 drift-test closure:
  `uv run pytest -q tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn tests/agent/test_overlay_publish.py::test_ipc_bus_none_is_silent tests/agent/test_overlay_publish.py::test_bus_emit_failure_is_swallowed`
  passed: 3 tests. This keeps fabricated recall strip isolated from the
  live-claim guard and updates overlay smoke expectations to the TTS-safe chunk
  contract: citation atoms remain available to logs/overlay parsing, not MOSS.

## Package 8K - EQ Move Physics Full-Suite Cleanup

Suggested commit: `fix(cohost): require eq state for move-effect license`

Include:

- `src/vibemix/state/deck_context.py` (state-aware EQ move license gate only;
  do not stage unrelated judge/voice/lufs/deck-audio hunks)
- `tests/state/test_deck_context.py` (state-aware stale EQ false-positive pins
  only)
- `src/vibemix/library/codex_curate.py`
- `src/vibemix/__main__.py` (only the `_load_env_robust` first-existing `.env`
  hunk; do not stage unrelated formatting/Viber setup hunks)
- `tests/agent/test_dj_cohost_streaming_pipe.py`
- `tests/library/test_codex_curate.py`
- `tests/state/test_coach.py`
- `tests/prompts/test_taste_persona_overlay.py`
- `tests/eval/test_replay_harness_phase_41.py`
- `scripts/release/check_cohost_viber_runtime_canaries.sh`
- `.planning/ROADMAP.md`
- `README.md`
- `docs/AUDIT.md`
- `.planning/codebase/orphans.csv`
- `.planning/eval-runs/flx4-live-context-current-codex-move-proof/session_trace_digest.jsonl`

Reason:

- Package `970e165b feat(intel): license grounded eq move effects` built the
  EQ move-effect producer and double gate. The full source suite then exposed
  stale expectations and one Viber guard edge: a licensed
  `move_effect_supported` verdict must be allowed to keep the grounded causal
  line instead of being flattened into the old generic refusal.
- The 2026-06-02 evidence pack then identified the remaining source-level
  keystone gap: prediction + measured delta can still be state-blind. This
  slice requires the current controller snapshot to agree with the canonical EQ
  move (`low_kill` needs the low tier to be killed/deep-cut/cut, boosts need a
  boost/max tier) before Sven may keep a causal move-effect line. Master-only
  rigs without a controller snapshot keep the older abstain-first measured-audio
  path; contradictory controller state always refuses.
- The cleanup keeps the default abstain/refuse posture intact, updates canaries
  and generated docs to the new guard behavior, and removes an oversized tracked
  live trace artifact while preserving the smaller proof summary files.

Proof to run:

- `uv run pytest -q tests/intel/test_eq_move_model.py tests/state/test_deck_context.py::test_move_effect_context_maps_recent_move_to_dsp_delta tests/state/test_deck_context.py::test_move_effect_context_refuses_stale_eq_move_when_controller_state_disagrees tests/state/test_deck_context.py::test_live_claim_guard_licenses_grounded_move_effect_causal_verdict tests/state/test_deck_context.py::test_live_claim_guard_refuses_move_effect_when_measured_bands_are_flat tests/state/test_deck_context.py::test_live_claim_guard_refuses_stale_eq_kill_when_controller_state_disagrees tests/state/test_deck_context.py::test_live_claim_guard_refuses_stale_eq_boost_when_controller_state_disagrees tests/state/test_deck_context.py::test_live_claim_guard_corrects_bare_move_effect_quality_verdict tests/state/test_deck_context.py::test_live_claim_guard_suppresses_eq_audio_song_detail_verdict`
- `uv run pytest -q tests/intel/test_eq_move_model.py tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py tests/library/test_codex_curate.py::test_chat_with_codex_licenses_grounded_move_effect_causal_verdict tests/library/test_codex_curate.py::test_chat_prompt_includes_recent_move_context_guard tests/state/test_coach.py::test_task_mix_move_includes_move_effect_context_when_dsp_delta_is_grounded`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
- `uv run pytest -q` before commit if the tree is otherwise settled enough.
- `uv run ruff check src/vibemix/intel/eq_move_model.py src/vibemix/state/deck_context.py src/vibemix/library/codex_curate.py src/vibemix/__main__.py tests/intel/test_eq_move_model.py tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost_streaming_pipe.py tests/library/test_codex_curate.py tests/state/test_coach.py tests/prompts/test_taste_persona_overlay.py tests/eval/test_replay_harness_phase_41.py`
- `git diff --check` across the Package 8K file set.

Remaining gate:

- LIVE proof remains separate from SRC: on the master-only FLX4/Rekordbox rig,
  confirm a real EQ move with bass licenses a grounded causal line, while the
  same move during a bassless breakdown stays silent/held. Do not claim this
  commit proves LIVE or PKG behavior.

## Package 8K2 - Short-Term LUFS Grounding Receipt

Suggested commit: `feat(audio): add short-term lufs grounding receipt`

Include:

- `src/vibemix/audio/lufs.py`
- `src/vibemix/state/music_state.py`
- `src/vibemix/state/refresh.py`
- `src/vibemix/state/deck_context.py`
- `tests/audio/test_lufs.py`
- `tests/state/test_deck_context.py`
- `tests/state/test_refresh_perceive.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Any co-host wording rewrite, prompt persona change, or DROP-call speech/timing.
- Any new citation source; the LUFS receipt rides the existing `mix:audio_delta`
  evidence key path.
- Any claim that LUFS alone proves a move's quality or causal effect. It is a
  loudness receipt only; EQ/fader causality stays behind the existing
  prediction-and-measurement guard.

Reason:

- Claude's Mixxx/R-SLOP backlog called for a short-term BS.1770 LUFS receipt as
  the next cheap grounding sibling after the EQ move-effect keystone. This
  package adds a dependency-free, K-weighted mono short-term loudness primitive,
  writes it through the state-refresh single writer, and renders a bounded
  `master_lufs_delta` atom only when the loudness window actually moves.
- Silence, cold windows, and flat/near-flat deltas abstain. The package does not
  make the co-host speak more often by itself; it gives the existing guard one
  more grounded receipt when a line is otherwise allowed.

Proof to run:

- `uv run pytest -q tests/audio/test_lufs.py tests/state/test_deck_context.py tests/state/test_refresh_perceive.py`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py tests/state/test_refresh.py tests/state/test_music_state.py tests/agent/test_dj_cohost_grounding.py tests/coach/test_citation_linter.py`
- `uv run ruff check src/vibemix/audio/lufs.py src/vibemix/state/music_state.py src/vibemix/state/refresh.py src/vibemix/state/deck_context.py tests/audio/test_lufs.py tests/state/test_deck_context.py tests/state/test_refresh_perceive.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check` across the Package 8K2 file set.

Remaining gate:

- SRC-only. A future LIVE pass must show the receipt appears on a real routed
  master signal during a measurable loudness move and remains absent on silence
  or a flat window.

## Package 8K3 - Move-Aligned EQ Audio Delta

Suggested commit: `fix(cohost): use move-aligned audio deltas for eq claims`

Include:

- `src/vibemix/state/music_state.py`
- `src/vibemix/state/refresh.py`
- `src/vibemix/state/deck_context.py`
- `tests/state/test_deck_context.py`
- `tests/state/test_refresh.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- No `runtime/coach.py` wording rewrite or DROP-call speech.
- No `src/vibemix/__main__.py` startup/config changes.
- No claim that source tests prove the FLX4/Rekordbox live rig.

Reason:

- The EQ move-effect gate already requires a recent move, predicted EQ physics,
  current controller state support, and measured audio direction. The remaining
  source gap was the audio window: consumers could read a generic tick-to-tick
  `audio_delta` after `prev_perceive` had advanced, so a real EQ move could be
  flattened by the next stable tick or confused with an unrelated delta.
- This slice adds a single-writer `move_audio_delta` cache in `MusicState`, seeded
  from the pre-move `prev_perceive` snapshot and kept briefly for the freshest
  controller move. EQ move-effect rendering, evidence keys, and the live claim
  guard prefer that move-aligned delta when it exists; otherwise the existing
  abstain/refuse path remains unchanged.

Proof to run:

- `uv run pytest -q tests/state/test_deck_context.py::test_move_effect_context_prefers_move_aligned_delta_over_flat_tick_delta tests/state/test_deck_context.py::test_live_claim_guard_prefers_move_aligned_delta_over_flat_tick_delta tests/state/test_refresh.py::test_tick_keeps_move_aligned_audio_delta_when_next_tick_is_flat`
- `uv run pytest -q tests/intel/test_eq_move_model.py tests/state/test_deck_context.py tests/state/test_refresh.py`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
- `uv run ruff check src/vibemix/state/music_state.py src/vibemix/state/refresh.py src/vibemix/state/deck_context.py tests/state/test_deck_context.py tests/state/test_refresh.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check` across the Package 8K3 file set.

Remaining gate:

- SRC-only. A future LIVE pass on the FLX4/Rekordbox rig must show a real EQ move
  licenses a grounded causal line only when the move-aligned measured delta and
  current mixer state both agree.

## Package 8L - AI Coach Prompt Builder Rename

Suggested commit: `refactor(state): rename ai coach prompt builder`

Include:

- `src/vibemix/state/prompt_builder.py`
- `src/vibemix/state/__init__.py`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/bench/assemble.py`
- `src/vibemix/learn/prompts.py`
- `src/vibemix/library/cue_detect.py`
- `tests/agent/test_coach_prompt_grounding.py`
- `tests/agent/test_dj_cohost_prompt_diet.py`
- `tests/agent/test_hype_prompt_grounding.py`
- `tests/learn/test_course3_live_set_rehearsal.py`
- `tests/learn/test_course3_uses_existing_coach.py`
- `tests/memory/test_no_live_path_import.py`
- `tests/repo/test_no_recall_antifeatures.py`
- `tests/repo/test_wire_regression_pins.py`
- `tests/state/test_coach.py`
- `tests/state/test_coach_course3_confidence_gate.py`
- `tests/state/test_coach_harmonic.py`
- `tests/state/test_coach_perceive.py`
- `tests/state/test_coach_prompt_diet.py`
- `tests/state/test_coach_prompt_grounding.py`
- `tests/state/test_refresh.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/runtime/coach.py` and its DROP-call hold-lane hunk.
- `src/vibemix/state/drop_predict.py`, `src/vibemix/state/event_detector.py`,
  `tests/state/test_drop_predict.py`, and `tests/state/test_event_detector_drop.py`.
- Any prompt wording, live-claim policy, or co-host speech behavior change.

Reason:

- The state-layer `AICoach` module builds grounded prompt text; it is not the
  runtime co-host loop. Renaming the implementation from `state/coach.py` to
  `state/prompt_builder.py` removes the long-running name collision with
  `runtime/coach.py` while preserving the public lazy export
  `from vibemix.state import AICoach`.

Proof before staging:

- `uv run pytest -q tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/state/test_coach_perceive.py tests/state/test_coach_prompt_grounding.py tests/state/test_coach_harmonic.py tests/state/test_coach_course3_confidence_gate.py tests/agent/test_dj_cohost_prompt_diet.py tests/agent/test_coach_prompt_grounding.py tests/agent/test_hype_prompt_grounding.py tests/learn/test_course3_uses_existing_coach.py tests/learn/test_course3_live_set_rehearsal.py tests/memory/test_no_live_path_import.py tests/bench/test_assemble.py tests/repo/test_no_recall_antifeatures.py`
- `uv run ruff check src/vibemix/state/__init__.py src/vibemix/state/prompt_builder.py src/vibemix/agent/dj_cohost.py src/vibemix/bench/assemble.py src/vibemix/learn/prompts.py src/vibemix/library/cue_detect.py tests/agent/test_coach_prompt_grounding.py tests/agent/test_dj_cohost_prompt_diet.py tests/agent/test_hype_prompt_grounding.py tests/learn/test_course3_uses_existing_coach.py tests/learn/test_course3_live_set_rehearsal.py tests/memory/test_no_live_path_import.py tests/repo/test_no_recall_antifeatures.py tests/repo/test_wire_regression_pins.py tests/state/test_coach.py tests/state/test_coach_course3_confidence_gate.py tests/state/test_coach_harmonic.py tests/state/test_coach_perceive.py tests/state/test_coach_prompt_diet.py tests/state/test_coach_prompt_grounding.py tests/state/test_refresh.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check`

## Hold Lane - Rebuild Carry-Forward Live Reality Pins

Suggested commit if/when selected: `test(repo): pin live reality gaps`

Hold:

- `tests/repo/test_live_reality_pins.py`

Reason:

- This is a reality pin that guards against false "Mastered" or live-capability
  claims, especially around the Beatmatch Judge producer gap. It is valuable
  during rebuild because it catches cases where the UI/consumer exists but the
  production event producer is absent.

Remaining gate:

- Keep the pin only while it describes the current rebuilt reality. Once the
  producer is wired and proven live, retire or rewrite the pin so it does not
  freeze a fixed gap as permanent truth.

## Package 8C - Mascot Emote Reaction Bridge

Suggested commit if/when selected: `feat(mascot): bridge cohost emotes to reactions`

Include:

- `src/vibemix/agent/emote_parser.py`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/state/music_state.py`
- `src/vibemix/runtime/ws_bus.py`
- `tauri/ui/src/mascot/index.ts`
- `tauri/ui/src/mascot/reaction-intent.ts`
- `tauri/ui/src/mascot/reaction-intent.test.ts`
- `tests/agent/test_emote_parser.py`
- `tests/agent/test_dj_cohost.py`
- `tests/e2e/test_seam_p31__ws_bus.py`

Reason:

- This closes the previously held seam where the Python parser existed and
  `ws_bus.py` exposed `reaction_intent`, but live co-host speech never stripped
  `[emote:*]` tags into state and the production mascot app never consumed the
  field. The bridge keeps raw model output in invocation artifacts, strips emote
  control tags from spoken/transcript/cohost-reaction text, increments
  `last_reaction_intent_seq` so the 30Hz snapshot stream fires once per co-host
  turn, and maps whitelisted intents onto existing production mascot states.
- Shared-file caution: `dj_cohost.py` is also in the AI-observability and Judge
  score lanes; `ws_bus.py` is also in Package 2. Stage by hunk if these packages
  are split.

Proof already run:

- `uv run python -m py_compile src/vibemix/agent/dj_cohost.py src/vibemix/agent/emote_parser.py src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py`
  passed.
- `uv run pytest -q tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/agent/test_dj_cohost_streaming_pipe.py tests/e2e/test_seam_p31__ws_bus.py`
  passed: 41 tests.
- `uv run ruff check src/vibemix/agent/emote_parser.py src/vibemix/agent/dj_cohost.py src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py tests/e2e/test_seam_p31__ws_bus.py`
  passed.
- `npm --prefix tauri/ui test -- src/mascot/reaction-intent.test.ts src/mascot/event-dispatcher.test.ts`
  passed: 22 tests.
- `npm --prefix tauri/ui run build`
  passed, including the mascot bundle.

Remaining gate:

- Source/Tauri visual proof with a live co-host response containing a whitelisted
  `[emote:*]` marker should verify the mascot visibly reacts once per response.
  Controller hardware is not required; a manual co-host trigger is enough.

Codex refresh, 2026-06-01:

- Classification: LAND as source-wired mascot reaction bridge. Live visual proof
  is still required before product acceptance.
- Current code flow verified: `strip_emote_tags(...)` strips control tags from
  spoken/transcript text; `DJCoHostAgent` writes `last_reaction_intent` plus an
  incremented `last_reaction_intent_seq`; `ws_bus.py` emits both fields in the
  snapshot; `selectReactionIntent(...)` accepts only whitelisted intents with a
  fresh numeric sequence; `mascot/index.ts` fires the mapped reaction once.
- Codex found and patched one edge during verification: unknown complete tags
  such as `[emote:wink]` are now stripped from speech without firing a mascot
  intent, instead of leaving raw bracket text in a replay buffer.
- `uv run python -m py_compile src/vibemix/agent/dj_cohost.py src/vibemix/agent/emote_parser.py src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py`
  passed.
- `uv run pytest -q tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/agent/test_dj_cohost.py::test_llm_node_strips_unknown_emote_tags_without_mascot_intent tests/agent/test_dj_cohost_streaming_pipe.py tests/e2e/test_seam_p31__ws_bus.py`
  passed: 43 tests.
- `uv run pytest -q tests/agent/test_dj_cohost.py::test_llm_node_logs_ai_message_observability_with_moves tests/agent/test_dj_cohost.py::test_llm_node_ai_message_uses_prompt_time_mixer_snapshot tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent tests/agent/test_dj_cohost.py::test_llm_node_strips_unknown_emote_tags_without_mascot_intent tests/runtime/test_ws_bus_snapshot.py`
  passed: 13 tests.
- `uv run ruff check src/vibemix/agent/emote_parser.py src/vibemix/agent/dj_cohost.py src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py tests/agent/test_emote_parser.py tests/agent/test_dj_cohost.py tests/e2e/test_seam_p31__ws_bus.py tests/runtime/test_ws_bus_snapshot.py`
  passed.
- `npm --prefix tauri/ui test -- src/mascot/reaction-intent.test.ts src/mascot/event-dispatcher.test.ts`
  passed: 22 tests.
- `npm --prefix tauri/ui run build`
  passed.
- `.planning/packets/2026-06-01/CODEX_READY-emote-mascot-reaction-bridge.md`
  added with current source evidence and live-proof caveat.

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
- `src/vibemix/runtime/drop_display.py`
- `src/vibemix/runtime/ws_bus.py`
- `src/vibemix/runtime/session_loop.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/mock-transfer/contract.ts`
- `tauri/ui/src/session/SessionLayout.ts`
- `tauri/ui/src/session/render-loop.ts`
- `tauri/ui/src/session/router.ts`
- `tauri/ui/src/session/state.ts`
- `tauri/ui/src/session/ws-bridge.ts`
- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/src/settings/components/citation-diagnostics.ts`
- `tauri/ui/src/settings/components/citation-diagnostics.spec.ts`
- `tauri/ui/src/settings/components/profile-panel.ts`
- `tauri/ui/src/settings/components/profile-panel.spec.ts`
- `tauri/ui/tests/session/components.spec.ts`
- `tauri/ui/tests/session/render-loop.spec.ts`
- `tauri/ui/tests/session/router-teardown.spec.ts`
- `tauri/ui/tests/mock-transfer-contract.spec.ts`
- `tauri/ui/tests/session/render-loop-actions.spec.ts`
- `tauri/ui/tests/session/ws-bridge.recordings.spec.ts`
- `tauri/ui/tests/settings/drawer.spec.ts`
- `tests/runtime/test_session_loop.py`
- `tests/runtime/test_ws_bus_snapshot.py`
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
- Codex drop-chip display slice, 2026-05-31: `src/vibemix/runtime/drop_display.py`
  converts finite `predicted_drop_in_sec` + BPM into whole 4-beat bars;
  `ws_bus.py` and `session_loop.py` now pass that value as `drop_pred_bars`;
  `SessionLayout.ts` mounts the existing `renderDropChip()` output only while
  the field is non-null. Focused proof passed:
  `uv run pytest -q tests/runtime/test_ws_bus_snapshot.py tests/runtime/test_session_loop.py`
  (35 tests), `uv run ruff check src/vibemix/runtime/drop_display.py src/vibemix/runtime/ws_bus.py src/vibemix/runtime/session_loop.py tests/runtime/test_ws_bus_snapshot.py tests/runtime/test_session_loop.py`,
  `npm --prefix tauri/ui test -- tests/session/components.spec.ts` (47 tests),
  and `git diff --check` across the slice.
- Codex deferred-settings truth slice, 2026-05-31: current source confirms
  voice persists when `cascade_agent is None` and output device/profile persist
  when `audio_core is None`; the Settings drawer now labels those controls as
  next-start settings instead of implying a live swap. Focused proof passed:
  `npm --prefix tauri/ui test -- tests/settings/drawer.spec.ts` (25 tests),
  `npm --prefix tauri/ui test -- tests/session/components.spec.ts` (47 tests),
  `npm --prefix tauri/ui run build`, and `git diff --check` across the slice.
- Codex mute-feedback slice, 2026-05-31: live source injects the real
  `PlaybackQueue` into `SessionLoop`, backend mute toggles state and drains that
  queue on mute-engage, and the UI now flips `SessionState.muted`
  optimistically while preserving the sidecar ack as authoritative. Focused
  proof passed: `uv run pytest -q tests/runtime/test_session_loop.py -k 'mute'`
  (3 tests), `npm --prefix tauri/ui test -- tests/session/render-loop-actions.spec.ts tests/session/components.spec.ts tests/settings/drawer.spec.ts`
  (79 tests), `npm --prefix tauri/ui test -- tests/session/shortcuts.spec.ts tests/session/integration.spec.ts`
  (29 tests), `npm --prefix tauri/ui run build`, and `git diff --check` across
  the slice.
- Codex live-claim proof chip slice, 2026-05-31: `ws_bus.py` now includes the
  current `live_claim_policy` collapsed to `green` / `yellow` / `red` in
  `ipc.session.snapshot`; `SessionLayout.ts` renders a small bottom-row proof
  chip (`verdict proof`, `candidate only`, `watch only`, `claims held`, or
  `proof pending`) without touching the co-host wording call sites. Focused
  proof passed: `uv run pytest -q tests/runtime/test_ws_bus_snapshot.py tests/ui_bus/test_messages_schema.py`
  (87 tests), `npm --prefix tauri/ui test -- tests/session/render-loop.spec.ts tests/session/state.spec.ts`
  (23 tests), `npm --prefix tauri/ui run check:ipc`, `uv run ruff check
  src/vibemix/runtime/ws_bus.py src/vibemix/ui_bus/messages.py
  tests/runtime/test_ws_bus_snapshot.py`, `npm --prefix tauri/ui run build`,
  and `git diff --check` across the slice.
- Codex overlay-highlight listener slice, 2026-05-31: Python already publishes
  `ipc.session.overlay-highlight` after spoken `[screen:*]` citations, and
  `overlay/overlay-highlight.ts` already forwards it to the Rust
  `show_overlay_highlight` command. `routeSession()` now starts that listener
  and `teardownSession()` unsubscribes it with the other route-owned listeners.
  Focused proof passed: `npm --prefix tauri/ui test -- tests/session/router-teardown.spec.ts`
  (1 test), `npm --prefix tauri/ui run build`, and `git diff --check` across
  the slice.
- Codex refresh, 2026-06-01: LAND as a session transport/diagnostics slice,
  with Package 2/3 schema-codegen staging caution still active. `which_handler`
  verified both-end wiring for `ipc.status.recheck`, `ipc.profile.view`,
  `ipc.session.citation`, `ipc.session.overlay-highlight`,
  `ipc.library.staleness_nudge`, and `ipc.session.snapshot`. Codex found and
  patched missing mock-transfer anchors for `session.drop`,
  `session.claim-policy`, `settings.persona.voice.deferred-note`, and
  `settings.output.deferred-note`. Current proof passed:
  `uv run python scripts/check_ipc_schema.py`, `uv run python
  .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`,
  `uv run pytest -q tests/ipc/test_library_schemas.py
  tests/ui_bus/test_messages_schema.py tests/ui_bus/test_recordings_messages.py
  tests/ui_bus/test_mood_change_envelope.py` (118 tests),
  `uv run pytest -q tests/wizard/test_wizard_loop_ipc.py
  tests/runtime/test_session_loop.py tests/ui_bus/test_status_tick.py
  tests/runtime/test_ws_bus_snapshot.py` (56 tests),
  `npm --prefix tauri/ui test -- src/settings/components/profile-panel.spec.ts
  src/settings/components/citation-diagnostics.spec.ts tests/settings/drawer.spec.ts
  tests/settings/staleness-banner.spec.ts tests/mock-transfer-contract.spec.ts`
  (71 tests), `npm --prefix tauri/ui test -- tests/session/components.spec.ts
  tests/session/render-loop.spec.ts tests/session/render-loop-actions.spec.ts
  tests/session/router-teardown.spec.ts tests/session/ws-bridge.recordings.spec.ts`
  (75 tests), `npm --prefix tauri/ui run check:ipc`, `npm --prefix tauri/ui run
  build`, `cargo test --manifest-path tauri/src-tauri/Cargo.toml
  resolve_sidecar` (5 tests), `uv run ruff check` across Package 2 Python
  files/tests, and `git diff --check` across Package 2 files. A source-mode
  websocket probe also passed: `ipc.status.recheck` for MIDI returned
  `ipc.status.tick livekit=connecting gemini=down midi=1 screen=ok`, and
  `ipc.profile.view` returned `ipc.profile.view_result`.
- `.planning/packets/2026-06-01/CODEX_READY-session-ipc-diagnostics-wiring.md`
  added with current source evidence and Tauri-GUI proof caveat.

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
- Codex refresh, 2026-06-01: LAND as an IPC contract cleanup slice. Current
  source confirms stale `ipc.library.search`, `ipc.library.search_result`,
  `ipc.library.confidence`, `ipc.library.similar`,
  `ipc.library.similar_result`, `ipc.debrief.citation-summary`, and
  `ipc.debrief.event-timeline` contracts are absent from the live bus. Real
  library search/similar remains available via Tauri `library_search` and
  `library_similar` commands. Current proof passed: `uv run python
  scripts/check_ipc_schema.py`, `uv run python
  .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`,
  `npm --prefix tauri/ui run check:ipc`, `uv run pytest -q
  tests/ipc/test_learn_envelope_parity.py tests/ipc/test_library_schemas.py
  tests/ui_bus/test_citation_schema.py tests/ui_bus/test_overlay_schema.py
  tests/ui_bus/test_debrief_new_wrappers_roundtrip.py
  tests/ui_bus/test_debrief_schema_additive_only.py
  tests/ui_bus/test_debrief_schemas.py tests/ui_bus/test_messages_schema.py
  tests/ui_bus/test_mood_change_envelope.py tests/ui_bus/test_recordings_messages.py`
  (185 tests), `cargo test --manifest-path tauri/src-tauri/Cargo.toml
  library_cmds` (30 tests), `uv run ruff check` across the IPC/UI-bus slice,
  and `git diff --check` across Package 3 files.
- `.planning/packets/2026-06-01/CODEX_READY-ipc-contract-cleanup.md` added
  with current source evidence and the Package 2/3 combined-staging warning.

## Package 4 - Auto And ANLZ Hot-Cue Pipeline

Suggested commit: `fix(library-cues): preserve hot cue slots through suggestions`

Include:

- `src/vibemix/library/ingest.py`
- `src/vibemix/library/folder_ingest.py`
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
- 2026-05-31 Codex refresh for opt-in cue-agreement calibration:
  `uv run pytest -q tests/library/test_ingest.py tests/library/test_cue_agreement.py`
  passed: 23 tests; `uv run ruff check src/vibemix/library/folder_ingest.py src/vibemix/library/ingest.py src/vibemix/__main__.py tests/library/test_ingest.py`
  passed.
- `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts`
  passed: 167 tests.
- `npm --prefix tauri/ui run test:e2e:pill`
  passed: 16 tests.

2026-06-01 Codex refresh:

- Packet: `.planning/packets/2026-06-01/CODEX_READY-auto-anlz-hot-cue-pipeline.md`
- `uv run pytest -q tests/library/test_ingest.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py`
  passed: 88 tests. This current run verifies ANLZ and auto cue materialization,
  semantic A-H slot preservation, next-suggestion auto-cue CARE downgrade, and
  Viber/MCP `get_track_sections` slot/source propagation.
- `uv run pytest -q tests/library/test_ingest.py tests/library/test_cue_agreement.py`
  passed: 23 tests. Cue-agreement calibration remains opt-in telemetry and does
  not replace DJ-authored cached cues.
- `uv run ruff check tests/library/test_ingest.py src/vibemix/library/ingest.py src/vibemix/library/folder_ingest.py src/vibemix/library/smart_cues.py src/vibemix/intel/move_grade.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py`
  passed.
- `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts`
  passed: 167 tests.
- `npm --prefix tauri/ui run test:e2e:pill`
  passed: 16 tests.
- `git diff --check -- <Package 4 files>` passed.

Remaining gate:

- Live DDJ/Viber proof. Preserve both `CuePoint.source` and `CuePoint.number`; cue-review
  uncertainty should surface as `CARE`.

## Package 4B - Real-Audio Cue Detection Eval Gate

Suggested commit: `test(library): add real-audio cue detection gate`

Include:

- `scripts/eval/cue_detect.py`
- `tests/library/fixtures/cue_real_corpus/manifest.json`
- `tests/library/test_cue_detect_eval.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime cue detector changes. This is an eval/test gate only.
- Product copy claiming cue detection is perfect. The gate is a no-regression
  floor over committed fixtures, not a published benchmark.

Reason:

- Package 4/Serato/cue GUI made auto cues valuable and visible, but most older
  tests still exercise synthetic cue payloads or monkeypatched detectors. This
  slice runs the shipped deterministic `vibemix.library.cue_detect.detect_cues`
  on the committed DJ MP3 fixtures in `tests/bench/data/`.
- The manifest checks real-audio labels plus coarse timing windows for
  breakdown/drop anchors, and intentionally forbids dance labels on flatter
  clips. That catches the dangerous regression class: fabricated drops that
  still pass synthetic tests.

Proof for this source slice:

- `uv run python scripts/eval/cue_detect.py`
- `uv run pytest -q tests/library/test_cue_detect_eval.py`
- `uv run ruff check scripts/eval/cue_detect.py tests/library/test_cue_detect_eval.py`
- `git diff --check -- scripts/eval/cue_detect.py tests/library/fixtures/cue_real_corpus/manifest.json tests/library/test_cue_detect_eval.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- Grow this corpus only with license-clean audio and grounded manifest windows.
  If a future cue engine legitimately improves timing/labels, update the
  manifest and document the measured change in the same commit.

## Package 4C - Auto-Cue Audible Boundary Floor

Suggested commit: `fix(library): bound auto cues to audible material`

Include:

- `src/vibemix/library/cue_detect.py`
- `src/vibemix/library/cue_engine.py`
- `tests/library/test_cue_detect.py`
- `tests/library/test_cue_engine.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime/live DROP speech or timing changes.
- Model hosting, CUE-DETR weight changes, or any published benchmark claim.

Reason:

- The recovered Mixxx goldmine identified a cheap deterministic cue floor:
  first/last audible material should bound any model-produced structural cue.
  The pure-DSP fallback already reasons about sustained intro/outro frames, but
  the ONNX producer path could still turn a candidate inside silent lead-in or
  silent tail into a hot-cue anchor.
- This slice exposes a shared `audible_bounds_s()` helper and applies it to the
  CUE-DETR → CueAnchor assembly. All-silent audio now returns no anchors, a
  lead-in candidate clamps to first audible material, and tail candidates after
  the last audible frame are suppressed.

Proof for this source slice:

- `uv run pytest -q tests/library/test_cue_detect.py tests/library/test_cue_engine.py tests/library/test_cue_detect_eval.py`
  passed with 30 tests.
- `uv run python scripts/eval/cue_detect.py` passed with `ok: true`,
  `label_recall: 1.0`, `unexpected_labels: 0`, and `timing_misses: 0`.
- `uv run ruff check src/vibemix/library/cue_detect.py src/vibemix/library/cue_engine.py tests/library/test_cue_detect.py tests/library/test_cue_engine.py`
  passed.

Remaining gate:

- This hardens cue placement in source. It does not prove CUE-DETR model
  availability, packaged-binary behavior, or cross-app render in Rekordbox /
  Serato / Mixxx.

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

2026-06-01 Codex refresh:

- Packet: `.planning/packets/2026-06-01/CODEX_READY-library-ui-live-read-context.md`
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed: 73 tests. This current run verifies live-context normalization,
  proof-state rendering, chat-bound deck-pair context, stale-context clearing,
  and live-verification receipt display without internal guard-label leakage.
- `npm --prefix tauri/ui run build` passed: `tsc --noEmit && vite build`.
- Supporting cross-lane proof, not a Package 5 staging file:
  `uv run pytest -q tests/library/test_live_context_cli.py` passed: 40 tests;
  `uv run ruff check tests/library/test_live_context_cli.py` passed. These
  tests prove proof-file live context can enter library chat and unsupported
  transition/audio claims are rejected or corrected by the verifier lane.
- `git diff --check -- <Package 5 files plus supporting live-context CLI test>`
  passed.

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

2026-06-01 Codex refresh:

- Packet: `.planning/packets/2026-06-01/CODEX_READY-compact-pill-polish.md`
- LAND as `feat(pill): polish next suggestion care interactions`.
- `npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts`
  passed: 167 tests. This current run verifies CARE/KEEP feedback contracts,
  compact ARIA/detail preservation, primary click/key completion, demo shortcut
  gating, and auto-cue-review CARE treatment.
- `npm --prefix tauri/ui run test:e2e:pill` passed: 16 Playwright tests. This
  covers hover/click ownership under demo-control overlap, CARE completion,
  stale-suggestion suppression, narrow layout containment, focus return,
  Escape dismissal, demo reaction pads, canvas pixels, and reduced motion.
- `npm --prefix tauri/ui run build` passed: `tsc --noEmit && vite build`.
- `git diff --check -- <Package 6 files>` passed.
- Remaining gate unchanged: optional visual pass in the live Tauri UI once a
  sidecar/app run is available.

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

2026-06-01 Codex refresh:

- Packet: `.planning/packets/2026-06-01/CODEX_READY-learn-operator-action-bridge.md`
- LAND as `feat(learn): bridge route-mismatch operator actions`.
- `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_operator_action.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  passed: 55 tests. This verifies Course 3 nested operator actions, generic
  `learn_operator_action` bridge/clear, Tauri `learn-operator-action`
  subscription/unlisten, route-mismatch compact prompt rendering, screen-only
  control fallback acks, and start-course automation payloads.
- `uv run python scripts/export_learn_curriculum_meta.py --check` passed.
- `uv run pytest -q tests/learn/test_curriculum_projection.py` passed: 4 tests.
- `npm --prefix tauri/ui run build` passed: `tsc --noEmit && vite build`.
- `git diff --check -- <Package 7 files>` passed.
- Boundary: this is a Learn UI/transport/projection package. It does not claim
  GSD, beginner-path-suite coverage, or Course 3 routed-audio release readiness.

## Package 8 - Beatmatch Judge Honesty Boundary

Suggested commit: `fix(learn): keep beatmatching unmastered until live producer`

Include:

- `src/vibemix/learn/beatmatch_judge.py`
- `src/vibemix/learn/skill_recognizer.py`
- `src/vibemix/learn/skill_tree.py`
- `tests/learn/test_judge_credits_beatmatch.py`
- `tests/learn/test_creditability_drift.py`
- `tests/learn/test_progress_snapshot_skill_wall.py`
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
- Codex honesty correction, 2026-05-31: the Beatmatch Judge/consumer remain
  future-ready, but the Earned Wall no longer promises a live Mastered path while
  the production `BEATMATCH_GRADED` emitter is absent. Stored/stale beatmatch
  mastery is masked at compute time until `live_creditable=True` again. Focused
  proof passed:
  `uv run pytest -q tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/learn/test_judge_credits_beatmatch.py tests/repo/test_live_reality_pins.py`
  (24 tests), `uv run ruff check src/vibemix/learn/skill_tree.py src/vibemix/learn/skill_recognizer.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py`,
  `npm --prefix tauri/ui test -- tests/learn/test_skill_wall.spec.ts tests/learn/skill-tree-a11y.spec.ts`
  (14 tests), and `git diff --check` across the slice.

Remaining gate:

- Wire the live practice loop to emit cited `BEATMATCH_GRADED` only from the
  owned-deck judge path. When that lands, flip `beatmatching.live_creditable`
  back to true, retire or rewrite the reality pin, and re-enable the ordinary
  "N more cited live demos" wall copy.

2026-06-01 Codex refresh:

- Packet: `.planning/packets/2026-06-01/CODEX_READY-beatmatch-judge-honesty-boundary.md`
- LAND as `fix(learn): keep beatmatching unmastered until live producer`.
- `uv run pytest -q tests/audio/test_grid.py tests/audio/test_miniplayer.py tests/learn/test_beatmatch_judge.py tests/learn/test_judge_credits_beatmatch.py`
  passed: 28 tests. This verifies the exact judge math and synthetic
  `BEATMATCH_GRADED` consumer branch.
- `uv run pytest -q tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/learn/test_judge_credits_beatmatch.py tests/repo/test_live_reality_pins.py`
  passed: 24 tests. This verifies beatmatching is the only current
  honest-uncreditable skill, stale stored mastery is masked, and no production
  emitter/import exists.
- `npm --prefix tauri/ui test -- tests/learn/test_skill_wall.spec.ts tests/learn/skill-tree-a11y.spec.ts`
  passed: 14 tests.
- `uv run ruff check <Package 8 Python files>` passed.
- `git diff --check -- <Package 8 files>` passed.
- Boundary unchanged: this package keeps the product honest; it does not ship
  the owned-deck live producer.

## Package 8A - Cue Placement Judge Primitive

Suggested commit: `feat(learn): grade cue placement against beatgrid`

Include:

- `src/vibemix/learn/cue_placement_judge.py`
- `tests/learn/test_cue_placement_judge.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live cue detector changes.
- Runtime coach or co-host speech changes.
- Learn skill-credit producer wiring.

Reason:

- Claude's capability inventory marked `grade_cue_placement` / Cue-Drop Judge as
  claimed-but-absent. The source already has the clean-room `BeatGrid` primitive;
  this package adds the offline Learn judge half without claiming live proof.
- The judge measures signed cue timing against the nearest beat and, when a drop
  target frame is provided, requires the cue to be near that absolute target
  rather than merely on some other beat.

Proof for this source slice:

- `uv run pytest -q tests/learn/test_cue_placement_judge.py tests/audio/test_grid.py`
- `uv run ruff check src/vibemix/learn/cue_placement_judge.py tests/learn/test_cue_placement_judge.py`
- `git diff --check -- src/vibemix/learn/cue_placement_judge.py tests/learn/test_cue_placement_judge.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- This is an offline primitive only. A future package must wire it into a real
  Learn/practice flow with cited evidence before any user-visible Mastered,
  cue-quality, or live-coach claim.

## Package 8B - Cue Placement Practice Producer

Suggested commit: `feat(learn): emit cited cue placement practice grades`

Include:

- `src/vibemix/learn/cue_practice.py`
- `src/vibemix/learn/skill_recognizer.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/learn/__init__.py`
- `tests/learn/test_cue_practice.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live co-host speech, runtime coach, DROP speech, and prompt wording changes.
- Library-file mutation / hot-cue writeback.
- Any new skill id or user-visible Mastered copy.

Reason:

- Package 8A intentionally stopped at the offline cue-placement judge. This
  package turns that measured judge result into a cited Learn practice event
  without making Sven speak or inferring from observational live audio.
- `CUE_PLACEMENT_GRADED` credits `phrasing_performance` only when the owned cue
  is beat-locked and, when a target is supplied, drop-locked to that absolute
  target. Wrong-drop/off-beat grades write no EvidenceRegistry receipt and move
  no skill wall count.

Proof for this source slice:

- `uv run pytest -q tests/learn/test_cue_practice.py tests/learn/test_cue_placement_judge.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_practice_loop.py tests/learn/test_skill_recognizer.py tests/learn/test_skill_wall_what_remains.py`
- `uv run ruff check src/vibemix/learn/cue_practice.py src/vibemix/learn/runtime.py src/vibemix/learn/skill_recognizer.py src/vibemix/learn/__init__.py tests/learn/test_cue_practice.py tests/learn/test_runtime_evidence_grounding.py`
- `git diff --check -- src/vibemix/learn/cue_practice.py src/vibemix/learn/skill_recognizer.py src/vibemix/learn/runtime.py src/vibemix/learn/__init__.py tests/learn/test_cue_practice.py tests/learn/test_runtime_evidence_grounding.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- SRC producer is real and cited. A future lesson-driver/UI package still needs
  to supply real cue frames from an owned practice deck before this becomes
  visible learner UX. Do not use this source proof to claim live hot-cue
  writeback or co-host coaching.

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

## Package B2 - Practice Deck Beatmatch Producer

2026-06-02 Codex refresh:

- Packet: `.planning/packets/2026-06-01/CODEX_READY-B2-practice-deck-beatmatch-producer.md`
- LAND as `feat(learn): emit cited beatmatch practice grades`.

Include:

- `src/vibemix/learn/practice_loop.py`
- `src/vibemix/learn/__init__.py`
- `src/vibemix/learn/beatmatch_judge.py`
- `src/vibemix/learn/skill_recognizer.py`
- `src/vibemix/learn/skill_tree.py`
- `tests/learn/test_practice_loop.py`
- `tests/learn/test_creditability_drift.py`
- `tests/learn/test_judge_credits_harmonic.py`
- `tests/learn/test_skill_recognizer.py`
- `tests/learn/test_skill_wall_what_remains.py`
- `tests/repo/test_live_reality_pins.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Course 3 full routed-audio proof.
- Frontend lesson UX polish and Tauri control-surface changes.
- Live co-host speech, DROP speech, `runtime/coach.py`, and `__main__.py`.

Proof for this source slice:

- `uv run pytest -q tests/learn/test_practice_loop.py tests/learn/test_beatmatch_judge.py tests/learn/test_judge_credits_beatmatch.py tests/learn/test_judge_credits_harmonic.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/learn/test_skill_recognizer.py tests/repo/test_live_reality_pins.py`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
- `uv run ruff check src/vibemix/learn/practice_loop.py src/vibemix/learn/__init__.py src/vibemix/learn/beatmatch_judge.py src/vibemix/learn/skill_recognizer.py src/vibemix/learn/skill_tree.py tests/learn/test_practice_loop.py tests/learn/test_creditability_drift.py tests/learn/test_judge_credits_harmonic.py tests/learn/test_skill_recognizer.py tests/learn/test_skill_wall_what_remains.py tests/repo/test_live_reality_pins.py`
- `git diff --check -- <Package B2 files>`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- SRC producer is real and cited. LIVE proof still needs the Learn beatmatch
  practice lesson driven on the actual rig: lock two owned decks -> cited
  `BEATMATCH_GRADED` credit; deliberate trainwreck -> no credit.

## Package W2 - Prep to Live Set Awareness

2026-06-02 Codex refresh:

- Packet: `.planning/packets/2026-06-01/CODEX_READY-W2-prep-live-set-awareness.md`
- LAND as `feat(coach): surface saved set progress`.

Include:

- `src/vibemix/state/set_plan.py`
- `src/vibemix/runtime/set_plan_voice.py`
- `src/vibemix/state/music_state.py`
- `src/vibemix/state/refresh.py`
- `src/vibemix/runtime/coach.py`
- `src/vibemix/state/prompt_builder.py`
- `src/vibemix/__main__.py`
- `tests/state/test_set_plan.py`
- `tests/runtime/test_set_plan_voice.py`
- `tests/runtime/test_coach.py`
- `tests/state/test_coach.py`
- `tests/state/test_refresh.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- DROP-call speech activation and any `VIBEMIX_DROP_CALL` default change.
- Energy-curve/ahead-behind language until the saved set artifact persists a
  citable planned curve or planned energy values.
- Viber GUI/editor changes; this package only exposes the latest saved pool to
  live state and the co-host prompt.

Proof for this source slice:

- `uv run pytest -q tests/state/test_set_plan.py tests/runtime/test_set_plan_voice.py tests/runtime/test_coach.py::test_coach_hands_grounded_set_progress_to_agent_without_suggestion_service tests/state/test_coach.py::test_task_track_change_includes_grounded_set_progress_receipt tests/state/test_refresh.py::test_tick_writes_set_progress_from_latest_prepared_pool`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_event_detector.py`
- `uv run ruff check src/vibemix/state/set_plan.py src/vibemix/runtime/set_plan_voice.py src/vibemix/state/music_state.py src/vibemix/state/refresh.py src/vibemix/runtime/coach.py src/vibemix/state/prompt_builder.py tests/state/test_set_plan.py tests/runtime/test_set_plan_voice.py tests/runtime/test_coach.py tests/state/test_coach.py tests/state/test_refresh.py`
- `git diff --check -- <Package W2 files>`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- LIVE proof remains open: load a saved Viber/prepared pool, play an in-pool
  track on a citable deck, and confirm Sven receives a resolved saved-set
  receipt; then play an off-plan track and confirm this axis stays silent.

## Hold Lane - 2026-06-02 Learn Army Workflow Docs

Hold:

- `.planning/packets/2026-06-02/`
- `.planning/packets/2026-06-02/_learn-army.workflow.js`
- `.planning/packets/2026-06-02/_learn-army-finish.workflow.js`
- `.planning/packets/2026-06-02/LEARN-ROADMAP-RISK-GRAVEYARD.md`
- `.planning/packets/2026-06-02/learn-army/A1-engine-census.md`
- `.planning/packets/2026-06-02/learn-army/A2-producer-gaps.md`
- `.planning/packets/2026-06-02/learn-army/A3-livecoach-join.md`
- `.planning/packets/2026-06-02/learn-army/A4-ipc-ui-surface.md`
- `.planning/packets/2026-06-02/learn-army/B1-gamification.md`
- `.planning/packets/2026-06-02/learn-army/B2-social-cert.md`
- `.planning/packets/2026-06-02/learn-army/B3-mastery-moat.md`
- `.planning/packets/2026-06-02/learn-army/B4-adaptive-personalization.md`
- `.planning/packets/2026-06-02/learn-army/B5-new-lesson-content.md`
- `.planning/packets/2026-06-02/learn-army/C1-dj-pedagogy.md`
- `.planning/packets/2026-06-02/learn-army/C2-competitive-market.md`
- `.planning/packets/2026-06-02/learn-army/C3-monetization.md`
- `.planning/packets/2026-06-02/learn-army/C4-honesty-moat.md`
- `.planning/packets/2026-06-02/learn-army/D1-build-roadmap.md`
- `.planning/packets/2026-06-02/learn-army/D2-risks-failuremodes.md`
- `.planning/packets/2026-06-02/learn-army/D3-graveyard-recovery.md`

Reason:

- These are Claude/read-only workflow planning artifacts for the Learn
  re-architecture lane. Keep them out of source packages until Codex routes a
  specific Learn implementation or docs package from them.

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

## Hold Lane - Mixxx Source Scratch

Suggested commit if/when selected: none, scratch only

Hold:

- `_mixxx_probe.txt`
- `_mx_grep.txt`
- `.mixxx-tmp-loop/bpmcontrol.cpp`
- `.mixxx-tmp-loop/bpmcontrol.h`
- `.mixxx-tmp-loop/clockcontrol.cpp`
- `.mixxx-tmp-loop/clockcontrol.h`
- `.mixxx-tmp-loop/cuecontrol.cpp`
- `.mixxx-tmp-loop/cuecontrol.h`
- `.mixxx-tmp-loop/enginecontrol.cpp`
- `.mixxx-tmp-loop/enginecontrol.h`
- `.mixxx-tmp-loop/keycontrol.cpp`
- `.mixxx-tmp-loop/keycontrol.h`
- `.mixxx-tmp-loop/loopingcontrol.cpp`
- `.mixxx-tmp-loop/loopingcontrol.h`
- `.mixxx-tmp-loop/quantizecontrol.cpp`
- `.mixxx-tmp-loop/quantizecontrol.h`
- `.mixxx-tmp-loop/ratecontrol.cpp`
- `.mixxx-tmp-loop/ratecontrol.h`
- `.mixxx-tmp-loop/vinylcontrolcontrol.cpp`
- `.mixxx-tmp-loop/vinylcontrolcontrol.h`
- `.mixxx-tmp/loopingcontrol.cpp`
- `.mixxx-tmp/loopingcontrol.h`

Reason:

- These are local Mixxx reverse-engineering scratch extracts. They may be useful
  for understanding loop/rate/cue control behavior, but they are not vibemix
  source and must not be staged into product or docs packages by accident.

Remaining gate:

- If a Mixxx integration package needs them, distill the relevant findings into a
  cited research note or implementation spec first, then delete or ignore the
  scratch tree separately.

## Package 16 - Octave-Aware BPM Compatibility

Suggested commit: `fix(library): accept half-time bpm matches`

Include:

- `src/vibemix/intel/transition_scorer.py`
- `src/vibemix/library/next_suggestion.py`
- `src/vibemix/library/sequencer.py`
- `src/vibemix/library/track_relation.py`
- `tests/intel/test_transition_scorer.py`
- `tests/library/test_next_suggestion.py`
- `tests/library/test_sequencer.py`
- `tests/library/test_track_relation.py`

Keep out:

- All DROP-call speech/timing hunks in `src/vibemix/runtime/coach.py`,
  `src/vibemix/state/drop_predict.py`, and `src/vibemix/state/event_detector.py`.
- The controller-weighted deck-audio HOLD lane in `src/vibemix/__main__.py`,
  `src/vibemix/audio/*`, `src/vibemix/midi/*`, and their tests.
- Mixxx scratch files under `.mixxx-tmp-loop/`; this package consumes the
  distilled BPM-folding finding only.

Reason:

- The recovered Mixxx/goldmine research called out a concrete DJ-logic bug:
  half/double-time BPM pairs such as 87↔174 or 80↔160 were treated as large
  tempo jumps. That makes psytrance/hi-tempo libraries look less mixable than a
  working DJ would hear them.
- This is a pure deterministic library/intel slice. It changes tempo
  compatibility math for track relations, transition scoring, Viber/set
  sequencing, and next-suggestion filtering; it does not change live speech,
  event timing, controller capture, or packaging.

Proof:

- `uv run pytest -q tests/intel/test_transition_scorer.py tests/library/test_track_relation.py tests/library/test_sequencer.py tests/library/test_next_suggestion.py`
- `uv run ruff check src/vibemix/intel/transition_scorer.py src/vibemix/library/track_relation.py src/vibemix/library/sequencer.py src/vibemix/library/next_suggestion.py tests/intel/test_transition_scorer.py tests/library/test_track_relation.py tests/library/test_sequencer.py tests/library/test_next_suggestion.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 17 - Viber Set Novelty Dial

Suggested commit: `feat(library): expose sequence novelty dial`

Include:

- `src/vibemix/library/toolset.py`
- `src/vibemix/library/mcp_server.py`
- `src/vibemix/library/codex_curate.py`
- `tests/library/test_setprep_tools.py`

Keep out:

- `src/vibemix/library/sequencer.py` behavior changes beyond using its existing
  `surprise`/`gamma` input.
- Live speech, DROP, deck-audio/controller, and packaging files.

Reason:

- The recovered goldmine flagged that the sequencer already has a default-off
  surprise/novelty term, but no Viber-facing caller. This package exposes a
  bounded `novelty` value on `sequence_set` so "deep cuts" and "surprise me"
  requests can nudge toward lower-similarity tracks from the already-issued
  discovery pool.
- Grounding stays intact: the novelty signal is derived only from
  `search_vibe`/`discover_pool` similarity/confidence for track ids already in
  the per-run seen set. It cannot introduce a new track id and it does not
  change set export validation.

Proof:

- `uv run pytest -q tests/library/test_setprep_tools.py`
- `uv run ruff check src/vibemix/library/toolset.py src/vibemix/library/mcp_server.py src/vibemix/library/codex_curate.py tests/library/test_setprep_tools.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 18 - ANLZ BeatGrid Metadata Bridge

Suggested commit: `feat(audio): build beatgrid from rekordbox anlz metadata`

Include:

- `src/vibemix/audio/grid.py`
- `tests/audio/test_grid.py`

Keep out:

- Live beatmatch producer work (`BEATMATCH_GRADED`) and any change that flips
  beatmatching back to live-creditable.
- Dirty deck-audio/controller-weighted capture files under the deck context
  hold lane.
- DROP-call speech/timing files and runtime co-host speech surfaces.

Reason:

- The recovered Mixxx/goldmine research flagged `BeatGrid.from_anlz()` as a
  small but absent metadata shortcut. Rekordbox ANLZ already carries beat
  marker times and beat-in-bar labels; this bridge lets the existing constant
  `BeatGrid` phase oracle anchor to the first known downbeat instead of forcing
  future beatmatch/cue-placement work to rediscover timing from audio.
- This is a pure deterministic audio helper. It creates no live producer, emits
  no event, changes no spoken output, and makes no runtime/controller claim.

Proof:

- `uv run pytest -q tests/audio/test_grid.py tests/library/test_anlz_ingest.py tests/learn/test_beatmatch_judge.py tests/learn/test_judge_credits_beatmatch.py`
- `uv run ruff check src/vibemix/audio/grid.py tests/audio/test_grid.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Hold Lane - Cue Export Folder Bridge

Suggested commit if/when selected: `feat(library): add folder cue export bridge`

Hold:

- `src/vibemix/__main__.py`
- `src/vibemix/library/cue_folder.py`
- `tests/library/test_cue_folder_cli.py`
- `tests/library/test_cue_folder.py`

Reason:

- These files appeared from the cue-export research lane as an implementation
  slice, not as part of the already mapped auto-cue/pill/Viber package.
- Keep this bridge separate from Package 4 until the CLI/export integration,
  Rekordbox XML behavior, and staging boundary are reviewed together.
- The nearby Singularity cue-export briefs can explain intent, but they are
  research inputs. They do not make these runtime/library files shippable on
  their own.
- Codex added the narrow `library cue <folder>` CLI surface for this existing
  engine: default additive Rekordbox XML export, optional M3U8 export, and
  explicit `--write-tags` Serato Markers2 mutation. `src/vibemix/__main__.py`
  is a shared file; only the `library cue` parser/handler hunks belong here.

Proof already run:

- `uv run pytest -q tests/library/test_cue_folder_cli.py tests/library/test_cue_folder.py tests/library/test_export_serato.py`
  passed: 29 tests.
- `uv run ruff check src/vibemix/__main__.py tests/library/test_cue_folder_cli.py src/vibemix/library/cue_folder.py tests/library/test_cue_folder.py`
  passed.
- `uv run python -m vibemix library cue --help` showed the `cue` subcommand and
  its export/tagging flags.

Remaining gate:

- Before promotion, run the package checker and `git diff --check`; then do at
  least one real folder smoke against copied audio and import the XML/M3U8 or
  Serato-tagged files in the target DJ app. Do not claim full Rekordbox/Serato
  compatibility from unit tests alone.

### Cue Export App Surface - selected 2026-06-01

Suggested commit if/when selected: `feat(library-ui): expose folder cue export`

Include:

- `tauri/src-tauri/src/library_cmds.rs`
- `tauri/src-tauri/src/main.rs`
- `tauri/ui/library.html`
- `tauri/ui/src/library/api.ts`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/library.css`
- `tauri/ui/src/library/state-machine.ts`
- `tauri/ui/src/mock-transfer/contract.ts`
- `tauri/ui/src/library/api.test.ts`
- `tauri/ui/src/library/build.test.ts`
- `tauri/ui/src/library/state-machine.test.ts`

Keep out:

- `src/vibemix/runtime/coach.py` and all DROP-call speech/timing hunks.
- `src/vibemix/audio/*`, `src/vibemix/midi/*`, and deck-audio hold-lane tests.
- Serato file-tag mutation from the GUI. The app surface must call only the
  export-safe `library cue <folder> --export ... --json` path and must never
  pass `--write-tags`.

Reason:

- The Python cue engine and CLI already exist; the product gap is that the
  library window has no visible button/Tauri command for it. This slice exposes
  the existing engine through the same direct Tauri invoke pattern as search,
  build-set, chat, models, and folder ingest.
- The GUI claim is intentionally narrow: "export written" with returned file
  paths and counts. It does not claim that Rekordbox, Mixxx, or Serato rendered
  every cue pad until a real app import pass confirms it.

Proof for this app-surface slice:

- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/state-machine.test.ts src/library/build.test.ts`
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds`
- `uv run pytest -q tests/library/test_cue_folder_cli.py tests/library/test_cue_folder.py tests/library/test_export_serato.py`
- `npm --prefix tauri/ui run build`
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- Run one real folder smoke on copied audio, then import the emitted XML/M3U8 in
  the target DJ app before claiming visual pad compatibility.

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

## Hold Lane - Eval Judge Cross-Check Gate

Suggested commit if/when selected: `test(eval): add two-judge grounding rubric gate`

Hold:

- `scripts/eval/judge.py`
- `tests/eval/test_judge_pro_rubric.py`

Reason:

- This is real eval/Judge work, not a stub and not signing/package behavior.
  The evaluator imports the shared AI-message observability spine and defines the
  Pro/Flash rubric schemas, model calls, and min-aggregation policy for the
  grounding evaluation lane.
- Keep it separate from the R-SLOP runtime guard and from release packaging. It
  can become a quality gate only after its rubrics, model routing posture,
  cassettes/live-key expectations, and observability outputs are reviewed as one
  eval package.

Remaining gate:

- Run the focused eval tests for `tests/eval/test_judge_pro_rubric.py` and a
  model-router/no-hardcoded-model review before promoting this hold lane.
- Decide whether the live API-backed judge calls are cassette-gated, network
  gated, or deferred from default CI.

## Package 1C - Eval Session Report Automation

Suggested commit: `feat(eval): report cohost and viber repair queue`

Include:

- `src/vibemix/eval/__init__.py`
- `src/vibemix/eval/session_report.py`
- `src/vibemix/__main__.py`
- `scripts/release/check_cohost_viber_autopilot.sh`
- `scripts/release/check_cohost_viber_corpus_benchmark.sh`
- `tests/eval/test_cohost_viber_session_report.py`
- `tests/eval/test_check_cohost_viber_autopilot_sh.py`
- `tests/eval/test_check_cohost_viber_corpus_benchmark_sh.py`

Reason:

- These fresh files add a deterministic source-only
  `vibemix eval latest-session` command that reads recorded `events.jsonl` plus
  optional global Viber/Codex `ai_messages.jsonl` and emits a cohost/Viber repair
  queue. It is useful acceptance automation for the rebuild: it turns the
  observability spine into a concrete repair queue instead of another manual
  artifact crawl.
- Keep it separate from the eval-judge model gate above: this report calls no
  model, touches no audio hardware, and only inspects persisted product
  artifacts.
- The failure-corpus benchmark wrapper belongs here too: it refreshes saved
  cohost/Viber failures from current recordings, runs deterministic repair
  candidates, and intentionally keeps strict release mode red while captured
  failures remain.

Proof already run:

- `uv run python -m vibemix eval latest-session --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-161228" --no-viber --json`
  exited 0 and emitted schema `cohost_viber_automation_report_v1` with one
  live-coach `ai_message`, one thin-ack watch issue, and no blockers.
- `uv run pytest -q tests/eval/test_cohost_viber_session_report.py`
  passed: 5 tests.
- `uv run pytest -q tests/eval/test_check_cohost_viber_autopilot_sh.py`
  proves the release shell gate fails strict release mode and passes operator
  repair mode.
- `uv run ruff check src/vibemix/eval/__init__.py src/vibemix/eval/session_report.py tests/eval/test_cohost_viber_session_report.py tests/eval/test_check_cohost_viber_autopilot_sh.py`
  passed.

Codex refresh, 2026-05-31 21:30 +03:

- Classification: LAND as source-only acceptance automation, not as a product
  runtime feature or model-quality fix.
- `uv run pytest -q tests/eval/test_cohost_viber_session_report.py tests/eval/test_check_cohost_viber_autopilot_sh.py tests/eval/test_check_cohost_viber_corpus_benchmark_sh.py`
  passed: 16 tests on the current tree.
- `uv run pytest -q tests/eval/test_check_cohost_viber_corpus_benchmark_sh.py`
  passes the shell wrapper contract for strict release-blocking mode and
  operator repair mode.
- `uv run python -m vibemix eval latest-session --session-dir "$HOME/Library/Application Support/vibemix/recordings/20260531-161228" --no-viber --json`
  exited 0 with `ok: true`, no blocker/care issues, and two watch-only issues
  (`citation_zero_ack`, `no_deck_audio_parts`).
- `PYTHON="$PWD/.venv/bin/python" PYTHONPATH="$PWD/src" COHOST_VIBER_SESSION_DIR="$HOME/Library/Application Support/vibemix/recordings/20260531-161228" COHOST_VIBER_NO_VIBER=1 COHOST_VIBER_FAIL_ON=automation COHOST_VIBER_OUT_DIR=/tmp/vibemix-eval-1c-autopilot bash scripts/release/check_cohost_viber_autopilot.sh`
  passed with `status=clean gate_ok=True release_gate_ok=True blockers=0 care=0 watch=2`.
- The same wrapper with `COHOST_VIBER_FAIL_ON=release` also passed on that
  recording. The wrapper is invoked by `bash`; direct execution is not part of
  the current test contract while the untracked file lacks executable mode.
- `git diff --check -- src/vibemix/eval/session_report.py tests/eval/test_cohost_viber_session_report.py scripts/release/check_cohost_viber_autopilot.sh tests/eval/test_check_cohost_viber_autopilot_sh.py src/vibemix/__main__.py`
  passed.
- `CODEX_READY-eval-session-report-automation.md` refreshed in the Codex inbox
  with the current eight-file package list, autopilot proof, failure-corpus
  benchmark proof, and Package 8D spoken-fallback overlap.

Remaining gate:

- Before final acceptance, run `vibemix eval latest-session` against the final
  rebuilt app/source recordings and attach the report to the release verifier
  packet. A report with blocker issues is not automatically a command failure
  when emitted as evidence, but it is a product-acceptance blocker until triaged.
- Stage `src/vibemix/__main__.py` by hunk; it also carries cue-folder, pricing,
  TTS, and deck-audio package work.

## Package 1D - FLX4 Live Context Release Gate

Suggested commit: `test(release): gate flx4 live context proof`

Include:

- `scripts/release/check_flx4_live_context.sh`
- `tests/eval/test_check_flx4_live_context_sh.py`

Reason:

- This is the hardware-in-the-loop companion to Package 1C's source-only repair
  queue. It verifies that the DDJ-FLX4 is visible as a MIDI port, visible as a
  macOS audio device, and that the running Vibemix socket can emit the grounded
  live-context packet Viber would receive.
- A plugged controller alone is not enough. The gate must see hardware plus
  live socket proof, so it prevents future release notes from treating
  controller presence as product grounding.
- Keep it separate from Package 15 deck-audio routing code. Package 1D is a
  release proof harness; Package 15 is the actual desktop audio/controller
  runtime upgrade.

Current proof:

- `uv run pytest -q tests/eval/test_check_flx4_live_context_sh.py`
  passes the shell wrapper contract for a ready FLX4/live-context proof and for
  the missing-socket failure path.
- `uv run ruff check tests/eval/test_check_flx4_live_context_sh.py`
  passes.
- Live hardware pre-check after the DDJ-FLX4 was plugged back in:
  `uv run python scripts/sniff_controller.py --list` reported `DDJ-FLX4`, and
  `system_profiler SPAudioDataType` reported `DDJ-FLX4` as an audio input.
- `bash scripts/release/check_flx4_live_context.sh` correctly failed while no
  Vibemix socket was listening, with `diagnosis=live_socket_missing`,
  `midi_port=DDJ-FLX4`, `audio_device=True`, `live_ready=False`, and
  `proof=.planning/eval-runs/flx4-live-context/live_context_proof.json`.
- Codex latest signed-DMG attempt, 2026-06-01:
  `dist/fresh-20260601-latest/vibemix-0.0.1.dmg` was mounted, copied to
  `/tmp/vibemix-signed-install.Tp4lk7/vibemix.app`, launched, and reached
  `127.0.0.1:8765` from bundled sidecar PID `57523`. Then
  `COHOST_VIBER_FLX4_OUT_DIR=.planning/eval-runs/flx4-live-context-codex-latest-signed COHOST_VIBER_FLX4_WAIT_READY_S=5 COHOST_VIBER_FLX4_TIMEOUT_S=3 COHOST_VIBER_FLX4_FRAMES=180 COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S=3 bash scripts/release/check_flx4_live_context.sh`
  failed honestly with `midi_port=DDJ-FLX4`, `audio_device=True`,
  `live_ok=True`, `live_ready=False`, `diagnosis=missing_physical_proof`,
  `controller_connected=True`, `recent_moves=False`, `audio_observed=False`,
  `direct_midi_frames=0`, and
  `midi_motion_diag=no_direct_midi_motion_observed`. Durable packet:
  `.planning/packets/2026-06-01/CODEX_HOLD-flx4-live-acceptance-current.md`.

Remaining gate:

- Rerun `bash scripts/release/check_flx4_live_context.sh` against the current
  signed/copied app or current source while audible deck audio is playing and a
  FLX4 fader/knob/transport control is moved during the proof window. It is
  expected to fail if physical motion, audible audio, deck identity, or canary
  proof is missing.

## Package 1D2 - FLX4 B Jog Live Mapping

Suggested commit: `fix(midi): accept live flx4 b-jog cc34`

Include:

- `src/vibemix/midi/profiles/pioneer_ddj_flx4.json`
- `tests/midi/test_profile.py`
- `tests/midi/test_profile_flx4_golden.py`
- `tests/midi/test_flx4_synthetic_decode.py`

Reason:

- 2026-06-01 clean-HEAD source proof with DDJ-FLX4 connected captured real
  hardware motion via `scripts/sniff_controller.py --port FLX4 --seconds 20
  --mode poll`: 134 MIDI frames, unique CC `[34]`, unique note `[54]`.
- The product profile already accepted live-discovered jog ticks on CC33, but
  the captured B-deck jog stream emitted channel 1 / CC34 alongside the
  jog-touch note. Without this additive binding, the direct hardware probe sees
  the move while the app's live `midi_events` ribbon stays empty.
- This package does not claim deck identity, audio routing, beat quality, or
  move impact. It only maps the observed B-jog byte so future live proof windows
  can surface the physical jog move honestly.

Current proof:

- `uv run python scripts/sniff_controller.py --port FLX4 --seconds 20 --mode
  poll` in clean worktree `4bc30e66` wrote
  `.planning/eval-runs/flx4-live-context-clean-head-4bc30e66/direct_midi_probe.jsonl`
  with 134 frames, CC34, and note54.
- Focused unit gates must pass before landing: `uv run pytest -q
  tests/midi/test_profile.py tests/midi/test_profile_flx4_golden.py
  tests/midi/test_flx4_synthetic_decode.py tests/midi/test_state.py`.

## Package 1D3 - FLX4 No-MIDI-Traffic Diagnostic

Suggested commit: `fix(controller): surface missing flx4 midi traffic`

Include:

- `src/vibemix/midi/state.py`
- `src/vibemix/state/music_state.py`
- `src/vibemix/state/refresh.py`
- `src/vibemix/state/deck_poller.py`
- `src/vibemix/runtime/ws_bus.py`
- `tauri/ui/src/session/components/status-bar.ts`
- `tests/midi/test_flx4_synthetic_decode.py`
- `tests/state/test_refresh.py`
- `tests/state/test_deck_poller.py`
- `tests/runtime/test_ws_bus_deck_state.py`
- `tests/runtime/test_ws_bus_status_tick.py`
- `tauri/ui/tests/session/components.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Reason:

- A visible CoreMIDI port is not controller proof. On 2026-06-02, the live
  FLX4/Rekordbox rig had audible BlackHole audio and `DDJ-FLX4` visible as an
  input port, but both the running Vibemix session and direct
  `scripts/sniff_controller.py --port FLX4 --seconds 12 --mode callback`
  probes saw `frames: 0` while Kaan moved controls.
- The old surface collapsed this into `controller_connected=true` and generic
  "Open one channel" guidance. That made the app look confused: Sven could
  truthfully say "no controller moves" while the DJ was physically moving the
  FLX4. This package adds traffic counters and the explicit
  `connected_no_midi_traffic` diagnostic so Viber/Sven/setup UI can ask for
  the real next action: enable/reconnect FLX4 MIDI output before trusting deck
  moves.

Proof to run:

- `uv run pytest -q tests/midi/test_flx4_synthetic_decode.py tests/state/test_refresh.py::test_tick_writes_recent_moves tests/state/test_refresh.py::test_tick_distinguishes_connected_controller_with_no_midi_traffic tests/state/test_deck_poller.py::test_source_status_distinguishes_visible_controller_with_no_midi_traffic tests/runtime/test_ws_bus_deck_state.py::test_payload_includes_bounded_deck_mixer_posture tests/runtime/test_ws_bus_deck_state.py::test_course3_operator_action_names_visible_controller_with_no_midi_traffic tests/runtime/test_ws_bus_status_tick.py`
- `npm --prefix tauri/ui test -- tests/session/components.spec.ts`
- `uv run pytest -q tests/midi tests/state/test_refresh.py tests/state/test_deck_poller.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_ws_bus_snapshot.py tests/runtime/test_live_course3_lens_probe.py tests/library/test_live_context_cli.py`
- `uv run ruff check src/vibemix/midi/state.py src/vibemix/state/music_state.py src/vibemix/state/refresh.py src/vibemix/state/deck_poller.py src/vibemix/runtime/ws_bus.py tests/midi/test_flx4_synthetic_decode.py tests/state/test_refresh.py tests/state/test_deck_poller.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_ws_bus_status_tick.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/midi/state.py src/vibemix/state/music_state.py src/vibemix/state/refresh.py src/vibemix/state/deck_poller.py src/vibemix/runtime/ws_bus.py tauri/ui/src/session/components/status-bar.ts tests/midi/test_flx4_synthetic_decode.py tests/state/test_refresh.py tests/state/test_deck_poller.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_ws_bus_status_tick.py tauri/ui/tests/session/components.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- This is source-level readiness guidance. After the DJ-side FLX4/Rekordbox MIDI
  setup is corrected, rerun the live proof and require the status to advance
  from `connected_no_midi_traffic` to `active` with real `midi_events` before
  claiming controller moves are grounded.

## Hold Lane - FLX4 Live Context Proof Artifacts

Suggested commit: none by default; attach to verifier packet if needed.

Hold:

- `.planning/eval-runs/flx4-live-context/audio_devices.stderr.log`
- `.planning/eval-runs/flx4-live-context/audio_devices.txt`
- `.planning/eval-runs/flx4-live-context/live_context_proof.json`
- `.planning/eval-runs/flx4-live-context/live_context_stderr.log`
- `.planning/eval-runs/flx4-live-context/live_context_stdout.json`
- `.planning/eval-runs/flx4-live-context/midi_ports.stderr.log`
- `.planning/eval-runs/flx4-live-context/midi_ports.txt`
- `.planning/eval-runs/flx4-live-context-codex-latest-signed/`

Reason:

- These are generated evidence artifacts from the real
  `bash scripts/release/check_flx4_live_context.sh` run. They prove the
  DDJ-FLX4 was visible as MIDI/audio while the live-context socket proof failed
  with `diagnosis=live_socket_missing`.
- Keep them out of source packages by default. If a reviewer wants the raw
  proof, attach or archive them explicitly with the verifier packet rather than
  silently staging generated run output.

## Package 1E - Cohost/Viber Release Matrix Wrapper

Suggested commit: `test(release): compose cohost viber release gates`

Include:

- `scripts/release/check_cohost_viber_matrix.sh`
- `tests/eval/test_check_cohost_viber_matrix_sh.py`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-viber-release-matrix-wrapper.md`

Reason:

- This is the one-command coordinator for the current cohost/Viber acceptance
  gates: latest-session autopilot, refreshed failure-corpus benchmark, and
  optional/auto/required DDJ-FLX4 live-context proof.
- Keep it separate from Package 1C and Package 1D if reviewers want the small
  wrappers staged independently. Package 1E owns composition only; it does not
  define the underlying report, corpus benchmark, or FLX4 proof semantics.

Current proof:

- `bash -n scripts/release/check_cohost_viber_matrix.sh` passes.
- `COHOST_VIBER_MATRIX_MODE=automation COHOST_VIBER_MATRIX_FLX4=skip COHOST_VIBER_MATRIX_OUT_DIR=/tmp/vibemix-cohost-viber-matrix-codex PYTHON="$PWD/.venv/bin/python" PYTHONPATH="$PWD/src" bash scripts/release/check_cohost_viber_matrix.sh`
  passed; it skips hardware proof and writes artifacts outside the repo.
- `uv run pytest -q tests/eval/test_check_cohost_viber_matrix_sh.py`
  passed: 20 tests.
- `uv run ruff check tests/eval/test_check_cohost_viber_matrix_sh.py` passed.

Remaining gate:

- Release mode must be rerun after the final app/source pass, with
  `COHOST_VIBER_MATRIX_FLX4=required` when the DDJ-FLX4 rig is connected and
  the live socket is up.

## Package 1F - Cohost/Viber Live Rehearsal Wrapper

Suggested commit: `test(release): add cohost viber live rehearsal wrapper`

Include:

- `scripts/release/check_cohost_viber_live_rehearsal.sh`
- `tests/eval/test_check_cohost_viber_live_rehearsal_sh.py`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-viber-live-rehearsal-wrapper.md`

Reason:

- This is the start-or-use-live wrapper around the cohost/Viber release matrix.
  It can launch the Vibemix live sidecar when needed, wait for
  `ws://127.0.0.1:8765`, run the matrix, preserve artifacts, and stop only the
  live process it started.
- Treat this as the benching Codex/Sven rehearsal lane. It composes existing
  acceptance gates and process lifecycle behavior; it does not change Viber,
  Sven, or set-generation runtime semantics.

Current proof:

- `bash -n scripts/release/check_cohost_viber_live_rehearsal.sh` passes.
- `COHOST_VIBER_REHEARSAL_START_LIVE=never COHOST_VIBER_REHEARSAL_OUT_DIR=/tmp/vibemix-cohost-viber-live-rehearsal-codex bash scripts/release/check_cohost_viber_live_rehearsal.sh`
  is the safe no-start smoke path; with no socket listening it must fail before
  launching a sidecar.
- `uv run pytest -q tests/eval/test_check_cohost_viber_live_rehearsal_sh.py`
  passed: 21 tests.
- `uv run ruff check tests/eval/test_check_cohost_viber_live_rehearsal_sh.py`
  passed.
- Safe no-start smoke on the current machine failed as expected with
  `FAIL check_cohost_viber_live_rehearsal: live socket missing and
  COHOST_VIBER_REHEARSAL_START_LIVE=never`; `lsof -nP -iTCP:8765 -sTCP:LISTEN`
  found no listener afterward.

Remaining gate:

- Run the wrapper for real only when the rig is ready: DDJ-FLX4 connected,
  audio routed, and either an existing live socket or permission to launch the
  current source sidecar.

## Package 1G - Cohost/Viber Runtime Canaries Wrapper

Suggested commit: `test(release): add cohost viber runtime canaries`

Include:

- `scripts/release/check_cohost_viber_runtime_canaries.sh`
- `tests/eval/test_check_cohost_viber_runtime_canaries_sh.py`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-viber-runtime-canaries-wrapper.md`

Reason:

- This is the focused source-side canary wrapper for the cohost/Viber
  anti-hallucination invariants. It pins the exact tests that must stay green
  before the broader matrix trusts a model run or captured session artifact.
- It covers manual silence, manual audio still reaching the model, audio
  listener-read allowance, audio/control causality stripping, hidden-source
  stripping, guard-fallback silence, repeated ack-only silence, and
  manual-silence report acceptance.
- Keep this as test/release automation. It does not change runtime semantics and
  does not replace the later live DDJ/BlackHole proof.

Proof already run:

- `bash -n scripts/release/check_cohost_viber_runtime_canaries.sh`
  passed.
- `uv run pytest -q tests/eval/test_check_cohost_viber_runtime_canaries_sh.py`
  passed: 2 tests.
- `uv run ruff check tests/eval/test_check_cohost_viber_runtime_canaries_sh.py`
  passed.
- `COHOST_VIBER_RUNTIME_CANARY_OUT_DIR=/tmp/vibemix-runtime-canaries-current-codex PYTHON="$PWD/.venv/bin/python" PYTHONPATH="$PWD/src" bash scripts/release/check_cohost_viber_runtime_canaries.sh`
  passed with `ok=True canaries=8 exercised=8 passed=8 failed=0 missing=0`.
- `.planning/packets/2026-06-01/CODEX_READY-cohost-viber-runtime-canaries-wrapper.md`
  records the current proof.

Remaining gate:

- Run the broader matrix/rehearsal lane after these source canaries are green,
  then rerun the final live proof against the settled source/package.

## Hold Lane - Cohost/Viber Eval Run Archives

Suggested commit: none by default; attach selectively to verifier packets.

Hold:

- `.planning/eval-runs/`

Reason:

- These are generated cohost/Viber matrix, live rehearsal, runtime canary,
  FLX4, autopilot, failure-corpus, and reprompt-pack artifacts. They are
  valuable evidence but not source code and not a default package payload.
- The checker assigns this directory as a proof archive so thousands of
  generated JSON/log files cannot silently go unclassified or flood the package
  checklist. Promote only narrow artifacts to a verifier packet when a package
  explicitly needs them.

Remaining gate:

- Before any commit, decide whether the run archive should stay untracked,
  be compressed/attached outside git, or be reduced to selected summary files.
  Do not stage the whole archive by accident.

## P0 Gap - Viber Library Freshness Watcher

Status: REQUIRED PRODUCT CAPABILITY / NO DIRTY CODE PATH YET

### Event-driven source slice - selected 2026-06-01

Suggested commit: `fix(library): accelerate freshness watcher with file events`

Include:

- `src/vibemix/library/staleness.py`
- `tests/library/test_staleness.py`
- `pyproject.toml`
- `uv.lock`
- `vibemix-core.macos.spec`
- `vibemix-core.windows.spec`
- `tests/sidecar/test_build_sidecar_rename.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Any automatic re-ingest/re-embed daemon. This slice marks/announces staleness
  fast; it does not mutate the library index without the user's refresh action.
- Viber answer-copy changes or spoken co-host changes.
- Packaged-runtime claim until a frozen sidecar smoke proves the native watcher
  extension loads from the built bundle.

Reason:

- Package 5E already added a source-aware live freshness pulse, but it waits for
  the bounded poll interval. This slice keeps that poll fallback and adds a
  first-class `watchfiles` path so changes to `library.pkl` or the source
  Rekordbox XML trigger an immediate re-check.
- `watchfiles` was already present transitively through LiveKit; this slice
  declares it directly because `staleness.py` now imports it, and makes the
  PyInstaller specs collect the native watcher package explicitly.

Proof for this source slice:

- `uv run pytest -q tests/library/test_staleness.py tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_collect_local_ai_runtime`
- `uv run ruff check src/vibemix/library/staleness.py tests/library/test_staleness.py tests/sidecar/test_build_sidecar_rename.py`
- `git diff --check -- src/vibemix/library/staleness.py tests/library/test_staleness.py pyproject.toml uv.lock vibemix-core.macos.spec vibemix-core.windows.spec tests/sidecar/test_build_sidecar_rename.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- Frozen sidecar smoke that the `watchfiles` native extension loads in the
  packaged app. Source tests prove fallback/event behavior, not packaged loading.

Requirement:

- Viber/set generation must have a first-class library freshness watcher. It
  should monitor the resolved Rekordbox `collection.xml`, selected music
  folders, generated playlist/set artifacts, cue/export outputs, and the local
  library cache/embedding freshness markers that Viber relies on.
- On change, the app should mark the library index stale, show a truthful
  in-app status, and trigger or offer an incremental re-ingest/re-embed path
  before Viber answers set-generation questions from stale context.

Why this is P0:

- `discover_pool`, `sequence_set`, `create_playlist`, `smart_hot_cues`, Viber
  chat, compact pill handoff, and export receipts are only as good as the
  library/cue/embedding state they read. A manual ingest-only model makes set
  generation silently stale after the DJ edits crates, exports Rekordbox XML,
  adds tracks, changes cues, or moves files.
- Current source has MIDI hot-plug watching and library staleness nudges, but
  the quick source map did not find a product-owned library/catalog file watcher
  that keeps Viber's set-prep context fresh automatically.

Initial evidence:

- `src/vibemix/library/sources/rekordbox.py` resolves and parses
  `collection.xml`, but it is read-only detection/iteration, not a watcher.
- `src/vibemix/library/ingest.py` is a resumable ingest orchestrator with
  content-hash CLAP caching and `library.pkl` writes, but it runs when invoked;
  it is not a long-lived freshness daemon.
- `src/vibemix/__main__.py` registers `~/.cache/vibemix/library.pkl` at boot
  and emits a staleness nudge, but does not keep Viber's library context live as
  files change.
- `uv.lock` already contains `watchfiles`, so this likely does not require a
  new dependency if promoted.

Acceptance sketch:

- A changed `collection.xml` or watched music folder marks library state stale
  within a bounded interval and surfaces that status to Viber/UI.
- Viber refuses or clearly qualifies set-generation answers while index state
  is stale, instead of pretending the old pool is current.
- Incremental ingest/re-embed is debounced, cancellable, logged to
  AI/lifecycle observability, and never blocks live co-host audio.
- Tests cover XML mtime/content changes, moved/missing tracks, cue changes,
  debounce, stale status propagation, and Viber refusing stale set-generation
  claims.

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
  passed: 37 tests.
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

Codex refresh, 2026-05-31 21:35 +03:

- Classification: LAND as backend Earned Wall refresh emission, with live UI
  repaint proof still required before product acceptance.
- Current source path verified: cited event enters `coach_loop`,
  `_credit_live_skill_demo(...)` advances persisted `LearnProgress.skills`,
  `_emit_earned_wall_refresh(...)` emits `ipc.learn.progress_state`, and the rare
  Mastered vocal uses fixed `session.say(..., add_to_chat_ctx=False)` rather
  than LLM generation.
- `uv run pytest -q tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py`
  passed: 41 tests.
- `uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py`
  passed: 37 tests.
- `uv run ruff check src/vibemix/runtime/coach.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py`
  passed.
- `CODEX_READY-earned-wall-live-refresh.md` was added to the Codex inbox.

Codex refresh, 2026-06-01:

- Classification remains LAND as backend Earned Wall refresh emission. This
  refresh recreates the lost `/tmp` packet in the durable archive at
  `.planning/packets/2026-06-01/CODEX_READY-earned-wall-live-refresh.md`.
- Current source path re-verified: cited coach events enter
  `_credit_live_skill_demo(...)`, persist Learn progress, emit
  `ipc.learn.progress_state` through `_emit_earned_wall_refresh(...)`, and route
  the rare Mastered unlock through fixed `session.say(..., add_to_chat_ctx=False)`
  rather than an LLM turn.
- `uv run pytest -q tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py`
  passed: 41 tests.
- `uv run pytest -q tests/learn/test_judge_credits_beatmatch.py tests/learn/test_creditability_drift.py tests/learn/test_skill_wall_what_remains.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py`
  passed: 37 tests.
- `uv run ruff check src/vibemix/runtime/coach.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py`
  passed.
- `git diff --check -- src/vibemix/runtime/coach.py tests/runtime/test_coach_skill_credit.py tests/runtime/test_coach_progress_emit.py tests/learn/test_mastered_vocal_fires_once.py`
  passed with no output.
- Boundary unchanged: this is backend refresh proof only until a live desktop
  artifact shows the Earned Wall repainting from a real cited runtime credit.

## Package 10 - Live Stack Cost And Pricing Model

Suggested commit: `feat(library-cost): add live stack budget model`

Include:

- `src/vibemix/library/cost.py`
- `src/vibemix/library/pricing.py`
- `src/vibemix/library/budget.py`
- `src/vibemix/__main__.py`
- `src/vibemix/llm/_router_config.py`
- `tests/library/test_budget.py`
- `tests/library/test_cost.py`
- `tests/library/test_pricing.py`
- `tests/library/test_session_meter.py`
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

Codex refresh, 2026-05-31 21:50 +03:

- Classification: LAND as internal reproducible live-stack cost model. External
  billing/current-pricing claims remain gated.
- Current source flow verified: pricing rows carry source/date/verified flags;
  router paths resolve through `model_router`; `library budget --stack live`
  emits human and JSON reports; `sonic-3` remains visibly `LEGACY_DERIVED` /
  `UNVERIFIED`.
- `uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/llm/test_model_router.py`
  passed: 37 tests.
- `uv run pytest -q tests/e2e/test_phase_41_latency_stack_integration.py tests/repo/test_live_spike_scaffold.py tests/llm/test_model_router.py tests/library/test_pricing.py tests/library/test_cost.py`
  passed: 62 tests.
- `bash scripts/release/check_no_hardcoded_model.sh`
  passed with no hardcoded Gemini model literals outside
  `src/vibemix/llm/_router_config.py`.
- `uv run ruff check src/vibemix/library/pricing.py src/vibemix/library/cost.py tests/library/test_pricing.py tests/library/test_cost.py`
  passed.
- `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3`
  exited 0 and printed `TOTAL 0.4857 EUR/session, 9.74 EUR/DJ-month, 97,374
  fleet EUR/mo`, dominant leg `TTS`, and `Cartesia Sonic 97,374 ! UNVERIFIED`.
- The JSON form wrote `/tmp/vibemix-live-budget-p10.json`, parsed with
  `uv run python -m json.tool`, and preserved `"verified": false` for the
  Cartesia Sonic sensitivity row.
- `CODEX_READY-live-stack-cost-pricing-model.md` added to the Codex inbox.

Codex refresh, 2026-06-01:

- Classification remains LAND as an internal reproducible cost model, not
  external pricing copy. The lost `/tmp` packet was recreated at
  `.planning/packets/2026-06-01/CODEX_READY-live-stack-cost-pricing-model.md`.
- Current source path re-verified: `PriceRow` carries source/date/verified
  metadata; Gemini pricing rows resolve through `model_router`; live budget
  composes brain/listen/TTS/Viber/LiveKit legs; CLI human and JSON outputs echo
  assumptions and preserve the Cartesia `! UNVERIFIED` flag.
- Official-source spot-check refreshed during this pass: Gemini 3.5 Flash,
  Gemini 3.1 Flash TTS, and DeepSeek V4 Pro matched the table; Cartesia public
  pricing still exposes plans/credits/minutes rather than a clean Sonic
  per-character SKU, supporting `sonic-3.verified = false`.
- `uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/llm/test_model_router.py`
  passed: 37 tests.
- `uv run pytest -q tests/e2e/test_phase_41_latency_stack_integration.py tests/repo/test_live_spike_scaffold.py tests/llm/test_model_router.py tests/library/test_pricing.py tests/library/test_cost.py`
  passed: 62 tests.
- `bash scripts/release/check_no_hardcoded_model.sh` passed.
- `uv run ruff check src/vibemix/library/pricing.py src/vibemix/library/cost.py tests/library/test_pricing.py tests/library/test_cost.py`
  passed.
- `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3`
  exited 0 and printed `TOTAL 0.4857 EUR/session, 9.74 EUR/DJ-month, 97,374
  fleet EUR/mo`, dominant leg `TTS`, and `Cartesia Sonic 97,374 ! UNVERIFIED`.
- The JSON form wrote `/tmp/vibemix-live-budget-p10-codex.json`, parsed with
  `uv run python -m json.tool`, and preserved `verified: false` for Cartesia
  Sonic.
- `git diff --check` over the Package 10 file set passed with no output.

Codex refresh, 2026-06-01 MOSS cost rebaseline:

- Classification remains LAND as an internal reproducible cost model. This
  refresh aligns the default live stack with the accepted MOSS-only voice
  policy: production TTS is now `moss-local` with an explicit zero provider
  bill; Gemini/Eleven/Hume/Cartesia/OpenAI TTS rows remain only as sensitivity
  what-ifs.
- `uv run pytest -q tests/library/test_cost.py tests/library/test_pricing.py tests/library/test_session_meter.py tests/llm/test_model_router.py tests/e2e/test_phase_41_latency_stack_integration.py`
  passed: 68 tests.
- `uv run ruff check src/vibemix/library/cost.py src/vibemix/library/pricing.py src/vibemix/library/budget.py tests/library/test_cost.py tests/library/test_pricing.py tests/library/test_session_meter.py`
  passed.
- `bash scripts/release/check_no_hardcoded_model.sh`
  passed.
- `uv run python -m vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts moss-local`
  exited 0 and printed `TOTAL 0.0485 EUR/session, 0.99 EUR/DJ-month,
  9,917 fleet EUR/mo`, dominant leg `LISTEN`, with the `tts` leg at `0`.
- The JSON form parsed successfully and preserved the sensitivity spread:
  `Local MOSS (production)` at 9,917 fleet EUR/mo, `Gemini value TTS` at
  54,371, `Gemini premium TTS` at 98,825, and `Cartesia Sonic` still marked
  `verified: false`.
- `git diff --check -- src/vibemix/library/cost.py src/vibemix/library/pricing.py src/vibemix/library/budget.py tests/library/test_cost.py tests/library/test_pricing.py tests/library/test_session_meter.py`
  passed with no output.
- Follow-up, 2026-06-02: `tests/library/test_budget.py` is included in Package
  10 because it owns the legacy Gemini-embedding what-if gate. The stale strict
  xfail was converted into a passing truth gate: legacy cloud embedding remains
  over the €50 ceiling, while production library embeddings are local CLAP and
  the current live-stack bill is covered by `tests/library/test_cost.py`.

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

Codex refresh, 2026-05-31 21:56 +03:

- Classification: LAND as selected launch collateral/assets, not as product
  release approval.
- Asset type proof: selected collateral contains the talking builder script,
  three prepared HTML pitch/brief files, one PDF, one MP3, eight canonical
  1440x900 PNG screenshots, and three selected close-up PNGs.
- `uv run ruff check docs/launch/.build_talking.py` passed.
- `uv run python docs/launch/.build_talking.py --out /tmp/vibemix-konusan.html --check`
  passed.
- `git check-ignore -v docs/launch/.vibemix-konusan.html docs/launch/.partner-capabilities.html docs/launch/.partner-capabilities-short.html`
  confirms generated preview HTML stays ignored.
- `git diff --check --` the launch collateral/docs slice passed.
- The public claim boundary is now tied to Package 0I wording: launch
  collateral may say macOS is release-gated, but must not claim a fresh
  signed/notarized package exists until Package 13B/13C proof lands.

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

Codex refresh, 2026-06-01:

- Classification changed to HOLD as current launch collateral. Mechanics pass,
  but the public/partner copy is not product-honest enough for the rebuild.
- Durable hold packet:
  `.planning/packets/2026-06-01/CODEX_HOLD-launch-collateral.md`.
- What passed: `uv run ruff check docs/launch/.build_talking.py`; generated
  talking-page build+check to `/tmp/vibemix-konusan-codex.html`; generated
  preview HTML ignore checks; media/dimension checks for PDF, MP3, eight
  1440x900 canonical PNGs, and three selected detail crops; `git diff --check`
  for the Package 11 file set.
- One small overclaim was patched in `docs/launch/.vibemix-pitch-en.html`: the
  controller-maker pitch now says partner bundles can carry "coach included"
  once release gates pass, instead of saying every sale already ships with it.
- HOLD blockers: `docs/launch/.partner-capabilities-tr-short.html` still claims
  macOS signed/notarized today, Windows stable soon, one-click Rekordbox XML
  export preserving cue/beatgrid, and a >=95% hallucination gate; the pitch HTML
  still says "Free/Open source/running on Mac today" and "everything stays on
  your machine, never cloud"; Learn and cue/export claims outrun current product
  proof.
- Visual/copy blocker: the pitch HTML still uses old amber-era styling, thick
  side-stripe card borders, and em-dash-heavy copy, conflicting with the current
  tozpembe product/design context.
- Recommended split: screenshots/media/README may become a smaller archive
  package later, but partner/public launch copy needs a truth rewrite against
  Product Reality, Package 0I posture, Viber correction, Learn boundaries, and
  Package 13B/13C release gates.

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

## Package 16 - Frontend Shell Settings Proof

Suggested commit: `fix(ui-shell): keep settings drawer navigation stable`

Include:

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

Packaging decision:

- This is production shell/settings behavior and shell visual polish plus proof
  collateral. It should not be folded into the design-only Premium Enterprise
  Visual Audit and should not ride with IPC/settings schema work unless the
  package deliberately proves both layers.
- The code diff keeps settings navigation synchronized with drawer open/close
  state, stabilizes settings-group layout, changes session picker/rocker
  styling, and changes shell chrome/sidebar CSS. It does not touch speech,
  runtime audio, IPC schema, or backend settings persistence.

Current evidence, 2026-06-01:

- `npm --prefix tauri/ui test -- tests/settings/drawer.spec.ts tests/session/components.spec.ts tests/session/router-teardown.spec.ts`
  passed: 73 tests.
- `npm --prefix tauri/ui test -- tests/session/integration.spec.ts tests/session/render-loop-actions.spec.ts tests/settings/drawer.spec.ts tests/session/components.spec.ts`
  passed: 88 tests.
- `npm --prefix tauri/ui run build` passed: TypeScript check plus Vite build.
- `git diff --check -- tauri/ui/src/settings/components/group.ts tauri/ui/src/session/components/picker.ts tauri/ui/src/session/components/rocker.ts tauri/ui/src/shell/app.ts tauri/ui/src/shell/shell.css docs/design/screenshots/2026-05-31-frontend-proof`
  passed.
- Clean detached replay at `/tmp/vibemix-ui-shell-clean.vJdvjF` passed the same
  88-test UI gate, the 73-test drawer/router/component gate, `npm --prefix
  tauri/ui run build`, `git diff --check`, and
  `uv run python scripts/check_dirty_package_plan.py --strict-assignments
  --summary`.
- Visual proof artifacts are kept with the slice under
  `docs/design/screenshots/2026-05-31-frontend-proof/`. The current after-fix
  screenshot is nonblank at 1440x900, the proof JSON records zero clipped
  settings groups, and the settings-close/deck-nav actionability check closes
  the drawer instead of trapping the shell.

Remaining gate:

- Packaged-app visual proof is still separate release evidence. This package
  proves source UI behavior/build plus captured screenshot artifacts.

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

Codex refresh, 2026-05-31 22:05 +03:

- Classification: LAND as runtime memory/CLAP readiness hardening, not as final
  Tauri/DDJ live acceptance.
- Durable packet: `.planning/packets/2026-06-01/CODEX_READY-runtime-memory-clap-readiness.md`.
- Current code path verified: `SqliteVecMemoryStore` checks the declared
  `FLOAT[N]` dimension on open, recreates empty stale vec tables at the current
  `EMBEDDING_DIM`, refuses to wipe populated stale tables by falling back, and
  diagnostic `run_session()` constructs `SessionLoop(memory_ingest_enabled=False)`.
- `uv run python -m vibemix library models --json` reported CLAP ONNX and
  CUE-DETR installed with `required_ready: true` and `all_ready: true`.
- `uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py tests/memory/test_store.py tests/memory/test_ingest.py`
  passed: 34 tests.
- `uv run ruff check src/vibemix/runtime/session_loop.py src/vibemix/memory/index_sqlite_vec_memory.py tests/memory/test_ingest_wiring.py tests/memory/test_store_parity.py`
  passed.
- `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session` reached
  `127.0.0.1:8765`; `.claude/skills/drive-vibemix/scripts/ws_probe.py --seconds 2`
  captured 58 `ipc.session.snapshot` frames; Ctrl-C exited with
  `memory ingest (boot) skipped: disabled for this session loop` and
  `memory ingest (close) skipped: disabled for this session loop`.
- Shared-file caution: `src/vibemix/runtime/session_loop.py` also contains
  non-Package-12 hunks for drop prediction and legacy timestamp normalization.
  Stage by hunk if this package lands independently.

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
- Current Codex refresh, 2026-05-31 22:14 +03:
  Durable packet:
  `.planning/packets/2026-06-01/CODEX_READY-tauri-sidecar-bundle-freshness-guard.md`.
  `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only`
  fails because the bundled sidecar IPC schema is stale relative to the current
  source schema. This is expected guard behavior, not package readiness.
- Codex follow-up, 2026-06-01:
  `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec`
  rebuilt and installed the Apple Silicon sidecar, scanning 403 bundled files
  with no AIza-pattern leak. After the rebuild,
  `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only`
  and `uv run python scripts/dist/check_sidecar_bundle_ready.py` both passed;
  `cmp -s` confirmed the embedded IPC schema byte-matches
  `tauri/ui/src/ipc/messages.schema.json`.
- Codex artifact follow-up, 2026-06-01:
  `bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats` rebuilt the
  frontend, rebuilt the Apple Silicon sidecar, built an unsigned Tauri `.app`,
  repaired 36 app-side PyInstaller dylib links, passed
  `check_macos_app_bundle_ready.py --smoke library-stats`, created
  `tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg`, then
  passed `check_macos_dmg_artifact_ready.py --smoke library-stats` on the
  copied app from the DMG. Fresh local DMG: 119464615 bytes, mtime
  `2026-06-01 07:36:28 +0300`, sha256
  `ae929e88c3ef24d092cfb915b6a01780e28353730e86a120212e5bd6724b321d`.
- `uv run python -m scripts.dist.verify_binary tauri/src-tauri/target/release/bundle/macos/vibemix.app --report /tmp/vibemix-local-app-verify-report.json`
  scanned 407 entries and found 0 hits.
- Re-running the stale IPC ghost scan across source, Tauri resources, tests,
  scripts, and remaining `target/` files produced no matches.
- `uv run pytest -q tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py`
  passed: 20 tests. The tests cover ready bundles, missing/stale embedded IPC
  schemas, placeholder-only bundles, too-small binaries, executable-bit checks,
  and prepare-build check/build behavior.
- `uv run ruff check scripts/dist/check_sidecar_bundle_ready.py tests/install/test_sidecar_bundle_ready.py`
  passed.
- Codex latest-code artifact follow-up, 2026-06-01:
  after the sidecar lifecycle and CoreAudio boot-safety fixes,
  `bash scripts/dist/build_macos_local_dmg.sh --smoke library-stats` passed
  again. Latest local DMG:
  `tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg`,
  119468447 bytes, mtime `2026-06-01 08:17:10 +0300`, sha256
  `efe673e4b0a36acd7723a650630008b8287df1a835063e556aa0c7d3c051fdfc`.
  Normal packaged `open -n .../vibemix.app` reached the bundled sidecar on
  `127.0.0.1:8765`, emitted `ipc.status.tick livekit=ok gemini=ok midi=1`, and
  normal macOS Quit removed both app and sidecar processes.

Remaining gate:

- The latest local `.app`/DMG exists, passes drag-install smoke, boots its
  bundled sidecar, and quits cleanly, but it is unsigned. Re-signing,
  notarization, clean-install proof, and live DJ acceptance still belong to the
  release gate.

## Package 13A2 - Packaged Test Fixture Exclusion Gate

Suggested commit: `fix(packaging): reject bundled test fixtures`

Include:

- `scripts/dist/check_macos_app_bundle_ready.py`
- `tests/install/test_macos_app_bundle_ready.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Signed/notarized artifacts, DMGs, PyInstaller output, and Tauri build output.
- `src/vibemix/library/rekordbox.py`; fixture-cache quarantine is a separate
  active library lane.

Reason:

- Fixture-cache rejection is only meaningful in packaged builds if repository
  test fixtures do not ship inside the `.app`. The app-bundle readiness gate now
  fails on any bundled `tests/.../fixtures/...` path before signing/upload.
- `check_macos_dmg_artifact_ready.py` reuses this app-bundle checker on the
  copied app from a DMG, so the same exclusion gate protects local DMG proof.

Proof before staging:

- `uv run pytest -q tests/install/test_macos_app_bundle_ready.py`
- `uv run ruff check scripts/dist/check_macos_app_bundle_ready.py tests/install/test_macos_app_bundle_ready.py`
- `git diff --check -- scripts/dist/check_macos_app_bundle_ready.py tests/install/test_macos_app_bundle_ready.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 13B - macOS Signing And Notarization Flow

Suggested commit if/when selected: `fix(packaging): support local notarization fallback`

Include:

- `docs/signing-macos.md`
- `.github/workflows/release.yml`
- `scripts/dist/sign_macos.sh`
- `tauri/src-tauri/tauri.conf.json5`
- `tests/security/test_release_yml_signing_skips.py`

Reason:

- This is release packaging/signing behavior, not the Package 13 sidecar bundle
  freshness guard and not the refactor/wiring lane. The current hunk adds a
  local Apple-ID app-specific-password notarization fallback, an
  `APPLE_SIGNING_IDENTITY` alias, and a Tauri build-command path correction.
- Code-signing changes prove identity selection, secret handling, notarization
  submission/log retrieval, staple verification, and the Tauri build hook path.
- The release workflow must build the macOS `.app` with `--no-sign` so Tauri
  does not notarize before `sign_macos.sh` force-signs the nested PyInstaller
  sidecar Mach-O tree.

Proof already run:

- `./scripts/dist/sign_macos.sh --dry-run tauri/src-tauri/target/release/bundle/macos/vibemix.app`
  passed with `notary_auth=apple-id` and no secret values echoed.
- `./scripts/dist/sign_macos.sh tauri/src-tauri/target/release/bundle/macos/vibemix.app`
  passed end-to-end: repaired sidecar symlinks, force-signed 167 nested Mach-O
  files, strict-verified the `.app`, created and signed
  `dist/vibemix-0.0.1.dmg`, submitted to Apple notarization, downloaded the
  accepted notary log, stapled and validated the ticket, passed Gatekeeper
  `spctl`, and ran `verify_binary.py`.
- `codesign -dv --verbose=4 dist/vibemix-0.0.1.dmg` reports
  `Authority=Developer ID Application: Francesco Fasanella (UK7DYFK6F8)`,
  `Timestamp=31 May 2026 at 18:58:51`, and `Notarization Ticket=stapled`.
- `xcrun stapler validate dist/vibemix-0.0.1.dmg` passed.
- `spctl -a -vvv -t install dist/vibemix-0.0.1.dmg` passed with
  `source=Notarized Developer ID`.
- `codesign --verify --deep --strict --verbose=2 tauri/src-tauri/target/release/bundle/macos/vibemix.app`
  passed.
- `spctl --assess --type execute --verbose=4 tauri/src-tauri/target/release/bundle/macos/vibemix.app`
  passed with `source=Notarized Developer ID`.
- `dist/verify-report.json` reports `status=clean`, `scanned=407`, `hits=[]`.
- `dist/notarytool-detail.json` reports `status=Accepted`.
- Fresh accepted artifact:
  `dist/vibemix-0.0.1.dmg`, 119812586 bytes, mtime
  `2026-05-31 19:02:20 +0300`, sha256
  `d3cbdeebd55aff6fcc37d1e3e499c57380fb0dfc57982119aa05fcd6b5300100`.
- `uv run pytest -q tests/security/test_release_yml_signing_skips.py tests/dist/test_verify_binary.py tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py`
  passed: 60 passed in 0.71s.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` passed.

Codex refresh, 2026-05-31 22:14 +03:

- Durable packet:
  `.planning/packets/2026-06-01/CODEX_READY-macos-signing-notarization-flow.md`.
- Classification: LAND as signing/notarization flow support and documentation,
  not as current-product release approval.
- `bash -n scripts/dist/sign_macos.sh` passed.
- `uv run pytest -q tests/security/test_release_yml_signing_skips.py tests/dist/test_verify_binary.py tests/install/test_sidecar_bundle_ready.py tests/install/test_prepare_tauri_build.py`
  passed: 60 tests.
- `uv run ruff check scripts/dist/check_sidecar_bundle_ready.py tests/install/test_sidecar_bundle_ready.py tests/security/test_release_yml_signing_skips.py`
  passed.
- `codesign -dv --verbose=4 dist/vibemix-0.0.1.dmg` reports Developer ID
  Application authority, Team `UK7DYFK6F8`, timestamp
  `31 May 2026 at 18:58:51`, and stapled notarization ticket.
- `xcrun stapler validate dist/vibemix-0.0.1.dmg` passed; `spctl -a -vvv -t install dist/vibemix-0.0.1.dmg`
  accepted it as `source=Notarized Developer ID`.
- `codesign --verify --deep --strict --verbose=2 tauri/src-tauri/target/release/bundle/macos/vibemix.app`
  passed; `spctl --assess --type execute --verbose=4 .../vibemix.app` accepted
  the app as `source=Notarized Developer ID`.
- `shasum -a 256 dist/vibemix-0.0.1.dmg` =
  `d3cbdeebd55aff6fcc37d1e3e499c57380fb0dfc57982119aa05fcd6b5300100`.
- `dist/verify-report.json` reports `status=clean`, `scanned=407`, `hits=[]`;
  `dist/notarytool-detail.json` reports `status=Accepted`.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` passed.
- Important boundary: Package 13's sidecar freshness blocker has since been
  cleared and a fresh unsigned local `.app`/DMG has been rebuilt and smoked.
- Fresh signing follow-up, 2026-06-01:
  `./scripts/dist/sign_macos.sh --dry-run --output-dir dist/fresh-20260601 tauri/src-tauri/target/release/bundle/macos/vibemix.app`
  passed with `notary_auth=apple-id`. Then
  `./scripts/dist/sign_macos.sh --output-dir dist/fresh-20260601 tauri/src-tauri/target/release/bundle/macos/vibemix.app`
  force-signed 167 nested Mach-O binaries, strict-verified the `.app`, created
  and signed `dist/fresh-20260601/vibemix-0.0.1.dmg`, submitted to Apple
  notarization, downloaded submission log
  `ff556162-a08d-4fb8-acfd-78664d8d8465`, stapled and validated the ticket,
  passed app Gatekeeper assessment, and ran `verify_binary.py`.
- Fresh signed artifact:
  `dist/fresh-20260601/vibemix-0.0.1.dmg`, 119953279 bytes, mtime
  `2026-06-01 07:42:22 +0300`, sha256
  `8f52423c7bdaf6a4bb9657606951532675f97239ecc857466c9721a39b26820b`.
- Independent follow-up checks passed:
  `xcrun stapler validate dist/fresh-20260601/vibemix-0.0.1.dmg`,
  `spctl -a -vvv -t install dist/fresh-20260601/vibemix-0.0.1.dmg`,
  `uv run python scripts/dist/check_macos_dmg_artifact_ready.py dist/fresh-20260601/vibemix-0.0.1.dmg --smoke library-stats --json`,
  `codesign --verify --deep --strict --verbose=2 tauri/src-tauri/target/release/bundle/macos/vibemix.app`,
  and `spctl --assess --type execute --verbose=4 tauri/src-tauri/target/release/bundle/macos/vibemix.app`.
- `dist/fresh-20260601/verify-report.json` reports `status=clean`,
  `scanned=407`, `hits=[]`; `dist/fresh-20260601/notarytool-detail.json`
  reports `status=Accepted`.
- Packaged launch smoke from the freshly signed app:
  `VIBEMIX_INPUT_DEVICE='BlackHole 16ch' VIBEMIX_DECK_AUDIO_CHANNELS=auto VIBEMIX_DROP_DEBUG=1 tauri/src-tauri/target/release/bundle/macos/vibemix.app/Contents/MacOS/vibemix`
  brought `127.0.0.1:8765` online with `dev_sidecar=false`, spawned the
  bundled sidecar from `Contents/Resources/binaries/...`, created session
  `20260601-074500`, emitted 100 observed `ipc.session.snapshot` frames, and
  produced UI status `gemini=ok`, `livekit=ok`, `midi=1`.
- Boundary from that smoke: music meters stayed `0`, no MIDI move events were
  captured in the short observe window, and directly terminating the app
  process left the bundled sidecar orphaned until it was killed manually.
  Therefore this is packaged boot proof, not normal Quit proof and not live DJ
  acceptance.
- Earlier normal packaged Quit proof failed:
  `open -n tauri/src-tauri/target/release/bundle/macos/vibemix.app` launched
  the signed app and brought `127.0.0.1:8765` online with `dev_sidecar=false`.
  `osascript -e 'tell application id "world.bravoh.vibemix" to quit'` removed
  the app process, but bundled sidecar PID `41742` remained alive as PPID 1 and
  kept `127.0.0.1:8765` reachable until `kill -KILL 41742`. This was a real
  release blocker and belonged with the Tauri sidecar/restart runtime lane, not
  the signing flow.
- Codex follow-up, 2026-06-01: the sidecar Quit blocker is fixed/proven in
  current source. Latest unsigned local DMG:
  `tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg`,
  119468447 bytes, mtime `2026-06-01 08:17:10 +0300`, sha256
  `efe673e4b0a36acd7723a650630008b8287df1a835063e556aa0c7d3c051fdfc`.
  `open -n tauri/src-tauri/target/release/bundle/macos/vibemix.app` produced
  app PID `53591`, bundled sidecar PID `53595`, a `127.0.0.1:8765` listener,
  `sidecar_status ws_reachable=true`, and `ipc.status.tick livekit=ok
  gemini=ok midi=1`. Normal macOS Quit then left no app process, no bundled
  sidecar process, no `8765` listener, and `sidecar_status ws_reachable=false`.
  The stale signed artifact above still proves the earlier signing flow, but
  `dist/fresh-20260601/vibemix-0.0.1.dmg` predates these runtime fixes.
- Codex latest-code signing follow-up, 2026-06-01:
  `./scripts/dist/sign_macos.sh --output-dir dist/fresh-20260601-latest tauri/src-tauri/target/release/bundle/macos/vibemix.app`
  passed end-to-end: repaired sidecar symlinks, force-signed 167 nested Mach-O
  binaries, strict-verified the `.app`, submitted notarization
  `8975c0c9-053b-4d95-94d0-ffa5e9044162`, stapled/validated the DMG, passed
  Gatekeeper app assessment, and scanned `407` bundle entries with `hits=[]`.
  Latest signed/notarized DMG:
  `dist/fresh-20260601-latest/vibemix-0.0.1.dmg`, 119957189 bytes, mtime
  `2026-06-01 08:32:00 +0300`, sha256
  `a5b56658595bbdae11e5558cdac35f266244192c5b37a51ff6361587e4566b29`.
  Independent `stapler`, `spctl -t install`,
  `check_macos_dmg_artifact_ready.py --smoke library-stats --json`,
  `codesign --verify --deep --strict`, app `spctl`, and verifier-report checks
  passed. A copy of the app from that DMG launched from
  `/tmp/vibemix-signed-install.Tp4lk7/vibemix.app`, reached `127.0.0.1:8765`
  with app PID `56437` and sidecar PID `56441`, emitted `ipc.status.tick
  livekit=ok gemini=ok midi=1`, and normal macOS Quit left no app process, no
  sidecar process, and no `8765` listener.

Remaining gate:

- Before final public release, run controller/audible live proof and keep launch
  collateral aligned with the verified product reality. Controller-specific
  proof is available to rerun when the DDJ-FLX4 is plugged in, but it is not
  part of the signing/notarization proof itself.

## Hold Lane - Local Code-Signing Certificate Dumps

Suggested commit: none; do not commit these files.

Hold:

- `codesign0`
- `codesign1`
- `codesign2`

Reason:

- These are local X.509 certificate chain dumps from signing/notarization
  inspection. They are useful as local evidence but are not product source,
  packaging logic, release artifacts, or docs.
- Do not stage them with signing work, release work, or any broad product
  commit. Before a final release branch is prepared, move them outside the repo
  or add an explicit local ignore rule if they are expected to recur.

Remaining gate:

- Confirm the final signed artifact with `codesign`, `stapler`, and `spctl`
  output, using tool output or docs rather than committing these dumped cert
  files.

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
- `tauri/src-tauri/src/sidecar.rs` also carries the sidecar restart recovery
  hunks below. If this log-drain lane and the restart lane are staged as
  separate commits, use hunk-level staging.

Remaining gate:

- Run `cargo fmt` / `cargo check --manifest-path tauri/src-tauri/Cargo.toml` and
  any focused sidecar tests before promoting this lane.

## Hold Lane - Tauri Cohost Restart Recovery

Suggested commit if/when selected: `fix(tauri): make cohost restart respawn sidecar`

Hold:

- `tauri/src-tauri/src/main.rs`
- `tauri/src-tauri/src/sidecar.rs`

Reason:

- The frontend-dead-buttons packet proved the crash/offline retry button called
  the registered `restart_sidecar` command, but the Rust body was still a Wave 2
  stub: kill the child if present, emit `sidecar-state: restarting`, and stop.
  If the watchdog had already exited, clicking `RESTART COHOST` could not
  actually bring the co-host back.
- The current hunk adds a guarded supervisor launcher, shares the Tauri
  sidecar log-path resolver between boot and restart, starts the boot watchdog
  through that launcher, and makes `restart_sidecar` start a fresh supervisor
  when no supervisor is active. If a supervisor is still active, it preserves
  the existing kill-child-and-let-watchdog-retry behavior.
- Codex packaged Quit proof, 2026-06-01, found the same runtime family from the
  other direction: `open -n .../vibemix.app` launched the signed packaged app,
  `osascript -e 'tell application id "world.bravoh.vibemix" to quit'` exited
  the app process, but the bundled sidecar stayed alive as PPID 1 and kept
  `127.0.0.1:8765` reachable until killed manually. This lane now owns both
  restart recovery and normal Quit sidecar cleanup before release.
- Codex follow-up, 2026-06-01: the Rust lifecycle hunk now also requests
  sidecar shutdown on `RunEvent::ExitRequested` and `RunEvent::Exit`, tracks a
  shutdown flag in the sidecar state, and terminates std-spawned sidecars with
  SIGTERM plus SIGKILL fallback. Latest-code unsigned packaged proof rebuilt
  `tauri/src-tauri/target/release/bundle/dmg/vibemix_0.0.1_aarch64.dmg`
  (119468447 bytes, mtime `2026-06-01 08:17:10 +0300`, sha256
  `efe673e4b0a36acd7723a650630008b8287df1a835063e556aa0c7d3c051fdfc`),
  `open -n .../vibemix.app` reached `127.0.0.1:8765` with
  `ipc.status.tick livekit=ok gemini=ok midi=1`, and normal macOS Quit left no
  app process, no bundled sidecar process, and no `8765` listener.

Remaining gate:

- `rustfmt --edition 2021 --check tauri/src-tauri/src/main.rs tauri/src-tauri/src/sidecar.rs`
  passed. Full `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check`
  is still blocked by unrelated formatting drift in `tauri/src-tauri/src/library_cmds.rs`.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml sidecar -- --nocapture`
  passed: 20 tests.
- `npm --prefix tauri/ui test -- tests/session/grounding-failure.spec.ts`
  passed: 12 tests.

## Package 14 - Live TTS Shutdown Hygiene

Suggested commit: `fix(runtime): close nested live tts providers`

Packaging decision: this shares `src/vibemix/__main__.py` with Package 10. If
staging as separate commits, stage only the `_close_tts_chain()` and shutdown
cleanup hunks here, and leave `vibemix library budget --stack live` hunks with
Package 10.

Include:

- `src/vibemix/__main__.py`
- `tests/test_main_smoke.py`
- `.planning/packets/2026-06-01/CODEX_READY-live-tts-shutdown-hygiene.md`

Keep out:

- Live-stack budget CLI/parser/reporting changes from the same `__main__.py`
  file; those remain Package 10.

Proof already run:

- Codex refresh, 2026-06-01:
  `.planning/packets/2026-06-01/CODEX_READY-live-tts-shutdown-hygiene.md`
  now includes a fresh source run: current `uv run python -m vibemix` reached
  `ws://127.0.0.1:8765`, detected `DDJ-FLX4`, MCP captured 26
  `ipc.session.snapshot` frames, Ctrl-C shutdown reached `-> bye`, and no
  `Unclosed client session` warning appeared in captured output.
- `uv run pytest -q tests/test_main_smoke.py -k close_tts_chain`
- `uv run pytest -q tests/test_main_smoke.py::test_close_tts_chain_closes_nested_providers_once tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams`
  passed: 2 tests.
- `uv run ruff check src/vibemix/__main__.py tests/test_main_smoke.py`
  passed.
- `git diff --check -- src/vibemix/__main__.py tests/test_main_smoke.py`
  passed.
- Full live rerun after the fix: `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`
  with `DDJ-FLX4` connected, `ws_probe.py --action trigger`, and Cartesia speech.
  Shutdown reached `-> bye` without the previous `Unclosed client session` warning.

Remaining gate:

- If Package 10 and Package 14 are staged separately, inspect
  `git diff --cached -- src/vibemix/__main__.py` before committing so the
  unrelated budget and shutdown hunks do not travel together accidentally.

## Package 14B - MOSS-only Voice Source

Suggested commit: `fix(tts): make moss the only voice source`

Packaging decision: this promotes the accepted local-MOSS voice policy into the
live TTS factory. Direct mode and proxy mode both resolve to the same on-device
MOSS adapter. Cloud TTS keys may still be accepted by compatibility call
signatures, but they must not select Cartesia, Gemini-native TTS, OpenRouter TTS,
or proxy speech. If MOSS is disabled or missing, speech fails loudly instead of
falling back to a paid/cloud voice.

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/agent/__init__.py`
- `src/vibemix/agent/config.py`
- `src/vibemix/agent/line_voice.py`
- `src/vibemix/agent/local_tts.py`
- `src/vibemix/agent/proxy_client.py`
- `src/vibemix/agent/tts_chain.py`
- `tests/agent/test_line_voice.py`
- `tests/agent/test_livekit_google_slim.py`
- `tests/agent/test_local_tts.py`
- `tests/agent/test_proxy_client.py`
- `tests/agent/test_tts_chain.py`
- `tests/agent/test_tts_chain_cartesia.py`
- `tests/test_main_smoke.py`
- `tests/test_phase05_verification.py`

Keep out:

- `scripts/local_tts_speak.py`, vendored MOSS runtime movement, model download
  UX, and dependency/lockfile churn unless selected as a separate model-shipping
  package.
- Package 14 shutdown cleanup hunks in `src/vibemix/__main__.py` and
  `tests/test_main_smoke.py`.
- Drop-call/default-on hunks in `src/vibemix/__main__.py` and
  `tests/test_main_smoke.py`.

Current evidence, 2026-06-01:

- `uv run pytest -q tests/test_phase05_verification.py::test_g8_direct_mode_phase4_regression_safe tests/test_main_smoke.py::test_smoke_03_full_wiring tests/test_main_smoke.py::test_smoke_04_no_openrouter_key tests/agent/test_tts_chain.py tests/agent/test_tts_chain_cartesia.py tests/agent/test_proxy_client.py tests/agent/test_local_tts.py tests/agent/test_line_voice.py tests/agent/test_livekit_google_slim.py tests/agent/test_config.py -m 'not slow'`
  passed: 44 tests, 1 deselected.
- `uv run ruff check src/vibemix/agent/__init__.py src/vibemix/agent/config.py src/vibemix/agent/line_voice.py src/vibemix/agent/local_tts.py src/vibemix/agent/proxy_client.py src/vibemix/agent/tts_chain.py src/vibemix/__main__.py tests/agent/test_tts_chain.py tests/agent/test_tts_chain_cartesia.py tests/agent/test_proxy_client.py tests/agent/test_local_tts.py tests/agent/test_line_voice.py tests/agent/test_livekit_google_slim.py tests/agent/test_config.py tests/test_main_smoke.py tests/test_phase05_verification.py`
  passed.
- Run the package checker after staging, because this package intentionally
  shares `src/vibemix/__main__.py` and `tests/test_main_smoke.py` with existing
  hold/land lanes and must be staged by hunk.

## Package 14I - Retire Cartesia TTS Dependency

Suggested commit: `fix(tts): remove cartesia voice dependency`

Packaging decision: Package 14B made MOSS the only live voice source but left
the Cartesia LiveKit plugin installed as a required dependency and kept a test
that imported the provider only to assert it was not called. This package closes
that residue by making Cartesia absent from the runtime dependency graph. The
legacy ``cartesia_api_key`` parameter remains an accepted no-op for caller
compatibility; it must not import or instantiate a Cartesia provider.

Include:

- `pyproject.toml`
- `uv.lock`
- `tests/agent/test_tts_chain_cartesia.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Provider-selection changes in `src/vibemix/agent/tts_chain.py`; MOSS-only
  behavior is already structural there.
- MOSS model download/ship UX and PyInstaller model bundling; those remain
  Package 14C/14E/14H release gates.
- Cloud LLM/OpenRouter brain routes. This package is voice-only.

Proof to run:

- `uv lock`
- `uv run pytest -q tests/agent/test_tts_chain_cartesia.py tests/agent/test_tts_chain.py tests/agent/test_proxy_client.py tests/agent/test_local_tts.py tests/test_phase05_verification.py::test_g8_direct_mode_phase4_regression_safe`
- `uv run ruff check tests/agent/test_tts_chain_cartesia.py tests/agent/test_tts_chain.py src/vibemix/agent/tts_chain.py src/vibemix/agent/proxy_client.py`
- `rg -n "livekit-plugins-cartesia|from livekit\\.plugins import cartesia" pyproject.toml uv.lock src tests --glob '!tauri/ui/node_modules/**' --glob '!tauri/src-tauri/target/**'`
- `uv tree --locked | rg "livekit-plugins-cartesia"` returns no matches.

Remaining gate:

- Packaged voice readiness is unchanged by this cleanup: the app still needs
  MOSS model availability/download/bundle proof before a release claim.

## Package 14C - MOSS-only Frozen Runtime Dependencies

Suggested commit: `fix(packaging): bundle sentencepiece for moss tts`

Packaging decision: Package 14B made MOSS the single source of TTS in every
runtime mode. That means a frozen sidecar missing MOSS runtime dependencies now
fails loudly with `LocalTTSUnavailable` instead of falling back to cloud speech.
The PyInstaller specs already collect `onnxruntime` and `tokenizers`, but the
MOSS engine imports `sentencepiece` at synthesis time. Bundle `sentencepiece`
explicitly on both macOS and Windows before any packaged/signed build claims a
working MOSS-only co-host.

Include:

- `vibemix-core.macos.spec`
- `vibemix-core.windows.spec`
- `tests/sidecar/test_build_sidecar_rename.py`

Keep out:

- MOSS model download/ship UX, vendored runtime movement, and
  `scripts/local_tts_speak.py`.
- Any live voice-quality claim. This package proves the frozen sidecar includes
  the Python/native dependency needed to import MOSS; Kaan ear-pass and packaged
  synthesis proof remain release gates.

Current evidence, 2026-06-01:

- `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_collect_local_ai_runtime`
  passed: 2 tests.
- `uv run ruff check tests/sidecar/test_build_sidecar_rename.py` passed.
- `git diff --check -- vibemix-core.macos.spec vibemix-core.windows.spec tests/sidecar/test_build_sidecar_rename.py`
  passed.

## Package 14D - MOSS-only Missing Model Boot Guard

Suggested commit: `fix(tts): boot muted when moss model is unavailable`

Packaging decision: MOSS remains the only live voice source. This package does
not add cloud fallback and does not fake speech. It translates the known
`LocalTTSUnavailable` boot case into a transparent muted LiveKit session
(`NOT_GIVEN` TTS) so a clean machine missing the large model does not crash the
sidecar before the UI can explain or repair it. Direct calls to
`build_tts_chain()` still fail loudly; only app boot catches the product-known
"model missing / local disabled" exception.

Include:

- `src/vibemix/__main__.py`
- `tests/test_main_smoke.py`

Keep out:

- Any cloud/provider TTS fallback.
- MOSS model download/ship UX, vendored runtime movement, and
  `scripts/local_tts_speak.py`.
- DROP-call speech/timing hunks and deck-audio capture hunks in `__main__.py`.

Proof for this boot-guard slice:

- `uv run pytest -q tests/test_main_smoke.py::test_smoke_04b_missing_moss_model_boots_muted_not_cloud_fallback tests/agent/test_tts_chain.py::test_tts_chain_missing_moss_model_fails_loud`
- `uv run ruff check src/vibemix/__main__.py tests/test_main_smoke.py`
- `git diff --check -- src/vibemix/__main__.py tests/test_main_smoke.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- Live source probe, 2026-06-01: `VIBEMIX_LOCAL_TTS=0` correctly selected
  `NOT_GIVEN` TTS but LiveKit still attempted `tts_node` because audio output
  stayed enabled. This package now disables session audio output when app boot
  is muted, so muted mode stays quiet without cloud fallback and without a
  background LiveKit error.

Remaining gate:

- Add real model download or model-bundle UX before packaged release can claim a
  speaking MOSS co-host on a fresh machine.

## Package 14E - MOSS Model Readiness and Installer Surface

Suggested commit: `fix(tts): surface moss model readiness`

Packaging decision: MOSS remains the only TTS source. This package makes the
required voice model visible in the same setup surface as CLAP/CUE instead of
letting a fresh install look "ready" while the co-host is muted. `library models`
now reports `moss-tts` as a required local model, includes it in
`--install required`, and supports a release/ops-hosted archive only when URL,
SHA-256, and byte-size pins are supplied. Without those pins it fails honestly
with manual setup guidance; it does not invent a cloud fallback or an unverified
download.

Include:

- `src/vibemix/agent/local_tts.py`
- `src/vibemix/library/model_assets.py`
- `src/vibemix/__main__.py`
- `tests/agent/test_local_tts.py`
- `tests/library/test_models_cli.py`

Keep out:

- Bundling the 600MB+ MOSS ONNX tree into PyInstaller specs.
- Any cloud/provider TTS fallback.
- DROP-call speech/timing hunks and deck-audio capture hunks in
  `src/vibemix/__main__.py`.

Proof for this readiness slice:

- `uv run pytest -q tests/library/test_models_cli.py tests/agent/test_local_tts.py`
- `uv run ruff check src/vibemix/agent/local_tts.py src/vibemix/library/model_assets.py src/vibemix/__main__.py tests/library/test_models_cli.py tests/agent/test_local_tts.py`
- `git diff --check -- src/vibemix/agent/local_tts.py src/vibemix/library/model_assets.py src/vibemix/__main__.py tests/library/test_models_cli.py tests/agent/test_local_tts.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- A packaged release still needs either a pinned hosted archive configured in
  release/ops, a bundled model, or a first-run downloader UI that feeds this
  installer surface. This package proves readiness and verified archive plumbing,
  not that the public hosted artifact exists.

## Package 14F - MOSS Model Setup UI Surface

Suggested commit: `fix(library-ui): show moss model readiness`

Packaging decision: Package 14E made the backend/CLI report `moss-tts` as a
required voice model. This package carries that truth into the Tauri library
window so the first-run setup line, install target routing, and progress tape no
longer imply CLAP is the only required asset. CUE remains optional and separate.

Include:

- `tauri/ui/src/library/api.ts`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/model-setup.test.ts`
- `tauri/ui/src/library/api.test.ts`
- `tauri/ui/src/library/build.test.ts`
- `tauri/src-tauri/src/library_cmds.rs`

Keep out:

- Any Python model installer changes; Package 14E owns those.
- Bundling the 600MB+ MOSS ONNX tree or changing PyInstaller specs.
- Any cloud/provider TTS fallback.
- Any co-host speech, DROP-call, live timing, or deck-audio capture changes.

Proof for this UI/Rust surface:

- `npm --prefix tauri/ui test -- src/library/model-setup.test.ts src/library/api.test.ts src/library/build.test.ts`
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds`
- `git diff --check -- tauri/ui/src/library/api.ts tauri/ui/src/library/index.ts tauri/ui/src/library/model-setup.test.ts tauri/ui/src/library/api.test.ts tauri/ui/src/library/build.test.ts tauri/src-tauri/src/library_cmds.rs .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- A packaged release still needs a real source of the MOSS model on fresh
  machines: pinned hosted archive, bundled model, or first-run downloader UI.
  This package makes the app honest about that readiness; it does not create the
  public artifact.

## Package 14G - Retire Dead Cloud TTS Residue

Suggested commit: `fix(tts): remove dead cloud tts residue`

Packaging decision: MOSS is the only live co-host TTS source. This package
removes source-level residue that still patched or exposed cloud TTS provider
paths even though no live code may select them.

Include:

- `src/vibemix/agent/tts_chain.py`
- `src/vibemix/agent/_livekit_google_slim.py`
- `src/vibemix/agent/config.py`
- `src/vibemix/agent/__init__.py`
- `tests/agent/test_tts_chain.py`
- `tests/agent/test_proxy_client.py`
- `tests/agent/test_livekit_google_slim.py`
- `tests/agent/test_config.py`
- `pyproject.toml`
- `uv.lock`
- `scripts/audit/dep_ratings.yaml`
- `docs/AUDIT.md`
- `tests/audit/test_dep_cull_complete.py`
- `tests/audit/test_opportunity_evaluations_schema.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- LLM/OpenRouter brain dispatch.
- MOSS local runtime, model download, and packaging behavior.
- Any fallback to cloud/provider speech.

Reason:

- `tts_chain.py` was still importing `livekit.plugins.openai.tts` to patch the
  legacy OpenRouter audio-stream model registry, and `_livekit_google_slim.py`
  still exposed a Gemini-native TTS helper used only by tests. Those are
  incompatible with the current "MOSS only" source-of-truth even if they were
  not selected by `build_tts_chain()`.
- The slice keeps legacy model constants only as import-compatibility strings;
  it removes the provider side effects and orphaned Cartesia voice config.
- Codex follow-up, 2026-06-01: the remaining package-root
  `OPENROUTER_TTS_MODEL` export was also import-only residue. `OPENROUTER_LLM_MODEL`
  stays because it is brain transport; the retired OpenRouter TTS id is no
  longer exported from `vibemix.agent` or `vibemix.agent.config`.
- Codex follow-up, 2026-06-02: after the source-level OpenAI TTS plugin imports
  were gone, the direct `livekit-plugins-openai` dependency/audit entry became
  dead residue too. Removing it is dependency hygiene only; OpenRouter brain
  streaming still uses the first-party `openai` SDK, not the LiveKit OpenAI TTS
  provider plugin.

Proof for this cleanup slice:

- `uv run pytest -q tests/agent/test_tts_chain.py tests/agent/test_proxy_client.py tests/agent/test_livekit_google_slim.py tests/agent/test_config.py`
- `uv run pytest -q tests/audit/test_dep_cull_complete.py tests/audit/test_opportunity_evaluations_schema.py tests/audit/test_audit_md_generator.py tests/agent/test_tts_chain.py tests/agent/test_proxy_client.py tests/agent/test_livekit_google_slim.py tests/agent/test_config.py`
- `uv run ruff check src/vibemix/agent/tts_chain.py src/vibemix/agent/_livekit_google_slim.py src/vibemix/agent/config.py src/vibemix/agent/__init__.py tests/agent/test_tts_chain.py tests/agent/test_proxy_client.py tests/agent/test_livekit_google_slim.py tests/agent/test_config.py`
- `uv run python scripts/audit/gen_audit_md.py --check`
- `! rg -q "livekit-plugins-openai" pyproject.toml uv.lock`
- `! rg -q "from livekit\\.plugins import openai|import livekit\\.plugins\\.openai|livekit\\.plugins\\.openai\\.tts" src/vibemix/agent`
- `git diff --check -- src/vibemix/agent/tts_chain.py src/vibemix/agent/_livekit_google_slim.py src/vibemix/agent/config.py src/vibemix/agent/__init__.py tests/agent/test_tts_chain.py tests/agent/test_proxy_client.py tests/agent/test_livekit_google_slim.py tests/agent/test_config.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- This only removes dead cloud-TTS residue. It does not solve fresh-machine MOSS
  model availability, packaged audio proof, or ear-pass quality.

## Package 14H - MOSS Model Source Release Gate

Suggested commit: `fix(packaging): require moss model source for release`

Packaging decision: MOSS is the only live co-host voice. Development builds may
start muted when the model is absent, but a release pretag must not cut a
MOSS-only artifact unless the sidecar bundle either contains a complete
`MOSS-TTS-Nano-100M-ONNX` tree or the release environment provides pinned HTTPS
archive metadata (`VIBEMIX_MOSS_TTS_ARCHIVE_URL`,
`VIBEMIX_MOSS_TTS_ARCHIVE_SHA256`, `VIBEMIX_MOSS_TTS_ARCHIVE_SIZE`). This is a
release blocker, not a cloud fallback.

Include:

- `scripts/dist/check_sidecar_bundle_ready.py`
- `scripts/dist/prepare_tauri_build.py`
- `scripts/dist/pretag_check.sh`
- `tests/install/test_sidecar_bundle_ready.py`
- `tests/install/test_prepare_tauri_build.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Bundling the 600MB+ MOSS ONNX tree into PyInstaller specs.
- Adding any cloud/provider TTS fallback.
- Live voice quality/ear-pass claims.
- Tauri library setup UI changes; Package 14F owns that surface.

Reason:

- Packages 14B-14F made MOSS the single TTS source, boot-safe when missing, and
  visible in setup. The remaining release risk is process-level: a signed DMG
  could still be cut with no MOSS model source, producing a product whose
  co-host is muted on a fresh machine.
- `check_sidecar_bundle_ready.py --require-moss-source` now validates either a
  complete bundled model tree using the same manifest checker the runtime uses,
  or a verified archive pin triple. `pretag_check.sh` and the Tauri prep script's
  release-only `--require-moss-source`/`VIBEMIX_REQUIRE_MOSS_SOURCE` path opt into
  that stricter release gate.

Proof for this release-gate slice:

- `uv run pytest -q tests/install/test_sidecar_bundle_ready.py`
- `uv run pytest -q tests/install/test_prepare_tauri_build.py tests/install/test_sidecar_bundle_ready.py`
- `uv run ruff check scripts/dist/check_sidecar_bundle_ready.py scripts/dist/prepare_tauri_build.py tests/install/test_prepare_tauri_build.py tests/install/test_sidecar_bundle_ready.py`
- `uv run python -m scripts.dist.check_sidecar_bundle_ready --help`
- `git diff --check -- scripts/dist/check_sidecar_bundle_ready.py scripts/dist/prepare_tauri_build.py scripts/dist/pretag_check.sh tests/install/test_prepare_tauri_build.py tests/install/test_sidecar_bundle_ready.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- A real release still needs Kaan/release-ops to either host the MOSS archive
  and export the three pins, or intentionally bundle the full model tree. This
  package makes the absence impossible to miss during pretag; it does not
  create the hosted artifact.

## Package 14J - MOSS Voice Picker Defaults

Suggested commit: `fix(settings): align voice picker with moss voices`

Packaging decision: MOSS is the only live co-host TTS source. The settings
drawer and runtime config must therefore expose/persist real MOSS voice names,
not retired Gemini/Cartesia voice ids such as `kore` or `puck`. This package
keeps the source default on `Adam`, gives the UI a small real-MOSS voice set,
and makes stale cloud-era config values fall back to `Adam` deterministically
instead of selecting the first arbitrary voice in the MOSS manifest.

Include:

- `src/vibemix/voice_presets.py`
- `src/vibemix/agent/config.py`
- `src/vibemix/agent/local_tts.py`
- `src/vibemix/runtime/config_store.py`
- `src/vibemix/runtime/settings.py`
- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/src/session/state.ts`
- `tauri/ui/src/session/SessionLayout.ts`
- `tests/agent/test_local_tts.py`
- `tests/agent/test_config.py`
- `tests/runtime/test_config_store.py`
- `tests/runtime/test_config_store_bravoh_waitlist.py`
- `tests/runtime/test_settings_apply.py`
- `tests/runtime/test_session_loop.py`
- `tests/ipc/test_session_messages.py`
- `tests/ui_bus/test_messages_schema.py`
- `tests/recording/test_session_metadata.py`
- `tests/security/test_telemetry_consent.py`
- `tauri/ui/src/ipc/validator.spec.ts`
- `tauri/ui/tests/session/integration.spec.ts`
- `tauri/ui/tests/session/render-loop.spec.ts`
- `tauri/ui/tests/session/components.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Any cloud/provider TTS fallback.
- MOSS model install/download/bundling behavior.
- Live voice quality, ear-pass, or packaged-audio claims.
- Any co-host prompt, claim guard, DROP-call, or deck-timing behavior.
- IPC schema/codegen changes; the voice value remains a string payload.

## Package 14K - MOSS-only Documentation Contract

Suggested commit: `docs(tts): align docs with moss-only voice`

Packaging decision: MOSS is the only product TTS source. Several generated or
human-authored docs still described Cartesia/Gemini/OpenAI as the live voice or
fallback path after the runtime policy changed. This package makes the docs and
diagram say the same thing as the source: Gemini remains the brain/listening
client, while speech is local MOSS-only. Paid cloud voices stay only as cost
what-if rows.

Include:

- `scripts/audit/dep_ratings.yaml`
- `scripts/audit/gen_audit_md.py`
- `docs/AUDIT.md`
- `docs/pricing/live-stack-economics.en.md`
- `docs/pricing/live-stack-economics.it.md`
- `docs/prompts/tts-tags.md`
- `scripts/dist/render_architecture.py`
- `docs/assets/architecture.svg`
- `tests/repo/test_docs_assets.py`
- `tests/llm/test_tts_3_1.py`
- `tests/audit/test_dep_cull_complete.py`
- `src/vibemix/agent/playback_sink.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime TTS provider selection; MOSS-only behavior is already structural.
- Dependency removal from `pyproject.toml` or `uv.lock`.
- MOSS model bundle/download/release gates.
- Co-host speech, prompt, grounding, DROP-call, or deck-timing behavior.

Proof to run:

- `uv run python scripts/audit/gen_audit_md.py`
- `uv run python scripts/dist/render_architecture.py`
- `uv run python scripts/audit/gen_audit_md.py --check`
- `uv run python scripts/dist/render_architecture.py --check`
- `uv run pytest -q tests/audit/test_audit_md_generator.py tests/audit/test_dep_cull_complete.py tests/audit/test_opportunity_evaluations_schema.py tests/repo/test_docs_assets.py tests/library/test_cost.py tests/library/test_pricing.py`
- `uv run pytest -q tests/llm/test_tts_3_1.py tests/llm/test_model_router.py tests/agent/test_tts_chain.py tests/agent/test_tts_chain_cartesia.py tests/agent/test_proxy_client.py`
- `uv run ruff check src/vibemix/agent/playback_sink.py tests/audit/test_dep_cull_complete.py tests/repo/test_docs_assets.py tests/llm/test_tts_3_1.py scripts/audit/gen_audit_md.py scripts/dist/render_architecture.py`
- `git diff --check -- scripts/audit/dep_ratings.yaml docs/AUDIT.md docs/pricing/live-stack-economics.en.md docs/pricing/live-stack-economics.it.md docs/prompts/tts-tags.md scripts/dist/render_architecture.py docs/assets/architecture.svg tests/repo/test_docs_assets.py tests/llm/test_tts_3_1.py tests/audit/test_dep_cull_complete.py src/vibemix/agent/playback_sink.py .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- This is a docs/contract cleanup only. It does not prove packaged MOSS voice,
  release artifact readiness, or live FLX4 audio behavior.

## Package 14K2 - Windows MOSS Source Setup Notes

Suggested commit: `docs(windows): document moss voice setup`

Packaging decision: Windows source testers need the same MOSS-only truth as the
runtime. The app voice is local MOSS only; if the MOSS model is absent, Sven is
muted/unready instead of falling back to a cloud TTS provider. The Windows source
setup page previously documented Python/audio/controller setup but did not tell a
tester how to inspect or satisfy the required local voice model.

Include:

- `docs/windows-setup.md`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime TTS provider selection.
- MOSS archive hosting, SHA/size pin decisions, or model bundling.
- Tauri setup UI changes.
- Co-host prompt, speech, grounding, DROP-call, or deck-timing behavior.

Proof to run:

- `uv run pytest -q tests/library/test_models_cli.py tests/install/test_prepare_tauri_build.py tests/install/test_sidecar_bundle_ready.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- docs/windows-setup.md .planning/handoffs/2026-05-31-package-checklist.md`

Remaining gate:

- A real Windows release still needs ops/release to provide the MOSS archive
  pins or bundle a complete model tree. This package only prevents the source
  setup docs from pretending voice readiness is automatic.

## Package 14L - MOSS-only Source Notes Contract

Suggested commit: `docs(tts): remove stale cloud voice source notes`

Packaging decision: MOSS-only needs to be true in source-facing comments and
source data too, not only in docs. This package removes stale comments/pricing
notes that still describe Cartesia/Gemini as the live voice or fallback chain,
while leaving runtime provider behavior untouched.

Include:

- `src/vibemix/library/pricing.py`
- `tests/library/test_pricing.py`
- `scripts/automix_demo_smoke.py`
- `scripts/dayzero/launch_copy/linkedin.txt`
- `scripts/launch/social_templates/hackernews.txt.jinja`
- `scripts/release/check_no_hardcoded_model.sh`
- `src/vibemix/prompts/matrix.py`
- `src/vibemix/platform/_audio_windows.py`
- `docs/byo-key.md`
- `SECURITY.md`
- `src/vibemix/runtime/sec_check.py`
- `tests/security/test_sec_check.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime TTS provider selection or model download/bundle behavior.
- Product pricing math; only wording and the guard assertion change.
- Co-host prompt semantics beyond stale comment wording.
- Live/packaged voice claims.

Proof to run:

- `uv run pytest -q tests/library/test_pricing.py tests/library/test_cost.py tests/scripts/test_demo_film_no_ai_vo.py tests/test_audio_macos.py`
- `uv run ruff check src/vibemix/library/pricing.py tests/library/test_pricing.py scripts/automix_demo_smoke.py src/vibemix/prompts/matrix.py src/vibemix/platform/_audio_windows.py`
- `rg -n "Live primary voice|Cartesia Sonic .*Gemini|Cartesia.*fallback|Gemini TTS expressivity|Gemini TTS streams produce|Cartesia needs it|live reactions/TTS|native-audio TTS|debrief TTS|fallback TTS" src scripts tests docs --glob '!docs/launch/**' --glob '!scripts/local_tts_speak.py' --glob '!tests/library/test_pricing.py'`
- `uv run pytest -q tests/security/test_sec_check.py tests/repo/test_byo_doc_shape.py`
- `uv run ruff check src/vibemix/runtime/sec_check.py tests/security/test_sec_check.py`
- `git diff --check -- src/vibemix/library/pricing.py tests/library/test_pricing.py scripts/automix_demo_smoke.py scripts/dayzero/launch_copy/linkedin.txt scripts/launch/social_templates/hackernews.txt.jinja scripts/release/check_no_hardcoded_model.sh src/vibemix/prompts/matrix.py src/vibemix/platform/_audio_windows.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- This is source-data/comment cleanup only. It does not prove packaged MOSS
  model availability, live voice quality, or real FLX4 audio behavior.

Reason:

- `SettingsDrawer.ts` still listed old Gemini voice ids (`kore`, `puck`,
  `charon`, `fenrir`, `aoede`, `leda`, `orus`, `zephyr`), while local MOSS
  defaults to `Adam`.
- Old persisted config values made the picker look alive but all landed on the
  same manifest fallback voice. The runtime now resolves missing/legacy names
  through the MOSS default first, not `voices[0]`.

Proof for this source/UI slice:

- `uv run pytest -q tests/agent/test_local_tts.py tests/runtime/test_config_store.py tests/runtime/test_config_store_bravoh_waitlist.py tests/runtime/test_settings_apply.py tests/runtime/test_session_loop.py tests/ipc/test_session_messages.py tests/ui_bus/test_messages_schema.py tests/recording/test_session_metadata.py tests/security/test_telemetry_consent.py`
- `npm --prefix tauri/ui test -- tests/session/integration.spec.ts tests/session/render-loop.spec.ts tests/session/components.spec.ts src/ipc/validator.spec.ts`
- `uv run ruff check src/vibemix/voice_presets.py src/vibemix/agent/local_tts.py src/vibemix/runtime/config_store.py tests/agent/test_local_tts.py tests/runtime/test_config_store.py tests/runtime/test_config_store_bravoh_waitlist.py tests/runtime/test_settings_apply.py tests/runtime/test_session_loop.py tests/ipc/test_session_messages.py tests/ui_bus/test_messages_schema.py tests/recording/test_session_metadata.py tests/security/test_telemetry_consent.py`
- `git diff --check -- src/vibemix/voice_presets.py src/vibemix/agent/local_tts.py src/vibemix/runtime/config_store.py tauri/ui/src/settings/SettingsDrawer.ts tauri/ui/src/session/state.ts tauri/ui/src/session/SessionLayout.ts tests/agent/test_local_tts.py tests/runtime/test_config_store.py tests/runtime/test_config_store_bravoh_waitlist.py tests/runtime/test_settings_apply.py tests/runtime/test_session_loop.py tests/ipc/test_session_messages.py tests/ui_bus/test_messages_schema.py tests/recording/test_session_metadata.py tests/security/test_telemetry_consent.py tauri/ui/src/ipc/validator.spec.ts tauri/ui/tests/session/integration.spec.ts tauri/ui/tests/session/render-loop.spec.ts tauri/ui/tests/session/components.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

Remaining gate:

- This only fixes the source settings and deterministic voice selection. It
  does not prove audible quality or voice differences on a live/packaged build.

## Hold Lane - Local MOSS TTS ONNX Runtime Spike

Suggested commit if/when it ships: `feat(tts): add wrapped local moss onnx runtime`

Hold:

- `pyproject.toml`
- `.tmp_gemini_ttft.py`
- `.tmp_tts_bench.py`
- `.tmp_tts_bench.log`
- `scripts/local_tts_speak.py`
- `src/vibemix/agent/local_tts.py`
- `src/vibemix/agent/moss_tts/__init__.py`
- `src/vibemix/agent/moss_tts/ort_cpu_runtime.py`
- `src/vibemix/agent/proxy_client.py`
- `src/vibemix/agent/tts_chain.py`
- `tests/agent/test_local_tts.py`
- `tests/agent/test_proxy_client.py`
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
- Codex added proxy-mode parity in this hold lane: when local MOSS is explicitly
  enabled and cached, `build_proxy_tts_chain()` returns the same single local
  MOSS provider shape instead of routing voice through proxy/OpenAI TTS. When
  local MOSS is unavailable, the old single-entry proxy TTS chain is preserved.

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

Codex proxy-parity proof, 2026-05-31 19:56 +03:

- `uv run pytest -q tests/agent/test_proxy_client.py tests/agent/test_local_tts.py -m 'not slow'`
  passed: 16 tests, 1 slow deselected.
- `uv run ruff check src/vibemix/agent/proxy_client.py tests/agent/test_proxy_client.py`
  passed.
- Remaining gate: this is still source-level proof. Before claiming a packaged
  never-mute proxy path, run a source or packaged session with `VIBEMIX_LOCAL_TTS=1`
  on a machine with the MOSS model cached and confirm the TTS provider in the
  AI-message/session artifacts is `moss-local`.

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
- `src/vibemix/audio/device_select.py`
- `src/vibemix/__main__.py`
- `tests/test_audio_macos.py`
- `tests/audio/test_device_select.py`
- `.planning/packets/2026-06-01/CODEX_READY-desktop-auto-master-16ch-upgrade.md`

Context:

- The first Tauri dev-source live proof reached the renderer and co-host, but
  session `20260531-102701` recorded `capture_device_too_few_channels` because
  Tauri sets `VIBEMIX_AUTO_MASTER_INPUT=1` and the 16ch upgrade probe was
  rerouted back through the silent auto-master fallback. Direct Python did not
  show this because it was not launched with the Tauri auto-master env default.

Proof already run:

- Codex refresh, 2026-06-01:
  `.planning/packets/2026-06-01/CODEX_READY-desktop-auto-master-16ch-upgrade.md`
  now includes current source refs plus a full
  `uv run pytest -q tests/test_audio_macos.py` pass: 23 tests.
- Codex follow-up, 2026-06-01:
  the packaged app no longer enables auto-master implicitly from Rust; explicit
  `VIBEMIX_AUTO_MASTER_INPUT` is still honored. Stale positional output-device
  ids that resolve to aggregate/multi-output/AI-capture devices are rejected,
  mic capture is opt-in (`VIBEMIX_ENABLE_MIC=1` or explicit
  `VIBEMIX_MIC_DEVICE`), and master input capture opens on a daemon background
  thread so a CoreAudio/PortAudio `Pa_OpenStream` stall cannot prevent the ws
  bus from binding.
- `uv run pytest -q tests/test_audio_macos.py::test_find_device_auto_master_input_honors_explicit_blackhole_variant tests/test_audio_macos.py::test_find_device_auto_master_input_chooses_live_48k_variant tests/test_audio_macos.py::test_find_device_auto_master_input_falls_back_to_48k_variant_when_silent tests/test_main_smoke.py::test_deck_audio_auto_upgrades_default_blackhole_input tests/test_main_smoke.py::test_deck_audio_global_default_upgrades_blackhole_without_env`
  passed: 5 tests.
- `uv run pytest -q tests/test_main_smoke.py::test_smoke_03_full_wiring tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams tests/audio/test_device_select.py tests/test_audio_macos.py::test_find_device_auto_master_input_chooses_live_48k_variant tests/test_audio_macos.py::test_find_device_auto_master_input_falls_back_to_48k_variant_when_silent tests/test_audio_macos.py::test_find_device_auto_master_input_uses_preferred_fallback_when_silent tests/test_audio_macos.py::test_find_device_auto_master_input_honors_explicit_blackhole_variant`
  passed: 29 tests.
- `uv run pytest -q tests/test_main_smoke.py::test_smoke_03_full_wiring tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams tests/audio/test_device_select.py`
  passed: 25 tests after the daemon input-open change.
- `uv run ruff check src/vibemix/platform/_audio_macos.py tests/test_audio_macos.py src/vibemix/__main__.py tests/test_main_smoke.py`
  passed.
- `uv run ruff check src/vibemix/__main__.py src/vibemix/audio/device_select.py tests/test_main_smoke.py tests/audio/test_device_select.py`
  passed after the boot-safety changes.
- `git diff --check -- src/vibemix/platform/_audio_macos.py tests/test_audio_macos.py`
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
- `src/vibemix/runtime/coach.py`
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
- `runtime/coach.py` belongs here for the matching DROP-event fixed-text
  `session.say()` hunk. It must not be staged with Judge Voice or Earned Wall
  coach work unless this hold lane's grounding-review and on-beat live proof
  are present.
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
## Package 0P - Viber/Sven Product Boundary Wording Guard

Suggested commit: `docs(product): separate viber agent from sven cohost`

Include:

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `src/vibemix/__main__.py`
- `src/vibemix/library/codex_curate.py`
- `tauri/ui/library.html`
- `tauri/ui/src/library/api.ts`
- `tauri/ui/src/library/library.css`
- `tests/repo/test_phase20_docs.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Co-host prompt/runtime behavior, TTS implementation, Viber tool semantics,
  live app control, package artifacts, and all DROP/Mix Timing Oracle hold-lane
  hunks.

Reason:

- Viber is the library/set-prep agent/operator; Sven is the live co-host voice.
  Active docs, comments, CLI help, and UI source comments must not call Viber
  the co-host or describe live speech as Gemini/cloud TTS. This package fixes
  the wording drift and adds an active-surface regression guard.

Proof before staging:

- `uv run pytest -q tests/repo/test_phase20_docs.py`
- `uv run ruff check src/vibemix/__main__.py src/vibemix/library/codex_curate.py tests/repo/test_phase20_docs.py`
- `git diff --check -- README.md AGENTS.md CLAUDE.md src/vibemix/__main__.py src/vibemix/library/codex_curate.py tauri/ui/library.html tauri/ui/src/library/api.ts tauri/ui/src/library/library.css tests/repo/test_phase20_docs.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 35 - Unpinned Genre Boot Default

Suggested commit: `fix(genre): leave cold start unpinned`

Include:

- `src/vibemix/_main_helpers.py`
- `tests/test_main_smoke.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live genre scoring thresholds, detector profile JSON, prompt persona wording,
  settings drawer UI, packaged defaults, and any event-detector behavior.

Reason:

- Absent `VIBEMIX_GENRE_PROFILE` should not fabricate a scene profile before the
  live detector earns one. Explicit env pins still work and still disable
  auto-detect; no-env cold start remains self-correcting.

Proof before staging:

- `uv run pytest -q tests/test_main_smoke.py -k genre`
- `uv run pytest -q tests/test_main_smoke.py`
- `uv run ruff check src/vibemix/_main_helpers.py tests/test_main_smoke.py`
- `git diff --check -- src/vibemix/_main_helpers.py tests/test_main_smoke.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 35B - Source Genre Prompt Precedence

Suggested commit: `fix(cohost): prefer source genre for citable decks`

Include:

- `src/vibemix/state/deck_state.py`
- `src/vibemix/state/deck_poller.py`
- `src/vibemix/runtime/ws_bus.py`
- `src/vibemix/state/prompt_builder.py`
- `tests/state/test_deck_poller.py`
- `tests/runtime/test_ws_bus_deck_state.py`
- `tests/state/test_coach.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- DSP genre thresholds/profiles, prompt persona wording, Viber tool semantics,
  live app control, and any speech-bank text.

Reason:

- When the deck is citable and the loaded source/library row has a genre tag,
  that song/source fact should outrank a short-window DSP/prototype guess in the
  co-host prompt. If the source genre is absent or the deck is not citable,
  the existing confidence-gated detector remains the fallback; otherwise Sven
  stays silent about genre.

Proof before staging:

- `uv run pytest -q tests/state/test_coach.py tests/state/test_deck_poller.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_ws_bus_genre_fields.py tests/state/test_refresh_perceive.py tests/state/test_genre_reconcile.py`
- `uv run ruff check src/vibemix/state/deck_state.py src/vibemix/state/deck_poller.py src/vibemix/runtime/ws_bus.py src/vibemix/state/prompt_builder.py tests/state/test_deck_poller.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_coach.py`
- `git diff --check -- src/vibemix/state/deck_state.py src/vibemix/state/deck_poller.py src/vibemix/runtime/ws_bus.py src/vibemix/state/prompt_builder.py tests/state/test_deck_poller.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_coach.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 35C - Psytrance Event Chain Routing

Suggested commit: `fix(genre): route psytrance through its own chain`

Include:

- `src/vibemix/events/genres/psytrance.py`
- `src/vibemix/events/genres/__init__.py`
- `src/vibemix/state/refresh.py`
- `src/vibemix/state/music_state.py`
- `tests/state/test_genre_router.py`
- `tests/state/test_genre_router_race.py`
- `tests/state/test_genre_router_integration.py`
- `tests/state/test_genre_autodetect.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New detector algorithms, prompt persona wording, speech-bank text,
  genre-profile JSON retuning, live app control, and Hard Tek detector
  threshold changes.

Reason:

- The DSP/profile path can confidently detect `psytrance`, but the old
  `active_genre` route was still a coarse BPM bucket. Fast psytrance could
  route as Hard Tek and enable acid/distortion overlays. Register psytrance as
  its own event-chain genre, reuse the existing kick/phrase structure for v1,
  exclude Hard Tek-only overlays, and let a user-pinned profile keep winning.

Proof before staging:

- `uv run pytest -q tests/state/test_genre_router.py tests/state/test_genre_router_race.py tests/state/test_genre_router_integration.py tests/state/test_genre_autodetect.py tests/state/test_genre_router_integration.py tests/state/test_event_detector.py tests/state/test_refresh.py`
- `uv run ruff check src/vibemix/events/genres/__init__.py src/vibemix/events/genres/psytrance.py src/vibemix/state/refresh.py src/vibemix/state/music_state.py tests/state/test_genre_router.py tests/state/test_genre_router_race.py tests/state/test_genre_router_integration.py tests/state/test_genre_autodetect.py`
- `git diff --check -- src/vibemix/events/genres/__init__.py src/vibemix/events/genres/psytrance.py src/vibemix/state/refresh.py src/vibemix/state/music_state.py tests/state/test_genre_router.py tests/state/test_genre_router_race.py tests/state/test_genre_router_integration.py tests/state/test_genre_autodetect.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 36 - Mastered Marker Writer Safety Spine

Suggested commit: `fix(learn): add mastered marker writer`

Include:

- `src/vibemix/learn/mastered_marker_writer.py`
- `tests/learn/test_mastered_marker_writer.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/runtime/coach.py`, `src/vibemix/__main__.py`, live speech,
  Earned Wall credit/vocal behavior, automatic library-file mutation, CUE-DETR
  snapping, and any claim that the L3 live hook is complete.

Reason:

- L3 needs a safe writer before it can be called from the Mastered flip branch.
  This package lands only the non-speaking, opt-in, never-raises helper: it
  refuses set-relative timing, requires an explicit in-track position, chooses
  an unused hot-cue pad so hand-set cues are preserved, and returns an honest
  abstain reason when the write is unsafe.

Proof before staging:

- `uv run pytest -q tests/learn/test_mastered_marker_writer.py tests/library/test_export_serato.py tests/learn/test_mastered_vocal_fires_once.py`
- `uv run ruff check src/vibemix/learn/mastered_marker_writer.py tests/learn/test_mastered_marker_writer.py`
- `git diff --check -- src/vibemix/learn/mastered_marker_writer.py tests/learn/test_mastered_marker_writer.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 45 - Debrief to Learn Recommendation Bridge

Suggested commit: `feat(learn): recommend graduation lesson from debrief`

Include:

- `src/vibemix/learn/graduation.py`
- `tests/learn/test_graduation.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/__main__.py`, `src/vibemix/runtime/coach.py`, Sven/live speech,
  Learn window UI rewrites, debrief generation prompts, and any uncited
  model-text recommendation.

Reason:

- L3.06 already checks whether a real debrief exists. This package lets the
  graduation surface derive one deterministic next lesson from the latest
  persisted debrief drill only when the drill field still carries a locked
  citation and names a concrete authored technique such as phrase matching,
  harmonic mixing, filter fade, or recovery. Vague or uncited advice stays
  silent.

Proof before staging:

- `uv run pytest -q tests/learn/test_graduation.py`
- `uv run ruff check src/vibemix/learn/graduation.py tests/learn/test_graduation.py`
- `git diff --check -- src/vibemix/learn/graduation.py tests/learn/test_graduation.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 35D - Psytrance BPM Fallback Band

Suggested commit: `fix(genre): classify psytrance bpm fallback`

Include:

- `src/vibemix/audio/constants.py`
- `src/vibemix/state/refresh.py`
- `tests/audio/test_phase17_constants.py`
- `tests/state/test_refresh.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New detector algorithms, prompt persona wording, speech-bank text, profile
  JSON retuning, and any live hardware claim.
- Rebuilding the psytrance event chain. Package 35C already registered the
  chain; this package only fixes the cold/coarse BPM fallback.

Reason:

- Psytrance is now a first-class event-router genre, but the coarse
  `GENRE_BPM_BANDS` fallback could still not emit `psytrance`. A fast
  low-centroid psytrance track around 145-150 BPM could therefore fall through
  into Hard Tek or unknown routing. Add a 138-150 psytrance band and use the
  existing Hard Tek spectral gate to disambiguate the overlapping 140-150
  region: low mid/high share routes psytrance; high mid/high share still routes
  Hard Tek.

Proof before staging:

- `uv run pytest -q tests/audio/test_phase17_constants.py tests/state/test_refresh.py tests/state/test_genre_router.py tests/state/test_genre_router_integration.py tests/state/test_genre_autodetect.py`
- `uv run ruff check src/vibemix/audio/constants.py src/vibemix/state/refresh.py tests/audio/test_phase17_constants.py tests/state/test_refresh.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/audio/constants.py src/vibemix/state/refresh.py tests/audio/test_phase17_constants.py tests/state/test_refresh.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 13E - Clean-Room Scratch Ignore Guard

Suggested commit: `fix(repo): ignore local clean-room scratch`

Include:

- `.gitignore`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Deleting or moving `.mixxx-tmp-loop/`, `.cp_probe.txt`, or any planning
  scratch files. Removal is a user/destructive-action call; this package only
  prevents accidental staging.
- Any Mixxx-derived implementation, spec prose, or GPL source copying.

Reason:

- The Mixxx verification lanes repeatedly found `.mixxx-tmp-loop/` holding
  untracked verbatim GPL source inside the repo root. It is not committed, but
  without a `.gitignore` guard a stray broad stage could absorb it into an
  Apache-licensed tree. Add ignore rules for that clean-room scratch dir plus
  two local probe/list files surfaced by the same dirty-tree audit.

Proof before staging:

- `git check-ignore -v .mixxx-tmp-loop/bpmcontrol.cpp .cp_probe.txt .planning/.tmp_filelist.txt`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- .gitignore .planning/handoffs/2026-05-31-package-checklist.md`

## Package 20 - Retire Dead Tend Citation Source

Suggested commit: `fix(grounding): remove dead tend citation source`

Include:

- `scripts/README.md`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/agent/language_guard.py`
- `src/vibemix/coach/citation_linter.py`
- `src/vibemix/debrief/drills.py`
- `src/vibemix/debrief/tldr.py`
- `src/vibemix/memory/ingest.py`
- `src/vibemix/prompts/matrix.py`
- `src/vibemix/state/deck_context.py`
- `src/vibemix/state/evidence_registry.py`
- `src/vibemix/ui_bus/learn_messages.py`
- `tauri/ui/src/debrief/__tests__/stripper-roundtrip.spec.ts`
- `tauri/ui/src/debrief/stripper-roundtrip.ts`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tests/agent/test_dj_cohost.py`
- `tests/coach/test_citation_linter.py`
- `tests/coach/test_citation_zero_orphan_replay.py`
- `tests/debrief/test_no_uncited_critique_in_debrief.py`
- `tests/prompts/test_matrix.py`
- `tests/scripts/fixtures/synthetic_session/events.jsonl`
- `tests/scripts/fixtures/synthetic_session/responses/0007_120130_MANUAL/response.txt`
- `tests/state/test_evidence_registry.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime co-host speech behavior beyond removing the unsupported citation source.
- DROP-call / Mix Timing Oracle hold-lane files.
- New profile-memory or preference-learning producers. This package chooses to cut
  the unproduced `[tend:]` grammar source, not build it.

Reason:

- `[tend:<fact>]` was still advertised and accepted by the citation grammar even
  though no runtime producer writes `registry.write("tend", ...)`. Keeping it made
  prompt/schema/test surfaces promise user-profile facts that the app cannot ground.
  The honest path is to remove the source until a real profile-fact producer exists.

Proof before staging:

- `npm --prefix tauri/ui run codegen:ipc`
- `uv run pytest -q tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py tests/debrief/test_no_uncited_critique_in_debrief.py tests/prompts/test_matrix.py tests/scripts/test_replay_linter.py tests/agent/test_dj_cohost.py::test_AE_citation_count_event_written_per_turn tests/agent/test_dj_cohost.py::test_AH_registry_record_citation_count_called_per_turn`
- `npm --prefix tauri/ui test -- src/debrief/__tests__/stripper-roundtrip.spec.ts`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/agent/language_guard.py src/vibemix/coach/citation_linter.py src/vibemix/debrief/drills.py src/vibemix/debrief/tldr.py src/vibemix/memory/ingest.py src/vibemix/prompts/matrix.py src/vibemix/state/deck_context.py src/vibemix/state/evidence_registry.py src/vibemix/ui_bus/learn_messages.py tests/agent/test_dj_cohost.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py tests/debrief/test_no_uncited_critique_in_debrief.py tests/prompts/test_matrix.py tests/state/test_evidence_registry.py`
- `git diff --check -- scripts/README.md src/vibemix/agent/dj_cohost.py src/vibemix/agent/language_guard.py src/vibemix/coach/citation_linter.py src/vibemix/debrief/drills.py src/vibemix/debrief/tldr.py src/vibemix/memory/ingest.py src/vibemix/prompts/matrix.py src/vibemix/state/deck_context.py src/vibemix/state/evidence_registry.py src/vibemix/ui_bus/learn_messages.py tauri/ui/src/debrief/__tests__/stripper-roundtrip.spec.ts tauri/ui/src/debrief/stripper-roundtrip.ts tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/validator.generated.mjs tests/agent/test_dj_cohost.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py tests/debrief/test_no_uncited_critique_in_debrief.py tests/prompts/test_matrix.py tests/scripts/fixtures/synthetic_session/events.jsonl tests/scripts/fixtures/synthetic_session/responses/0007_120130_MANUAL/response.txt tests/state/test_evidence_registry.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 21 - Grounded Spoken Next Suggestion Receipt

Suggested commit: `feat(coach): surface grounded next suggestions`

Include:

- `src/vibemix/runtime/suggestion_voice.py`
- `src/vibemix/runtime/transition_verdict_voice.py`
- `src/vibemix/runtime/coach.py`
- `src/vibemix/state/prompt_builder.py`
- `tests/runtime/test_suggestion_voice.py`
- `tests/runtime/test_transition_verdict_voice.py`
- `tests/runtime/test_coach.py`
- `tests/state/test_coach.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- DROP-call / Mix Timing Oracle hold-lane hunks in `src/vibemix/runtime/coach.py`,
  `src/vibemix/state/drop_predict.py`, `src/vibemix/state/event_detector.py`, and
  `tests/state/test_drop_predict.py`.
- Any direct `session.say()` path for the suggestion. This package feeds Sven
  grounded prompt context only; the existing LLM/linter/live-claim path decides
  whether speech survives.
- Viber UI/library-agent behavior. Viber remains the set-prep/library agent;
  Sven is the live co-host voice.

Reason:

- The next-suggestion engine already powers pills/Viber, but the live co-host
  had no citable receipt for the current candidate. This package writes
  existence-only `[track:<id>]` and `[mix:next_suggestion=<id>]` citations before
  the prompt, then appends an optional suggestion receipt to TRACK_CHANGE /
  TRANSITION_OPPORTUNITY tasks. It explicitly says the candidate is not loaded,
  playing, or a proven transition unless deck/live evidence supports that claim.

Proof before staging:

- `uv run pytest -q tests/runtime/test_transition_verdict_voice.py tests/runtime/test_suggestion_voice.py tests/runtime/test_coach.py::test_coach_hands_grounded_next_suggestion_to_agent tests/state/test_coach.py::test_task_track_change_includes_grounded_next_suggestion_receipt tests/state/test_coach.py::test_task_track_change_includes_grounded_transition_verdict_receipt tests/state/test_coach.py::test_task_transition_opportunity_includes_grounded_next_suggestion_receipt tests/state/test_coach.py::test_task_transition_opportunity_includes_grounded_transition_verdict_receipt tests/coach/test_citation_linter.py::test_track_atom_existence_only tests/coach/test_citation_linter.py::test_screen_mix_key_existence_only`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
- `uv run ruff check src/vibemix/runtime/suggestion_voice.py src/vibemix/runtime/transition_verdict_voice.py src/vibemix/runtime/coach.py src/vibemix/state/prompt_builder.py tests/runtime/test_suggestion_voice.py tests/runtime/test_transition_verdict_voice.py tests/runtime/test_coach.py tests/state/test_coach.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check`

## Package 22 - Loop Beatjump Geometry SRC Gate

Suggested commit: `feat(state): add loop geometry grounding primitive`

Include:

- `src/vibemix/state/loop_geometry.py`
- `src/vibemix/midi/state.py`
- `src/vibemix/midi/profile.py`
- `tests/state/test_loop_geometry.py`
- `tests/midi/test_state.py`
- `tests/midi/test_profile.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Co-host speech, prompt text, `session.say()` paths, and any live claim about
  loop quality or deck intent.
- DROP-call / Mix Timing Oracle hold-lane files:
  `src/vibemix/runtime/coach.py`, `src/vibemix/state/drop_predict.py`,
  `src/vibemix/state/event_detector.py`, `tests/state/test_drop_predict.py`, and
  `tests/state/test_event_detector_drop.py`.
- Beatmatch producer wiring and live deck-identity changes.

Reason:

- H1 loop/beatjump research needs a source-level primitive before any live
  speech can be grounded. This package preserves rapid loop-roll MIDI evidence
  past the legacy 400ms same-label dedup, accepts future loop/beatjump profile
  button kinds, and provides a citation-safe `mix:` atom shape for a future
  beatgrid-exact receipt. It does not make the co-host speak about loops.

Proof before staging:

- `uv run pytest -q tests/state/test_loop_geometry.py tests/midi/test_state.py::test_loop_roll_stack_bypasses_400ms_move_dedup tests/midi/test_state.py::test_dedup_within_400ms_collapses_repeated_label tests/midi/test_state.py::test_handle_msg_loop_in_implicit_play_workaround_preserved tests/midi/test_profile.py::test_schema_validator_accepts_loop_performance_button_kinds tests/midi/test_profile.py::test_pioneer_ddj_flx4_json_buttons_section_lists_all_v4_notes tests/midi/test_profile_flx4_golden.py::test_pioneer_flx4_profile_internal_lookup_byte_equivalent_to_v4 tests/midi/test_profile_flx4_golden.py::test_pioneer_flx4_full_message_replay_byte_equivalent`
- `uv run pytest -q tests/state/test_loop_geometry.py tests/midi/test_state.py tests/midi/test_profile.py tests/midi/test_profile_flx4_golden.py tests/test_midi_macos.py tests/midi/test_profiles_all_controllers.py`
- `uv run ruff check src/vibemix/state/loop_geometry.py src/vibemix/midi/state.py src/vibemix/midi/profile.py tests/state/test_loop_geometry.py tests/midi/test_state.py tests/midi/test_profile.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/state/loop_geometry.py src/vibemix/midi/state.py src/vibemix/midi/profile.py tests/state/test_loop_geometry.py tests/midi/test_state.py tests/midi/test_profile.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 23 - Crate Invoke Bridge SRC Gate

Suggested commit: `test(library-ui): pin crate invoke bridge contract`

Include:

- `tests/capabilities/test_library_window_contract.py`
- `tauri/src-tauri/capabilities/default.json`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Viber agent/tool implementation, library backend behavior, and generated IPC
  schema files.
- Co-host speech, prompt text, Sven TTS paths, runtime coach, and DROP-call hold
  lanes.
- Broad cleanup of `ipc.library.*` import/staleness messages. Current source
  still uses those for renderer↔sidecar library import and staleness actions;
  Crate's search/similar/curate/build-set/cue/chat/stats/model/embed actions use
  the separate Tauri `invoke()` bridge.

Reason:

- H4 asks for a source-level proof that Crate/Viber actions are both-ends wired
  before anyone says "Crate is fully wired." This package strengthens the
  existing desktop capability contract so it pins every Crate Tauri command,
  including the previously omitted `library_cue_folder`, and also pins the live
  `library://viber-tool` event tape from Rust bridge to frontend listener.

Proof before staging:

- `uv run pytest -q tests/capabilities/test_library_window_contract.py`
- `uv run pytest -q tests/security/test_tauri_plugin_macos_permissions_wired.py tests/repo/test_tauri_activation_policy.py tests/repo/test_tauri_dev_command.py`
- `uv run ruff check tests/capabilities/test_library_window_contract.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tests/capabilities/test_library_window_contract.py tauri/src-tauri/capabilities/default.json .planning/handoffs/2026-05-31-package-checklist.md`

## Package 24 - HEARTBEAT Silence Escape Hatch

Suggested commit: `fix(coach): let heartbeat stay silent without a grounded read`

Include:

- `src/vibemix/state/prompt_builder.py`
- `tests/state/test_coach.py`
- `tests/agent/test_coach_prompt_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime loop scheduling, `src/vibemix/runtime/coach.py`, `session.say()`, TTS
  behavior, and live app control.
- DROP-call / Mix Timing Oracle hold-lane files:
  `src/vibemix/state/drop_predict.py`,
  `src/vibemix/state/event_detector.py`,
  `tests/state/test_drop_predict.py`, and
  `tests/state/test_event_detector_drop.py`.
- New audio/device heuristics. EventDetector already gates auto-events on true
  music presence; this package only changes the HEARTBEAT task's model contract.

Reason:

- H3 asks for a grounding audit of idle HEARTBEAT speech. Current source still
  told the co-host "Always reply with something fresh; don't go silent," which
  pushes the model toward filler when the correct no-slop behavior is silence.
  This package changes HEARTBEAT to sound-only-or-silence, preserves the no
  coaching-advice-without-real-move rule, and pins tests so the old anti-mute
  wording cannot return unnoticed.

Proof before staging:

- `uv run pytest -q tests/state/test_coach.py::test_task_heartbeat_LOAD_BEARING_silence_escape_hatch tests/state/test_coach.py::test_build_prompt_format tests/agent/test_coach_prompt_grounding.py::test_build_prompt_uses_real_evidence_registry_not_mocks`
- `uv run pytest -q tests/state/test_coach.py tests/agent/test_coach_prompt_grounding.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py tests/prompts/test_negative_dict.py`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
- `uv run ruff check src/vibemix/state/prompt_builder.py tests/state/test_coach.py tests/agent/test_coach_prompt_grounding.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/state/prompt_builder.py tests/state/test_coach.py tests/agent/test_coach_prompt_grounding.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 25 - Runtime HEARTBEAT Speak Gate

Suggested commit: `fix(cohost): silence low-value heartbeat narration`

Include:

- `src/vibemix/runtime/speak_gate.py`
- `src/vibemix/runtime/coach.py`
- `tests/runtime/test_speak_gate.py`
- `tests/runtime/test_coach.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Prompt/persona copy in `src/vibemix/prompts/matrix.py` and
  `src/vibemix/state/prompt_builder.py`.
- Fixed-text `session.say()` paths, DROP-call / Mix Timing Oracle hold-lane
  files, TTS provider behavior, and any change to MOSS voice selection.
- Novelty scoring or long-window context rewrites. This is the first safe
  runtime gate, not the full X1 value model.

Reason:

- X1's live capture showed Sven speaking accurate but low-value HEARTBEAT
  descriptions too often. This package moves the first value decision upstream
  of the LLM: a plain HEARTBEAT with no grounded voice payload is silent by
  default, while manual/user speech and structural events keep the existing
  reaction path. The citation/slop filters remain the safety gate; this only
  prevents true-but-worthless describe-bank calls from being generated.

Proof before staging:

- `uv run pytest -q tests/runtime/test_speak_gate.py tests/runtime/test_coach.py::test_coach_03_event_fire_path tests/runtime/test_coach.py::test_coach_10_manual_trigger tests/runtime/test_coach.py::test_coach_14_plain_heartbeat_stays_silent tests/runtime/test_coach.py::test_coach_15_manual_heartbeat_reaches_model`
- `uv run pytest -q tests/runtime/test_speak_gate.py tests/runtime/test_coach.py tests/runtime/test_coach_cancel_wiring.py tests/runtime/test_coach_citation_publish.py`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
- `uv run ruff check src/vibemix/runtime/speak_gate.py src/vibemix/runtime/coach.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/runtime/speak_gate.py src/vibemix/runtime/coach.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 26 - Learn AIM Live Coach Frame

Suggested commit: `feat(coach): frame live coaching with learn aim`

Include:

- `src/vibemix/coach/prompt_fragments.py`
- `src/vibemix/learn/coaching_aim.py`
- `src/vibemix/prompts/matrix.py`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/agent/cache.py`
- `src/vibemix/runtime/coach.py`
- `src/vibemix/__main__.py`
- `tests/learn/test_coaching_aim.py`
- `tests/prompts/test_coaching_aim.py`
- `tests/agent/test_coaching_aim_prompt.py`
- `tests/agent/test_cache.py`
- `tests/runtime/test_coach.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Any new musical/audio claim, citation grammar source, slop-filter relaxation,
  or learned-progress write path.
- DROP-call speech / Mix Timing Oracle hold-lane files, MOSS provider behavior,
  voice-picker UI, and long-window/rich-context X4 rewrites.
- Hype-mode prompts. The AIM frame is coach-mode-only and fixed-string only.

Reason:

- X3's packet identifies a half-open Learn loop: the live runtime credits cited
  demonstrations into the skill tree, but Sven has no fixed coaching aim from
  the Competent-not-Mastered frontier. This package resolves a deterministic
  Learn AIM at session start, injects it as a coach-mode relevance frame, and
  refreshes that frame after a live credit can change the frontier. The AIM is
  not evidence; it never lowers the grounding bar or licenses feed-forward
  prescriptions in the live ear.

Proof before staging:

- `uv run pytest -q tests/learn/test_coaching_aim.py tests/prompts/test_coaching_aim.py tests/agent/test_coaching_aim_prompt.py tests/agent/test_cache.py::test_set_system_instruction_body_updates_future_padded_body tests/runtime/test_coach.py::test_coach_16_live_credit_refreshes_coaching_aim`
- `uv run pytest -q tests/learn/test_coaching_aim.py tests/learn/test_skill_tree.py tests/prompts/test_coaching_aim.py tests/prompts/test_matrix.py tests/agent/test_coaching_aim_prompt.py tests/agent/test_coach_prompt_grounding.py tests/agent/test_dj_cohost.py::test_resolve_prompt_cell_uses_shared_lens tests/agent/test_dj_cohost.py::test_resolve_prompt_cell_cold_path_byte_identical tests/agent/test_dj_cohost.py::test_resolve_prompt_cell_lens_wins_over_live_mood tests/agent/test_dj_cohost.py::test_resolve_prompt_cell_corrupt_lens_falls_back_no_crash tests/runtime/test_coach.py::test_coach_16_live_credit_refreshes_coaching_aim tests/runtime/test_coach.py::test_coach_14_plain_heartbeat_stays_silent tests/runtime/test_coach.py::test_coach_15_manual_heartbeat_reaches_model tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
- `uv run ruff check src/vibemix/coach/prompt_fragments.py src/vibemix/learn/coaching_aim.py src/vibemix/prompts/matrix.py src/vibemix/agent/dj_cohost.py src/vibemix/agent/cache.py src/vibemix/runtime/coach.py src/vibemix/__main__.py tests/learn/test_coaching_aim.py tests/prompts/test_coaching_aim.py tests/agent/test_coaching_aim_prompt.py tests/agent/test_cache.py tests/runtime/test_coach.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/coach/prompt_fragments.py src/vibemix/learn/coaching_aim.py src/vibemix/prompts/matrix.py src/vibemix/agent/dj_cohost.py src/vibemix/agent/cache.py src/vibemix/runtime/coach.py src/vibemix/__main__.py tests/learn/test_coaching_aim.py tests/prompts/test_coaching_aim.py tests/agent/test_coaching_aim_prompt.py tests/agent/test_cache.py tests/runtime/test_coach.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 27 - FLX4 Zero-Traffic Sniff Diagnostic

Suggested commit: `fix(midi): explain zero-frame controller sniffs`

Include:

- `scripts/sniff_controller.py`
- `tests/midi/test_sniff_controller.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Runtime MIDI listener behavior, FLX4 profile mappings, controller-state
  decoding, live co-host claim guards, and any app-control automation.
- Live proof archives. This package makes the diagnostic JSON more actionable;
  it does not claim a live controller fix.

Reason:

- Live FLX4 proof on 2026-06-02 repeatedly showed macOS exposing a `DDJ-FLX4`
  input port while both poll and callback sniffs saw zero supported CC/note
  frames during physical controller movement. The raw summary (`frames: 0`) was
  easy to misread as an app bug or missing proof. This package keeps the frame
  JSON schema unchanged and adds a bounded diagnosis plus next action to the
  final summary line so future Codex/Claude/live rig passes can archive the
  exact setup state: frames observed versus visible port with no supported MIDI
  traffic.

Proof before staging:

- `uv run pytest -q tests/midi/test_sniff_controller.py`
- `uv run ruff check scripts/sniff_controller.py tests/midi/test_sniff_controller.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- scripts/sniff_controller.py tests/midi/test_sniff_controller.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 28 - HEARTBEAT Pacing Retune

Suggested commit: `fix(cohost): slow heartbeat pacing after speak gate`

Include:

- `src/vibemix/audio/constants.py`
- `tests/audio/test_constants.py`
- `tests/state/test_event_detector.py`
- `tests/state/test_hype_cooldown_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/runtime/coach.py`, prompt text, `src/vibemix/state/event_detector.py`,
  DROP-call speech, and any session-cap or describe-bank-budget implementation.
- New generated text, new citation grammar, new claim permissions, or any live app
  control. This package only changes the HEARTBEAT metronome constant and its pins.

Reason:

- X1's runtime speak gate already makes a plain HEARTBEAT with no grounded voice
  payload silent before the LLM call, but the detector can still offer HEARTBEAT
  opportunities every 45 seconds. Retuning `HEARTBEAT_SEC` to 180 seconds follows
  the verified X1 threshold while avoiding the dirty speech/drop lanes. It reduces
  residual low-value "still hearing the groove" opportunities without changing
  structural events, manual reactions, or grounded coach lines.

Proof before staging:

- `uv run pytest -q tests/audio/test_constants.py tests/state/test_event_detector.py tests/state/test_hype_cooldown_grounding.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py::test_coach_14_plain_heartbeat_stays_silent tests/runtime/test_coach.py::test_coach_15_manual_heartbeat_reaches_model`
- `uv run pytest -q tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
- `uv run ruff check src/vibemix/audio/constants.py tests/audio/test_constants.py tests/state/test_event_detector.py tests/state/test_hype_cooldown_grounding.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/audio/constants.py tests/audio/test_constants.py tests/state/test_event_detector.py tests/state/test_hype_cooldown_grounding.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 29 - Learn Beatmatch Practice Driver

Suggested commit: `feat(learn): wire owned beatmatch practice driver`

Include:

- `src/vibemix/learn/beatmatch_practice_driver.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/__main__.py`
- `tests/learn/test_beatmatch_practice_driver.py`
- `tests/learn/test_ipc_handlers_dispatch.py`
- `tests/learn/test_lesson_flow_contract.py`
- `tests/learn/test_lesson_runtime_smoke.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/learn/test_practice_loop.py`
- `tests/repo/test_live_reality_pins.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Sven/co-host speech, prompt text, `src/vibemix/runtime/coach.py`, DROP-call
  speech, and any external Rekordbox/FLX4 beatmatch claim.
- New live audio output devices, user-file mutation, packaged-build claims, or
  fake external deck identity. This package is Learn-owned practice state only.
- Any relaxation of the cited `BEATMATCH_GRADED` credit gate or the
  Competent-before-Mastered skill-tree floor.

Reason:

- The Learn beatmatch producer and recognizer branch existed, and
  `LessonRuntime` had a grading hook, but live boot never supplied the
  `beatmatch_practice_loader`, leaving the shipped path functionally orphaned.
  This package adds a small Learn-owned practice driver for L2.01/L2.02, records
  matched beatmatch lesson actions, grades them immediately through the existing
  EvidenceRegistry-backed producer, and strengthens the repo pin so a future
  hook-only regression cannot pass green.

Proof before staging:

- `uv run pytest -q tests/learn/test_beatmatch_practice_driver.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_lesson_flow_contract.py tests/learn/test_lesson_runtime_smoke.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_practice_loop.py tests/repo/test_live_reality_pins.py`
- `uv run ruff check src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/learn/runtime.py src/vibemix/__main__.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_lesson_flow_contract.py tests/learn/test_lesson_runtime_smoke.py tests/learn/test_runtime_evidence_grounding.py tests/repo/test_live_reality_pins.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/learn/runtime.py src/vibemix/__main__.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_lesson_flow_contract.py tests/learn/test_lesson_runtime_smoke.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_practice_loop.py tests/repo/test_live_reality_pins.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 30 - Learn Cue Placement Practice Driver

Suggested commit: `feat(learn): wire owned cue placement practice driver`

Include:

- `src/vibemix/learn/cue_placement_practice_driver.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/__main__.py`
- `tests/learn/test_cue_placement_practice_driver.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/learn/test_cue_practice.py`
- `tests/repo/test_live_reality_pins.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Sven/co-host speech, prompt text, `src/vibemix/runtime/coach.py`, DROP-call
  speech, and any external Rekordbox/FLX4 cue-placement claim.
- User-library hot-cue writeback, Serato/Rekordbox tag mutation, L3 mastered
  hotcue writeback, and any `library/export_serato.py` changes.
- Any relaxation of the cited `CUE_PLACEMENT_GRADED` credit gate or the
  Competent-before-Mastered skill-tree floor.

Reason:

- The Learn cue-placement producer and recognizer branch existed, and
  `LessonRuntime` had a grading hook, but live boot never supplied the
  `cue_placement_practice_loader`, leaving the shipped path functionally
  orphaned. This package adds a small Learn-owned practice driver for L2.10,
  records the authored hot-cue action on deck B, grades it immediately through
  the existing EvidenceRegistry-backed producer, and strengthens the repo pin so
  a future hook-only regression cannot pass green.

Proof before staging:

- `uv run pytest -q tests/learn/test_cue_placement_practice_driver.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_cue_practice.py tests/repo/test_live_reality_pins.py`
- `uv run ruff check src/vibemix/learn/cue_placement_practice_driver.py src/vibemix/learn/runtime.py src/vibemix/__main__.py tests/learn/test_cue_placement_practice_driver.py tests/learn/test_runtime_evidence_grounding.py tests/repo/test_live_reality_pins.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/learn/cue_placement_practice_driver.py src/vibemix/learn/runtime.py src/vibemix/__main__.py tests/learn/test_cue_placement_practice_driver.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_cue_practice.py tests/repo/test_live_reality_pins.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 31 - Library Freshness Watcher Direct Tests

Suggested commit: `test(library): pin freshness watcher loop`

Include:

- `tests/library/test_watcher.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/library/watcher.py`, `src/vibemix/library/staleness.py`, and
  `src/vibemix/__main__.py`; this package is a regression pin only.
- UI freshness copy, import actions, Viber setup flows, and any live app control.

Reason:

- The shipped library freshness watcher is user-visible Viber/set-prep
  infrastructure. Existing `test_staleness.py` covers wrapper behavior and
  payload policy; this package pins the dedicated watcher module directly:
  cache-path fallback, dynamic cache/source watch targets across loop
  iterations, and duplicate stale-signature suppression.

Proof before staging:

- `uv run pytest -q tests/library/test_watcher.py tests/library/test_staleness.py`
- `uv run ruff check tests/library/test_watcher.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tests/library/test_watcher.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 32 - MOSS-only PyInstaller TTS Hidden Import Cleanup

Suggested commit: `fix(packaging): stop bundling gemini tts leaf`

Include:

- `vibemix-core.macos.spec`
- `vibemix-core.windows.spec`
- `tests/sidecar/test_build_sidecar_rename.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/agent/_livekit_google_slim.py`, `src/vibemix/agent/tts_chain.py`,
  MOSS runtime/model download behavior, and LiveKit Gemini LLM brain transport.
- Google Cloud STT/TTS exclusion strings in the sidecar test; those remain
  intentional negative guards.

Reason:

- Product speech is local MOSS only, and local import proof shows
  `livekit.plugins.google.llm` does not import the beta `gemini_tts` leaf. The
  PyInstaller specs still bundled that dead TTS leaf and described "Gemini
  LLM/TTS" packaging. Remove the unused hidden import while keeping the slim
  Google LLM leaf and the explicit Google Cloud STT/TTS anti-collection guard.

Proof before staging:

- `uv run python - <<'PY'` local import proof that
  `vibemix.agent._livekit_google_slim.google_llm_class()` resolves and
  `livekit.plugins.google.llm` source does not reference `gemini_tts`, `tts`,
  `stt`, `google.cloud`, or `grpc`.
- `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_use_slim_livekit_google_collection`
- `uv run ruff check tests/sidecar/test_build_sidecar_rename.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- vibemix-core.macos.spec vibemix-core.windows.spec tests/sidecar/test_build_sidecar_rename.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 33 - First-run FLX4 Controller Hint

Suggested commit: `fix(wizard): name flx4 usb setup on controller timeout`

Include:

- `tauri/ui/src/wizard/components/controller-probe.ts`
- `tauri/ui/tests/wizard.tokens.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- MIDI probe runtime behavior, `tauri/ui/src/wizard/router.ts`, backend MIDI
  listen IPC, Learn controller SVGs, and any live hardware claim. This package
  is UI copy plus a render regression only.
- Wizard audio/BlackHole setup, MOSS model install, and library import CTAs.

Reason:

- The controller step could time out while only saying generic "no midi
  received" / "plug one in" copy. For a first-run user with the documented
  default controller, that misses the practical setup clue: connect the
  DDJ-FLX4 over USB and press a physical pad/cue/play control. This package adds
  that short timeout hint without adding a modal, changing probe behavior, or
  claiming the controller is detected.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/wizard.tokens.test.ts`
- `npm --prefix tauri/ui test -- src/wizard/__tests__/first-run-continuity.spec.ts tests/wizard.tokens.test.ts`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/wizard/components/controller-probe.ts tauri/ui/tests/wizard.tokens.test.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 34 - Shell MOSS Voice Readiness Badge

Suggested commit: `fix(shell): surface moss voice readiness`

Include:

- `tauri/ui/src/shell/VoiceReadinessBadge.ts`
- `tauri/ui/src/shell/app.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/voice-readiness-badge.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Backend model download/install logic, hosted MOSS archive decisions, PyInstaller
  model bundling, startup stderr copy, and runtime TTS provider behavior.
- Duplicating the Crate model setup card. This shell badge is a small readiness
  readout and route into Crate, not a second installer.

Reason:

- MOSS is the only product voice. A clean machine can boot muted when the model
  is absent, and the existing model setup card is inside Crate. The live deck
  needs a compact, honest status surface so a user can see `voice missing` /
  `voice manual` and click into the existing setup path instead of thinking Sven
  is simply broken.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/voice-readiness-badge.spec.ts tests/shell/library-freshness-badge.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/VoiceReadinessBadge.ts tauri/ui/src/shell/app.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/voice-readiness-badge.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 37 - X4 Live Coach Deep Router Reserve

Suggested commit: `fix(llm): reserve deep live coach route`

Include:

- `src/vibemix/llm/_router_config.py`
- `tests/llm/test_model_router.py`
- `tests/llm/test_model_router_live_coach_deep.py`
- `tests/e2e/test_phase_41_latency_stack_integration.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Prompt text, `agent/dj_cohost.py`, `src/vibemix/runtime/coach.py`, and the
  X4 sectioned context bundle implementation.
- Any model upgrade claim. The deep route intentionally resolves to the same
  model and STANDARD tier as `live_coach` today.

Reason:

- X4 needs a named model-router seam before the rich-context packet can become
  a product path. Reserving `live_coach_deep` keeps future deep-context routing
  in the allowlisted router table instead of creating hardcoded model literals
  at call sites. This is structural only: no current speech behavior changes.

Proof before staging:

- `uv run pytest -q tests/llm/test_model_router.py tests/llm/test_model_router_live_coach_deep.py tests/e2e/test_phase_41_latency_stack_integration.py`
- `uv run pytest -q tests/bench/test_no_model_literal.py tests/library/test_pricing.py tests/library/test_cost.py tests/library/test_session_meter.py`
- `uv run ruff check src/vibemix/llm/_router_config.py tests/llm/test_model_router.py tests/llm/test_model_router_live_coach_deep.py tests/e2e/test_phase_41_latency_stack_integration.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/llm/_router_config.py tests/llm/test_model_router.py tests/llm/test_model_router_live_coach_deep.py tests/e2e/test_phase_41_latency_stack_integration.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 38 - X4 Set Window Context Renderer

Suggested commit: `fix(cohost): add set window context renderer`

Include:

- `src/vibemix/state/deck_context.py`
- `tests/state/test_deck_context.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/runtime/coach.py`, `src/vibemix/__main__.py`,
  `src/vibemix/agent/dj_cohost.py`, prompt text, model route selection, live
  speech, TTS behavior, and any live FLX4/Rekordbox proof claim.
- The sectioned `AICoach.evidence_line` prompt rewrite. This package is only
  the bounded long-window TEXT packet and its validator.

Reason:

- X4 needs a 4-5 minute deep-context artifact before it can be wired into Sven.
  The renderer summarizes existing state streams as structured text, lifts the
  move-history cap only inside that packet, and hard-codes the master-only
  honesty atoms: one bounded P1 master mix, no attached per-deck audio, no
  isolated-deck claim, and no transition/quality verdict field.

Proof before staging:

- `uv run pytest -q tests/state/test_deck_context.py -k set_window_context`
- `uv run pytest -q tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_perceive.py tests/state/test_coach_prompt_diet.py`
- `uv run ruff check src/vibemix/state/deck_context.py tests/state/test_deck_context.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/state/deck_context.py tests/state/test_deck_context.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 39 - Psytrance Profile Memory Allowlist

Suggested commit: `fix(profile): allow psytrance taste memory`

Include:

- `src/vibemix/profile/schema.py`
- `tests/profile/test_schema.py`
- `tests/profile/test_builder.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Event-router chains, BPM fallback bands, runtime prompt text, Sven speech,
  Viber tools, deck polling, genre profile JSON, and live FLX4/Rekordbox proof.

Reason:

- Packages 35C/35D made `psytrance` a citable source genre and a routeable
  coarse event-chain genre, but the long-term DJ profile privacy schema still
  rejected `preferred_genre="psytrance"`. That made the profile builder ignore
  sustained psytrance evidence and fall back to a prior/unknown taste memory.
  This package aligns the privacy allowlist with the already-shipped genre
  profile/event-router surface without widening the schema to arbitrary genres.

Proof before staging:

- `uv run pytest -q tests/profile/test_schema.py tests/profile/test_builder.py`
- `uv run pytest -q tests/state/test_genre_router.py tests/audio/test_phase17_constants.py tests/state/test_genre_autodetect.py`
- `uv run ruff check src/vibemix/profile/schema.py tests/profile/test_schema.py tests/profile/test_builder.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/profile/schema.py tests/profile/test_schema.py tests/profile/test_builder.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 40 - Shipped Genre Profile Memory Allowlist

Suggested commit: `fix(profile): remember all shipped genre profiles`

Include:

- `src/vibemix/profile/schema.py`
- `tests/profile/test_schema.py`
- `tests/profile/test_builder.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New genre profiles, event-router chain registration for non-router genres,
  prompt text, Sven speech, DSP scoring thresholds, runtime settings UI, and
  live FLX4/Rekordbox proof.

Reason:

- Package 39 fixed the immediate psytrance miss, but the long-term profile
  allowlist still did not cover every shipped genre profile. The live
  profile detector can produce `disco`, `drum_and_bass`, and `pop`; if those
  evidence labels are sustained, the privacy schema should allow the compact
  local taste memory to remember them. This remains a closed allowlist:
  arbitrary labels such as `dubstep` still fail schema validation.

Proof before staging:

- `uv run pytest -q tests/profile/test_schema.py tests/profile/test_builder.py`
- `uv run pytest -q tests/state/test_genre_profile.py tests/state/test_genre_autodetect.py`
- `uv run ruff check src/vibemix/profile/schema.py tests/profile/test_schema.py tests/profile/test_builder.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/profile/schema.py tests/profile/test_schema.py tests/profile/test_builder.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 41 - Profile Genre Evidence Alias Normalization

Suggested commit: `fix(profile): normalize genre evidence aliases`

Include:

- `src/vibemix/profile/builder.py`
- `tests/profile/test_builder.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Schema expansion beyond the closed allowlist, runtime settings behavior,
  event-router chains, prompt text, Sven speech, source parsers, and live
  FLX4/Rekordbox proof.

Reason:

- Source/library/prototype evidence can carry real scene labels that are not
  byte-identical to profile filenames: `goa`, `full-on`, `trance`, `dnb`,
  `jungle`, `hardtechno`, `hard-tek`, `tech house`, and `nu-disco`. The profile
  builder previously ignored those keys even when they had sustained citations.
  Normalize only known aliases into the closed profile allowlist; unknown
  labels still degrade to `unknown` and cannot pollute local taste memory.

Proof before staging:

- `uv run pytest -q tests/profile/test_builder.py tests/profile/test_schema.py`
- `uv run ruff check src/vibemix/profile/builder.py tests/profile/test_builder.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/profile/builder.py tests/profile/test_builder.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 42 - Shipped Genre Event-Chain Coverage

Suggested commit: `fix(genre): route shipped profiles safely`

Include:

- `src/vibemix/events/genres/__init__.py`
- `src/vibemix/events/genres/disco.py`
- `src/vibemix/events/genres/drum_and_bass.py`
- `src/vibemix/events/genres/pop.py`
- `src/vibemix/state/music_state.py`
- `src/vibemix/runtime/ws_bus.py`
- `tests/state/test_genre_router.py`
- `tests/state/test_genre_router_race.py`
- `tests/state/test_genre_autodetect.py`
- `tests/state/test_refresh.py`
- `tests/runtime/test_ws_bus_phase22_fields.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Prompt text, Sven speech, `src/vibemix/__main__.py`, `src/vibemix/runtime/coach.py`,
  new DSP thresholds, arbitrary genre strings outside the shipped profile
  allowlist, and live FLX4/Rekordbox proof.

Reason:

- Packages 39-41 made the profile layer recognize the shipped profile labels,
  but the event router still only had chains for `house`, `techno`,
  `psytrance`, `hard_tek`, and `unknown`. That meant a grounded full-library
  detection of `disco`, `drum_and_bass`, or `pop` could render as genre
  evidence while the live event chain still fell back to a coarse/unknown path.
  Add conservative routeable chains for the remaining shipped profiles:
  disco/pop get sub-arrival + phrase structure; drum-and-bass gets bass/drop
  structure with paired kill/re-entry. None inherit Hard Tek-only
  acid/distortion overlays.

Proof before staging:

- `uv run pytest -q tests/state/test_genre_router.py tests/state/test_genre_router_race.py tests/state/test_genre_autodetect.py tests/state/test_refresh.py tests/runtime/test_ws_bus_phase22_fields.py`
- `uv run pytest -q tests/state/test_genre_profile.py tests/state/test_genre_autodetect.py tests/profile/test_schema.py tests/profile/test_builder.py tests/audio/test_phase17_constants.py`
- `uv run ruff check src/vibemix/events/genres src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py tests/state/test_genre_router.py tests/state/test_genre_router_race.py tests/state/test_genre_autodetect.py tests/state/test_refresh.py tests/runtime/test_ws_bus_phase22_fields.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/events/genres/__init__.py src/vibemix/events/genres/disco.py src/vibemix/events/genres/drum_and_bass.py src/vibemix/events/genres/pop.py src/vibemix/state/music_state.py src/vibemix/runtime/ws_bus.py tests/state/test_genre_router.py tests/state/test_genre_router_race.py tests/state/test_genre_autodetect.py tests/state/test_refresh.py tests/runtime/test_ws_bus_phase22_fields.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 43 - Beat-Trusted Track Position Clock

Suggested commit: `fix(state): dead-reckon track position between polls`

Include:

- `src/vibemix/state/position_clock.py`
- `src/vibemix/platform/_track_macos.py`
- `src/vibemix/state/refresh.py`
- `tests/state/test_position_clock.py`
- `tests/test_track_macos.py`
- `tests/state/test_refresh.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/__main__.py`, `src/vibemix/runtime/coach.py`, DROP-call speech,
  prompt text, new Mixxx dependencies, per-deck audio claims, and any live-proof
  assertions. Do not change the public `NowPlayingSnapshot` protocol in this
  slice; macOS keeps the legacy `track_info.snapshot()` dict extension.

Reason:

- The Mixxx goldmine packet identified track position as the load-bearing clock
  for drop ETA, phrase anchors, and "N bars to" coaching. The current
  nowplaying-cli source polls at about 1 Hz, while the state refresh loop runs
  much faster. Add a small, deterministic position-clock helper that advances
  the last raw seconds value between OS polls only when the BPM lock is
  trustworthy. BPM is an honesty gate, not a seconds-to-beats unit conversion:
  position advances by elapsed wall time times playback rate, clamps to
  duration, and falls back to raw 1 Hz position when the beat lock is weak,
  stale, or missing. This lands the substrate without enabling DROP speech or
  claiming live on-beat proof.

Proof before staging:

- `uv run pytest -q tests/state/test_position_clock.py tests/test_track_macos.py tests/state/test_refresh.py`
- `uv run pytest -q tests/state/test_drop_predict.py tests/state/test_event_detector_drop.py tests/runtime/test_drop_reaction.py`
- `uv run ruff check src/vibemix/state/position_clock.py src/vibemix/platform/_track_macos.py src/vibemix/state/refresh.py tests/state/test_position_clock.py tests/test_track_macos.py tests/state/test_refresh.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/state/position_clock.py src/vibemix/platform/_track_macos.py src/vibemix/state/refresh.py tests/state/test_position_clock.py tests/test_track_macos.py tests/state/test_refresh.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 44 - X4 Set Window Context Prompt Attachment

Suggested commit: `fix(cohost): attach set window context on full prompts`

Include:

- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/state/deck_context.py`
- `tests/agent/test_dj_cohost.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/__main__.py`, `src/vibemix/runtime/coach.py`, DROP-call speech,
  new co-host line templates, new model literals, sectioned prompt relayout,
  live-proof claims, and any change to the diet/ack prompt cadence.

Reason:

- X4's safe substrate already exists in source: `render_set_window_context()`
  builds a normalized master-only long-window text digest, and
  `live_coach_deep` is already reserved in the model router. The missing wire is
  that the digest is not attached to Sven's live prompt. Add it only to the full
  60s audio path, not the 6s diet path, so the contract atom
  `audio_attached=P1_only_last_60-90s` stays true and routine ack prompts stay
  small.

Proof before staging:

- `uv run pytest -q tests/agent/test_dj_cohost.py tests/state/test_deck_context.py tests/llm/test_model_router_live_coach_deep.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
- `uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py tests/agent/test_dj_cohost.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py tests/agent/test_dj_cohost.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 45 - First-Run Deck Route Clarity

Suggested commit: `fix(wizard): explain deck-aware blackhole routing`

Include:

- `tauri/ui/src/wizard/components/blackhole-step.ts`
- `tauri/ui/src/wizard/__tests__/blackhole-step.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Audio capture/runtime routing, `src/vibemix/__main__.py`, `src/vibemix/runtime/coach.py`,
  co-host speech, Tauri IPC schema changes, installer downloads, and live FLX4 proof claims.

Reason:

- The first-run BlackHole step previously went silent once any BlackHole variant
  was installed. That hides the load-bearing product distinction users hit on
  real Rekordbox rigs: BlackHole 2ch is enough for master-output listening, but
  deck-aware proof needs a Multi-Output/Aggregate route with the FLX4 plus
  BlackHole 16ch, with deck 1 on channels 1/2 and deck 2 on channels 3/4.
  Surface that distinction in the wizard so setup failure reads as an actionable
  route issue, not an invisible model/co-host problem.

Proof before staging:

- `npm --prefix tauri/ui test -- src/wizard/__tests__/blackhole-step.spec.ts`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/wizard/components/blackhole-step.ts tauri/ui/src/wizard/__tests__/blackhole-step.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 46 - Tauri MOSS Source Release Gate

Suggested commit: `fix(packaging): require moss source for tauri builds`

Include:

- `tauri/src-tauri/tauri.conf.json5`
- `tests/repo/test_tauri_dev_command.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- PyInstaller specs, model download manifests, local TTS runtime behavior,
  `src/vibemix/__main__.py`, app UI copy, release workflow signing, and live
  MOSS ear-pass claims.

Reason:

- Product speech is local MOSS-only. `prepare_tauri_build.py` already has a
  `--require-moss-source` release gate that rejects packages without either a
  bundled MOSS model tree or pinned `VIBEMIX_MOSS_TTS_ARCHIVE_*` metadata, but
  direct local `cargo tauri build` still invoked the preparation script without
  that flag. Wire the gate into `tauri.conf.json5` so the normal Tauri packaging
  path cannot emit a voiceless app by accident.

Proof before staging:

- `uv run pytest -q tests/repo/test_tauri_dev_command.py tests/install/test_prepare_tauri_build.py tests/install/test_sidecar_bundle_ready.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/src-tauri/tauri.conf.json5 tests/repo/test_tauri_dev_command.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 47 - Honest Live Quit Guard Copy

Suggested commit: `fix(session): stop calling live quit guard a recording proof`

Include:

- `tauri/ui/src/session/quit-guard.ts`
- `tauri/ui/tests/session/quit-guard.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Recorder consent/runtime plumbing, `src/vibemix/__main__.py`, local audio
  capture behavior, titlebar layout, Tauri tray Rust code, and co-host speech.

Reason:

- The quit guard is keyed off `status.livekit === "ok"` because that is the
  frontend's active live-session signal. The UI does not currently carry a
  dedicated recorder-active/recording-consent bit, so the previous warning
  text "your set is recording" overclaimed what the state can prove. Keep the
  quit protection, but make the wording honest: the live session is running.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/session/quit-guard.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/session/quit-guard.ts tauri/ui/tests/session/quit-guard.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 48 - Release Artifact MOSS Source Gate

Suggested commit: `fix(release): require moss source in artifact verifiers`

Include:

- `scripts/dist/check_sidecar_bundle_ready.py`
- `scripts/dist/check_macos_app_bundle_ready.py`
- `scripts/dist/check_macos_dmg_artifact_ready.py`
- `scripts/dist/check_macos_updater_artifact_ready.py`
- `scripts/dist/check_release_upload_dir_ready.py`
- `scripts/dist/check_updater_manifest_ready.py`
- `scripts/dist/check_windows_app_payload_ready.py`
- `scripts/dist/build_macos_local_dmg.sh`
- `scripts/win/build_local.ps1`
- `.github/workflows/release.yml`
- `tests/install/test_sidecar_bundle_ready.py`
- `tests/install/test_macos_app_bundle_ready.py`
- `tests/install/test_macos_dmg_artifact_ready.py`
- `tests/install/test_macos_local_dmg_build.py`
- `tests/install/test_macos_updater_artifact_ready.py`
- `tests/install/test_release_upload_dir_ready.py`
- `tests/install/test_updater_manifest_ready.py`
- `tests/install/test_windows_app_payload_ready.py`
- `tests/install/test_windows_packaging_paths.py`
- `tests/security/test_release_yml_signing_skips.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Bundling or hosting the MOSS model archive, PyInstaller spec data additions,
  runtime TTS behavior, `src/vibemix/__main__.py`, app UI voice-readiness copy,
  signing secrets, and live MOSS ear-pass claims.

Reason:

- MOSS is the only product voice. The sidecar checker already knows how to fail
  a release without a complete bundled MOSS model tree or pinned hosted archive
  metadata, but the macOS app/DMG/updater and Windows payload artifact verifiers
  did not expose or use that gate. Thread `--require-moss-source` through the
  artifact verifiers and turn it on in CI plus local rehearsal scripts so a
  voiceless package cannot pass readiness before signing/upload.

Proof before staging:

- `uv run pytest -q tests/install/test_sidecar_bundle_ready.py tests/install/test_macos_app_bundle_ready.py tests/install/test_macos_dmg_artifact_ready.py tests/install/test_macos_local_dmg_build.py tests/install/test_macos_updater_artifact_ready.py tests/install/test_release_upload_dir_ready.py tests/install/test_updater_manifest_ready.py tests/install/test_windows_app_payload_ready.py tests/install/test_windows_packaging_paths.py tests/security/test_release_yml_signing_skips.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- scripts/dist/check_sidecar_bundle_ready.py scripts/dist/check_macos_app_bundle_ready.py scripts/dist/check_macos_dmg_artifact_ready.py scripts/dist/check_macos_updater_artifact_ready.py scripts/dist/check_release_upload_dir_ready.py scripts/dist/check_updater_manifest_ready.py scripts/dist/build_macos_local_dmg.sh scripts/win/build_local.ps1 .github/workflows/release.yml tests/install/test_sidecar_bundle_ready.py tests/install/test_macos_app_bundle_ready.py tests/install/test_macos_dmg_artifact_ready.py tests/install/test_macos_local_dmg_build.py tests/install/test_macos_updater_artifact_ready.py tests/install/test_release_upload_dir_ready.py tests/install/test_updater_manifest_ready.py tests/install/test_windows_app_payload_ready.py tests/install/test_windows_packaging_paths.py tests/security/test_release_yml_signing_skips.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 49 - Honest Connected Controller Status

Suggested commit: `fix(status): show connected flx4 as controller-ready`

Include:

- `src/vibemix/runtime/ws_bus.py`
- `tests/runtime/test_ws_bus_status_tick.py`
- `tests/runtime/test_session_loop.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Controller decoder semantics, Course 3 operator actions, `src/vibemix/__main__.py`,
  co-host speech, runtime coach, and frontend layout.

Reason:

- The compact footer status badge should answer whether a controller is connected
  to vibemix. A connected DDJ-FLX4 with no decoded movement yet must not paint the
  controller LED red; the no-frame/no-move truth remains available in
  `deck_mixer.midi_activity` and Course 3 guidance.

Proof before staging:

- `uv run pytest -q tests/runtime/test_ws_bus_status_tick.py tests/runtime/test_session_loop.py::test_live_status_recheck_reports_visible_controller_without_midi_as_connected tests/runtime/test_ws_bus_deck_state.py::test_course3_operator_action_names_visible_controller_with_no_midi_traffic`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/runtime/ws_bus.py tests/runtime/test_ws_bus_status_tick.py tests/runtime/test_session_loop.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 50 - Speak Gate Describe-Bank Suppression

Suggested commit: `fix(cohost): suppress plain phase describe-bank turns`

Include:

- `src/vibemix/runtime/speak_gate.py`
- `tests/runtime/test_speak_gate.py`
- `tests/runtime/test_coach.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `src/vibemix/runtime/coach.py`, `src/vibemix/__main__.py`, prompts, MOSS/TTS,
  DROP-call speech, event detector timing, and citation grammar.

Reason:

- Sven should not spend voice on plain texture narration. The runtime already
  gates HEARTBEAT describe-bank turns, but plain PHASE and LAYER_ARRIVAL events
  can still ask the LLM for narration with no deterministic grounded voice
  payload. Extend the same subtractive gate to those low-value automatic events
  while preserving MIX_MOVE/TRACK_CHANGE and grounded payloads.

Proof before staging:

- `uv run pytest -q tests/runtime/test_speak_gate.py tests/runtime/test_coach.py::test_coach_14_plain_heartbeat_stays_silent tests/runtime/test_coach.py::test_coach_14_plain_phase_stays_silent`
- `uv run pytest -q tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/runtime/speak_gate.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 51 - Bundled MOSS Runtime Discovery

Suggested commit: `fix(tts): load bundled moss model in packaged sidecar`

Include:

- `src/vibemix/agent/local_tts.py`
- `scripts/dist/moss_bundle.py`
- `vibemix-core.macos.spec`
- `vibemix-core.windows.spec`
- `tests/agent/test_local_tts.py`
- `tests/install/test_moss_bundle_data.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Hosted MOSS archive decisions, Tauri UI voice-readiness copy, `src/vibemix/__main__.py`,
  runtime coach/speech behavior, live MOSS ear-pass claims, signing/notarization, and
  generated sidecar binaries.

Reason:

- MOSS is the only product voice. The release gates can require a complete bundled model
  tree, but the runtime still looked only at `VIBEMIX_MOSS_TTS_DIR` or the user's cache.
  That lets Kaan's dev cache mask a packaged clean-machine mute. Bundle the configured or
  cached MOSS tree into PyInstaller's `_internal/models/moss-tts-onnx/` layout and make
  the frozen runtime resolve that bundled tree before falling back to the dev cache.

Proof before staging:

- `uv run pytest -q tests/agent/test_local_tts.py tests/install/test_moss_bundle_data.py tests/install/test_sidecar_bundle_ready.py::test_require_moss_source_accepts_complete_bundled_model`
- `uv run ruff check src/vibemix/agent/local_tts.py scripts/dist/moss_bundle.py tests/agent/test_local_tts.py tests/install/test_moss_bundle_data.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/agent/local_tts.py scripts/dist/moss_bundle.py vibemix-core.macos.spec vibemix-core.windows.spec tests/agent/test_local_tts.py tests/install/test_moss_bundle_data.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 52 - PyInstaller Spec Target-Arch Build Fix

Suggested commit: `fix(packaging): stop passing target-arch to spec builds`

Include:

- `scripts/build_sidecar.py`
- `tests/sidecar/test_build_sidecar_rename.py`
- `tests/runtime_closeouts/test_universal2_sidecar.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- PyInstaller spec data changes, MOSS runtime behavior, generated sidecar binaries,
  Tauri UI, signing/notarization, and app runtime speech code.

Reason:

- Current PyInstaller rejects `--target-arch` when a `.spec` file is supplied, so
  the release sidecar rebuild fails before it can refresh IPC or bundle MOSS. Keep
  `--target-arch` as the requested matrix arch/triple selector, but do not pass it
  through to PyInstaller; the post-build `lipo -archs` assertion remains the actual
  single-arch safety gate.

Proof before staging:

- `uv run pytest -q tests/sidecar/test_build_sidecar_rename.py::test_run_pyinstaller_does_not_pass_target_arch_with_spec tests/sidecar/test_build_sidecar_rename.py::test_run_pyinstaller_installs_local_ai_extra tests/runtime_closeouts/test_universal2_sidecar.py::test_build_sidecar_supports_target_arch`
- `uv run ruff check scripts/build_sidecar.py tests/sidecar/test_build_sidecar_rename.py tests/runtime_closeouts/test_universal2_sidecar.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- scripts/build_sidecar.py tests/sidecar/test_build_sidecar_rename.py tests/runtime_closeouts/test_universal2_sidecar.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 53 - PyInstaller Spec Helper Import Path

Suggested commit: `fix(packaging): let specs import bundle helpers`

Include:

- `vibemix-core.macos.spec`
- `vibemix-core.windows.spec`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Sidecar build wrapper behavior, runtime MOSS lookup, tests, generated sidecar binaries,
  Tauri UI, signing/notarization, and app speech behavior.

Reason:

- PyInstaller executes the `.spec` file in a namespace that did not include the repo
  root on `sys.path`, so importing `scripts.dist.moss_bundle` failed before Analysis
  could run. Add the spec directory to `sys.path` before importing shared bundle
  helpers so release builds can use the MOSS data collector.

Proof before staging:

- `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec --target-arch arm64`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- vibemix-core.macos.spec vibemix-core.windows.spec .planning/handoffs/2026-05-31-package-checklist.md`

## Package 54 - Live Learn QA Hands And L1.03 Hardware Action Fix

Suggested commit: `fix(learn): accept live hardware practice actions`

Include:

- `src/vibemix/runtime/dev_mcp_server.py`
- `tests/runtime/test_dev_mcp_server.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/learn/transcripts/course_1_anatomy/03_channel_strip.json`
- `tests/learn/test_ipc_handlers_dispatch.py`
- `tests/learn/test_lesson_flow_contract.py`
- `tests/learn/test_lesson_runtime_smoke.py`
- `tauri/ui/tests/learn/browser-python-beginner-path.pw.ts`
- `src/vibemix/prompts/matrix.py`
- `tests/prompts/test_matrix.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Tauri UI visual redesign, packaged-build claims, generated sidecar binaries, Sven
  fixed-line/DROP speech, real FLX4 beatmatch scoring claims, and any claim that
  Viber is the live co-host. This package adds an operator QA hand and fixes the
  first Learn hardware action getting stuck; it does not claim the whole Learn
  product is complete.

Reason:

- The signed app opened into a stale/broken Learn experience: L1.03 kept asking for
  a huge extreme EQ motion even though live FLX4 MIDI was observed. Add an MCP QA
  hand that can start a lesson, send the same typed websocket frames a human action
  would produce, and summarize Learn frames. Then make matched hardware CC actions
  advance and complete after a short action settle instead of sitting behind the
  skip-only dwell floor. Tighten the prompt matrix at the same time so Sven does
  not turn unsupported transition/blend guesses into confident coaching.

Proof before staging:

- Source live run with `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix`; MCP
  `tool_learn_probe_async(... lesson_id="L1.03", control_id="eq_hi:A", source="midi",
  value=65, prev_value=64 ...)` observed `ipc.learn.lesson_loaded`,
  `ipc.learn.highlight`, `ipc.learn.advance`, `ipc.learn.complete_lesson`, and final
  progress with `L1.03.completed: true`.
- `uv run pytest -q tests/runtime/test_dev_mcp_server.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_advancement_gates.py tests/learn/test_lesson_flow_contract.py tests/learn/test_lesson_runtime_smoke.py tests/prompts/test_matrix.py`
- `uv run ruff check src/vibemix/runtime/dev_mcp_server.py src/vibemix/learn/runtime.py src/vibemix/prompts/matrix.py tests/runtime/test_dev_mcp_server.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_lesson_flow_contract.py tests/learn/test_lesson_runtime_smoke.py tests/prompts/test_matrix.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/runtime/dev_mcp_server.py tests/runtime/test_dev_mcp_server.py src/vibemix/learn/runtime.py src/vibemix/learn/transcripts/course_1_anatomy/03_channel_strip.json tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_lesson_flow_contract.py tests/learn/test_lesson_runtime_smoke.py tauri/ui/tests/learn/browser-python-beginner-path.pw.ts src/vibemix/prompts/matrix.py tests/prompts/test_matrix.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 55 - Settings Overlay Keeps Current Surface

Suggested commit: `fix(shell): keep settings as an overlay`

Include:

- `tauri/ui/src/shell/app.ts`
- `tauri/ui/tests/shell/settings-nav.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Settings drawer group internals, visual theme/token rewrites, Learn runtime
  behavior, native packaging scripts, and product claims that the whole first-run
  flow is complete. This package only removes the fake Settings stage behind the
  existing drawer.

Reason:

- In the packaged app, choosing Settings switched the main stage to a blank
  "Not set up yet" Settings placeholder while also opening the real Settings
  drawer. That made the app feel unfinished and cluttered. Settings is an
  overlay control surface, not a task route; keep the current Deck/Crate/Learn
  surface active behind it and close the drawer on later real-surface navigation.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/settings-nav.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/app.ts tauri/ui/tests/shell/settings-nav.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 56 - Folded Learn Practice-First Layout

Suggested commit: `fix(learn-ui): make folded learn practice first`

Include:

- `tauri/ui/src/shell/app.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/learn-folded-layout.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Learn runtime semantics, lesson transcript copy, Earned Wall scoring rules,
  Settings drawer internals, packaging scripts, and any claim that the whole Learn
  journey is finished. This package only fixes the shell-embedded Learn hierarchy
  and layout.

Reason:

- The shipped app opened Learn as a cluttered stack: the Earned Wall dominated the
  surface while the actual next practice CTA floated near the bottom, and the
  embedded lesson window still behaved like a standalone `100vh` window inside the
  shell. Fold Learn practice-first, constrain the embedded root to the shell stage,
  make viewport-fixed Learn controls absolute inside that stage, and compact the
  Earned Wall into progress context below the practice surface.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/learn-folded-layout.spec.ts tests/shell/settings-nav.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/app.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/learn-folded-layout.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 57 - Folded Learn Readiness Rail

Suggested commit: `fix(learn-ui): surface real practice readiness`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/learn-folded-layout.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Learn scoring, curriculum progression semantics, Python lesson runtime,
  co-host speech, Settings drawer internals, and packaging scripts. This package
  only makes the shell-embedded Learn readiness state truthful and easier to
  scan.

Reason:

- The packaged Learn view was technically working but still felt fake: it could
  show "screen deck ready" while the runtime status stream already saw MIDI, and
  the next-practice controls read as a centered popover instead of part of the
  practice instrument. Listen to `ipc.status.tick` for the MIDI-present signal,
  surface that as "midi signal ready" until the controller-specific Learn mapper
  binds, and fold the next-practice module into a full-width command rail above
  the deck.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/learn-folded-layout.spec.ts tests/shell/settings-nav.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/learn-folded-layout.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 58 - Packaged Learn MIDI Readiness Envelope

Suggested commit: `fix(learn-ui): read packaged midi status envelope`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/components/status-bar.ts`
- `tauri/ui/tests/shell/learn-folded-layout.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/handoffs/2026-06-02-learn-first-screen-product-qa.md`

Keep out:

- Learn scoring, curriculum progression semantics, Python lesson runtime,
  co-host speech, Settings drawer internals, and packaging scripts. This package
  only fixes the mounted packaged Learn readiness display when the global status
  stream sees MIDI before the Learn-specific controller mapper binds.

Reason:

- The signed packaged app at `6bf13c6f` saw `ipc.status.tick` with `midi:1` in
  `ui.log`, but Learn still rendered "screen practice deck" and the bottom
  status still said "on-screen deck". Read both raw-payload and envelope-shaped
  status details, and surface the intermediate state as "midi signal" /
  "midi signal ready" until `ipc.learn.controller_detected` can name the exact
  controller.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/learn-folded-layout.spec.ts tests/shell/settings-nav.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/components/status-bar.ts tauri/ui/tests/shell/learn-folded-layout.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 59 - Learn Status Tick Bridge

Suggested commit: `fix(learn-ui): bridge status ticks into learn readiness`

Include:

- `tauri/ui/src/learn/ws-client.ts`
- `tauri/ui/tests/shell/learn-folded-layout.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Broader session snapshot forwarding, Learn runtime semantics, controller SVG
  rendering, co-host speech, and packaging scripts. This package only forwards
  the validated `ipc.status.tick` frame that Learn needs for honest MIDI
  readiness.

Reason:

- Package 58 made Learn able to parse a MIDI-bearing status detail, but the
  Learn event client never forwarded `ipc.status.tick`: the Tauri path
  subscribed only to `ipc.learn.*`, and the websocket fallback intentionally
  dropped non-Learn frames. Bridge exactly `ipc.status.tick`, still validate it,
  and keep all other session bus traffic filtered so Learn does not drown in
  snapshot/mascot noise.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/learn-folded-layout.spec.ts tests/shell/settings-nav.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/learn/ws-client.ts tauri/ui/tests/shell/learn-folded-layout.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 60 - Learn First-Screen Clarity

Suggested commit: `fix(learn-ui): clarify folded practice screen`

Include:

- `tauri/ui/src/shell/DesktopShell.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/components/status-bar.ts`
- `tauri/ui/tests/shell/learn-folded-layout.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Lesson scoring, controller SVG semantics, Learn runtime progression, co-host
  speech, packaging scripts, and any broad shell redesign. This package only
  changes the folded Learn first screen so the shipped app stops hiding the
  ready state inside clutter.

Reason:

- The freshly signed packaged app at `68da49e6` finally proved the MIDI bridge:
  Learn displayed `midi signal ready` and the bottom rail showed `midi signal`.
  That fixed the lie, but the product surface still read poorly: the first
  viewport gave a huge ghost controller schematic more weight than the next
  action, kept the full trademark footer visible inside the practice cockpit,
  rendered an empty Earned Wall as a framed bottom card, and let the right
  grounding drawer compete with Learn while saying nothing useful. Technically
  ready but visually unclear is still a broken shipped state. Hide only the
  folded legal footer, hide the empty Earned wall until it has rows, and demote
  the Learn grounding drawer width. The packaged proof then exposed one more
  honesty edge: `ipc.status.tick.midi=1` means a controller port is visible, not
  that movement frames are flowing. The intermediate rail must therefore say
  a plain product state, `controller detected`, leaving `Enable FLX4 MIDI`
  free to remain the next action when deck-mixer evidence still reports no
  traffic. Record the failure mode in a short QA note so future agents treat
  confusing signed-app UI as a product bug, not a documentation problem.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/learn-folded-layout.spec.ts tests/shell/settings-nav.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/DesktopShell.ts tauri/ui/src/shell/shell.css tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/components/status-bar.ts tauri/ui/tests/shell/learn-folded-layout.spec.ts .planning/handoffs/2026-05-31-package-checklist.md .planning/handoffs/2026-06-02-learn-first-screen-product-qa.md`

## Package 61 - Viber Crate First-Screen Missions

Suggested commit: `fix(crate-ui): make viber first screen actionable`

Include:

- `tauri/ui/library.html`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/library.css`
- `tauri/ui/src/library/chat.test.ts`
- `tauri/ui/src/mock-transfer/contract.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Viber backend/tool semantics, library ingest/freshness behavior, co-host/Sven
  speech, Learn, Settings, packaging scripts, and any broad visual redesign.
  This package only fixes the Crate/Viber first screen so the shipped app stops
  opening onto an internal-looking console.

Reason:

- The signed packaged app at `a037a749` showed Crate/Viber with a real indexed
  backend and live grounding sidecar, but the center of the surface still read
  like a debug console: one vague line, no obvious first move, and side-rack
  placeholders saying `trace idle` / `artifact idle`. Make Viber's money-making
  actions visible at rest with three wired starter missions (build a set, solve
  a grounded transition, rediscover deep cuts), hide them once the user asks
  something, and rename the side rack to product receipt language while keeping
  the live-proof state honest.

Proof before staging:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/library.html tauri/ui/src/library/index.ts tauri/ui/src/library/library.css tauri/ui/src/library/chat.test.ts tauri/ui/src/mock-transfer/contract.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 62 - Deck Idle Readiness Contract

Suggested commit: `fix(deck-ui): make idle deck state actionable`

Include:

- `tauri/ui/src/session/SessionLayout.ts`
- `tauri/ui/tests/session/components.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Co-host speech generation, claim guards, DROP-call behavior, runtime audio,
  Viber/Crate, Learn, Settings, packaging scripts, and any broad shell redesign.
  This package only fixes the signed app's first Deck read when the live session
  is mounted but no reaction has landed yet.

Reason:

- The signed packaged app at `a1c7014f` still opened Deck onto a giant
  `listening for the mix...` line even while the footer carried useful truth:
  library fresh, voice ready, proof pending, and current routing/persona. That
  made a quiet but working product look like the same old broken void. Replace
  the vague mood line with a precise idle contract: the app is ready for the
  first move, it shows audio/Sven/controller readiness, it names screen-proof
  availability, and it says it will not guess. No fake live
  claims, no new controls, no card clutter.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/session/components.spec.ts tests/session/grounding-failure.spec.ts tests/session/render-loop.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/session/SessionLayout.ts tauri/ui/tests/session/components.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 63 - Debrief Empty Review Dock

Suggested commit: `fix(shell): make debrief empty state valuable`

Include:

- `tauri/ui/src/shell/surfaces.ts`
- `tauri/ui/src/shell/DesktopShell.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Debrief generation, standalone debrief window behavior, recordings, co-host
  speech, runtime audio, Learn, Crate/Viber, Settings, and packaging scripts.
  This package only fixes the folded shell Debrief route when no review is
  available yet.

Reason:

- The signed packaged app at `2846ef10` showed Debrief as a giant void with
  `No set to review.` and one vague sentence. That is honest but too weak for a
  commercial product: it makes a powerful post-set engine read like an empty
  placeholder. Replace it with a compact review dock that previews the actual
  value Debrief will deliver after a real set: timeline, grounded receipts, and
  next action. It still does not claim any review exists before evidence lands.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/shell.spec.ts tests/shell/settings-nav.spec.ts tests/shell/surface-mounts.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/surfaces.ts tauri/ui/src/shell/DesktopShell.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 64 - Settings Drawer Human Labels

Suggested commit: `fix(settings-ui): clarify drawer labels`

Include:

- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/tests/settings/drawer.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Settings IPC schemas, sidecar config persistence, audio routing behavior,
  wizard/calibration behavior, Learn/Deck/Crate/Debrief surfaces, runtime
  co-host speech, and packaging scripts. This package only changes the
  user-facing labels and notes inside the existing Settings drawer.

Reason:

- The signed packaged app at `506795a2` showed the real Settings drawer, but
  the top controls still leaked internal abbreviations and raw IDs: `CFG`,
  `HP`, `SPK`, `INT`, and output device `5`. That makes the product feel like
  a debug config panel even when the wires are working. Keep the exact backend
  values (`hp`, `spk`, `intermediate`, raw device id) but render commercial
  language: `Headphones`, `Speakers`, `Intermediate`, `Device 5`, and short
  notes that explain when a change takes effect.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/settings/drawer.spec.ts tests/session/integration.spec.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/settings/SettingsDrawer.ts tauri/ui/tests/settings/drawer.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 65 - Crate Operator Labels

Suggested commit: `fix(crate-ui): clarify viber operator labels`

Include:

- `tauri/ui/library.html`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/chat.test.ts`
- `tauri/ui/src/library/build.test.ts`
- `tauri/ui/src/library/model-setup.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Viber backend/tool semantics, library ingest/freshness behavior, settings,
  Learn, Deck, Sven speech, runtime audio, packaging scripts, and any broad
  Crate redesign. This package only changes product-facing Crate/Viber labels
  and tests that pin those labels.

Reason:

- The exact signed app at `70d520a0` made Crate more actionable, but the idle
  surface still looked like a debug console: `BACKEND sqlite-vec`, `MODELS CLAP
  ready · MOSS ready · CUE ready`, a prompt with generated-copy punctuation, and
  `LIVE PROOF partial · transport state`. Keep the same truthful readiness
  states while translating the resting product face to Viber operator language:
  local search, search/voice/cue export readiness, proof gate, and receipt-first
  starter missions.

Proof before staging:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/model-setup.test.ts src/library/build.test.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/library.html tauri/ui/src/library/index.ts tauri/ui/src/library/chat.test.ts tauri/ui/src/library/build.test.ts tauri/ui/src/library/model-setup.test.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 66 - Crate Shell Fallback Resilience

Suggested commit: `fix(shell): keep crate fallback useful on mount failure`

Include:

- `tauri/ui/src/shell/surfaces.ts`
- `tauri/ui/src/shell/surface-mounts.ts`
- `tauri/ui/tests/shell/shell.spec.ts`
- `tauri/ui/tests/shell/surface-mounts.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Library/Viber backend behavior, `tauri/ui/library.html`, Learn/Deck/Settings
  interiors, Sven speech, runtime audio, packaging scripts, and broad shell
  layout. This package only changes the shell fallback copy and the fold-in
  mount protocol for failed stub interiors.

Reason:

- The exact signed app at `e955c106` could still show the Crate route as
  `Nothing loaded yet.` if the folded library/Viber interior did not appear in
  time. Worse, the mount protocol revealed a stub mount before the heavy interior
  succeeded, so a Crate mount failure could blank the useful fallback. Keep the
  fallback visible until mount success, and make the Crate fallback preview
  Viber's operator jobs: build sets, solve grounded transitions, and find deep
  cuts with receipts.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/shell.spec.ts tests/shell/surface-mounts.spec.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/surfaces.ts tauri/ui/src/shell/surface-mounts.ts tauri/ui/tests/shell/shell.spec.ts tauri/ui/tests/shell/surface-mounts.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 67 - Folded Viber Crate Mount

Suggested commit: `fix(crate-ui): mount viber inside shell crate`

Include:

- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/library.css`
- `tauri/ui/src/library/state-machine.ts`
- `tauri/ui/src/library/folded-mount.test.ts`
- `tauri/ui/src/shell/app.ts`
- `tauri/ui/src/shell/surface-mounts.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Viber backend/tool semantics, Learn, Deck, Settings drawer behavior, Sven
  speech, runtime audio, packaging scripts, and broad shell layout. This package
  only makes the existing Viber/library UI mount safely as the shell's Crate
  interior and logs any future fold-in failures to `ui.log`.

Reason:

- The exact signed app at `7982a72d` showed the improved Crate fallback instead
  of the real Viber operator. The folded mount path still treated the library
  page as a document-wide surface: auto-boot could fire from injected scaffold
  markup, selectors reached outside the Crate root, and mode CSS only listened
  to `body[data-mode]`. Scope Viber DOM lookup/event binding to the provided
  mount root, let folded mode drive `.vmx-lib-app[data-mode]`, preserve
  standalone `library.html` auto-boot, and send mount failures into the
  headless `ui.log` sink.

Proof before staging:

- `npm --prefix tauri/ui test -- src/library/folded-mount.test.ts src/library/chat.test.ts src/library/build.test.ts tests/shell/shell.spec.ts tests/shell/surface-mounts.spec.ts tests/shell/scaffolds.spec.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/library/index.ts tauri/ui/src/library/library.css tauri/ui/src/library/state-machine.ts tauri/ui/src/library/folded-mount.test.ts tauri/ui/src/shell/app.ts tauri/ui/src/shell/surface-mounts.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 68 - Learn Next Practice Readout

Suggested commit: `fix(learn-ui): clarify next practice`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/learn/test_controller_detected_mounts_svg.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- GSD, beginner-path suites, Python curriculum semantics, Learn backend
  progression rules, Sven speech, Viber, Crate, Settings, packaging scripts,
  and broad shell layout. This package only makes the existing Learn practice
  booth name the next lesson and the available practice path.

Reason:

- The exact signed app at `0efab7da` showed Learn as a large faint controller
  with two disconnected actions. It looked calm but not valuable: a learner had
  to infer what lesson was next, why Start mattered, and whether the controller
  state was usable. Keep the practice deck primary, but make the top strip name
  the course, lesson title, and current practice path: hardware mapped,
  controller detected, or screen deck available.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_controller_detected_mounts_svg.test.ts tests/learn/test_first_launch_announce.spec.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/styles/learn.css tauri/ui/src/shell/shell.css tauri/ui/tests/learn/test_controller_detected_mounts_svg.test.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 69 - Settings Drawer Active Chrome

Suggested commit: `fix(shell): mark settings active while open`

Include:

- `tauri/ui/src/shell/shell-store.ts`
- `tauri/ui/src/shell/Sidebar.ts`
- `tauri/ui/src/shell/DesktopShell.ts`
- `tauri/ui/src/shell/app.ts`
- `tauri/ui/tests/shell/settings-nav.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Settings control semantics, settings IPC/schema, Deck, Crate, Learn, Debrief,
  packaging scripts, and broad shell layout. This package only makes the shell
  chrome tell the truth when the Settings drawer is visible.

Reason:

- The exact signed app at `8da49374` opened Settings as a right drawer while
  the sidebar still highlighted Debrief. The drawer model is useful because it
  preserves the user's task surface behind settings, but the visible app chrome
  contradicted the open module. Keep the stage on the last real surface, carry
  a separate `settingsOpen` store bit, and let the sidebar use Settings as the
  effective active row while the drawer is open.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/settings-nav.spec.ts tests/shell/shell.spec.ts tests/shell/command-palette.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/shell-store.ts tauri/ui/src/shell/Sidebar.ts tauri/ui/src/shell/DesktopShell.ts tauri/ui/src/shell/app.ts tauri/ui/tests/shell/settings-nav.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 70 - Debrief Review Dock

Suggested commit: `fix(debrief-ui): surface recent review sessions`

Include:

- `tauri/ui/src/shell/DebriefDock.ts`
- `tauri/ui/src/shell/app.ts`
- `tauri/ui/src/shell/surface-mounts.ts`
- `tauri/ui/src/mock-transfer/contract.ts`
- `tauri/ui/tests/shell/debrief-dock.spec.ts`
- `tauri/ui/tests/shell/surface-mounts.spec.ts`
- `tauri/ui/tests/mock-transfer-contract.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Debrief sidecar generation, TLDR/chapter semantics, recordings deletion or
  reveal flows, Settings drawer behavior, Deck, Crate, Learn, IPC schema,
  Sven speech, Viber tooling, packaging scripts, and broad shell layout. This
  package only makes the folded Debrief shell route list recent recordings and
  open the existing dedicated review window for sessions with enough evidence.

Reason:

- The exact signed app at `9d0aa0d4` showed Debrief as a clean but inert
  placeholder: "Your set review lands here" plus proof rows. That tells a
  product story without letting the user do anything. Keep Debrief's full
  analysis in the dedicated `debrief.html` window, but make the shell route a
  real review dock: request the real recording list, show readiness honestly,
  keep short/crashed sessions visible but disabled, and launch
  `open_debrief_window` for eligible sessions.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/debrief-dock.spec.ts tests/shell/surface-mounts.spec.ts tests/shell/shell.spec.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/DebriefDock.ts tauri/ui/src/shell/app.ts tauri/ui/src/shell/surface-mounts.ts tauri/ui/src/mock-transfer/contract.ts tauri/ui/tests/shell/debrief-dock.spec.ts tauri/ui/tests/shell/surface-mounts.spec.ts tauri/ui/tests/mock-transfer-contract.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 71 - Settings Trust Rail

Suggested commit: `feat(settings-ui): surface local trust status`

Include:

- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/src/mock-transfer/contract.ts`
- `tauri/ui/tests/settings/drawer.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Settings IPC/schema changes, new settings persistence fields, recording
  browser behavior, profile/library import semantics, Deck, Crate, Learn,
  Debrief, Sven speech, Viber tooling, packaging scripts, and broad shell
  layout. This package only adds a compact top-of-drawer trust/readiness rail
  using existing settings, recording usage, and proof-gate state.

Reason:

- The exact signed app at `58420967` showed Settings as a polished control
  drawer, but it buried the product's trust facts across separate groups. A
  paying DJ should see immediately that Sven is local MOSS, output routing is
  known, recordings are local, and proof-gated commentary will not guess. Add a
  restrained four-cell rail above Persona, contract its `data-wire` anchors, and
  keep missing evidence visibly honest instead of converting it into marketing
  reassurance.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/settings/drawer.spec.ts tests/mock-transfer-contract.spec.ts tests/settings.tokens.test.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/settings/SettingsDrawer.ts tauri/ui/src/mock-transfer/contract.ts tauri/ui/tests/settings/drawer.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 72 - Command Deck Palette

Suggested commit: `feat(shell-ui): upgrade command palette`

Include:

- `tauri/ui/src/shell/CommandPalette.ts`
- `tauri/ui/src/shell/DesktopShell.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/command-palette.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Backend/runtime IPC, settings drawer behavior, Deck/Crate/Learn/Debrief
  surface interiors, Sven speech, Viber tooling, packaging scripts, and new
  dependencies. This package only makes the existing Cmd+K shell palette feel
  like a real navigation/control deck using current shell state and local
  commands.

Reason:

- The exact signed app at `8bda1a1d` showed a functional but underpowered
  palette: rows navigated and taught shortcuts, but the surface did not show
  current readiness, grouped intent, product aliases such as Viber/proof, or
  enough control context to feel like a native vibemix command surface. Add a
  compact status strip, grouped rows, state chips, alias-backed search, and
  footer key hints without changing IPC or pretending live audio is present.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/command-palette.spec.ts tests/shell/shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/CommandPalette.ts tauri/ui/src/shell/DesktopShell.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/command-palette.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 73 - Learn Practice Brief Rail

Suggested commit: `feat(learn-ui): add practice brief rail`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `tauri/ui/tests/shell/learn-folded-layout.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Learn curriculum/backend lesson flow, beginner-path/GSD suites, controller
  SVG geometry, Course 3 live evidence semantics, Deck, Crate, Debrief,
  Settings, Sven speech, Viber tooling, IPC schema, and packaging scripts. This
  package only upgrades the folded Learn first-screen practice booth using
  already-known recommendation and readiness state.

Reason:

- The exact signed app at `18a6e593` showed Learn as the next commercial-value
  target: controller-forward and ready to practice, but still too passive. The
  DJ sees a large dim schematic plus Start/Choose controls, yet not enough
  immediate answer to "what am I about to practice, what proof path is active,
  and why does this matter?" Add a compact target/proof/payoff brief rail to
  the existing booth, keep it tied to the current recommended lesson and
  readiness mode, and adjust the folded shell spacing so the practice deck
  remains readable.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts tests/shell/learn-folded-layout.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/styles/learn.css tauri/ui/src/shell/shell.css tauri/ui/tests/learn/test_practice_booth_shell.spec.ts tauri/ui/tests/shell/learn-folded-layout.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 74 - Debrief Readiness Console

Suggested commit: `feat(debrief-ui): add review readiness console`

Include:

- `tauri/ui/src/shell/DebriefDock.ts`
- `tauri/ui/tests/shell/debrief-dock.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Dedicated debrief window internals, recordings backend, sidecar/debrief port
  8766 behavior, recording IPC schema, Deck/Crate/Learn/Settings surfaces,
  Sven speech, Viber tooling, packaging scripts, and new dependencies. This
  package only upgrades the folded shell Debrief dock using existing recording
  summaries and the current honest eligibility gate.

Reason:

- The exact signed app at `722f76af` showed Debrief as the next weakest
  commercial-value module: it has real recording summaries and honest not-ready
  gates, but reads like a quiet archive. Add a next-review readiness console
  and row-level evidence meters so a DJ immediately sees whether a cited review
  is armed, what is blocking the nearest recording, and why weak sessions cannot
  open yet.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/debrief-dock.spec.ts tests/debrief/no-legacy-amber.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/DebriefDock.ts tauri/ui/tests/shell/debrief-dock.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 79 - Settings Sven Contract

Suggested commit: `feat(settings-ui): add sven operating contract`

Include:

- `tauri/ui/src/settings/SettingsDrawer.ts`
- `tauri/ui/src/mock-transfer/contract.ts`
- `tauri/ui/tests/settings/drawer.spec.ts`
- `tauri/ui/tests/mock-transfer-contract.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Settings IPC schema/codegen, backend settings persistence, audio restart
  behavior, Deck/Crate/Learn/Debrief surfaces, Sven speech, Viber tooling,
  packaging scripts, and new dependencies. This package only upgrades the
  Settings drawer's first screen using already-rendered settings, recording,
  and proof state.

Reason:

- The exact signed app at `a40a24cf` showed Settings as the next weakest
  commercial-value module: it exposes the right local voice, output, recording,
  and proof facts, but still reads like a control drawer rather than a live DJ
  operating contract. Add a compact Sven contract inside the existing trust
  rail so the DJ sees the active persona, route, and proof state before
  adjusting controls.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/settings/drawer.spec.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/settings/SettingsDrawer.ts tauri/ui/src/mock-transfer/contract.ts tauri/ui/tests/settings/drawer.spec.ts tauri/ui/tests/mock-transfer-contract.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 75 - Deck Live Proof Readiness Rail

Suggested commit: `feat(deck-ui): add live proof readiness rail`

Include:

- `tauri/ui/src/session/SessionLayout.ts`
- `tauri/ui/tests/session/render-loop.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Sven speech, prompt wording, co-host runtime behavior, LiveKit/Gemini/MOSS
  backends, IPC schema/codegen, Viber/Crate, Learn, Debrief, Settings, shell
  navigation, packaging scripts, and new dependencies. This package only
  upgrades the Deck first-move idle surface using already-projected session
  status.

Reason:

- The exact signed app at `14bfd8fc` showed Deck as the primary remaining
  product-value target: visually central, but too passive at rest. It said the
  first move was pending and marked screen proof unavailable, yet did not give a
  compact booth-readable answer to what is armed, what is blocked, and what
  Sven will do next. Add a first-move readiness rail inside the existing deck
  slab so audio, Sven, controller, and screen proof are visible without
  implying missing screen evidence has landed.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/session/render-loop.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/session/SessionLayout.ts tauri/ui/tests/session/render-loop.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 76 - Crate Operator Brief

Suggested commit: `feat(crate-ui): add viber operator brief`

Include:

- `tauri/ui/library.html`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/library.css`
- `tauri/ui/src/library/chat.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Viber tool implementations, library search/ranking semantics, backend
  commands, IPC schema/codegen, Deck, Learn, Debrief, Settings, Sven speech,
  packaging scripts, and new dependencies. This package only upgrades the
  folded Crate first screen using already-rendered library stats and live proof
  status.

Reason:

- The exact signed app at `5bd9fa8b` showed Crate as the next commercial-value
  target after Deck: it has the real Viber chat path and grounded proof rack,
  but the first screen still reads like a prompt console. Add a compact
  operator brief that states what Viber can do now: build from the indexed
  crate, mix only when proof is armed, and rediscover through local search. The
  rail must stay tied to existing stats/live context and must not imply a live
  transition proof until the existing gate says `armed`.

Proof before staging:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/folded-mount.test.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/library.html tauri/ui/src/library/index.ts tauri/ui/src/library/library.css tauri/ui/src/library/chat.test.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 77 - Learn Mission Contract

Suggested commit: `feat(learn-ui): add practice mission contract`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Learn curriculum/backend lesson flow, beginner-path/GSD suites, controller
  SVG semantics, IPC schema/codegen, Deck, Crate, Debrief, Settings, Sven
  speech, packaging scripts, and new dependencies. This package only upgrades
  the folded Learn first screen using already-rendered recommended lesson and
  readiness state.

Reason:

- The exact signed app at `f344c4c9` showed Learn as the next commercial-value
  target after Crate: the controller stage looks like a real training surface,
  but the top rail still asks the DJ to infer the actual mission from small
  target/proof/payoff labels. Add a compact mission contract that says what to
  practice and what proof source must land before a receipt unlocks, while
  preserving the existing screen deck, mapped-controller, and MIDI-only fallback
  truthfulness.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts tests/shell/learn-folded-layout.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/styles/learn.css tauri/ui/src/shell/shell.css tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 78 - Debrief Payback Path

Suggested commit: `feat(debrief-ui): add review payback path`

Include:

- `tauri/ui/src/shell/DebriefDock.ts`
- `tauri/ui/tests/shell/debrief-dock.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Dedicated debrief window internals, recordings backend, sidecar/debrief port
  8766 behavior, recording IPC schema, Deck/Crate/Learn/Settings surfaces,
  Sven speech, Viber tooling, packaging scripts, and new dependencies. This
  package only upgrades the folded shell Debrief dock using existing recording
  summaries and the current honest eligibility gate.

Reason:

- The exact signed app at `1981b071` showed Debrief as the next weakest
  commercial-value module after Learn: the shell route has honest recording
  rows and a readiness console, but still reads like a passive recording
  ledger. Add a compact payback path that names the closest review target, the
  blocker, the next action, and the unlocked value, while row copy keeps weak
  recordings visible without allowing fake debrief launches.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/debrief-dock.spec.ts tests/debrief/no-legacy-amber.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/shell/DebriefDock.ts tauri/ui/tests/shell/debrief-dock.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 80 - Crate Viber Runbook Receipt

Suggested commit: `feat(library-ui): add viber runbook receipt`

Include:

- `tauri/ui/library.html`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/library.css`
- `tauri/ui/src/library/chat.test.ts`
- `tauri/ui/src/mock-transfer/contract.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Viber tool implementations, library search/ranking semantics, backend
  commands, IPC schema/codegen, Deck, Learn, Debrief, Settings, Sven speech,
  packaging scripts, and new dependencies. This package only upgrades the
  Crate/Viber idle receipt rack using already-rendered library stats and live
  proof status.

Reason:

- The exact signed app at `ad32fd18` showed Crate as the next weakest
  commercial-value module: the chat starters and operator brief are present,
  but the right grounding rack still waits empty until a run. Add an at-rest
  Viber runbook that names the build, transition, and export path from existing
  stats/proof gates so the first screen reads like a working DJ set-prep
  console without implying missing live transition evidence has landed.

Proof before staging:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/library.html tauri/ui/src/library/index.ts tauri/ui/src/library/library.css tauri/ui/src/library/chat.test.ts tauri/ui/src/mock-transfer/contract.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 81 - Wizard Live Contract Intro

Suggested commit: `feat(wizard-ui): add first-run live contract`

Include:

- `tauri/ui/src/wizard/step0-intro.ts`
- `tauri/ui/tests/wizard/step0-intro.spec.ts`
- `tauri/ui/src/mock-transfer/contract.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Wizard step order, wizard IPC schema/codegen, sidecar onboarding commands,
  driver install behavior, Deck/Crate/Learn/Debrief/Settings interiors, Sven
  speech, Viber tooling, packaging scripts, and new dependencies. This package
  only upgrades the first-run visual contract before the existing CTA advances
  to permissions.

Reason:

- The exact signed app at `570a663e` showed the first-run intro as the next
  weakest commercial-value surface: it has a strong brand hero, but the first
  screen still asks a new DJ to infer what makes the app real. Add a compact
  live contract strip that names the local MOSS voice, master-audio input,
  screen proof, and controller MIDI chain before the first click, without
  adding a tour, a second CTA, or fake readiness claims.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/wizard/step0-intro.spec.ts tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- tauri/ui/src/wizard/step0-intro.ts tauri/ui/tests/wizard/step0-intro.spec.ts tauri/ui/src/mock-transfer/contract.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 82 - Live Coach Route Chain Telemetry

Suggested commit: `fix(cohost): report live route chain telemetry`

Include:

- `src/vibemix/llm/route_chain.py`
- `src/vibemix/agent/dj_cohost.py`
- `tests/llm/test_route_chain.py`
- `tests/agent/test_dj_cohost.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Automatic provider switching, prompt rewrites, OpenRouter client construction,
  proxy auth changes, TTS voice routing, UI settings behavior, Viber tooling,
  and new dependencies. This package only exposes the runtime live-coach route
  chain and TTFT/proxy hedge state as telemetry; switch policy stays manual.

Reason:

- The live app can be in direct, proxy, or dormant OpenRouter-capable states,
  and proxy 503s already silence safely. Add a small read-only route-chain
  descriptor so `llm_invoke`, `proxy_unavailable`, and `connection_error`
  events explain the active route, TTFT pressure, and whether a provider hedge
  requires Kaan/operator decision, without changing dispatch.

Proof before staging:

- `uv run pytest -q tests/llm/test_route_chain.py tests/runtime/test_ttft.py tests/agent/test_dj_cohost.py::test_llm_node_direct_mode_5xx_surfaces_connection_error tests/agent/test_dj_cohost.py::test_llm_node_proxy_mode_503_marks_proxy_unavailable_without_speech tests/agent/test_dj_cohost.py::test_llm_invoke_logs_route_chain_with_manual_ttft_hedge`
- `uv run pytest -q tests/integration/test_proxy_fallback.py tests/agent/test_proxy_client.py tests/agent/test_llm_factory.py`
- `uv run pytest -q tests/agent/test_dj_cohost.py`
- `uv run ruff check src/vibemix/llm/route_chain.py src/vibemix/agent/dj_cohost.py tests/llm/test_route_chain.py tests/agent/test_dj_cohost.py`
- `uv run python -m compileall -q src/vibemix/llm/route_chain.py src/vibemix/agent/dj_cohost.py tests/llm/test_route_chain.py tests/agent/test_dj_cohost.py`
- `git diff --check -- src/vibemix/llm/route_chain.py src/vibemix/agent/dj_cohost.py tests/llm/test_route_chain.py tests/agent/test_dj_cohost.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 83 - Learn Repeat Mismatch Silence

Suggested commit: `fix(learn): silence repeated mismatch hints`

Include:

- `src/vibemix/learn/runtime.py`
- `tests/learn/test_adaptive_coaching_runtime_contract.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Learn ground-up rebuild, curriculum transcript rewrites, frontend Learn UI,
  GSD/beginner-path suites, practice-player audio synthesis changes, co-host
  Sven speech, and new dependencies. This package only changes repeated
  identical wrong-control feedback in the Learn runtime.

Reason:

- Live Learn logs showed authored mismatch hints repeating the same correction
  on repeated wrong controls. Keep the evidence path intact by recording every
  observed action, but suppress duplicate tutor speech/subtitle until the
  observed or expected control changes. Correct-but-too-small moves still keep
  their feedback path.

Proof before staging:

- `uv run pytest -q tests/learn/test_adaptive_coaching_runtime_contract.py tests/learn/test_tutor_voice_callback.py tests/learn/test_lesson_runtime_smoke.py tests/learn/test_advancement_gates.py`
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/test_adaptive_coaching_runtime_contract.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py tests/learn/test_adaptive_coaching_runtime_contract.py`
- `git diff --check -- src/vibemix/learn/runtime.py tests/learn/test_adaptive_coaching_runtime_contract.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 84 - Sven Replay-Fitted Speak Gate

Suggested commit: `fix(cohost): require payload for priority speech`

Include:

- `src/vibemix/runtime/speak_gate.py`
- `src/vibemix/runtime/coach.py`
- `scripts/eval/respan_sven_heartbeat_judge.py`
- `scripts/eval/respan_sven_sim.py`
- `tests/runtime/test_speak_gate.py`
- `tests/runtime/test_coach.py`
- `tests/eval/test_respan_sven_heartbeat_quality_gate.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- LLM prompt rewrites, provider switching, TTS voice changes, new UI channels,
  generic text-to-pill rendering, detector deletion, Learn runtime changes, and
  new dependencies. This package only prevents bare priority event names from
  reaching Sven without detector payload and adds replay proof for no-TTS
  suppression.

Reason:

- The 20260602 137-line Sven replay had 135 lines already suppressed by the
  describe-bank gate, but two no-payload priority events still reached the
  judge path. Require detector payload for structural priority speech while
  preserving payload-backed KICK/MIX events, and record suppressed turns as
  `tts_route=suppressed` with `pill_route=live_next_pill` only when an existing
  grounded next-suggestion receipt belongs on the pill.

Proof before staging:

- `uv run pytest -q tests/runtime/test_speak_gate.py tests/runtime/test_coach.py::test_coach_14_plain_heartbeat_stays_silent tests/runtime/test_coach.py::test_coach_low_worth_next_suggestion_routes_to_pill_not_tts tests/eval/test_respan_sven_heartbeat_quality_gate.py tests/eval/test_respan_sven_sim_quality_gate.py`
- `uv run python scripts/eval/respan_sven_heartbeat_judge.py --session "/Users/ozai/Library/Application Support/vibemix/recordings/20260602-075843" --events ALL --describe-bank-census --dry-run --require-census-silence --min-census-rows 137 --out /tmp/vmx-137-census-after.json`
- `uv run python scripts/eval/respan_sven_sim.py --strict-sven-gate --gate-only --out /tmp/vmx-sven-gate-after.json`
- `uv run ruff check src/vibemix/runtime/speak_gate.py src/vibemix/runtime/coach.py scripts/eval/respan_sven_heartbeat_judge.py scripts/eval/respan_sven_sim.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py tests/eval/test_respan_sven_heartbeat_quality_gate.py tests/eval/test_respan_sven_sim_quality_gate.py`
- `uv run python -m compileall -q src/vibemix/runtime/speak_gate.py src/vibemix/runtime/coach.py scripts/eval/respan_sven_heartbeat_judge.py scripts/eval/respan_sven_sim.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py tests/eval/test_respan_sven_heartbeat_quality_gate.py tests/eval/test_respan_sven_sim_quality_gate.py`
- `git diff --check -- src/vibemix/runtime/speak_gate.py src/vibemix/runtime/coach.py scripts/eval/respan_sven_heartbeat_judge.py scripts/eval/respan_sven_sim.py tests/runtime/test_speak_gate.py tests/runtime/test_coach.py tests/eval/test_respan_sven_heartbeat_quality_gate.py tests/eval/test_respan_sven_sim_quality_gate.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 85 - Nowplaying Track Name Omission

Suggested commit: `fix(state): omit nominal nowplaying track names`

Include:

- `src/vibemix/state/deck_poller.py`
- `src/vibemix/state/refresh.py`
- `tests/state/test_deck_poller.py`
- `tests/state/test_refresh.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Deck-poller source rewrites, library matching changes, nowplaying owner
  allowlist changes, CLAP self-match wiring, UI deck chips, prompt rewrites,
  and new dependencies. This package only keeps the nominal macOS Now Playing
  fallback below the track-name floor.

Reason:

- `nowplaying_playback` was documented as non-physical deck proof but used
  confidence `0.5`, exactly the title naming floor in `derive_audible_track`.
  Lowering that nominal fallback below the floor preserves deck provenance while
  omitting the possibly wrong Now Playing title from `state.audible_track`.

Proof before staging:

- `uv run pytest -q tests/state/test_track_resolver.py tests/state/test_deck_poller.py::test_nowplaying_playback_seeds_deck_when_controller_has_no_midi_motion tests/state/test_refresh.py::test_tick_uses_nowplaying_playback_deck_status_without_naming_track tests/state/test_refresh.py::test_tick_does_not_append_track_history_when_confidence_below_05`
- `uv run ruff check src/vibemix/state/deck_poller.py src/vibemix/state/refresh.py tests/state/test_deck_poller.py tests/state/test_refresh.py`
- `uv run python -m compileall -q src/vibemix/state/deck_poller.py src/vibemix/state/refresh.py tests/state/test_deck_poller.py tests/state/test_refresh.py`
- `git diff --check -- src/vibemix/state/deck_poller.py src/vibemix/state/refresh.py tests/state/test_deck_poller.py tests/state/test_refresh.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 86 - Citation Strip Pre-TTS Silence

Suggested commit: `fix(cohost): keep citation strips pre-tts`

Include:

- `src/vibemix/agent/dj_cohost.py`
- `tests/agent/test_dj_cohost_linter.py`
- `tests/agent/test_dj_cohost_streaming_pipe.py`
- `tests/agent/test_dj_cohost_ground_secondary.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Prompt rewrites, provider switching, linter policy changes, citation grammar
  changes, new fallback speech, UI behavior, Learn runtime changes, and new
  dependencies. This package only ensures wired citation-linter turns do not
  stream speculative TTS before the full response validates.

Reason:

- A silence-pad cancel can mask trailing audio but cannot prove the already
  yielded head was never heard. In linter-wired live mode, hold model chunks
  until citation validation passes; valid cited lines still speak, while
  uncitable/fabricated/no-citation replies yield zero TTS chunks. Update the
  secondary-ear guard test to encode the same pre-TTS strip contract.

Proof before staging:

- `uv run pytest -q tests/agent/test_dj_cohost_ground_secondary.py tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost_streaming_pipe.py tests/llm/test_route_chain.py tests/agent/test_dj_cohost.py::test_llm_node_direct_mode_5xx_surfaces_connection_error tests/agent/test_dj_cohost.py::test_llm_node_proxy_mode_503_marks_proxy_unavailable_without_speech tests/integration/test_proxy_fallback.py`
- `uv run ruff check src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_ground_secondary.py`
- `uv run python -m compileall -q src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_ground_secondary.py`
- `git diff --check -- src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_ground_secondary.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 87 - Disable Citation Bypass Speech

Suggested commit: `fix(cohost): disable citation bypass speech`

Include:

- `src/vibemix/agent/dj_cohost.py`
- `tests/agent/test_dj_cohost_linter.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Tracker telemetry semantics, historical report parsing, provider switching,
  prompt rewrites, citation grammar changes, UI behavior, Learn runtime changes,
  and new dependencies. This package only removes the live co-host call site
  that consumed the one-shot citation bypass as a speech permission.

Reason:

- After pre-TTS deferral, the remaining escape hatch was the old one-shot
  bypass: an invalid linter result could still speak an unverified line when
  `StrippedRateTracker.should_bypass()` fired. The live co-host must treat every
  invalid citation-linter result as silent `citation_strip`; historical
  `citation_bypass` rows can remain readable as blocker diagnostics, but new
  live speech must not create them.

Proof before staging:

- `uv run pytest -q tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost_streaming_pipe.py tests/agent/test_dj_cohost_ground_secondary.py tests/coach/test_stripped_rate_tracker.py tests/eval/test_cohost_viber_session_report.py`
- `uv run ruff check src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_linter.py`
- `uv run python -m compileall -q src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_linter.py`
- `git diff --check -- src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_linter.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 88 - Live Prompt No Listening Fallback

Suggested commit: `fix(cohost): omit listening fallback from live prompt`

Include:

- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/agent/persona.py`
- `src/vibemix/prompts/matrix.py`
- `tests/agent/test_dj_cohost.py`
- `tests/agent/test_dj_cohost_matrix_dispatch.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Generic prompt-matrix defaults, prompt cell rewrites, citation grammar
  changes, provider switching, UI behavior, Learn runtime changes, tracker
  telemetry semantics, and new dependencies. This package only makes the live
  co-host dispatcher opt out of `IM_LISTENING_FRAGMENT`.

Reason:

- The live co-host path already suppresses fail-soft fallback before TTS, but
  `_resolve_prompt_cell()` still let the generic builder append the prompt rule
  that tells the model to answer "I'm listening" when it cannot cite. That
  keeps priming the exact anti-slop failure class. The runtime prompt should
  still include citation grammar and the audio-vibe contract, but not the
  uncited listening fallback.

Proof before staging:

- `uv run pytest -q tests/agent/test_dj_cohost.py::test_resolve_prompt_cell_uses_shared_lens tests/agent/test_dj_cohost.py::test_resolve_prompt_cell_cold_path_byte_identical tests/agent/test_dj_cohost.py::test_resolve_prompt_cell_lens_wins_over_live_mood tests/agent/test_dj_cohost.py::test_resolve_prompt_cell_corrupt_lens_falls_back_no_crash tests/agent/test_dj_cohost_matrix_dispatch.py tests/prompts/test_matrix.py tests/agent/test_coach_mood_template.py`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
- `uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/agent/persona.py src/vibemix/prompts/matrix.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_matrix_dispatch.py`
- `uv run python -m compileall -q src/vibemix/agent/dj_cohost.py src/vibemix/agent/persona.py src/vibemix/prompts/matrix.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_matrix_dispatch.py`
- `git diff --check -- src/vibemix/agent/dj_cohost.py src/vibemix/agent/persona.py src/vibemix/prompts/matrix.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_matrix_dispatch.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 89 - Recall Memory Accrual Live Wiring

Suggested commit: `fix(memory): wire recall ingest on live path`

Include:

- `src/vibemix/__main__.py`
- `tests/memory/test_ingest_wiring.py`
- `tests/test_main_smoke.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- UI settings for recall, retention policy changes, memory schema changes,
  prompt rewrites, Learn runtime changes, provider switching, and new
  dependencies. This package only makes the existing explicit recall flag
  reach the live runtime and existing off-loop ingest hooks.

Reason:

- `ConfigStore.recall_enabled` and `VIBEMIX_RECALL_ENABLED` existed, and
  `SessionLoop._fire_ingest()` already handled boot/close memory accrual off
  the event loop, but live `main()` hardcoded `recall_enabled=False` on the
  co-host and `memory_ingest_enabled=False` on the session IPC. An opted-in
  user could not accrue or retrieve session memory. Resolve the flag once at
  boot, build `MemoryRecall` only inside the Start-gated live session, enable
  ingest on the live IPC only when opted in, and call the ingest-only boot/close
  hooks without double-running recording retention.

Proof before staging:

- `uv run pytest -q tests/memory/test_ingest_wiring.py tests/test_main_smoke.py::test_recall_enabled_resolves_env_before_config tests/test_main_smoke.py::test_smoke_03_full_wiring tests/test_main_smoke.py::test_smoke_03_recall_enabled_wires_memory_recall_and_ingest tests/test_main_smoke.py::test_smoke_03b_idle_is_cold_until_start`
- `uv run pytest -q tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/memory/test_retention.py tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py tests/memory/test_thread_safety.py`
- `uv run ruff check src/vibemix/__main__.py tests/memory/test_ingest_wiring.py tests/test_main_smoke.py`
- `uv run python -m compileall -q src/vibemix/__main__.py tests/memory/test_ingest_wiring.py tests/test_main_smoke.py`
- `git diff --check -- src/vibemix/__main__.py tests/memory/test_ingest_wiring.py tests/test_main_smoke.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 90 - Memory Ingest Hygiene Sweeps

Suggested commit: `fix(memory): run ingest hygiene sweeps`

Include:

- `src/vibemix/runtime/session_loop.py`
- `tests/memory/test_ingest_wiring.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Memory retention policy changes, schema changes, UI controls, new recall
  producers, prompt rewrites, and `__main__` orchestration changes. This package
  only wires the existing `MemoryStore` hygiene primitives into the existing
  off-loop memory ingest worker.

Reason:

- `MemoryStore.reconcile_orphans()` and `MemoryStore.run_retention_sweep()`
  existed, but the live boot/close ingest worker never called them. That left
  dangling vectors and over-budget memory rows to persist until a manual test or
  future tool invoked the primitives. Run orphan reconciliation on boot before
  ingest, run memory retention after boot/close ingest, keep all work inside the
  executor worker, and swallow hygiene failures so cleanup can never block the
  live session loop or prevent ingest.

Proof before staging:

- `uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_retention.py tests/memory/test_store.py tests/memory/test_thread_safety.py`
- `uv run pytest -q tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py`
- `uv run ruff check src/vibemix/runtime/session_loop.py tests/memory/test_ingest_wiring.py`
- `uv run python -m compileall -q src/vibemix/runtime/session_loop.py tests/memory/test_ingest_wiring.py`
- `git diff --check -- src/vibemix/runtime/session_loop.py tests/memory/test_ingest_wiring.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 91 - Library Embed Folder Error Detail

Suggested commit: `fix(library-ui): surface embed-folder stderr`

Include:

- `tauri/src-tauri/src/library_cmds.rs`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Python ingest behavior, model installation behavior, UI layout/copy rewrites,
  and library cache resets. This package only preserves a bounded stderr tail
  from the existing Python child process and includes it in the existing Tauri
  command error.

Reason:

- Fresh-user folder import can fail before any progress line reaches the UI
  (missing folder, model/dependency hint, stale index, or other CLI fatal). The
  Rust bridge logged stderr but returned only `embed-folder exited N`, leaving
  the Library window with an opaque error. Keep the last non-empty stderr lines,
  cap them to avoid dumping a full traceback, and append them to the returned
  error so the UI can show the actionable Python message it already produced.

Proof before staging:

- `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml`
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds::tests`
- `git diff --check -- tauri/src-tauri/src/library_cmds.rs .planning/handoffs/2026-05-31-package-checklist.md`

## Package 92 - Main-Bus Library Import Wiring

Suggested commit: `fix(library): restore ipc import handler`

Include:

- `src/vibemix/runtime/session_loop.py`
- `tests/runtime/test_session_loop.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Library UI layout, standalone Library-window command behavior, model
  installation, cache resets, and new source parser behavior. This package
  restores the main app's existing `ipc.library.import` contract, using the
  already-shipped folder/XML/catalog ingest paths and schema parity.

Reason:

- The Python `LibraryImport*` wrappers and UI schema tests still existed, but
  the live `SessionLoop` registered no `ipc.library.import` handler and the
  JSON schema had dropped the three import oneOf branches. A fresh user could
  emit `ipc.library.import` from the main app and get no real import path or
  progress validation. Register import/cancel handlers, route folders through
  `ingest_folder`, infer known DJ catalog files before the XML fallback, route
  XML through `import_library_async`, emit validated
  `ipc.library.import_progress`, and regenerate the TS IPC validator.

Proof before staging:

- `uv run pytest -q tests/runtime/test_session_loop.py::test_register_handlers_covers_all_session_types tests/runtime/test_session_loop.py::test_parse_folder_import_progress_line tests/runtime/test_session_loop.py::test_library_import_routes_folder_to_ingest tests/runtime/test_session_loop.py::test_library_import_routes_xml_to_existing_importer tests/runtime/test_session_loop.py::test_library_import_routes_catalog_before_xml`
- `uv run pytest -q tests/ui_bus/test_messages_schema.py tests/ipc/test_library_schemas.py`
- `npm --prefix tauri/ui run codegen:ipc`
- `npm --prefix tauri/ui run check:ipc`
- `uv run python scripts/check_ipc_schema.py`
- `uv run ruff check src/vibemix/runtime/session_loop.py tests/runtime/test_session_loop.py`
- `uv run python -m compileall -q src/vibemix/runtime/session_loop.py tests/runtime/test_session_loop.py`
- `git diff --check -- src/vibemix/runtime/session_loop.py tests/runtime/test_session_loop.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs .planning/handoffs/2026-05-31-package-checklist.md`

## Package 93 - Default Strict Citation Gate and Deck-Matched Titles

Suggested commit: `fix(cohost): default to strict cited speech`

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/state/refresh.py`
- `src/vibemix/state/track_resolver.py`
- `tests/coach/test_main_anti_slop_wiring.py`
- `tests/state/test_refresh.py`
- `tests/state/test_track_resolver.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Prompt rewrites, live-claim guard policy rewrites, UI settings changes, replay
  report scoring, and library/deck-poller source acquisition changes. This
  package only makes the existing citation linter the normal launch default and
  prevents a nowplaying title resolved to one deck from naming the other deck.

Reason:

- A normal user launch still defaulted `VIBEMIX_CITATION_LINT` to `off`, so the
  response-level strip-to-silence chokepoint could be skipped even though the
  linter, tracker, playback, and registry were wired. Default the gate on while
  preserving `VIBEMIX_CITATION_LINT=off` as an explicit debug opt-out and print
  the startup state. Also thread deck-source `resolved_side` provenance into
  `derive_audible_track()` so Sven says `track=unknown` when the current
  nowplaying title belongs to deck A but the audible deck is deck B.

Proof before staging:

- `uv run pytest -q tests/coach/test_main_anti_slop_wiring.py tests/state/test_track_resolver.py tests/state/test_refresh.py tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py::test_llm_node_11_exception_does_not_propagate tests/agent/test_dj_cohost.py::test_llm_node_proxy_mode_503_marks_proxy_unavailable_without_speech tests/agent/test_dj_cohost_streaming_pipe.py::test_citation_failure_after_short_response_stays_silent`
- `uv run ruff check src/vibemix/__main__.py src/vibemix/state/track_resolver.py src/vibemix/state/refresh.py tests/coach/test_main_anti_slop_wiring.py tests/state/test_track_resolver.py tests/state/test_refresh.py`
- `uv run python -m compileall -q src/vibemix/__main__.py src/vibemix/state/track_resolver.py src/vibemix/state/refresh.py tests/coach/test_main_anti_slop_wiring.py tests/state/test_track_resolver.py tests/state/test_refresh.py`
- `git diff --check -- src/vibemix/__main__.py src/vibemix/state/track_resolver.py src/vibemix/state/refresh.py tests/coach/test_main_anti_slop_wiring.py tests/state/test_track_resolver.py tests/state/test_refresh.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 94 - Proxy Outage Transcript Silence

Suggested commit: `fix(cohost): keep outage diagnostics out of transcript`

Include:

- `src/vibemix/agent/dj_cohost.py`
- `tests/agent/test_dj_cohost.py`
- `tests/integration/test_proxy_fallback.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Proxy routing policy, model selection, local voice playback, LiveKit status,
  UI badges, and citation prompt rewrites. This package only removes canned
  outage/recovery diagnostics from the transcript surface while preserving the
  existing `events.jsonl`, stderr, and route telemetry diagnostics.

Reason:

- Proxy and connection failure helpers still pushed canned lines such as
  `Co-host unavailable this session`, `Co-host back online`, and connection
  error hints into the `transcript_delta` sink. Those were not model output and
  were not synthesized by Sven, but the UI could display them as co-host speech.
  Keep the loud diagnostics in recorder events/stderr while reserving transcript
  for genuine spoken/model lines.

Proof before staging:

- `uv run pytest -q tests/agent/test_dj_cohost.py::test_llm_node_direct_mode_5xx_surfaces_connection_error tests/agent/test_dj_cohost.py::test_llm_node_proxy_mode_503_marks_proxy_unavailable_without_speech tests/integration/test_proxy_fallback.py`
- `uv run ruff check src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost.py tests/integration/test_proxy_fallback.py`
- `uv run python -m compileall -q src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost.py tests/integration/test_proxy_fallback.py`
- `git diff --check -- src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost.py tests/integration/test_proxy_fallback.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 95 - Consent-Gated Memory Accrual

Suggested commit: `fix(memory): decouple accrual from recall`

Include:

- `src/vibemix/__main__.py`
- `tests/memory/test_ingest_wiring.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Prompt recall policy, memory retrieval ranking, MemoryStore retention
  algorithms, CLAP/embedder construction, and UI settings changes. This package
  only changes the live main-path enable condition for the already-built
  off-loop ingest/hygiene worker.

Reason:

- Live memory ingest was tied to `recall_enabled`, which controls whether Sven
  may read past-session memory into prompts. That meant installs with profile
  consent but recall still OFF did not accrue memory at boot/close. Split the
  gates: memory accrual follows profile consent (with an explicit dev env
  override), while recall remains the separate prompt-read opt-in.

Proof before staging:

- `uv run pytest -q tests/memory/test_ingest_wiring.py tests/memory/test_retention.py tests/memory/test_store.py`
- `uv run ruff check src/vibemix/__main__.py tests/memory/test_ingest_wiring.py`
- `uv run python -m compileall -q src/vibemix/__main__.py tests/memory/test_ingest_wiring.py`
- `git diff --check -- src/vibemix/__main__.py tests/memory/test_ingest_wiring.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 96 - Learn Boot Tutor Voice Stream

Suggested commit: `fix(learn): voice tutor before session start`

Include:

- `src/vibemix/__main__.py`
- `tests/learn/test_tutor_voice_callback.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live co-host prompt policy, cloud TTS fallback, packaged model install flow,
  Learn transcript copy, and frontend lesson layout. This package only makes
  existing Learn tutor lines audible before `ipc.session.start`.

Reason:

- Learn runtime is created at app boot, but the local voice provider and
  `open_voice_output()` stream were previously created only inside live session
  activation. A first-user Learn flow could emit `ipc.learn.tutor_speak` and
  subtitles while no voice stream existed to consume the playback queue. Lazily
  open a boot-owned Learn voice stream on first tutor speech, lazily reuse the
  local Chatterbox provider, and let live session reuse the Learn stream when it
  is already open.

Proof before staging:

- `uv run pytest -q tests/learn/test_tutor_voice_callback.py tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `uv run ruff check src/vibemix/__main__.py tests/learn/test_tutor_voice_callback.py`
- `uv run python -m compileall -q src/vibemix/__main__.py tests/learn/test_tutor_voice_callback.py`
- `git diff --check -- src/vibemix/__main__.py tests/learn/test_tutor_voice_callback.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 97 - Learn Practice Recovery Targets

Suggested commit: `feat(learn): route measured misses into recovery missions`

Include:

- `src/vibemix/learn/progress.py`
- `src/vibemix/learn/practice_mission.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/learn/curriculum_projection.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tests/learn/test_progress_persistence.py`
- `tests/learn/test_practice_mission.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New Mastery credit signals, Viber/library transition-score promotion, tutor
  prompt rewrites, and frontend layout redesign. This package only persists
  measured owned-practice misses as next-mission recovery targets; cited
  successful events remain the only Mastery-credit path.

Reason:

- Beatmatch and cue-placement practice already measure useful misses, but that
  correction vanished after the spoken grade. Persist one bounded
  `practice_feedback` target per lesson, derive the next mission as a recovery
  rep, and clear the target after a measured clean rep.

Proof before staging:

- `uv run pytest -q tests/learn/test_progress_persistence.py::test_practice_feedback_is_bounded_and_cleared_by_completion tests/learn/test_practice_mission.py::test_measured_miss_turns_current_proof_mission_into_recovery_target tests/learn/test_runtime_evidence_grounding.py::test_beatmatch_miss_updates_mission_then_locked_grade_clears_it tests/learn/test_runtime_evidence_grounding.py::test_cue_placement_wrong_drop_updates_recovery_mission`
- `uv run pytest -q tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py tests/learn/test_progress_snapshot_skill_wall.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_practice_loop.py tests/learn/test_cue_practice.py`
- `uv run ruff check src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/runtime.py src/vibemix/learn/curriculum_projection.py tests/learn/test_progress_persistence.py tests/learn/test_practice_mission.py tests/learn/test_runtime_evidence_grounding.py`
- `uv run python -m compileall -q src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/runtime.py src/vibemix/learn/curriculum_projection.py tests/learn/test_progress_persistence.py tests/learn/test_practice_mission.py tests/learn/test_runtime_evidence_grounding.py`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/runtime.py src/vibemix/learn/curriculum_projection.py tests/learn/test_progress_persistence.py tests/learn/test_practice_mission.py tests/learn/test_runtime_evidence_grounding.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/lesson/curriculum-meta.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 98 - Learn Recovery Mission CTA

Suggested commit: `fix(learn-ui): label recovery missions as fixes`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Backend recovery feedback persistence, Mastery-credit rules, status-priority
  redesign, and broader Learn visual layout. This package only changes the
  primary practice CTA language for already-grounded recovery missions.

Reason:

- The backend now marks measured-miss missions with `focus: "recovery"`. The
  first visible action should say "fix", not "prove", so learners understand the
  app is sending them back to repair a specific miss before chasing Mastery.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 99 - Learn Practice Recency Routing

Suggested commit: `feat(learn): route missions by latest practice receipt`

Include:

- `src/vibemix/learn/progress.py`
- `src/vibemix/learn/practice_mission.py`
- `src/vibemix/learn/curriculum_projection.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tests/learn/test_practice_mission.py`
- `tests/learn/test_progress_persistence.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New schema-version migration, visual redesign, streak badges, lesson-credit
  rules, and free-practice completion credit. This package only records a
  bounded practice receipt sequence and lets the derived next mission follow
  the learner's latest unfinished banked gesture.

Reason:

- The sandbox already banks useful practice receipts, but mission routing could
  still choose the earliest unfinished lesson and ignore the control the user
  just moved. Route the next booth mission by the latest banked unfinished
  practice receipt so free play feels connected to the curriculum.

Proof before staging:

- `uv run pytest -q tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py tests/learn/test_progress_snapshot_skill_wall.py tests/learn/test_curriculum_projection.py`
- `uv run ruff check src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/curriculum_projection.py tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py`
- `uv run python scripts/export_learn_curriculum_meta.py --check`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `uv run python -m compileall -q src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/curriculum_projection.py tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/curriculum_projection.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/learn/lesson/curriculum-meta.ts tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 100 - Learn Practice Momentum Surface

Suggested commit: `feat(learn-ui): surface practice momentum in lesson routing`

Include:

- `src/vibemix/learn/curriculum_projection.py`
- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tauri/ui/src/learn/lesson/progress-list.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/test_curriculum_meta.spec.ts`
- `tauri/ui/tests/learn/test_progress_list.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New lesson engines, live-credit rules, runtime coach copy, and broader Learn
  layout redesign. This package only makes already-persisted practice receipts
  and measured recovery targets visible and consistent in the lesson chooser.

Reason:

- Backend missions now follow the latest banked practice and measured misses,
  but the local curriculum projection and visible progress list could still
  read like a static checklist. Carry recency and recovery feedback into the
  list rows, prefer the newest repair/practice row when no backend mission is
  attached, and label repair rows as fixes so the learner understands why the
  app is sending them back.

Proof before staging:

- `uv run python scripts/export_learn_curriculum_meta.py --check`
- `uv run ruff check src/vibemix/learn/curriculum_projection.py`
- `uv run python -m compileall -q src/vibemix/learn/curriculum_projection.py`
- `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts tests/learn/test_progress_list.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/learn/curriculum_projection.py tauri/ui/src/learn/lesson/curriculum-meta.ts tauri/ui/src/learn/lesson/progress-list.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/test_curriculum_meta.spec.ts tauri/ui/tests/learn/test_progress_list.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 101 - Learn Earned Wall Frontstage Mount

Suggested commit: `feat(learn-ui): mount earned wall in learn window`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Skill-tree backend math, Mastered credit rules, new wall copy, and beginner
  path suites. This package only mounts the already-built Earned Wall into the
  real Learn frontstage and verifies it consumes the existing progress snapshot.

Reason:

- `SkillWall.ts` and `skill_wall` snapshots were built and tested, but the real
  Learn window only imported the row type. Mount the wall as a quiet desktop
  rail so Competent and Mastered progress is visible during practice, and tear
  its subscription down with the Learn window lifecycle.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_skill_wall.spec.ts tests/learn/skill-tree-a11y.spec.ts tests/learn/skill-tree-quiet-fill.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 102 - Learn Cited Receipt Feedback Parity

Suggested commit: `feat(learn): speak cited practice receipts`

Include:

- `src/vibemix/learn/runtime.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/learn/test_harmonic_practice_runtime.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- `ipc.learn.live_grade` schema expansion, UI lock-meter changes, owned-track
  audio swaps, and any generated tutor copy. The current live-grade contract is
  beatmatch-shaped, so this package uses the existing cited tutor-speak channel
  instead of pretending EQ or harmonic receipts have phase error.

Reason:

- Beatmatch and cue practice already give immediate feedback, but matched
  control and harmonic practice could write progress receipts without saying
  anything unless the action flipped Mastered. Speak a short authored receipt
  for ordinary cited control/harmonic grades, cite the evidence atom (and
  library tracks for harmonic pairs), and suppress the receipt when the same
  action already earns the one-time Mastered line.

Proof before staging:

- `uv run pytest -q tests/learn/test_runtime_evidence_grounding.py::test_matched_eq_lesson_action_writes_control_receipt_and_progress tests/learn/test_runtime_evidence_grounding.py::test_matched_control_mastered_flip_speaks_factual_proof_once tests/learn/test_harmonic_practice_runtime.py::test_l211_final_continue_writes_cited_harmonic_practice_receipt`
- `uv run pytest -q tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py tests/learn/test_scripts_are_fixtures.py`
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py`
- `git diff --check -- src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 103 - Learn Live Meter Lock Edge

Suggested commit: `feat(learn-ui): celebrate earned lock edge`

Include:

- `tauri/ui/src/learn/live-meter.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/live-meter.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New IPC payloads, backend grading changes, debrief replay UI, and broad Learn
  layout work. This package only improves the existing beatmatch lock meter fed
  by `ipc.learn.live_grade`.

Reason:

- The live meter moved the needle but did not treat a lock as an earned moment.
  Add a real verdict edge detector, a compact receipt row, and one reduced-motion
  safe pulse only when the grade crosses into `locked`. Sustained locked ticks do
  not repeat the celebration; drift rearms the next edge.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/live-meter.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/live-meter.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/live-meter.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`

## Package 104 - Learn Measured Beatmatch Voice Bank

Suggested commit: `feat(learn): vary measured beatmatch feedback`

Include:

- `src/vibemix/learn/runtime.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Randomized/generated tutor copy, live-grade IPC changes, lock-meter UI, and
  owned-track audio. This package only replaces the old four-line beatmatch
  text map with deterministic authored text chosen from measured grade fields.

Reason:

- Beatmatch feedback was grounded but robotic: every locked/drift/tempo/trainwreck
  state used one generic line. Use the existing deterministic grade fields to
  say whether deck B is late or early, whether tempo is far out or close, and
  whether a locked result has proof. Keep the current verdict de-dupe cadence so
  voice fires on meaningful changes instead of every meter tick.

Proof before staging:

- `uv run pytest -q tests/learn/test_runtime_evidence_grounding.py tests/learn/test_beatmatch_practice_audio_lifecycle.py tests/learn/test_scripts_are_fixtures.py`
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `git diff --check -- src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_beatmatch_practice_audio_lifecycle.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 105 - Debrief Near-Miss Detector CLI

Suggested commit: `feat(debrief): detect last-night timing recoveries`

Include:

- `src/vibemix/debrief/near_miss_detector.py`
- `src/vibemix/__main__.py`
- `src/vibemix/audio/recorder.py`
- `tests/debrief/test_near_miss_detector.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Debrief UI cards, generated friend lines, Gemini prompt rewrites, live
  co-host speech, and lesson routing. This package only lands the headless
  detector and CLI entry point that future Learn/Debrief surfaces can consume.

Reason:

- Last Night, Heard needs a real observed receipt, not a presence-only story.
  Re-derive one OUT->IN timing recovery from `input.wav` around MIX_MOVE /
  TRACK_CHANGE / transition_judged windows, abstain when confidence is low, and
  phrase the result as "the mix" instead of deck blame.

Proof before staging:

- `uv run pytest -q tests/debrief/test_near_miss_detector.py`
- `uv run ruff check src/vibemix/debrief/near_miss_detector.py src/vibemix/__main__.py src/vibemix/audio/recorder.py tests/debrief/test_near_miss_detector.py`
- `uv run python -m compileall -q src/vibemix/debrief/near_miss_detector.py src/vibemix/__main__.py src/vibemix/audio/recorder.py tests/debrief/test_near_miss_detector.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/debrief/near_miss_detector.py src/vibemix/__main__.py src/vibemix/audio/recorder.py tests/debrief/test_near_miss_detector.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 106 - Debrief Resolver-Backed Friend Line

Suggested commit: `feat(debrief): ground last-night friend lines`

Include:

- `src/vibemix/debrief/friend_line.py`
- `tests/debrief/test_friend_line.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Debrief UI frames, IPC schema changes, waveform rendering, Gemini prompts,
  and broader receipt assembly. This package only builds the pure line/receipt
  helper and the small local voice seam.

Reason:

- The "Last Night, Heard" line must feel like a friend, but it cannot be a
  decorative citation. Build the near-miss and gap lines on the debrief drill
  resolver, phrase timing as "the mix", and return honest nulls when the
  citation source/key/timestamp does not resolve.

Proof before staging:

- `uv run pytest -q tests/debrief/test_friend_line.py`
- `uv run ruff check src/vibemix/debrief/friend_line.py tests/debrief/test_friend_line.py`
- `uv run python -m compileall -q src/vibemix/debrief/friend_line.py tests/debrief/test_friend_line.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/debrief/friend_line.py tests/debrief/test_friend_line.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 107 - Debrief Near-Miss Frame Sender

Suggested commit: `feat(debrief): emit last-night near-miss payload`

Include:

- `src/vibemix/debrief/main.py`
- `src/vibemix/debrief/ws_server.py`
- `src/vibemix/debrief/session_loader.py`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/ui_bus/schemas/debrief.py`
- `src/vibemix/ui_bus/__init__.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `scripts/check_ipc_schema.py`
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `tests/debrief/test_ws_server_progressive_emit.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- The visual debrief card, waveform rendering, audio playback controls, and
  Learn routing. This package only produces and validates the backend frame UX
  will consume.

Reason:

- A2/A1 can now produce a grounded line, but UX needs a real IPC contract
  instead of inferred field names. Emit a compact `ipc.debrief.near-miss` frame
  with `{input_wav_relative_path, t_center, window, receipt_text,
  friend_line_text, duration_s}`, allow null replay fields for honest quiet
  states, and fix the session-loaded duration axis to use real session duration
  instead of `voice.wav`.

Proof before staging:

- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `uv run pytest -q tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/ui_bus/test_debrief_schema_additive_only.py tests/debrief/test_ws_server_progressive_emit.py tests/debrief/test_friend_line.py tests/debrief/test_near_miss_detector.py`
- `uv run ruff check src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py src/vibemix/debrief/session_loader.py src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/schemas/debrief.py src/vibemix/ui_bus/__init__.py scripts/check_ipc_schema.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/debrief/test_ws_server_progressive_emit.py`
- `uv run python -m compileall -q src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py src/vibemix/debrief/session_loader.py src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/schemas/debrief.py src/vibemix/ui_bus/__init__.py scripts/check_ipc_schema.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/debrief/test_ws_server_progressive_emit.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py src/vibemix/debrief/session_loader.py src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/schemas/debrief.py src/vibemix/ui_bus/__init__.py scripts/check_ipc_schema.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/debrief/test_ws_server_progressive_emit.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs .planning/handoffs/2026-05-31-package-checklist.md`

## Package 108 - Debrief Receipt Assembly

Suggested commit: `feat(debrief): assemble last-night receipts`

Include:

- `src/vibemix/debrief/drills.py`
- `src/vibemix/debrief/main.py`
- `src/vibemix/debrief/ws_server.py`
- `tests/debrief/test_drill_citations_resolve.py`
- `tests/debrief/test_transition_judged_critique.py`
- `tests/debrief/test_ws_server_progressive_emit.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Debrief UI rendering, schema changes, waveform work, and own-track Save mode.
  This package only makes backend receipts resolver-safe and richer.

Reason:

- The near-miss frame had a grounded friend line, but the receipt still needed
  the A4/A6 glue: Learn beatmatch/cue grade receipts in the cited critique,
  wall-clock context for the morning card, Judge context when the recording
  actually logged it, and debrief resolver/tooltip support for existence-key
  citations like `[judge:transition@128.4]` without double timestamping them.

Proof before staging:

- `uv run pytest -q tests/debrief/test_drill_citations_resolve.py tests/debrief/test_transition_judged_critique.py tests/debrief/test_ws_server_progressive_emit.py`
- `uv run ruff check src/vibemix/debrief/drills.py src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py tests/debrief/test_drill_citations_resolve.py tests/debrief/test_transition_judged_critique.py tests/debrief/test_ws_server_progressive_emit.py`
- `uv run python -m compileall -q src/vibemix/debrief/drills.py src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py tests/debrief/test_drill_citations_resolve.py tests/debrief/test_transition_judged_critique.py tests/debrief/test_ws_server_progressive_emit.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/debrief/drills.py src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py tests/debrief/test_drill_citations_resolve.py tests/debrief/test_transition_judged_critique.py tests/debrief/test_ws_server_progressive_emit.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 109 - Learn Save-Mode Own-Track Loader

Suggested commit: `feat(learn): load save mode from own tracks`

Include:

- `src/vibemix/learn/save_mode_loader.py`
- `src/vibemix/learn/beatmatch_practice_driver.py`
- `tests/learn/test_save_mode_loader.py`
- `tests/learn/test_beatmatch_practice_driver.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Tauri/UI changes, app-start eager decoding, new IPC schemas, and save-landed
  animation signals. This package only creates the grounded own-track source
  loader and teaches the existing owned-deck driver how to grade different-BPM
  real sources.

Reason:

- Save mode should practice on the user's own library when the library can
  honestly provide two decoded, ANLZ-gridded tracks. Filter to Save-ready
  entries before calling the grounded next-suggestion engine, decode bounded
  audio slabs, build real `BeatGrid.from_anlz` grids, and fall back with an
  explicit reason instead of fabricating a practice grid.

Proof before staging:

- `uv run pytest -q tests/learn/test_save_mode_loader.py tests/learn/test_beatmatch_practice_driver.py`
- `uv run ruff check src/vibemix/learn/save_mode_loader.py src/vibemix/learn/beatmatch_practice_driver.py tests/learn/test_save_mode_loader.py tests/learn/test_beatmatch_practice_driver.py`
- `uv run python -m compileall -q src/vibemix/learn/save_mode_loader.py src/vibemix/learn/beatmatch_practice_driver.py tests/learn/test_save_mode_loader.py tests/learn/test_beatmatch_practice_driver.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/learn/save_mode_loader.py src/vibemix/learn/beatmatch_practice_driver.py tests/learn/test_save_mode_loader.py tests/learn/test_beatmatch_practice_driver.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 110 - Learn Save-Landed Live Grade Signal

Suggested commit: `feat(learn): signal save landed on recovery edge`

Include:

- `src/vibemix/learn/practice_loop.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/ui_bus/learn_messages.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tests/ui_bus/test_learn_live_grade_message.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- UX animation/rendering, Save-mode escalation, and own-track runtime boot
  selection. This package only adds the validated backend signal UX can render.

Reason:

- The Learn live-grade meter can already say locked/drifting, but The Save
  needs a distinct one-shot moment. Compute it in the owned-deck practice tick
  only when a measured `drifting`/`trainwreck` grade transitions directly to a
  cited locked grade. Do not fire it on an initial lock, sustained lock, sandbox
  grade, or a later lock after tempo went off.

Proof before staging:

- `uv run pytest -q tests/ui_bus/test_learn_live_grade_message.py tests/learn/test_runtime_evidence_grounding.py::test_live_beatmatch_grade_voices_locked_with_resolving_citation tests/learn/test_runtime_evidence_grounding.py::test_live_beatmatch_save_landed_flags_real_recovery_edge tests/learn/test_runtime_evidence_grounding.py::test_live_beatmatch_save_landed_ignores_tempo_off_interruption tests/learn/test_runtime_evidence_grounding.py::test_live_beatmatch_grade_keeps_meter_updates_when_phase_changes`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `uv run ruff check src/vibemix/learn/practice_loop.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py tests/ui_bus/test_learn_live_grade_message.py tests/learn/test_runtime_evidence_grounding.py`
- `uv run python -m compileall -q src/vibemix/learn/practice_loop.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py tests/ui_bus/test_learn_live_grade_message.py tests/learn/test_runtime_evidence_grounding.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/learn/practice_loop.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py tests/ui_bus/test_learn_live_grade_message.py tests/learn/test_runtime_evidence_grounding.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs .planning/handoffs/2026-05-31-package-checklist.md`

## Package 111 - Learn Save-Mode Lazy Own-Track Activation

Suggested commit: `feat(learn): activate own-track save mode lazily`

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/learn/two_deck_player.py`
- `tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `tests/learn/test_observer_boot_wiring.py`
- `tests/learn/test_two_deck_player.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- App-start eager audio decode, UI animation work, and Save-mode difficulty
  escalation. This package only makes the own-track loader reachable at the
  moment Learn is about to start Save-mode practice audio.

Reason:

- Package 109 built the real own-track loader, but boot still bound runtime to
  the initial bundled-loop driver. Use wrapper callbacks so a later driver swap
  is visible, add a `beatmatch_practice_prepare` runtime hook, and let
  `TwoDeckPlayer` swap to the new `MiniDeck` without opening an extra audio
  path. Gate lazy loading to Save-mode lessons so basic deck-anatomy practice
  stays on stable bundled loops.

Proof before staging:

- `uv run pytest -q tests/learn/test_beatmatch_practice_audio_lifecycle.py::test_beatmatch_practice_prepare_runs_before_waveform_emit tests/learn/test_observer_boot_wiring.py::test_beatmatch_practice_audio_uses_shared_learn_output_device tests/learn/test_two_deck_player.py`
- `uv run ruff check src/vibemix/__main__.py src/vibemix/learn/runtime.py src/vibemix/learn/two_deck_player.py tests/learn/test_beatmatch_practice_audio_lifecycle.py tests/learn/test_observer_boot_wiring.py tests/learn/test_two_deck_player.py`
- `uv run python -m compileall -q src/vibemix/__main__.py src/vibemix/learn/runtime.py src/vibemix/learn/two_deck_player.py tests/learn/test_beatmatch_practice_audio_lifecycle.py tests/learn/test_observer_boot_wiring.py tests/learn/test_two_deck_player.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/__main__.py src/vibemix/learn/runtime.py src/vibemix/learn/two_deck_player.py tests/learn/test_beatmatch_practice_audio_lifecycle.py tests/learn/test_observer_boot_wiring.py tests/learn/test_two_deck_player.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 112 - Learn Save-Mode Escalation Timer

Suggested commit: `feat(learn): add save mode escalation timer`

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/learn/beatmatch_practice_driver.py`
- `src/vibemix/learn/practice_loop.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/ui_bus/learn_messages.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tests/ui_bus/test_learn_live_grade_message.py`
- `tests/learn/test_beatmatch_practice_driver.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/learn/test_observer_boot_wiring.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- UX rendering for the dare HUD, persistence across cold boots, and unrelated
  Learn lesson rewrites. This package only adds the backend attempt state,
  countdown fields, and driver difficulty hook that UX can render.

Reason:

- B2 needs stakes. Start a Save attempt only from a real owned-deck
  `drifting`/`trainwreck` grade, carry a bounded floor-dies countdown on
  `ipc.learn.live_grade`, expire the attempt before a late lock can fake
  `save_landed`, and escalate successful saves by shrinking the next window
  while pushing the level into the owned-deck recovery drill magnitude.

Proof before staging:

- `uv run pytest -q tests/ui_bus/test_learn_live_grade_message.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_beatmatch_practice_audio_lifecycle.py tests/learn/test_observer_boot_wiring.py`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `uv run ruff check src/vibemix/learn/practice_loop.py src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py src/vibemix/__main__.py tests/ui_bus/test_learn_live_grade_message.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_observer_boot_wiring.py`
- `uv run python -m compileall -q src/vibemix/learn/practice_loop.py src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py src/vibemix/__main__.py tests/ui_bus/test_learn_live_grade_message.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_observer_boot_wiring.py`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
- `git diff --check -- src/vibemix/learn/practice_loop.py src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py src/vibemix/__main__.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tests/ui_bus/test_learn_live_grade_message.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_observer_boot_wiring.py .planning/handoffs/2026-05-31-package-checklist.md`

## Package 113 - Learn Save-Mode Dare HUD

Suggested commit: `feat(learn-ui): show save mode dare hud`

Include:

- `tauri/ui/src/learn/live-meter.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/live-meter.spec.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New backend save-state semantics, thunk/ring animation, waveform animation,
  and broader Learn layout rewrites. This package only renders the existing
  Save-mode live-grade fields in the current Learn meter and status hint.

Reason:

- Package 112 made Save mode real but invisible. Put the dare in the user-facing
  booth: active Save attempts show a countdown, level, and streak; late saves
  read as `floor dropped`; earned recoveries read as `save landed` before
  generic locked/drifting copy can flatten the moment.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/live-meter.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/live-meter.ts tauri/ui/src/learn/styles/learn.css tauri/ui/src/learn/learn-window.ts tauri/ui/tests/learn/live-meter.spec.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 114 - Learn Save-Only Thunk Ring

Suggested commit: `feat(learn-ui): add save-only thunk ring`

Include:

- `tauri/ui/src/learn/live-meter.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/live-meter.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Galloping beat-train waveform motion, backend save-landed semantics, and
  broader Learn/debrief surfaces. This package only adds the earned save
  effect on the existing `save_landed` live-grade flag.

Reason:

- A save should land like a physical close, not another text tick. Gate the
  WebAudio thunk and closing ring strictly on the `save_landed` edge, replay it
  only after the flag falls false, and mute the thunk while tutor speech is
  active so the effect stays rare and never talks over Sven.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/live-meter.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/live-meter.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/live-meter.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 117 - Memory Ingest Sidecar Erasure Cascade

Suggested commit: `fix(memory): purge ingest artifacts on session erase`

Include:

- `src/vibemix/memory/ingest.py`
- `src/vibemix/memory/ingest_artifacts.py`
- `src/vibemix/memory/store.py`
- `tests/memory/test_store.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Retention policy changes, recall prompt behavior, UI settings, and new
  embedding semantics. This package only makes `MemoryStore.delete_session()`
  cascade into the ingest-owned marker/cache sidecar.

Reason:

- `memory_ingest.db` stores per-session idempotency markers and a content-hash
  embed cache next to `memory.db`. Deleting a memory session erased moments and
  vectors but left stale ingest artifacts behind. Delete the session marker,
  clear the content-addressed cache conservatively after a real erasure, and
  still purge stale markers when the live moments are already gone.

Proof before staging:

- `uv run pytest -q tests/memory/test_store.py`
- `uv run ruff check src/vibemix/memory/ingest.py src/vibemix/memory/ingest_artifacts.py src/vibemix/memory/store.py tests/memory/test_store.py`
- `uv run python -m compileall -q src/vibemix/memory/ingest.py src/vibemix/memory/ingest_artifacts.py src/vibemix/memory/store.py tests/memory/test_store.py`
- `git diff --check -- src/vibemix/memory/ingest.py src/vibemix/memory/ingest_artifacts.py src/vibemix/memory/store.py tests/memory/test_store.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 115 - Learn Gallop Beat Trains

Suggested commit: `feat(learn-ui): show gallop beat trains`

Include:

- `tauri/ui/src/learn/waveform-display.ts`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/test_waveform_hidden_until_ready.spec.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Backend grade semantics, waveform peak generation, debrief Morning Mirror,
  and new IPC. This package only renders existing `ipc.learn.live_grade`
  phase error as motion over the already-mounted practice waveform strips.

Reason:

- The meter tells the DJ they are behind or ahead, but it does not show two
  beat trains fighting. Feed live-grade phase into the waveform component so
  deck A/B pulses diverge while drifting and collapse on lock/save, making the
  Save drill feel like pulling two moving trains into one pulse.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_waveform_hidden_until_ready.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/live-meter.spec.ts`
- `npm --prefix tauri/ui run test:e2e:learn -- tests/learn/browser-responsive.pw.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/waveform-display.ts tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/test_waveform_hidden_until_ready.spec.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 116 - Learn Directional Meter Face

Suggested commit: `feat(learn-ui): add directional meter face`

Include:

- `tauri/ui/src/learn/live-meter.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/live-meter.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New backend grading, waveform motion, and broader Learn layout changes. This
  package only turns the existing live-grade phase into an actionable meter
  face with direction, tier, and a session best marker.

Reason:

- The meter should be readable under hand pressure. Show `rush`/`drag`/`hold`,
  a compact tier word (`tight`, `drift`, `off`, `locked`), and a best-so-far
  phase marker so the DJ can chase a visible improvement without parsing the
  receipt line.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/live-meter.spec.ts tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_waveform_hidden_until_ready.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/live-meter.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/live-meter.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 118 - Debrief Morning Mirror Consumer

Suggested commit: `feat(debrief-ui): show morning mirror replay card`

Include:

- `tauri/ui/debrief.html`
- `tauri/ui/src/debrief/ws-client.ts`
- `tauri/ui/src/debrief/debrief-window.ts`
- `tauri/ui/src/debrief/components/timeline.ts`
- `tauri/ui/src/debrief/components/morning-mirror.ts`
- `tauri/ui/src/debrief/styles/debrief.css`
- `tauri/ui/src/debrief/__tests__/timeline-regions-click-seek.spec.ts`
- `tauri/ui/src/debrief/__tests__/morning-mirror.spec.ts`
- `tauri/ui/src/debrief/__tests__/ws-client-near-miss.spec.ts`
- `tauri/ui/src/mock-transfer/contract.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Backend detector, friend-line generation, schema codegen, and new audio
  dependencies. This package consumes the already-generated
  `ipc.debrief.near-miss` frame and renders the first playable replay surface.

Reason:

- Backend was already emitting `ipc.debrief.near-miss`, and the schema already
  knew the frame, but the debrief WS client dropped it as an unknown kind. Map
  the frame, render the grounded Last Night card, mount `input.wav`, and mark
  the near-miss window on the existing timeline so the morning replay is visible
  instead of silently discarded.

Proof before staging:

- `npm --prefix tauri/ui test -- src/debrief/__tests__/morning-mirror.spec.ts src/debrief/__tests__/ws-client-near-miss.spec.ts src/debrief/__tests__/timeline-regions-click-seek.spec.ts`
- `npm --prefix tauri/ui test -- tests/mock-transfer-contract.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/debrief.html tauri/ui/src/debrief/ws-client.ts tauri/ui/src/debrief/components/timeline.ts tauri/ui/src/debrief/components/morning-mirror.ts tauri/ui/src/debrief/debrief-window.ts tauri/ui/src/debrief/styles/debrief.css tauri/ui/src/mock-transfer/contract.ts tauri/ui/src/debrief/__tests__/timeline-regions-click-seek.spec.ts tauri/ui/src/debrief/__tests__/morning-mirror.spec.ts tauri/ui/src/debrief/__tests__/ws-client-near-miss.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 119 - Debrief Real Master Peaks

Suggested commit: `feat(debrief): surface real master peaks`

Include:

- `src/vibemix/audio/waveform_peaks.py`
- `src/vibemix/ui_bus/schemas/debrief.py`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/debrief/main.py`
- `src/vibemix/debrief/ws_server.py`
- `tests/audio/test_waveform_peaks.py`
- `tests/debrief/test_near_miss_detector.py`
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `tests/debrief/test_ws_server_progressive_emit.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/debrief/components/timeline.ts`
- `tauri/ui/src/debrief/components/morning-mirror.ts`
- `tauri/ui/src/debrief/debrief-window.ts`
- `tauri/ui/src/debrief/__tests__/timeline-regions-click-seek.spec.ts`
- `tauri/ui/src/debrief/__tests__/morning-mirror.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- WaveSurfer adoption, new npm dependencies, new debrief detector semantics, and
  any extra generated copy. This package only makes the existing replay rail
  use bounded real master-output peaks when the recording can be decoded.

Reason:

- The Morning Mirror can play `input.wav`, but the rail beneath it is still a
  synthetic sine/cosine bed. That reads polished but not truthful. Emit a
  small optional `waveform_peaks` matrix from the backend, keep corrupt/legacy
  recordings fail-soft, and let the timeline render grounded bar heights
  whenever the sidecar supplies them.

Proof before staging:

- `uv run pytest -q tests/audio/test_waveform_peaks.py tests/debrief/test_near_miss_detector.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/debrief/test_ws_server_progressive_emit.py`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run codegen:ipc`
- `npm --prefix tauri/ui test -- src/debrief/__tests__/morning-mirror.spec.ts src/debrief/__tests__/timeline-regions-click-seek.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/audio/waveform_peaks.py src/vibemix/ui_bus/schemas/debrief.py src/vibemix/ui_bus/messages.py src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py tests/audio/test_waveform_peaks.py tests/debrief/test_near_miss_detector.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/debrief/test_ws_server_progressive_emit.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/debrief/components/timeline.ts tauri/ui/src/debrief/components/morning-mirror.ts tauri/ui/src/debrief/debrief-window.ts tauri/ui/src/debrief/__tests__/timeline-regions-click-seek.spec.ts tauri/ui/src/debrief/__tests__/morning-mirror.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 120 - Debrief Friend Line Audio

Suggested commit: `feat(debrief): play morning friend line`

Include:

- `src/vibemix/debrief/persistence.py`
- `src/vibemix/ui_bus/schemas/debrief.py`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/debrief/main.py`
- `src/vibemix/debrief/ws_server.py`
- `tests/debrief/test_friend_line.py`
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `tests/debrief/test_ws_server_progressive_emit.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/debrief/components/morning-mirror.ts`
- `tauri/ui/src/debrief/__tests__/morning-mirror.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New LLM text, new TTS provider wiring, TLDR persistence changes, and hard
  failures when local voice is unavailable. The line is already grounded text;
  this package only writes and renders an optional local-voice MP3 for it.

Reason:

- The Morning Mirror shows the human line but cannot yet speak it. Generate
  `debrief_friend_line.mp3` from the resolver-backed line through the existing
  local Chatterbox seam, carry an optional relative path on
  `ipc.debrief.near-miss`, and render a small Play line control only when the
  file exists. If synthesis fails, the card still works as text plus master
  replay.

Proof before staging:

- `uv run pytest -q tests/debrief/test_friend_line.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/debrief/test_ws_server_progressive_emit.py`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run codegen:ipc`
- `npm --prefix tauri/ui test -- src/debrief/__tests__/morning-mirror.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/debrief/persistence.py src/vibemix/ui_bus/schemas/debrief.py src/vibemix/ui_bus/messages.py src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py tests/debrief/test_friend_line.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/debrief/test_ws_server_progressive_emit.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/debrief/components/morning-mirror.ts tauri/ui/src/debrief/__tests__/morning-mirror.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 121 - Debrief Moment Feedback Loop

Suggested commit: `feat(debrief): persist moment feedback`

Include:

- `src/vibemix/intel/feedback.py`
- `src/vibemix/ui_bus/schemas/debrief.py`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/ui_bus/__init__.py`
- `src/vibemix/debrief/ws_server.py`
- `tests/intel/test_feedback.py`
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `tests/ui_bus/test_messages_schema.py`
- `tests/debrief/test_ws_server_progressive_emit.py`
- `scripts/check_ipc_schema.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/debrief/ws-client.ts`
- `tauri/ui/src/debrief/components/drills-panel.ts`
- `tauri/ui/src/debrief/debrief-window.ts`
- `tauri/ui/src/debrief/styles/debrief.css`
- `tauri/ui/src/debrief/__tests__/drills-panel-shape.spec.ts`
- `tauri/ui/src/debrief/__tests__/ws-client-near-miss.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New taste weighting for debrief labels, backend prompt changes, debrief
  regeneration, and any cloud call. This package only lets the user mark a
  cited debrief moment as right/off/unclear and persists that correction when
  profile consent allows it.

Reason:

- The debrief can now show and speak grounded moments, but the correction
  flywheel is still broken: the user cannot tell vibemix whether a cited
  moment was actually right. Add the `ipc.debrief.moment-feedback` sender and
  consent-gated backend persistence through the existing feedback JSONL path,
  keeping debrief labels neutral so they become local evidence without
  pretending to be track-pick taste weights.

Proof before staging:

- `uv run pytest -q tests/intel/test_feedback.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/ui_bus/test_messages_schema.py tests/debrief/test_ws_server_progressive_emit.py`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run codegen:ipc`
- `npm --prefix tauri/ui test -- src/debrief/__tests__/drills-panel-shape.spec.ts src/debrief/__tests__/ws-client-near-miss.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/intel/feedback.py src/vibemix/ui_bus/schemas/debrief.py src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/__init__.py src/vibemix/debrief/ws_server.py tests/intel/test_feedback.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/ui_bus/test_messages_schema.py tests/debrief/test_ws_server_progressive_emit.py scripts/check_ipc_schema.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/debrief/ws-client.ts tauri/ui/src/debrief/components/drills-panel.ts tauri/ui/src/debrief/debrief-window.ts tauri/ui/src/debrief/styles/debrief.css tauri/ui/src/debrief/__tests__/drills-panel-shape.spec.ts tauri/ui/src/debrief/__tests__/ws-client-near-miss.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 122 - Learn Own-Track Exemplar Import

Suggested commit: `feat(learn): resolve own-track exemplars`

Include:

- `src/vibemix/learn/exemplar.py`
- `src/vibemix/runtime/session_loop.py`
- `src/vibemix/__main__.py`
- `tests/learn/test_exemplar_finder.py`
- `tests/runtime/test_session_loop.py`
- `tests/library/test_folder_ingest_band_shares.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New lesson copy, UI redesign, exemplar-bank retuning, and any change to
  CLAP vector search. This package only makes first-user folder import feed
  Learn's band-share table and prevents unplayable library rows from being
  announced as own-track exemplars.

Reason:

- Learn already has the own-library moat on paper: folder ingest can compute
  band shares and `ExemplarFinder` can pick the strongest band track. The
  running app did not actually turn that on for GUI/CLI folder import, and
  the finder read `.path` while real `TrackEntry` rows carry `.filepath`.
  Enable band-share accrual on folder imports and require enough playable
  resolved files before returning a "from your library" exemplar; stale rows
  fall back to the packaged honest-null bank instead of emitting silent audio.

Proof before staging:

- `uv run pytest -q tests/learn/test_exemplar_finder.py tests/library/test_folder_ingest_band_shares.py tests/runtime/test_session_loop.py`
- `uv run ruff check src/vibemix/learn/exemplar.py src/vibemix/runtime/session_loop.py src/vibemix/__main__.py tests/learn/test_exemplar_finder.py tests/library/test_folder_ingest_band_shares.py tests/runtime/test_session_loop.py`
- `uv run python -m compileall -q src/vibemix/learn/exemplar.py src/vibemix/runtime/session_loop.py src/vibemix/__main__.py tests/learn/test_exemplar_finder.py tests/library/test_folder_ingest_band_shares.py tests/runtime/test_session_loop.py`
- `git diff --check -- src/vibemix/learn/exemplar.py src/vibemix/runtime/session_loop.py src/vibemix/__main__.py tests/learn/test_exemplar_finder.py tests/library/test_folder_ingest_band_shares.py tests/runtime/test_session_loop.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 123 - Learn Control Live Grade Parity

Suggested commit: `feat(learn): emit live grades for practice receipts`

Include:

- `src/vibemix/learn/runtime.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/learn/test_harmonic_practice_runtime.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New IPC schema, new lesson copy, UI meter changes, generative tutor text,
  and beatmatch/cue placement behavior. This package only mirrors existing
  cited control and harmonic practice receipts onto the existing
  `ipc.learn.live_grade` payload.

Reason:

- Beatmatch and cue-placement practice already move the live-grade stream,
  but matched EQ/control actions and the L2.11 compatible-key receipt only
  wrote/speaker receipts. Emit a minimal `locked` live-grade tick with
  `score=1.0`, `phase_error_beats=0.0`, and the existing `ev` citation so
  the Learn meter is not blind to non-beatmatch practice success.

Proof before staging:

- `uv run pytest -q tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py`
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py`
- `git diff --check -- src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 124 - Learn Cue Live Grade Parity

Suggested commit: `feat(learn): emit live grades for cue placement`

Include:

- `src/vibemix/learn/runtime.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New IPC schema, UI meter changes, cue judge retuning, new lesson copy, and
  any changes to skill credit. This package only mirrors cue-placement grades
  onto the existing `ipc.learn.live_grade` stream.

Reason:

- Current source showed `_emit_live_cue_placement_grade` only spoke tutor
  feedback. Map cue placement onto the existing beatmatch-shaped payload:
  beat/drop-locked cues emit `locked` with the citable
  `CUE_PLACEMENT_GRADED` atom, wrong-drop emits an uncited `drifting` tick
  using target error, and off-beat cues emit uncited drift/trainwreck based
  on beat error. The meter can now react to cue placement without schema or
  UI lane churn.

Proof before staging:

- `uv run pytest -q tests/learn/test_runtime_evidence_grounding.py`
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py`
- `git diff --check -- src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 125 - Learn Save Source Metadata

Suggested commit: `feat(learn): surface save-mode source metadata`

Include:

- `src/vibemix/learn/beatmatch_practice_driver.py`
- `src/vibemix/learn/practice_loop.py`
- `src/vibemix/learn/runtime.py`
- `src/vibemix/ui_bus/learn_messages.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/learn/live-meter.ts`
- `tauri/ui/src/learn/waveform-display.ts`
- `tests/learn/test_beatmatch_practice_driver.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/ui_bus/test_learn_live_grade_message.py`
- `tests/ui_bus/test_learn_waveform_ready_message.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New UI rendering/copy, new lesson text, Save-mode difficulty tuning, own-track
  loading heuristics, and cue/harmonic/control grade behavior. This package
  only preserves the already-grounded source metadata the owned-deck driver had
  in memory.

Reason:

- Current source showed Save-mode own-track loading already builds waveform deck
  rows with `track_id`, `title`, `artist`, `source`, and `source_start_s`, but
  `LearnWaveformReady.make()` dropped that metadata before the webview could
  see it. The runtime live-grade receipt also could not say whether the learner
  was saving a drift on real library tracks or the bundled demo loops. Carry the
  source metadata through driver snapshots, beatmatch practice results,
  `ipc.learn.live_grade`, `ipc.learn.waveform_ready`, generated IPC types, and
  the local Learn UI payload types. Optional fields stay absent for unrelated
  cue/harmonic/control live grades.

Proof before staging:

- `uv run pytest -q tests/learn/test_beatmatch_practice_driver.py tests/learn/test_runtime_evidence_grounding.py tests/ui_bus/test_learn_live_grade_message.py tests/ui_bus/test_learn_waveform_ready_message.py`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `uv run pytest -q tests/ui_bus/test_messages_schema.py tests/ipc/test_learn_envelope_parity_p92.py`
- `uv run ruff check src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/learn/practice_loop.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_runtime_evidence_grounding.py tests/ui_bus/test_learn_live_grade_message.py tests/ui_bus/test_learn_waveform_ready_message.py`
- `uv run python -m compileall -q src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/learn/practice_loop.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_runtime_evidence_grounding.py tests/ui_bus/test_learn_live_grade_message.py tests/ui_bus/test_learn_waveform_ready_message.py`
- `git diff --check -- src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/learn/practice_loop.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/learn_messages.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/learn/live-meter.ts tauri/ui/src/learn/waveform-display.ts tests/learn/test_beatmatch_practice_driver.py tests/learn/test_runtime_evidence_grounding.py tests/ui_bus/test_learn_live_grade_message.py tests/ui_bus/test_learn_waveform_ready_message.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py` (expected current-source fail: existing one-ended calibration/settings/library types; no new `ipc.learn.*` dead type)
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 126 - Learn Waveform Source Readout

Suggested commit: `feat(learn-ui): show save-mode source readout`

Include:

- `tauri/ui/src/learn/waveform-display.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/test_waveform_hidden_until_ready.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Backend metadata changes, new schema fields, live-meter animation changes,
  lesson copy, and broader Learn layout work. Package 125 supplies the
  metadata; this package only renders it in the existing waveform host.

Reason:

- Package 125 made Save-mode source truth available to the webview, but the
  learner still could not see whether the practice decks were real library
  tracks or bundled loops. Add a compact source readout above the waveform
  strips: `own tracks` when `library_save_mode` metadata is present, otherwise
  `practice loops`, plus bounded deck title/artist text. The readout follows
  the existing hidden-until-ready behavior and does not add another card,
  modal, or motion source.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_waveform_hidden_until_ready.spec.ts`
- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `cd tauri/ui && npx playwright test -c tests/learn/playwright.config.ts tests/learn/browser-responsive.pw.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/waveform-display.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/test_waveform_hidden_until_ready.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 127 - Learn Save Fallback Reason

Suggested commit: `feat(learn): explain save-mode practice fallback`

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/learn/beatmatch_practice_driver.py`
- `src/vibemix/ui_bus/learn_messages.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/learn/waveform-display.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/test_waveform_hidden_until_ready.spec.ts`
- `tests/learn/test_beatmatch_practice_driver.py`
- `tests/learn/test_observer_boot_wiring.py`
- `tests/ui_bus/test_learn_waveform_ready_message.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Save-mode loader ranking changes, new onboarding/library ingest flows, new
  lesson copy, broader waveform UI redesign, and any changes to practice
  grading. This only carries the existing fallback reason from the lazy loader
  to the already-rendered waveform source readout.

Reason:

- After Package 126, Save Mode can show `practice loops`, but first-user tests
  still cannot see why own-track Save Mode failed to arm. Preserve
  `SaveModeLoadOutcome.fallback_reason` on the bundled practice driver,
  serialize it as optional `source_reason` on waveform deck rows, and show a
  bounded `reason:` suffix only when the source remains bundled practice loops.
  This makes library-vector/ANLZ readiness problems visible without claiming
  the loops are user tracks.

Proof before staging:

- `uv run pytest -q tests/learn/test_beatmatch_practice_driver.py tests/learn/test_observer_boot_wiring.py tests/ui_bus/test_learn_waveform_ready_message.py`
- `npm --prefix tauri/ui test -- tests/learn/test_waveform_hidden_until_ready.spec.ts`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `npm --prefix tauri/ui run build`
- `cd tauri/ui && npx playwright test -c tests/learn/playwright.config.ts tests/learn/browser-responsive.pw.ts`
- `uv run ruff check src/vibemix/__main__.py src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/ui_bus/learn_messages.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_observer_boot_wiring.py tests/ui_bus/test_learn_waveform_ready_message.py`
- `uv run python -m compileall -q src/vibemix/__main__.py src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/ui_bus/learn_messages.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_observer_boot_wiring.py tests/ui_bus/test_learn_waveform_ready_message.py`
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py` (expected current-source fail: existing one-ended calibration/settings/library types; no new `ipc.learn.*` dead type)
- `git diff --check -- src/vibemix/__main__.py src/vibemix/learn/beatmatch_practice_driver.py src/vibemix/ui_bus/learn_messages.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/learn/waveform-display.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/test_waveform_hidden_until_ready.spec.ts tests/learn/test_beatmatch_practice_driver.py tests/learn/test_observer_boot_wiring.py tests/ui_bus/test_learn_waveform_ready_message.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 128 - Learn Save Event Source Provenance

Suggested commit: `feat(learn): log save receipt source context`

Include:

- `src/vibemix/learn/runtime.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Schema/UI changes, Save-mode difficulty tuning, own-track loader ranking,
  debrief rendering, and new lesson copy. Packages 125-127 already expose the
  source truth live; this package only preserves it in session history.

Reason:

- Current source showed `ipc.learn.live_grade` and `ipc.learn.waveform_ready`
  now carry Save-mode source metadata, but the durable session events for
  `learn_beatmatch_save_landed` and `learn_beatmatch_save_floor_expired`
  remained anonymous. Add the practice source and deck track/title fields to
  those two event records so debrief/replay/taste accrual can distinguish a
  save on the user's own tracks from a bundled-loop practice attempt.

Proof before staging:

- `uv run pytest -q tests/learn/test_runtime_evidence_grounding.py`
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py`
- `git diff --check -- src/vibemix/learn/runtime.py tests/learn/test_runtime_evidence_grounding.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 129 - Debrief Near-Miss Ear-Test Clip

Suggested commit: `feat(debrief): export near-miss ear-test clip`

Include:

- `src/vibemix/__main__.py`
- `src/vibemix/debrief/__init__.py`
- `src/vibemix/debrief/ear_test.py`
- `tests/debrief/test_near_miss_detector.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Detector threshold tuning, Morning Mirror UI changes, friend-line/TTS copy,
  real-session verdict claims, and debrief websocket rendering. This package
  only turns an already-detected near-miss window into a playable proof file.

Reason:

- The detector could name a timestamp, but the useful shipping gate is by ear:
  can the DJ play the exact master-audio window and hear the gallop snap back?
  Add `vibemix debrief near-miss --write-clip` so the headless tool writes a
  bounded `input.wav` slice that preserves the recorded channel count, sample
  width, and sample rate.

Proof before staging:

- `uv run pytest -q tests/debrief/test_near_miss_detector.py tests/debrief/test_friend_line.py`
- `uv run ruff check src/vibemix/__main__.py src/vibemix/debrief/__init__.py src/vibemix/debrief/ear_test.py tests/debrief/test_near_miss_detector.py`
- `uv run python -m compileall -q src/vibemix/__main__.py src/vibemix/debrief/__init__.py src/vibemix/debrief/ear_test.py tests/debrief/test_near_miss_detector.py`
- `git diff --check -- src/vibemix/__main__.py src/vibemix/debrief/__init__.py src/vibemix/debrief/ear_test.py tests/debrief/test_near_miss_detector.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 130 - Debrief Near-Miss Clip Payload

Suggested commit: `feat(debrief-ui): play focused near-miss clip`

Include:

- `src/vibemix/debrief/main.py`
- `src/vibemix/debrief/ws_server.py`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/ui_bus/schemas/debrief.py`
- `tests/debrief/test_near_miss_detector.py`
- `tests/debrief/test_ws_server_progressive_emit.py`
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/debrief/components/morning-mirror.ts`
- `tauri/ui/src/debrief/__tests__/morning-mirror.spec.ts`
- `tauri/ui/src/debrief/__tests__/ws-client-near-miss.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Morning Mirror visual redesign, new playback controls, detector tuning,
  debrief persistence migrations, and any change to the main full-set audio
  timeline. This only adds an optional focused clip pointer and uses it when
  present.

Reason:

- Package 129 made the detector's near-miss window playable from the headless
  CLI. Carry the same proof artifact through `ipc.debrief.near-miss` so the
  Morning Mirror play action can target the short clip directly while keeping
  the existing `input.wav` seek fallback.

Proof before staging:

- `uv run pytest -q tests/debrief/test_near_miss_detector.py tests/debrief/test_ws_server_progressive_emit.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tests/ui_bus/test_messages_schema.py`
- `npm --prefix tauri/ui test -- src/debrief/__tests__/morning-mirror.spec.ts src/debrief/__tests__/ws-client-near-miss.spec.ts`
- `uv run python scripts/check_ipc_schema.py`
- `npm --prefix tauri/ui run check:ipc`
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py` (expected current-source fail: existing one-ended calibration/settings/library types; no new debrief type)
- `npm --prefix tauri/ui run build`
- `uv run ruff check src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/schemas/debrief.py tests/debrief/test_near_miss_detector.py tests/debrief/test_ws_server_progressive_emit.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `uv run python -m compileall -q src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/schemas/debrief.py tests/debrief/test_near_miss_detector.py tests/debrief/test_ws_server_progressive_emit.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `git diff --check -- src/vibemix/debrief/main.py src/vibemix/debrief/ws_server.py src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/schemas/debrief.py tests/debrief/test_near_miss_detector.py tests/debrief/test_ws_server_progressive_emit.py tests/ui_bus/test_debrief_new_wrappers_roundtrip.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/debrief/components/morning-mirror.ts tauri/ui/src/debrief/__tests__/morning-mirror.spec.ts tauri/ui/src/debrief/__tests__/ws-client-near-miss.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 131 - Tauri Dev Command Cwd Guard

Suggested commit: `fix(tauri): harden dev command cwd`

Include:

- `tauri/src-tauri/tauri.conf.json5`
- `tests/repo/test_tauri_dev_command.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Tauri window geometry, release build command changes, package scripts,
  sidecar spawn behavior, and bundled app resources. This only hardens the
  Vite dev-server command used by `cargo tauri dev`.

Reason:

- Live first-user testing hit the exact dev-loop failure this guard prevents:
  some Tauri CLI invocations run `beforeDevCommand` from `tauri/`, while this
  local path/version ran it from `tauri/ui/`, producing a bad `ui/ui` prefix.
  Use a cwd guard so the command works from both launch directories.

Proof before staging:

- `uv run pytest -q tests/repo/test_tauri_dev_command.py`
- `uv run ruff check tests/repo/test_tauri_dev_command.py`
- `uv run python -m compileall -q tests/repo/test_tauri_dev_command.py`
- `git diff --check -- tauri/src-tauri/tauri.conf.json5 tests/repo/test_tauri_dev_command.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 132 - Learn Screen-to-Hardware Mission Escalation

Suggested commit: `feat(learn): escalate screen practice to hardware proof`

Include:

- `src/vibemix/learn/runtime.py`
- `src/vibemix/learn/practice_mission.py`
- `tests/learn/test_practice_mission.py`
- `tests/learn/test_ipc_handlers_dispatch.py`
- `tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Progress persistence migrations, lesson completion gates, controller
  detection changes, and UI layout work. This package only changes derived
  mission/prelude copy so screen practice remains useful but stops being the
  strongest target after three screen-only reps.

Reason:

- Free-practice banking made Learn feel playable, but screen-only repetition
  could fill the visible bank without nudging the learner toward physical
  control. Three screen reps should become warm-up: the next mission asks for
  one controller checkpoint while preserving screen fallback and all existing
  progress credit.

Proof before staging:

- `uv run pytest -q tests/learn/test_practice_mission.py tests/learn/test_ipc_handlers_dispatch.py::test_banked_practice_lesson_starts_with_proof_preface tests/learn/test_beatmatch_practice_audio_lifecycle.py::test_free_practice_distinct_controls_fill_practice_bank`
- `uv run ruff check src/vibemix/learn/runtime.py src/vibemix/learn/practice_mission.py tests/learn/test_practice_mission.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py src/vibemix/learn/practice_mission.py tests/learn/test_practice_mission.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `git diff --check -- src/vibemix/learn/runtime.py src/vibemix/learn/practice_mission.py tests/learn/test_practice_mission.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_beatmatch_practice_audio_lifecycle.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 133 - Debrief All Learn Practice Receipts

Suggested commit: `feat(debrief): include all learn practice receipts`

Include:

- `src/vibemix/debrief/main.py`
- `tests/debrief/test_transition_judged_critique.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Debrief schema changes, new UI frames, TLDR prompt rewrites, and Learn
  runtime logging changes. This package only lets already-logged Learn
  evidence receipts enter the cited critique stream.

Reason:

- Learn already logs control, beatmatch, cue-placement, and harmonic practice
  receipts. Debrief remembered beatmatch/cue but dropped control/harmonic,
  which broke the "what I practiced shows up tomorrow" utility loop. Surface
  all four receipt kinds through resolver-shaped `[ev:*@t]` atoms.

Proof before staging:

- `uv run pytest -q tests/debrief/test_transition_judged_critique.py`
- `uv run ruff check src/vibemix/debrief/main.py tests/debrief/test_transition_judged_critique.py`
- `uv run python -m compileall -q src/vibemix/debrief/main.py tests/debrief/test_transition_judged_critique.py`
- `git diff --check -- src/vibemix/debrief/main.py tests/debrief/test_transition_judged_critique.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 134 - Learn Mismatch Recovery Targets

Suggested commit: `feat(learn): turn wrong moves into recovery targets`

Include:

- `src/vibemix/learn/progress.py`
- `src/vibemix/learn/practice_mission.py`
- `src/vibemix/learn/runtime.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tauri/ui/src/learn/lesson/progress-list.ts`
- `tests/learn/test_ipc_handlers_dispatch.py`
- `tests/learn/test_runtime_evidence_grounding.py`
- `tests/learn/test_harmonic_practice_runtime.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New lesson content, new visual treatment, co-host prompt rewrites, and Learn
  completion-gate changes. This package only routes existing deterministic
  mismatch evidence into the already-built next-practice mission spine.

Reason:

- Learn could speak an adaptive wrong-control hint but forgot it immediately.
  Persist the wrong control / wrong deck / move-farther target as bounded
  `practice_feedback`, let the booth foreground it as a recovery mission, and
  clear the stale target when a grounded control or harmonic receipt lands.

Proof before staging:

- `uv run pytest -q tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py`
- `npm --prefix tauri/ui test -- tests/learn/test_progress_list.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
- `npm --prefix tauri/ui run check:ipc`
- `uv run python scripts/check_ipc_schema.py`
- `uv run ruff check src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/runtime.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py`
- `uv run python -m compileall -q src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/runtime.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py`
- `git diff --check -- src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/runtime.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/learn/lesson/curriculum-meta.ts tauri/ui/src/learn/lesson/progress-list.ts tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_harmonic_practice_runtime.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 135 - Folded Learn Local Practice Readiness

Suggested commit: `fix(learn-ui): make folded practice read alive offline`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/src/shell/StatusFooter.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `tauri/ui/tests/shell/shell.spec.ts`
- `tauri/ui/tests/shell/learn-folded-layout.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Lesson content rewrites, new backend packets, co-host/Sven prompt rewrites,
  and library ingest behavior. This package only fixes how the existing Learn
  practice surface reads inside the folded shell.

Reason:

- In the folded shell, Learn still spent standalone-window rows on hidden chrome
  and its own status bar while the shell footer overlaid the bottom edge. That
  made the tutor line clip and the screen read as dead when Sven was offline,
  even though the on-screen deck and subtitles-only tutor path were still
  usable. Reclaim the duplicate chrome space, reserve a real tutor row, and
  surface local input/credit/voice readiness in the booth panel.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts tests/shell/shell.spec.ts tests/shell/learn-folded-layout.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/styles/learn.css tauri/ui/src/shell/StatusFooter.ts tauri/ui/src/shell/shell.css tauri/ui/tests/learn/test_practice_booth_shell.spec.ts tauri/ui/tests/shell/shell.spec.ts tauri/ui/tests/shell/learn-folded-layout.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 136 - Learn Live Meter Waits For Proof

Suggested commit: `fix(learn-ui): hide idle beatmatch meter until graded`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Beatmatch scoring, lesson content, deck-proof backend behavior, and meter
  visuals. This package only changes when the existing live proof meter is
  allowed to appear.

Reason:

- Course 1 anatomy lessons looked blocked because the beatmatch meter mounted
  in its idle state on every lesson load, showing "waiting for decks / no proof
  yet" before any `ipc.learn.live_grade` evidence existed. Keep the meter hidden
  on first paint and lesson load, reveal it only when live grading arrives, and
  hide it again on lesson completion.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 137 - Earned Wall Hides Empty Locked Grid

Suggested commit: `fix(learn-ui): collapse empty locked skill wall`

Include:

- `tauri/ui/src/learn/SkillWall.ts`
- `tauri/ui/tests/learn/test_skill_wall.spec.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Skill-tree backend math, mastery gates, live proof rules, and trophy visuals.
  This package only changes how a zero-progress all-locked snapshot is rendered.

Reason:

- Fresh Learn snapshots can legitimately contain the six known skills, all
  locked with zero fill. Rendering those as six large locked cards makes the
  active practice screen look dead before the learner has earned anything.
  Collapse that exact zero-progress state into the honest empty Earned line,
  while preserving normal rows once any lesson or live proof has moved.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_skill_wall.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/SkillWall.ts tauri/ui/tests/learn/test_skill_wall.spec.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 138 - Viber Ingest Error Is Visible

Suggested commit: `fix(library-ui): show folder ingest failures in panel`

Include:

- `tauri/ui/library.html`
- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/library.css`
- `tauri/ui/src/library/chat.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Rust command resolution, CLAP model install behavior, Python folder ingest
  algorithms, Settings drawer import UI, and fake replay semantics. This
  package only makes real Viber ingest failures visible and retryable.

Reason:

- In Viber's ingest mode, backend failures were routed through `renderError()`,
  which writes to `.vmx-lib-results`; ingest mode hides that panel. A failed
  `library_embed_folder` therefore showed up mainly as the DevTools
  `[vmx-lib] run failed: embed-folder exited 1` log, while the user-facing
  ingest panel stayed ambiguous. Add a visible ingest error slot, preserve the
  backend message, show an actionable hint, and re-enable retry.

Proof before staging:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/library.html tauri/ui/src/library/index.ts tauri/ui/src/library/library.css tauri/ui/src/library/chat.test.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 139 - Viber DJ Knowledge Uses Text Embeddings

Suggested commit: `fix(library): route dj knowledge through text embedder`

Include:

- `src/vibemix/library/dj_knowledge.py`
- `src/vibemix/library/toolset.py`
- `src/vibemix/library/doctor.py`
- `tests/library/test_toolset.py`
- `tests/library/test_doctor.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Music-library CLAP search, knowledge corpus rebuilds, proxy registration
  changes, Viber prompt tuning, and live co-host speech behavior. This package
  only fixes the knowledge RAG embedder wiring and capability diagnosis.

Reason:

- The bundled DJ-knowledge store is a text-embedding space (`1536` dimensions),
  but `LibraryToolset.retrieve_dj_knowledge()` queried it with the normal
  music-library CLAP embedder (`512` dimensions). The retrieval guard correctly
  failed loud, and `library doctor` then mislabeled the healthy text store as
  orphaned by comparing it to the CLAP constant. Route DJ-knowledge through a
  dedicated text embedder sized to the store, keep CLAP for music search, and
  make doctor report the real requirement: a present store plus text-embedding
  credentials.

Proof before staging:

- `uv run pytest -q tests/library/test_dj_knowledge.py tests/library/test_toolset.py tests/library/test_doctor.py`
- `uv run python -m compileall -q src/vibemix/library/dj_knowledge.py src/vibemix/library/toolset.py src/vibemix/library/doctor.py tests/library/test_toolset.py tests/library/test_doctor.py`
- `uv run python -m vibemix library doctor --json`
- `uv run python - <<'PY' ... LibraryToolset(...).retrieve_dj_knowledge({"query": "EQ bass while blending", "k": 1}) ... PY`
- `git diff --check -- src/vibemix/library/dj_knowledge.py src/vibemix/library/toolset.py src/vibemix/library/doctor.py tests/library/test_toolset.py tests/library/test_doctor.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 140 - Memory Consent Updates Live Ingest Gate

Suggested commit: `fix(memory): update ingest gate on consent changes`

Include:

- `src/vibemix/runtime/session_loop.py`
- `tests/profile/test_profile_ipc.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Memory schema changes, recall prompt behavior, retention budget changes,
  CLAP ingest algorithms, and Wizard onboarding UI. This package only keeps the
  live session-loop ingest gate synchronized with the Settings profile-consent
  toggle.

Reason:

- `main()` resolves `memory_ingest_enabled` at boot from profile consent, but a
  fresh user can grant or revoke profile consent later through
  `ipc.profile.set_consent`. The handler persisted the new value and acked the
  renderer, but left `SessionLoop.memory_ingest_enabled` stale. That means a
  user who granted consent after boot could still skip close-path memory
  accrual, while a user who revoked consent could leave accrual enabled until
  relaunch. Update the live flag only after `save_consent()` succeeds.

Proof before staging:

- `uv run pytest -q tests/profile/test_profile_ipc.py tests/memory/test_ingest_wiring.py`
- `uv run python -m compileall -q src/vibemix/runtime/session_loop.py tests/profile/test_profile_ipc.py`
- `git diff --check -- src/vibemix/runtime/session_loop.py tests/profile/test_profile_ipc.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 141 - Learn Booth Shows Practice Mission Stakes

Suggested commit: `feat(learn-ui): surface practice mission stakes`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/learn/styles/learn.css`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Learn lesson FSMs, beginner-path suites, Python mission ranking, controller SVG
  assets, live grading algorithms, and Sven/Viber prompt behavior. This package
  only renders the existing backend `next_practice_mission` stakes in the Learn
  booth.

Reason:

- `next_practice_mission` already carries the utility loop (`why`, `payoff`,
  `challenge`, reward meter, and route chain), but the practice booth mostly
  showed command/proof. Surface those mission stakes as a compact frontstage
  strip so the next rep feels useful, finishable, and worth starting instead of
  looking like another static lesson row.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/src/learn/styles/learn.css tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Hold Lane - 2026-06-06 Untriaged Drift

Hold:

- `.trivyignore`
- `learn-no-empty-waveforms.png`
- `.planning/handbooks/liquid-glass/`
- `.planning/packets/2026-06-02/`
- `.planning/packets/2026-06-03/`
- `.planning/packets/2026-06-04/`
- `.planning/packets/2026-06-05/`
- `proxy/uv.lock`
- `tauri/ui/src/mascot/__tests__/v2-1-no-animation-cycle-warning.spec.ts`
- `tauri/ui/src/mascot/focus-layer.test.ts`
- `tauri/ui/tsconfig.json`
- `tauri/ui/vitest.config.ts`

Reason:

- These paths are currently dirty but unrelated to Package 141. Track them as
  hold-lane drift so the strict dirty-tree guard stays honest while this Learn
  booth package stages only its source, test, style, and checklist paths. The
  packet and handbook directories are broad tokens by design: they are planning
  artifacts, not source files for the Learn booth package.

## Package 142 - Folded Learn Mission Layout

Suggested commit: `fix(learn-ui): fit mission stakes in folded shell`

Include:

- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/learn-folded-layout.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Learn mission backend ranking, shell routing, sidebar/footer activation, Skill
  Wall rendering, and standalone Learn booth behavior. This package only keeps
  the folded shell layout aligned with the existing Learn booth mission rows.

Reason:

- The real app folds Learn into the desktop shell, whose CSS overrides the
  booth grid. After Package 141 added reward/mission/chain rows, the shell
  override still only named kicker/next/command/brief/pulse, so the new mission
  stakes could auto-place awkwardly in the user-tested app even though the
  standalone Learn window was green. Add folded grid areas and width caps for
  the same mission rows.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/shell/learn-folded-layout.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/shell/shell.css tauri/ui/tests/shell/learn-folded-layout.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 143 - Learn Mission Practice Surface Routing

Suggested commit: `feat(learn): route missions by practice surface`

Include:

- `src/vibemix/learn/practice_mission.py`
- `src/vibemix/learn/curriculum_projection.py`
- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tauri/ui/src/learn/learn-window.ts`
- `tests/learn/test_practice_mission.py`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Live grading algorithms, controller detection, lesson FSM timing, shell
  activation/footer behavior, and beginner-path suites. This package only adds
  an explicit mission contract for the surface the learner should use now.

Reason:

- The mission packet already tells the booth what to do, why it matters, and
  what reward is next, but the shell still inferred input/credit copy from
  current MIDI readiness. That made proof missions appear as screen reps when
  the actual next useful move needs live/cited proof, and made controller
  checkpoints depend on prose. Add `practice_surface` so the backend says
  `screen_deck`, `controller`, or `live_proof`, then let the booth render
  honest input/credit labels from that contract.

Proof before staging:

- `uv run pytest -q tests/learn/test_practice_mission.py tests/learn/test_progress_snapshot_skill_wall.py`
- `uv run python scripts/export_learn_curriculum_meta.py --check`
- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/learn/practice_mission.py src/vibemix/learn/curriculum_projection.py tauri/ui/src/learn/lesson/curriculum-meta.ts tauri/ui/src/learn/learn-window.ts tests/learn/test_practice_mission.py tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 144 - Learn Anatomy Ignores Beatmatch Proof Meter

Suggested commit: `fix(learn-ui): keep beatmatch meter off anatomy lessons`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Beatmatch judge math, Course 2/3 live grading, free-practice sandbox
  feedback, mission ranking, and footer activation state. This package only
  stops irrelevant beatmatch grades from painting the proof meter during Course
  1 controller-anatomy lessons.

Reason:

- The live grade meter's idle DOM says `waiting for decks` / `no proof yet`.
  That is correct for beatmatch/live-proof contexts, but confusing on lessons
  like pitch fader where the next useful move is a controller/screen action.
  Gate `ipc.learn.live_grade` so free practice, Course 2/3, and explicit
  live-proof missions still render the meter, while ordinary Course 1 anatomy
  lessons ignore unrelated beatmatch grades entirely.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 145 - Learn Mission Momentum Streaks

Suggested commit: `feat(learn): surface practice momentum streaks`

Include:

- `src/vibemix/learn/practice_mission.py`
- `src/vibemix/learn/curriculum_projection.py`
- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tests/learn/test_practice_mission.py`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `tests/ipc/test_learn_envelope_parity_p92.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New progress persistence fields, lesson FSM timing, live grading algorithms,
  shell layout, controller detection, beginner-path suites, and Sven/Viber
  prompt behavior. This package only derives a momentum/streak line from
  already-persisted practice receipts and keeps the closed IPC mission contract
  aligned.

Reason:

- The Learn booth already rewards a banked rep, but it does not make the next
  repetition feel sticky. Add `momentum_*` fields to the derived
  `next_practice_mission` packet so a learner sees "streak 2/3" and the exact
  next unlock ("one more clean rep fills the bank", "controller checkpoint
  next", "proof streak 2/3") from real `practice_sources` /
  `last_practice_seq` data. Update the JSON schema/codegen too, including the
  already-landed `practice_surface` field, so full progress snapshots validate
  through the real closed IPC envelope.

Proof before staging:

- `uv run pytest -q tests/learn/test_practice_mission.py tests/ipc/test_learn_envelope_parity_p92.py`
- `uv run python scripts/export_learn_curriculum_meta.py --check`
- `npm --prefix tauri/ui run codegen:ipc`
- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/learn/practice_mission.py src/vibemix/learn/curriculum_projection.py tauri/ui/src/learn/lesson/curriculum-meta.ts tauri/ui/src/learn/learn-window.ts tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tests/learn/test_practice_mission.py tauri/ui/tests/learn/test_practice_booth_shell.spec.ts tests/ipc/test_learn_envelope_parity_p92.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 146 - Learn Free Practice Repeats Earn Real Bank

Suggested commit: `fix(learn): count separate free-practice gestures`

Include:

- `src/vibemix/learn/runtime.py`
- `tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Mission ranking, lesson scripts, live-grade math, controller mapping, frontend
  reward rendering, and beginner-path suites. This package only changes the
  sandbox receipt dedupe rule so real repeated gestures can fill the persisted
  practice bank.

Reason:

- Free practice already shows a local warmup counter, but the backend de-duped
  receipts by `(lesson, source, control)` for the entire runtime. That protected
  against duplicate drag frames, but it also meant three deliberate reps on the
  same knob could paint as `warmup 3/3` while the stored Learn progress only
  banked one rep. Keep a duplicate-frame signature for continuous CC moves,
  continue collapsing exact repeated frames, cap the persisted bank at three,
  and let separate toggles/gestures on the same control earn the same
  controller-checkpoint mission the UI is promising.

Proof before staging:

- `uv run pytest -q tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py tests/learn/test_beatmatch_practice_audio_lifecycle.py`
- `git diff --check -- src/vibemix/learn/runtime.py tests/learn/test_beatmatch_practice_audio_lifecycle.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 147 - Library Index Receipts Stay Actionable

Suggested commit: `fix(library-ui): surface folder index receipts`

Include:

- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/chat.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Python ingest behavior, Tauri command spawning, model installation, Viber
  chat tooling, Learn lesson runtime, shell footer status, and fresh-user state
  resets. This package only changes the terminal folder-index receipt rendered
  by the library window when the existing bridge emits `library://embed-done`.

Reason:

- Fresh-user library setup should not end on a vague `done` or hide partial
  ingest failures. Current-source CLI proof on `/Users/ozai/Music/bois` shows
  the backend can legitimately finish as `0 embedded / 49 cached / 0 failed`;
  the UI should say that plainly. When failed files exist, keep the usable
  indexed tracks available while showing an actionable partial-failure receipt
  instead of looking clean or wedged.

Proof before staging:

- `uv run python -m vibemix library embed-folder /Users/ozai/Music/bois --strategy mean_excerpt --no-key --no-bpm --json`
- `npm --prefix tauri/ui test -- src/library/chat.test.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/library/index.ts tauri/ui/src/library/chat.test.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 148 - Library Setup Card Import Receipt

Suggested commit: `fix(library-ui): finish setup-card index receipts`

Include:

- `tauri/ui/src/library/index.ts`
- `tauri/ui/src/library/chat.test.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Python embed-folder behavior, Rust command spawning, chat answer rendering,
  model installation, ingest-tab replay, Learn runtime, and shell status. This
  package only fixes the first-user setup-card action that runs folder indexing
  from chat mode.

Reason:

- The chat setup card was a real first-run path, but it called
  `libraryEmbedFolder()` while the main embed listeners ignored events outside
  `state.mode === "ingest"`. A user could approve Viber's discovered music
  folder, the command could finish, and the card would still read like it only
  started. The setup action now listens for its own one-shot progress and done
  events, releases the button on completion, and falls back to a non-stuck
  command-finished receipt if the bridge accepts the command without a parsed
  terminal frame.

Proof before staging:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/library/index.ts tauri/ui/src/library/chat.test.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 149 - Learn Controller Checkpoint Readiness

Suggested commit: `fix(learn-ui): tell controller checkpoints apart`

Include:

- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Backend mission ranking, curriculum projection, controller mapping, MIDI
  driver behavior, lesson scripts, live-grade math, beginner-path suites,
  library ingest, and shell footer status. This package only changes how the
  existing Learn booth renders a controller-surface mission when runtime
  readiness is still screen-only.

Reason:

- After free-practice warmup, the backend can correctly ask for a hardware rep,
  but a fresh user with no controller connected sees the same ready-looking
  booth as a screen-deck mission. That reads like Learn is stalled. Keep the
  mission target intact, but make the frontstage say the controller checkpoint
  is waiting, keep the screen drill warm, and mark the hardware credit as
  pending until MIDI/controller proof is available.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/learn-window.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 150 - Learn Exemplar Provenance Chip

Suggested commit: `feat(learn): label packaged exemplar playback`

Include:

- `src/vibemix/learn/exemplar_lesson.py`
- `src/vibemix/ui_bus/learn_messages.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`
- `tests/learn/test_exemplar_lesson.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Exemplar ranking, packaged-bank audio assets, player routing, live Course 3
  audio guards, lesson transcript copy, citation grammar, library ingest, and
  controller mapping. This package only carries the already-known exemplar
  provenance through the closed IPC envelope and renders it in the Learn chip.

Reason:

- The engine already knows whether an EQ exemplar came from the user's library
  or from the packaged fallback bank, but `ipc.learn.exemplar_play` only sent a
  track id. Fresh-library users could see an opaque `_packaged:*` id while
  hearing a bundled example, which makes the lesson feel synthetic instead of
  honest. Add optional `source` and `reason` fields, preserve old payload
  compatibility, and let the UI show `packaged example` or `library example`
  with the reason in aria/title.

Proof before staging:

- `uv run pytest -q tests/learn/test_exemplar_lesson.py tests/ipc/test_learn_envelope_parity_p92.py`
- `npm --prefix tauri/ui run codegen:ipc`
- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
- `uv run python scripts/check_ipc_schema.py`
- `uv run ruff check src/vibemix/learn/exemplar_lesson.py src/vibemix/ui_bus/learn_messages.py tests/learn/test_exemplar_lesson.py`
- `uv run python -m compileall -q src/vibemix/learn/exemplar_lesson.py src/vibemix/ui_bus/learn_messages.py tests/learn/test_exemplar_lesson.py`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/learn/exemplar_lesson.py src/vibemix/ui_bus/learn_messages.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/learn/learn-window.ts tauri/ui/tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_exemplar_lesson.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 151 - Recordings Voice Replay Availability

Suggested commit: `fix(recordings-ui): skip missing voice replay loads`

Include:

- `src/vibemix/runtime/recordings_index.py`
- `src/vibemix/ui_bus/messages.py`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tauri/ui/src/settings/components/recording-row.ts`
- `tauri/ui/src/settings/components/recording-row.spec.ts`
- `tests/recording/test_recordings_index.py`
- `tests/ui_bus/test_recordings_messages.py`
- `tests/ui_bus/test_messages_schema.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Recording asset scope changes, debrief renderer changes, recorder close
  semantics, retention/deletion behavior, live voice/TTS routing, library ingest,
  and Learn runtime work. This package only lets the recordings list tell the UI
  whether a `voice.wav` artifact exists before the row mounts a replay player.

Reason:

- Fresh-user sessions can contain `events.jsonl` without a `voice.wav` artifact.
  The Settings recordings row still mounted an `asset://.../voice.wav` audio
  element on expand, causing WebKit 403 spam and making the drawer look broken
  even though the events list loaded correctly. Add an additive
  `voice_available` summary field, derive it from a regular-file check under
  the recordings root, and have the row render a quiet unavailable receipt
  instead of requesting a missing audio asset.

Proof before staging:

- `uv run pytest -q tests/recording/test_recordings_index.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_messages_schema.py`
- `npm --prefix tauri/ui run codegen:ipc`
- `npm --prefix tauri/ui test -- src/settings/components/recording-row.spec.ts`
- `uv run python scripts/check_ipc_schema.py`
- `uv run ruff check src/vibemix/runtime/recordings_index.py src/vibemix/ui_bus/messages.py tests/recording/test_recordings_index.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_messages_schema.py`
- `uv run python -m compileall -q src/vibemix/runtime/recordings_index.py src/vibemix/ui_bus/messages.py tests/recording/test_recordings_index.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_messages_schema.py`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/runtime/recordings_index.py src/vibemix/ui_bus/messages.py tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tauri/ui/src/settings/components/recording-row.ts tauri/ui/src/settings/components/recording-row.spec.ts tests/recording/test_recordings_index.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_messages_schema.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 152 - Learn Recovery Mission Recency

Suggested commit: `feat(learn): prioritize fresh recovery missions`

Include:

- `src/vibemix/learn/progress.py`
- `src/vibemix/learn/practice_mission.py`
- `src/vibemix/learn/curriculum_projection.py`
- `tauri/ui/src/learn/lesson/curriculum-meta.ts`
- `tauri/ui/src/learn/lesson/progress-list.ts`
- `tauri/ui/tests/learn/test_curriculum_meta.spec.ts`
- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `tests/learn/test_progress_persistence.py`
- `tests/learn/test_practice_mission.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- New Learn UI layouts, runtime grading behavior, spoken tutor copy, beginner
  path wiring, controller mapping, lesson content, and live co-host changes. The
  package only makes already-persisted measured misses carry recency and makes
  the backend mission plus frontend recommendation choose the freshest recovery
  target before generic unfinished or banked practice.

Reason:

- Learn already stores measured misses as recovery targets and the UI already
  ranks a fix above ordinary progress, but the backend next-practice mission
  could still route a returning user through linear or banked practice unless
  the missed lesson was active. Persist an additive `last_feedback_seq`, clear
  it with the stale feedback, and use it to choose the newest recovery mission
  deterministically after reloads.

Proof before staging:

- `uv run pytest -q tests/learn/test_progress_persistence.py tests/learn/test_practice_mission.py tests/learn/test_curriculum_projection.py tests/ui_bus/test_messages_schema.py`
- `python scripts/export_learn_curriculum_meta.py`
- `npm --prefix tauri/ui run codegen:ipc`
- `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts`
- `uv run python scripts/check_ipc_schema.py`
- `uv run ruff check src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/curriculum_projection.py tests/learn/test_progress_persistence.py tests/learn/test_practice_mission.py tests/learn/test_curriculum_projection.py`
- `uv run python -m compileall -q src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/curriculum_projection.py tests/learn/test_progress_persistence.py tests/learn/test_practice_mission.py tests/learn/test_curriculum_projection.py`
- `npm --prefix tauri/ui run build`
- `git diff --check -- src/vibemix/learn/progress.py src/vibemix/learn/practice_mission.py src/vibemix/learn/curriculum_projection.py tauri/ui/src/learn/lesson/curriculum-meta.ts tauri/ui/src/learn/lesson/progress-list.ts tauri/ui/tests/learn/test_curriculum_meta.spec.ts tauri/ui/src/ipc/messages.schema.json tauri/ui/src/ipc/messages.ts tauri/ui/src/ipc/validator.generated.mjs tests/learn/test_progress_persistence.py tests/learn/test_practice_mission.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 153 - Learn Recital Recovery Targets

Suggested commit: `feat(learn): route failed recitals to recovery practice`

Include:

- `src/vibemix/learn/recital.py`
- `src/vibemix/learn/practice_mission.py`
- `tests/learn/test_recital.py`
- `tests/learn/test_course_2_recital.py`
- `tests/learn/test_practice_mission.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Beginner-path suites, new lesson content, UI layout changes, spoken tutor
  rewrite work, live co-host routing, and new grading algorithms. This package
  only lets an already-scored recital fail persist the first missed source
  prompt as the same bounded recovery target that Learn missions already know
  how to render.

Reason:

- Recital fail copy told the learner to replay the check, but did not feed the
  missed checkpoint back into the practice loop. Persist the first unscored
  recital prompt as a measured miss, emit a progress snapshot after the save,
  and let recovery missions reopen a completed lesson only when a fresh
  measured miss exists. Completion still clears stale targets, so normal course
  progress does not nag forever.

Proof before staging:

- `uv run pytest -q tests/learn/test_recital.py tests/learn/test_course_2_recital.py tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py`
- `uv run ruff check src/vibemix/learn/recital.py src/vibemix/learn/practice_mission.py tests/learn/test_recital.py tests/learn/test_course_2_recital.py tests/learn/test_practice_mission.py`
- `uv run python -m compileall -q src/vibemix/learn/recital.py src/vibemix/learn/practice_mission.py tests/learn/test_recital.py tests/learn/test_course_2_recital.py tests/learn/test_practice_mission.py`
- `git diff --check -- src/vibemix/learn/recital.py src/vibemix/learn/practice_mission.py tests/learn/test_recital.py tests/learn/test_course_2_recital.py tests/learn/test_practice_mission.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 154 - Learn Recital Recovery Clearance

Suggested commit: `fix(learn): clear recital recovery targets on pass`

Include:

- `src/vibemix/learn/recital.py`
- `tests/learn/test_recital.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Practice mission ranking changes, new recital scoring rules, UI layout work,
  beginner-path suites, spoken tutor rewrites, and broader progress schema
  changes. This package only clears stale recital-created recovery targets when
  the sampled recital prompts are later passed.

Reason:

- A failed recital now feeds the first missed source prompt into recovery
  practice. Once the user later passes that sampled recital prompt, keeping the
  old `recital miss` target would make Learn keep nudging a move the user just
  proved. Clear only recital-authored targets with the exact label/message on
  the sampled prompts, and persist the cleanup together with the existing unlock
  save.

Proof before staging:

- `uv run pytest -q tests/learn/test_recital.py tests/learn/test_course_2_recital.py tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py`
- `uv run ruff check src/vibemix/learn/recital.py tests/learn/test_recital.py`
- `uv run python -m compileall -q src/vibemix/learn/recital.py tests/learn/test_recital.py`
- `git diff --check -- src/vibemix/learn/recital.py tests/learn/test_recital.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 155 - Learn Failed Recitals Stay Uncompleted

Suggested commit: `fix(learn): keep failed recitals uncompleted`

Include:

- `src/vibemix/learn/runtime.py`
- `tests/learn/test_ipc_handlers_dispatch.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Recital scoring changes, practice mission ranking, regular user-skip
  persistence semantics, UI layout work, beginner-path suites, and progress
  schema changes. This package only distinguishes a failed observer-driven gate
  from a completed or skipped regular lesson at the runtime progress write site.

Reason:

- Observer recitals already report `completed=False` to the canonical
  `LessonRuntime` bridge on fail, but `on_enter_completed` still called
  `mark_completed(... demonstrated=False)`, which made the failed recital dot
  look completed while the course gate stayed locked. Keep regular user-skip
  behavior unchanged, but suppress the progress completion write for failed
  observer gates so the user sees the gate still needs a real pass.

Proof before staging:

- `uv run pytest -q tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_recital.py tests/learn/test_course_2_recital.py tests/learn/test_practice_mission.py tests/learn/test_progress_persistence.py`
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/test_ipc_handlers_dispatch.py`
- `uv run python -m compileall -q src/vibemix/learn/runtime.py tests/learn/test_ipc_handlers_dispatch.py`
- `git diff --check -- src/vibemix/learn/runtime.py tests/learn/test_ipc_handlers_dispatch.py .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 156 - Learn Completed Recovery Fix Badges

Suggested commit: `fix(learn-ui): surface completed recovery fixes`

Include:

- `tauri/ui/src/learn/lesson/progress-list.ts`
- `tauri/ui/tests/learn/test_progress_list.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- Backend mission ranking, recital scoring, broader Learn window layout,
  beginner-path suites, and visual redesign. This package only makes the
  progress list honor the backend's completed-lesson recovery mission.

Reason:

- Backend recovery can now reopen a previously completed lesson when a fresh
  measured miss lands there, but the progress list dropped all feedback for
  completed rows. That made the row and course summary look fully complete
  while the booth button was correctly saying "fix". Let a recommended
  completed row with valid measured feedback render as a fix, while ordinary
  completed rows stay plain replay.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_progress_list.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/lesson/progress-list.ts tauri/ui/tests/learn/test_progress_list.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`

## Package 157 - Learn Tutor Subtitle Voice Receipt

Suggested commit: `fix(learn-ui): label muted tutor lines as subtitles`

Include:

- `tauri/ui/src/learn/lesson/tutor-dock.ts`
- `tauri/ui/src/learn/learn-window.ts`
- `tauri/ui/tests/learn/test_tutor_speak_sr_announcement.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`

Keep out:

- TTS backend changes, shell footer redesign, Learn copy rewrites,
  beginner-path suites, and co-host/Sven prompt work. This package only makes
  the tutor receipt match the already-reported local voice state.

Reason:

- The Learn tutor dock printed `speaking` for every authored tutor line even
  when `ipc.status.tick` reported `voice: muted`. That made subtitle-only
  lessons look like broken voice playback during fresh user tests. Pass the
  latest Learn voice status into `TutorSpeakDock.show()` so muted tutor lines
  are labeled as subtitles while normal/unknown voice states keep the existing
  speaking receipt.

Proof before staging:

- `npm --prefix tauri/ui test -- tests/learn/test_tutor_speak_sr_announcement.spec.ts`
- `npm --prefix tauri/ui run build`
- `git diff --check -- tauri/ui/src/learn/lesson/tutor-dock.ts tauri/ui/src/learn/learn-window.ts tauri/ui/tests/learn/test_tutor_speak_sr_announcement.spec.ts .planning/handoffs/2026-05-31-package-checklist.md`
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
