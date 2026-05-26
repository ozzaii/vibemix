---
phase: 80-ground-gemini-as-secondary-ear
plan: 02
subsystem: prompts / agent / llm / orchestrator
tags: [secondary-ear, gated-additive, byte-identity, citation-grounding, trust-the-audio, bench-alias, ground-01, ground-02]
requires:
  - phase: 80-ground-gemini-as-secondary-ear
    plan: 01
    provides: "the 2 xfail-strict guard scaffolds (flag-ON framing + un-backed-audio-claim strip) + the 2 real-green cold-path/router pins this plan flips/keeps"
provides:
  - "src/vibemix/prompts/matrix.py — gated `secondary_ear` framing extension to build_parts_description (default OFF = byte-identical; ON = 'secondary grounding signal' clause across all 4 branches)"
  - "src/vibemix/agent/dj_cohost.py — `secondary_ear` kwarg threaded into the build_parts_description call (Part-1 audio attach UNTOUCHED)"
  - "src/vibemix/__main__.py — VIBEMIX_GROUND_SECONDARY_EAR env read (default OFF) → secondary_ear kwarg + startup print"
  - "src/vibemix/llm/_router_config.py — live_coach documented as the Phase-81 bench-swap alias (comment only)"
  - "tests/agent/test_dj_cohost_ground_secondary.py — both Wave-0 guards flipped to real-green (4 passed / 0 xfailed)"
affects:
  - "Phase 81 (BENCH) — live_coach is now the documented config-alone reaction-model swap point; the gated secondary-ear path is bench-measurable (flag ON vs OFF)."
tech-stack:
  added: []
  patterns: [gated-additive-cold-path-byte-identity, four-kwarg-linter-wiring, config-resolved-model-no-literals]
key-files:
  created: []
  modified:
    - src/vibemix/prompts/matrix.py
    - src/vibemix/agent/dj_cohost.py
    - src/vibemix/__main__.py
    - src/vibemix/llm/_router_config.py
    - tests/agent/test_dj_cohost_ground_secondary.py
decisions:
  - "The framing clause is appended via a `base + secondary_clause` restructure (the 4 if-returns became if/elif assigning `base`, then a single return). Flag OFF → `secondary_clause` is the empty string → every branch byte-identical to v8.0 (verified: build_parts_description(...secondary_ear=False) == build_parts_description(...) across all 4 branches)."
  - "The Part-1 audio attach (dj_cohost.py:1511-1514) was left EXACTLY as-is — Part 1 is unconditional in v8.0; gating it was the #1 pitfall (breaks byte-identity). The flag gates ONLY parts_clause/contents[0] text, shared by both the genai + OpenRouter brain paths (no path-specific branch)."
  - "_router_config.py change is comment-only — no model literal introduced; the grep-gate (test_model_literal_gate.py) stays green in both task verifies."
  - "Removed the now-unused `import pytest` from the test file after flipping both xfail decorators off (the decorators were the only pytest reference)."
metrics:
  duration: ~6m
  tasks: 2
  files: 5
  completed: 2026-05-26
---

# Phase 80 Plan 02: GROUND Secondary-Ear Framing + Flag Thread Summary

Made the "Gemini as a secondary ear" contract deliberate, gated, and bench-measurable over the existing v8.0 machinery (the master audio was already Part 1, the model already resolves via `model_router`, the linter is already prompt/audio-blind). GROUND-01: a default-OFF `VIBEMIX_GROUND_SECONDARY_EAR` flag threads through to a gated `secondary_ear` framing clause in `build_parts_description` — flag OFF is byte-identical to v8.0, flag ON names the audio a *secondary grounding signal* with the structured evidence authoritative. GROUND-02: `live_coach` is documented as the Phase-81 bench-swap alias (the model already resolves via `resolve("live_coach")`, no literal). Both Wave-0 guard xfails flipped real-green, proving (via the un-backed-claim strip guard) that the audio Part can never widen the citable set.

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-26T01:56:01Z
- **Completed:** 2026-05-26T02:02:21Z
- **Tasks:** 2
- **Files modified:** 5

## What Was Built

**Task 1 — gated secondary-ear framing in `build_parts_description` (`matrix.py`):**
- Added a default-False `secondary_ear: bool = False` parameter (appended to the signature so every existing positional/keyword call site stays valid). Docstring documents the gated extension + the flag-OFF byte-identity guarantee.
- Restructured the body: the 4 `if ... return` branches became `if/elif` blocks assigning a per-branch `base` string, followed by a single `return base + secondary_clause`. `secondary_clause` is `""` unless `secondary_ear` is True, where it appends ` The live audio is a secondary grounding signal — the structured evidence above is authoritative; never claim an event the evidence does not list.` (mirrors the existing anti-prediction guard phrasing style).
- Pure function, stdlib only, no model literal, no new import. Verified byte-identity (`secondary_ear=False == default`) AND clause-presence (`"secondary grounding signal" in ...`) across all four `(has_mic_part, has_lookahead_part)` combinations. **No test scaffold flipped in Task 1** (deferred to Task 2 since both scaffolds drive `llm_node` with the not-yet-existing kwarg).

**Task 2 — thread the flag + flip both guards + document the bench alias:**
- `dj_cohost.py`: added `secondary_ear: bool = False` to `DJCoHostAgent.__init__` (next to `grounding`), stored `self._secondary_ear` (mirrors `self._recall_enabled`/`self._grounding`), and passed `secondary_ear=self._secondary_ear` into the `build_parts_description` call (`:1505-1509`). The `contents` Part-1 attach (`:1511-1514`) is **untouched** — Part 1 is unconditional.
- `__main__.py`: read `VIBEMIX_GROUND_SECONDARY_EAR` (default OFF, same `not in ("0","off","false","no","")` idiom as the recall read) next to the recall read; added a one-line `-> secondary-ear: ON|OFF (...)` startup print; passed `secondary_ear=ground_secondary_ear` to the `DJCoHostAgent(...)` construction next to `recall_enabled=recall_enabled`.
- `_router_config.py`: added a comment above the `"live_coach"` entry documenting it as the Phase-81 BENCH bench-swap alias (one-line config edit, resolves at `agent/config.py:25`). No literal tuple change.
- `test_dj_cohost_ground_secondary.py`: removed both `@pytest.mark.xfail(strict=True)` decorators (and the now-unused `import pytest`), updated the two docstrings from "fails today / xfail-strict" to "real-green as of Plan 02". `test_flag_on_audio_framed` (Part 1 survives + framing token in `contents[0]`) and `test_unbacked_audio_claim_strips` (all four non-None linter deps → `_linter_wired` True → the `[ev:PHANTOM_DROP@45.2]` reply strips the whole turn to nothing) both pass real-green.

## Live anchors used

- `dj_cohost.py:388-487` — `__init__` signature; `secondary_ear` added after `grounding`.
- `dj_cohost.py:591-592` — `self._grounding` storage block; `self._secondary_ear` stored adjacent.
- `dj_cohost.py:1505-1514` — the `build_parts_description` call + the unconditional Part-1 attach (the latter left exactly as-is).
- `dj_cohost.py:551-554` — `_linter_wired = all(... in (citation_linter, stripped_rate_tracker, playback))` — the four-kwarg construction shape the strip guard relies on (encoded in 80-01's test, unchanged here).
- `__main__.py:1035-1040` (recall read pattern) + `:1099-1100` (the `recall_enabled=` kwarg, where `secondary_ear=` was added).
- `_router_config.py:27` — the `live_coach` alias entry (comment added above it).

## Verification

- `PYTHONPATH=src python3 -m pytest tests/agent/test_dj_cohost_ground_secondary.py -q` → **4 passed, 0 xfailed** (both guards flipped; an `xpassed` would have been a HARD strict failure had either been left xfail).
- `PYTHONPATH=src python3 -m pytest tests/prompts/test_matrix_3part_labeling.py tests/agent/test_dj_cohost.py tests/repo/test_model_literal_gate.py -q` → all green (cold-path byte-identity + no literal introduced).
- Byte-identity asserted directly: `build_parts_description(60.0, m, l, secondary_ear=False) == build_parts_description(60.0, m, l)` for all 4 branches; `"secondary grounding signal" in build_parts_description(60.0, m, l, secondary_ear=True)` for all 4.
- `grep -rn "VIBEMIX_GROUND_SECONDARY_EAR" src/` → exactly one env read (`__main__.py:1041`-area); other matches are the startup-print string + doc comments.
- Full suite: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` → **4507 passed, 26 skipped, 1 xfailed, 4 xpassed** (241s, exit 0). The 1 xfailed = the pre-existing budget gate; the 4 xpassed = pre-existing live-only markers (wizard port-bind + macOS BlackHole kext). Plan-01 baseline was 4505 passed / 3 xfailed → **net +2 passes, −2 xfails** (the two flipped guards), zero new failures.
- Honest green: no `genai.Client` constructed, no `GEMINI_API_KEY` read, no network, no model literal inlined, no new package.

## Deviations from Plan

**1. [Rule 1 — Bug] Removed an unused import after flipping the xfails**
- **Found during:** Task 2
- **Issue:** After removing both `@pytest.mark.xfail` decorators, `import pytest` in `test_dj_cohost_ground_secondary.py` became unused (the decorators were its only reference) — a lint-grade dead import.
- **Fix:** Dropped the `import pytest` line.
- **Files modified:** tests/agent/test_dj_cohost_ground_secondary.py
- **Commit:** bdbe11b

Otherwise the plan executed exactly as written.

## Known Stubs

None. This plan is gated-additive wiring + framing over existing, tested machinery; no UI/data stubs introduced.

## Threat Flags

None. No new network endpoint, auth path, file-access pattern, or schema change. The only new surface is one local env-var read (validated to a bool, default OFF) and one key-free startup print — both covered by the plan's threat register (T-80-03 / T-80-04).

## Self-Check: PASSED

- `src/vibemix/prompts/matrix.py` — FOUND (gated `secondary_ear` kwarg present).
- `src/vibemix/agent/dj_cohost.py` — FOUND (`secondary_ear` kwarg + `self._secondary_ear` + threaded call).
- `src/vibemix/__main__.py` — FOUND (`VIBEMIX_GROUND_SECONDARY_EAR` read + `secondary_ear=` kwarg).
- `src/vibemix/llm/_router_config.py` — FOUND (bench-alias comment on `live_coach`).
- Commit `44d9594` (Task 1) — FOUND in git log.
- Commit `bdbe11b` (Task 2) — FOUND in git log.
