# Phase 100: HARDEN-CLARIFY — Viber RequestClarification Tool (Factor 7) - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Auto-resolved via `--auto` (default-YES on grey-area per `gsd-autonomous fully`). All gray areas auto-selected; each pick logged inline with rationale.

<domain>
## Phase Boundary

**From ROADMAP.md § Phase 100:** Close the Factor-7 partial from the 2026-05-28 humanlayer/12-factor-agents audit. When Codex sees an ambiguous theme ("uplifting" — for whom? bedroom-headphones or peak-time-club? 80 BPM ambient or 130 BPM driving?), instead of silently picking one heuristic, it calls a NEW `request_clarification(question, choices)` MCP tool. This terminates the run with `stop_reason="clarification_needed"` (sibling to Phase 99's `tool_starvation` — same side-channel propagation seam, same wrapper read posture). CLI prints the question + numbered choices and exits with code **11** (Phase 99 reserved this; distinct from `tool_starvation`'s exit 10). Telegram bridge renders the clarification as a chat message with numbered choices.

**Single-turn semantics:** the caller is responsible for re-invoking curation with the augmented theme. vibemix does NOT retain state across the clarification cycle. Codex is fully restarted on the next run. This is a Factor-7 right-pattern compromise: the LLM has a structured way to ask for human disambiguation without violating Factor-6 (we still don't have persistent durable pause/resume — that's HARDEN-FUTURE-01).

**Island scope:** `src/vibemix/library/toolset.py` (new handler) + `src/vibemix/library/mcp_server.py` (FastMCP exposure) + `src/vibemix/library/codex_curate.py` (parse-branch on stop_reason="clarification_needed") + `src/vibemix/library/telegram_bridge.py` (`format_reply` branch) + `src/vibemix/__main__.py:2545-2900` (CLI exit 11 branch, surgical addition to the existing dispatch already wired in Phase 99). Tests under `tests/library/`.

**Files explicitly NOT touched (disjointness contract):** `src/vibemix/agent/*`, `src/vibemix/__main__.py:1353` (LiveKit handoff), `src/vibemix/intel/*`, `tauri/ui/*`. Same parallel-session-tree discipline as Phase 99.

**Cardinal invariants (additively held):**
- **#1 single-writer (analog):** `request_clarification` handler writes to the SAME `self.stop_reason: dict | None` attribute Phase 99 introduced. The single-writer property holds because both terminal stop_reasons share one storage. The AST gate from Phase 99 (`tests/repo/test_no_seen_relaxation.py`) already pins the whitelist of files allowed to read/write `stop_reason` — Phase 100 stays within those 4 files (toolset.py write, codex_curate.py read, __main__.py read, telegram_bridge.py read).
- **#2 citation grounding:** `request_clarification` has NO `track_id` surface (AST-gated). A clarification cannot fabricate a track reference — it can only return a question + choices. Pinned by new `tests/library/test_request_clarification_no_track_surface.py`.
- **#3 trust the audio:** N/A (live co-host untouched).
- **#4 one socket:** N/A. No new ws traffic — CLI + MCP STDIO + Telegram long-poll only.

**Forward-compat with Phase 99:** Phase 100 IS the forward-compat exercise. The side-channel file format (`{"reason": "<discriminator>", ...}`) Phase 99 locked is the seam — Phase 100 sibling-extends with `reason="clarification_needed"` and adds `question: str` + `choices: list[str]` fields. Wrapper branches stay `if payload.get("reason") == "tool_starvation"` and add `elif payload.get("reason") == "clarification_needed"`.

</domain>

<decisions>
## Implementation Decisions (auto-resolved gray areas)

### Decision 1 — Handler signature

**Question:** What's the exact handler signature in `LibraryToolset`?

**Options considered:**
1. **(recommended)** `def request_clarification(self, args: dict[str, Any]) -> dict[str, Any]` — matches every other handler's signature in `library/toolset.py` (single `args` dict per dispatch convention).
2. Explicit kwargs: `def request_clarification(self, question: str, choices: list[str])` — breaks dispatch convention.

**[auto] Selected: Option 1 — `(self, args: dict[str, Any]) -> dict[str, Any]`.**

**Why:** Every other handler in `library/toolset.py:115-906` takes `args: dict`. Dispatch table at `toolset.py:982-1001` calls handlers uniformly. Breaking that for one tool fractures the dispatch contract.

### Decision 2 — Choices length validation

**Question:** How strictly are `choices` length-bounded?

**Options considered:**
1. **(recommended)** 2-5 inclusive: 0/1 rejected (no real disambiguation), 6+ rejected (choice paralysis). Hardcoded `MIN_CHOICES = 2`, `MAX_CHOICES = 5` module constants.
2. 2-10 (more flexible).
3. Unbounded.

**[auto] Selected: Option 1 — `MIN_CHOICES = 2`, `MAX_CHOICES = 5`.**

**Why:** REQ-CLARIFY-01 explicitly names 2-5 with rationale: "0/1 = no real disambiguation; 6+ = choice paralysis". The cognitive science consensus (Hick's law) supports 5±2; 5 is the upper bound on a single-turn LLM disambiguation. Module constants make these tunable for KAAN-ACTION ear-pass (§HARDEN-PHASE-B-CLARIFICATION-TONE).

### Decision 3 — Stop-reason payload shape

**Question:** What's the exact payload written via `self.stop_reason`?

**Options considered:**
1. **(recommended)** `{"reason": "clarification_needed", "question": "<str>", "choices": ["<str>", ...], "tool": "request_clarification"}` — discriminated-union with explicit `question` + `choices` fields.
2. Flat dict with all clarification data at top level (no `reason` field) — breaks Phase 99's branch shape.
3. Nested `payload: {question, choices}` — extra nesting for no benefit.

**[auto] Selected: Option 1 — discriminated-union with `reason` discriminator.**

**Why:** Phase 99's side-channel file shape is `{"reason": "<discriminator>", ...}` — Phase 100 sibling-extends. Wrapper branches stay `if payload.get("reason") == "tool_starvation": ...` and add `elif payload.get("reason") == "clarification_needed": ...` without restructuring (verified by Phase 99's plan-checker forward-compat audit).

### Decision 4 — Terminal short-circuit semantics

**Question:** After `request_clarification` fires, do subsequent dispatch calls become no-ops (like `tool_starvation` does)?

**Options considered:**
1. **(recommended)** Yes — same terminal idempotence as Phase 99. Reuse the existing short-circuit at `toolset.py:1078-1079`. Once `self.stop_reason is not None`, every dispatch returns the stop_reason payload without invoking the handler.
2. No — clarification is "soft terminal" (caller may proceed despite the request).

**[auto] Selected: Option 1 — terminal short-circuit, same as starvation.**

**Why:** Single-turn semantics (CONTEXT § domain) require the run END at clarification. Codex restart with augmented theme is the resolution. Mixing soft-and-hard terminal patterns within one stop_reason mechanism would fracture the contract Phase 99 locked. The wrapper restart by the user IS the multi-turn surface — vibemix stays single-turn-per-run.

### Decision 5 — CLI exit code

**Question:** CLI exit code for `clarification_needed`?

**Options considered:**
1. **(recommended)** Exit **11** — Phase 99 reserved 10-19 for stop_reasons. 10=tool_starvation, 11=clarification_needed. Future stop_reasons get 12-19.
2. Exit 10 (same as starvation).
3. Exit 1 (generic).

**[auto] Selected: Option 1 — exit 11.**

**Why:** CONTEXT.md (Phase 99 D-06) explicitly reserved 11 for `clarification_needed`. Scripts can distinguish "need user input" (11) from "library starved" (10) without parsing stdout.

### Decision 6 — CLI output format

**Question:** How does the CLI render the question + choices?

**Options considered:**
1. **(recommended)** Two-block stderr output: question on one line, then numbered choices (1-indexed) on separate lines, then a re-run hint suffix:
   ```
   [viber] clarification needed:
     <question>

     1. <choice 1>
     2. <choice 2>
     3. <choice 3>

     Re-run with: library curate "<theme> + <chosen option>"
   ```
   Stdout stays clean (no JSON envelope on this path — the run is terminal).
2. JSON envelope to stdout (machine-parseable).
3. Inline single-line "Q: ... A: <ch1> | <ch2>".

**[auto] Selected: Option 1 — two-block stderr with numbered choices + re-run hint.**

**Why:** Mirrors Phase 99's `tool_starvation` posture (hint to stderr, stdout reserved for the happy-path envelope). Numbered 1-indexed is the convention every shell user reads. The re-run hint closes the single-turn loop by telling the caller exactly how to resolve. Machine consumers can still parse stderr; JSON-to-stdout (option 2) would surprise the existing exit-10 contract.

### Decision 7 — Telegram rendering

**Question:** How does the Telegram bridge render the clarification in `format_reply`?

**Options considered:**
1. **(recommended)** Branch in `format_reply` rendering: header line with question, then numbered choices on separate lines, leak-stripped through `strip_leaks`. Telegram bot users reply with the choice number — but vibemix does NOT auto-resolve; the user composes the next theme manually (single-turn semantic). No buttons / inline keyboards.
2. Telegram inline-keyboard buttons (interactive choice).
3. Skip Telegram rendering (CLI-only).

**[auto] Selected: Option 1 — branch in `format_reply` with numbered choices.**

**Why:** Inline keyboards (option 2) require a state machine on the bot side to handle the callback — violates single-turn semantic + adds complexity for v1. Skipping Telegram (option 3) fails REQ-CLARIFY-05's "uniform across CLI and Telegram". Numbered-choices-in-text is consistent with the CLI surface and works without bot state.

### Decision 8 — Test seam parity

**Question:** Test posture for `request_clarification` handler + propagation?

**Options considered:**
1. **(recommended)** Mirror Phase 99: direct toolset unit tests for handler validation (`tests/library/test_toolset_clarification.py`) + side-channel propagation tests via existing `_runner` injection seam (`tests/library/test_codex_curate_stop_reason.py` extension) + CLI exit-code tests (`tests/library/test_cli_exit_codes.py` extension) + Telegram format_reply tests (`tests/library/test_telegram_bridge.py` extension).
2. New test files for each surface — duplicates Phase 99's posture for no benefit.

**[auto] Selected: Option 1 — extend Phase 99 test corpus + one new file for the toolset handler.**

**Why:** Maximum test seam reuse. The CLI exit-code dispatch + Telegram format_reply already have branches that need to grow by one — extending the existing test files (with new test_clarification_* methods) is cleaner than spawning parallel test files.

</decisions>

<code_context>
## Existing Code Insights (Phase 99 already wired the infrastructure)

**Files to touch:**

- `src/vibemix/library/toolset.py:982-1001` — `dispatch()` table. Add `"request_clarification": self.request_clarification` entry. The terminal short-circuit at line 1078-1079 already handles "subsequent dispatch returns stop_reason payload" — no change needed.
- `src/vibemix/library/toolset.py` — NEW `request_clarification` handler method. Mirrors `search_vibe(args)` signature posture.
- `src/vibemix/library/toolset.py` — NEW `_build_clarification_payload(question, choices)` private helper, mirroring `_build_starvation_payload(...)` from Phase 99 at line 998-1049.
- `src/vibemix/library/toolset.py` — counter logic UNCHANGED. `request_clarification` does NOT touch `_consecutive_empties` — it's a different terminal path (LLM-initiated, not counter-driven).
- `src/vibemix/library/mcp_server.py` — NEW `@mcp.tool() def request_clarification(question: str, choices: list[str]) -> dict[str, Any]` FastMCP-exposed handler. Delegates to `toolset.request_clarification({"question": question, "choices": choices})`.
- `src/vibemix/library/codex_curate.py:524-546` (curate path) + `:837-861` (build-set path) — ADD `elif payload.get("reason") == "clarification_needed":` branch alongside the existing `if payload.get("reason") == "tool_starvation":` branch. Populate `CodexCurateResult.stop_reason` = `"clarification_needed"`, store `question` + `choices` in error/payload fields.
- `src/vibemix/library/codex_curate.py` — `CodexCurateResult` and `CodexBuildSetResult` dataclasses may need new optional fields `question: str | None = None` + `choices: list[str] | None = None` (additive, default None preserves cold path).
- `src/vibemix/__main__.py:2545-2900` — CLI dispatch. ADD `elif result.stop_reason == "clarification_needed":` branch returning exit 11 with the 2-block stderr render. Mirror the structure of the existing exit-10 branch.
- `src/vibemix/__main__.py` `_normalize_codex_curate_result` helper — extend the normalized dict shape to carry `question` + `choices` for the Telegram surface.
- `src/vibemix/library/telegram_bridge.py:107 format_reply` — ADD `elif norm.get("stop_reason") == "clarification_needed":` branch rendering the numbered-choices message through `strip_leaks`.

**Files explicitly NOT touched:**
- `src/vibemix/agent/*`
- `src/vibemix/__main__.py` lines outside 2545-2900 (LiveKit handoff at ~1353 is parallel session)
- `tauri/ui/*`
- `src/vibemix/intel/*`
- `src/vibemix/library/create_playlist.py` (Invariant #2 protected — clarification handler has NO track_id surface anyway)

**Patterns to mirror:**
- Phase 99's `_build_starvation_payload` → `_build_clarification_payload`
- Phase 99's threshold-trip + `self.stop_reason = ...` write → `request_clarification` handler writes directly to `self.stop_reason` (no threshold gate — it's LLM-driven, single trip)
- Phase 99's CLI exit-10 dispatch branch → CLI exit-11 dispatch branch
- Phase 99's `_write_side_channel` is REUSED unchanged — it handles any payload shape because it just `json.dump`s the dict
- Phase 99's `format_reply` `tool_starvation` branch → `format_reply` `clarification_needed` branch

</code_context>

<specifics>
## Specific Ideas (locked at this phase)

- **`MIN_CHOICES = 2`, `MAX_CHOICES = 5`** module constants in `library/toolset.py`. Tunable for ear-pass.
- **`request_clarification(args)` handler** in `LibraryToolset`. Validates `args["question"]` is non-empty string + `args["choices"]` is list of 2-5 strings. Rejection returns `{"error": "...", "rejected": True}` (NO stop_reason write — invalid args don't terminate the run).
- **On valid args:** write `self.stop_reason = {"reason": "clarification_needed", "question": q, "choices": cs, "tool": "request_clarification"}`. Call `self._write_side_channel(self.stop_reason)` (REUSED from Phase 99). Return `{"clarification_needed": True, "question": q, "choices": cs}` so Codex sees its own call succeeded.
- **MCP tool docstring** teaches Codex: "Call this when the user theme is materially ambiguous and a single sensible default cannot be picked. Provide 2-5 specific choices that cover the disambiguation space. Examples: 'BPM range' (slow / mid / fast / mixed), 'context' (bedroom / club / festival), 'mood register' (chill / energetic / dark / euphoric)."
- **CLI exit code 11**. Mirror exit-10 dispatch pattern.
- **Telegram format**: leak-stripped multi-line message: question line, numbered choices, no buttons (single-turn).
- **No track_id surface AST gate** — new test `tests/library/test_request_clarification_no_track_surface.py` verifies the handler does NOT touch `self.seen` and does NOT validate any track_id.

</specifics>

<deferred>
## Deferred Ideas (captured, NOT in scope)

- **Inline-keyboard Telegram buttons** — multi-turn state machine on bot side. Deferred to HARDEN-FUTURE (multi-turn Viber state persistence).
- **Auto-restart with augmented theme** — CLI auto-retries with `<theme> + <chosen option>`. Deferred — violates single-turn contract + Codex restart is the resolution.
- **Open-ended free-text clarification** — `request_clarification(question)` without `choices`. Deferred — choices force the LLM to bound the disambiguation space, which is the whole Factor-7 point.
- **Clarification copy A/B testing** — KAAN-ACTION §HARDEN-PHASE-B-CLARIFICATION-TONE on funded-key ear-pass.

</deferred>
