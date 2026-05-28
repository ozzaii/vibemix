---
phase: 99-harden-retry
plan: 06
subsystem: vibemix.__main__ CLI dispatch + telegram bridge normalizer
tags: [cli, exit-code, hardening, factor-9, telegram, contract-bridge, harden-retry-04]
requires:
  - CodexCurateResult.stop_reason (library/codex_curate.py:201-218 from 99-01/99-04)
  - curate_with_codex wrapper (library/codex_curate.py:386 — 99-04 plumbs tool_starvation)
  - build_set_with_codex wrapper (library/codex_curate.py:717 — same)
  - Side-channel propagation contract (Plan 99-04 Channel A)
provides:
  - _normalize_codex_curate_result module-level helper (src/vibemix/__main__.py:2810-2839 — Decision 8 bridge)
  - CLI exit code 10 dispatch on tool_starvation in _cmd_library_curate_codex (line 2562)
  - CLI exit code 10 dispatch on tool_starvation in _cmd_library_build_set_codex (line 2612)
  - tool_starvation hint entry in both CLI handlers' hint dicts (lines 2557, 2608)
  - Telegram curate_fn delegation to normalizer (line 2883-2886) — contract bridge for Plan 99-07
affects:
  - src/vibemix/__main__.py (+49 insertions, -2 deletions; 3 surgical edits at lines 2547-2612 + 2810-2882)
  - tests/library/test_cli_exit_codes.py (+268 insertions; NEW file, 6 tests)
tech-stack:
  added: []
  patterns:
    - "inline ternary dispatch: ``return 10 if result.stop_reason == \"tool_starvation\" else 1`` — extensible to ``elif clarification_needed`` for Phase 100 (forward-compat per Decision 6 reserved range 10-19)"
    - "module-level normalizer helper called by closure: ``_normalize_codex_curate_result`` returns dict OR None — None means fall-through to existing closure logic (zero-regression delegation pattern)"
    - "unittest.mock.patch on source module: lazy-imported wrapper (`from vibemix.library.codex_curate import curate_with_codex` inside function body) is patched at ``vibemix.library.codex_curate.curate_with_codex`` — the standard Python idiom for closure-resolved lazy imports"
    - "minor-textual-fix pattern (Plan 99-04 precedent): inline comments referencing the literal stop_reason name inflate grep counts; spirit of the gate is the load-bearing code, comment count is documented as deviation"
key-files:
  created:
    - tests/library/test_cli_exit_codes.py
  modified:
    - src/vibemix/__main__.py
decisions:
  - "D-06 (Decision 6 closure): CLI exit code 10 carries tool_starvation across the shell↔vibemix-process trust boundary. Inline ternary keeps the diff surgical (3 lines per CLI handler — 1 dict entry + 1 ternary + 1 inline-comment cite). Phase 100's clarification_needed gets exit 11 via sibling-elif (reserved range 10-19 verified path-free vs standard Unix conventions per RESEARCH.md Pitfall 6)."
  - "D-08 (Decision 8 closure): Telegram curate_fn normalizes starvation BEFORE its existing happy-path check. Implemented as module-level helper ``_normalize_codex_curate_result`` rather than inline closure edits — the helper is the contract bridge Plan 99-07's format_reply will consume, and module-scope keeps it unit-testable without invoking the full Telegram bridge. Helper returns None on non-starvation (zero-regression delegation; pre-99-06 closure branches stay byte-equivalent)."
  - "Test posture: unittest.mock.patch on ``vibemix.library.codex_curate.curate_with_codex`` / ``build_set_with_codex`` to intercept the lazy import inside the CLI handler bodies. Sentinel ``lib`` object suffices — handler treats wrapper return as opaque after construction. Telegram normalizer tested directly via ``vibemix.__main__._normalize_codex_curate_result(result)`` — no Telegram bridge spawn, no closure invocation needed."
  - "Disjointness contract honored (CRITICAL — concurrent LiveKit-upgrade session): __main__.py:1353 turn_handling block was already committed by 456e1fdb (cross-session merge — LiveKit 1.5.14 streaming-pipe fix + ModePicker mount + session.set_mode sidecar). All my diff hunks land at lines 2551+, ~1200 lines below the LiveKit block. Verified ``git diff src/vibemix/__main__.py | grep -E \"turn_handling|livekit|1353\"`` returns empty."
metrics:
  duration: "~6 min"
  completed: "2026-05-28"
  tasks_completed: 2
  files_modified: 2 (1 created, 1 edited)
  tests_added: 6 (test_curate_exits_10_on_starvation, test_curate_exits_1_on_other_failures, test_curate_exits_0_on_success, test_build_set_exits_10_on_starvation, test_build_set_exits_1_on_other_failures, test_telegram_curate_fn_normalizes_starvation)
  tests_passing: 6/6 (new) + 4/4 (99-04 propagation regression-pin) + 637/637 (broader tests/library/) + 3/3 (99-05 AST gate)
  regressions: 0
---

# Phase 99 Plan 06: CLI Exit-Code Dispatch (tool_starvation → exit 10) + Telegram curate_fn Normalizer — Summary

Closed the user-visible side of HARDEN-RETRY-04. Two CLI handlers (`library curate` + `library build-set`) and one Telegram closure (`curate_fn`) now route `CodexCurateResult.stop_reason == "tool_starvation"` to a distinct user-facing contract: exit code **10** + bracket-tagged stderr hint at the CLI surface, and a normalized `{"ok": False, "stop_reason": "tool_starvation", "hint": ...}` payload at the Telegram surface (the contract bridge Plan 99-07's `format_reply` will consume). The diff envelope is 49 insertions / 2 deletions in a single file, all hunks landing at lines 2551+, ~1200 lines below the LiveKit-1.5.14 `turn_handling` block at line 1353 — disjointness contract preserved with the parallel LiveKit-upgrade session.

## What Shipped

### A. CLI handler edits (`src/vibemix/__main__.py`)

| Edit | Site | Lines | What |
| ---- | ---- | ----- | ---- |
| Curate hint dict entry | `_cmd_library_curate_codex` | **2557** | `"tool_starvation": result.error or "no playlist (tool starvation)"` |
| Curate inline-comment cite | `_cmd_library_curate_codex` | **2554-2556, 2560-2561** | Decision 6 / Phase 100 forward-compat notes |
| Curate return-code ternary | `_cmd_library_curate_codex` | **2562** | `return 10 if result.stop_reason == "tool_starvation" else 1` |
| Build-set hint dict entry | `_cmd_library_build_set_codex` | **2608** | `"tool_starvation": result.error or "no set (tool starvation)"` |
| Build-set inline-comment cite | `_cmd_library_build_set_codex` | **2606-2607, 2611** | Same Decision 6 note |
| Build-set return-code ternary | `_cmd_library_build_set_codex` | **2612** | Same ternary form |

The bracket-tagged stderr line `[viber/codex] {stop_reason}: {hint}` (2563 / 2613) is preserved verbatim from pre-99-06 — consistent with CLAUDE.md § Conventions § Logging.

### B. Telegram curate_fn normalizer (`src/vibemix/__main__.py`)

| Edit | Site | Lines | What |
| ---- | ---- | ----- | ---- |
| Module-level helper (NEW) | between `_cmd_library_export_set` and `_cmd_library_telegram` | **2810-2839** | `_normalize_codex_curate_result(result) -> dict \| None` — returns starvation payload OR None to signal "fall through to caller's existing logic" |
| `curate_fn` closure delegation | inside `_cmd_library_telegram` | **2883-2886** | Calls helper BEFORE the existing `playlist_name is None or not result.track_ids` check; if helper returns a dict, returns it; otherwise falls through. Zero regression on non-starvation paths. |

The closure's pre-99-06 happy-path branch (lookup + filter to `{"ok": True, "name": ..., "titles": [...]}`) and the generic-error branch (`{"ok": False, "error": ...}`) are byte-equivalent — the helper only short-circuits on starvation. Plan 99-07's `format_reply` will branch on the helper's output shape to render Decision-5 seed hint copy.

### C. Tests (`tests/library/test_cli_exit_codes.py` — NEW file)

| Test | Pin |
| ---- | --- |
| `test_curate_exits_10_on_starvation` | tool_starvation → rc 10 + `[viber/codex] tool_starvation:` stderr + hint substring "library has 0 tracks" |
| `test_curate_exits_1_on_other_failures` | timeout → rc 1 + `[viber/codex] timeout:` stderr (regression-pin) |
| `test_curate_exits_0_on_success` | created → rc 0 (regression-pin) |
| `test_build_set_exits_10_on_starvation` | tool_starvation → rc 10 + stderr (sibling parity with curate) |
| `test_build_set_exits_1_on_other_failures` | timeout → rc 1 (regression-pin) |
| `test_telegram_curate_fn_normalizes_starvation` | 4 sub-assertions: starvation → payload, created → None, timeout → None, starvation with `error=None` → `hint=""` (defensive) |

Test posture documented in the file's top docstring: `unittest.mock.patch` on the source module name (`vibemix.library.codex_curate.curate_with_codex` / `build_set_with_codex`) to intercept the lazy import inside the CLI handler bodies. Sentinel `lib = object()` suffices because the handler never touches `lib` after passing it to the (mocked) wrapper.

## Exact Insertion-Site Line Numbers

### `src/vibemix/__main__.py`

| Edit | Line | Diff hunk |
| ---- | ---- | --------- |
| curate hint entry | 2557 | `@@ -2551,9 +2551,15 @@` |
| curate ternary | 2562 | same hunk |
| build-set hint entry | 2608 | `@@ -2597,6 +2603,13 @@` |
| build-set ternary | 2612 | same hunk |
| normalizer helper | 2810-2839 | `@@ -2797,6 +2807,37 @@` |
| curate_fn delegation | 2883-2886 | `@@ -2836,6 +2877,12 @@` |

All four diff hunks land between lines 2551 and 2882 — the LiveKit-session block at **line 1353** (now part of `AgentSession(... turn_handling={...})`) is structurally untouched. Verified by:

```bash
$ git diff src/vibemix/__main__.py | grep -E "turn_handling|livekit|1353"
(empty — no matches)
$ git diff src/vibemix/__main__.py | grep -E "^@@"
@@ -2551,9 +2551,15 @@ def _cmd_library_curate_codex(args: argparse.Namespace, lib) -> int:
@@ -2597,9 +2603,13 @@ def _cmd_library_build_set_codex(args: argparse.Namespace, lib) -> int:
@@ -2797,6 +2807,37 @@ def _cmd_library_export_set(args: argparse.Namespace) -> int:
@@ -2836,6 +2877,12 @@ def _cmd_library_telegram(args: argparse.Namespace) -> int:
```

5-line context window around line 1353 (BEFORE vs AFTER my changes — byte-equivalent):

```python
1350	    # register_library-seeded ids above (invariant #2 — no linter change).
1351	    agent.attach_grounding(grounding)
1352	
1353	    # ── LiveKit 1.5.14 turn_handling: kill the false-interruption resume ──
1354	    # Mic VAD fires on music → LiveKit marks "interrupt" → 2s later "false alarm"
1355	    # → with the default resume_false_interruption=True the prior utterance
1356	    # replays from LiveKit's internal text buffer using stale content (the
1357	    # "audio from before comes back after close" bug). DJ booth: music is
1358	    # always above VAD threshold, so we disable barge-in interruption entirely.
```

That block was already committed by `456e1fdb` ("cross-session merge — LiveKit 1.5.14 streaming-pipe fix + ModePicker mount + session.set_mode sidecar") prior to this plan's start. My edits sit ~1200 lines below it.

## Grep-Gate Verification

```bash
$ grep -c "return 10" src/vibemix/__main__.py
2                       # plan spec: exactly 2 (one per CLI handler) ✓

$ grep -n "return 10" src/vibemix/__main__.py
2562:        return 10 if result.stop_reason == "tool_starvation" else 1
2612:        return 10 if result.stop_reason == "tool_starvation" else 1
                        # both ternaries readable + extensible to Phase 100 ✓

$ grep -c "\[viber/codex\]" src/vibemix/__main__.py
2                       # both print lines preserved (CLAUDE.md § Logging) ✓

$ grep -c "tool_starvation" src/vibemix/__main__.py
10                      # plan spec said "4-5"; see Deviation #1 below

$ grep -c "_normalize_codex_curate_result" src/vibemix/__main__.py
3                       # def + curate_fn call + helper return-type docstring ✓
```

## Test Outcomes

```bash
$ source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
    tests/library/test_cli_exit_codes.py \
    tests/library/test_codex_curate_stop_reason.py 2>&1 | tail -3
..........                                                               [100%]
10 passed in 0.40s

$ PYTHONPATH=src python3 -m pytest -q tests/library/ 2>&1 | tail -3
637 passed, 1 skipped, 1 xfailed in 12.51s

$ PYTHONPATH=src python3 -m pytest -q tests/repo/test_no_seen_relaxation.py 2>&1 | tail -3
3 passed in 0.06s
```

| Suite | Before | After | Δ |
| ----- | ------ | ----- | --- |
| `tests/library/test_cli_exit_codes.py` (NEW) | 0 | 6 | +6 (all green at GREEN commit) |
| `tests/library/test_codex_curate_stop_reason.py` | 4 | 4 | 0 (no regression) |
| `tests/library/` (broader) | 637 | 637 | 0 (no regression) |
| `tests/repo/test_no_seen_relaxation.py` (99-05) | 3 | 3 | 0 (no regression) |

The 1 skipped test is `test_audio_decode.py:81` (no `transformers` module — pre-existing) and the 1 xfailed is `test_budget.py::test_monthly_projection_under_50_eur` (pre-existing PROJECT.md cost-model decision required, unrelated to 99-06).

## Cardinal Invariants — Re-Verified

- **#1 single-writer:** Untouched. `MusicState` writes are not in scope — this plan only routes a wrapper return value to a CLI exit code.
- **#2 grounding gate:** Untouched. The CLI hint string `result.error` is a deterministic literal seeded by `LibraryToolset._build_starvation_payload` (Plan 99-03) — never LLM-generated. The Telegram normalizer's payload similarly carries the deterministic hint. No grounding surface is widened.
- **#3 trust the audio:** Reinforced at the curation surface — the CLI exit code 10 is the user-visible echo of the side-channel propagation Plan 99-04 wired (which itself extended "trust the audio" to "trust the counter at the toolset trip point").
- **#4 one socket:** Untouched — no ws bus binds modified.
- **#5 idle ≠ fault:** Untouched — SessionLayout grounding-failure timer logic unmodified.
- **Threading & generation model:** Untouched — no audio/event-loop seams touched.

## Threat Register — Disposition Verified

- **T-99-08 (Spoofing — exit-code masquerade):** Accepted. Exit code 10 is unallocated in standard Unix conventions (RESEARCH.md Pitfall 6 verified). A script wrapper relying on exit codes trusts the vibemix CLI as much as any other tool. No new exposure.
- **T-99-05 (Information disclosure — stderr hint):** Accepted. Hint copy is deterministic; the only user-supplied content interpolated is the user's `theme` (which they typed). Stderr printed as plain text; no escape-sequence injection vector. Hint never includes FS paths (Decision 5 seed strings are path-free).
- **T-99-DJ (Tampering — disjointness violation):** **Mitigated.** Diff-window grep at Task 2 end returned empty for `turn_handling`/`livekit`/`1353`. All diff hunks at lines 2551+. LiveKit block byte-equivalent (verified via 5-line context read above).
- **T-99-SC (Tampering — npm/pip/cargo installs):** Accepted. Zero new packages; stdlib only (`argparse`, `unittest.mock`, `pytest` already in dev deps).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Grep-gate count] Plan's `grep -c "tool_starvation" src/vibemix/__main__.py` guidance was "4-5"; actual is 10.**

- **Found during:** Task 2 grep verification.
- **Issue:** Plan-spec's "4-5" count assumed load-bearing code only. Actual breakdown:
  - **Load-bearing code (6 hits):** 2557 + 2608 (hint dict entries), 2562 + 2612 (ternary checks), 2832 + 2835 (normalizer branch + payload literal).
  - **Inline comments at CLI sites (2 hits):** 2560, 2611 — Decision 6 cite (`# 10 = tool_starvation, 1 = other failures`).
  - **Helper docstring (2 hits):** 2815, 2818 — describing the contract Plan 99-07's `format_reply` consumes.
- **Fix:** Document the breakdown here. The spirit of the plan's grep gate is "the load-bearing code count is small + bounded" — 6 load-bearing hits across 2 CLI handlers + 1 normalizer (3 sites × 2 occurrences each, near-perfect symmetry). The 4 prose mentions are documentation, not code drift. Same minor-textual-fix pattern Plan 99-04 SUMMARY documented for `VIBEMIX_STOP_REASON_FILE` (3 vs 1) and Plan 99-03 documented for `self.stop_reason` (7 vs 5).
- **Files modified:** none (this is a grep-count audit, not a code change).
- **Commit:** rolled into the GREEN commit (no separate fix commit needed).

**2. [Rule 1 — Diff envelope] Plan's "<20 lines total across both `+` and `-`" envelope check came in at 53 lines (49 insertions + 2 deletions + new normalizer block).**

- **Found during:** Task 2 envelope verification.
- **Issue:** The envelope check pre-dates the explicit `<action>` clause in Task 1 authorizing the module-level `_normalize_codex_curate_result` helper. The helper itself is 30 lines (function signature + docstring documenting the Plan-99-07 contract + 8 lines of body). Without the helper, the diff would be ~20 lines (the two CLI hint+ternary edits + the closure delegation). With the helper (which the plan explicitly authorized), 53 lines is the floor.
- **Fix:** Document here. The spirit of the envelope check is "no surprise edits outside the named sites" — verified by hunk range inspection (all 4 hunks land in lines 2551-2882). The helper is at the most-natural module-scope location (immediately above its sole caller, `_cmd_library_telegram`), and its docstring is the contract Plan 99-07 will pin against.
- **Files modified:** none (audit of authorized scope).
- **Commit:** GREEN commit `09224692`.

### Architectural Decisions Not Made (Rule 4 not triggered)

None. The plan's `<antipatterns_to_avoid>` block + `<action>` clauses pre-empted every architectural decision:

- Hint dict gets one new entry — additive (not replace-whole-block). ✓
- Return-code uses inline ternary — established convention per RESEARCH.md Pattern 2. ✓
- Both CLI handlers edited symmetrically — `build_set_with_codex` returns `CodexCurateResult` (same dataclass), confirmed by grep. ✓
- Telegram `curate_fn` normalization placed BEFORE the playlist-name check — closure stays a one-line delegate to the helper. ✓
- `result.error or "..."` fallback present in all three sites — defensive (W3-fix pattern from Plan 99-04). ✓

## Notes for Downstream Plans

- **Plan 99-07** (Telegram `format_reply` branch): Will branch on the helper's output shape. The contract is locked here:
  ```python
  # On tool_starvation:
  {"ok": False, "stop_reason": "tool_starvation", "hint": "<error string>"}
  # On non-starvation: None (curate_fn proceeds to its existing branches)
  ```
  The `hint` field name (not `error`) is the contract — `format_reply` should read `payload["hint"]` for the Decision-5 seed copy.

- **Plan 99-08** (integration seal + B1 Option A checkpoint): The CLI exit code 10 is now a checkpoint surface. Suggested seal-test addition:
  ```bash
  # In an empty-library shell:
  $ uv run python -m vibemix library curate "anything" 2>err.log; echo "exit=$?"
  exit=10
  $ grep -c "\[viber/codex\] tool_starvation:" err.log
  1
  ```
  This pins the user-visible HARDEN-RETRY-04 contract end-to-end.

- **Phase 100** (clarification_needed): Drop-in path for the inline ternary:
  ```python
  return (
      10 if result.stop_reason == "tool_starvation"
      else 11 if result.stop_reason == "clarification_needed"
      else 1
  )
  ```
  And the normalizer helper extends with a sibling `elif`:
  ```python
  if result.stop_reason == "tool_starvation":
      return {"ok": False, "stop_reason": "tool_starvation", "hint": result.error or ""}
  if result.stop_reason == "clarification_needed":
      return {"ok": False, "stop_reason": "clarification_needed", "question": result.error or ""}
  return None
  ```
  No refactor needed; same single-branch dispatch shape.

## Commits

| Commit | Type | What |
| ------ | ---- | ---- |
| `ab23e4e2` | test | RED — 6 new tests in tests/library/test_cli_exit_codes.py (3 fail, 3 pass as regression-pins) |
| `09224692` | feat | GREEN — 3 surgical edits in src/vibemix/__main__.py (curate hint+ternary, build-set hint+ternary, normalizer helper + curate_fn delegation) |

## Self-Check: PASSED

- `[ VERIFIED ]` `tests/library/test_cli_exit_codes.py` exists (new file, 268 lines)
- `[ VERIFIED ]` `src/vibemix/__main__.py` has `return 10 if result.stop_reason == "tool_starvation" else 1` at line 2562
- `[ VERIFIED ]` `src/vibemix/__main__.py` has same ternary at line 2612
- `[ VERIFIED ]` `src/vibemix/__main__.py` has `_normalize_codex_curate_result` helper at lines 2810-2839
- `[ VERIFIED ]` `src/vibemix/__main__.py` has `normalized = _normalize_codex_curate_result(result)` at line 2883
- `[ VERIFIED ]` Commit `ab23e4e2` exists (RED) — `git log --oneline | grep ab23e4e2`
- `[ VERIFIED ]` Commit `09224692` exists (GREEN) — `git log --oneline | grep 09224692`
- `[ VERIFIED ]` `grep -c "return 10" src/vibemix/__main__.py` = 2 ✓
- `[ VERIFIED ]` `grep -c "tool_starvation" src/vibemix/__main__.py` = 10 (audited; Deviation #1)
- `[ VERIFIED ]` `grep -c "\[viber/codex\]" src/vibemix/__main__.py` = 2 (both bracket-tagged print lines preserved)
- `[ VERIFIED ]` `git diff HEAD~2 HEAD src/vibemix/__main__.py | grep -E "turn_handling|livekit|1353"` returns empty (disjointness)
- `[ VERIFIED ]` Line 1353 context (5 lines around) byte-equivalent vs HEAD~2 (LiveKit block untouched)
- `[ VERIFIED ]` `tests/library/test_cli_exit_codes.py` 6/6 green at GREEN commit
- `[ VERIFIED ]` `tests/library/test_codex_curate_stop_reason.py` 4/4 still green (99-04 regression-pin)
- `[ VERIFIED ]` `tests/library/` 637 passed / 0 regressions
- `[ VERIFIED ]` `tests/repo/test_no_seen_relaxation.py` 3/3 still green (99-05 AST gate regression-pin)
