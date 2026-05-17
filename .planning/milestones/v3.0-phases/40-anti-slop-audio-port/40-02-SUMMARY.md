---
phase: 40-anti-slop-audio-port
plan: 02
subsystem: audio
tags: [audio, lookahead, ffmpeg, nowplaying, mdfind, anti-slop, gemini-multimodal, tdd, poc-port]
requires: [01]  # Wave 1 cooldown re-tune lands first; no functional dependency, only sequencing
provides: [LookaheadProvider, LOOKAHEAD_SECONDS, LOOKAHEAD_WINDOW_SECONDS, LOOKAHEAD_SAMPLE_RATE, LOOKAHEAD_TIMEOUT_S]
affects: [src/vibemix/audio/__init__.py]
tech_stack:
  added: []  # zero new pip deps — ffmpeg / nowplaying-cli / mdfind already verified in environment
  patterns:
    - "input-seek ffmpeg invocation (`-ss` BEFORE `-i`) for sub-300ms wall-clock per 18s extract"
    - "subprocess list-form argv (V10 Malicious Code mitigation; never shell=True)"
    - "graceful-degrade contract: every failure path returns (None, meta_with_reason) — never raises to caller"
    - "per-instance title→path cache for the duration of a session (None cached too)"
    - "title-change extrapolation guard for nowplaying-cli (Pitfall 2 defense)"
key_files:
  created:
    - src/vibemix/audio/lookahead.py
    - tests/audio/test_lookahead.py
    - tests/audio/fixtures/test_lookahead_track.mp3
    - .planning/phases/40-anti-slop-audio-port/deferred-items.md
  modified:
    - src/vibemix/audio/__init__.py  # +5 re-exports
decisions:
  - "Module constants live in lookahead.py (not audio/constants.py) per CONTEXT §Claude's Discretion"
  - "Provider is per-session — instantiate in __main__.py alongside clean_audio_buf; pass into DJCoHostAgent kwargs"
  - "`-f wav` (not `-f s16le`) per RESEARCH Open Question 3 — matches existing snapshot_wav format"
  - "Fixture mp3 checked in (40KB) + auto-regenerated via conftest if absent — hermetic CI on Linux runners without ffmpeg"
metrics:
  duration_minutes: 12
  completed_at: 2026-05-16
  tests_added: 8
  loc_added: 605
---

# Phase 40 Plan 02: LookaheadProvider Port Summary

Three-second file-based lookahead window for anti-slop temporal grounding. Verbatim port of `cohost_v4_tr.py:624-770` `LookaheadProvider` into `src/vibemix/audio/lookahead.py` with package-convention adaptations (typing, sys.stderr logging, module-level docstring).

## What Shipped

| Artifact | Lines | Purpose |
|---|---:|---|
| `src/vibemix/audio/lookahead.py` | 294 | `LookaheadProvider` class + 4 module constants + 3 private helpers |
| `tests/audio/test_lookahead.py` | 311 | 8 unit tests: 1 happy + 4 graceful-degrade + 2 security/correctness + 1 extrapolation-guard |
| `tests/audio/fixtures/test_lookahead_track.mp3` | (40KB binary) | 5s 440Hz sine fixture for happy-path; auto-regenerable via conftest |
| `src/vibemix/audio/__init__.py` | +12 | Re-exports `LookaheadProvider` and 4 LOOKAHEAD_* constants |

## Pipeline Implemented

1. **`_poll_raw()`** — `nowplaying-cli get-raw` → JSON dict; drops `*art*` fields (album-cover blob); returns `None` on any subprocess / parse failure.
2. **`_resolve_file(title)`** — `mdfind -name <title>` → best-matching `.mp3 / .m4a / .aiff / .aif / .wav / .flac / .ogg / .aac` path. Match ranking: exact stem → substring → first-by-mdfind-order. Per-title cache (including `None` for streaming-only titles).
3. **`_current_position()`** — Returns `(title, elapsed_sec, playback_rate)`. Extrapolation guard: on same-title-same-elapsed across consecutive polls, extrapolate by `wall_delta * rate`. On **title change**, ALWAYS return fresh elapsed (no extrapolation — Pitfall 2 defense).
4. **`snapshot_wav()`** — Computes `end_file_sec = pos + lookahead*rate`, seeks `max(0, end - window)`, decodes `max(0.5, end - seek)` seconds via `ffmpeg -ss <seek> -i <path> -t <duration> -ac 1 -ar 16000 -f wav`. Returns `(wav_bytes, meta)` on success or `(None, meta)` on every failure path (`"no nowplaying"`, `"no file"`, `"ffmpeg rc=<n> <stderr>"`, `"ffmpeg timeout"`, `"ffmpeg exc: <e>"`).

## Module Constants

| Constant | Value | Anchor |
|---|---:|---|
| `LOOKAHEAD_SECONDS` | `3.0` | `cohost_v4_tr.py:150` — LLM+TTS latency offset |
| `LOOKAHEAD_WINDOW_SECONDS` | `18.0` | `cohost_v4_tr.py:151` — 15s past + 3s future |
| `LOOKAHEAD_SAMPLE_RATE` | `INPUT_SR_TARGET` (`16000`) | `cohost_v4_tr.py:152` — matches Part-1 audio_wav rate |
| `LOOKAHEAD_TIMEOUT_S` | `4.0` | ffmpeg wall-clock ceiling — Pitfall 4 malformed-file defense |

## Test Coverage

```
tests/audio/test_lookahead.py::test_snapshot_wav_happy_path PASSED
tests/audio/test_lookahead.py::test_no_nowplaying_returns_none PASSED
tests/audio/test_lookahead.py::test_no_file_match_returns_none PASSED
tests/audio/test_lookahead.py::test_ffmpeg_error_returns_none PASSED
tests/audio/test_lookahead.py::test_subprocess_timeout_returns_none PASSED
tests/audio/test_lookahead.py::test_subprocess_args_use_list_form PASSED
tests/audio/test_lookahead.py::test_input_seek_before_dash_i PASSED
tests/audio/test_lookahead.py::test_extrapolation_guard_on_title_change PASSED

============================== 8 passed in 0.03s ===============================
```

The plan asked for 7 tests; we shipped 8 — the extra is the explicit Pitfall 2 extrapolation-guard test, pinning load-bearing IP. The plan's `<done>` line "7 tests pass total" is exceeded, not missed.

**Hermetic guarantee:** no test body fires a real `nowplaying-cli` / `mdfind` / `ffmpeg` subprocess. The fixture-gen step in `conftest.py` is the only ffmpeg call and it skips cleanly on hosts without ffmpeg.

**No-regression sweep:** `pytest tests/audio/ --deselect <Phase-30-stale-test>` → 66 passed, 0 regressions. See `deferred-items.md::DEFERRED-40-02-01` for the pre-existing Phase 30 test debt — unrelated to this plan.

## TDD Gate Compliance

| Phase | Commit | Tests |
|---|---|---|
| RED  | `37c0e10` `test(40-02): add failing tests for LookaheadProvider` | 8 tests collected, all fail on `ImportError: cannot import name 'LOOKAHEAD_SAMPLE_RATE'` |
| GREEN | `1282b4b` `feat(40-02): port LookaheadProvider for 3s anti-slop lookahead window` | 8/8 pass |
| REFACTOR | (omitted) | Port is already idiomatic — no cleanup pass needed; v4_tr-verbatim semantics preserved |

Gate sequence: ✓ RED before GREEN, ✓ GREEN commit type is `feat(...)`, ✓ tests transitioned red→green within a single GREEN commit.

## Security Gates (Threat Register Mitigations)

| Threat | Test | Status |
|---|---|---|
| T-40-02-01 Tampering — mdfind shell injection via track title | `test_subprocess_args_use_list_form` | ✓ pinned |
| T-40-02-02 DoS — ffmpeg on malformed input | `test_subprocess_timeout_returns_none` | ✓ pinned |
| T-40-02-03 Tampering — ffmpeg moov-atom-not-found | `test_ffmpeg_error_returns_none` | ✓ pinned |
| T-40-02-04 Spoofing — nowplaying-cli other-app spoof | `test_extrapolation_guard_on_title_change` | ✓ pinned |
| T-40-02-05 Info Disclosure — file paths in meta dict | (accepted in threat model — paths only in per-session events.jsonl, gitignored) | ✓ accepted |

## Deviations from Plan

**None.** Plan executed verbatim per `<tasks>` + `<verify>` + `<done>` blocks. The one nuance:

- Plan said "7 tests pass total"; we shipped 8 (the extra is `test_extrapolation_guard_on_title_change`, explicitly enumerated in plan task 2 `<behavior>` but counted as task-2's 6th test there — depending on counting it's either 6+1 or 7 — we counted as 8 standalone tests for the final report).

## POC Immutability (Phase 37-06 Gate)

`git status cohost.py cohost_v2.py cohost_lk.py mascot.html` → working tree clean. `cohost_v4_tr.py` is not present in the worktree (it's a Kaan-machine-local reference). Immutability gate satisfied trivially.

## Plan 40-03 Hand-off Note

**`LookaheadProvider` is per-session.** In Plan 40-03, instantiate the provider in `src/vibemix/__main__.py` next to `clean_audio_buf` and pass it into `DJCoHostAgent(..., lookahead=lookahead_provider)`. The agent's `llm_node` then calls `lookahead_wav, meta = self._lookahead.snapshot_wav()` and conditionally appends a third `types.Part.from_bytes(data=lookahead_wav, mime_type="audio/wav")` when `lookahead_wav is not None`. **Do not log the AI about the offset** — v4:1788 anti-slop principle: silent latency masking, not "future-audio" labeling.

## Commits

| Hash | Type | Summary |
|---|---|---|
| `37c0e10` | test | RED gate — 8 failing tests for LookaheadProvider |
| `1282b4b` | feat | GREEN — port LookaheadProvider verbatim from cohost_v4_tr.py:624-770 |

## Self-Check: PASSED

- `src/vibemix/audio/lookahead.py` → FOUND (294 LOC)
- `tests/audio/test_lookahead.py` → FOUND (311 LOC)
- `tests/audio/fixtures/test_lookahead_track.mp3` → FOUND (40585 bytes)
- `.planning/phases/40-anti-slop-audio-port/deferred-items.md` → FOUND
- `src/vibemix/audio/__init__.py` → MODIFIED (LookaheadProvider + 4 constants re-exported)
- Commit `37c0e10` → FOUND in git log (RED)
- Commit `1282b4b` → FOUND in git log (GREEN)
- POC immutability (`cohost.py` / `cohost_v2.py` / `cohost_lk.py` / `mascot.html`) → working tree clean
- All 8 plan tests → PASSING locally
