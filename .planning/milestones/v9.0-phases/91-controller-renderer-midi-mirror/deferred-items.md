# Phase 91 — Deferred Items

Out-of-scope findings discovered during plan execution. **Not fixed in-plan** per
executor protocol §SCOPE BOUNDARY ("Only auto-fix issues DIRECTLY caused by the
current task's changes").

---

## Discovered during Plan 03 (Controller Renderer + MIDI Mirror — Python backend)

### 1. `tests/security/test_capability_snapshot.py` x2 failures — pre-existing from Plan 91-01

**Discovered:** 2026-05-28 during the wider regression sweep after Task 2.

**Failures:**
- `test_capability_snapshot.py::test_committed_snapshot_matches_current_default`
- `test_capability_snapshot.py::test_check_mode_passes_on_current_state`

**Root cause:** Plan 91-01 appended `"learn"` to the `windows` scope array in
`tauri/src-tauri/capabilities/default.json` (per Plan 01 SUMMARY §Files Modified)
but did NOT regenerate the committed
`tauri/src-tauri/capabilities/SNAPSHOT.json`. The `--check` mode of
`scripts/dist/snapshot_capabilities.py` detects the drift and fails red.

**Resolution:** Run `python scripts/dist/snapshot_capabilities.py --write` and
commit `SNAPSHOT.json` plus a `SECURITY_CAPABILITY_DELTA: added "learn" window
label for the Learn surface` note. Belongs in Plan 91-04 (Rust shell) which
already touches the Tauri capability surface, OR in a follow-up plan-01 fix-up
commit by whichever session owns the security-snapshot surface.

**Why not auto-fixed here:** Plan 03 touches neither
`tauri/src-tauri/capabilities/default.json` nor `SNAPSHOT.json`; regenerating
the security snapshot is outside this plan's named-files list and unrelated to
the MidiMirror backend. Logging here per executor §SCOPE BOUNDARY.

---

### 2. Other unrelated pre-existing failures in the wider suite

The 6 other regressions in the post-Task-2 wider run are all pre-existing and
unrelated to `src/vibemix/learn/`, `src/vibemix/runtime/ws_bus.py`, or
`src/vibemix/__main__.py`:

- `tests/audit/test_audit_md_generator.py::test_generator_is_idempotent`
- `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired`
- `tests/repo/test_phase20_docs.py::test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback`
- `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline`
- `tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_filter_test_submodules[vibemix-core.macos.spec]`
- `tests/sidecar/test_build_sidecar_rename.py::test_pyinstaller_specs_filter_test_submodules[vibemix-core.windows.spec]`

These belong to: documentation/meta-suites (audit/repo/scripts) and the sidecar
build chain (PyInstaller spec filtering). All untouched by Plan 03. They reflect
**concurrent-session work-in-flight** on the `live-tuning-or-brain` branch —
other sessions have uncommitted edits in `src/vibemix/agent/`,
`src/vibemix/intel/`, `src/vibemix/prompts/`, etc. (verified via `git status`
at Plan 03 start).

**Why not auto-fixed here:** Same reason — not in Plan 03's named-files list,
not caused by Plan 03's changes. The orphan-inventory and audit tests
specifically check for drift introduced by OTHER sessions' uncommitted work.
