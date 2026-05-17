---
phase: 40-anti-slop-audio-port
plan: 03
subsystem: audio
tags: [audio, lookahead, gemini-multimodal, anti-slop, prompt-engineering, kaan-spoke, tdd]

# Dependency graph
requires:
  - plan: 01
    provides: DJCoHostAgent.llm_node mic Part-2 attach point at dj_cohost.py:417 + mic_part_* event pattern
  - plan: 02
    provides: LookaheadProvider.snapshot_wav() per-session per-instance API + LOOKAHEAD_* constants
provides:
  - DJCoHostAgent ``lookahead`` kwarg + try/except-wrapped Part-3 attach in llm_node
  - 3-Part additive Gemini contract (text + P1 mix + P2 mic + P3 lookahead) per locked CONTEXT.md Q1
  - Part-aware prompt suffix builder ``vibemix.prompts.matrix.build_parts_description`` enforcing locked CONTEXT.md Q2 ("NOT YET HEARD BY AUDIENCE" + anti-prediction guard "do NOT describe Part [23] as if it has played")
  - lookahead_part_attached / lookahead_part_skipped recorder events mirroring the Plan 40-01 mic_part_* pair
  - Per-session LookaheadProvider lifecycle in __main__.py (title→path cache persists across the whole DJ session per RESEARCH OQ3)
affects:
  - 40-04-PLAN.md (cooldown re-tune — Part-count integration is now stable; cooldown changes won't affect Part assembly)
  - src/vibemix/prompts/__init__.py (re-exports build_parts_description)

# Tech tracking
tech-stack:
  added: []  # zero new deps — LookaheadProvider was Plan 40-02; prompt-suffix builder is pure-Python
  patterns:
    - "Pure prompt-suffix builder (locked-string lookup table by (has_mic, has_lookahead) boolean tuple) — extensible to future Part 4 without touching the agent's llm_node hot path"
    - "Double-belt exception safety on optional multimodal Part providers: (a) provider contract returns (None, meta), (b) agent try/except wraps the call site — neither layer alone is sufficient when the provider is community-extensible"
    - "Slot-renumbering on omitted Parts: when mic is absent, lookahead occupies the P2 slot rather than P3 — keeps the prompt-side label semantics tight (Gemini sees contiguous slot numbering)"

key-files:
  created:
    - "tests/agent/test_dj_cohost_3part.py (375 LOC) — 6 integration tests covering 4 Part-count scenarios + exception safety + recorder event surface"
    - "tests/prompts/test_matrix_3part_labeling.py (140 LOC) — 6 unit tests covering all 4 boolean permutations + anti-prediction phrase pin + v4 refrain carry-over"
    - "tests/audio/conftest fixture access (no new file — reused via tests.audio.conftest.int16_sine)"
  modified:
    - "src/vibemix/agent/dj_cohost.py — +50 / -25 LOC: lookahead kwarg + try/except snapshot block + build_parts_description delegation + Part 3 attach + lookahead_part_* events"
    - "src/vibemix/__main__.py — +20 / -1 LOC: LookaheadProvider import + instantiation + startup log + lookahead=lookahead_provider kwarg on DJCoHostAgent"
    - "src/vibemix/prompts/matrix.py — +117 LOC: build_parts_description function + section header + locked-strings documentation"
    - "src/vibemix/prompts/__init__.py — +2 LOC: re-export build_parts_description"

key-decisions:
  - "Honored locked CONTEXT.md Q1 (3-Part additive) over v4 actual code (2-Part silent-offset swap at cohost_v4_tr.py:1788). Plan 40-02's hand-off SUMMARY note suggesting silent-offset was deliberately overridden — CONTEXT.md is the locked source of truth per gsd-autonomous fully."
  - "Honored locked CONTEXT.md Q2 (explicit 'NOT YET HEARD BY AUDIENCE' labeling) — wired the label into a pure builder rather than inlining the f-string in llm_node, so the locked strings live in one place and can be grep-pinned by future verifier checks."
  - "Slot-renumbering when mic is absent (lookahead lives at P2 slot, not P3) — keeps the anti-prediction guard wording referring to the actual slot Gemini sees. The 4-way builder dispatches deterministically on (has_mic, has_lookahead) so the (P2 vs P3) label decision is encoded in one place, not split between llm_node and the prompt."
  - "Double-belt exception safety on lookahead.snapshot_wav() — Plan 40-02 guarantees (None, meta) on every observed failure path, but the agent's try/except wrapper adds belt-and-braces protection (T-40-03-02). This is the standard pattern for any future community-extensible multimodal Part provider."
  - "Event field schema for lookahead_part_attached carries the full provider meta dict (title, file, seek_sec, duration_sec, etc.) — coach-loop tails + Settings → Diagnostics can show the lookahead decision per turn without re-running the provider's introspection."

patterns-established:
  - "Pattern: pure prompt-suffix builder for multimodal Part-count dispatch — when adding a future 4th Part (e.g. structure-from-rekordbox metadata in v2.x), extend build_parts_description's boolean dispatch table; llm_node stays unchanged."
  - "Pattern: locked-strings live in builder, not call site — the verifier can grep for 'NOT YET HEARD BY AUDIENCE' in build_parts_description and pin the contract without parsing llm_node's hot path."

requirements-completed: [AUDIO-02, AUDIO-04]

# Metrics
duration: ~15 min
completed: 2026-05-16
---

# Phase 40 Plan 03: 3rd-Part Lookahead Wire-In + "NOT YET HEARD BY AUDIENCE" Labeling Summary

**Wires the LookaheadProvider (Plan 40-02) into the DJCoHostAgent's `llm_node` as the 3rd Gemini multimodal Part, with explicit "NOT YET HEARD BY AUDIENCE" prompt labeling per locked CONTEXT.md Q2 — closes the "AI reacts after the moment passed" AND the "AI claims to predict the future" hallucination classes simultaneously.**

## Performance

- **Duration:** ~15 min (4 commits: 2 RED, 2 GREEN)
- **Started:** 2026-05-16T15:00:00Z (approximate — wall-clock from worktree-merge to final commit)
- **Tasks:** 2 (each TDD: test → impl)
- **Files modified:** 4 (2 src + 1 src/init + __main__)
- **Files created:** 2 (one test per task)
- **LOC delta:** +632 / -26 (gross +606 net per src/test deltas above)

## 3-Part Contract Diagram

```
                    DJCoHostAgent.llm_node
                              │
                              ▼
        ┌──────────────────────────────────────────┐
        │  contents = [                            │
        │    text_prompt + build_parts_description(...)  │ ◄─ Part-aware prompt suffix
        │    Part(audio_wav,      "audio/wav"),    │ ◄─ Part 1 — ALWAYS (live BlackHole mix)
        │    Part(mic_wav,        "audio/wav"),    │ ◄─ Part 2 — iff Plan 40-01 mic gates (8s)
        │    Part(lookahead_wav,  "audio/wav"),    │ ◄─ Part 3 — iff LookaheadProvider returns bytes
        │  ]                                       │
        └──────────────────────────────────────────┘
```

### Conditional labeling rules

| Mic | Lookahead | Count | P1 slot | P2 slot          | P3 slot          | "NOT YET HEARD" label |
|-----|-----------|-------|---------|------------------|------------------|----------------------|
|  F  |     F     |   1   | mix     | (absent)         | (absent)         | NO                   |
|  F  |     T     |   2   | mix     | **lookahead**    | (absent)         | YES (on P2)          |
|  T  |     F     |   2   | mix     | mic              | (absent)         | NO                   |
|  T  |     T     |   3   | mix     | mic              | **lookahead**    | YES (on P3)          |

The lookahead Part **slot-renumbers** when mic is absent (occupies P2 rather than P3) so the prompt-side anti-prediction guard always references the correct slot number Gemini sees. The locked CONTEXT.md Q2 phrase `"do NOT describe Part [23] as if it has played"` is built dynamically per scenario.

## Accomplishments

- **3-Part additive contract end-to-end live.** When all three signals are present, Gemini now receives `[text, P1=live_mix, P2=mic, P3=lookahead]`. Locked decision Q1 honored over the v4 silent-offset swap pattern (the Plan 40-02 hand-off note suggesting silent offset was deliberately overridden per CONTEXT.md authority).
- **Locked Q2 labeling pinned by 2 test layers.** The `"NOT YET HEARD BY AUDIENCE"` substring + anti-prediction phrase `"do NOT describe Part [23] as if it has played"` are checked in `tests/prompts/test_matrix_3part_labeling.py` (unit) AND `tests/agent/test_dj_cohost_3part.py` (integration). A future verifier can `grep` the prompt for the locked label and the contract still holds.
- **Double-belt exception safety.** Plan 40-02 guaranteed `LookaheadProvider.snapshot_wav` returns `(None, meta)` on every failure path; this plan adds a `try/except Exception` wrapper in `llm_node` so even a misbehaving provider cannot crash the LLM hot path. Test `test_lookahead_exception_does_not_crash_llm_node` pins the contract — `RuntimeError("boom")` from `snapshot_wav` produces a 1-Part fallback + `lookahead_part_skipped` event with `reason` mentioning the exception.
- **Per-session lifecycle.** `LookaheadProvider()` instantiated once in `__main__.py` next to `clean_audio_buf` / `mic_audio_buf` — the title→path Spotlight cache + extrapolation-guard state live for the whole DJ session per RESEARCH Open Question 3 resolution.
- **Diagnostic surface uniform with mic Part.** The `lookahead_part_attached` / `lookahead_part_skipped` recorder events mirror the Plan 40-01 `mic_part_*` event pair shape — coach-loop tails + Settings → Diagnostics can render both pairs with one renderer. Attached event carries the full provider meta dict (`title`, `file`, `seek_sec`, `duration_sec`, etc.); skipped event carries the `reason` field from the provider's contract.
- **Startup log line announces the offset.** `-> lookahead: +3.0s @ 18s window (degrades silently on streaming tracks)` printed at boot — mirrors `cohost_v4_tr.py:2314`. The "degrades silently" wording warns Kaan that streaming-only sets won't trigger Part 3 (no Spotlight match → no file).

## Task Commits

1. **Task 1 RED: build_parts_description failing tests** — `14ad699` (test)
2. **Task 1 GREEN: build_parts_description + re-export** — `d241b3e` (feat)
3. **Task 2 RED: DJCoHostAgent Part 3 wiring failing tests** — `b8d90b7` (test)
4. **Task 2 GREEN: lookahead kwarg + try/except + Part 3 attach + __main__ wiring** — `4c4534e` (feat)

_TDD RED→GREEN cycle followed for both tasks. Each RED commit's test failure mode confirmed the implementation gap (ImportError for build_parts_description; TypeError for the new `lookahead` kwarg)._

## Files Created/Modified

### Created

- **`tests/prompts/test_matrix_3part_labeling.py`** (140 LOC) — 6 unit tests:
  - `test_1_part_baseline` — `(False, False)` returns 1-Part wording with no P2/P3/NOT-YET-HEARD.
  - `test_lookahead_only_at_p2` — `(False, True)` puts lookahead at P2 slot with "NOT YET HEARD BY AUDIENCE" + anti-prediction guard on Part 2.
  - `test_mic_only_at_p2` — `(True, False)` puts mic at P2; no NOT-YET-HEARD leakage.
  - `test_full_3part` — `(True, True)` puts mic at P2, lookahead at P3, both labels present.
  - `test_anti_prediction_phrase_in_lookahead_variants` — T-40-03-01 mitigation pin.
  - `test_ears_are_the_referee_in_all_variants` — v4 anti-slop refrain carry-over from Plan 40-01.

- **`tests/agent/test_dj_cohost_3part.py`** (375 LOC) — 6 integration tests:
  - `test_part_count_1_no_mic_no_lookahead` — backward-compat: both kwargs None → 1-Part.
  - `test_part_count_2_lookahead_only` — lookahead bytes mocked, mic None → 2-Part with NOT-YET-HEARD on P2.
  - `test_part_count_2_mic_only` — mic ring populated, lookahead returns None → 2-Part mic, no leak.
  - `test_part_count_3_mic_and_lookahead` — all three signals present → 3-Part full contract with P3 label.
  - `test_lookahead_exception_does_not_crash_llm_node` — T-40-03-02 mitigation pin (RuntimeError raised, fallback 1-Part + skipped event with reason).
  - `test_lookahead_part_attached_logs_event` — recorder event surface mirror for mic_part_*.

### Modified

- **`src/vibemix/agent/dj_cohost.py`** (+50 / -25 LOC):
  - New import: `build_parts_description` from `vibemix.prompts`.
  - `TYPE_CHECKING`: `LookaheadProvider` import added (no runtime cost when lookahead=None).
  - `__init__`: new kwargs-only `lookahead: "LookaheadProvider | None" = None` (default None preserves Phase 4/18/19/40-01 backward compat); stored as `self._lookahead`.
  - `llm_node` body change: AFTER the mic Part-2 attach block (was at line 417), added `lookahead_wav, lookahead_meta = self._lookahead.snapshot_wav()` inside `try/except Exception` — captures any provider misbehavior and falls back to `(None, {"reason": "exception: <e>"})`.
  - `llm_node` body change: REPLACED the hand-rolled 1-Part-vs-2-Part f-string suffix with a single delegating call to `build_parts_description(audio_seconds=float(audio_seconds), has_mic_part=mic_attached, has_lookahead_part=lookahead_attached)`. The locked Q2 string semantics now live in the builder, not the hot path.
  - `llm_node` body change: Added Part 3 conditional attach `if lookahead_attached: contents.append(types.Part.from_bytes(data=lookahead_wav, mime_type="audio/wav"))` after the mic Part attach block; matched recorder event pair `lookahead_part_attached` (with `bytes` + full provider meta) / `lookahead_part_skipped` (with `reason` from meta).

- **`src/vibemix/__main__.py`** (+20 / -1 LOC):
  - Imports: added `LOOKAHEAD_SECONDS`, `LOOKAHEAD_WINDOW_SECONDS`, `LookaheadProvider` from `vibemix.audio`.
  - Instantiation: `lookahead_provider = LookaheadProvider()` immediately after `mic_audio_buf = AudioBuffer(...)` (line ~458) — per-session lifecycle.
  - Startup log: `print(f"-> lookahead: +{LOOKAHEAD_SECONDS:.1f}s @ {LOOKAHEAD_WINDOW_SECONDS:.0f}s window (degrades silently on streaming tracks)")` mirrors cohost_v4_tr.py:2314.
  - Agent wiring: `lookahead=lookahead_provider` added to the `DJCoHostAgent(...)` constructor call kwargs.

- **`src/vibemix/prompts/matrix.py`** (+117 LOC):
  - New function `build_parts_description(audio_seconds, has_mic_part, has_lookahead_part) -> str` immediately before the `# Dispatcher` section header.
  - Locked strings (per CONTEXT.md Q2) embedded as the 4 deterministic return branches; anti-prediction guard `"do NOT describe Part [23] as if it has played"` rendered dynamically depending on which slot lookahead occupies.
  - 30-line section header documenting the 3-Part additive contract + slot semantics + locked decision references.

- **`src/vibemix/prompts/__init__.py`** (+2 LOC):
  - Added `build_parts_description` to the matrix-source import list AND the `__all__` tuple.

## Decisions Made

1. **Honored locked CONTEXT.md Q1 over v4 actual code.** v4 (cohost_v4_tr.py:1788) does a 2-Part SWAP — replaces Part 1 with the lookahead WAV. CONTEXT.md Q1 chose 3-Part ADDITIVE — keep Part 1 (audience perspective) AND append Part 3 (lookahead). The Plan 40-02 SUMMARY's hand-off note suggesting "silent latency masking, not future-audio labeling" was deliberately overridden — CONTEXT.md is the locked source of truth per `gsd-autonomous fully`. This is the central anti-slop trade-off: explicit labeling sacrifices a small amount of "natural-feeling" reaction timing in exchange for closing the "AI claims to predict the future" hallucination class entirely (T-40-03-01 mitigation).

2. **Locked Q2 strings live in a pure builder, not inlined.** The 4 possible suffix strings live in `build_parts_description`; `llm_node` calls it with a `(has_mic, has_lookahead)` tuple and appends the result. This means: (a) the verifier can `grep` `"NOT YET HEARD BY AUDIENCE"` in `src/vibemix/prompts/matrix.py` and pin the locked contract, (b) future Part-4 additions (v2.x — structure-from-rekordbox metadata?) extend the builder's dispatch table without touching `llm_node`'s hot path, (c) the prompt-suffix unit tests run in <50ms with zero `DJCoHostAgent` setup overhead.

3. **Slot-renumber when mic is absent.** When `(has_mic=False, has_lookahead=True)`, the lookahead WAV is the SECOND content element (after Part 1 mix) — so the prompt MUST label it as P2 (not P3). The alternative — leaving a "P2: (absent)" gap and labeling lookahead as P3 — would confuse Gemini's positional mental model. The builder enforces the slot-renumbering deterministically; the anti-prediction guard phrase is rendered with the correct number depending on the scenario.

4. **Double-belt exception safety on `snapshot_wav`.** Plan 40-02's `LookaheadProvider.snapshot_wav` already returns `(None, meta)` on every observed failure path (T-40-02-01 through T-40-02-04 — see Plan 40-02 SUMMARY). The agent's `try/except Exception` wrapper adds belt-and-braces protection for future provider variants that may raise rather than return (e.g. a community-contributed Spotify-API lookahead provider in v2.x). The test `test_lookahead_exception_does_not_crash_llm_node` pins this contract.

5. **Event field schema carries provider meta verbatim.** `lookahead_part_attached` emits the full provider meta dict (title, file, seek_sec, duration_sec, etc.) — coach-loop tails + Settings → Diagnostics show the lookahead decision per turn without re-running the provider. `lookahead_part_skipped` emits the `reason` field (`"no nowplaying"` / `"no file"` / `"ffmpeg rc=<n> ..."` / `"ffmpeg timeout"` / `"exception: ..."`) so the events.jsonl audit trail captures WHY the Part was omitted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] cohost_v4*.py symlinks for tests/test_main_smoke.py::test_smoke_06.**

- **Found during:** Task 2 GREEN regression sweep.
- **Issue:** `tests/test_main_smoke.py::test_smoke_06_poc_files_untouched_during_smoke` reads `cohost_v4.py` from the worktree root; the file is untracked in the repo (lives at the main project root only). On the original Plan 40-01 worktree this was a documented dev-env fix.
- **Fix:** Symlinked `cohost_v4.py` and `cohost_v4_tr.py` from the main project root into this worktree's root (`ln -sf ...`). Identical fix to Plan 40-01's Deviation #1 — local-dev only, NOT committed (the symlinks are local-filesystem state, untracked).
- **Files modified:** None tracked. Symlinks at worktree root: `cohost_v4.py → /Users/ozai/projects/dj-set-ai/cohost_v4.py`, `cohost_v4_tr.py → /Users/ozai/projects/dj-set-ai/cohost_v4_tr.py`.
- **Verification:** `test_smoke_06_poc_files_untouched_during_smoke` passes; the other smoke 03/04/05 failures are the SAME pre-existing fixture-drift failures documented in DEFERRED-40-01-02 — they reproduce identically WITHOUT my changes.

**No code deviations.** The plan's `<interfaces>` block specified everything needed; the locked Q2 strings (PLAN lines 122-127) ported verbatim into `build_parts_description`. The only nuance was: the PLAN's interface block reused the older `LookaheadProvider` 1-Part / 2-Part / 3-Part naming with lookahead at P3 in the 1-Part-plus-lookahead variant, but reading the locked CONTEXT.md Q2 carefully and the test surface specs (test_lookahead_only_at_p2 explicitly says "labeled `P2 =`"), the lookahead lands at P2 when mic is absent. Implemented per the test surface — the test names embed the locked decision.

---

**Total deviations:** 1 auto-fixed (local-dev infrastructure symlink fix, identical to Plan 40-01's). Zero code-deviations from the plan.
**Impact on plan:** None. The symlink fix is local-dev infrastructure (no committed code). All plan-specified behaviors implemented per spec.

## Issues Encountered

- **Pre-existing test failures on main (DEFERRED-40-01-02 / 04 + Phase 30 SENSE drift):**
  - `tests/test_main_smoke.py::test_smoke_03_full_wiring` — `AssertionError: assert 0 == 3` on `audio_mocks["find_device"].call_count`. Pre-existing.
  - `tests/test_main_smoke.py::test_smoke_04_no_openrouter_key` — same fixture-chain drift. Pre-existing.
  - `tests/test_main_smoke.py::test_smoke_05_cleanup_closes_all_streams` — same fixture-chain drift. Pre-existing.
  - `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — `SYSTEM_INSTRUCTION` drift from v4 baseline. Pre-existing (post-Phase-18 intentional persona evolution).
  - `tests/audio/test_constants.py::test_event_gap_dict_shape_and_values` — Phase 30 SENSE-17/18 keys missing from snapshot. Pre-existing.
  All five reproduce identically on `main` WITHOUT any Plan 40-03 changes. Documented in `deferred-items.md` per executor SCOPE BOUNDARY rule.

- **Stale LFS pointers in `tauri/ui/assets/mascot/*.glb` (21 files):** Worktree LFS resolution mismatch — pre-existing infrastructure issue (DEFERRED-40-01-01). Not relevant to audio code; will surface when Phase 43 mascot render rebuilds. Did NOT stage these in any of this plan's commits.

## User Setup Required

None — no external service configuration. All wiring is in-process (LookaheadProvider per-session instance + agent kwarg + prompt-suffix builder).

## Plan 40-04 Continuation Note

**Cooldown re-tune in `audio/constants.py` — Part-count integration is now stable; cooldown changes won't affect Part assembly.**

The 3-Part contract is fully decoupled from `MIN_EVENT_GAP_PER_TYPE` cooldown values. Plan 40-04 can re-tune cooldowns (PHASE 18→10s, LAYER_ARRIVAL 16→10s, MIX_MOVE 20→14s, HEARTBEAT 70→45s, TRACK_CHANGE 6→5s per CONTEXT.md decisions) without touching `dj_cohost.py` or `matrix.py`. The `EventDetector._cooldown_ok()` is the only consumer of those constants; the new Part-count assembly is invariant under cooldown changes.

The `build_parts_description` builder is also extension-ready for any future Part-4 (e.g. structure-from-rekordbox metadata, library-vibe lookup Part). Add a third boolean parameter, extend the dispatch table, and `llm_node` continues to delegate without modification.

## POC Immutability Gate (Phase 37-06)

```
$ git status cohost.py cohost_v2.py cohost_lk.py mascot.html
On branch worktree-agent-ad153306cd19a2b8d
nothing to commit, working tree clean
```

`cohost_v4.py` and `cohost_v4_tr.py` are not tracked in the repo; the worktree symlinks them locally for `test_smoke_06` access only — they are NOT committed. **POC immutability gate: PASS.**

## Self-Check: PASSED

- All four task commits exist in `git log`: `14ad699` (RED 1), `d241b3e` (GREEN 1), `b8d90b7` (RED 2), `4c4534e` (GREEN 2).
- All 4 created/modified files exist at the expected paths.
- Plan 40-03 verify suite green: `tests/prompts/test_matrix_3part_labeling.py` (6 passed) + `tests/agent/test_dj_cohost_3part.py` (6 passed) + `tests/agent/test_dj_cohost_mic_part.py` (6 passed) + `tests/agent/test_dj_cohost.py` (31 passed, no regression) = 49/49 in the verify-suite.
- Broader regression: `tests/agent/ tests/prompts/ tests/audio/` → 457 passed, 2 pre-existing failures (DEFERRED-40-01-04 + Phase 30 SENSE drift), zero new failures.
- `grep -c "self._lookahead" src/vibemix/agent/dj_cohost.py` = 5 (≥ 3) ✓
- `grep -c "lookahead_provider" src/vibemix/__main__.py` = 2 (= 2 required) ✓
- `grep -v '^#' src/vibemix/prompts/matrix.py | grep -c "NOT YET HEARD BY AUDIENCE"` = 3 (≥ 2 — appears in the 2 lookahead variants + once in the section-header comment block; the comment-stripping grep counts in-string occurrences only) ✓
- POC immutability gate: PASS (cohost.py / cohost_v2.py / cohost_lk.py / mascot.html clean).
- Locked Q2 phrase `"NOT YET HEARD BY AUDIENCE"` rendered correctly in the live 3-Part prompt: verified via `python -c "from vibemix.prompts.matrix import build_parts_description; print(build_parts_description(7, True, True))"` → contains the phrase.

---
*Phase: 40-anti-slop-audio-port*
*Completed: 2026-05-16*
