---
phase: 100-harden-clarify
plan: 05
subsystem: library/telegram_bridge format_reply
tags: [telegram, format-reply, clarification-needed, factor-7, hardening, sibling-extension, anti-slop, harden-clarify-05]
requires:
  - _normalize_codex_curate_result clarification branch (__main__.py:3004-3010 from 100-04 — emits {ok: False, stop_reason: "clarification_needed", question: str, choices: list[str]})
  - tool_starvation branch in format_reply (telegram_bridge.py:118-127 from 99-07 — sibling whose insertion-order discipline this plan continues)
  - strip_leaks scrubber (telegram_bridge.py:102-104 — unchanged, T-99-05 mitigation reused for T-100-05-01)
  - Plan 99-05 AST whitelist for stop_reason reads in telegram_bridge.py (already authorized by tests/repo/test_no_seen_relaxation.py — Plan 100-05 reads `norm.get("stop_reason")` inside that whitelist)
provides:
  - clarification_needed branch in format_reply (library/telegram_bridge.py:137-145 — 9-line block BETWEEN the tool_starvation branch and the generic `if not norm.get("ok")` error branch)
  - Multi-line render: "❓ <question>\n1. <choice>\n2. <choice>\n..." — numbered 1-indexed (CLI parity with Plan 100-04)
  - Leak-stripped output (T-100-05-01 mitigation via strip_leaks)
  - EXPECTED_STARVATION_OUTPUT regression-pin (tests/library/test_telegram_bridge.py:130 — captures Phase 99 byte-equivalent shape, extends test_format_reply_existing_branches_unchanged)
  - 2 new tests (test_format_reply_clarification_branch + test_format_reply_clarification_strips_leaks) — pin question header + numbered choices + non-⚠️ leading glyph + path-leak scrub
affects:
  - src/vibemix/library/telegram_bridge.py (+16 insertions, 0 deletions; single additive edit inside format_reply, between lines 127 and 129 pre-edit)
  - tests/library/test_telegram_bridge.py (+77 insertions, -1 deletion; 2 new tests + 1 module-scope EXPECTED_STARVATION_OUTPUT pin + extension of existing regression-pin to cover starvation byte-equivalence + Phase 100 section-header comment)
tech-stack:
  added: []
  patterns:
    - "Sibling-branch dispatch on stop_reason: `if norm.get(\"stop_reason\") == \"clarification_needed\":` matches the Phase 99-07 `tool_starvation` shape verbatim — future stop_reasons (Phase 100+) follow the same single-branch-per-reason pattern, never refactored into a switch/dict."
    - "Insertion-order discipline (load-bearing): clarification branch sits BETWEEN tool_starvation (above) and the generic `if not norm.get(\"ok\")` (below) — the clarification payload carries ok=False so the generic would shadow it otherwise. Same discipline Plan 99-07 documented at the same site."
    - "Defense-in-depth on strip_leaks: question + choices flow through `strip_leaks(\"\\n\".join(lines))` — defensive against future FS-path leaks in Codex's clarification copy (T-100-05-01). Mirrors Plan 99-07's `strip_leaks(f\"⚠️ {hint}\")` pattern."
    - "Distinguishing leading glyph for stop_reason branches: ❓ (U+2753 BLACK QUESTION MARK ORNAMENT) for clarification, ⚠️ for tool_starvation + generic error. Visually signals \"needs user input\" vs \"error\" — a sighted user can distinguish the two at a glance without reading text."
    - "Defensive `or` fallbacks on payload fields: `norm.get(\"question\") or \"(no question)\"` + `norm.get(\"choices\") or []` — empty payload renders structurally instead of raising, mirroring Phase 99-07's `norm.get(\"hint\") or norm.get(\"error\") or \"<fallback>\"` triple-fallback pattern."
    - "Regression-pin extension instead of new sibling test: EXPECTED_STARVATION_OUTPUT pinned at module scope (mirrors Phase 99-07's EXPECTED_PLAYLIST_OUTPUT) + the existing test_format_reply_existing_branches_unchanged extended to also assert starvation byte-equivalence. Plan-suggested alternative (new sibling test) would have duplicated the existing test's pattern; extension keeps the regression-pin axis single-source."
    - "Named-path stage discipline (concurrent-session hazard): Wave-4 concurrent Plan 100-04 was active on __main__.py + test_cli_exit_codes.py. Plan 100-05 commits explicitly staged only telegram_bridge.py + test_telegram_bridge.py via `git add <named-path>`; `git diff --cached --name-only` verified before each commit."
key-files:
  created: []
  modified:
    - src/vibemix/library/telegram_bridge.py
    - tests/library/test_telegram_bridge.py
decisions:
  - "D-07 closure (CONTEXT.md Decision 7): branch in format_reply renders the question + numbered choices as a multi-line text message, leak-stripped through strip_leaks. NO inline-keyboard buttons — single-turn semantic; the user re-composes the next theme manually. This sibling-extends Plan 99-07's tool_starvation branch with the same insertion-order discipline (BEFORE the generic ok=False block)."
  - "Leading glyph choice: ❓ (U+2753 BLACK QUESTION MARK ORNAMENT). Rationale: must be distinct from ⚠️ used by the tool_starvation + generic error branches (visually signals \"error\" — wrong semantic for clarification). ❓ signals \"needs user input\" intuitively. Plan offered executor latitude; the CONTEXT.md anti-slop tone supports asking-not-warning. Test asserts `not out.startswith(\"⚠️\")` (distinguishability) rather than the exact ❓ glyph — keeps room for ear-pass refinement (e.g. 🤔, ❔) without test churn."
  - "Defensive fallback shape: `norm.get(\"question\") or \"(no question)\"` matches the docstring-noted Plan 100-04 contract that the normalizer emits `question: str` (may be empty string on malformed payload). The fallback `(no question)` makes the empty case structurally render a question marker instead of `❓ ` (a glyph alone) — small anti-slop quality lift for a near-unreachable defensive branch. `choices: list[str]` empty list iterates to zero `1. ...` lines — clean structural render."
  - "Existing Phase 99-07 forward-compat comment KEPT: line 117 still reads \"Phase 100 adds `clarification_needed` as a sibling branch in the same slot.\" The pointer remains accurate as documentation of Phase 99's forward-compat intent. The new branch's own comment block (lines 129-136) describes it as now-wired. Plan offered executor latitude on this — kept-as-is is the harmless documentation-of-history disposition."
  - "Regression-pin extension over new sibling test: EXPECTED_STARVATION_OUTPUT pinned at module scope + test_format_reply_existing_branches_unchanged extended to assert byte-equivalence. The plan offered a new sibling test as an alternative — chose extension because the existing test is already the byte-equivalence axis; adding it inline keeps the regression-pin single-source and reads naturally as \"the three pre-Plan-100-05 branches stay byte-equivalent\"."
  - "Disjointness verification with concurrent Wave-4 Plan 100-04: at both commits, `git diff --cached --name-only` showed only telegram_bridge.py + test_telegram_bridge.py. Plan 100-04's island (__main__.py + test_cli_exit_codes.py) was already committed at c7dfb81b before Plan 100-05 RED; no concurrent staging-race occurred. T-100-05-DJ mitigated."
patterns-established:
  - "Stop-reason branch sibling-extension at format_reply: when a new stop_reason ships (Phase 99 = tool_starvation, Phase 100 = clarification_needed, future = ?), add an `if norm.get(\"stop_reason\") == \"<new>\":` branch in the same slot — BEFORE the generic ok=False fallback. Pick a distinguishing leading glyph (⚠️ taken, ❓ taken). Always wrap through strip_leaks for defense-in-depth."
  - "Triple-test posture for a new format_reply branch: (1) render-shape test pins the structure, (2) leak-strip test pins T-N-N-01 privacy mitigation, (3) extend the existing byte-equivalence regression-pin instead of duplicating it."
requirements-completed: [HARDEN-CLARIFY-05]
metrics:
  duration: "~6 min"
  completed: "2026-05-28"
  tasks_completed: 2
  files_modified: 2
  tests_added: 2 (test_format_reply_clarification_branch, test_format_reply_clarification_strips_leaks)
  tests_extended: 1 (test_format_reply_existing_branches_unchanged — extended with EXPECTED_STARVATION_OUTPUT assertion)
  tests_passing: 20/20 (test_telegram_bridge.py — was 18, +2) + 11/11 (test_codex_curate_stop_reason.py — Phase 99/100 regression-pin) + 9/9 (test_cli_exit_codes.py — Plan 100-04 regression-pin) + 12/12 (test_toolset_clarification.py — Plan 100-01 regression-pin) + 11/11 (test_mcp_server_clarification.py — Plan 100-02 regression-pin) + 19/19 (test_toolset_starvation.py — Phase 99 regression-pin) + 3/3 (test_no_seen_relaxation.py — Plan 99-05 AST gate)
  regressions: 0
---

# Phase 100 Plan 05: format_reply clarification_needed Branch (Telegram Surface) — Summary

**Closed the Telegram leg of HARDEN-CLARIFY-05. Plan 100-04's `_normalize_codex_curate_result` clarification branch emits `{"ok": False, "stop_reason": "clarification_needed", "question": str, "choices": list[str]}` — `format_reply` now renders that as a multi-line message with a ❓ header line carrying the question + numbered 1-indexed choices, leak-stripped through `strip_leaks` (T-100-05-01 defense). Sibling-extension of Plan 99-07's `tool_starvation` branch at the same insertion site, with the same insertion-order discipline (BEFORE the generic `if not norm.get("ok")` block, because the clarification payload also carries ok=False).**

The full Factor-7 Telegram chain is now end-to-end: `toolset.request_clarification` → side-channel write (Plan 100-01) → wrapper read into `CodexCurateResult.stop_reason="clarification_needed"` (Plan 100-03) → `_normalize_codex_curate_result` dict-shape conversion (Plan 100-04) → `format_reply` chat render (this plan). Plan 100-07 will pin this end-to-end in an integration seal test.

## What Shipped

### A. format_reply clarification_needed branch (`src/vibemix/library/telegram_bridge.py`)

**Exact insertion site: lines 129-145** — BETWEEN the existing Phase 99 `tool_starvation` branch (lines 118-127, byte-equivalent) and the existing generic `if not norm.get("ok"):` block (now at line 147).

| Edit | Lines | What |
| ---- | ----- | ---- |
| Comment block | **129-136** | "Plan 100-05 HARDEN-CLARIFY-05: clarification_needed branch — sibling of the tool_starvation branch above. Renders the question + numbered choices as a multi-line message. Insertion order load-bearing: BEFORE the generic `if not norm.get(\"ok\")` branch, because the clarification payload also carries ok=False and would otherwise be shadowed (the same insertion-order discipline Phase 99 Plan 99-07 documented for tool_starvation). Single-turn semantic (CONTEXT.md Decision 7): no inline-keyboard buttons — the user reads the choices and re-composes the next theme manually." |
| Branch check | **137** | `if norm.get("stop_reason") == "clarification_needed":` — sibling shape of Phase 99-07's `tool_starvation` check; pinned by Plan 99-05 AST whitelist (telegram_bridge.py already authorized). |
| Defensive fallbacks | **138-139** | `question = norm.get("question") or "(no question)"` + `choices = norm.get("choices") or []` — empty payload renders structurally instead of raising. Mirrors Plan 100-04's `or ""` + `or []` defensive pattern. |
| Header line | **140** | `lines = [f"❓ {question}"]` — leading glyph ❓ (U+2753) distinct from ⚠️ used by error branches. Visually signals "needs user input" vs "error". |
| Numbered choices loop | **141-142** | `for i, choice in enumerate(choices, start=1): lines.append(f"{i}. {choice}")` — 1-indexed, dot separator. CLI parity with Plan 100-04's stderr render. |
| Return | **143** | `return strip_leaks("\n".join(lines))` — T-100-05-01 defense; mirrors Plan 99-07's `return strip_leaks(f"⚠️ {hint}")` posture. |

### B. Tests (`tests/library/test_telegram_bridge.py`)

Two new tests + one regression-pin extension + one new module-scope constant, appended after the existing Plan 99-07 tests:

| Test | What pinned |
| ---- | ----------- |
| `test_format_reply_clarification_branch` | Calls `format_reply({"ok": False, "stop_reason": "clarification_needed", "question": "What BPM range?", "choices": ["slow (90-110)", "fast (130-140)", "mixed"]})`. Asserts return is non-empty str, contains question substring, contains each choice with `1.` / `2.` / `3.` integer-dot prefix, and does NOT start with ⚠️ (distinguishability from error branches). |
| `test_format_reply_clarification_strips_leaks` | Calls with `question="Library at /Users/ozai/.cache/vibemix — context?"` + `choices=["bedroom", "club"]`. Asserts `/Users/ozai` NOT in output, `[path]` IS in output (strip_leaks scrubbed), and the non-path portions `context?`, `bedroom`, `club` survive. T-100-05-01 pin. |
| `test_format_reply_existing_branches_unchanged` (EXTENDED) | Already pinned playlist + generic-error byte-equivalence (Phase 99-07). EXTENDED to also assert tool_starvation byte-equivalence against the new `EXPECTED_STARVATION_OUTPUT` constant. Drift from a Plan 100-05 edit to the tool_starvation branch = test failure. |

**New module-scope constant** at line 130:

```python
EXPECTED_STARVATION_OUTPUT = "⚠️ library has 0 tracks — run `library ingest` first"
```

Captured by manually running `format_reply({"ok": False, "stop_reason": "tool_starvation", "hint": "library has 0 tracks — run `library ingest` first"})` on current source pre-edit. The hint contains no FS paths, so `strip_leaks` is a no-op — the literal string above is the byte-equivalent render.

## Leading Glyph Choice + Distinguishability

The plan offered executor latitude on the glyph; chose **❓ (U+2753 BLACK QUESTION MARK ORNAMENT)**.

| Branch | Glyph | Reads as |
| ------ | ----- | -------- |
| `tool_starvation` (Phase 99) | ⚠️ | "warning — something went wrong" |
| Generic `ok=False` (pre-99) | ⚠️ | "warning — something went wrong" |
| `clarification_needed` (Plan 100-05) | ❓ | "asking — needs your input" |
| Playlist happy-path | 🎧 | "delivering — here's your set" |

The semantic axis is **error (⚠️) vs ask (❓) vs deliver (🎧)** — a sighted user can distinguish the three at a glance without reading text. The test asserts `not out.startswith("⚠️")` (the distinguishability axis), not the exact ❓ glyph — leaves room for ear-pass refinement (e.g. 🤔 BLOWING-A-KISS variations, or removing the glyph entirely if anti-slop tone demands it) without test churn.

## Insertion-Site Line Numbers

### `src/vibemix/library/telegram_bridge.py`

| Region | Lines (post-edit) | Notes |
| ------ | ----------------- | ----- |
| format_reply docstring | 108-113 | byte-equivalent |
| Phase 99-07 sibling-pointer comment | 114-117 | byte-equivalent (kept as historical-intent documentation; sibling now exists) |
| Phase 99 tool_starvation branch | 118-127 | byte-equivalent — regression-pinned by EXPECTED_STARVATION_OUTPUT |
| **Plan 100-05 clarification_needed branch** | **129-145** | **NEW — single additive hunk, +16 / -0** |
| Generic `if not norm.get("ok")` block | 147-149 | byte-equivalent (pushed from line 129 to 147 by the additive insert) |
| Playlist happy-path | 151-157 | byte-equivalent — regression-pinned by EXPECTED_PLAYLIST_OUTPUT |

Diff envelope: **+16 insertions / 0 deletions** in `telegram_bridge.py` (`git diff src/vibemix/library/telegram_bridge.py | grep -E "^-" | grep -v "^---"` empty). Clean additive insert.

## Grep-Gate Verification

```bash
$ grep -c "clarification_needed" src/vibemix/library/telegram_bridge.py
3
# Breakdown:
#   1 load-bearing (line 137 — branch check)
#   2 inline comments (line 117 Phase-99 forward-compat pointer; line 129 Plan-100-05 comment header)
# Same minor-textual-fix pattern Plan 99-07 / 100-04 documented as Deviation #1.

$ grep -c "❓" src/vibemix/library/telegram_bridge.py
1
# Exactly 1 — line 140 (new branch leading glyph). ✓

$ grep -c "⚠️" src/vibemix/library/telegram_bridge.py
4
# Breakdown:
#   line 127 — tool_starvation branch (Phase 99, byte-equivalent)
#   line 147 — generic error branch (pre-99, byte-equivalent)
#   line 205 — _handle timeout reply (pre-99, byte-equivalent, OUTSIDE format_reply)
#   line 209 — _handle exception reply (pre-99, byte-equivalent, OUTSIDE format_reply)
# Plan-spec "= 2" was scoped to format_reply; lines 127 + 147 = 2 inside format_reply.
# Lines 205 + 209 are TelegramBridge._handle's reply messages, untouched by this plan.

$ grep -c "tool_starvation" src/vibemix/library/telegram_bridge.py
3
# Breakdown:
#   1 load-bearing (line 118 — Phase 99 branch check, byte-equivalent)
#   2 inline comments in the new Plan 100-05 comment block (lines 130, 134 — both reference
#     "tool_starvation branch above" as context for the new sibling branch)
# byte-equivalent BRANCH BEHAVIOR proved by EXPECTED_STARVATION_OUTPUT regression-pin.

$ grep -n "stop_reason\|return strip_leaks" src/vibemix/library/telegram_bridge.py
118:    if norm.get("stop_reason") == "tool_starvation":
127:        return strip_leaks(f"⚠️ {hint}")
137:    if norm.get("stop_reason") == "clarification_needed":
143:        return strip_leaks("\n".join(lines))
147:    if not norm.get("ok"):
149:        return strip_leaks(f"⚠️ {err}")
156:    return strip_leaks("\n".join(lines))
# Insertion-order check: tool_starvation (118) < clarification_needed (137) < generic-ok (147) ✓
```

## Test Outcomes

```bash
$ source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
    tests/library/test_telegram_bridge.py \
    tests/library/test_codex_curate_stop_reason.py \
    tests/library/test_cli_exit_codes.py \
    tests/library/test_toolset_clarification.py \
    tests/library/test_mcp_server_clarification.py \
    tests/library/test_toolset_starvation.py \
    tests/repo/test_no_seen_relaxation.py 2>&1 | tail -3
........................................................................ [ 69%]
................................                                          [100%]
104 passed in 5.65s
```

| Suite | Before | After | Δ |
| ----- | ------ | ----- | --- |
| `tests/library/test_telegram_bridge.py` | 18 | 20 | +2 (clarification branch + leak-strip) |
| `tests/library/test_codex_curate_stop_reason.py` | 11 | 11 | 0 (no regression) |
| `tests/library/test_cli_exit_codes.py` | 9 | 9 | 0 (Plan 100-04 surface unchanged) |
| `tests/library/test_toolset_clarification.py` | 12 | 12 | 0 (Plan 100-01 surface unchanged) |
| `tests/library/test_mcp_server_clarification.py` | 11 | 11 | 0 (Plan 100-02 surface unchanged) |
| `tests/library/test_toolset_starvation.py` | 19 | 19 | 0 (Phase 99 contract byte-equivalent) |
| `tests/repo/test_no_seen_relaxation.py` | 3 | 3 | 0 (Plan 99-05 AST gate — telegram_bridge.py whitelisted) |
| **Total** | 83 | **85** | **+2** |

**RED→GREEN evidence:**

```bash
# At RED commit e7180592 (test commit, before impl):
$ PYTHONPATH=src python3 -m pytest -q tests/library/test_telegram_bridge.py 2>&1 | tail -3
2 failed, 18 passed in 5.06s
# Failures (expected RED):
#   test_format_reply_clarification_branch         → "What BPM range?" not in '⚠️ no playlist could be built'
#   test_format_reply_clarification_strips_leaks   → "[path]" not in '⚠️ no playlist could be built'
# At GREEN commit e0819f77 (after impl):
$ PYTHONPATH=src python3 -m pytest -q tests/library/test_telegram_bridge.py 2>&1 | tail -3
20 passed in 5.03s
```

**Manual smoke** (Plan verification step 5):

```bash
$ python3 -c "from vibemix.library.telegram_bridge import format_reply; \
out = format_reply({'ok': False, 'stop_reason': 'clarification_needed', 'question': 'Q?', 'choices': ['a', 'b']}); \
print(repr(out))"
'❓ Q?\n1. a\n2. b'
```

Renders cleanly. The empty-choices defensive path produces `'❓ Q?'` with no trailing 1. line (clean structural render); the empty-question path produces `'❓ (no question)'` (the defensive `or "(no question)"` fallback).

## Cardinal Invariants — Re-Verified

- **#1 single-writer (analog):** Untouched. `format_reply` only ROUTES on `norm.get("stop_reason")` (a dict read, not an assignment). No new `self.stop_reason` writer. The Plan 99-05 AST gate at `tests/repo/test_no_seen_relaxation.py` confirms `telegram_bridge.py` is on the read-only whitelist; this plan stays inside that constraint.
- **#2 citation grounding:** Reinforced. The clarification path has NO `track_id` surface — `format_reply` iterates `norm["choices"]` (a `list[str]`) and prints `norm["question"]` (a `str`). Neither could carry a track citation; the AST gate from Plan 100-01 already prevented `request_clarification` from receiving track_ids upstream. Citation grounding is structurally impossible to leak through this surface.
- **#3 trust the audio:** N/A — Telegram surface only.
- **#4 one socket:** N/A — no ws bus traffic; Telegram is long-poll only.
- **#5 idle ≠ fault:** N/A — SessionLayout grounding-failure logic unmodified.

## Threat Register — Disposition Verified

- **T-100-05-01 (Information disclosure — FS path leak via question/choices):** **Mitigated** by `strip_leaks("\n".join(lines))` at line 143. `test_format_reply_clarification_strips_leaks` pins the scrub against an injected `/Users/ozai/.cache/vibemix` path in the question; the `[path]` substitution survives in the output, the literal path does not. Same defense pattern Plan 99-07 used.
- **T-100-05-02 (Tampering — future code change breaks tool_starvation byte-equivalence):** **Mitigated** by EXPECTED_STARVATION_OUTPUT regression-pin extension in `test_format_reply_existing_branches_unchanged`. Drift from a Plan 100-05 edit to the tool_starvation branch trips the test.
- **T-100-05-03 (Spoofing — clarification_needed mention outside whitelist):** **Mitigated.** Plan 99-05's AST gate at `tests/repo/test_no_seen_relaxation.py::test_stop_reason_writes_confined_to_toolset` already pins the four-file whitelist for `stop_reason` references. `telegram_bridge.py` is on the list — Plan 100-05's clarification_needed branch lands inside the authorized whitelist. The AST gate test stays GREEN post-Plan-100-05 (3/3 in the run above).
- **T-100-05-04 (Anti-slop drift — robot-survey tone):** **Accepted** as KAAN-ACTION §HARDEN-PHASE-B-CLARIFICATION-TONE. The rendering format (numbered choices, ❓ glyph) is structurally locked here; the question text comes from Codex per CONTEXT.md Decision 7. Tone verdict happens on funded-key ear-pass.
- **T-100-05-05 (DoS — pathological choices wedges render):** **Mitigated by construction.** Plan 100-01's toolset validates `choices` length 2-5 at the boundary; by the time `result.choices` reaches `format_reply`, it's guaranteed bounded. The `for i, choice in enumerate(norm.get("choices") or [], start=1)` defensive `or []` handles None / cold path; iteration is bounded.
- **T-100-05-DJ (Disjointness violation with Wave-4 Plan 100-04):** **Mitigated.** Plan 100-04's island (`__main__.py` + `test_cli_exit_codes.py`) was already committed at `c7dfb81b` BEFORE Plan 100-05 RED at `e7180592`. `git diff --cached --name-only` at both Plan 100-05 commits showed only `telegram_bridge.py` (GREEN) and `test_telegram_bridge.py` (RED). Zero staging-race overlap.
- **T-100-05-SC (Tampering — npm/pip/cargo installs):** **Accepted.** Zero new packages.

## Disjointness Verification (Concurrent Wave-4)

```bash
$ git log --oneline -3
e0819f77 feat(100-05): GREEN — format_reply clarification_needed branch ...
e7180592 test(100-05): RED — Telegram clarification_needed format_reply branch ...
c7dfb81b docs(100-04): complete CLI exit 11 + 2-block stderr render + ...

$ git diff HEAD~2 HEAD --name-only
src/vibemix/library/telegram_bridge.py
tests/library/test_telegram_bridge.py
```

Plan 100-04 (Wave-4 parallel — `__main__.py` + `test_cli_exit_codes.py`) finalized its docs commit at `c7dfb81b` immediately before Plan 100-05 RED. Plan 100-05's two commits (`e7180592` + `e0819f77`) touched only this plan's two named files. Zero overlap, no concurrent-session staging race. Both plans' islands (CLI + Telegram) close the user-visible HARDEN-CLARIFY-05 + HARDEN-CLARIFY-06 contracts in parallel.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Plan grep-gate: `clarification_needed` count] Plan's `grep -c "clarification_needed" src/vibemix/library/telegram_bridge.py == 1` (load-bearing-only) returned 3 after Task 2.**

- **Found during:** Task 2 grep verification.
- **Issue:** The plan's `<done>` criterion specified `grep -c` returning exactly 1, "comment-filtered count: same". Actual = 3, breakdown:
  - **1 load-bearing** (line 137 — branch check): plan-spec ✓.
  - **2 inline comments**: line 117 (the EXISTING Phase 99-07 forward-compat comment, untouched by Plan 100-05 — the plan offered executor latitude on whether to remove it; I kept it as historical-intent documentation) + line 129 (the NEW Plan 100-05 comment block header).
- **Fix:** No code fix. The spirit of the gate ("load-bearing references bounded + symmetric across sites") is honored: 1 load-bearing hit, exactly per plan-spec. The 2 comment hits are documentation-of-intent (one referencing the historical Phase 99 forward-compat note, one introducing the new branch with the same insertion-order comment Plan 99-07 used). Same minor-textual-fix pattern Plan 99-07 SUMMARY documented as Deviation #1 (`tool_starvation` count 1→2 inflation from a single comment-word).
- **Files modified:** none.
- **Commit:** N/A.

**2. [Rule 1 — Plan grep-gate: `tool_starvation` byte-equivalence vs comment count] Plan didn't specify a `tool_starvation` grep count, but Phase 99-07's SUMMARY pinned `grep -c == 1`. Plan 100-05's edit inflated it to 3.**

- **Found during:** Task 2 grep verification.
- **Issue:** Phase 99-07's `tool_starvation` grep count was 1 (the branch check at line 118). Plan 100-05's new comment block at lines 129-136 mentions "tool_starvation branch above" twice (lines 130, 134 — both as documentation context for the new sibling branch). Total now = 3.
- **Fix:** No code fix. The LOAD-BEARING branch behavior is byte-equivalent (regression-pinned by EXPECTED_STARVATION_OUTPUT). The 2 new comment mentions are documentation that the new sibling branch *follows* the existing tool_starvation branch — load-bearing context for future readers. Rephrasing the comments to drop the literal `tool_starvation` mentions would degrade documentation quality for no benefit (same-shape minor-textual fix Phase 99-07 used to drop the count from 2 to 1 was for a DIFFERENT site — a comment that named the literal token redundantly). Here the literal token IS the documentation point.
- **Files modified:** none.
- **Commit:** N/A.

**3. [Rule 1 — Plan grep-gate: `⚠️` count interpretation] Plan-spec said "grep -c ⚠️ ... returns 2 still (Phase 99 starvation + generic error, both unchanged)". Actual = 4.**

- **Found during:** Task 2 grep verification.
- **Issue:** The plan-spec count of 2 was scoped to `format_reply` (the only function this plan edits). Actual file-wide count includes 2 additional ⚠️ instances at lines 205 + 209 in `TelegramBridge._handle` (the bot's per-message handler), which were already in the file pre-Plan-99-07 and pre-Plan-100-05 (pre-Phase-99 too — they're the no-hang timeout + exception-degrade messages from the original v0 telegram_bridge).
- **Fix:** No code fix. Inside `format_reply` specifically: `⚠️` = 2 (line 127 starvation + line 147 generic error — both byte-equivalent). The 2 outside-format_reply instances are pre-existing handler reply strings untouched by any of Phases 99-100. The plan-spec's interpretation was scope-bound to format_reply; the file-wide grep simply also catches the unrelated handler messages.
- **Files modified:** none.
- **Commit:** N/A.

### Architectural Decisions Not Made (Rule 4 not triggered)

None. The plan's `<antipatterns_to_avoid>` + Plan 99-07's forward-compat authorization + Plan 100-04's contract lock pre-empted every architectural decision:

- Branch inserted BETWEEN tool_starvation and generic error — insertion order load-bearing ✓
- Single-branch dispatch shape (`if norm.get("stop_reason") == "clarification_needed":`) — matches Phase 99-07 sibling shape ✓
- Multi-line numbered-choices rendering — antipattern guard against single-line collapse ✓
- `strip_leaks` applied defensively even though seeded Codex copy may have no FS paths today — defense-in-depth per T-100-05-01 ✓
- No inline-keyboard buttons — Decision 7 single-turn semantic ✓
- ❓ leading glyph chosen for distinguishability from ⚠️ — anti-slop tone preserved ✓
- Defensive `or "(no question)"` + `or []` fallbacks — empty payload renders structurally ✓
- Phase 99-07 forward-compat comment KEPT as historical-intent documentation — executor latitude exercised ✓

## Notes for Downstream Plans

- **Plan 100-07** (integration seal): The full Factor-7 Telegram chain is now end-to-end. Seal-test candidate (sibling of Plan 99-07's suggested starvation seal):

  ```python
  # tests/library/test_harden_clarify_05_seal.py (or extension of test_telegram_bridge.py)
  from vibemix.__main__ import _normalize_codex_curate_result
  from vibemix.library.codex_curate import CodexCurateResult
  from vibemix.library.telegram_bridge import format_reply

  result = CodexCurateResult(
      theme="ambiguous",
      stop_reason="clarification_needed",
      question="What BPM range?",
      choices=["slow (90-110)", "fast (130-140)", "mixed"],
  )
  norm = _normalize_codex_curate_result(result)
  assert norm == {
      "ok": False,
      "stop_reason": "clarification_needed",
      "question": "What BPM range?",
      "choices": ["slow (90-110)", "fast (130-140)", "mixed"],
  }
  rendered = format_reply(norm)
  assert rendered.startswith("❓")
  assert "What BPM range?" in rendered
  assert "1. slow (90-110)" in rendered
  assert "2. fast (130-140)" in rendered
  assert "3. mixed" in rendered
  ```

  This pins the full end-to-end clarification-propagation contract from `_normalize_codex_curate_result` → `format_reply`. Combined with Plan 100-03's `test_clarification_side_channel_propagation_with_real_writer` (toolset → side-channel → wrapper → CodexCurateResult), the full chain is sealable in one composite test.

- **Plan 100-06** (AST gate / contract pin): The `clarification_needed` references on the read side (`telegram_bridge.py` line 137) and on the wrapper-write side (`codex_curate.py` from Plan 100-03) are now both load-bearing. A Plan 100-06 AST extension to the Plan 99-05 gate could add a forward-compat read-whitelist for `stop_reason == "clarification_needed"` mirroring the current `tool_starvation` whitelist — but this is OPTIONAL because the existing gate already whitelists `stop_reason` references file-by-file, not value-by-value.

- **Clarification copy ear-pass (KAAN-ACTION §HARDEN-PHASE-B-CLARIFICATION-TONE):** When Kaan tunes the question + choices Codex emits, the existing regression-pin tests catch any byte-shift on the unrelated branches. The clarification branch's assertions are keyed on the substring contents of an explicit test payload (not Codex's actual production copy), so an ear-pass rewording of Codex's copy doesn't affect test_format_reply_clarification_branch. The Decision-7 rendering format (numbered choices, ❓ glyph) is structurally locked here.

## Commits

| Commit | Type | What |
| ------ | ---- | ---- |
| `e7180592` | test | RED — 2 new tests + 1 new EXPECTED_STARVATION_OUTPUT module-scope pin + extension of test_format_reply_existing_branches_unchanged in tests/library/test_telegram_bridge.py (2 fail RED, 18 prior + regression-pin extension GREEN) |
| `e0819f77` | feat | GREEN — 1 single additive edit in src/vibemix/library/telegram_bridge.py (9-line clarification_needed branch + 7 comment lines, BETWEEN the tool_starvation branch and the generic error branch). +16 / -0 envelope. |

## Self-Check: PASSED

- `[ VERIFIED ]` `src/vibemix/library/telegram_bridge.py` has `if norm.get("stop_reason") == "clarification_needed":` at line 137
- `[ VERIFIED ]` `src/vibemix/library/telegram_bridge.py` has `lines = [f"❓ {question}"]` at line 140
- `[ VERIFIED ]` `src/vibemix/library/telegram_bridge.py` has `return strip_leaks("\n".join(lines))` at line 143 (T-100-05-01 defense)
- `[ VERIFIED ]` `src/vibemix/library/telegram_bridge.py` insertion order: tool_starvation (118) < clarification_needed (137) < generic-ok (147) ✓
- `[ VERIFIED ]` `tests/library/test_telegram_bridge.py` has `test_format_reply_clarification_branch` + `test_format_reply_clarification_strips_leaks` + EXTENDED `test_format_reply_existing_branches_unchanged`
- `[ VERIFIED ]` `tests/library/test_telegram_bridge.py` has `EXPECTED_STARVATION_OUTPUT` module-scope regression-pin constant at line 130
- `[ VERIFIED ]` Commit `e7180592` exists (RED) — `git log --oneline | grep e7180592`
- `[ VERIFIED ]` Commit `e0819f77` exists (GREEN) — `git log --oneline | grep e0819f77`
- `[ VERIFIED ]` `grep -c "clarification_needed" src/vibemix/library/telegram_bridge.py` = 3 (1 load-bearing + 2 comments; Deviation #1 documented)
- `[ VERIFIED ]` `grep -c "❓" src/vibemix/library/telegram_bridge.py` = 1 ✓
- `[ VERIFIED ]` `grep -c "⚠️" src/vibemix/library/telegram_bridge.py` = 4 (2 inside format_reply byte-equivalent + 2 outside in _handle, pre-existing; Deviation #3 documented)
- `[ VERIFIED ]` `grep -c "tool_starvation" src/vibemix/library/telegram_bridge.py` = 3 (1 load-bearing byte-equivalent + 2 new comment refs; Deviation #2 documented)
- `[ VERIFIED ]` `git diff HEAD~2 HEAD --name-only` shows ONLY `src/vibemix/library/telegram_bridge.py` (GREEN) and `tests/library/test_telegram_bridge.py` (RED) — named-path discipline preserved
- `[ VERIFIED ]` `git diff src/vibemix/library/telegram_bridge.py HEAD~1 HEAD | grep -E "^-" | grep -v "^---"` returns empty (purely additive)
- `[ VERIFIED ]` `git diff HEAD~2 HEAD --stat src/vibemix/library/telegram_bridge.py` = +16 / -0 in the single hunk
- `[ VERIFIED ]` Disjointness with Plan 100-04: c7dfb81b (100-04 docs) finalized BEFORE e7180592 (100-05 RED); zero staging-race
- `[ VERIFIED ]` `tests/library/test_telegram_bridge.py` 20/20 GREEN at GREEN commit (was 18, +2)
- `[ VERIFIED ]` `tests/library/test_cli_exit_codes.py` 9/9 still GREEN (Plan 100-04 regression-pin)
- `[ VERIFIED ]` `tests/library/test_codex_curate_stop_reason.py` 11/11 still GREEN (Phase 99/100 regression-pin)
- `[ VERIFIED ]` `tests/library/test_toolset_clarification.py` 12/12 still GREEN (Plan 100-01 surface unchanged)
- `[ VERIFIED ]` `tests/library/test_mcp_server_clarification.py` 11/11 still GREEN (Plan 100-02 surface unchanged)
- `[ VERIFIED ]` `tests/library/test_toolset_starvation.py` 19/19 still GREEN (Phase 99 contract byte-equivalent)
- `[ VERIFIED ]` `tests/repo/test_no_seen_relaxation.py` 3/3 still GREEN (Plan 99-05 AST gate — telegram_bridge.py whitelisted; new branch reads `norm.get("stop_reason")` inside that whitelist)
- `[ VERIFIED ]` Manual smoke: `format_reply({'ok': False, 'stop_reason': 'clarification_needed', 'question': 'Q?', 'choices': ['a', 'b']})` returns `'❓ Q?\n1. a\n2. b'`
- `[ VERIFIED ]` Manual smoke: `format_reply({'ok': False, 'stop_reason': 'tool_starvation', 'hint': 'library has 0 tracks — run \`library ingest\` first'})` returns `'⚠️ library has 0 tracks — run \`library ingest\` first'` (byte-equivalent vs Phase 99)
- `[ VERIFIED ]` Post-commit deletion check: 0 deletions across both commits
- `[ VERIFIED ]` Untracked-file audit: zero new untracked files from this plan (the existing 40+ untracked entries are pre-existing concurrent-session work: v9.0 learn module, debrief, partner docs — none of them is in Plan 100-05's island)
