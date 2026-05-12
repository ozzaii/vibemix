---
phase: 12
review_depth: standard
review_scope: wave-1-only
reviewer: autonomous-inline
reviewed_at: 2026-05-12
status: passed
---

# Phase 12 — Code Review

## Scope

Wave 1 (12-01) shipped files only. Waves 2-5 are deferred plans — no code yet, nothing to review.

Files reviewed:
- `tauri/ui/src/ipc/messages.schema.json` — 7 new top-level definitions + 1 helper (LevelPair)
- `tauri/ui/src/ipc/messages.ts` — codegen output (auto-generated)
- `tauri/ui/src/ipc/validator.spec.ts` — 18 new test cases
- `src/vibemix/ui_bus/messages.py` — 7 new wrapper dataclasses + 11 payload structs
- `src/vibemix/ui_bus/__init__.py` — re-exports
- `scripts/check_ipc_schema.py` — examples list extended
- `tests/ipc/test_session_messages.py` — NEW, 26 focused tests
- `tests/ui_bus/test_messages_schema.py` — count assertions updated

## Findings

### Critical: NONE

### Warning: NONE

### Info

**I-01 (Info, accepted) — `SettingsSet.payload.value` schema uses `anyOf [string, integer, null]`.**
The schema permits any string for any field (e.g. `voice="techno"` would pass schema even though techno isn't a voice). Defense-in-depth: the Python `SettingsApplier` (Wave 2) will validate `value` against per-field allowlists at runtime before applying. This is by design — schema enforces *transport* shape; runtime enforces *semantic* validity. Documented in `12-02-PLAN.md` truths.

**I-02 (Info, accepted) — `SessionMute.to_json()` overrides `_serialize`.**
Because the asymmetric `{toggle?, muted?}` payload requires None-field stripping at serialization, `SessionMute` overrides the shared `_serialize` helper rather than passing through. Pattern repeated for `IpcError.to_json()` to drop `original_type` when None. Acceptable — these are the only two wrappers with optional payload fields in v1; deferring to a helper macro would be premature abstraction.

**I-03 (Info, accepted) — `LevelPair` is a $ref helper rather than a top-level message.**
Bumps `definitions` count to 27 while `oneOf` stays at 26. Tests assert both counts explicitly (`test_schema_oneof_count_is_26`). Documented in `12-SUMMARY.md` decisions.

## Quality gates

| Gate | Result |
|------|--------|
| AIza key leak scan in modified files | ✓ clean (0 matches) |
| No-pydantic in `src/vibemix/ui_bus/` | ✓ clean (0 imports) |
| POC files untouched (cohost*, mascot.html, mocks/) | ✓ 0 lines diff vs Phase 11 close commit `7dbc742` |
| `npm run check:ipc` (codegen + tsc --noEmit) | ✓ pass |
| `npm run test` (vitest) | ✓ 31/31 pass |
| `python -m pytest tests/ipc/ tests/ui_bus/` | ✓ 68/68 pass |
| `python scripts/check_ipc_schema.py` (count parity + roundtrip) | ✓ green, 26 == 26 |
| Apache 2.0 SPDX headers on new Python files | ✓ present |
| All imports relative within `vibemix` package | ✓ confirmed |
| macOS + Windows parity (no Linux paths) | ✓ confirmed |

## Security posture

- All new IPC messages enforce `additionalProperties: false` on every payload object — drift caught by both ajv (TS) and jsonschema (Python) gates.
- All enum fields constrained (mode, output_profile, cohost_status, settings.set.field, status.recheck.component, ipc.error envelope) — no free-text spaces where an attacker could inject control values.
- No new shell-out, no new file-system writes, no new credential handling in Wave 1.
- `SessionMute` toggle does NOT carry a payload trigger source — sidecar trusts the WS bus boundary (already authenticated via 127.0.0.1 binding per Phase 11 W1).
- `tauri-plugin-global-shortcut` integration is Wave 4 deferred — no Rust capability changes in Wave 1.

## Anti-slop posture

- Zero hardcoded hex outside `tokens.css` — Wave 1 only touches schema + Python + tests; no UI code shipped yet.
- Wave 1 has no copy/microcopy — strings live in UI-SPEC.md and ship in Wave 3.
- Schema docstrings reference plan IDs (UX-06..11, D-Area-*) — traceability preserved.

## Recommendation

**Accept Wave 1 as shipped.** Code is contract-only, gated green on both sides, follows every Phase 11 convention (anti-pydantic, hand-written dataclasses, `additionalProperties: false`, separate ipc/ test dir). No fixes needed.

Defer code review of Waves 2-5 to their respective execute sessions.
