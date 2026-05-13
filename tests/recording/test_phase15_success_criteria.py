# SPDX-License-Identifier: Apache-2.0
"""Phase 15 Plan 01 — ROADMAP success-criteria gates (audit + test).

This file is the TEST-side wedge for Phase 15's four ROADMAP success criteria.
It locks the surface-as-shipped against regression and documents the gaps that
Plans 15-02 / 15-03 / 15-04 will close.

NEVER edit ``recordings_index.py`` / ``config_store.py`` / ``__main__.py`` /
``runtime/settings.py`` to make these tests pass. They are read-only gates;
any failure here is either a regression (fix the source in a NEW plan) or a
real GAP (closure tracked in the table below — fix in 15-02/03/04).

----------------------------------------------------------------------
Audit Table — Phase 15 ROADMAP Success Criteria → Shipped Artifact → Status
----------------------------------------------------------------------

| # | ROADMAP success criterion | Shipped artifact (path:line) | Status   | Closure plan |
|---|---------------------------|------------------------------|----------|--------------|
| 1 | Settings → Recordings list — chronological roster of past sessions, reveal-in-Finder per row | `tauri/ui/src/settings/components/recording-browser.ts` (renderRecordingBrowser) + `recording-row.ts` (date + duration cells); newest-first sort enforced in `src/vibemix/runtime/recordings_index.py:296` (`summaries.sort(..., reverse=True)`) | PARTIAL | reveal-in-Finder icon → 15-04 |
| 2 | Per-row replay — voice.wav inline, input.wav opens in OS default app | inline `<audio controls>` for voice.wav via `convertFileSrc(asset://...)` in `recording-row.ts` (lazy-mount + collapse-teardown of decoder); native scrubber accent-color amber | PARTIAL | open-input.wav-externally icon → 15-04 |
| 3 | Delete with confirm pattern | SHIPPED via alternate pattern (impeccable Wave 5.A 2026-05-14): optimistic-remove + 4s undo toast in `recording-browser.ts` (~lines 332-360) replaces the modal confirm flow declared in CONTEXT.md. Locked by `recording-browser.spec.ts` Tests 6/7/8. The undo toast IS the confirm — see UI-SPEC §"Delete Flow" + §"Row delete (no modal)". | SHIPPED | n/a |
| 4 | Retention auto-prune 7d default + every 6h + events.jsonl logging | boot sweep at `src/vibemix/__main__.py:332` + session-close sweep at `src/vibemix/__main__.py:523` + settings-change sweep at `src/vibemix/runtime/settings.py:284-312`; default 7d declared in `config_store.ConfigStore.retention_days = 7` + retention-slider; ∞ sentinel short-circuit in `recordings_index.py:482-483` | PARTIAL | (a) periodic every-6h sweep loop → 15-02; (b) events.jsonl `retention_pruned` line → 15-02 |

----------------------------------------------------------------------
Gap Evidence (verbatim grep output, executed 2026-05-14)
----------------------------------------------------------------------

  $ grep -rn 'retention_pruned' src/vibemix/
  → no matches → GAP confirmed: retention_pruned events.jsonl line absent

  $ grep -rn '21600\\|hours=6\\|sweep_loop\\|sweep_task' src/vibemix/
  → no matches → GAP confirmed: periodic 6h sweep loop absent

  $ grep -rn 'reveal_in_os\\|open_external\\|recording.reveal' src/vibemix/ tauri/
  → no matches → GAP confirmed: reveal-in-OS / open-input.wav IPC absent

----------------------------------------------------------------------
Found Gaps → Closure Plan Pointers
----------------------------------------------------------------------

  * GAP A — periodic 6h sweep loop (`asyncio.create_task` w/ `await asyncio.sleep(21600)`) → addressed by **Plan 15-02**
  * GAP B — `events.jsonl` `{"event":"retention_pruned","count":N,"bytes":M,...}` log line → addressed by **Plan 15-02**
  * GAP C — reveal-in-OS sidecar IPC + UI icon → addressed by **Plan 15-03** (sidecar) and **Plan 15-04** (UI)
  * GAP D — open-input.wav-in-default-app sidecar IPC + UI icon → addressed by **Plan 15-04**

----------------------------------------------------------------------
Pre-existing Test Status (clean checkout, executed 2026-05-14)
----------------------------------------------------------------------

  $ pytest tests/recording/test_recordings_index.py tests/recording/test_retention_sweep.py tests/ui_bus/test_recordings_messages.py
  → 46 passed in 0.60s  (16 + 7 + 23 cases)

  $ npm run test -- --run \\
        src/settings/components/recording-browser.spec.ts \\
        src/settings/components/recording-row.spec.ts \\
        tests/session/ws-bridge.recordings.spec.ts
  → 34 tests passed (8 + 14 + 5 + extras)

Baseline is GREEN before any new test is added. The four pytest cases below
defend the SHIPPED columns of the audit table; the GAPS are tracked above for
closure in Plans 15-02 / 15-03 / 15-04.
"""

from __future__ import annotations
