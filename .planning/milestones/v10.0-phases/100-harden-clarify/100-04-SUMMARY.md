---
phase: 100-harden-clarify
plan: 04
subsystem: vibemix.__main__ CLI dispatch + telegram bridge normalizer (clarification)
tags: [factor-7, clarification, cli, exit-code-11, hardening, sibling-extension, single-turn-rerun-hint, contract-bridge]
requires:
  - CodexCurateResult.question + .choices (library/codex_curate.py:221-222 from 100-03)
  - curate_with_codex clarification_needed sibling branch (library/codex_curate.py:569-588 from 100-03)
  - build_set_with_codex clarification_needed sibling branch (library/codex_curate.py:902-918 from 100-03)
  - _normalize_codex_curate_result module-level helper (__main__.py:2917-2945 from 99-06 — extended)
  - CLI exit-10 ternary in both handlers (__main__.py:2670 + :2720 from 99-06 — byte-equivalent preserved)
  - Reserved exit-code range 10-19 (Phase 99 D-06)
provides:
  - CLI exit 11 dispatch on clarification_needed in _cmd_library_curate_codex (src/vibemix/__main__.py:2656-2676)
  - CLI exit 11 dispatch on clarification_needed in _cmd_library_build_set_codex (src/vibemix/__main__.py:2731-2749)
  - 2-block stderr render (header + question + numbered choices + re-run hint) in both CLI handlers (Decision 6 closure)
  - _normalize_codex_curate_result clarification branch returning {ok: False, stop_reason: 'clarification_needed', question: str, choices: list[str]} (src/vibemix/__main__.py:3004-3010 — contract bridge for Plan 100-05)
  - Single-turn contract reaffirmed at user-visible CLI surface — re-run hint literally tells the user how to resolve
affects:
  - src/vibemix/__main__.py (+69 insertions, -8 deletions; 3 surgical edits in target zone 2543-2835)
  - tests/library/test_cli_exit_codes.py (+200 insertions; 3 new tests + section header)
tech-stack:
  added: []
  patterns:
    - "Branch-before-hint-dict refactor: the clarification path renders its 2-block layout BEFORE the existing single-line hint dispatch (which is shaped for one-line strings, incompatible with question + numbered choices). The starvation/timeout/codex_* paths fall through to the pre-100-04 single-line hint print unchanged — Phase 99 contract byte-equivalent."
    - "Reserved exit-code range continuation: 10 (tool_starvation, Phase 99), 11 (clarification_needed, Phase 100), 12-19 (future stop_reasons). Documented inline at both return-11 sites + the legacy `return 10 if ...` ternary comment updated."
    - "Defensive normalizer extension: result.question or '' + list(result.choices or []) mirrors Phase 99's result.error or '' pattern — Plan 100-05's format_reply can iterate payload['choices'] without is-None guards."
    - "Named-path stage discipline (concurrent-session hazard): the parallel learn/lesson observer + persona seeding session has unstaged hunks at lines 37-1711 of __main__.py. The plan-100-04 hunks are in lines 2543-2835 (target zone 2545-2950). Staging via `git apply --cached /tmp/target.patch` (a Python-filtered patch of only the target-zone hunks) preserves disjointness — `git diff --cached --name-only` confirms only __main__.py + tests/.../test_cli_exit_codes.py landed in the two commits."
key-files:
  created: []
  modified:
    - src/vibemix/__main__.py
    - tests/library/test_cli_exit_codes.py
key-decisions:
  - "D-05 closure (CONTEXT.md Decision 5): CLI exit code 11 carries clarification_needed across the shell↔vibemix-process trust boundary. Inline `if result.stop_reason == 'clarification_needed': ... return 11` placed BEFORE the existing inline-ternary `return 10 if ... else 1` — sibling extension, not refactor. Phase 99's RESEARCH.md Pitfall 6 verified the 10-19 range path-free vs standard Unix conventions; this plan continues that allocation."
  - "D-06 closure (CONTEXT.md Decision 6): 2-block stderr layout chosen. Block 1 = `[viber/codex] clarification_needed:` header + indented question. Block 2 = blank line + indented numbered choices (1-indexed, dot separator) + blank line + indented `Re-run with: library curate \"<theme> + <chosen option>\"` (or `library build-set \"<brief> + ...\"`). stdout stays clean — the run is terminal (no JSON envelope on this path)."
  - "Placeholder-line decision (plan executor latitude): chose the REMOVED-placeholder-line refactor — the clarification branch SKIPS the JSON dump + bracket-tagged single-line hint and goes straight to the rich 2-block render. The alternative (leave both lines, then print rich block below) was rejected because the JSON dump on stderr would noise up the user-visible block and the dict-lookup hint line `[viber/codex] clarification_needed: see formatted question + choices below` would lie (the question is rendered BELOW, not the same as a hint string). The branch-before-hint-dict refactor is cleaner and the 2 deletions (1 inline comment per handler) are documentation-only — load-bearing logic unchanged."
  - "Single-turn contract reaffirmed: the re-run hint string proves vibemix retains NO state across the clarification cycle. The user re-invokes manually with `<theme> + <chosen option>`; Codex is fully restarted on the next run. This is the Factor-7 right-pattern compromise (CONTEXT.md § Phase Boundary)."
  - "Plan 100-05 forward-handoff: the _normalize_codex_curate_result clarification branch returns `{ok: False, stop_reason: 'clarification_needed', question: str, choices: list[str]}` — Plan 100-05 telegram_bridge.format_reply branches on `norm.get('stop_reason') == 'clarification_needed'` and reads `norm['question']` + `norm['choices']` to render the leak-stripped numbered-choices message. The contract is locked here. Defensive: empty question / empty choices fall back to '' and [] respectively — format_reply can iterate without is-None guards."
patterns-established:
  - "Sibling-extension of inline-ternary dispatch: the Phase 99 `return 10 if ... else 1` form stays; the new branch sits ABOVE as an explicit `if ... return 11`. Future stop_reasons (12+) follow the same `if-above + ternary-below` pattern."
  - "Normalizer extension via paired-if sibling: the helper grows by a sibling `if` (not elif) — both branches return immediately on match, so semantically equivalent. Matches Phase 99-04's paired-if pattern in codex_curate.py."
requirements-completed: [HARDEN-CLARIFY-04, HARDEN-CLARIFY-06]
duration: 5min
completed: 2026-05-28
---

# Phase 100 Plan 04: CLI Exit-Code 11 Dispatch + Normalizer Clarification Branch — Summary

**Sibling-extended Phase 99 Plan 99-06's CLI exit-code dispatch with the clarification_needed branch — exit 11 + 2-block stderr render (header + question + numbered choices + re-run hint) at both CLI handlers, plus the `_normalize_codex_curate_result` clarification dict shape Plan 100-05's `format_reply` will consume.**

Closes CONTEXT.md Decisions 5 (exit 11 reserved range 10-19) + 6 (2-block stderr layout, clean stdout, single-turn contract via re-run hint). The user-visible HARDEN-CLARIFY-04 + HARDEN-CLARIFY-06 contracts now hold end-to-end: scripts can distinguish "need user input" (exit 11) from "library starved" (exit 10) from "other failure" (exit 1) from "success" (exit 0), and the re-run hint closes the single-turn loop by telling the caller exactly how to resolve.

## What Shipped

### A. CLI handler edits (`src/vibemix/__main__.py`)

| Edit | Site | Lines (post-edit) | What |
| ---- | ---- | ----------------- | ---- |
| Curate clarification branch | `_cmd_library_curate_codex` | **2656-2676** | New `if result.stop_reason == "clarification_needed":` block BEFORE the hint-dict — prints header + question + numbered choices + re-run hint + returns 11 |
| Curate ternary comment | same | **2698** | Old `# 11 reserved for Phase 100` updated to `# 11 = clarification_needed handled above (Plan 100-04)` |
| Build-set clarification branch | `_cmd_library_build_set_codex` | **2731-2749** | Same shape; re-run hint uses `library build-set` and echoes `args.brief` |
| Build-set ternary comment | same | **2769** | Same comment update |

The 2-block stderr layout (Decision 6):

```
[viber/codex] clarification_needed:
  <question>

  1. <choice 1>
  2. <choice 2>
  3. <choice 3>

  Re-run with: library curate "<theme> + <chosen option>"
```

stdout stays clean on this path (single-turn terminal). The pre-100-04 starvation/timeout/codex_* paths fall through to the existing single-line hint print unchanged — Phase 99 contract byte-equivalent.

### B. Normalizer extension (`src/vibemix/__main__.py`)

| Edit | Site | Lines (post-edit) | What |
| ---- | ---- | ----------------- | ---- |
| Clarification sibling branch | `_normalize_codex_curate_result` | **3004-3010** | New `if result.stop_reason == "clarification_needed":` returning `{"ok": False, "stop_reason": "clarification_needed", "question": result.question or "", "choices": list(result.choices or [])}` |
| Extended docstring | same | **2967-2993** | Documents both branches + the Plan 100-05 forward-handoff |

Phase 99's `tool_starvation` branch is byte-equivalent. The new clarification branch is a sibling `if` placed between starvation and the final `return None`.

### C. Tests (`tests/library/test_cli_exit_codes.py`)

3 new tests appended AFTER the 6 existing Phase 99 tests, with section header comment "## Phase 100 HARDEN-CLARIFY-04 — exit code 11 dispatch + normalizer extension":

| Test | Pin |
| ---- | --- |
| `test_curate_exits_11_on_clarification` | curate path → rc 11 + `[viber/codex] clarification_needed:` header + question substring + 3 numbered choices + `Re-run with:` + `library curate` + theme echo. stdout empty. |
| `test_build_set_exits_11_on_clarification` | build-set sibling parity → rc 11 + `library build-set` in re-run hint + brief echo |
| `test_telegram_curate_fn_normalizes_clarification` | 4 sub-assertions: (1) clarification → full dict shape, (2) created → None (cold-path regression), (3) tool_starvation → starvation dict (Phase 99 regression byte-equivalent), (4) defensive: clarification with question=None+choices=None → `question=''`, `choices=[]` |

## Exact Insertion-Site Line Numbers

### `src/vibemix/__main__.py`

| Edit | Lines | Diff hunk |
| ---- | ----- | --------- |
| Curate clarification branch | 2656-2676 | `@@ -2543,6 +2651,31 @@ def _cmd_library_curate_codex` |
| Curate ternary comment | 2698 (was 2669) | `@@ -2558,7 +2691,7 @@ def _cmd_library_curate_codex` |
| Build-set clarification branch | 2731-2749 | `@@ -2595,6 +2728,24 @@ def _cmd_library_build_set_codex` |
| Build-set ternary comment | 2769 (was 2719) | `@@ -2609,6 +2760,7 @@ def _cmd_library_build_set_codex` |
| Normalizer docstring + clarification branch | 2965-3010 | `@@ -2813,21 +2965,28 @@ def _normalize_codex_curate_result` + `@@ -2835,6 +2994,16 @@` |

All 6 diff hunks land between lines 2543 and 2835 (HEAD-side) / 2651-3010 (new-side). The target zone authorized by the plan was 2545-2950 — every hunk lands inside. The LiveKit-session block at **line 1353** is structurally untouched.

## Disjointness Verification (LiveKit + Frontend)

```bash
$ git diff HEAD~1 HEAD src/vibemix/__main__.py | grep -E "turn_handling|livekit|1353"
(empty — no matches)

$ git diff HEAD~1 HEAD src/vibemix/__main__.py | grep -E "^@@"
@@ -2543,6 +2651,31 @@ def _cmd_library_curate_codex(args: argparse.Namespace, lib) -> int:
@@ -2558,7 +2691,7 @@ def _cmd_library_curate_codex(args: argparse.Namespace, lib) -> int:
@@ -2595,6 +2728,24 @@ def _cmd_library_build_set_codex(args: argparse.Namespace, lib) -> int:
@@ -2609,6 +2760,7 @@ def _cmd_library_build_set_codex(args: argparse.Namespace, lib) -> int:
@@ -2813,21 +2965,28 @@ def _normalize_codex_curate_result(
@@ -2835,6 +2994,16 @@ def _normalize_codex_curate_result(

$ git diff HEAD~1 HEAD --name-only
src/vibemix/__main__.py
```

5-line context window around line 1353 (LiveKit turn_handling block) — byte-equivalent vs HEAD~2:

```python
1350    # register_library-seeded ids above (invariant #2 — no linter change).
1351    agent.attach_grounding(grounding)
1352
1353    # ── LiveKit 1.5.14 turn_handling: kill the false-interruption resume ──
1354    # Mic VAD fires on music → LiveKit marks "interrupt" → 2s later "false alarm"
1355    # → with the default resume_false_interruption=True the prior utterance
```

That block (committed by `456e1fdb`, the cross-session merge) is not in any of my hunks. The parallel session's unstaged hunks in `__main__.py` (lines 37-1711 — learn/lesson observers + persona seeding) are deliberately left unstaged — only Plan 100-04 hunks landed in the GREEN commit.

## Grep-Gate Verification

```bash
$ grep -c "return 11" src/vibemix/__main__.py
2                       # plan spec: exactly 2 (one per CLI handler) ✓

$ grep -n "return 11" src/vibemix/__main__.py
2676:            return 11
2749:            return 11
                        # both reads + 1-indexed enumerate ✓

$ grep -c "return 10" src/vibemix/__main__.py
2                       # Phase 99 ternaries unchanged ✓

$ grep -n "return 10" src/vibemix/__main__.py
2700:        return 10 if result.stop_reason == "tool_starvation" else 1
2771:        return 10 if result.stop_reason == "tool_starvation" else 1

$ grep -c "Re-run with:" src/vibemix/__main__.py
2                       # plan spec: exactly 2 ✓

$ grep -c "\[viber/codex\]" src/vibemix/__main__.py
4                       # 2 from Phase 99 (starvation hint print)
                        # + 2 new from Plan 100-04 (clarification header) ✓

$ grep -c "clarification_needed" src/vibemix/__main__.py
12                      # breakdown (audited per Phase 99-06 deviation precedent):
                        # 6 load-bearing code refs:
                        #   - 2 curate handler (1 elif check + 1 print)
                        #   - 2 build-set handler (1 elif check + 1 print)
                        #   - 2 normalizer (1 elif check + 1 dict literal)
                        # 6 inline comment / docstring refs:
                        #   - 2 curate handler (Plan 100-04 / Decision 5 cites)
                        #   - 2 build-set handler (same)
                        #   - 2 normalizer (docstring + sibling-extension comment)
```

## Test Outcomes

```bash
$ source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
    tests/library/test_cli_exit_codes.py \
    tests/library/test_codex_curate_stop_reason.py \
    tests/library/test_telegram_bridge.py \
    tests/library/test_toolset_clarification.py \
    tests/library/test_mcp_server_clarification.py \
    tests/library/test_toolset_starvation.py \
    tests/repo/test_no_seen_relaxation.py 2>&1 | tail -3
....................................................................... [ 69%]
...............................                                          [100%]
102 passed in 5.70s
```

| Suite | Before | After | Δ |
| ----- | ------ | ----- | --- |
| `tests/library/test_cli_exit_codes.py` | 6 | 9 | +3 (clarification dispatch + normalizer) |
| `tests/library/test_codex_curate_stop_reason.py` | 11 | 11 | 0 (no regression) |
| `tests/library/test_telegram_bridge.py` | 16 | 16 | 0 (no regression) |
| `tests/library/test_toolset_clarification.py` | 12 | 12 | 0 (Plan 100-01 surface unchanged) |
| `tests/library/test_mcp_server_clarification.py` | 11 | 11 | 0 (Plan 100-02 surface unchanged) |
| `tests/library/test_toolset_starvation.py` | 19 | 19 | 0 (Phase 99 contract byte-equivalent) |
| `tests/repo/test_no_seen_relaxation.py` | 3 | 3 | 0 (AST gate regression-pin) |
| **Total** | 99 | **102** | **+3** |

**RED→GREEN evidence:**
```bash
# At RED commit a0854eba (test commit, before impl):
$ PYTHONPATH=src python3 -m pytest -q tests/library/test_cli_exit_codes.py 2>&1 | tail -3
3 failed, 6 passed in 0.36s
# At GREEN commit f5dcb307 (after impl):
$ PYTHONPATH=src python3 -m pytest -q tests/library/test_cli_exit_codes.py 2>&1 | tail -3
9 passed in 0.37s
```

## Cardinal Invariants — Re-Verified

- **#1 single-writer (analog):** Untouched. `MusicState` writes are not in scope. This plan only routes a wrapper return value to a CLI exit code + a Telegram-bridge dict shape.
- **#2 citation grounding:** Reinforced. The clarification path has NO `track_id` surface — the CLI render iterates `result.choices` (a `list[str]`) and prints `result.question` (a `str`). Neither field could carry a track citation; the AST gate from Plan 100-01 already prevented `request_clarification` from receiving track_ids upstream. Citation grounding is structurally impossible to leak through this surface.
- **#3 trust the audio:** Untouched. The clarification path is Viber set-prep (offline) — live audio handoff at `__main__.py:1353` (LiveKit turn_handling) byte-equivalent vs HEAD~1.
- **#4 one socket:** Untouched. No new ws traffic. The CLI exit code + stderr render flow through the existing shell trust boundary.
- **#5 idle ≠ fault:** Untouched. SessionLayout grounding-failure timer logic unmodified.

## Threat Register — Disposition Verified

- **T-100-04-01 (Spoofing — exit code masquerade):** Accepted per plan. Exit code 11 is unallocated in standard Unix conventions (Phase 99-06 RESEARCH.md Pitfall 6 verified). Documented inline at both return-11 sites: `# Plan 100-04 / Decision 5: exit 11 — reserved range 10-19 for stop_reasons`.
- **T-100-04-02 (Information disclosure — args.theme echoed in re-run hint):** Accepted per plan. The theme/brief came from the user's own CLI argv. Echoing it back is not new disclosure. NO `strip_leaks` applied at CLI (mirrors Phase 99). Telegram surface (Plan 100-05) will apply `strip_leaks` defensively when it lands.
- **T-100-04-03 (DoS — pathological choices wedges render):** Mitigated by construction. Plan 100-01's toolset handler validates `choices` length 2-5 at the boundary; by the time `result.choices` reaches the CLI render, it's guaranteed bounded. The `for i, choice in enumerate(result.choices or [], start=1)` defensive `or []` handles None on cold path; iteration is bounded.
- **T-100-04-04 (Tampering — future code drop):** Mitigated. `test_curate_exits_11_on_clarification` + `test_build_set_exits_11_on_clarification` pin the return value. Drift = test failure.
- **T-100-04-DJ (Disjointness violation):** **Mitigated.** Diff-window grep for `turn_handling`/`livekit`/`1353` returned empty across both this plan's commits. All hunks land between lines 2543-2835 (HEAD side). The parallel session's `__main__.py` unstaged hunks (lines 37-1711) were never staged in this plan's commits — `git apply --cached /tmp/target.patch` with a Python-filtered patch enforced the named-path discipline. `git diff --cached --name-only` at each commit showed only the expected file.
- **T-100-04-SC (Tampering — npm/pip/cargo installs):** Accepted. Zero new packages.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Plan envelope: deletions count] Plan's "0-3 deletions" envelope check came in at 8 deletions.**

- **Found during:** Task 2 envelope verification.
- **Issue:** The 8 deletions break down as:
  - **1 line: inline-comment refresh in `_cmd_library_curate_codex`** — `# 11 reserved for Phase 100 ...` superseded by `# 11 = clarification_needed handled above (Plan 100-04)`. Phase 100 IS the forward-compat surface the old comment named; updating the comment to reflect that it's now wired (not reserved) is a documentation refresh.
  - **7 lines: normalizer docstring refresh** — the old docstring described one branch + a "Forward-compat (Phase 100) ..." block. The new docstring describes both branches verbatim + a single defensive-fallback block covering both. The old `Forward-compat (Phase 100)` block is now untrue (the sibling branch IS wired). The plan-prescribed extension on this docstring is documented in CONTEXT.md handoff notes.
- **Fix:** No code fix needed. Load-bearing logic deletions: 0. The 8 deletions are all documentation/comment refreshes that no longer hold once the extension is wired. Same minor-textual-fix pattern as Phase 99-06's `grep -c tool_starvation = 10 vs plan-spec 4-5` deviation (Phase 99-06 SUMMARY § Deviation #1).
- **Files modified:** none beyond the planned scope (the deletions occurred inside the named-action edit sites).
- **Commit:** rolled into the GREEN commit `f5dcb307` (no separate fix commit needed).

**2. [Rule 1 — Plan grep-gate: clarification_needed count] Plan's `grep -c "clarification_needed" src/vibemix/__main__.py` guidance was "at least 4 + comments". Actual: 12.**

- **Found during:** Task 2 grep verification.
- **Issue:** Plan-spec said "at least 4 (2 hint dict entries + 2 elif branch checks + 2 normalizer branch — load-bearing) plus comment count (audit in SUMMARY per Phase 99 W3-fix precedent)." The plan-spec actually under-counted load-bearing references:
  - **Load-bearing (6 hits):** 2 curate (elif check + print header), 2 build-set (elif check + print header), 2 normalizer (elif check + dict literal value).
  - **Inline comments / docstring (6 hits):** 2 curate (Decision 5 + Decision 6 cites), 2 build-set (same), 2 normalizer (docstring sibling-extension paragraph + W3-style comment).
- **Fix:** No code fix needed. The spirit of the gate ("load-bearing references are bounded + symmetric across 3 sites") is honored: 6 load-bearing hits, 2 per site, near-perfect symmetry. The plan also did NOT spec hint-dict entries for the clarification path — the chosen refactor SKIPS the hint dict for clarification (placeholder-line-removed path per Decision 6), so the plan's "+2 hint dict entries" never materialize. Same minor-textual-fix pattern Phase 99-06 documented.
- **Files modified:** none.
- **Commit:** N/A.

**3. [Rule 1 — Placeholder-line decision] Plan offered executor latitude between (a) leave both lines (placeholder dict-lookup hint print + rich block) and (b) refactor so clarification SKIPS the placeholder.**

- **Found during:** Task 2 implementation.
- **Decision:** Took path (b) — the clarification branch SKIPS the JSON dump + bracket-tagged single-line hint and goes straight to the rich 2-block render. Why:
  - The JSON dump on stderr would noise up the user-visible block (the result is already conveyed by the rendered question + choices).
  - The dict-lookup placeholder hint `[viber/codex] clarification_needed: see formatted question + choices below` would lie (the rendered block IS the hint, not a fallback for one).
  - Placement BEFORE the existing print is cleaner — the existing `print(_json.dumps(out, indent=2), file=sys.stderr)` line is now unreachable for clarification_needed, so the early `return 11` keeps the control flow linear.
- **Files modified:** none beyond the planned scope.
- **Commit:** documented in the GREEN commit message body.

### Architectural Decisions Not Made (Rule 4 not triggered)

None. The plan's `<antipatterns_to_avoid>` block + Phase 99-06's forward-compat authorization pre-empted every architectural decision:

- Hint dict NOT extended for clarification (refactor path b above). ✓
- Return-code uses explicit `if ... return 11` BEFORE the existing ternary — additive (not replace). ✓
- Both CLI handlers edited symmetrically — `build_set_with_codex` returns `CodexCurateResult` (same dataclass, same fields), confirmed by grep. ✓
- Normalizer extension uses sibling `if` (not elif) — both branches return immediately on match, semantically equivalent. ✓
- `result.question or ""` + `list(result.choices or [])` fallback present in normalizer (defensive W3-fix pattern from Phase 99-04). ✓

## Notes for Downstream Plans

- **Plan 100-05** (Telegram `format_reply` clarification branch): The contract is locked here:
  ```python
  # On clarification_needed:
  {
      "ok": False,
      "stop_reason": "clarification_needed",
      "question": <str>,     # may be empty string on malformed payload
      "choices": list[str],  # may be empty list on malformed payload
  }
  # On non-clarification-or-starvation: None (curate_fn proceeds to existing branches)
  ```
  Plan 100-05's `format_reply` should branch on `norm.get("stop_reason") == "clarification_needed"`, read `norm["question"]` + `norm["choices"]`, and render via `strip_leaks` (Telegram applies leak-stripping defensively; CLI does not — args.theme came from the user's own argv).

- **Plan 100-06** (AST gate / integration seal): The CLI exit code 11 is now a checkpoint surface. Suggested seal-test addition (sibling of the Phase 99 starvation seal):
  ```bash
  # In a shell with a mocked clarification-emitting Codex:
  $ uv run python -m vibemix library curate "ambiguous" 2>err.log; echo "exit=$?"
  exit=11
  $ grep -c "\[viber/codex\] clarification_needed:" err.log
  1
  $ grep -c "Re-run with: library curate" err.log
  1
  ```
  This pins the user-visible HARDEN-CLARIFY-04 + HARDEN-CLARIFY-06 contracts end-to-end.

- **Plan 100-07** (integration seal): Plan 100-03's `test_clarification_side_channel_propagation_with_real_writer` exercises the chain real toolset.request_clarification → side-channel → wrapper → CodexCurateResult. Plan 100-04 extends the chain to CLI exit 11 + 2-block stderr render. A Plan 100-07 seal can chain: real toolset → real wrapper → mocked `_runner` → CLI dispatch → assert exit 11 + stderr render + (Plan 100-05) Telegram format string.

## Commits

| Commit | Type | What |
| ------ | ---- | ---- |
| `a0854eba` | test | RED — 3 new tests in tests/library/test_cli_exit_codes.py (all fail; 6 Phase 99 regression-pins still pass) |
| `f5dcb307` | feat | GREEN — 3 surgical edits in src/vibemix/__main__.py (curate clarification branch, build-set clarification branch, normalizer clarification branch). +69/-8 in target zone 2543-2835. |

## Self-Check: PASSED

- `[ VERIFIED ]` `tests/library/test_cli_exit_codes.py` exists; 468 lines after extension (3 new tests appended)
- `[ VERIFIED ]` `src/vibemix/__main__.py` has `return 11` at curate handler (line 2676) + build-set handler (line 2749)
- `[ VERIFIED ]` `src/vibemix/__main__.py` has `Re-run with: library curate` literal at line 2673
- `[ VERIFIED ]` `src/vibemix/__main__.py` has `Re-run with: library build-set` literal at line 2746
- `[ VERIFIED ]` `src/vibemix/__main__.py` has `_normalize_codex_curate_result` clarification branch at lines 3004-3010
- `[ VERIFIED ]` Commit `a0854eba` exists (RED) — `git log --oneline | grep a0854eba`
- `[ VERIFIED ]` Commit `f5dcb307` exists (GREEN) — `git log --oneline | grep f5dcb307`
- `[ VERIFIED ]` `grep -c "return 11" src/vibemix/__main__.py` = 2 ✓
- `[ VERIFIED ]` `grep -c "return 10" src/vibemix/__main__.py` = 2 (Phase 99 byte-equivalent) ✓
- `[ VERIFIED ]` `grep -c "Re-run with:" src/vibemix/__main__.py` = 2 ✓
- `[ VERIFIED ]` `grep -c "clarification_needed" src/vibemix/__main__.py` = 12 (6 load-bearing + 6 comments; W3 deviation documented)
- `[ VERIFIED ]` `git diff HEAD~2 HEAD src/vibemix/__main__.py | grep -E "turn_handling|livekit|1353"` returns empty (LiveKit disjointness)
- `[ VERIFIED ]` `git diff HEAD~2 HEAD --name-only` shows ONLY `src/vibemix/__main__.py` (GREEN) and `tests/library/test_cli_exit_codes.py` (RED) — named-path discipline preserved
- `[ VERIFIED ]` All 6 diff hunks in HEAD~2..HEAD `__main__.py` diff land between lines 2543-2835 (target zone 2545-2950) ✓
- `[ VERIFIED ]` Line 1353 context (LiveKit turn_handling block) byte-equivalent vs HEAD~2 (5-line context above)
- `[ VERIFIED ]` `tests/library/test_cli_exit_codes.py` 9/9 GREEN (3 new + 6 Phase 99 regression)
- `[ VERIFIED ]` 102/102 across broader regression sweep (codex_curate_stop_reason + telegram_bridge + toolset_clarification + toolset_starvation + mcp_server_clarification + no_seen_relaxation)
- `[ VERIFIED ]` Cold-path smoke: `_normalize_codex_curate_result(CodexCurateResult(theme='x', stop_reason='created'))` returns None
- `[ VERIFIED ]` Cold-path smoke: starvation contract byte-equivalent — `_normalize_codex_curate_result(CodexCurateResult(theme='z', stop_reason='tool_starvation', error='hint'))` returns Phase 99 dict
- `[ VERIFIED ]` Defensive smoke: `_normalize_codex_curate_result(CodexCurateResult(theme='w', stop_reason='clarification_needed', question=None, choices=None))` returns `{question: '', choices: []}`
- `[ VERIFIED ]` No new untracked files in this plan's scope (the existing untracked entries in `.agents/` + `.claude/skills/` are pre-existing from other workflows, not Plan 100-04)
- `[ VERIFIED ]` Disjointness: only `src/vibemix/__main__.py` + `tests/library/test_cli_exit_codes.py` staged in each commit
