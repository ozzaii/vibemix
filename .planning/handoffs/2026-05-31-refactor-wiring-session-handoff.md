# Refactor/Wiring Session Handoff - 2026-05-31

Purpose: give another AI session a bounded way to take refactor/wiring work
without sweeping up every floating dirty file. This handoff is not permission to
refactor the whole tree. Pick one lane, prove it, and stage only that lane.

## Start Here

Read in this order:

1. `AGENTS.md` - repository rules, excluded suites, live-proof expectations, and
   IPC/codegen discipline.
2. `CLAUDE.md` - deeper runtime/product context and local source-mode caveats.
3. `.planning/handoffs/2026-05-31-future-ai-routing.md` - current doorway into
   the dirty tree.
4. `.planning/handoffs/2026-05-31-package-checklist.md` - authoritative dirty
   path assignment table. If a dirty path is not listed under `Include:` or
   `Hold:`, classify it before coding or staging.
5. `.planning/handoffs/2026-05-31-ipc-staging-packet.md` - use this if taking
   the recommended IPC contract lane.
6. `.planning/handoffs/2026-05-31-dependency-modernization-packet.md` - use this
   only for dependency modernization, and keep it out of feature commits.

## Recommended First Lane

Take the combined Package 2 + Package 3 IPC contract lane first.

Why:

- Packages 2 and 3 share the Python message wrappers, JSON schema, generated
  TypeScript, generated validator, UI consumers, mock-transfer contract anchors,
  and count/parity tests.
- The current top-level IPC count is intentionally 72. Splitting the contract
  cleanup from the diagnostics/settings wiring can produce a false green if
  generated files or parity tests land in different commits.
- The staging packet already records the current proof commands, keep-outs, and
  split rules.

Expected commit shape:

- Commit message: `fix(ipc): prune stale contracts and wire diagnostics`
- Scope: only the Package 2 + Package 3 dirty subset and its tests/docs hunk.
- Stage by path and inspect the cached diff. Use hunk staging for shared docs.
- Do not include unrelated runtime, cue, pill, Viber, design, launch, pricing,
  local TTS, signing, or dependency files.

## Keep Out

Do not include these in the first refactor/wiring pass:

- `src/vibemix/runtime/diag.py` - runtime diagnostic stdout resilience hold.
- `tauri/src-tauri/src/sidecar.rs` - Tauri sidecar log-drain hold.
- `docs/signing-macos.md`, `scripts/dist/sign_macos.sh`, and
  `tauri/src-tauri/tauri.conf.json5` - release packaging/signing hold.
- `src/vibemix/library/ingest.py`, `src/vibemix/library/smart_cues.py`,
  `src/vibemix/intel/move_grade.py`, `tauri/ui/src/pill/**`, and Viber/library
  UI paths - Packages 4-6 cue/pill/Viber product pipeline.
- `uv.lock`, `pyproject.toml`, `tauri/ui/package.json`,
  `tauri/ui/package-lock.json`, `tauri/src-tauri/Cargo.toml`, and `Cargo.lock`
  unless the user explicitly opens the dependency-modernization lane.
- `.planning/singularity/**`, launch collateral, pricing docs, generated
  screenshots, and public-claims material.
- GSD and beginner Learn suites unless the user explicitly asks for that lane.

## Alternate Lanes

If the user does not want IPC first:

- Product musical value: take Packages 4-6 together as a cue/pill/Viber pipeline.
  Require live DDJ/Viber evidence before claiming app-level correctness.
- Low-risk runtime cleanup: take one of Packages 12-15, but keep sidecar-log,
  diagnostic-output, signing, and dependency lanes separate.
- Dependency modernization: use the modernization packet and work ring by ring.
  Do not mix library upgrades with active feature packages.
- Visual polish: take one frontend proof lane with UI tests, build proof, and
  screenshots. Do not call static mockups live product evidence.

## Evidence Gates

Before staging any refactor/wiring package:

```bash
git status --short
git diff --shortstat
git ls-files --others --exclude-standard | wc -l
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
```

For the recommended IPC lane:

```bash
uv run python scripts/check_ipc_schema.py
uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py
uv run pytest -q \
  tests/ipc/test_library_schemas.py \
  tests/ipc/test_learn_envelope_parity.py \
  tests/ui_bus/test_messages_schema.py \
  tests/ui_bus/test_mood_change_envelope.py \
  tests/ui_bus/test_recordings_messages.py \
  tests/ui_bus/test_status_tick.py \
  tests/ui_bus/test_citation_schema.py \
  tests/ui_bus/test_overlay_schema.py \
  tests/ui_bus/test_debrief_new_wrappers_roundtrip.py \
  tests/ui_bus/test_debrief_schema_additive_only.py \
  tests/ui_bus/test_debrief_schemas.py \
  tests/runtime/test_session_loop.py \
  tests/wizard/test_wizard_loop_ipc.py
npm --prefix tauri/ui run check:ipc
npm --prefix tauri/ui test -- \
  tests/mock-transfer-contract.spec.ts \
  tests/session/components.spec.ts \
  tests/session/render-loop-actions.spec.ts \
  tests/session/ws-bridge.recordings.spec.ts \
  tests/settings/drawer.spec.ts \
  src/settings/components/profile-panel.spec.ts \
  src/settings/components/citation-diagnostics.spec.ts
npm --prefix tauri/ui run build
```

Live proof is still separate. The source diagnostic bus proves sidecar handlers;
full Tauri proof is required for GUI click/log rendering paths.

## Staging Rules

- Never run `git add -A`.
- Stage exactly the chosen package paths.
- Use `git diff --cached --name-only`, `git diff --cached --check`, and
  `git diff --cached --stat` before committing.
- If another session staged files, stop and inspect the cached set before adding
  anything.
- Make DCO-signed commits with `git commit -s`.
- After committing, rerun the dirty package checker and update the checklist if
  new drift appears.

## Handoff Prompt

Use this prompt when giving the lane to another session:

```text
You are taking one bounded refactor/wiring package in
/Users/ozai/projects/dj-set-ai.

Do not refactor the whole tree. Do not stage broad dirty work.

Read:
- AGENTS.md
- CLAUDE.md
- .planning/handoffs/2026-05-31-future-ai-routing.md
- .planning/handoffs/2026-05-31-package-checklist.md
- .planning/handoffs/2026-05-31-ipc-staging-packet.md

Target lane:
Combined Package 2 + Package 3 IPC contract.

Goal:
Review and, if still green, stage only the IPC contract/wiring package:
diagnostic/profile/session IPC, stale-contract pruning, generated schema/TS
validator parity, mock-transfer anchors, and focused tests.

Keep out:
runtime diag stdout hold, Tauri sidecar log drain, signing/notarization files,
cue/pill/Viber packages, dependency manifests, pricing/launch/design collateral,
local TTS, Singularity research, GSD, and beginner Learn suites.

Required evidence:
run the package checker, IPC schema checker, IPC wiring checker, focused Python
tests, UI IPC/tests/build, cached diff review, then commit with git commit -s.

If any dirty path is unassigned, classify it before staging.
```
