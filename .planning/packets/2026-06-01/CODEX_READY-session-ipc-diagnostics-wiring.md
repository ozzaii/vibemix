# CODEX_READY: Session IPC And Diagnostics Wiring

Date: 2026-06-01
Author: Codex
Status: LAND packet, session transport and diagnostics slice
Package: Package 2 - Session IPC And Diagnostics Wiring

## Decision

LAND this slice as `fix(session-ipc): wire status recheck errors and citation telemetry`.

The current source has a schema-valid session IPC spine for the live deck UI:
status rechecks, profile view, generic IPC errors, session citations, mute
acks, drop countdown bars, live-claim proof policy, overlay highlights, and
settings diagnostics are wired through the Python sidecar boundary and the
Tauri UI consumers. The package is landable only with its schema/codegen/count
parity intact; Package 2 and Package 3 share generated IPC files, so staging
must be hunk-level or intentionally combined.

## Files

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

## What Changed

- `ipc.status.recheck` is a real button-to-sidecar path: the session render loop
  emits it, `SessionLoop` validates the component and replies with
  `ipc.status.tick` or `ipc.error`.
- `ipc.profile.view` is a request/reply path from the Settings profile panel to
  the session handler. The drawer preserves the profile panel handle across
  drawer refreshes, so opening Settings sends one profile view request per open
  cycle instead of spamming the bus.
- `normalize_legacy_timestamp(...)` accepts old local drive-tool numeric `ts`
  only at websocket/session ingress. The schema and generated wrappers remain
  strict.
- `predicted_drop_bars(...)` converts finite `predicted_drop_in_sec` plus BPM
  into whole bars; snapshots carry `drop_pred_bars`; the session UI mounts the
  existing drop chip only when the value is non-null.
- Live claim policy is collapsed into a small `claim_policy` snapshot payload
  and rendered as a bottom-row proof chip without changing co-host wording.
- `ipc.session.citation` feeds the Settings diagnostics row through
  `ws-bridge.ts` and the component-local diagnostics store.
- `ipc.session.mute` is optimistic in the UI and authoritative on sidecar ack;
  the backend clears the playback queue when muting engages.
- The session router now starts and tears down the overlay-highlight listener
  for spoken `[screen:*]` citations.
- During this verification pass, Codex fixed mock-transfer coverage for the new
  runtime anchors: `session.drop`, `session.claim-policy`,
  `settings.persona.voice.deferred-note`, and `settings.output.deferred-note`.

## Wiring Evidence

`vibemix_dev.which_handler` reported both-end wiring for:

- `ipc.status.recheck`
- `ipc.profile.view`
- `ipc.session.citation`
- `ipc.session.overlay-highlight`
- `ipc.library.staleness_nudge`
- `ipc.session.snapshot`

Selected source anchors:

- `src/vibemix/runtime/session_loop.py:271` registers
  `ipc.status.recheck`; `src/vibemix/runtime/session_loop.py:1021` emits a
  fresh tick or `ipc.error`.
- `src/vibemix/runtime/session_loop.py:282` registers `ipc.profile.view`;
  `src/vibemix/runtime/session_loop.py:581` emits
  `ipc.profile.view_result`.
- `src/vibemix/ui_bus/validator.py:37` contains the ingress-only legacy
  timestamp normalizer.
- `src/vibemix/runtime/drop_display.py:9` converts seconds to whole drop bars.
- `src/vibemix/runtime/ws_bus.py:697` builds a schema-valid session snapshot
  with `drop_pred_bars` and `claim_policy`.
- `tauri/ui/src/session/ws-bridge.ts:244` subscribes to `ipc.error`;
  `tauri/ui/src/session/ws-bridge.ts:249` subscribes to
  `ipc.session.citation`; `tauri/ui/src/session/ws-bridge.ts:528` applies mute
  acks.
- `tauri/ui/src/session/SessionLayout.ts:957` mounts `session.drop`;
  `tauri/ui/src/session/SessionLayout.ts:1257` renders the proof chip state.
- `tauri/ui/src/settings/SettingsDrawer.ts:1263` limits profile refresh to one
  per open cycle and `tauri/ui/src/settings/SettingsDrawer.ts:1278` mounts the
  diagnostics row.
- `tauri/ui/src/session/router.ts:104` starts the overlay-highlight listener and
  `tauri/ui/src/session/router.ts:158` tears it down.

## Verification

Schema and wiring:

```text
uv run python scripts/check_ipc_schema.py
OK: 72 dataclasses validate against schema
OK: count parity - 72 oneOf entries == 72 wrapper dataclasses
OK: SettingsSet field enum parity
OK: SettingsState payload parity

uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py
OK - every type has both a shell and a sidecar reference.
```

Python IPC/runtime tests:

```text
uv run pytest -q tests/ipc/test_library_schemas.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_mood_change_envelope.py
118 passed in 3.00s

uv run pytest -q tests/wizard/test_wizard_loop_ipc.py tests/runtime/test_session_loop.py tests/ui_bus/test_status_tick.py tests/runtime/test_ws_bus_snapshot.py
56 passed in 1.25s
```

Frontend tests:

```text
npm --prefix tauri/ui test -- src/settings/components/profile-panel.spec.ts src/settings/components/citation-diagnostics.spec.ts tests/settings/drawer.spec.ts tests/settings/staleness-banner.spec.ts tests/mock-transfer-contract.spec.ts
71 passed

npm --prefix tauri/ui test -- tests/session/components.spec.ts tests/session/render-loop.spec.ts tests/session/render-loop-actions.spec.ts tests/session/router-teardown.spec.ts tests/session/ws-bridge.recordings.spec.ts
75 passed
```

Codegen/build:

```text
npm --prefix tauri/ui run check:ipc
npm --prefix tauri/ui run build
```

Rust launch-decision smoke:

```text
cargo test --manifest-path tauri/src-tauri/Cargo.toml resolve_sidecar
5 passed; 111 filtered out
```

Lint/whitespace:

```text
uv run ruff check src/vibemix/ui_bus/messages.py src/vibemix/ui_bus/schemas/library.py src/vibemix/ui_bus/__init__.py src/vibemix/ui_bus/validator.py src/vibemix/runtime/drop_display.py src/vibemix/runtime/ws_bus.py src/vibemix/runtime/session_loop.py tests/runtime/test_session_loop.py tests/runtime/test_ws_bus_snapshot.py tests/wizard/test_wizard_loop_ipc.py tests/ipc/test_library_schemas.py tests/ui_bus/test_status_tick.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_mood_change_envelope.py tests/ui_bus/test_recordings_messages.py
All checks passed!

git diff --check -- <Package 2 files>
```

Live source-mode probe:

```text
VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix --session
-> wizard bus on ws://127.0.0.1:8765 (handlers: 12)

uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}' --watch ipc.status.tick --seconds 3
-> done (1 frames matched)
[0001] ipc.status.tick  livekit=connecting gemini=down midi=1 screen=ok

uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.profile.view --payload-json '{}' --watch ipc.profile.view_result --seconds 3
-> done (1 frames matched)
[0001] ipc.profile.view_result ...
```

After the probe, the launched source-mode session was stopped cleanly and
`vibemix_dev.sidecar_status` reported `ws_reachable=false`.

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This packet does not prove full Tauri GUI clicking. It proves schema parity,
  source-mode websocket handlers, and focused UI unit tests.
- Package 2 shares generated IPC files with Package 3. Do not stage
  `messages.schema.json`, generated TS, Python wrappers, and count/parity tests
  as separate partial hunks unless the split is re-verified.
- Debrief citation timeline/summary reservations remain out of this package.
- Library search/similar contract pruning belongs to Package 3 unless the two
  IPC packages are intentionally combined.

## Next Required Proof

Before product acceptance, run the packaged or source Tauri app and verify:

- clicking a down status input emits `ipc.status.recheck` and updates the badge,
- opening Settings emits one `ipc.profile.view` per open cycle,
- the Settings diagnostics row updates from `ipc.session.citation`, and
- the library staleness banner keeps one subscription across drawer refreshes.
