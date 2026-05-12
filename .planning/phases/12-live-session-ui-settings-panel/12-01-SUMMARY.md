---
phase: 12-live-session-ui-settings-panel
plan: 01
subsystem: ipc
tags: [tauri, ipc, schema, jsonschema, ajv, typescript, python, dataclass, session, settings]

# Dependency graph
requires:
  - phase: 11-tauri-shell-calibration-wizard
    provides: ipc.* JSON Schema baseline (19 messages) + dual-language validators + Python dataclasses + TS codegen pipeline + scripts/check_ipc_schema.py drift gate
provides:
  - JSON Schema extended to 26 ipc.* messages — adds session.snapshot (30Hz), session.mute (toggle/ack), settings.set/get/state, status.recheck, error
  - Python @dataclass(frozen=True, slots=True) wrappers + payload structs in src/vibemix/ui_bus/messages.py
  - AUTO-GENERATED tauri/ui/src/ipc/messages.ts committed alongside schema (regenerated via npm run codegen:ipc)
  - scripts/check_ipc_schema.py drift gate count-parity bumped 19 → 26
  - tests/ipc/test_session_messages.py — 26 focused Python tests (round-trip + boundary + invalid-payload)
  - tauri/ui/src/ipc/validator.spec.ts — +18 vitest cases (snapshot bounds, mute ack contract, settings field discriminator, status recheck names, error envelope shape)
affects:
  - 12-02 (SessionLoop + SettingsApplier — consumes the new ipc.* schemas at handler dispatch time)
  - 12-03 (presentation components — consume IpcSessionSnapshot shape for prop typing)
  - 12-04 (ws-bridge state writer — uses parseIpcMessage discriminated union to write SessionState)
  - 12-05 (Settings drawer — sends ipc.settings.set with discriminated `field` union)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Snapshot envelope at 30Hz (UX-08 / UX-11) — meters + phase + bpm + drop_pred_bars + transcript_delta + midi_events + track + cohost_status + latency_ms + grounded
    - Discriminated union on settings.set.field (voice|mode|genre|output_device|output_profile|retention|hotkey) for compile-time exhaustiveness
    - rms/peak constrained to [0, 1] at schema level (validator catches numeric drift before it reaches the renderer)
    - ipc.error envelope — sidecar can decline malformed requests without crashing the loop

# Outcome
status: completed
shipped:
  - tauri/ui/src/ipc/messages.schema.json (extended, +7 message families)
  - tauri/ui/src/ipc/messages.ts (regenerated)
  - tauri/ui/src/ipc/validator.spec.ts (+18 cases)
  - src/vibemix/ui_bus/messages.py (+6 wrappers + payload structs)
  - scripts/check_ipc_schema.py (count parity bumped to 26)
  - tests/ipc/test_session_messages.py (new — 26 tests)

tests:
  python: 68 / 68 pass (was 35 baseline; +33 new across tests/ipc/ + tests/ui_bus/)
  vitest: 31 / 31 pass (was 13 baseline; +18 new validator cases)
  drift_gate: green (26 == 26 wrapper-count parity, codegen output matches committed messages.ts)
  aiza_scan: 0 matches
  poc_files: untouched (0 lines diff)

# Deviations from plan
none — plan executed verbatim. Wave 1 was the contract layer; no surprises encountered.

# Handoffs
- 12-02 (Wave 2 — sidecar): SessionLoop subscribes to ws_bus, registers ipc.session.* + ipc.settings.* + ipc.status.recheck handlers; emits ipc.session.snapshot @30Hz built from MusicState. SettingsApplier dispatches by field discriminator.
- 12-03 (Wave 2 — components): IpcSessionSnapshot is the prop shape for the rAF-driven meter / phase-tape / cohost / event-ribbon presentation layer.
- 12-04 (Wave 3 — glue): parseIpcMessage discriminated union is the typed entry point for ws-bridge.ts → SessionState writes.

# Commits
- 5d6fec5 feat(12-01): wave 1 — IPC schema additions for session + settings
