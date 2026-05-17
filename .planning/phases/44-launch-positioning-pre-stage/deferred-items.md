# Deferred Items — Phase 44 Launch Positioning + Pre-stage

Out-of-scope discoveries surfaced during Phase 44 plan execution. Each
entry: where found + symptom + recommended owner-phase.

## Pre-existing test failures

### `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`

* **Found during:** 44-03 execution (broad agent-test run for regression
  baseline).
* **Symptom:** `SYSTEM_INSTRUCTION` in the package has drifted from
  `cohost_v4.py` `SYSTEM_INSTRUCTION` body (pkg=8358 chars, v4=8934 chars,
  body texts diverge from the first sentence).
* **Pre-existing:** confirmed by re-running on a clean stash (the test
  fails identically without any 44-03 changes touched).
* **Out-of-scope for 44-03:** the persona-port surface lives in Phase
  10/13/etc.; LAUNCH-02 only touches the broadcast emission path. A
  fix here would be either re-syncing the package SYSTEM_INSTRUCTION
  to v4 (canonical baseline per `project_v4_canonical_baseline`) or
  re-tuning v4 to match the current package — Kaan-decision.
* **Recommended:** open a focused `/gsd-quick` (or Phase 45 plan) to
  reconcile.

### `tauri/ui` pre-existing test failures

* **Found during:** 44-03 execution (broad `vitest run` for regression baseline).
* **Failing tests** (confirmed pre-existing via clean-stash repro):
  1. `src/ipc/validator.spec.ts > parseIpcMessage — ipc.recordings.delete_ack > accepts ok=false with string error` — `TypeError: func4 is not a function` (ajv compilation cache issue, unrelated to citation_strip).
  2. `tests/settings/drawer.spec.ts > Phase 15: recording browser wiring > list_result populates 2 row elements in the recording browser DOM` — 5s timeout.
  3. `tests/settings/drawer.spec.ts > Phase 15: recording browser wiring > list IPC timeout swaps the disk-usage line to UNAVAILABLE copy` — 5s timeout.
  4. 4× `tests/visual/*.spec.ts` — `Cannot find module '@playwright/test'` (Playwright dep not installed).
* **Out-of-scope for 44-03:** none of these touch the citation-strip
  / cohost-reaction surface. Recording-browser + Playwright visual
  harness are owned by earlier phases.
* **Recommended:** Playwright setup is a Phase 45 launch-readiness
  item; recording-browser timeouts are likely flaky-fixture issues
  worth a dedicated `/gsd-debug` pass.
