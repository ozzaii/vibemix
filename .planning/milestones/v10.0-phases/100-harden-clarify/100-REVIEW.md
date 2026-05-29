---
phase: 100-harden-clarify
reviewed: 2026-05-28T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - src/vibemix/library/toolset.py
  - src/vibemix/library/mcp_server.py
  - src/vibemix/library/codex_curate.py
  - src/vibemix/library/telegram_bridge.py
  - src/vibemix/__main__.py
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 100 HARDEN-CLARIFY: Code Review Report

**Reviewed:** 2026-05-28
**Depth:** standard (cross-file traced — toolset → mcp_server → codex_curate → CLI/Telegram)
**Files Reviewed:** 5 source files + 7 test files cross-checked
**Status:** issues_found (0 BLOCKER / 2 WARNING / 5 INFO)

## Summary

Phase 100 sibling-extends the Phase 99 stop_reason infrastructure with the Factor-7 `request_clarification` tool cleanly. The architecture decisions land where they were planned: the LLM-driven terminal path reuses Phase 99's `_write_side_channel`, the `dispatch()` top short-circuit handles the new discriminator by construction (no new control flow), and the wrappers branch on `payload.get("reason")` as forward-compat-promised in the Phase 99 review (verdict #7 of that file).

**Cardinal Invariant #2 (citation grounding) verdict: HELD.** The new `request_clarification` handler has zero track_id surface — reads `args.get("question")` and `args.get("choices")` only, touches no grounding container. The AST gate at `tests/library/test_request_clarification_no_track_surface.py` ACTUALLY proves it (scans `ast.Constant` string-literals + dotted attribute chains in the handler's FunctionDef node — both checks fire on real source). `BASELINE_SEEN_ADD_COUNT` stays at 2 (Phase 99 baseline); the test-gate at `tests/repo/test_no_seen_relaxation.py::test_request_clarification_handler_two_file_pattern` pins the two-file (toolset.py + mcp_server.py) `def request_clarification(` pattern.

**Cardinal Invariant #1 (single-writer analog) verdict: MOSTLY HELD — one robustness gap (WR-01 below).** Phase 100 adds a second `self.stop_reason` write site at `toolset.py:1236`. Via the dispatch table, the dispatch-top short-circuit at line 1314 prevents this site from firing AFTER a prior threshold trip (a starved state masks all subsequent handler invocations, including `request_clarification`). But the handler itself omits the `self.stop_reason is None` first-write-wins guard that the Phase 99 threshold-trip site at line 1372-1378 carries — direct-call callers (e.g. tests, future non-dispatch code paths) can overwrite a starvation payload with a clarification payload.

**Forward-compat for future stop_reasons:** mentally simulating a `user_canceled` sibling lands cleanly. CLI dispatch in `_cmd_library_curate_codex` and `_cmd_library_build_set_codex` would add one more `elif result.stop_reason == "user_canceled":` branch in the same slot (above the generic `print(_json.dumps...)` block). `_normalize_codex_curate_result` adds one more `if result.stop_reason == "user_canceled":` branch. Telegram `format_reply` adds one more sibling branch ABOVE the generic `if not norm.get("ok")` (the same insertion-order discipline Plan 99-07 and Plan 100-05 documented). No restructuring required. **Confirmed sibling-extensible.**

**Anti-slop check on MCP teaching docstring** (`mcp_server.py:230-257`): mentions "ambiguous" + 3 seed examples (BPM range / context / mood register) + the 2-5 length bound + the single-turn semantic. No "I apologize" / "Sorry, I cannot" / generic-AI tone. The docstring teaches Codex when to call.

**Anti-slop check on CLI 2-block render** (`__main__.py:2671-2680`, `:2741-2750`): direct, actionable, no apology language. Re-run hint closes the single-turn loop with the exact subcommand (`library curate` vs `library build-set`) and echoes the user's own theme/brief.

**OUT-OF-SCOPE / not flagged:** Phase 99 carry-over issues (theme-injection in tool_starvation hint, side-channel path-traversal trust, MCP B1 probe stderr noise, `payload` variable name reuse in `codex_curate.py`) — these are pre-existing in Phase 99 and were already addressed or accepted in `99-REVIEW.md`. The current review only flags net-new behaviors introduced by Phase 100.

## Warnings

### WR-01: `request_clarification` handler missing first-write-wins guard

**File:** `src/vibemix/library/toolset.py:1236-1237`
**Issue:** Phase 99's threshold-trip site at lines 1372-1378 wraps its `self.stop_reason = ...` write in `if (... and self.stop_reason is None)` — the documented "first-write-wins" idempotence guard (also documented in this same file's docstring: "After this assignment, the short-circuit at the top of `dispatch()` returns the terminal echo on every subsequent call"). Phase 100's `request_clarification` handler does NOT mirror that guard:

```python
# Valid args. Write the terminal payload ...
self.stop_reason = self._build_clarification_payload(question, choices)
self._write_side_channel(self.stop_reason)
```

In the canonical production code path (LLM → MCP → `dispatch("request_clarification", args)`), the dispatch-top short-circuit at `toolset.py:1314` intercepts any call to `request_clarification` made AFTER `self.stop_reason` was already written by a prior starvation trip, so the handler body is unreachable in that case. Phase 99 review verdict #4 (`First-write-wins idempotence`) confirms the same defense for the threshold-trip site.

But the handler is also callable as a regular bound method (`toolset.request_clarification(args)` — exercised by every test in `tests/library/test_toolset_clarification.py`). In that path, the dispatch-top short-circuit is BYPASSED, and a prior `self.stop_reason` payload (e.g. tool_starvation already tripped on the same run) gets clobbered. The handler's docstring promises "First-write-wins" semantics by analogy to Phase 99 ("Decision 4 — terminal semantics: writing `self.stop_reason` trips the dispatch-top short-circuit") but the actual write site doesn't enforce it.

Concrete defect scenario: a future test or a refactor that calls `request_clarification` directly after a starvation trip silently swaps the payload. The Phase 99 starvation hint (which a wrapper would have surfaced as exit 10) is lost, replaced with an exit-11 clarification — diagnostically wrong, since the LLM never even got to call the tool (starvation already terminated the run).

**Fix:** mirror the Phase 99 threshold-trip site's `is None` guard:

```python
# Valid args. Write the terminal payload (first-write-wins, mirrors the
# threshold-trip site at line ~1372-1378). The dispatch-top short-circuit
# at line ~1314 already intercepts canonical post-trip calls, so this guard
# only fires on direct-call paths (tests, future non-dispatch wrappers) —
# the in-process invariant: ONE terminal stop_reason per run.
if self.stop_reason is None:
    self.stop_reason = self._build_clarification_payload(question, choices)
    self._write_side_channel(self.stop_reason)
# Return the payload to Codex either way — calling request_clarification
# in an already-terminal state still surfaces a coherent response to the
# caller; the prior stop_reason wins the propagation race.
return {
    "clarification_needed": True,
    "question": question,
    "choices": list(choices),
}
```

Alternative (less invasive): leave the write unguarded but document explicitly that `request_clarification` is dispatch-only and direct calls have ill-defined behavior under prior terminal state — and add a test that calls `request_clarification` after a starvation trip to pin whichever semantics the team chooses.

### WR-02: Wrapper side-channel reader silently coerces non-string `choices` entries

**File:** `src/vibemix/library/codex_curate.py:573`, also `:896`, also `:1313-1317`
**Issue:** All three wrapper read sites (curate, build-set, chat) coerce side-channel `choices` entries via `[str(c) for c in cs]`:

```python
if isinstance(payload, dict) and payload.get("reason") == "clarification_needed":
    q = payload.get("question")
    cs = payload.get("choices")
    return CodexCurateResult(
        theme=theme,
        stop_reason="clarification_needed",
        question=str(q) if isinstance(q, str) else None,
        choices=([str(c) for c in cs] if isinstance(cs, list) else None),
    )
```

The handler validates choices as `list[str]` (handler at `toolset.py:1221-1229`: rejects non-string entries with `{"error": ..., "rejected": True}`). The wrapper, reading the same payload from the side-channel file, does NOT re-validate — it coerces. Three regression scenarios:

1.  A side-channel file with `choices: [1, 2, 3]` (corrupted/tampered) propagates as `["1", "2", "3"]` — meaningless choices in the user-facing surface.
2.  A side-channel with `choices: [{"k": "v"}, {}]` propagates as `["{'k': 'v'}", "{}"]` — debug-dict text rendered as a numbered choice.
3.  More importantly: the wrapper read is the trust boundary for the propagation seam. The handler-side validation cannot guarantee anything about a file the wrapper reads — Phase 99's IN-03 (path-traversal trust on `VIBEMIX_STOP_REASON_FILE`) is the orthogonal vulnerability, and this is the data-shape side of the same trust gap.

The defensive isinstance check `if isinstance(cs, list)` only guards against non-list values; it does NOT guard against list-of-non-strings. Comment at codex_curate.py:561-565 says "structurally unreachable in production (Plan 100-01's _build_clarification_payload always populates both fields with the right shape, pinned by Plan 100-01's tests)" — true for the canonical path, but the wrapper is the defensive boundary and should fail-honestly (or normalize) on malformed shape rather than silently coercing to garbage strings.

**Fix:** validate-and-skip non-string entries (defensive), and fall through if the resulting list is empty:

```python
if isinstance(payload, dict) and payload.get("reason") == "clarification_needed":
    q = payload.get("question")
    cs = payload.get("choices")
    # Defensive: skip non-string entries instead of coercing — handler
    # validates list[str] (toolset.py:1221-1229); a corrupted/tampered
    # side-channel file with non-string entries would otherwise propagate
    # as repr-strings ("{'k': 'v'}" etc.). Empty post-filter → propagate
    # None so CLI/Telegram surface the "(no choices)" honest-empty path.
    if isinstance(cs, list):
        validated_choices = [c for c in cs if isinstance(c, str) and c.strip()]
    else:
        validated_choices = None
    return CodexCurateResult(
        theme=theme,
        stop_reason="clarification_needed",
        question=q if isinstance(q, str) and q.strip() else None,
        choices=validated_choices if validated_choices else None,
    )
```

(Apply the same patch at codex_curate.py:889-897 build_set path and codex_curate.py:1306-1331 chat path.)

## Info

### IN-01: Phase-100 wrapper branch uses `if` instead of `elif`

**File:** `src/vibemix/library/codex_curate.py:548-574`, also `:876-897`, also `:1295-1331`
**Issue:** All three wrapper read sites have the structural shape:

```python
if isinstance(payload, dict) and payload.get("reason") == "tool_starvation":
    return CodexCurateResult(...)
if isinstance(payload, dict) and payload.get("reason") == "clarification_needed":
    return CodexCurateResult(...)
```

Both branches end in `return`, so functionally the second `if` is unreachable when the first matches — works correctly. But the structural pattern is two sibling `if`s, not the documented `if / elif` pattern from the CONTEXT.md Decision 3 comment ("Wrapper branches stay `if payload.get("reason") == "tool_starvation": ...` and add `elif payload.get("reason") == "clarification_needed": ...`"). Forward-compat for a future `user_canceled` / etc. would naturally add another sibling `if` instead of growing an `elif` chain — readers see N independent checks rather than one discriminated dispatch.

**Fix:** switch the two clarification-needed read sites to `elif`:

```python
if isinstance(payload, dict) and payload.get("reason") == "tool_starvation":
    return CodexCurateResult(...)
elif isinstance(payload, dict) and payload.get("reason") == "clarification_needed":
    return CodexCurateResult(...)
```

(Strictly mechanical; the test suite stays green.)

### IN-02: `question.strip()` validated but RAW value stored — propagates leading/trailing whitespace

**File:** `src/vibemix/library/toolset.py:1193-1200, 1236`
**Issue:** The handler's question validation reads `if not isinstance(question, str) or not question.strip()` — rejects empty-after-strip. But the accepted `question` value is stored UNSTRIPPED into the payload at line 1236 (via `_build_clarification_payload(question, choices)`). A clarification question like `"  What BPM range?  \n"` passes validation and propagates verbatim:

  * CLI render `__main__.py:2672`: `print(f"  {result.question or '(no question)'}", file=sys.stderr)` — two spaces of indent are appended to the already-leading two spaces, drifting the layout
  * Telegram `format_reply` line 140: `lines = [f"❓ {question}"]` — leading whitespace shifts under the emoji
  * Chat `_chat_clarification_reply` line 1184: `lines = [question or "I need..."]` — appears as first line of reply with whatever leading whitespace Codex emitted

Not a security issue (Codex-supplied, ultimately LLM-bounded). Cosmetic + the same class as Phase 99's IN-02 (theme interpolation without sanitization). The same `isprintable()` filter suggested in 99-REVIEW.md would apply here.

**Fix:** strip and re-validate after stripping:

```python
question = args.get("question")
if not isinstance(question, str):
    return {"error": "...", "rejected": True}
question = question.strip()
if not question:
    return {"error": "request_clarification: 'question' must be a non-empty string", "rejected": True}
```

Apply the same `choice = choice.strip()` normalization in the choices validation loop (lines 1221-1229) so accepted choices store the canonical form. Tests at `test_toolset_clarification.py::test_accept_*` only check truthy semantics, not exact strings — they would still pass.

### IN-03: Two different `question`-None fallback strings across surfaces

**File:** `src/vibemix/__main__.py:2672, 2742, 3007`, `src/vibemix/library/telegram_bridge.py:138`, `src/vibemix/library/codex_curate.py:1184`
**Issue:** Each surface has its own None-fallback for `question`:

  * CLI (`__main__.py:2672, 2742`): `result.question or '(no question)'`
  * Telegram (`telegram_bridge.py:138`): `norm.get("question") or "(no question)"`
  * Telegram normalizer (`__main__.py:3007`): `result.question or ""`
  * Chat (`codex_curate.py:1184`): `question or "I need one more detail before I can answer that."`

Three different strings for the same defensive case. The chat one is the friendliest; CLI's `(no question)` is debug-ish; Telegram's empty string + `❓ ` glyph produces a bare emoji line. A user hitting this fallback on Telegram vs CLI vs chat sees three different products. It also makes "search for the None-fallback copy" non-obvious.

The handler validates question as non-empty before write, so this fallback only fires on a side-channel race (file corruption, malformed JSON, etc.). Low-impact, but a single shared `_FALLBACK_QUESTION` module constant (or a `prompts/` entry) would centralize the copy.

**Fix:** consolidate into a single anti-slop fallback used by every surface, e.g. add to `src/vibemix/library/codex_curate.py`:

```python
# Plan 100 anti-slop fallback for the structurally-unreachable defensive
# case where a clarification payload propagates without a usable question
# (toolset validates pre-write — this fires only on side-channel corruption).
CLARIFICATION_FALLBACK_QUESTION = (
    "I need one more detail before I can build that — could you clarify?"
)
```

…and import it into CLI/Telegram/chat sites.

### IN-04: CLI re-run hint not shell-quote-safe when theme contains double quotes

**File:** `src/vibemix/__main__.py:2678, 2748`
**Issue:** The re-run hint interpolates `args.theme` (CLI argv) and `args.brief` (CLI argv) into a copy-pasteable shell command form:

```python
print(
    f'  Re-run with: library curate "{args.theme} + <chosen option>"',
    file=sys.stderr,
)
```

If `args.theme` contains a literal double quote (e.g. theme `peak-time "wave" mode`), the shell-pasteable command becomes:

```
  Re-run with: library curate "peak-time "wave" mode + <chosen option>"
```

…which is malformed shell quoting. A user who pastes it gets unexpected splitting. Also: theme containing a newline (LLM tool-call args trickling back through Codex echo) shifts the layout of the next stderr line.

Low severity — Codex is unlikely to surface a theme with embedded `"`, and the hint is human-readable regardless of shell-safety. But the executor could use `shlex.quote(args.theme)` to make the hint robustly pasteable:

**Fix:**

```python
import shlex
quoted_theme = shlex.quote(f"{args.theme} + <chosen option>")
print(f"  Re-run with: library curate {quoted_theme}", file=sys.stderr)
```

### IN-05: Validation reports only the FIRST error when both question and choices are invalid

**File:** `src/vibemix/library/toolset.py:1192-1229`
**Issue:** The handler validates question first; if question fails, choices are never inspected. If a Codex call has both `question=""` AND `choices=[]`, the LLM sees the question-error response, fixes the question, retries, then sees the choices-error response. Two round-trips for one fundamentally bad call.

The LibraryToolset's other handlers do single-error-at-a-time too (`search_vibe` checks `query` and exits; etc.), so this is consistent with house style. But a clarification-specific contract (Codex is the consumer; clear, complete validation feedback shortens the retry loop) might justify a richer multi-error response:

**Fix (optional, consistency-with-house-style argues against):** collect both errors and return one composite:

```python
errors = []
if not isinstance(question, str) or not question.strip():
    errors.append("'question' must be a non-empty string")
if not isinstance(choices, list):
    errors.append(f"'choices' must be a list of {MIN_CHOICES}-{MAX_CHOICES} non-empty strings")
elif len(choices) < MIN_CHOICES or len(choices) > MAX_CHOICES:
    errors.append(f"'choices' must contain {MIN_CHOICES}-{MAX_CHOICES} entries; got {len(choices)}")
else:
    for choice in choices:
        if not isinstance(choice, str) or not choice.strip():
            errors.append("every entry in 'choices' must be a non-empty string")
            break
if errors:
    return {
        "error": "request_clarification: " + "; ".join(errors),
        "rejected": True,
    }
```

Net Codex retry round-trips drop from up to 4 (one per error class) to 1. Trade-off: more complex handler; deviates from the single-issue-per-error pattern the rest of the toolset uses. Either choice is defensible — flagging for awareness, not blocking.

---

## Structural / Cross-File Verification

Confirmed by direct read (not re-listed as findings — clean):

1. **AST gate actually proves no-track-id surface** — `tests/library/test_request_clarification_no_track_surface.py::test_request_clarification_no_track_surface` walks `ast.Constant` nodes in the resolved FunctionDef; `args.get("track_id")` leaves `"track_id"` as a constant string. The gate's intersection check on FORBIDDEN_TRACK_ID_KEYS (`track_id`, `trackId`, `track-id`, `track_ids`, `trackIds`) catches every alias. Confirmed by inspecting `_walk_strings` (AST traversal looks right) and `_find_function_in_class` (top-level method lookup, no recursion into nested classes which could match a same-named helper falsely).
2. **AST gate also pins attribute chains** — `test_request_clarification_no_seen_mutation` walks dotted attribute chains via `_walk_attribute_chains`. A `self.seen.add("...")` call would leave a chain `self.seen.add` — the chain `startswith("self.seen.")` check catches it. The handler legitimately references `self.stop_reason` + `self._build_clarification_payload` + `self._write_side_channel` — none of those collide with FORBIDDEN_GROUNDING_ATTRS, so zero false positives on current source.
3. **AST gate confirms strict dispatch signature** — `test_request_clarification_signature_strict` pins `(self, args)` with no kwonly/vararg/kwarg. Handler matches. Defends Decision 1 (uniform dispatch contract).
4. **Telegram format_reply branch ordering correct** — clarification branch at `telegram_bridge.py:137` sits BEFORE the generic `if not norm.get("ok")` at line 145, so the clarification's `ok=False` doesn't shadow into the generic-error branch. Identical insertion-order discipline to Phase 99's tool_starvation branch (Plan 99-07 — verified pin in `99-REVIEW.md` structural verification #5).
5. **Telegram strip_leaks applied** — `format_reply` line 143 returns `strip_leaks("\n".join(lines))` for the clarification branch. Question + choices pass through the same `_PATH_RE` scrub the tool_starvation branch uses. Telegram test `test_format_reply_clarification_strips_leaks` confirms.
6. **CLI exit code distinct** — 11 (clarification_needed) vs 10 (tool_starvation) vs 1 (generic error) vs 0 (success). Phase 99 reserved range 10-19 for stop_reasons; Phase 100 lands at the next slot. Confirmed unique.
7. **stdout clean on clarification path** — `_cmd_library_curate_codex` returns 11 BEFORE the existing `_json.dumps(out, indent=2)` to stderr at line 2682, and never invokes the success-path `_json.dump(out, sys.stdout, indent=2)` at line 2700. stdout stays empty; test `test_curate_exits_11_on_clarification` pins `captured.out == ""`. Same on build-set path.
8. **Terminal short-circuit short-circuits clarification too** — `tests/library/test_toolset_clarification.py::test_dispatch_short_circuit_after_clarification` patches `search_vibe` with a RuntimeError sentinel and confirms `dispatch("search_vibe", ...)` returns the terminal echo without invoking it. Phase 99's short-circuit at line 1314 already returns `dict(self.stop_reason)` — discriminator-agnostic by construction.
9. **Side-channel writer reused unchanged** — `_write_side_channel` was widened in Phase 99 review fix (catches `OSError, TypeError, ValueError`). No change needed for Phase 100; the new payload is byte-equivalent to the starvation one for JSON-serialization purposes.
10. **MCP teaching docstring substring gates** — `test_request_clarification_docstring_teaches_codex` confirms docstring mentions "ambiguous" + at least one of {bpm range, context, mood register}. `test_docstring_mentions_choices_length_bound` confirms the 2-5 bound is documented. All gates green on current source (handler docstring at `mcp_server.py:232-257` has all three).
11. **Two-file gate on `def request_clarification(`** — `tests/repo/test_no_seen_relaxation.py::test_request_clarification_handler_two_file_pattern` pins ALLOWED to `{toolset.py, mcp_server.py}` only. A future copy-paste into agent/dj_cohost.py or runtime/wizard.py trips the gate.
12. **`MIN_CHOICES`/`MAX_CHOICES` re-exported in `__all__`** — `toolset.py:1514-1520` exports both. `test_choices_constants_re_exported` pins it. Decision 2 contract surface preserved for KAAN-ACTION ear-pass.
13. **Chat path also clears side-channel before out.json parse** — `chat_with_codex` at lines 1292-1333 reads side-channel first (matching Phase 99 posture), then falls through to out.json parse. Stops `request_clarification` from being shadowed by a stale Codex out.json.

---

_Reviewed: 2026-05-28_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
