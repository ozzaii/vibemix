---
phase: 41-gemini-sku-upgrade-latency-stack-v2
plan: 04
subsystem: agent/llm
tags: [LAT-04, LAT-05, streaming, tts-dsl, anti-slop, gemini-3.1-flash-tts]
requires: [41-01]
provides: [streaming-pipe-through, llm-to-tts-delta-meter, tts-tag-dsl]
affects: [agent/dj_cohost.py, prompts/matrix.py, agent/persona.py]
tech_stack_added:
  - vibemix.agent._streaming_pipe (bracket-depth-aware sentence boundary)
  - vibemix.runtime.llm_to_tts_delta_meter (LLMToTTSDeltaMeter)
  - vibemix.prompts.matrix.TTS_TAGS / TTS_TAG_DSL_BLOCK (6-tag DSL)
patterns:
  - dual-phase gate (head-fast speculative emit + trailing-slow full gate)
  - cancel-with-silence-pad on post-stream gate failure (Open Q2 auto-resolve)
  - bracket-depth state machine for citation-aware boundary detection (Pitfall 1)
  - triple opt-out pattern for v4 byte-identity callers (matches Plan 18-03 / 20-02)
key_files_created:
  - src/vibemix/agent/_streaming_pipe.py
  - src/vibemix/runtime/llm_to_tts_delta_meter.py
  - tests/agent/test_streaming_pipe_helpers.py
  - tests/runtime/test_llm_to_tts_delta_meter.py
  - tests/agent/test_dj_cohost_streaming_pipe.py
  - tests/llm/test_tts_3_1.py
  - tests/llm/cassettes/test_tts_3_1/README.md
  - docs/prompts/tts-tags.md
key_files_modified:
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/prompts/matrix.py
  - src/vibemix/agent/persona.py
  - tests/prompts/test_matrix.py
  - tests/agent/test_coach_mood_template.py
key_decisions:
  - bracket-depth state machine over regex for sentence-boundary detection (Pitfall 1)
  - MIN_HEAD_LEN=20 to skip Yo./Yeah./Dr. mis-fires (A4 mitigation)
  - head_gate slop subset = "AI tells" + "Slop framings" only (NOT "Empty hype" — those legit open replies)
  - cancel-with-silence-pad = 500ms zero-fill at 24kHz int16 (24000 bytes)
  - VCR cassette recording deferred to Kaan-action session (gsd-autonomous fully defer protocol)
  - 6 audio tags = whisper / laugh / fast / slow / excited / chill (curated subset of Gemini's 200+)
  - DSL block default-on for live coach; persona.SYSTEM_INSTRUCTION opts out via triple-opt-out
  - round() over int() in delta_ms to smooth sub-ms float-precision drift
metrics:
  duration_minutes: 90
  tasks_completed: 3
  files_created: 8
  files_modified: 5
  tests_added: 41
  regression_tests_passing: 191
  completion_utc: "2026-05-16T14:04:00Z"
---

# Phase 41 Plan 04: LLM→TTS Streaming Pipe-Through + Dual-Phase Gate + 3.1 Flash TTS Audio-Tag DSL Summary

**One-liner:** Refactored `DJCoHostAgent.llm_node` from buffer-then-yield to streaming sentence-boundary yield with a dual-phase gate (head emits speculatively, post-stream gate cancels-with-silence-pad on slop/citation_failure); shipped `LLMToTTSDeltaMeter` for perceived-latency telemetry; added 6-tag audio DSL surfaced via Gemini 3.1 Flash TTS (`live_coach_tts` router path).

## What shipped

### Task 1 — `_streaming_pipe` helpers + `LLMToTTSDeltaMeter` (commit `7c1709e`)

- **`vibemix.agent._streaming_pipe`**:
  - `find_sentence_end(text, start=0) -> int | None` — bracket-depth-aware state machine. Periods inside `[ev:kick@2.5]` citations at depth > 0 do NOT trigger boundaries (Pitfall 1 mitigation). Skips heads below `MIN_HEAD_LEN=20` to avoid Yo./Yeah./Dr. mis-fires (A4 mitigation).
  - `passes_head_gate(head) -> bool` — fast prefix check rejecting silence-token + slop-prefix subset (Generic AI tells + Slop framings; Empty hype excluded because legitimate openers like "killer drop" must pass).
  - `SENTENCE_BOUNDARY_CHARS = ".!?…"` covers ASCII + single-codepoint ellipsis (U+2026).
- **`vibemix.runtime.llm_to_tts_delta_meter`**:
  - `LLMToTTSDeltaMeter` mirrors `TTFTMeter` pattern: injectable `time_fn`, pending-pointer + record contract, no-pending no-op.
  - `delta_ms()` returns `int | None` via `round()` (smooths sub-ms float drift).
  - `log_turn(recorder, extra={})` emits `llm_to_tts_delta_ms` event with `{delta_ms, **extra}`. Head content NEVER logged (T-41-04-06 mitigation).
- **23 tests green:** 16 boundary/head-gate cases + 7 meter cases.

### Task 2 — `dj_cohost.llm_node` streaming refactor + dual-phase gate (commit `074198a`)

- **Refactor region marked with comment block:** `# === Plan 41-04 streaming pipe-through (LAT-04) ===` / `# === end Plan 41-04 streaming pipe-through ===` (lines 582-674 in current dj_cohost.py).
- **Streaming pipe state:** `accum` accumulates per-chunk text; `find_sentence_end` polls each chunk; `passes_head_gate` clears the speculative emit; `head_yielded` flag drives post-stream branching.
- **Trailing chunks** stream as-they-arrive after the head fires — no further boundary gating.
- **Post-stream cancel-with-silence-pad:** when `head_yielded=True` AND the post-stream gate fails (silence / slop / citation_failure), the agent pushes 500ms of zero-fill PCM (24kHz int16 mono = 24000 bytes) into the `PlaybackQueue` and emits a `streaming_cancel` event. Per Pitfall 8, if LiveKit cancellation is queued-not-immediate the head plays through (documented degrade — see code comment block).
- **All 4 post-stream branches gain `head_yielded` guards:**
  - **valid:** skip the buffered_chunks re-yield (head + trailing already in flight).
  - **invalid + bypass:** same skip.
  - **invalid + strip:** push silence-pad instead of ack-bank substitute (ack would overlap the head — worse than a clean pad).
  - **legacy emit:** same skip.
- **Meta.json gains `head_yielded` field** for invocation diagnostics.
- **`LLMToTTSDeltaMeter` wired:** `start_turn` in `set_next_event` (parallel to TTFT meter); `record_first_sentence` at the speculative-yield point; `log_turn` at end-of-method.
- **11 streaming-pipe tests + 105 DJCoHostAgent regression tests = 116 tests green.**

### Task 3 — Gemini 3.1 Flash TTS audio-tag DSL + docs (commit `5a69a09`)

- **`TTS_TAGS = ([whisper], [laugh], [fast], [slow], [excited], [chill])`** — curated 6-tag subset of Gemini's 200+ audio tags. Locked in `vibemix.prompts.matrix`.
- **`TTS_TAG_DSL_BLOCK`** — inline reference rendered into the system instruction. Each tag carries intent + example. The LLM emits the tag as the first inline token of its reply; Gemini 3.1 Flash TTS reads it at synthesis time.
- **`build_system_instruction(include_tag_dsl=True)`** default-on. The persona/byte-identity opt-out is now a triple (`include_citation_grammar=False, include_listening_fallback=False, include_tag_dsl=False`) — matches the Plan 18-03 / 20-02 pattern.
- **`docs/prompts/tts-tags.md`** — public-facing OSS DSL reference. Table + persona opt-in/opt-out + "real DJ friend" anti-slop principle + spec-source map.
- **15 mock-based contract tests + 86 matrix regression tests = 101 green** (1 skip on `test_unknown_tag_behavior_documented` — cassette-deferred).
- **Router contract pinned:** `resolve("live_coach_tts")` → `gemini-3.1-flash-tts-preview`; OpenRouter Achird OPUS fallback chain + legacy Gemini 2.5 Flash TTS fallback preserved (v4 IP intact).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree base sync from stale commit**
- **Found during:** Step 0 (mandatory pre-execution sync).
- **Issue:** Worktree HEAD was at `d7accba` (Phase 40 baseline); plan required `206389e` (after Phase 41-01 + 41-05 merged into local main). Remote `origin/main` matches the stale HEAD, but local `main` carries the up-to-date refs.
- **Fix:** `git merge main --no-edit` brought the worktree to `206389e`. ModelRouter + Phase 40 dj_cohost shape verified post-merge.
- **Commit:** Merge commit (no separate hash; merge integrated into the working state).

**2. [Rule 3 - Blocking] Float-precision in `delta_ms()`**
- **Found during:** Task 1 GREEN gate (`test_multiple_turns_reset_state` failed: `199 == 200`).
- **Issue:** `int((30.2 - 30.0) * 1000.0)` truncates to 199 due to IEEE 754 representation of 30.2.
- **Fix:** Swapped `int(...)` for `round(...)` — sub-ms drift smoothing matches the schema's int contract while keeping intuitive numbers.
- **Commit:** Included in `7c1709e`.

**3. [Rule 3 - Blocking] Plan 41-02 `cache_hit` block not yet shipped**
- **Found during:** Task 2 refactor.
- **Issue:** Plan 41-04 spec references "preserve Plan 41-02 cache_hit telemetry verbatim". Plan 41-02 has NOT merged to the worktree's base; the cache_hit block does not yet exist in dj_cohost.py.
- **Fix:** Skipped the `test_cache_hit_telemetry_preserved` test (it was a regression-against-future-state test, not a current-state assertion). The streaming refactor is purely additive — when 41-02 lands it will integrate via the existing `cache_state` dispatch (lines 497-523), which 41-04 did NOT touch.
- **Action item:** Plan 41-02 author should verify the streaming refactor (post-merge) preserves the per-chunk usage_metadata read path. The 41-04 stream loop reads `chunk.text`; adding a parallel `chunk.usage_metadata.cached_content_token_count` read is a 2-line addition with no structural conflict.

### Cassette Recording Deferred (Kaan-Action)

**Cassette test:** `tests/llm/test_tts_3_1.py::test_unknown_tag_behavior_documented`
- **Status:** Skipped — cassettes not yet recorded.
- **Why deferred:** Live `GEMINI_API_KEY` recording requires hands-on session. Per `gsd-autonomous fully` defer protocol, the mock-based unit tests fully cover the router-derivation + DSL-injection contract; the cassette test would additionally pin actual audio-response behavior for each tag (especially the unknown-tag pass-through-vs-strip behavior).
- **Recording command:**
  ```bash
  VCR_RECORD_MODE=new_episodes uv run pytest tests/llm/test_tts_3_1.py -v
  ```
- **Tracked in:** `tests/llm/cassettes/test_tts_3_1/README.md`.

## Pre-Refactor vs Post-Refactor LOC Delta

- **Pre-refactor streaming region:** lines 555-582 + 624-790 (citation linter chokepoint) ≈ 195 lines combined buffer-then-yield + gate pipeline.
- **Post-refactor streaming region:** lines 582-674 (Plan 41-04 block, comment-delimited) = 93 lines. The post-stream gate pipeline (lines after `# === end`) is untouched — only the wire-in branches gained `head_yielded` guards.
- **New module surface:** 170 lines (`_streaming_pipe.py`) + 105 lines (`llm_to_tts_delta_meter.py`) = 275 lines of net-new helper code.

## Measured First-Sentence Delta

**Pinning the synthetic baseline for Plan 41-07 CI gate is deferred** — the synthetic-session replay harness extension (`--print-llm-to-tts-delta` flag) is in Plan 41-07 scope. The meter is wired and emits events.jsonl rows; the harness needs to summarize them. For now, unit-test assertions confirm:

- Head yields BEFORE stream completes (asserted via mocker.AsyncMock chunk ordering — `test_first_sentence_streams_before_completion`).
- Per-turn meter resets correctly (`test_per_turn_meter_resets`).
- Delta payload is int ms with no head-content leak (T-41-04-06).

Real-DJ-clip measurement target per CONTEXT.md: 200-400ms perceived savings against the pre-refactor baseline of ~1-2s full-stream-duration. Plan 41-07 ratifies this.

## Pitfall 8 Observation

**No mid-utterance cancellation race observed in unit tests** — they exercise the cancel path via mock `playback.push` assertions, but the LiveKit OPUS encoder is not in the loop. The realistic degrade scenario (head finishes playing through to OPUS even after silence-pad pushes) is documented in the code comment block at `SILENCE_PAD_MS` and the cancel helper. Plan 41-07's synthetic replay or Phase 16 ear-test on real DJ clips will catch it if it surfaces — at which point the fallback semantics is "allow-truncate" (head plays through; silence-pad appends; no further audio).

## VCR Cassette Inventory

| Cassette | Path | Recorded? | Notes |
|----------|------|-----------|-------|
| (deferred) | `tests/llm/cassettes/test_tts_3_1/*.yaml` | No | Recording-mode command + steps in `README.md`. Run with real `GEMINI_API_KEY`. |

## Audio-Tag DSL — 6 Tags

| Tag | Status | Cassette-Confirmed? |
|-----|--------|---------------------|
| `[whisper]` | Documented + DSL-injected | No (deferred) |
| `[laugh]` | Documented + DSL-injected | No (deferred) |
| `[fast]` | Documented + DSL-injected | No (deferred) |
| `[slow]` | Documented + DSL-injected | No (deferred) |
| `[excited]` | Documented + DSL-injected | No (deferred) |
| `[chill]` | Documented + DSL-injected | No (deferred) |

The locked Gemini 3.1 Flash TTS release notes list these as supported; vibemix's curation chooses 6 of 200+ for DJ-coach intent coverage. Cassette confirmation of each tag's actual audio rendering is the Kaan-action recording step.

## Threat Flags

None — the refactor touches the existing `llm_node` trust boundaries (LLM stream + TTS pipeline + playback queue) but introduces no new network endpoints, auth paths, or schema changes at trust boundaries. All threats in the plan's `<threat_model>` block (T-41-04-01 through T-41-04-06) have mitigations wired:

- **T-41-04-01 (slop through head):** `passes_head_gate` runs the slop-PREFIX subset check synchronously; full slop filter runs post-stream.
- **T-41-04-02 (citation period mis-fire):** bracket-depth state machine in `find_sentence_end` + explicit `test_pitfall_1_citation_period_no_premature_yield` test.
- **T-41-04-03 (no-boundary DoS):** falls through to post-stream full-gate path (legacy behavior); no perceived latency win but no regression.
- **T-41-04-04 (LiveKit cancel race):** documented degrade — allow-truncate fallback noted at `SILENCE_PAD_MS` constant.
- **T-41-04-05 (persona injects bracket markup):** Gemini TTS handles unknown tags per cassette (deferred); no code-execution surface.
- **T-41-04-06 (meter logs head text):** `log_turn` schema is `{delta_ms, **extra}`; head text NEVER logged. `test_log_turn_payload_excludes_head_text` pins it.

## Deferred Issues

- **`tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`** — pre-existing failure (last modified at commit `28f5f09`, well before 41-04). The test reads `cohost_v4.py` via `Path("cohost_v4.py").read_text()`; the worktree doesn't have the POC reference file (gitignored / present only in Kaan's main checkout per `feedback_poc_is_reference`). Out of scope for 41-04. Tracked for future debt cleanup.
- **`tests/recording/test_phase15_success_criteria.py::test_default_retention_7d_prunes_old_session`** — pre-existing failure (last modified at commit `460e100`, well before 41-04). Out of scope.

## Self-Check: PASSED

**Created files exist:**
- `src/vibemix/agent/_streaming_pipe.py` ✓
- `src/vibemix/runtime/llm_to_tts_delta_meter.py` ✓
- `tests/agent/test_streaming_pipe_helpers.py` ✓
- `tests/runtime/test_llm_to_tts_delta_meter.py` ✓
- `tests/agent/test_dj_cohost_streaming_pipe.py` ✓
- `tests/llm/test_tts_3_1.py` ✓
- `tests/llm/cassettes/test_tts_3_1/README.md` ✓
- `docs/prompts/tts-tags.md` ✓

**Commits exist:**
- `7c1709e` — Task 1 ✓
- `074198a` — Task 2 ✓
- `5a69a09` — Task 3 ✓

**Verification:**
- Plan 41-04 test surface: 49 tests pass, 1 deferred skip.
- DJCoHostAgent regression: 105/105 tests pass.
- Matrix / coach mood byte-identity regression: 86 + 7 = 93/93 tests pass.
- Grep gate (Plan 41-01 CI): clean.
