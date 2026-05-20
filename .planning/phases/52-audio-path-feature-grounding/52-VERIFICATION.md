---
phase: 52
slug: audio-path-feature-grounding
kind: verification
status: passed
verifier: Claude Opus 4.7 (GSD review + verification step)
date: 2026-05-21
requirements: [BRINGUP-02, GENRE-01, GENRE-02]
---

# Phase 52 — Goal-Backward Verification

Verified the executed phase against its requirements by working backward from
the goal ("the AI/UI never sees a value that did not happen; genre is grounded,
confidence-gated, honest"). Evidence is from re-run targeted tests + direct
empirical probes of the scorer, not from reading the executor's summaries.

**Verdict: PASSED.** Two requirements (GENRE-01, GENRE-02) are fully proven by
automated tests. BRINGUP-02's automated portion (guard + grounding regressions)
passes; its one real-hardware multi-genre live-drive on Kaan's Mac is
**Kaan-action** (per the autonomous carveout + `project_phase_16_kaan_dj_testing`)
— marked deferred, NOT a gap.

Independent evidence (orchestrator): full default suite **3719 passed, 25
skipped, 0 failed**. Re-confirmed the Phase-52 targeted slice locally: **150
passed** (genre + bpm + features + sample-rate + refresh + ws_bus) + **3 passed**
(`macos_audio` live tests on this Mac with BlackHole @48k).

---

## BRINGUP-02 — Audio path guarded + features grounded → PASSED (automated) / human_needed (live drive)

**Requirement:** 48 kHz capture path guarded; every derived feature grounded —
BPM never > `BPM_VALID_MAX=180` on the harmonic-leak trace; rms/bands/onset
finite + in-range.

- **48 kHz guard:** `assert_device_sample_rate` raises `SampleRateMismatchError`
  with actionable `44100`/`48` text on a misconfigured BlackHole, attempts the
  best-effort fix + opens Audio MIDI Setup, and `open_capture` provably calls
  the guard pre-open. `INPUT_SR_NATIVE == 48000` pinned.
  → `tests/audio/test_sample_rate_guard.py` (3 passed).
- **BPM grounding:** the real bimodal harmonic-leak distribution (incl. the
  194-200 subdivision cluster) replayed through the actual `_tick_once`
  stabilizer chain across 300 ticks never lets `state.bpm` exceed `BPM_VALID_MAX`
  for either techno or psytrance active profile, AND steady-state median tracks
  the real ~130 (not the 200 lock or a wrong-but-in-range clamp).
  → `tests/state/test_bpm_bus_grounding.py` (3 passed).
- **Feature grounding:** silence→quiet→loud→sweep replay keeps every bus-facing
  field finite (no NaN/inf) + in-range (rms≥0, bands∈[0,1], onset≥0).
  → `tests/state/test_feature_grounding.py` (3 passed).
- **Real multi-genre live drive on Kaan's Mac** (his library, his ears) — the
  true grounding sign-off — is **human_needed** (Kaan-action). The runnable
  recipe is `tests/test_audio_macos_live.py::test_blackhole_input_is_48k_for_live_capture`
  (the 4-point live-tap procedure: meters move + bpm in-band + detected_genre
  honest). The opt-in `macos_audio` tests PASS on this Mac (BlackHole @48k).

**One-line rationale:** the guard + median-ring stabilizer + range gate
provably keep out-of-range audio off the bus; the across-the-library ear test
is the deferred Kaan-action surface, by design — not a gap.

## GENRE-01 — Psytrance profile + grounded confidence-gated DSP auto-detector → PASSED

**Requirement:** psytrance profile exists; a DSP auto-detector classifies from
real features, confidence-gated with `unknown` fallback + hysteresis + env
override.

- **Profile:** `psytrance.json` loads + validates through the hand-written
  `_parse_profile` (no pydantic) with locked values; sub heavier than mid;
  bpm_range fully inside the valid window. → `tests/state/test_psytrance_profile.py`
  (7 passed); `list_profiles()` now returns 6 → `tests/state/test_genre_profile.py`.
- **Psytrance-shaped vector → confident psytrance** (the regression for Kaan's
  bug), proven directly: psy vector scores `psytrance` ≥ gate, never `techno`,
  despite the subset band overlap. Every profile centre scores itself @ conf 1.0
  (empirical probe + `test_midpoint_vector_scores_its_own_profile`).
- **Out-of-library / no-BPM-lock / tie → `unknown`** (no false-confident pick):
  alien high-band vector → unknown; `bpm<=0` → unknown; tie-within-margin →
  unknown. → `tests/state/test_genre_autodetect.py`.
- **Hysteresis** debounces flicker (3-tick dwell to commit; oscillation never
  commits; `unknown` commits immediately) without masking real changes (~0.3s
  to commit a sustained switch). → same suite.
- **Env override** wins: explicit `VIBEMIX_GENRE_PROFILE` pin → auto-detect
  scores but does NOT flip the active profile (detection still surfaced); no
  pin → auto-detect flips. Both directions proven at the real `_tick_once`
  boundary. → same suite.
- **Single-writer wiring:** detector runs inside the `state._lock` batch in
  `_tick_once`; writes parallel `detected_genre`/`genre_confidence`; the coarse
  `active_genre` / `_classify_active_genre` signal is AST-identical (untouched).
  → `tests/state/test_refresh.py` (+3 new) all green.

**One-line rationale:** psytrance-shaped features score confident psytrance and
out-of-library features score `unknown`, with hysteresis + env override proven —
the grounded, anti-slop detector Kaan asked for.

## GENRE-02 — Detected genre + confidence on the bus, `unknown` when unsure → PASSED

**Requirement:** detected genre + confidence surfaced on the bus; `unknown`
when unsure, never a hallucinated label.

- `detected_genre` + `genre_confidence` ride the 30Hz mascot frame with exact
  round-trip values; a low-confidence pick is surfaced as `unknown` (honesty
  enforced at the source scorer, the wire carries it verbatim); the new keys do
  not trip the Phase-51 empty-frame guard; `active_genre` still rides the wire
  unchanged; fresh-state default is `unknown`/0.0.
  → `tests/runtime/test_ws_bus_genre_fields.py` (5 passed); existing ws_bus
  suites green.

**One-line rationale:** the two fields are additively on the wire with verbatim
honesty (`unknown` when unsure) and no disturbance to the existing frame.

---

## Re-confirmed invariants

- **`_stabilize_bpm` untouched** — AST-identical `c5c66a4`↔HEAD.
- **`active_genre` / `_classify_active_genre` untouched** — AST-identical;
  `detected_genre` is a parallel field, not a replacement.
- **Anti-slop contract holds — no confident-wrong-genre path** under real
  (stabilized) feature ranges: every library centre maps to itself; ambiguity
  returns `unknown`; `bpm<=0` returns unknown; the only confident-pick-on-odd
  input (`bpm=200`) is unreachable because `state.bpm ≤ 180` is guaranteed
  before scoring.
- **No new heavy deps** — `genre_autodetect.py` imports only stdlib +
  `GenreProfile`; no-heavy-deps grep test green.

## Gaps

None blocking. The only outstanding item is the Kaan-action real-hardware
multi-genre live drive (BRINGUP-02 SC), which is deferred by design, not a gap.

## Sign-off

Phase 52 is **COMPLETE** — safe to transition and advance to Phase 53.
