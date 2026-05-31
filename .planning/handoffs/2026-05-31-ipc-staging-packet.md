# IPC Staging Packet - Packages 2 + 3 - 2026-05-31

Purpose: give the next agent a concrete, reviewable packet for the combined IPC
contract package. This is planning/evidence only. Do not stage these files
unless the user opens a staging window.

## Decision

Default to one combined Package 2 + Package 3 review:

- Package 2 wires session diagnostics, profile/settings/session consumers, and
  runtime ingress behavior.
- Package 3 prunes stale schema-only IPC contracts and locks the top-level IPC
  count at 72.

Splitting is risky because the same contract spine is shared by Python message
wrappers, JSON schema, generated TypeScript, generated AJV validator, UI
consumers, mock-transfer contract anchors, and parity/count tests.

## Current Evidence

Fresh planning pass evidence:

- `uv run python scripts/check_ipc_schema.py`
  - `OK: 72 dataclasses validate against schema`
  - `OK: count parity - 72 oneOf entries == 72 wrapper dataclasses`
  - `OK: SettingsSet field enum parity`
  - `OK: SettingsState payload parity`
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
  - 72 message types declared
  - 72 shell references
  - 72 sidecar references
  - OK: every type has both shell and sidecar reference
- `uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary`
  - green at the time of this packet; every dirty path assigned

This proves current contract shape is internally consistent. It does not prove
GUI click behavior, live Settings drawer behavior, or Tauri renderer logs.

## Stage List

Stage the dirty subset of these paths only. If a path below is clean when the
staging window opens, do not force it into the commit.

Python runtime and schema spine:

- `src/vibemix/runtime/session_loop.py`
- `src/vibemix/runtime/ws_bus.py`
- `src/vibemix/ui_bus/__init__.py`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/ui_bus/schemas/debrief.py`
- `src/vibemix/ui_bus/schemas/library.py`
- `src/vibemix/ui_bus/validator.py`
- `scripts/check_ipc_schema.py`

Library contract cleanup:

- `src/vibemix/library/search.py`
- `src/vibemix/library/similar.py`
- `tauri/src-tauri/src/library_cmds.rs`

Frontend IPC schema and consumers:

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

Tests and fixtures:

- `tests/runtime/test_session_loop.py`
- `tests/wizard/test_wizard_loop_ipc.py`
- `tests/ipc/test_library_schemas.py`
- `tests/ipc/test_learn_envelope_parity.py`
- `tests/ui_bus/test_status_tick.py`
- `tests/ui_bus/test_messages_schema.py`
- `tests/ui_bus/test_mood_change_envelope.py`
- `tests/ui_bus/test_recordings_messages.py`
- `tests/ui_bus/test_citation_schema.py`
- `tests/ui_bus/fixtures/debrief_schema_v2_1_baseline.json`
- `tests/ui_bus/test_debrief_schema_additive_only.py`
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py`
- `tests/ui_bus/test_debrief_schemas.py`
- `tests/ui_bus/test_overlay_schema.py`
- `tauri/ui/tests/session/components.spec.ts`
- `tauri/ui/tests/mock-transfer-contract.spec.ts`
- `tauri/ui/tests/session/render-loop-actions.spec.ts`
- `tauri/ui/tests/session/ws-bridge.recordings.spec.ts`
- `tauri/ui/tests/settings/drawer.spec.ts`

Agent docs/tooling hunk:

- `AGENTS.md` only for the IPC count/tooling guidance hunk.
- `.claude/skills/ipc-wiring-checker/SKILL.md`
- `.claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`

## Keep Out

Do not include these nearby dirty lanes in the IPC commit:

- `src/vibemix/runtime/diag.py` - runtime diagnostic stdout resilience hold.
- `tauri/src-tauri/src/sidecar.rs` - Tauri sidecar log-drain hold.
- `tauri/ui/src/library/api.ts`, `tauri/ui/src/library/index.ts`, and library UI
  tests - Package 5 Viber live-read context.
- `src/vibemix/library/ingest.py`, `src/vibemix/library/smart_cues.py`,
  `src/vibemix/intel/move_grade.py`, and cue tests - Package 4 cue pipeline.
- `tauri/ui/src/pill/**` and `tauri/ui/tests/pill/**` - Package 6 pill polish.
- `CLAUDE.md` - runtime orientation drift hold.
- `uv.lock`, pricing docs, launch/design screenshots, Singularity research, and
  local TTS files.

## Current Dirty Footprint

The current IPC-shaped dirty footprint is large enough that whole-file staging
without review is unsafe. Recent `git diff --numstat` highlights:

- `tauri/ui/src/ipc/messages.schema.json`: 1 insertion / 414 deletions
- `tauri/ui/src/ipc/messages.ts`: 0 insertions / 90 deletions
- `src/vibemix/ui_bus/messages.py`: 5 insertions / 190 deletions
- `src/vibemix/ui_bus/schemas/library.py`: 3 insertions / 76 deletions
- `src/vibemix/runtime/ws_bus.py`: 33 insertions / 22 deletions
- `src/vibemix/ui_bus/validator.py`: 30 insertions / 1 deletion
- `tauri/ui/src/settings/SettingsDrawer.ts`: 171 insertions / 34 deletions
- `tauri/ui/src/session/SessionLayout.ts`: 98 insertions / 38 deletions
- `tests/ui_bus/test_messages_schema.py`: 28 insertions / 103 deletions

Treat the schema deletion count as a contract deletion, not a cosmetic cleanup.
The removed IPC ghosts must stay removed across Python, TypeScript, validators,
tests, mock-transfer anchors, and Rust/UI call sites.

## Pre-Stage Commands

Run before staging:

```bash
git status --short
git diff --shortstat
git ls-files --others --exclude-standard | wc -l
uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
uv run python scripts/check_ipc_schema.py
uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py
```

If either IPC checker fails before staging, stop and inspect the generated schema
or wiring delta before touching the index.

## Staging Review

After staging the combined packet, verify the cached set:

```bash
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
git diff --cached -- src/vibemix/ui_bus/messages.py
git diff --cached -- tauri/ui/src/ipc/messages.schema.json
git diff --cached -- tauri/ui/src/ipc/messages.ts
git diff --cached -- tauri/ui/src/ipc/validator.generated.mjs
git diff --cached -- tests/ui_bus/test_messages_schema.py
```

Abort if the cached diff contains runtime diagnostic holds, Tauri sidecar log
drain, cue/pill/library-live-read work, design/launch assets, pricing, local TTS,
or unrelated `__main__.py` hunks.

## Verification Commands

Minimum contract gates for a combined IPC commit:

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
```

Frontend gates:

```bash
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

Rust gate if `tauri/src-tauri/src/library_cmds.rs` is dirty/staged:

```bash
cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds
```

Live proof remains separate:

- Source diagnostic bus can prove sidecar handlers.
- Full Tauri live app proof is still needed for GUI click/log rendering paths:
  Settings/Profile open, `ipc.status.recheck`, `ipc.error`,
  `ipc.session.citation`, and staleness subscriptions.

## Split Rules

Only split Packages 2 and 3 if the split is deliberate and the schema-count
commit owns all of these together:

- `tauri/ui/src/ipc/messages.schema.json`
- `tauri/ui/src/ipc/messages.ts`
- `tauri/ui/src/ipc/validator.generated.mjs`
- `src/vibemix/ui_bus/messages.py`
- `src/vibemix/ui_bus/__init__.py`
- schema wrappers under `src/vibemix/ui_bus/schemas/`
- `scripts/check_ipc_schema.py`
- all count/parity tests

The other split may carry runtime/UI consumers only after the contract baseline
is already green. If `check_ipc_schema.py`, the wiring checker, or
`npm --prefix tauri/ui run check:ipc` fails, widen the split back into the
combined package.

## Commit Message

Recommended combined commit:

```text
fix(ipc): prune stale contracts and wire diagnostics
```

Use `git commit -s`. Before committing, ensure no other session has staged
extra files:

```bash
git diff --cached --name-only
```
