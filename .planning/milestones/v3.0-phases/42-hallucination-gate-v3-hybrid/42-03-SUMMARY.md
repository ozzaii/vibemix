---
phase: 42-hallucination-gate-v3-hybrid
plan: 03
subsystem: eval
tags: [eval, ear-test, debrief, gate-05, gate-07, kaan-action, ui, bash-gate]
requires:
  - Phase 29-05 (debrief window UI surface)
  - Phase 29-02 (debrief WS sidecar on 127.0.0.1:8766)
  - Phase 29-01 (vibemix.debrief.persistence atomic-write pattern)
  - Plan 42-01 §GATE-03 convention (KAAN-ACTION-LEGAL.md section anchor)
provides:
  - eval/EAR-TEST-PROTOCOL.md (30min / 14d / ≥2 genres / 4-slop-flag taxonomy)
  - eval/ear-test-logs/schema.json (draft-2020-12 JSON Schema for log entries)
  - src/vibemix/debrief/ear_test_capture.py (validator + atomic writer)
  - tauri/ui/src/debrief/components/ear-test-toggle.ts (mountEarTestToggle + EarTestSubmission)
  - scripts/release/check_ear_test.sh (release gate enforcing the 14d ≥2 sessions ≥2 genres 0-slop contract)
  - KAAN-ACTION-LEGAL.md §GATE-05 (Kaan-discharge runbook for first 2 ear-test sessions)
affects:
  - Plan 42-04 (check_gate.sh Gate-2 consumes check_ear_test.sh)
  - Plan 42-06 (eval/README.md cites this protocol; redacts log content)
  - Phase 29 debrief window layout (new ear-test toggle host inside debrief.html)
tech-stack:
  added: []
  patterns:
    - "Atomic temp+rename writer mirroring vibemix.debrief.persistence._atomic_write_bytes for the new ear-test capture surface"
    - "Schema validator with jsonschema.Draft202012Validator primary path + manual _validate_dict fallback (fails closed on either)"
    - "Bash release gate combining macOS BSD date (-v) and GNU date (-d) probe-and-branch — works on both maintainer machines and CI"
    - "Co-located JSON Schema next to the audit-trail JSON files (eval/ear-test-logs/schema.json) — bash globs skip schema.json by name"
    - "Tauri IPC primary + DebriefWsClient fallback for ear-test submit path (mirrors the citation-tooltip dispatch pattern)"
key-files:
  created:
    - eval/EAR-TEST-PROTOCOL.md
    - eval/ear-test-logs/.gitkeep
    - eval/ear-test-logs/schema.json
    - src/vibemix/debrief/ear_test_capture.py
    - tauri/ui/src/debrief/components/ear-test-toggle.ts
    - scripts/release/check_ear_test.sh
    - tests/debrief/test_ear_test_capture.py
    - tests/eval/test_ear_test_protocol_doc.py
    - tests/eval/test_check_ear_test_sh.py
  modified:
    - tauri/ui/src/debrief/debrief-window.ts
    - tauri/ui/src/debrief/ws-client.ts
    - tauri/ui/src/debrief/styles/debrief.css
    - tauri/ui/debrief.html
    - KAAN-ACTION-LEGAL.md
    - .planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md
decisions:
  - "Ear-test log files and the JSON Schema both live under eval/ear-test-logs/ — schema.json is co-located with the data it validates so the validator + bash gate import path stays adjacent. The bash gate explicitly skips schema.json when globbing *.json."
  - "Single-DJ regime locked at schema level (signed_by enum = [kaan] only). Cross-DJ sign-off is a v3.x deferral per Plan 42 CONTEXT; bumping to multi-DJ requires a schema bump + check_ear_test.sh update."
  - "30-min minimum (duration_s >= 1800) enforced at the JSON Schema level — the bash gate trusts the schema rather than re-checking, because gate-time the writer is already the only path that produces logs."
  - "Tauri IPC is the primary submission channel; the DebriefWsClient.sendEarTestSubmit fallback exists for dev mode (`npm run dev` without Tauri runtime). Mirrors the citation-tooltip dispatch split."
  - "Form-collapse-on-success + 'Signed off ✓' button copy chosen over the chapter-list-style 'mounted' pattern because the ear-test is one-shot per session — re-opening would invite re-signing and the writer's overwrite semantics would silently drop the original signature."
  - "Bash gate exits 1 (not 2) on every reject path including jq-missing — Plan 42-04's check_gate.sh treats any nonzero exit as 'Gate-2 not green', so distinguishing reasons by exit code adds no signal."
metrics:
  duration_min: ~14 (single agent, single-pass execution from worktree base sync to final commit)
  completed_date: 2026-05-16
  tasks_completed: 3
  files_created: 9
  files_modified: 6
  tests_added: 41
  tests_failing: 0
  tests_skipped_conditional: 1
---

# Phase 42 Plan 03: Hallucination Gate v3 Hybrid — Ear-Test Protocol + Capture + Gate Summary

GATE-05 (protocol) + GATE-07 (capture) closure. Codifies the **slow lane** of
the v3.0 hybrid hallucination gate — Kaan's ear, signed inside the existing
Phase 29 debrief window, gated by `check_ear_test.sh`. Plan 42-04's
`check_gate.sh` will AND-gate the 7-day autonomous-proxy result with the
output of this gate; Plan 42-06 will cite the protocol publicly while
redacting log content.

One-liner: ear-test protocol document + JSON Schema + Python capture writer
+ Phase 29 debrief toggle UI + bash release gate enforcing the 14-day /
≥ 2 sessions / ≥ 2 genres / zero-slop-flag contract.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1    | Protocol doc + JSON Schema + Python capture writer + writer tests | `e50cea9` | `eval/EAR-TEST-PROTOCOL.md`, `eval/ear-test-logs/{.gitkeep,schema.json}`, `src/vibemix/debrief/ear_test_capture.py`, `tests/debrief/test_ear_test_capture.py`, `tests/eval/test_ear_test_protocol_doc.py` |
| 2    | Debrief window ear-test toggle UI + wire-in | `a8c4fc2` | `tauri/ui/src/debrief/components/ear-test-toggle.ts`, `tauri/ui/src/debrief/debrief-window.ts`, `tauri/ui/src/debrief/ws-client.ts`, `tauri/ui/src/debrief/styles/debrief.css`, `tauri/ui/debrief.html`, `.planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md` |
| 3    | `check_ear_test.sh` + bash-gate tests + §GATE-05 runbook | `8bcc9cf` | `scripts/release/check_ear_test.sh`, `tests/eval/test_check_ear_test_sh.py`, `KAAN-ACTION-LEGAL.md` |

## Verification

All plan-level verification commands ran clean:

- `uv run pytest tests/debrief/test_ear_test_capture.py tests/eval/test_ear_test_protocol_doc.py tests/eval/test_check_ear_test_sh.py -q` → **40 passed, 1 skipped** (jq-missing simulation skips when jq is on minimal PATH — expected on macOS dev machines, will run on hermetic CI).
- `uv run python -c "import json, jsonschema; jsonschema.Draft202012Validator.check_schema(json.load(open('eval/ear-test-logs/schema.json')))"` → `schema valid` (draft-2020-12 valid).
- `bash scripts/release/check_ear_test.sh` (empty dir) → exit 1, message `FAIL check_ear_test: no ear-test logs found under eval/ear-test-logs (need ≥ 2)`. Matches the empty-dir contract.
- `uv run pytest tests/debrief/ -q` → **105 passed**. Phase 29 debrief test suite still green; no regression.
- `grep -q "mountEarTestToggle" tauri/ui/src/debrief/components/ear-test-toggle.ts && grep -q "mountEarTestToggle" tauri/ui/src/debrief/debrief-window.ts && grep -q "EarTestSubmission" tauri/ui/src/debrief/components/ear-test-toggle.ts && echo OK` → `OK`.
- `grep -q "^## §GATE-05 " KAAN-ACTION-LEGAL.md` → present.

## Success Criteria — Confirmed

- [x] `eval/EAR-TEST-PROTOCOL.md` documents 30 min / 14d / ≥ 2 genres / 4-slop-flag taxonomy. (`test_protocol_doc_*` × 8 pin each invariant)
- [x] `eval/ear-test-logs/schema.json` is a valid draft-2020-12 schema. (`test_schema_json_parses_as_valid_jsonschema`)
- [x] `src/vibemix/debrief/ear_test_capture.py` validates + atomic-writes. (`test_atomic_write_roundtrip`, `test_path_traversal_*`, full validator suite)
- [x] `tauri/ui/src/debrief/components/ear-test-toggle.ts` shipped + imported by `debrief-window.ts`. (grep verification passed)
- [x] `scripts/release/check_ear_test.sh` implements the ≥ 2-sessions ≥ 2-genres in 14d + zero-slop-flag contract. (`test_check_ear_test_sh.py` × 12 tests)
- [x] ≥ 20 new tests pass across 3 test files. (Actual: 41 tests added; 40 pass + 1 conditional skip — 2× the plan minimum.)
- [x] `KAAN-ACTION-LEGAL.md §GATE-05` runbook appended.
- [x] No regression on Phase 29 debrief tests. (105/105 green.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `check_ear_test.sh` initially blew up on co-located `schema.json`**
- **Found during:** Task 3 verification — running the gate against the real `eval/ear-test-logs/` dir (which contains `schema.json` plus the `.gitkeep`) tripped the catch-all "all logs failed to parse" error message instead of the cleaner "no ear-test logs found" message.
- **Issue:** The shell glob `${EAR_TEST_DIR}/*.json` picked up `schema.json` as if it were a log file; `jq` returned null for `signed_at`/`genre`/`slop_flags`, which then failed the parse loop.
- **Fix:** Replaced the bare `LOGS=( "${EAR_TEST_DIR}"/*.json )` glob with an explicit loop that skips `schema.json` by basename. The schema must stay co-located with the data so the writer + bash gate find it via a relative path; moving the schema to a sibling dir would have added a path-resolution branch to both.
- **Files modified:** `scripts/release/check_ear_test.sh`
- **Commit:** Folded into `8bcc9cf` (single Task 3 commit — fix was during Task 3 implementation, not a follow-up).

No other deviations. Plan executed as written across all 3 tasks.

## Deferred Issues

### Pre-existing / out-of-scope (logged in `deferred-items.md`)

- **TS typecheck unavailable in this worktree** — `tauri/ui/node_modules` is not installed locally (`.gitignore`'d). `npm run check:ipc` fails on missing `ajv` before `tsc --noEmit` can run. Plan smoke-verification was the grep check (passed); CI runs the full TS pipeline on PR. Added a new entry to `deferred-items.md` documenting the gap.

### Already deferred from Plan 42-01

- `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` — out-of-scope from Plan 42-01; closure path is the GATE-03 Kaan-discharge runbook (corpus acquisition). Plan 42-03 does not touch this.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-03-01 | Co-locate `schema.json` next to the log files (`eval/ear-test-logs/`) | Keeps writer + bash gate import paths trivially relative; the bash gate skips `schema.json` by basename so it does not pollute the log glob. |
| D-03-02 | Lock `signed_by` to `["kaan"]` enum at schema level | v3.0 is single-DJ per Plan 42 CONTEXT; cross-DJ sign-off requires both a schema bump and updated gate math — deferring this to v3.x keeps the v3.0 gate one-decision. |
| D-03-03 | 30-min minimum enforced at JSON Schema level (`duration_s >= 1800`) | The writer is the only path that produces logs, so trusting the schema rather than re-checking in the bash gate avoids contract drift between writer + gate. |
| D-03-04 | Bash gate exits `1` on every reject path including jq-missing | Plan 42-04's `check_gate.sh` will treat any nonzero exit as "Gate-2 not green" — distinguishing reasons by exit code would not be consumed by any downstream code. |
| D-03-05 | Tauri IPC primary submission + DebriefWsClient fallback | Mirrors the existing citation-tooltip dispatch split. Real desktop builds use IPC; `npm run dev` (no Tauri runtime) falls back to the existing 8766 WS channel. |
| D-03-06 | Form collapses + toggle disables permanently after first sign-off | Ear-test is one-shot per session; re-opening the form would invite re-signing and the writer's overwrite semantics would silently drop the original. The disabled toggle says "Signed off for release-gate ✓". |
| D-03-07 | CSS uses existing CDJ Whisper amber tokens (`--amber-1/2/3`) | Per `project_visual_direction_cdj_whisper` memory + the plan's "do NOT introduce new colors" directive. Tactility via amber border-tone shifts on hover/focus, not faux-3D bevels. |

## Authentication Gates

None hit during this plan. The capture surface is offline (atomic disk write); the bash gate is offline (filesystem + jq only); no Gemini API calls anywhere in the new code path.

## Known Stubs

None. Every UI element rendered is wired to a real data source (the session metadata flowing through `session-loaded` becomes the submission's `duration_s` + `genre`; the form inputs become the slop flags + free-form; the Tauri IPC / WS fallback is the live submission channel). The `EAR_TEST_LOG_DIR` constant is the only "configurable" surface and it has the correct production default.

## Threat Flags

No new threat surface beyond what the plan's `<threat_model>` already accounts for. The 6 STRIDE entries in PLAN.md (T-42-03-01 through T-42-03-06) are mitigated as planned:

| Threat ID | Mitigation realized |
|-----------|---------------------|
| T-42-03-01 | `write_ear_test_log` rejects path-traversal in `session_id` via the `_reject_path_traversal` helper + the schema regex `^[a-zA-Z0-9_-]{1,64}$`; pinned by `test_path_traversal_rejected` + `test_path_traversal_slash_rejected`. |
| T-42-03-02 | Privacy split documented in `eval/EAR-TEST-PROTOCOL.md` "Privacy" section; `eval/README.md` (Plan 42-06) will redact textual ear-test content while keeping the structured logs in repo as audit trail. |
| T-42-03-03 | JSON Schema `signed_by` enum locks the value to `["kaan"]`; pinned by `test_schema_locks_signed_by_to_kaan` + `test_payload_rejects_unknown_signer`. |
| T-42-03-04 | Schema `additionalProperties: false` at both top level AND inside `slop_flags`; pinned by `test_payload_rejects_extra_property` + `test_slop_flag_extra_keys_rejected` + `test_slop_flag_keys_required`. |
| T-42-03-05 | `check_ear_test.sh` reads JSON only via `jq` — no `eval`, no `source`, no `$()`-substitution of log contents into shell. `set -euo pipefail` at top. Pinned indirectly: the gate test suite uses payloads with quote-escape chars in `free_form` without observable misbehavior. |
| T-42-03-06 | Accept disposition unchanged — single-DJ regime relies on git history as the audit chain; not in scope for engineering mitigation. |

## Self-Check: PASSED

- `eval/EAR-TEST-PROTOCOL.md` — FOUND
- `eval/ear-test-logs/.gitkeep` — FOUND
- `eval/ear-test-logs/schema.json` — FOUND
- `src/vibemix/debrief/ear_test_capture.py` — FOUND
- `tauri/ui/src/debrief/components/ear-test-toggle.ts` — FOUND
- `scripts/release/check_ear_test.sh` — FOUND (`+x` mode)
- `tests/debrief/test_ear_test_capture.py` — FOUND
- `tests/eval/test_ear_test_protocol_doc.py` — FOUND
- `tests/eval/test_check_ear_test_sh.py` — FOUND
- Commit `e50cea9` — FOUND in git log
- Commit `a8c4fc2` — FOUND in git log
- Commit `8bcc9cf` — FOUND in git log
- §GATE-05 section — FOUND in `KAAN-ACTION-LEGAL.md`
- `mountEarTestToggle` symbol — FOUND in component + debrief-window.ts
- `EarTestSubmission` symbol — FOUND in component (+ type-re-export from debrief-window.ts)
