---
phase: 98-live-audit-ear-pass
plan: 02
subsystem: rc1 sidecar smoke regression
tags: [smoke, sidecar, rc1-regression, envelope-namespace, audit-04]
requirements: [AUDIT-04]
provides:
  - scripts/smoke/sidecar_bundle_smoke.sh (10-check rc1 regression smoke)
  - scripts/smoke/README.md (usage + exit code semantics)
requires: []
affects:
  - rc1 regression posture (future milestone close-outs re-run this)
  - v9.0 public-ship gate (one of the engineering deliverables for AUDIT-04)
key-files:
  created:
    - scripts/smoke/sidecar_bundle_smoke.sh
    - scripts/smoke/README.md
  modified: []
tech-stack:
  added: []
  patterns:
    - "Bash + macOS portable smoke: uses perl alarm() instead of GNU timeout (which is not on macOS by default)"
    - "Set -u (NOT -e): accumulates failures across all checks for one final report instead of bailing early"
    - "WARN vs FAIL distinction: pre-existing baseline drift is WARN; regression of rc1 fixes is FAIL"
    - "--only=<id> mode for iterating on a single check during dev"
decisions:
  - "10 sub-checks chosen to cover the 4 rc1 fixes + v9.0 additive surface: (1) pre-flight binary present + (2) livekit-agents patch + (3) mascot envelope namespace audit + (4) IPC schema parity + (5) --help boot + (6) --wizard --help boot + (7) --session --help boot + (8) spec _ANALYSIS_EXCLUDES blocklist + (9) sidecar.rs std::process pin + (10) learn.* envelope count"
  - "IPC schema check (sub-check 4) is WARN-not-FAIL on pre-existing baseline drift (78 schema oneOf vs 77 dataclass wrappers from sibling-session cross-merge 456e1fdb adding ipc.session.set_mode). NOT v9.0-caused; the validator itself stays clean (77 dataclasses validate). Per Plan 98-02 instructions: 'document the SCRIPT-VS-PRE-EXISTING-DRIFT distinction'."
  - "perl alarm() chosen over Python timeout-runner for the boot tests because perl is stdlib on macOS + Linux + Windows-with-Strawberry-Perl; Python startup cost would inflate the per-check time"
  - "Three separate --help boot checks (--help, --wizard --help, --session --help) instead of one combined check because each one exercises a different argparse code path and any one of them could regress if the livekit patch lapses (--help skips main runtime; --wizard initializes wizard; --session initializes session loop)"
  - "Spec blocklist check uses 5 representative needles (livekit.agents.cli, livekit.agents.jupyter, vibemix.bench, transformers, scipy) — not the full 67-entry list. The 5 are the highest-signal ones (any of them dropping triggers the rc1 circular import or balloons the bundle)."
metrics:
  duration_minutes: 35
  tasks_completed: 1
  files_created: 2
  files_modified: 0
  pytest_count_delta: 0
  vitest_count_delta: 0
  completed: 2026-05-28
---

# Phase 98 Plan 02: rc1 Sidecar Smoke Script Summary

Authored `scripts/smoke/sidecar_bundle_smoke.sh` + `scripts/smoke/README.md`. AUDIT-04 REQ-ID engineering-complete.

## Sub-check results on current tree

| # | Sub-check | Result | Notes |
|---|-----------|--------|-------|
| 1 | pre-flight (sidecar binary present) | PASS | `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/vibemix-core-aarch64-apple-darwin` exists, executable |
| 2 | livekit-patch (idempotent re-run) | PASS | Re-ran `scripts/dist/patch_livekit_agents_init.py`; patched both `__init__.py` + `agent_session.py` + purged stale .pyc cache; OK msg printed |
| 3 | mascot-envelope (P92 namespace audit) | PASS | `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts` 2/2 green via `npx vitest run`; all 13 `ipc.learn.*` envelopes drop silently via dispatcher's null-return; PHASE event still produces DispatchResult after 13-envelope volley |
| 4 | ipc-schema (ajv parity) | WARN | `python scripts/check_ipc_schema.py` exits 1 because 78 schema `oneOf` entries vs 77 dataclass wrappers — pre-existing baseline drift from sibling-session cross-merge (commit 456e1fdb) adding `ipc.session.set_mode` to schema without a Python dataclass mirror in `ui_bus/messages.py`. NOT v9.0-caused. Validator path itself stays clean ("OK: 77 dataclasses validate against schema"). Smoke flags as WARN, does not fail. |
| 5 | help-boot (`--help`) | PASS | Bundled `vibemix-core-aarch64-apple-darwin --help </dev/null` exits 0 in <2s; prints "usage: vibemix [-h] [--version] [--wizard] [--session] [--debrief [SESSION_DIR]] [--debug-log]" (22 lines of usage); proves livekit-agents patch holds under closed-stdin spawn |
| 6 | wizard-help (`--wizard --help`) | PASS | Boots cleanly; no ImportError in stderr |
| 7 | session-help (`--session --help`) | PASS | Boots cleanly; no ImportError in stderr |
| 8 | spec-blocklist (rc1 `_ANALYSIS_EXCLUDES`) | PASS | 5 representative needles present in `vibemix-core.macos.spec`: `livekit.agents.cli`, `livekit.agents.jupyter`, `vibemix.bench`, `transformers`, `scipy` |
| 9 | sidecar-std-process (rc1 spawn pin) | PASS | `tauri/src-tauri/src/sidecar.rs` contains `std::process::Command` (NOT `tokio::process` or `app.shell().command()`) |
| 10 | learn-envelopes (v9.0 namespace count) | PASS | `tauri/ui/src/ipc/messages.schema.json` contains 13 occurrences of `ipc.learn.` (one per envelope: `controller_detected`, `midi_position`, `start_course`, `start_lesson`, `complete_lesson`, `lesson_loaded`, `highlight`, `advance`, `ack`, `tutor_speak`, `exemplar_play`, `exemplar_stop`, `progress_state`) |

**Final report: 9 PASS / 0 FAIL / 1 WARN; exit 0.**

## Confirmation: rc1 fixes are intact post-v9.0

- **livekit-agents 1.x circular-import patch:** intact at `scripts/dist/patch_livekit_agents_init.py`; bundled binary re-runs the patch idempotently; both `livekit/agents/__init__.py` cli-explicit-first split and `livekit/agents/voice/agent_session.py` cli-lazy-import patch in place.
- **sidecar.rs `std::process::Command` spawn:** intact at `tauri/src-tauri/src/sidecar.rs:21` (`use std::process::{Command as StdCommand, Stdio};`) + module comment at line 85 documents why NOT `app.shell().command()`.
- **vibemix-core.macos.spec `_ANALYSIS_EXCLUDES` blocklist:** intact; the 5 highest-signal needles (`livekit.agents.cli`, `livekit.agents.jupyter`, `vibemix.bench`, `transformers`, `scipy`) all present.
- **Mascot envelope namespace audit (v9.0-specific):** intact at `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts`; passes 2/2 cases; all 13 v9.0 `ipc.learn.*` envelopes drop silently via the dispatcher's "unknown type, return null" path; known-good PHASE event still produces a DispatchResult after the 13-envelope volley.

## Deviations (1 — Rule 3, blocking)

**[Rule 3 - Blocking issue] IPC schema parity check exit code**

- **Found during:** Sub-check 4 (`ipc-schema`).
- **Issue:** `python scripts/check_ipc_schema.py` exits 1 because 78 schema `oneOf` entries vs 77 dataclass wrappers — pre-existing baseline drift from sibling-session cross-merge (commit 456e1fdb) adding `ipc.session.set_mode` to schema without a Python dataclass mirror in `ui_bus/messages.py`. Plan 98-02 explicitly anticipated this — instructed to "document the SCRIPT-VS-PRE-EXISTING-DRIFT distinction in the script comments and either skip the check or flag with `[smoke] WARN`."
- **Fix:** Re-wrote `check_ipc_schema()` smoke sub-check to (a) capture exit code + output separately, (b) if exit 1 AND the output contains the documented drift message AND the validator-OK message ("OK: 77 dataclasses validate"), flag WARN and return 0 (smoke pass); (c) otherwise propagate the real exit code (regression).
- **Files modified:** `scripts/smoke/sidecar_bundle_smoke.sh`
- **Commit:** `3acb50f6` (single commit; the WARN logic was part of the initial author + post-test refinement, all in one commit).

## Self-Check

- `scripts/smoke/sidecar_bundle_smoke.sh` — CREATED (357 lines including README)
- `scripts/smoke/README.md` — CREATED
- Script executable: `chmod +x` applied (mode 0755 verified)
- Final smoke run on current tree: `9 PASS / 0 FAIL / 1 WARN; exit 0`
- rc1 fixes verified intact: ✓
- v9.0 mascot envelope namespace audit verified: ✓

## Self-Check: PASSED
