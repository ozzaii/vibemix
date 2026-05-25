---
status: complete
slug: dead-controls-fix
date: 2026-05-25
branch: live-tuning-or-brain
---

# Dead session controls — root-cause + fix

Kaan ran the real `cargo tauri dev` app and reported: "none of the buttons
work… HYPE doesn't work, beg/int/pro doesn't work, dropdown drill-downs
don't work." All unit tests were green. This closes the two real frontend
bugs + the missing backend field behind them.

## Root cause (from code, confirmed)

The session components themselves are fine — the SAME `renderRocker` /
`renderPicker` render both working and "dead" controls. The bugs were in
the wiring:

1. **BEG/INT/PRO skill rocker** — shipped as a static read-only render with
   **no `onChange` at all** (`SessionLayout.ts`), AND there was **no `skill`
   field anywhere** in the IPC schema / `SettingsApplier` / config. Fully
   dead end-to-end. (The mood rocker, by contrast, has an `onChange` +
   optimistic `setRockerActive`, which is why HYPE/TEACH/COACH at least
   flip.)

2. **Voice / genre / device pickers** — `onChange` fired `sendSettings`, but
   the picker **never updated its own row label optimistically**. Without a
   live sidecar round-trip (which never comes in dev), selecting an option
   closed the dropdown with the displayed value unchanged → "does nothing."

## Fix

- `picker.ts` — added `selectOption(label)`: on option click, optimistically
  update the row label + `data-selected`/`aria-selected` (the picker analog
  of `rocker.setRockerActive`). +`picker.test.ts` (5 tests).
- `SessionLayout.ts` — skill rocker is now a `const skillRocker` with an
  `onChange` (optimistic `setRockerActive` + `sendSettings("skill", …)`).
  Added `deckSkillToWire(BEG/INT/PRO → beginner/intermediate/pro)`.
- `skill` field wired through the whole IPC spine:
  `ws-bridge.ts SETTINGS_FIELDS`, `ipc/messages.ts` (SettingsSet union +
  optional SettingsState.skill), `ipc/messages.schema.json` (field enum +
  optional SettingsState.skill), Python `ui_bus/messages.py`
  (SettingsSetPayload.field + SettingsStatePayload.skill + SettingsState.make),
  `runtime/settings.py` `_apply_skill` (validate enum → set
  `VIBEMIX_SKILL_LEVEL` env → persist `extra["skill"]`),
  `session_loop._emit_settings_state` round-trips skill from `extra`.

`_apply_skill` sets the env var that `DJCoHostAgent._resolve_prompt_cell`
reads at build → new level applies on the next agent build (same lifecycle
mood rides on; mid-session live re-instantiation is the shared Plan 13-06
surface, not done here).

## Verification

- `scripts/check_ipc_schema.py` — OK (64/64 parity).
- pytest `runtime/test_settings_apply.py` 31 (+3 skill), `test_session_loop`,
  `ui_bus`, `ipc` green.
- vitest full 874 (+5 picker), tsc clean.

## Known residual (not a dead button)

The persona panel body is built once at mount and not rebuilt by the render
loop, so on boot the skill rocker shows the default "INT" rather than the
persisted value (same limitation voice/genre/mood already have). Optimistic
flip makes the control work; boot-sync of persisted value is a separate
small item.

## "verify everything" pass — 5 pre-existing failures also resolved

The prior session's 50-file uncommitted batch had left 5 baselines trailing
already-committed code (none caused by this fix). Resolved during the
verify-everything pass:

1. `test_router_resolves_all_paths` — the e2e expected-table mirror was
   missing `library_agent` (added to ROUTER_PATHS + _ROUTES when the Viber
   agent shipped). Synced the test to production (gemini-3-flash-preview / FLEX).
2. Tauri **capability snapshot** — refreshed `capabilities-snapshot/SNAPSHOT.json`
   to match the committed `default.json` (commit a1ffcb2 added documented
   dev-path `python3`/`uv` shell-execute entries + `library` window scope for
   the vibe-engine bridge — NOT a regression, baseline just trailed).
3. `docs/AUDIT.md` — regenerated (generator-drift gate).
4. orphan baseline `.planning/codebase/orphans.csv` — refreshed: dropped
   `IngestResult` (now wired), added `mcp_server.py` `build_server`/`build_toolset`
   (MCP entry points, orphan to static analysis).

All 5 → green. Backend wire path also verified end-to-end with REAL classes
(SettingsSet→SettingsApplier→persist→env→SettingsState round-trip + schema
validation + reject path), and the live vite dev server confirmed serving the
changed modules (selectOption, deckSkillToWire/skillRocker, skill field).

## LIVE-VERIFY (the lesson: green tests ≠ working app)

In the real `cargo tauri dev` app: click BEG/INT/PRO (segment should light),
click each dropdown + an option (row label should change instantly), confirm
`[vmx:click]` lines land in the file-based debug log.
