---
phase: 100-harden-clarify
plan: 07
subsystem: library/codex_curate + library/toolset + __main__ CLI dispatch + library/telegram_bridge — integration seal
tags: [integration-seal, harden-clarify-07, factor-7, clarification, uniform-propagation, end-to-end-pin, kaan-action-surface, phase-100-close, anti-slop]
requires:
  - LibraryToolset._build_clarification_payload (library/toolset.py:1084-1124 from 100-01 — the discriminated-union sibling of Phase 99's _build_starvation_payload that the seal test invokes directly)
  - LibraryToolset.request_clarification + _write_side_channel reuse (library/toolset.py:1126-1245 + :1247 from 100-01 / 99-04 — toolset-side end of Channel A)
  - curate_with_codex clarification_needed elif branch (library/codex_curate.py:569-588 from 100-03 — wrapper-side end of Channel A)
  - build_set_with_codex clarification_needed elif branch (library/codex_curate.py:902-918 from 100-03 — set-prep wrapper parallel)
  - CodexCurateResult.question + .choices (library/codex_curate.py:221-222 from 100-03 — dataclass surface)
  - CLI exit-11 dispatch + 2-block stderr render (src/vibemix/__main__.py:2656-2676 + :2731-2749 from 100-04 — user-visible CLI surface)
  - _normalize_codex_curate_result clarification branch (src/vibemix/__main__.py:3001-3008 from 100-04 — Telegram contract bridge)
  - format_reply clarification branch (src/vibemix/library/telegram_bridge.py:137-143 from 100-05 — Telegram chat render)
  - tests/library/test_codex_curate_stop_reason.py at commit 24319125 (HEAD prior to this plan — 11 tests across Phase 99 + Phase 100-03 propagation; pin point for the additive seal extension)
provides:
  - test_clarification_full_chain_to_cli_curate (tests/library/test_codex_curate_stop_reason.py — HARDEN-CLARIFY-07 seal: REAL toolset payload → REAL wrapper → REAL CLI handler → exit 11 + 2-block stderr render)
  - test_clarification_full_chain_to_telegram (tests/library/test_codex_curate_stop_reason.py — HARDEN-CLARIFY-07 seal: REAL chain → REAL normalizer → REAL format_reply + leak-strip regression-pin)
  - test_clarification_build_set_path_seal (tests/library/test_codex_curate_stop_reason.py — HARDEN-CLARIFY-07 seal: build_set_with_codex sibling parity through the CLI surface; 'library build-set' command form pinned vs 'library curate')
  - Forward-compat verification documented inline at the top of the new seal block — future stop_reasons drop in by sibling-elif additions in six locations (handler / payload helper / wrapper elif / CLI elif / format_reply elif / normalizer if) with zero refactoring of existing code
  - §HARDEN-PHASE-B-CLARIFICATION-TONE KAAN-ACTION checkpoint surface (deferred per `gsd-autonomous fully` mode default — rides forward to v10.0 milestone close per `.planning/PROJECT.md` § v10.0 KAAN-ACTION queue)
affects:
  - tests/library/test_codex_curate_stop_reason.py (+310 insertions, 0 deletions — purely additive, single hunk at end-of-file)
  - Phase 100 close: 7/7 HARDEN-CLARIFY REQs are now closed + tested + sealed end-to-end across Plans 100-01..07
tech-stack:
  added: []
  patterns:
    - "Phase-99 seal-test posture clones VERBATIM for Phase 100 clarification (forward-compat verified): same `_runner_with_side_channel` helper + REAL `_build_clarification_payload` generator + REAL wrapper + REAL CLI handler / REAL format_reply. Codex CLI is the ONLY mocked boundary. The Phase-99 starvation seal (commit a8ac195f) and the Phase-100 clarification seal (this commit 991b7938) share the same scaffolding posture with only payload-generator name swap + asserted-substring swap. No test scaffolding was changed for clarification — this is the structural proof of forward-compat."
    - "Two-leg integration coverage (CLI + Telegram) inside a single test file: the seal tests reach into __main__._cmd_library_curate_codex / _cmd_library_build_set_codex via unittest.mock.patch on the SOURCE module attr (vibemix.library.codex_curate.curate_with_codex) — matches the patching pattern in tests/library/test_cli_exit_codes.py. Cross-file coupling kept minimal: the seal file imports only public surface (curate_with_codex / build_set_with_codex / CodexCurateResult / LibraryToolset) + the two test-only entry points (_cmd_library_curate_codex / _normalize_codex_curate_result / format_reply)."
    - "Leak-strip regression-pin at the integration boundary: the Telegram leg includes a malicious-shaped norm with an FS path in `question` → assert `/Users/ozai` is scrubbed → `[path]` marker present → non-path question text survives. This is the T-100-05-01 mitigation pin at the end-to-end seal layer — not just at the Plan 100-05 unit-test layer."
    - "Distinguishing-glyph latitude: the Telegram render test asserts `not rendered.startswith('⚠️')` rather than exact-glyph equality with ❓. Keeps room for §HARDEN-PHASE-B-CLARIFICATION-TONE ear-pass refinement (e.g. switching to 🤔, ❔, or a different intro convention) without test churn — only the distinguishability property is load-bearing."
    - "Disjointness via working-tree restore: the test file had pre-existing uncommitted edits from a parallel concurrent session (chat_with_codex tests + formatting collapses across many existing tests). My commit was kept clean by (a) saving the parallel session's working-tree state to a temp file, (b) `git checkout HEAD --` restoring the file, (c) re-applying ONLY my net-new seal block, (d) staging by named path, (e) committing, then (f) restoring the parallel session's saved state to the working tree. Net result: 1 hunk in my commit, 0 deletions, 310 insertions; parallel session's work-in-progress preserved untouched in the working tree for their own commit."
key-files:
  created:
    - .planning/phases/100-harden-clarify/100-07-SUMMARY.md
  modified:
    - tests/library/test_codex_curate_stop_reason.py
decisions:
  - "D-Plan-100-07-01 (Forward-compat verification posture): the seal tests prove forward-compat structurally by REUSING the Phase-99 `_runner_with_side_channel` helper byte-equivalent, just swapping the payload generator from `_build_starvation_payload` to `_build_clarification_payload`. No new test infrastructure was needed — proof-by-construction that the discriminated-union pattern locked in Phases 99 + 100 scales to N+1 stop_reasons by sibling additions only."
  - "D-Plan-100-07-02 (Test surface boundaries): the seal stops at the CLI rc + stderr substrings and the format_reply render string — it does NOT exercise the actual Codex MCP child subprocess boundary, the Telegram bot long-poll loop, or the Tauri bridge. Each of those boundaries has its own dedicated test surface (test_mcp_server_clarification.py / test_telegram_bridge.py / future Tauri tests). The seal is the *vibemix-internal* propagation pin; the external boundaries (Codex CLI binary, Telegram API, OS Tauri) stay in unit tests for their narrow surfaces."
  - "D-Plan-100-07-03 (§HARDEN-PHASE-B-CLARIFICATION-TONE verdict): DEFERRED TO v10.0 MILESTONE CLOSE per `gsd-autonomous fully` mode default + `gate=\"non-blocking\"` posture. Three sample question framings (BPM range / context / mood register) are surfaced inline below for Kaan's ear-pass on a funded Codex key. The verdict matrix offers PASS / REVISE / DEFER / REPLACE — DEFER is the auto-selected default; the item rides forward to milestone close alongside the Phase 99 §HARDEN-PHASE-A-EAR-PASS + §HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY items in the same KAAN-ACTION queue."
  - "D-Plan-100-07-04 (Working-tree discipline against parallel session): the test file had ~13 unrelated uncommitted hunks (chat_with_codex import + 2 new chat tests + formatting collapses across 11 existing tests) from a sibling executor session. I (a) saved the parallel session's working tree to /tmp/working-tree-saved.py, (b) restored HEAD with `git checkout HEAD -- ...`, (c) re-applied ONLY my single net-new block, (d) staged + committed, (e) restored the parallel session's saved state. My commit landed as one hunk / 310 insertions / 0 deletions; the parallel session's work-in-progress remains uncommitted in the working tree for their own commit. NO `git add -A`, NO `git stash`, NO `git restore .` — only HEAD-then-overlay-then-restore. Matches the CLAUDE.md concurrent-session discipline."
  - "D-Plan-100-07-05 (Phase 100 close handoff): with this plan's 3 seal tests landing, Phase 100 has 7/7 REQs shipped + tested + integration-sealed end-to-end. Cardinal-invariant gates pinned across Phases 99 + 100: (#1) single-writer analog via STOP_REASON_WHITELIST; (#2) citation grounding via Plan 99-05 AST gate + Plan 100-06 AST gate; (#3) trust-the-audio extended to the curation surface via deterministic generators; (#4) one-socket N/A for CLI/MCP/Telegram only. Phase 100 is ready for `/gsd:verify-work 100`."
metrics:
  duration: "~25 min"
  completed: "2026-05-28"
  tasks_completed: 1
  files_modified: 1 (tests/library/test_codex_curate_stop_reason.py)
  tests_added: 3 (test_clarification_full_chain_to_cli_curate, test_clarification_full_chain_to_telegram, test_clarification_build_set_path_seal)
  tests_passing: "14/14 on test_codex_curate_stop_reason.py (HEAD-clean: 11 prior + 3 new seal) + 16/16 with parallel session's chat tests applied + 115/115 on Plan 100-07 verify chain + 706 passed / 1 skipped / 1 xfailed on tests/library/ (zero regressions; the skip + xfail are pre-existing unrelated)"
  regressions: 0
requirements_completed: [HARDEN-CLARIFY-07]
---

# Phase 100 Plan 07: End-to-End Integration Seal + §HARDEN-PHASE-B-CLARIFICATION-TONE Checkpoint — Summary

Closed the Phase 100 integration seal end-to-end. Three new tests in `tests/library/test_codex_curate_stop_reason.py` extend the existing Plan 100-03 wrapper-level propagation tests to the USER-VISIBLE surfaces — the CLI exit code 11 + 2-block stderr render (Plan 100-04) and the Telegram `format_reply` chat render (Plan 100-05). Each seal test exercises the FULL Factor-7 clarification chain — REAL `_build_clarification_payload` generator (Plan 100-01) → REAL side-channel write through `_write_side_channel` (Plan 99-04 reused) → REAL `curate_with_codex` / `build_set_with_codex` elif branch (Plan 100-03) → REAL `_cmd_library_*_codex` dispatch / REAL `_normalize_codex_curate_result` + REAL `format_reply` — with Codex CLI as the ONLY mocked boundary (same `_runner_with_side_channel` posture as Phase 99 Plan 99-08's seal).

The §HARDEN-PHASE-B-CLARIFICATION-TONE KAAN-ACTION checkpoint is surfaced inline below with three sample question framings + a four-option verdict matrix. Per `gsd-autonomous fully` mode default, the verdict is DEFER — the item rides forward to v10.0 milestone close alongside the existing Phase 99 KAAN-ACTION queue items.

Phase 100 is engineering-complete: 7/7 HARDEN-CLARIFY REQ-IDs shipped + tested + integration-sealed.

## What Shipped

### A. Integration-seal tests (`tests/library/test_codex_curate_stop_reason.py`)

Three new tests appended after the existing Phase 100-03 propagation block, under a new section header `## Phase 100 HARDEN-CLARIFY-07 — integration seal (end-to-end uniform propagation)`. Net diff: **+310 insertions, 0 deletions, single hunk** (purely additive — no existing test touched).

| Test | What it pins |
| ---- | ----------- |
| `test_clarification_full_chain_to_cli_curate` | REAL `_build_clarification_payload` (zero-track library, question="What BPM range?", choices=["slow (90-110)", "fast (130-140)", "mixed"]) → side-channel → REAL `curate_with_codex` short-circuit → REAL `_cmd_library_curate_codex` via `unittest.mock.patch("vibemix.library.codex_curate.curate_with_codex", return_value=result)`. Asserts: `rc == 11`; stderr contains `clarification_needed` discriminator, question substring, all 3 choice substrings, `Re-run with:`, `library curate`; stdout stays empty (Decision 6). |
| `test_clarification_full_chain_to_telegram` | Same REAL chain (toolset → wrapper) → REAL `_normalize_codex_curate_result` → REAL `format_reply`. Asserts: norm dict matches `{ok: False, stop_reason: "clarification_needed", question, choices}` exactly; rendered string is non-empty, contains question + all 3 choices, does NOT start with ⚠️ (distinguishability from error branches — the exact ❓ glyph stays executor-latitude for §HARDEN-PHASE-B ear-pass). Includes a leak-strip regression-pin: malicious-shaped `question="Library at /Users/ozai/.cache/vibemix — pick context?"` → assert `/Users/ozai` not in output, `[path]` marker present, `pick context?` survives. T-100-05-01 mitigation pinned at the integration boundary. |
| `test_clarification_build_set_path_seal` | REAL chain via `build_set_with_codex` (5-track library, question="Which energy curve?", choices=["slow-build", "peak-time", "wave"]) → REAL `_cmd_library_build_set_codex` via `unittest.mock.patch("vibemix.library.codex_curate.build_set_with_codex", return_value=result)`. Asserts: `rc == 11`; stderr contains `clarification_needed`, question, all 3 choices, `Re-run with:`, `library build-set` (NOT `library curate`); brief `"peak-time 60 min"` echoed in re-run hint; stdout empty. Proves uniform propagation across BOTH wrappers + BOTH CLI handlers. |

### B. Test-helper reuse (no new helpers)

The seal tests reuse:
- `_empty_library()` (zero-track `RekordboxLibrary` fixture-style helper from Plan 99-08 seal)
- `_make_real_clarification_payload(library, question, choices)` (REAL toolset generator from Plan 100-03 propagation tests — line 586)
- `_runner_with_side_channel(...)` (fake `subprocess.run` from Plan 99-04 — writes side-channel JSON at the wrapper-allocated env-var path; same posture used by every Phase 99 + Phase 100 propagation test in this file)
- `_RekordboxLibrary`, `_LibraryToolset`, `_MagicMock` (existing seal-block imports)

NEW imports only: `unittest.mock.patch as _patch` (line 884 inside the new seal block, aliased to avoid colliding with the top-of-file `patch` that's already imported elsewhere in the test suite) + function-local `argparse` + `vibemix.__main__ as _main` + `_normalize_codex_curate_result` + `format_reply`. All test-only — the seal is the only consumer.

### C. Forward-compat verification (documented inline at the top of the new seal block)

The block-opening comment in the test file explicitly states:

> Forward-compat: future stop_reasons (12 = user_canceled, 13 = ..., ...) drop in by sibling-elif additions in (a) toolset handler (b) `_build_<reason>_payload` (c) wrapper elif (d) CLI elif (e) `format_reply` elif (f) normalizer if. No refactoring of existing code — discriminated-union pattern locked across Phases 99 + 100.

Structural proof: the Phase-99 starvation seal at commit `a8ac195f` and the Phase-100 clarification seal at commit `991b7938` share the same scaffolding posture (`_runner_with_side_channel` helper, real-generator invocation pattern, fake-runner injection seam). The ONLY differences between the two are (a) which `_build_<reason>_payload` is called and (b) which asserted substrings live in the test body. No test infrastructure was changed for clarification — that proves N+1 stop_reasons can be added by sibling tests with the same posture.

## REQ Coverage Matrix (7/7 Closed Across Plans 100-01..07)

| REQ-ID | Closure plan(s) | What pins it | Test files |
| ------ | --------------- | ------------ | ---------- |
| **HARDEN-CLARIFY-01** | 100-01 | `request_clarification` handler + `MIN_CHOICES=2` + `MAX_CHOICES=5` + dispatch entry @ `src/vibemix/library/toolset.py:83-84` + `:1084-1245` + `:1333` | `tests/library/test_toolset_clarification.py` (34 tests) |
| **HARDEN-CLARIFY-02** | 100-02 | MCP FastMCP `@mcp.tool()` exposure + teaching docstring @ `src/vibemix/library/mcp_server.py` | `tests/library/test_mcp_server_clarification.py` (11 tests) |
| **HARDEN-CLARIFY-03** | 100-03 | `CodexCurateResult.question` + `.choices` fields + `curate_with_codex` / `build_set_with_codex` clarification_needed elif branches @ `src/vibemix/library/codex_curate.py:221-222` + `:569-588` + `:902-918` | `tests/library/test_codex_curate_stop_reason.py` (Phase 100-03 block — propagation + shape pin) |
| **HARDEN-CLARIFY-04** | 100-04 | CLI exit code 11 + 2-block stderr render in both handlers @ `src/vibemix/__main__.py:2656-2676` + `:2731-2749` + `_normalize_codex_curate_result` clarification branch @ `:3001-3008` | `tests/library/test_cli_exit_codes.py` (Phase 100-04 block — 3 tests) |
| **HARDEN-CLARIFY-05** | 100-05 | `format_reply` clarification_needed branch + numbered choices + `strip_leaks` defense @ `src/vibemix/library/telegram_bridge.py:137-143` | `tests/library/test_telegram_bridge.py` (Phase 100-05 block — 2 new + 1 extended regression-pin) |
| **HARDEN-CLARIFY-06** | 100-04 + 100-06 | Single-turn re-run hint (100-04 — `Re-run with: library curate \"<theme> + <chosen option>\"`) + AST gate single-trip (100-06) | `tests/library/test_cli_exit_codes.py` + `tests/library/test_request_clarification_no_track_surface.py` |
| **HARDEN-CLARIFY-07** | 100-03 + 100-06 + **100-07** | Test coverage propagation (100-03 wrapper-level) + AST gate (100-06 structural) + integration seal (100-07 end-to-end at CLI + Telegram surfaces) — **THIS PLAN** | `tests/library/test_codex_curate_stop_reason.py` (Phase 100-07 seal block — 3 new tests) |

**All 7 REQs CLOSED.** Plan-checker can verify by grepping for each REQ-ID across the SUMMARY artifacts at `.planning/phases/100-harden-clarify/100-NN-SUMMARY.md`.

## Forward-Compat Verification

Demonstration that adding a new `stop_reason` (e.g. `stop_reason="user_canceled"` in some future phase) requires ONLY sibling additions — zero refactoring of existing code:

| Layer | File | New code | Existing code touched? |
| ----- | ---- | -------- | ---------------------- |
| (a) Handler | `src/vibemix/library/toolset.py` | New `def cancel_run(self, args)` method — sibling of `request_clarification` | NO |
| (b) Payload helper | `src/vibemix/library/toolset.py` | New `def _build_canceled_payload(self, reason: str) -> dict` returning `{"reason": "user_canceled", ...}` — sibling of `_build_clarification_payload` | NO |
| (c) Wrapper elif | `src/vibemix/library/codex_curate.py` (both `curate_with_codex` and `build_set_with_codex`) | New `elif payload.get("reason") == "user_canceled":` — sibling of the clarification elif | NO |
| (d) CLI elif | `src/vibemix/__main__.py` (both `_cmd_library_curate_codex` and `_cmd_library_build_set_codex`) | New `if result.stop_reason == "user_canceled": ... return 12` — sibling of the exit-11 if-block, exit code 12 in the reserved 10-19 range | NO |
| (e) `format_reply` elif | `src/vibemix/library/telegram_bridge.py` | New `if norm.get("stop_reason") == "user_canceled":` — sibling of the clarification branch, BEFORE the generic `if not norm.get("ok")` block | NO |
| (f) Normalizer if | `src/vibemix/__main__.py::_normalize_codex_curate_result` | New `if result.stop_reason == "user_canceled":` returning the appropriate dict shape — sibling of the clarification `if` | NO |
| Seal test | `tests/library/test_codex_curate_stop_reason.py` | New `test_<reason>_full_chain_to_cli_curate` / `_to_telegram` / `_build_set_path_seal` triplet using the SAME `_runner_with_side_channel` helper + a new `_make_real_<reason>_payload` helper — sibling of the Phase-100 seal block | NO existing seal test touched |

This is the **discriminated-union pattern** Plans 99 + 100 lock. The seal test scaffolding (helpers, runner factory, posture) carries forward verbatim.

## §HARDEN-PHASE-B-CLARIFICATION-TONE KAAN-ACTION Checkpoint

**Status:** DEFERRED TO v10.0 MILESTONE CLOSE (default per `gsd-autonomous fully` mode + `gate="non-blocking"` posture).

**The three sample question framings** (Codex-generated copy that vibemix renders verbatim — vibemix's rendering structure is locked; the TONE of the question text is the ear-pass surface):

**Sample A — BPM range disambiguation:**

```
❓ Which BPM range fits this set?
  1. slow (90-110)
  2. mid (115-128)
  3. fast (130-145)
  4. mixed

  Re-run with: library curate "<original theme> + <chosen option>"
```

**Sample B — context disambiguation:**

```
❓ Which context is this for?
  1. bedroom headphones
  2. club peak time
  3. festival main stage
  4. warmup set

  Re-run with: library curate "<original theme> + <chosen option>"
```

**Sample C — mood register disambiguation:**

```
❓ Which mood register?
  1. chill / introspective
  2. energetic / driving
  3. dark / techno
  4. euphoric / uplifting

  Re-run with: library curate "<original theme> + <chosen option>"
```

**Kaan's ear-pass question:** *"Does Codex's actual production framing sound like a real DJ friend asking for a quick check, or like a robot survey?"*

**Verdict matrix (4 options):**

| Verdict | Action | KAAN-ACTION outcome | Downstream |
| ------- | ------ | ------------------- | ---------- |
| **PASS** | All 3 framings sound on-brand on Kaan's ear-pass | Ship as-is — vibemix's rendering is locked, Codex's tone-on-live-key is endorsed | DISCHARGED — §HARDEN-PHASE-B-CLARIFICATION-TONE closed in `.planning/PROJECT.md` |
| **REVISE** | Some framings sound robotic — planner ear-pass adjusts wording | Tiny edit to `mcp_server.py`'s `request_clarification` `@mcp.tool()` docstring to coach Codex on TONE (not just "when" but "how to phrase"). vibemix code unchanged. | Small fix-up commit on `live-tuning-or-brain`; SUMMARY's "Kaan-action queue" updated. |
| **DEFER** (TAKEN HERE per `gsd-autonomous fully` mode default) | Kaan can't get to funded-key ear-pass yet | Item RIDES FORWARD to v10.0 milestone close, alongside Phase 99's `§HARDEN-PHASE-A-EAR-PASS` + `§HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY` | `.planning/PROJECT.md` KAAN-ACTION queue keeps the open item; Phase 100 closes regardless per `gate="non-blocking"` |
| **REPLACE** | Re-author the MCP tool docstring to coach Codex on tone (not just "when" to call but "how to phrase") | Larger edit: rewrite the `request_clarification` `@mcp.tool()` docstring as a teaching surface that gives Codex 2-3 in-line example question framings + tone guardrails ("ask like a friend checking in, not a survey asking for input"). vibemix code unchanged. | Larger fix-up commit on `live-tuning-or-brain`; PROJECT.md KAAN-ACTION marked DISCHARGED with rewrite hash. |

**KAAN-ACTION outcome (this plan):** Item RIDES FORWARD to v10.0 milestone close. Per `.planning/PROJECT.md` § v10.0 KAAN-ACTION queue, the ear-pass is parked alongside the Phase 99 items; the funded-Codex-key live run will be Kaan's first session that surfaces real Codex framings against the three sample shapes above. The verdict will be recorded in the milestone-close discharge note.

**Note on test-substring tolerance:** the seal tests pin DISTINGUISHABILITY (`not rendered.startswith("⚠️")`) NOT the exact ❓ glyph. Tone tweaks that change the LEADING GLYPH (e.g. ❓ → 🤔 → ❔) or the WORDING AROUND THE STRUCTURE won't break the seal — only changes that remove the structural pins (question rendered, choices numbered, no FS-path leaks, no ⚠️ on the clarification surface) would force test updates.

## Plan-by-Plan Summary (Phase 100 Close — Commits + Files)

| Plan | Commits | Key files modified | REQ closed |
| ---- | ------- | ------------------ | ---------- |
| 100-01 | `b30a3bf3` (RED) + `c578b839` (GREEN) + `9068d641` (fix) | `src/vibemix/library/toolset.py`, `tests/library/test_toolset_clarification.py` (NEW) | HARDEN-CLARIFY-01 |
| 100-02 | 2 commits (RED + GREEN) | `src/vibemix/library/mcp_server.py`, `tests/library/test_mcp_server_clarification.py` (NEW) | HARDEN-CLARIFY-02 |
| 100-03 | `2e028bbd` (RED) + GREEN | `src/vibemix/library/codex_curate.py`, `tests/library/test_codex_curate_stop_reason.py` (extended), `tests/library/test_toolset.py` | HARDEN-CLARIFY-03 |
| 100-04 | 2 commits | `src/vibemix/__main__.py`, `tests/library/test_cli_exit_codes.py` (extended) | HARDEN-CLARIFY-04, HARDEN-CLARIFY-06 (CLI side) |
| 100-05 | `c7dfb81b` + 1 more | `src/vibemix/library/telegram_bridge.py`, `tests/library/test_telegram_bridge.py` (extended) | HARDEN-CLARIFY-05 |
| 100-06 | `b5ee3cbc` (GREEN) + `77b95563` (docs) + `24319125` (close) | `tests/library/test_request_clarification_no_track_surface.py` (NEW or extended — AST gate) | HARDEN-CLARIFY-06 (AST gate side) + complement to HARDEN-CLARIFY-07 |
| **100-07** | `991b7938` (this plan — GREEN seal) | `tests/library/test_codex_curate_stop_reason.py` (extended +310 lines, 0 deletions) | **HARDEN-CLARIFY-07** + Phase 100 close |

## Acid Test Verdict

Phase 100 § CONTEXT.md domain section acid test:

> **When Codex sees an ambiguous theme, it calls `request_clarification(question, choices)`; vibemix terminates with `stop_reason="clarification_needed"`; CLI exits with code 11 + 2-block render; Telegram renders numbered choices leak-stripped; vibemix retains NO state across the cycle.**

**Status: PASSED (engineering surface).** Verified by:

1. **Codex sees an ambiguous theme** → trusted via `@mcp.tool()` decorator + teaching docstring (Plan 100-02) + the MCP STDIO seam.
2. **Codex calls `request_clarification(question, choices)`** → routed to `LibraryToolset.request_clarification` via the dispatch table entry (Plan 100-01).
3. **vibemix terminates with `stop_reason="clarification_needed"`** → `_build_clarification_payload` writes the discriminated-union shape; the dispatch-top short-circuit (Phase 99) fires on every subsequent call. Pinned by Plan 100-01 + the Phase-100 seal tests in this plan.
4. **CLI exits with code 11 + 2-block render** → `_cmd_library_curate_codex` + `_cmd_library_build_set_codex` carry the exit-11 if-block + 2-block stderr render. Pinned by Plan 100-04 unit tests + this plan's `test_clarification_full_chain_to_cli_curate` + `test_clarification_build_set_path_seal`.
5. **Telegram renders numbered choices leak-stripped** → `_normalize_codex_curate_result` emits the contract dict; `format_reply` renders the multi-line `❓ <question>\n1. <choice>...` shape through `strip_leaks`. Pinned by Plan 100-05 unit tests + this plan's `test_clarification_full_chain_to_telegram` (with the leak-strip regression-pin).
6. **vibemix retains NO state across the cycle** → the re-run hint string is the user-facing single-turn closure; Codex is fully restarted on the next run. Pinned by the AST gate in Plan 100-06 + the re-run-hint assertion in this plan's CLI seal.

**KAAN-ACTION ear-pass** (§HARDEN-PHASE-B-CLARIFICATION-TONE) is parked to v10.0 milestone close per `gsd-autonomous fully` mode default (see KAAN-ACTION Checkpoint section above).

## Cardinal Invariants — Re-Verified

- **#1 single-writer (analog):** Holds. The seal tests are READ-ONLY against `self.stop_reason` — they construct a fresh toolset, call `_build_clarification_payload`, and assert on the returned dict + the wrapper's `CodexCurateResult.stop_reason` field. The only writers of `self.stop_reason` are still the two confined sites inside `LibraryToolset` (threshold-trip from Plan 99-03 + handler from Plan 100-01). The Plan 99-05 AST gate via `tests/repo/test_no_seen_relaxation.py STOP_REASON_WHITELIST` stays GREEN (verified in plan verify chain).
- **#2 citation grounding:** Holds STRUCTURALLY. `request_clarification` has no `track_id` surface (Plan 100-01 behavioral pin + Plan 100-06 AST gate prove it). The seal tests in this plan do not touch grounding state at all — they read only the public dataclass + CLI exit codes + format_reply string. `self.seen.add` count in `toolset.py` is unchanged (the Plan 99-05 baseline of 2).
- **#3 trust the audio:** N/A direct. Extended to the curation surface in Plan 99-03 via `_build_starvation_payload` (deterministic 3-case dispatch) and Plan 100-01 via `_build_clarification_payload` (defensive `list(choices)` copy + structural validation). The seal tests in this plan prove the deterministic generators reach the user-visible CLI + Telegram surfaces unchanged — the "trust the audio" extension to the curation surface is now sealed at the user-visible boundary.
- **#4 one socket:** N/A. CLI + MCP STDIO + Telegram long-poll surfaces only; no new ws traffic.

## Threat Register — Disposition Verified

- **T-100-07-01 (Tampering — future PR drifts ONE plan's surface without breaking its narrow test):** Mitigated. Integration seal tests assert end-to-end substring presence + the dataclass shape contract. A render-format drift in Plan 100-04 (e.g. removing "Re-run with:" from the CLI stderr) fails this plan's seal test with a precise substring diff even if Plan 100-04's narrow test still passes. Same for `format_reply` (Plan 100-05) and the normalizer (Plan 100-04 bridge).
- **T-100-07-02 (Information disclosure — integration test prints leaks during execution):** Accepted. The seal tests use `capsys` for stderr/stdout capture (pytest-managed, in-memory, auto-cleaned). No `tmp_path` fixture is used in the new tests — the wrapper allocates its own `TemporaryDirectory` inside the wrapped `curate_with_codex` call, which pytest doesn't touch. No leak to disk persists beyond test session.
- **T-100-07-03 (Anti-slop — Codex's actual clarification question copy is robotic / sloppy in production):** Accepted (KAAN-ACTION ear-pass). Plan 100-07 SUMMARY surfaces three sample question framings for KAAN-ACTION §HARDEN-PHASE-B-CLARIFICATION-TONE on funded key. Per CLAUDE.md "real DJ friend in your ear, no AI slop" + `gsd-autonomous fully` mode default = DEFER to v10.0 milestone close.
- **T-100-07-SC (Tampering — npm/pip/cargo installs):** Accepted. Zero new packages; the seal tests use stdlib `unittest.mock`, `argparse`, plus the existing `vibemix.*` imports.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Process discipline] Pre-existing parallel-session uncommitted work in the target test file.**

- **Found during:** Task 1 — pre-stage `git diff --cached --name-only` check.
- **Issue:** The test file `tests/library/test_codex_curate_stop_reason.py` had ~13 uncommitted hunks in the working tree from a sibling executor session that's not yet committed: (a) `chat_with_codex` import addition + (b) two new chat-propagation tests (`test_uniform_clarification_propagation_chat_path` + `test_chat_propagates_starvation_via_side_channel`) + (c) formatting collapses across ~11 existing tests (multi-line f-string assertions collapsed to single-line). If I had naively staged the full file, my commit would have included the parallel session's work-in-progress, claiming credit for it AND blocking the other session from making its own clean commit when it finishes.
- **Fix:** Used the HEAD-then-overlay-then-restore pattern, NOT `git stash` (the destructive-git-prohibition rule forbids `git stash` because the stash list is shared across worktrees and sibling sessions). Sequence:
  1. `cp tests/library/test_codex_curate_stop_reason.py /tmp/working-tree-saved.py` (save parallel session's working tree state)
  2. `git checkout HEAD -- tests/library/test_codex_curate_stop_reason.py` (restore HEAD)
  3. Re-applied my net-new seal block via `Edit` tool (one append at end of file)
  4. `git add tests/library/test_codex_curate_stop_reason.py` + `git diff --cached --stat` verified 310 insertions, 0 deletions
  5. Committed `991b7938` with named-path staging discipline
  6. `cp /tmp/working-tree-saved.py tests/library/test_codex_curate_stop_reason.py` (restore parallel session's saved state)
- **Damage assessment (verified):** None. My commit (`991b7938`) shows clean single hunk at end of file. Working tree now contains parallel session's uncommitted edits PLUS my committed seal block (in HEAD) — the other session can run `git diff HEAD --` to see only their own work, unchanged. Test counts: 14 tests on `test_codex_curate_stop_reason.py` at HEAD-clean (11 prior + 3 new seal) + 16 tests with parallel session's chat tests applied. All green in both states.
- **Why auto-fixable (Rule 1):** Process discipline failure (would have claimed credit for another session's work) — pure procedural fix. No code change. No architectural decision.

### Architectural Decisions Not Made (Rule 4 not triggered)

None. The plan's `<task type="auto" tdd="true">` block + the existing seal-test posture from Phase 99 Plan 99-08 + the Phase 100-03 propagation tests already in the file pre-empted every architectural decision. The plan even notes "Plan 100-07 is GREEN-only (no RED → GREEN cycle needed)" — there was no design choice on whether to run RED first.

## Phase 100 Deferred-Items Update

No new pre-existing failures surfaced from this plan's verify run on the Phase 100 island. The Phase 99 deferred-items.md inventory carries forward unchanged. The single pre-existing skip + xfail in `tests/library/` are pre-existing (transformers missing + budget gate xfail per Kaan's 2026-05-25 decision) — both documented in their respective xfail/skip messages, owned by other phases or upstream cost-model decisions.

If a future broader-suite run uncovers Phase-100-specific deferrals, they will be filed at `.planning/phases/100-harden-clarify/deferred-items.md` under the same scope-boundary disposition as the Phase 99 deferred-items.md.

## Phase 100 VERIFICATION.md Handoff

`gsd-verifier` should run the following as Phase 100 verification report inputs:

1. **REQ coverage matrix** (above — 7/7 closed).
2. **Acid test verdict** (above — PASSED engineering surface).
3. **KAAN-ACTION surface** (above — DEFERRED to v10.0 milestone close per `gsd-autonomous fully` mode).
4. **Forward-compat structural proof** (above — sibling-extension pattern locked, demonstrated by `user_canceled` exemplar).
5. **Cardinal invariants re-verification** (above — all 4 hold).
6. **Plan verify chain** (`source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/library/test_codex_curate_stop_reason.py tests/library/test_cli_exit_codes.py tests/library/test_telegram_bridge.py tests/library/test_toolset_clarification.py tests/library/test_mcp_server_clarification.py tests/library/test_request_clarification_no_track_surface.py tests/repo/test_no_seen_relaxation.py tests/library/test_toolset_starvation.py tests/library/test_toolset_starvation_concurrency.py`) → 115 passed, 0 regressions, on HEAD-clean state.
7. **Phase island full sweep** (`tests/library/`) → 706 passed, 1 skipped (pre-existing transformers), 1 xfailed (pre-existing budget gate), 0 regressions.

## Self-Check: PASSED

**Files claimed:**
- `[ FOUND ]` `tests/library/test_codex_curate_stop_reason.py` — 1160 lines at HEAD post-commit (was 850 in HEAD prior), modified +310 insertions / 0 deletions in 1 hunk. Confirmed via `git show 991b7938 --stat`.
- `[ FOUND ]` `.planning/phases/100-harden-clarify/100-07-SUMMARY.md` — this file.

**Commits claimed:**
- `[ FOUND ]` `991b7938` — `test(100-07): GREEN — integration seal proving end-to-end uniform clarification propagation across toolset+wrapper+normalizer+CLI+Telegram`. Verified via `git log --oneline -3`.

**Test counts claimed:**
- `[ VERIFIED ]` 14/14 GREEN on `tests/library/test_codex_curate_stop_reason.py` at HEAD-clean (11 prior + 3 new seal).
- `[ VERIFIED ]` 16/16 GREEN with parallel session's chat tests re-applied to working tree (verification that my changes don't conflict with parallel session's in-flight work).
- `[ VERIFIED ]` 115/115 GREEN on the Plan 100-07 verify chain.
- `[ VERIFIED ]` 706 passed / 1 skipped / 1 xfailed on `tests/library/` — zero regressions.

**Symbol locations claimed:**
- `[ VERIFIED ]` `test_clarification_full_chain_to_cli_curate` at `tests/library/test_codex_curate_stop_reason.py` (post-Phase-100-07 seal block).
- `[ VERIFIED ]` `test_clarification_full_chain_to_telegram` at same file.
- `[ VERIFIED ]` `test_clarification_build_set_path_seal` at same file.

**Concurrent-sessions discipline claimed:**
- `[ VERIFIED ]` Single hunk in commit (`git show 991b7938 --stat` → 310 insertions, 0 deletions).
- `[ VERIFIED ]` Post-commit deletion check (`git diff --diff-filter=D --name-only HEAD~1 HEAD`) returned empty.
- `[ VERIFIED ]` No `git stash`, no `git add -A`, no `git restore .` used. HEAD-then-overlay-then-restore pattern only.
- `[ VERIFIED ]` Parallel session's uncommitted work preserved in working tree (verified via `git diff HEAD -- tests/library/test_codex_curate_stop_reason.py` showing 13 unrelated hunks from sibling session).

## Notes for Downstream Phases

- **v10.0 milestone close**: TWO + ONE KAAN-ACTION items now ride forward to milestone close:
  - `§HARDEN-PHASE-A-EAR-PASS` (Phase 99 — seeded starvation hint copy)
  - `§HARDEN-PHASE-A-ENV-PROPAGATION-VERIFY` (Phase 99 — Codex CLI env-passthrough live verification)
  - `§HARDEN-PHASE-B-CLARIFICATION-TONE` (Phase 100 — clarification question framing ear-pass) — surfaced in this SUMMARY with three sample framings + 4-option verdict matrix.
- **Future stop_reasons (Phase 101+)**: forward-compat is structurally proven. Add a sibling test triplet (cli_curate + telegram + build_set_path) using the SAME `_runner_with_side_channel` helper + a new `_make_real_<reason>_payload` helper. Slot alongside the existing Phase-99 / Phase-100 seal blocks. The discriminated-union pattern at 6 sibling-extension layers (handler / payload helper / wrapper elif / CLI elif / format_reply elif / normalizer if) is the contract that Phases 99 + 100 lock.
- **Plan-checker**: REQ coverage 7/7 verified across `.planning/phases/100-harden-clarify/100-{01..07}-SUMMARY.md`. Each REQ-ID has a closure plan + test pin documented in the matrix above.
