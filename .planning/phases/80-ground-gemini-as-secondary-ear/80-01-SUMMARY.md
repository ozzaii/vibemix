---
phase: 80-ground-gemini-as-secondary-ear
plan: 01
subsystem: testing / agent / prompts / llm
tags: [tdd-scaffold, xfail-strict, byte-identity, secondary-ear, citation-grounding, nyquist-safety-net, ground-01, ground-02]
requires:
  - phase: 77-wire
    provides: "the Grounding/EvidenceRegistry seam + the linter chokepoint the audio-claim guard rides through"
provides:
  - "tests/agent/test_dj_cohost_ground_secondary.py — 2 real-green pins (flag-OFF cold-path byte-identity + GROUND-02 model-via-router) + 2 xfail-strict RED scaffolds (flag-ON framing + un-backed-audio-claim strip guard)"
  - "the four-kwarg linter-wiring contract encoded as the construction shape for the core hallucination guard (T-80-01)"
affects:
  - "Plan 02 (GROUND-01/02 implementation) flips both xfail-strict scaffolds to real-green: the secondary_ear kwarg + the 'secondary grounding signal' framing clause in build_parts_description"
tech-stack:
  added: []
  patterns: [pytest-xfail-strict, real-green-pin, cold-path-byte-identity, four-kwarg-linter-wiring]
key-files:
  created:
    - tests/agent/test_dj_cohost_ground_secondary.py
  modified: []
decisions:
  - "The flag-OFF byte-identity pin and the GROUND-02 router-resolve pin are REAL-GREEN guards (must keep passing through Plan 02), NOT xfail — they describe behavior true today; a strict-xfail would xpass→fail."
  - "The core guard (Test 4) is constructed with ALL FOUR non-None linter deps (citation_linter + stripped_rate_tracker + playback + evidence_registry). Omitting playback leaves _linter_wired False → the chokepoint is skipped → the guard silently never fires (verified against dj_cohost.py:551-554 + :1346)."
  - "Both RED scaffolds are keyed to the not-yet-existing secondary_ear kwarg, so they fail today with a clean TypeError on construction (verified via --runxfail) and flip to real green when Plan 02 threads the kwarg."
metrics:
  duration: ~5m
  tasks: 2
  files: 1
  completed: 2026-05-26
---

# Phase 80 Plan 01: GROUND Secondary-Ear Wave-0 Safety Net Summary

Installed the Nyquist safety net for "Gemini as a secondary ear" before any `src/` change: two `xfail(strict=True)` scaffolds that flip to real passes when Plan 02 lands the `secondary_ear` flag + framing, plus two real-green pins that lock today's cold-path request shape and the GROUND-02 router-resolve contract so a half-wired second ear cannot regress invariant #2 (citation grounding) or break v8.0 byte-identity.

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-26T01:47:43Z
- **Completed:** 2026-05-26T01:53:00Z
- **Tasks:** 2
- **Files modified:** 1 (created)

## What Was Built

**Task 1 — real-green pins (must KEEP passing through Plan 02):**
- `test_flag_off_byte_identical` — with the secondary-ear path OFF the reaction request is the v8.0 1-Part baseline: `contents` has exactly 2 entries (text packet + `types.Part` mix audio), `contents[0]` carries the v8.0 `"(audience perspective)"` label + the `"Your ears are the referee"` refrain, and does NOT yet contain the secondary-ear framing token (`"secondary grounding signal"`). This is the cold-path byte-identity pin.
- `test_model_via_router` — GROUND-02: `LLM_MODEL == resolve("live_coach")[0]` (the single resolution point at `agent/config.py:25`; no hardcoded literal on the reaction path). `live_coach` is the Phase-81 bench-swap alias.

**Task 2 — xfail-strict RED scaffolds (FAIL today, flip in Plan 02):**
- `test_flag_on_audio_framed` — flag ON: Part 1 survives (`audio/wav` / `b"RIFF"`) AND `contents[0]` now carries the `"secondary grounding signal"` framing token. Fails today (the `secondary_ear` kwarg + framing do not exist).
- `test_unbacked_audio_claim_strips` — **THE core guard (T-80-01).** Constructed with all FOUR non-None linter deps (`citation_linter` = real `CitationLinter`, `stripped_rate_tracker` = real `StrippedRateTracker`, `playback` = non-None mock, `evidence_registry` = real `EvidenceRegistry` seeded with a real library track but NOT `PHANTOM_DROP`). Precondition asserts `registry.has("ev","PHANTOM_DROP",45.2) is False`. The fake genai stream returns a reply citing `[ev:PHANTOM_DROP@45.2]` — an audio-derived claim for an event the DSP never detected — and the test asserts `llm_node` yields NOTHING (the whole turn strips to `<silence/>`). Proves the audio Part cannot widen the citable set: trust-the-audio (invariant #3) wins by construction.

## Live anchors verified before writing

- `dj_cohost.py:551-554` — `_linter_wired = all(x is not None for x in (citation_linter, stripped_rate_tracker, playback))`. The trio (NOT `evidence_registry`) flips the gate.
- `dj_cohost.py:1346` — `snapshot = self._registry.snapshot() if self._registry is not None else None` — `evidence_registry` is SEPARATELY required so the snapshot is non-None.
- `dj_cohost.py:1973-1976` — linter chokepoint; `lint_result.valid is False` → strip (no yield). `StrippedRateTracker.should_bypass()` returns False on a fresh tracker (`rate()==0.0`) so the strip path (not bypass) fires.
- `citation_linter.py:139-173` — a reply with a citation atom missing from the snapshot → `valid=False`, `reason="invalid_atoms"`.
- `agent/config.py:25` — `LLM_MODEL: str = resolve("live_coach")[0]`.
- `prompts/matrix.py:639-648` — the `"Your ears are the referee"` refrain + `"(audience perspective)"` label live in `build_parts_description`; `"secondary grounding signal"` is absent today (grep confirmed).

## Verification

- `PYTHONPATH=src python3 -m pytest tests/agent/test_dj_cohost_ground_secondary.py -k "flag_off_byte_identical or model_via_router" -x` → **2 passed**.
- `PYTHONPATH=src python3 -m pytest tests/agent/test_dj_cohost_ground_secondary.py -q` → **2 passed, 2 xfailed**, zero xpassed.
- `--runxfail` confirms both scaffolds fail for the RIGHT reason: `TypeError: DJCoHostAgent.__init__() got an unexpected keyword argument 'secondary_ear'` (not an unrelated error). When Plan 02 adds the kwarg, Test 4 proceeds past construction into the verified strip logic.
- Full suite: **4505 passed, 26 skipped, 3 xfailed, 4 xpassed** (244s, exit 0). The 3 xfailed = my 2 new + the pre-existing budget gate; the 4 xpassed are all pre-existing non-strict live-only markers (wizard port-bind + macOS BlackHole kext) unrelated to this plan. Baseline was 4501 passed / 1 xfailed; net +4 (the 2 new real-green pins + the 2 module xfails register as xfailed, not failures), zero new failures.
- Honest green: no `genai.Client`, no `GEMINI_API_KEY`, no network, no model literal, no new package. No `src/` change (Plan 02 owns the implementation).

## Deviations from Plan

None — plan executed exactly as written. The two real-green pins (Test 1, Test 2) and the two xfail-strict scaffolds (Test 3, Test 4) landed in the single planned file with the prescribed four-kwarg construction for the core guard.

## Known Stubs

None. This is a test-only Wave-0 plan; no UI/data stubs introduced.

## Self-Check: PASSED

- `tests/agent/test_dj_cohost_ground_secondary.py` — FOUND.
- Commit `26d2e28` — FOUND in git log.
