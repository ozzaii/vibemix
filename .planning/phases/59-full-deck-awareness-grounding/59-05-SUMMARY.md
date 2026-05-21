---
phase: 59-full-deck-awareness-grounding
plan: 05
subsystem: state
tags: [gemini-vision, deck-read, structured-output, eval-gated, anti-hallucination, camelot]

# Dependency graph
requires:
  - phase: 59-04
    provides: "DeckPoller source ladder with the source='screen_vision' slot scaffolded; DeckTrack model; harmonics.to_camelot writer-side normalization"
  - phase: 59-01
    provides: "DeckTrack/DeckState dataclasses; harmonics.to_camelot"
provides:
  - "DeckVisionReader — a SEPARATE structured-output Gemini deck-read (own prompt + JSON response_schema for {decks:[{side,title,key,bpm}]}, null-defensive parse, cadence debounce, below-XML confidence, graceful degradation)"
  - "GATED vision slot in DeckPoller (vision_enabled=False by default — conservative; consumes vision keys only post-eval)"
  - "eval/deck_vision/run_eval.py — real-screenshot accuracy eval harness + ACCURACY_FLOOR per-app enable gate (opt-in live path)"
  - "eval/deck_vision/README.md — KAAN-ACTION corpus instructions + the accuracy-floor gate definition"
affects: [phase-60-harmonic-firing, deck-state, key-citation, cross-deck-clash]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Separate structured-output Gemini call (response_mime_type=application/json + response_schema) for a grounded fact-read, OUTSIDE the de-screened reaction path"
    - "Eval-gated capability: a hallucination-risky leg ships dormant (vision_enabled=False) behind a real-corpus accuracy floor + KAAN-ACTION sign-off"
    - "null-defensive parse → confidence=0/unknown (no free-text guess); below-XML confidence so a misread can never out-cite a pre-analyzed tag"

key-files:
  created:
    - src/vibemix/state/deck_vision.py
    - tests/state/test_deck_vision.py
    - eval/deck_vision/run_eval.py
    - eval/deck_vision/README.md
  modified:
    - src/vibemix/state/deck_poller.py

key-decisions:
  - "Vision is a SEPARATE structured call — the reaction-path screen_jpeg=None v4 killswitch is UNTOUCHED (grep-asserted =1)"
  - "VISION_CONF=0.5 sits below deck_poller.XML_CONF_FLOOR (0.6) — a misread badge can never out-cite an XML tag"
  - "vision_enabled defaults False (conservative-by-design) — vision feeds deck-state only after the real-screenshot eval clears the per-app accuracy floor (KAAN-ACTION)"
  - "ACCURACY_FLOOR=0.90 starting bar; Kaan tunes/locks against measured real-rig numbers, mirroring eval/THRESHOLD-LOCK.md"

patterns-established:
  - "Eval-gated dormant capability: build + test + harness fully, ship OFF, flip only on signed real-corpus eval"
  - "Grounded vision-read as a constrained structured call (JSON schema + 'null if not legible'), never free-text re-attachment to the reaction turn"

requirements-completed: [DECK-02]

# Metrics
duration: 22min
completed: 2026-05-21
---

# Phase 59 Plan 05: Gemini-Vision Deck-Read Leg Summary

**A SEPARATE structured-output Gemini deck-read (`DeckVisionReader`) + a real-screenshot accuracy eval harness + a KAAN-ACTION accuracy-floor gate — the universal cross-app fallback leg of the source ladder, shipped DORMANT (vision_enabled=False) behind the eval so it can never feed a misread key until Kaan signs off the real-rig corpus.**

## Performance

- **Duration:** ~22 min
- **Completed:** 2026-05-21
- **Tasks:** 2 built + committed (Task 1 TDD, Task 2); Task 3 recorded as KAAN-ACTION (not blocked, per `gsd-autonomous fully`)
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- **`DeckVisionReader.read()`** — a dedicated, non-streaming `generate_content` call with `response_mime_type=application/json` + a `response_schema` for `{"decks":[{"side","title","key","bpm"}]}` and an explicit *"return null if a field is not clearly visible"* instruction. The constrained schema is what closes the free-text hallucination class that killed the original screen Part. Null/missing/junk fields → `None` → confidence=0/unknown (no guess); key normalized via `harmonics.to_camelot` (raw kept, camelot cited). Swallows all exceptions (TrackInfo.poll_once discipline) — never raises into the poller.
- **Cadence-bounded** — debounce gate (~7s default) refuses too-soon reads (returns last-known); audio-only tier skips the read entirely (cost/DoS bound). Never per-10Hz-tick.
- **Below-XML confidence** — `VISION_CONF=0.5 < XML_CONF_FLOOR=0.6` so a runtime badge misread can never out-cite a pre-analyzed XML tag.
- **GATED slot in DeckPoller** — `vision_reader` injectable + `vision_enabled` (default **False**). Vision-sourced keys are consumed ONLY when explicitly enabled (post-eval). While gated, the silent deck stays suppressed (Phase 60 clash uncitable) and the co-host runs XML-or-unknown — the safe state.
- **Eval harness** (`eval/deck_vision/run_eval.py`) — loads a corpus of real screenshots + hand-labeled ground-truth JSON, runs the read against each, reports per-app + overall title/key accuracy (Camelot-normalized, `null↔null` correct to reward honest abstention), and gates each app on `ACCURACY_FLOOR=0.90`. Live Gemini path is OPT-IN (injectable reader for tests) — NOT collected by the default fast suite.
- **README** documents the KAAN-ACTION corpus collection, ground-truth format, the accuracy-floor gate, and the "vision stays gated until eval passes" rule.

## Task Commits

1. **Task 1 (TDD RED): failing deck-vision tests** — `0302231` (test)
2. **Task 1 (TDD GREEN): DeckVisionReader + gated poller slot** — `e36d1ce` (feat)
3. **Task 2: eval harness + KAAN-ACTION README** — `55baa58` (feat)

**Plan metadata:** _(this commit)_ (docs: complete plan)

## Files Created/Modified

- `src/vibemix/state/deck_vision.py` — DeckVisionReader: separate structured-output Gemini deck-read, null-defensive parse, cadence debounce, VISION_CONF below XML floor, graceful degradation.
- `tests/state/test_deck_vision.py` — 15 mocked-client tests (happy path, null/missing/junk→unknown, raising/malformed/empty→graceful, debounce, audio-only skip, below-XML conf, Gemini-only). No live call.
- `src/vibemix/state/deck_poller.py` — GATED vision slot: injectable `vision_reader` + `vision_enabled=False` default; `_maybe_apply_vision` consumes vision only when enabled; never overwrites an XML-resolved deck.
- `eval/deck_vision/run_eval.py` — real-screenshot accuracy eval + ACCURACY_FLOOR per-app enable gate (opt-in live path).
- `eval/deck_vision/README.md` — KAAN-ACTION corpus instructions + accuracy-floor gate definition + "gated until eval passes" rule.

## Decisions Made

- Modeled the Gemini call on the in-repo `debrief/tldr.py` precedent (`client.models.generate_content` + `_extract_text` shape) and the `dj_cohost.py` `types.Part.from_bytes(image/jpeg)` + `GenerateContentConfig` patterns — reused, no new capture/encode path.
- `_DECK_READ_SCHEMA` kept as a plain dict (works with both `GenerateContentConfig(response_schema=...)` and dict-config; trivially inspectable in tests).
- A deck with nothing legible (no title AND no key) → confidence=0; a deck with at least a readable title → `VISION_CONF`. The poller's `_maybe_apply_vision` only fills a deck with `confidence > 0` and never overwrites a higher-confidence XML deck.

## Deviations from Plan

None — plan executed as written for Tasks 1 + 2.

One micro-adjustment (not a deviation): the GREEN docstring originally contained the literal `generate_content_stream` (in a "NOT the streaming path" clarification), which tripped the acceptance grep `grep -c "generate_content_stream" == 0`. Reworded the comment to "deliberately NOT the streaming reaction path" — same meaning, grep now returns 0. Caught + fixed within the Task-1 GREEN commit.

## Task 3 — KAAN-ACTION (recorded, NOT blocked)

Per `gsd-autonomous fully`, the Task 3 `checkpoint:human-verify` (vision deck-read accuracy eval gate) does **not** pause the workflow. The conservative-by-design state is shipped: **vision is GATED/OFF by default** (`DeckPoller(vision_enabled=False)`), so vision never feeds deck-state until the real-screenshot eval clears the floor. The reaction-path killswitch is untouched regardless.

**KAAN-ACTION (surfaced, not blocking):**
> Kaan must run `PYTHONPATH=src python3 eval/deck_vision/run_eval.py <corpus_dir>` against a corpus of his real djay Pro / Serato / Traktor screenshots (light + dark; silent/second-deck badge = RESEARCH Open Q1), per `eval/deck_vision/README.md`. Review the per-app accuracy report against `ACCURACY_FLOOR=0.90`. For each app that clears the floor → flip `DeckPoller(vision_enabled=True)` for it (vision-sourced keys at the below-XML `VISION_CONF`). Below-floor apps stay XML-or-unknown (vision dormant — conservative, not a failure). Record the per-app enable/gate outcome back here.

This is also appended to `deferred-items.md`.

## Issues Encountered

None. Full default suite: **7 failed, 3992 passed, 26 skipped** — the SAME 7 pre-existing `live-tuning-or-brain` WIP failures, unchanged count (passing rose 3976 → 3992 from this plan's 15 new mocked deck_vision tests + 1). None of the 7 reference `deck_vision` / `DeckVisionReader` / `VISION_CONF` (grep-verified empty). No new failures, no golden flips, no new orphans (orphan-diff clean — the two stale baseline entries left untouched).

## Verification

- `PYTHONPATH=src python3 -m pytest tests/state/test_deck_vision.py -x -q` → **15 passed** (mocked client).
- `grep -cE "^[[:space:]]+screen_jpeg = None$" src/vibemix/agent/dj_cohost.py` → **1** (reaction-path killswitch untouched).
- `grep -c "response_schema\|response_mime_type" src/vibemix/state/deck_vision.py` → **5** (structured output, not free text).
- `grep -c "generate_content_stream" src/vibemix/state/deck_vision.py` → **0** (separate non-reaction call).
- `grep -ci "openai\|anthropic\|claude" src/vibemix/state/deck_vision.py` → **0** (Gemini-only).
- `eval/deck_vision/run_eval.py` parses (`ast.parse`); README present; `grep -ci "accuracy floor" README.md` → **3**.
- Default fast suite collects NO test from `eval/` → no live Gemini call in the default path.

## Next Phase Readiness

- The DECK-02 source ladder is now structurally complete: XML primary → vision fallback (gated) → numpy last-resort (deferred). Phase 60's harmonic firing/clash detection can proceed on XML-resolved decks today; vision adds the silent-deck source signal once the KAAN-ACTION eval clears the floor.
- Blocker (non-blocking per autonomous mode): vision stays dormant until Kaan runs the eval and flips `vision_enabled` per app.

## Self-Check: PASSED

All 5 created/modified files exist on disk; all 3 task commits (`0302231`, `e36d1ce`, `55baa58`) present in git history.

---
*Phase: 59-full-deck-awareness-grounding*
*Completed: 2026-05-21*
