---
phase: 10-prompt-template-matrix
plan: 01
subsystem: prompts
tags: [prompts, anti-slop, matrix, persona, dj-cohost, silence-short-circuit, slop-filter, turn-history, scorecard, tdd]

requires:
  - phase: 04-livekit-cascade-agent-pivot
    provides: vibemix.agent.persona.SYSTEM_INSTRUCTION (v4-port, 8358 bytes), vibemix.agent.dj_cohost.DJCoHostAgent.llm_node hijack
  - phase: 03-sensing-state-port
    provides: vibemix.state.AICoach.build_prompt + vibemix.state.Event taxonomy (KAAN_SPOKE / MANUAL / TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE / HEARTBEAT)
provides:
  - vibemix.prompts subpackage with 6-cell matrix + dispatcher (build_system_instruction(skill, mode))
  - vibemix.prompts.matrix.{HYPE,COACH}_{BEGINNER,INTERMEDIATE,PRO} module-level constants
  - HYPE_INTERMEDIATE = byte-identical v4 SYSTEM_INSTRUCTION (8358 bytes); other 5 cells get the anti-slop substrate footer inline (anchor phrases + describe-before-infer + past-tense + literal <silence/> token + KAAN_SPOKE/MANUAL exception + 40-phrase ban list)
  - vibemix.prompts.negative_dict: 40 banned phrases (3 buckets — AI tells, empty hype, slop framings) + compiled NEGATIVE_REGEX (word-boundary + IGNORECASE)
  - vibemix.prompts.filter.filter_for_slop(text) → (filtered_or_<silence/>, [matches]) — passes-through clean text; word-boundary semantics
  - vibemix.prompts.turn_history.TurnHistory: thread-safe deque ring (max_pairs=12 default) with push_user/push_model/clear/__len__ and as_text() emitting <recent_turns>\n<user>...</user>\n<model>...</model>\n</recent_turns> format
  - vibemix.prompts.scorecard.summarize_session(events) → one of 4 qualitative bands (clean/decent/abrupt/train-wreck); never numeric
  - vibemix.agent.persona.SYSTEM_INSTRUCTION: thin re-export of HYPE_INTERMEDIATE (backward compat)
  - vibemix.agent.dj_cohost.DJCoHostAgent: env-var dispatch (VIBEMIX_SKILL_LEVEL + VIBEMIX_MODE) + llm_node buffer-then-flush silence/slop short-circuit
affects: [11-12 (Settings UI surfaces VIBEMIX_SKILL_LEVEL + VIBEMIX_MODE toggles), 14 (anti-slop polish — may rewrap HYPE_INTERMEDIATE with the substrate or relax suppress-whole-turn to in-place rewrite), 16 (hallucination verification gate consumes events.jsonl slop_suppressed + silence_short_circuit + coach_scorecard event types)]

tech-stack:
  added: []
  patterns:
    - "Thin re-export shim for backward-compat (vibemix.agent.persona.SYSTEM_INSTRUCTION → vibemix.prompts.matrix.HYPE_INTERMEDIATE), with import-time identity assert to catch dispatcher drift"
    - "Buffer-then-flush LLM streaming for post-hoc gating — accumulate full text, run silence + slop gate, yield iff clean (~1 LLM-stream-duration latency cost; Phase 14 may revisit)"
    - "Suppress-whole-turn slop strategy (cheaper, blunter) — Phase 14 may relax to in-place rewrite when prompt-engineering data justifies it"
    - "Substrate-as-footer pattern — 5 NEW cells share a hand-crafted anti-slop block appended to per-cell prose (preserves per-cell vocabulary anchoring)"
    - "Worst-band-wins reduction for multi-signal classification (slop count and abrupt-moves count both feed the band; max rank wins)"

key-files:
  created:
    - src/vibemix/prompts/__init__.py
    - src/vibemix/prompts/matrix.py
    - src/vibemix/prompts/negative_dict.py
    - src/vibemix/prompts/filter.py
    - src/vibemix/prompts/turn_history.py
    - src/vibemix/prompts/scorecard.py
    - tests/prompts/__init__.py
    - tests/prompts/test_matrix.py
    - tests/prompts/test_negative_dict.py
    - tests/prompts/test_filter.py
    - tests/prompts/test_turn_history.py
    - tests/prompts/test_scorecard.py
    - tests/agent/test_dj_cohost_matrix_dispatch.py
    - tests/agent/test_dj_cohost_silence_short_circuit.py
  modified:
    - src/vibemix/agent/persona.py (collapsed to thin re-export of vibemix.prompts.matrix.HYPE_INTERMEDIATE; import-time identity assert)
    - src/vibemix/agent/dj_cohost.py (env-var dispatch in __init__; llm_node now buffer-then-flush with silence + slop gate; per-invocation meta.json gains 'suppression' + 'slop_matches' fields)

key-decisions:
  - "HYPE_INTERMEDIATE = v4 verbatim (no substrate appended). The plan called for backward-compat byte-equality with the current persona.SYSTEM_INSTRUCTION; the v4 prompt already carries equivalent semantics in different phrasing (past tense, KAAN_SPOKE / MANUAL exception, 'react to what you HEAR', 'reply with silence'). Bans for HYPE_INTERMEDIATE fire post-hoc via filter_for_slop. Phase 14 may revisit with a unified substrate."
  - "Buffer-then-flush LLM streaming. To run filter_for_slop and the silence-token check on the FULL accumulated text, llm_node now buffers all chunks until the stream completes, then yields them in order iff both gates pass. Adds ~1 LLM-stream-duration of TTS-path latency (~1-2s for short replies); acceptable for v1, Phase 14 may revisit with progressive streaming if the latency cost shows in real DJ Coach feedback."
  - "Suppress-whole-turn (not in-place rewrite) for slop. Per CONTEXT §Filter post-processing — cheaper, blunter, can be relaxed in Phase 14 polish. Filter returns ('<silence/>', matches) to signal both suppression AND the matched phrases for telemetry."
  - "VIBEMIX_SKILL_LEVEL + VIBEMIX_MODE env vars (defaults intermediate / hype). Re-evaluated per DJCoHostAgent instantiation (no module-level caching) so unit tests can monkeypatch and Phase 11/12 Settings UI can hot-swap by re-instantiating the agent."
  - "Fail-loud env var validation. Unknown skill / mode raises ValueError (not silent fallback to intermediate/hype). Silent fallback would mask env-var typos; loud failure surfaces them at agent startup."
  - "TurnHistory format = <recent_turns>\\n<user>...</user>\\n<model>...</model>\\n</recent_turns>. Hand-crafted format (POC variants used types.Content objects rather than a wrapped string block); plan specified the wrapper shape. Empty ring → empty string (NOT a bare wrapper) so prompt builders can append conditionally."
  - "summarize_session is NEVER numeric — regex pin in test_scorecard_03 catches any '8/10' / '0.8' style score regression. Coach mode persists this at session end; Phase 16 verification consumes the qualitative band."
  - "silence_short_circuit events do NOT degrade the scorecard band. The LLM correctly emitting <silence/> means the prompt-substrate is working — those are well-behaved skips, not slop."

requirements-completed: [PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04, PROMPT-05, PROMPT-06]

duration: ~50min
completed: 2026-05-12
---

# Phase 10 Plan 01: Prompt Template Matrix + Anti-Slop Substrate Summary

**Shipped the entire 6-cell prompt-template matrix (3 skill levels × 2 modes), 40-phrase negative dictionary + word-boundary regex filter, TurnHistory ring (12-pair deque, byte-formatted `<recent_turns>` block), Coach scorecard (4 qualitative bands, never numeric), and wired env-var dispatch + buffer-then-flush silence/slop short-circuit into DJCoHostAgent.llm_node — preserving v4 SYSTEM_INSTRUCTION as byte-identical HYPE_INTERMEDIATE backward compat.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-05-12 (worktree spawn)
- **Completed:** 2026-05-12
- **Tasks:** 4/4 complete (Task 1 matrix+filter, Task 2 turn_history+scorecard, Task 3 dj_cohost wiring, Task 4 regression+SUMMARY)
- **Files created:** 14 (6 source modules + 1 package marker + 7 test files)
- **Files modified:** 2 (vibemix.agent.persona.py collapsed to re-export shim; vibemix.agent.dj_cohost.py gained env-var dispatch + silence/slop gate)
- **Test deltas:** 530 → 669 baseline (+139 new); wave-scope 158 tests (114 prompts + 25 new agent + 18 existing dj_cohost + 3 persona)

## Accomplishments

- **vibemix.prompts subpackage** with 6 prompt cells as module-level constants and `build_system_instruction(skill, mode)` dispatcher. HYPE_INTERMEDIATE is byte-identical (8358 bytes) to the previous Phase-4 v4-port `persona.SYSTEM_INSTRUCTION` — the existing dj_cohost (15 tests) and persona (`test_persona_01_resolves_as_str`, `test_persona_03_anti_hallucination_substrings_present`) tests stay green.
- **Other 5 prompt cells (HYPE_BEGINNER, HYPE_PRO, COACH_BEGINNER, COACH_INTERMEDIATE, COACH_PRO)** carry hand-crafted per-cell vocabulary anchoring (8 anchor phrases each, drawn from real DJ-friend / coach phrasings in the plan) PLUS the inline anti-slop substrate footer (describe-before-infer + past-tense + literal `<silence/>` instruction + KAAN_SPOKE/MANUAL always-reply exception + full 40-phrase ban list).
- **Negative dictionary** ships 40 phrases across 3 buckets: 16 generic AI tells (`as an AI`, `delve`, `leverage`, `synergy`, `robust`, `seamless`, ...), 16 empty hype words (`amazing`, `awesome`, `incredible`, `fantastic`, `love it`, `killing it`, `nailed it`, ...), 8 slop framings (`in this dynamic world`, `at the intersection of`, `navigate the landscape`, `unlock the potential`, ...). Compiled `NEGATIVE_REGEX` uses unicode `\b` word boundaries + `re.IGNORECASE` — `amazingly` does NOT trigger the `amazing` ban (boundary breaks).
- **filter_for_slop(text)** returns `("<silence/>", [matches])` on any banned-phrase hit; passes clean text through unchanged; recognises an existing `<silence/>` payload and returns `(<silence/>, [])` (no double-flagging).
- **TurnHistory class** is a thread-safe `__slots__` ring backed by `collections.deque(maxlen=max_pairs * 2)` (default `max_pairs=12`). `push_user` / `push_model` / `clear` / `__len__` / `as_text` — `as_text` emits the canonical `<recent_turns>\n<user>...</user>\n<model>...</model>\n</recent_turns>` block (byte-tested in `test_turn_history_10_format_byte_match`). Empty ring → empty string so prompt builders can append it conditionally.
- **summarize_session(events) -> str** returns one of `clean` / `decent` / `abrupt` / `train-wreck` — NEVER numeric (regex-pinned by `test_scorecard_03_never_numeric`). Counts `slop_suppressed` events and `MIX_MOVE` events flagged `extra={"abrupt": True}`; `silence_short_circuit` events do NOT degrade the band (well-behaved LLM skips). Worst-band-wins on combined inputs.
- **DJCoHostAgent env-var dispatch** — `__init__` reads `VIBEMIX_SKILL_LEVEL` + `VIBEMIX_MODE` (defaults `intermediate` / `hype`) and dispatches via `build_system_instruction(...)`. Both the LiveKit-side `instructions` arg AND the google.genai-side `GenerateContentConfig.system_instruction` get the resolved cell. Re-evaluated per instantiation (no caching) so Phase 11/12 Settings UI can hot-swap.
- **Buffer-then-flush silence + slop gate in llm_node** — accumulates the full LLM stream, then runs the silence-token check (stripped == `<silence/>` or starts-with) followed by `filter_for_slop` on the full accumulated text. Suppressed turns:
  - Yield NO chunks (no TTS playback).
  - Log `silence_short_circuit` (with response_chars + latency_s) or `slop_suppressed` (with matches list + response_chars + latency_s) to events.jsonl.
  - Do NOT pollute the v4 anti-repeat `_ai_text_history` deque.
  - Per-invocation meta.json still written, with `suppression` + `slop_matches` fields added to the v4 schema.
- **Backward-compat invariant preserved** — `vibemix.agent.persona.SYSTEM_INSTRUCTION` still resolves to the v4-port string body (now reached via `HYPE_INTERMEDIATE` re-export). Import-time `assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE` catches dispatcher drift at module-load time, not silently downstream.
- **POC files diff-untouched** — `git diff --name-only main..HEAD -- 'cohost*.py' 'run*.sh' mascot.html fillers/ cohost.streaming.py.bak` returns empty.
- **Wheel packaging verified** — `uv build --wheel && unzip -l dist/vibemix-*.whl | grep prompts/` confirms all 6 prompts modules ship in the wheel.

## Task Commits

Each task followed RED → GREEN TDD discipline (RED test commit first; GREEN feat commit second):

1. **Task 1: 6-cell matrix + negative dictionary + filter**
   - RED: `71bdb8b` (test) — initial RED tests for matrix + negative-dict + filter (3 test files)
   - RED-refine: `b0a7e79` (test) — refined matrix tests after discovering the byte-identical-to-v4 constraint forces HYPE_INTERMEDIATE to lack the inline substrate; introduced NEW_CELLS = ALL_CELLS \\ {("intermediate", "hype")}
   - GREEN: `95e6703` (feat) — vibemix.prompts.matrix + negative_dict + filter; 77 prompts tests pass; existing dj_cohost + persona tests stay green

2. **Task 2: TurnHistory ring + Coach scorecard**
   - RED: `977f1ea` (test) — 13 TurnHistory tests + 14 scorecard tests (37 collected with parametrization)
   - GREEN: `a885a58` (feat) — vibemix.prompts.turn_history.TurnHistory + vibemix.prompts.scorecard.summarize_session; all 37 tests pass

3. **Task 3: dj_cohost matrix dispatch + silence/slop short-circuit**
   - RED: `ed1c455` (test) — 10 dispatch tests + 15 silence/slop tests (25 total parametrized)
   - GREEN: `c46a3f7` (feat) — persona.py collapsed to re-export shim; dj_cohost.py llm_node now buffer-then-flush with silence + slop gate; 25 new tests pass; existing dj_cohost (15) + persona (2 of 3) tests stay green

4. **Task 4: Full-suite regression + SUMMARY**
   - Style: `88082af` (style) — ruff --fix (import sorting, slots ordering, unused-import removal) + replaced 5 ambiguous `×` (MULTIPLICATION SIGN) chars with ASCII `x` to clear RUF002/RUF003
   - Style: `1a8f5f5` (style) — ruff format pass (line wrapping cleanup)
   - This SUMMARY commit closes the wave

## Files Created/Modified

### Created (source — 6 modules + 1 package marker)

- `src/vibemix/prompts/__init__.py` — top-level subpackage; re-exports the 6 cells, `build_system_instruction`, `filter_for_slop`, `TurnHistory`, `summarize_session`, `NEGATIVE_PHRASES`, `NEGATIVE_REGEX`
- `src/vibemix/prompts/matrix.py` — 6 prompt cells + dispatcher (~415 lines, ~23 KB; HYPE_INTERMEDIATE alone is 8358 bytes of v4-verbatim body)
- `src/vibemix/prompts/negative_dict.py` — 40 banned phrases + `NEGATIVE_REGEX` (~80 lines)
- `src/vibemix/prompts/filter.py` — `filter_for_slop(text) -> tuple[str, list[str]]` (~45 lines)
- `src/vibemix/prompts/turn_history.py` — `TurnHistory` class with `__slots__` deque (~85 lines)
- `src/vibemix/prompts/scorecard.py` — `summarize_session(events) -> str` (~110 lines)

### Created (tests — 7 test files)

- `tests/prompts/__init__.py` — package marker
- `tests/prompts/test_matrix.py` — 35 tests (cell existence + uniqueness + dispatcher correctness + per-cell anchor phrases + shared substrate)
- `tests/prompts/test_negative_dict.py` — 9 tests (count + tuple + no-dupes + bucket coverage + regex compilation + case-insensitive matching + clean-text negative)
- `tests/prompts/test_filter.py` — 13 tests (suppression + clean pass-through + case-insensitive + word-boundary respect + multi-match collection + edge cases + per-bucket parametrization)
- `tests/prompts/test_turn_history.py` — 15 tests (construction + push semantics + ring overflow at default 12 + format byte-match + clear + empty-string + no-XML-escape edge cases)
- `tests/prompts/test_scorecard.py` — 19 tests (empty + return-type invariants + never-numeric + slop band thresholds + abrupt-mix-move band thresholds + worst-band-wins + silence_short_circuit doesn't degrade + unrelated-events ignored)
- `tests/agent/test_dj_cohost_matrix_dispatch.py` — 16 tests (defaults + explicit env-var dispatch + case-insensitive + gen_cfg system_instruction matches + invalid env raises + privacy check + per-instantiation re-read)
- `tests/agent/test_dj_cohost_silence_short_circuit.py` — 11 tests (silence-only suppression + silence event logged + history not polluted + whitespace padding + meta.json updated + slop suppression + slop event with matches + clean pass-through + slop history not polluted + chunked-silence buffering)

### Modified (source)

- `src/vibemix/agent/persona.py` — collapsed from 70-line v4-verbatim string-body to a 30-line thin re-export of `vibemix.prompts.matrix.HYPE_INTERMEDIATE`; import-time `assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE` pins identity
- `src/vibemix/agent/dj_cohost.py` — `__init__` now resolves the prompt cell via `_resolve_prompt_cell()` (reads `VIBEMIX_SKILL_LEVEL` + `VIBEMIX_MODE`, defaults `intermediate` / `hype`); `llm_node` accumulates the LLM stream into a buffer, runs the silence + slop gate, yields chunks iff clean; meta.json schema gains `suppression` + `slop_matches` fields. v4:1502 anti-hallucination single-modality comment + `screen_jpeg = None` gate preserved verbatim per CLAUDE.md load-bearing-IP rule.

## Decisions Made

1. **HYPE_INTERMEDIATE = v4 verbatim (no substrate appended).** Plan tension: matrix tests required every cell to contain the literal `<silence/>` token + literal "describe what you HEAR" phrase + inline ban list, BUT the orchestrator-level constraint required HYPE_INTERMEDIATE to be byte-identical to current `persona.SYSTEM_INSTRUCTION` (= v4 port). Resolution: HYPE_INTERMEDIATE stays byte-identical (8358 bytes) to v4; the substrate-presence test exempts it (`NEW_CELLS` parametrization excludes it) AND a separate test asserts HYPE_INTERMEDIATE carries equivalent semantics in v4's phrasing (past tense ✓, KAAN_SPOKE ✓, MANUAL ✓, "React to what you HEAR" ✓, "reply with silence" ✓). The post-hoc filter still fires for HYPE_INTERMEDIATE — bans are enforced at runtime via `filter_for_slop`, not inline in the v4 prompt prose. Phase 14 polish may rewrap HYPE_INTERMEDIATE with the unified substrate after Coach feedback validates it doesn't degrade Kaan's tuned v4 IP.

2. **Buffer-then-flush LLM streaming.** Phase 4 yielded chunks immediately as they arrived from the LLM. Phase 10 needs to run `filter_for_slop` on the FULL accumulated text — partial chunks could miss multi-token banned phrases (`"in this dynamic world"`). Same for the `<silence/>` token (could arrive split across chunks like `<sil` + `ence/>` per `test_silence_06`). Resolution: accumulate all chunks into a buffer, run gates on full text, then yield buffered chunks in order iff both gates pass. Cost: ~1 LLM-stream-duration latency added to the TTS path (~1-2s for short replies). Acceptable for v1; Phase 14 may revisit with progressive streaming if Coach feedback flags it.

3. **Suppress-whole-turn (not in-place rewrite) on slop.** Per CONTEXT §Filter post-processing — "suppress whole turn is the v1 approach; relax to in-place rewrite in Phase 14 polish". Cheaper, blunter, more recoverable. `filter_for_slop` returns `("<silence/>", matches)` to signal BOTH suppression AND the matched phrases for telemetry/Coach scorecard.

4. **Fail-loud env-var validation.** Unknown `VIBEMIX_SKILL_LEVEL` or `VIBEMIX_MODE` → `ValueError` at agent startup, not silent fallback to defaults. Silent fallback would mask env-var typos; loud failure surfaces them when the user runs `./run_v4.sh` and sees the traceback.

5. **TurnHistory format hand-crafted from plan, not POC.** The POC `TurnHistory` (`cohost.py:635`) used `types.Content` objects rather than a wrapped string block. The plan specifies the `<recent_turns>\\n<user>...</user>\\n<model>...</model>\\n</recent_turns>` format explicitly. Implemented per plan; empty ring returns empty string (NOT a bare wrapper) so prompt builders can append it conditionally.

6. **scorecard's `silence_short_circuit` doesn't degrade band.** Slip judgement: 50 well-behaved silences = the LLM correctly skipped 50 turns. Counting them as slop would discourage the prompt's `<silence/>` instruction. `test_scorecard_13_silence_short_circuit_does_not_count_as_slop` pins this.

7. **Worst-band-wins reduction.** When slop count says "decent" and abrupt-moves count says "train-wreck", the band is "train-wreck" (the user wants to know the worst signal, not an averaged blur). `test_scorecard_12_worst_band_wins` pins this.

8. **Substrate-as-footer (not header).** The 5 NEW cells start with the per-cell prose (anchor phrases + register-specific guidance) and END with the shared substrate. Reasoning: per-cell prose contains the per-register language model the LLM should match; trailing substrate functions as the "do not violate these rules" reminder closer to where the actual generation begins. No measured A/B yet — this is a v1 ordering hypothesis Phase 14 may flip.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong test parametrization at substrate-presence assertion**

- **Found during:** Task 1 GREEN — first test run of `test_prompt_01_each_cell_has_silence_token` parametrized over `ALL_CELLS` (which includes `("intermediate", "hype")`).
- **Issue:** HYPE_INTERMEDIATE is byte-identical to v4, which doesn't contain the literal `<silence/>` token (it says "reply with silence" in prose). The test asserted `<silence/>` in HYPE_INTERMEDIATE → fail.
- **Fix:** Refactored the parametrization: `NEW_CELLS = ALL_CELLS \\ {("intermediate", "hype")}` for substrate-presence tests; added a separate `test_prompt_01_hype_intermediate_carries_equivalent_substrate` that asserts the v4-equivalent phrasings (past tense, KAAN_SPOKE/MANUAL, "React to what you HEAR", "reply with silence") are present. Documented in the cell-block docstring above the constant.
- **Files modified:** `tests/prompts/test_matrix.py`
- **Committed in:** `b0a7e79` (RED-refine)

**2. [Rule 1 - Bug] Off-by-one substring match in `test_turn_history_09`**

- **Found during:** Task 2 GREEN — first run of `test_turn_history_09_overflow_at_default_12` failed with "u1 in out" but the test author meant "literal u1 turn (not u10/u11/u12/u13 substrings)".
- **Issue:** `assert "u1" not in out` matched `u10`, `u11`, `u12`, `u13` substrings (all retained in the ring after 14-pair push at default cap 12 → only u0 + u1 evicted).
- **Fix:** Changed to full-tag substring check: `assert "<user>u0</user>" not in out` etc. — the `<user>uN</user>` framing makes substring boundaries unambiguous.
- **Files modified:** `tests/prompts/test_turn_history.py`
- **Committed in:** `a885a58` (Task 2 GREEN — bundled with TurnHistory+scorecard impl)

**3. [Rule 3 - Blocking] Stub turn_history.py + scorecard.py needed before matrix.py could import-test**

- **Found during:** Task 1 GREEN — running `uv run python -c "from vibemix.prompts.matrix import HYPE_INTERMEDIATE"` failed because `vibemix.prompts.__init__` re-exports `summarize_session` and `TurnHistory` (which Task 2 implements).
- **Fix:** Added stub `turn_history.py` and `scorecard.py` raising `NotImplementedError` so the package imports during Task 1; Task 2 replaced them with the real implementations.
- **Files modified:** `src/vibemix/prompts/turn_history.py`, `src/vibemix/prompts/scorecard.py` (initially as stubs in Task 1; replaced with full impl in Task 2)
- **Committed in:** `95e6703` (stubs in Task 1 GREEN); `a885a58` (replacements in Task 2 GREEN)

**4. [Rule 3 - Blocking] ruff RUF002/RUF003 on `×` (MULTIPLICATION SIGN) chars**

- **Found during:** Task 4 — `uv run ruff check` flagged 5 ambiguous unicode chars in docstrings/comments.
- **Fix:** Replaced all 5 `×` chars with ASCII `x` (semantic-equivalent in "3 skill levels x 2 modes" context).
- **Files modified:** `src/vibemix/agent/persona.py`, `src/vibemix/prompts/__init__.py`, `src/vibemix/prompts/matrix.py`, `src/vibemix/prompts/turn_history.py`, `tests/prompts/test_matrix.py`
- **Committed in:** `88082af` (style)

## Authentication Gates

None.

## Test Results

- **Wave-scope tests:** 158 collected (114 in `tests/prompts/`, 25 new in `tests/agent/test_dj_cohost_matrix_dispatch.py` + `test_dj_cohost_silence_short_circuit.py`, 18 existing in `tests/agent/test_dj_cohost.py`, 3 in `tests/agent/test_persona.py`); 157 pass (the only failure is the pre-existing `test_persona_02_byte_identical_to_v4` — POC absent in worktree, see Out-of-Scope below)
- **Full suite:** 669 passed, 1 skipped (`test_main_live` — opt-in live audio), 5 warnings (HMAC key length in tests/agent/test_jwt_cache.py — Phase 5 baseline, not Wave 1)
- **Test deltas:** 530 baseline → 669 (+139 new tests added by Wave 1)
- **Backward-compat invariants:**
  - `vibemix.agent.persona.SYSTEM_INSTRUCTION` resolves to a string of 8358 bytes (verified: `len(SYSTEM_INSTRUCTION) == len(HYPE_INTERMEDIATE) == 8358`)
  - `SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE` (import-time assert in persona.py)
  - `test_persona_01_resolves_as_str` ✓
  - `test_persona_03_anti_hallucination_substrings_present` ✓ (all 6 invariant substrings still present)
  - All 15 existing `test_dj_cohost.py` tests stay green (LLM_NODE-01..11 + AGENT-01..04)

## Out-of-Scope (Not Fixed)

Three pre-existing test failures in this worktree environment, unrelated to Wave 1:

1. **`tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`** — depends on `cohost_v4.py` at repo root; POC files don't live in worktrees by design (per Phase 9 09-01 SUMMARY). Pre-existing failure on the merge-base; reproduces identically before any Wave-1 commits.
2. **`tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke`** — same root cause (POC files not present in worktree).
3. **`tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device`** — depends on a CoreAudio device named "Headphones"; this worktree environment has different audio devices. Live-hardware smoke test, environment-dependent.

These are out of scope per the GSD scope-boundary rule (only auto-fix issues directly caused by the current task's changes). All three reproduce identically on the pre-Wave-1 merge-base.

Tracking these as **deferred items** — they don't block 10-02 (PROMPT-07 reaction throttle) or downstream phases. Same status as Phase 9.

## Verification Checklist

- [x] `uv run pytest tests/prompts/ tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_matrix_dispatch.py tests/agent/test_dj_cohost_silence_short_circuit.py tests/agent/test_persona.py -q` — 157/158 (only pre-existing test_persona_02 fails)
- [x] Full suite (minus 3 pre-existing baseline failures) — 669 green
- [x] `uv run ruff check src/ tests/` — clean (0 errors)
- [x] `uv run ruff format --check src/ tests/` — clean (115/115 already formatted)
- [x] `python -c "from vibemix.prompts import build_system_instruction, filter_for_slop, TurnHistory, summarize_session, NEGATIVE_PHRASES, NEGATIVE_REGEX"` exits 0
- [x] `python -c "from vibemix.prompts.matrix import HYPE_INTERMEDIATE; from vibemix.agent.persona import SYSTEM_INSTRUCTION; assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE; assert len(SYSTEM_INSTRUCTION) == 8358"` exits 0
- [x] `grep -r "phrase ended on the 3" src/vibemix/prompts/matrix.py` returns COACH_PRO anchor (1 hit)
- [x] `grep -c "amazing" src/vibemix/prompts/negative_dict.py` returns ≥1 (in NEGATIVE_PHRASES)
- [x] `grep -c "<silence/>" src/vibemix/prompts/matrix.py` returns ≥5 (one per NEW cell)
- [x] `grep -rn "VIBEMIX_SKILL_LEVEL\|VIBEMIX_MODE" src/vibemix/agent/dj_cohost.py | wc -l` returns ≥2 (env-var reads)
- [x] POC files diff-untouched: `git diff --name-only main..HEAD -- 'cohost*.py' 'run*.sh' mascot.html fillers/ cohost.streaming.py.bak` empty
- [x] Wheel packaging: `uv build --wheel && unzip -l dist/vibemix-*.whl | grep prompts/ | wc -l` returns 6 (all 6 prompts modules ship)

## Self-Check: PASSED

All claimed source files exist:

- `src/vibemix/prompts/__init__.py` ✓
- `src/vibemix/prompts/matrix.py` ✓
- `src/vibemix/prompts/negative_dict.py` ✓
- `src/vibemix/prompts/filter.py` ✓
- `src/vibemix/prompts/turn_history.py` ✓
- `src/vibemix/prompts/scorecard.py` ✓

All claimed test files exist:

- `tests/prompts/__init__.py` ✓
- `tests/prompts/test_matrix.py` ✓
- `tests/prompts/test_negative_dict.py` ✓
- `tests/prompts/test_filter.py` ✓
- `tests/prompts/test_turn_history.py` ✓
- `tests/prompts/test_scorecard.py` ✓
- `tests/agent/test_dj_cohost_matrix_dispatch.py` ✓
- `tests/agent/test_dj_cohost_silence_short_circuit.py` ✓

All claimed commits exist on the worktree branch:

- `71bdb8b` (Task 1 RED initial) ✓
- `b0a7e79` (Task 1 RED-refine) ✓
- `95e6703` (Task 1 GREEN) ✓
- `977f1ea` (Task 2 RED) ✓
- `a885a58` (Task 2 GREEN) ✓
- `ed1c455` (Task 3 RED) ✓
- `c46a3f7` (Task 3 GREEN) ✓
- `88082af` (style ruff fix) ✓
- `1a8f5f5` (style ruff format) ✓

## Hand-Off to 10-02

Plan 10-02 (PROMPT-07 — reaction throttle, global cap on top of Phase 3 per-event-type cooldown) picks up:

- Add global `MIN_INTER_EVENT_GAP_SEC=8.0` cap to `vibemix.state.event_detector.EventDetector` on top of the existing per-type cooldowns.
- TurnHistory wiring into `dj_cohost.llm_node` (Phase 10 ships the class but doesn't yet inject `<recent_turns>` block into the prompt — Wave 1 left this to a follow-up so the LLM-side anti-repeat clause stays unchanged in Wave 1; Wave 1's dj_cohost still uses the v4 `_ai_text_history` deque inlined in the prompt body).
- Coach scorecard emission at session-end via a new `events.jsonl` `coach_scorecard` event — needs a session-end hook in `vibemix.runtime.session_runner` (or the Phase 4 main entry) to call `summarize_session` on the accumulated events.
