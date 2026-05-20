---
phase: 52
slug: audio-path-feature-grounding
kind: code-review
status: clean
reviewer: Claude Opus 4.7 (GSD review + verification step)
reviewed_range: c5c66a4..HEAD (src/ tests/)
date: 2026-05-21
---

# Phase 52 — Code Review (Audio Path + Feature Grounding)

Deep review of the Phase 52 diff (`git diff c5c66a4..HEAD -- src/ tests/`): 18
phase commits + a README sync. Load-bearing scrutiny on the anti-slop contract
of the new DSP genre detector, the single-writer wiring, the bus additions, and
test realness.

**Verdict: CLEAN.** No HIGH or MEDIUM findings. Three LOW notes (all
pre-existing / non-enforced). Nothing fixed because nothing required a fix.

---

## Scope reviewed

| Area | File(s) | Disposition |
|------|---------|-------------|
| Genre scorer + hysteresis (NEW) | `src/vibemix/state/genre/genre_autodetect.py` | clean |
| Detector wiring (single-writer) | `src/vibemix/state/refresh.py` | clean, additive |
| Psytrance profile (NEW data) | `src/vibemix/state/genre/profiles/psytrance.json` | clean |
| Bus additions | `src/vibemix/runtime/ws_bus.py` | clean, additive |
| State fields | `src/vibemix/state/music_state.py` | clean, additive |
| Env-override gate | `src/vibemix/__main__.py` | clean |
| Genre package exports | `src/vibemix/state/genre/__init__.py`, `profiles/__init__.py` | clean |
| 52-01..52-04 tests | `tests/audio/`, `tests/state/`, `tests/runtime/`, `tests/test_audio_macos_live.py` | real, targeted |

---

## Anti-slop contract — the central scrutiny (PASS)

The question that gates this phase: **is there ANY input that yields a confident
WRONG genre?** Verified empirically, not just by reading code.

- **Every profile centre maps to itself at conf 1.0.** Drove each of the 6
  library profiles' midpoint feature vector (band centres + mid-BPM + mid-crest)
  through `score_genre`: disco→disco, dnb→dnb, house→house, pop→pop,
  psytrance→psytrance, techno→techno — all conf 1.0, zero cross-confident picks.
- **The exact Kaan bug is closed.** A psy-shaped vector (sub 0.40 / 144 BPM /
  crest 5.5) scores `psytrance`, NOT `techno`, even though psytrance's band
  ranges are a *subset* of techno's. The midpoint-proximity band axis (not a
  membership test) is what separates them; at `_BAND_TOLERANCE=0.08` the
  psy/techno midpoint lead clears `GENRE_TIE_MARGIN=0.08`. Confirmed numerically.
- **Genuine ambiguity returns `unknown`, never a coin-flip.** A house/techno
  band-blend at 128 BPM scores `unknown` despite a high raw 0.84 — because no
  profile beats the runner-up by the tie margin. A psy/techno band-blend at 144
  scores `unknown` at raw 0.95. This is the contract working as intended:
  honest abstention over a guess.
- **No-BPM-lock guard holds.** `bpm <= 0` → `("unknown", 0.0)` outright; a
  perfect band+crest match cannot manufacture confidence without a tempo lock
  (mirrors `_classify_active_genre`).
- **The only confident-pick-on-odd-input is unreachable in production.** A
  synthetic `bpm=200` + psy bands returns `psytrance` @0.6 — but `state.bpm`
  can never exceed `BPM_VALID_MAX=180` before reaching the scorer (the
  `_stabilize_bpm` ring drops out-of-range samples; pinned by
  `test_bpm_bus_grounding.py`). The scorer is fed the stabilized `bpm_cache`,
  not raw autocorr. So this is not a live confident-wrong-genre path.
- **200k random-vector sweep:** ~40% land on a confident (non-unknown) pick;
  none of them is a confident-wrong pick at any library centre. The detector
  abstains in the genuinely ambiguous middle and commits only when a profile
  clearly dominates.

**Conclusion:** the gate (0.55) + tie-margin (0.08) + no-BPM-lock guard is sound.
No confident-wrong-genre path exists under the real (stabilized) feature ranges.

## Hysteresis — flicker prevention vs masking real changes (PASS)

- A real, sustained genre change commits in exactly 3 ticks
  (`_HYSTERESIS_DWELL_TICKS=3`). At the 10Hz genre-scoring cadence that is
  ~0.3 s — fast enough not to mask a real switch. The actual responsiveness
  bottleneck is the 15 s BPM stabilizer window feeding the scorer, not the
  dwell, which is the correct ordering.
- A 2-tick blip of the wrong genre then back never commits (verified).
- Oscillation (`psy/house/psy/house/psy`) never commits — the pending counter
  resets on a new pending value (verified).
- `unknown` commits immediately (no dwell) — when confidence drops we stop
  claiming the old genre at once. Correct anti-hallucination idiom, mirrors
  `silent` in the phase `HysteresisState`.

## Pure-numpy / no heavy deps (PASS)

`genre_autodetect.py` imports only `dataclasses` + the `GenreProfile` type. No
numpy even (the scoring is plain Python float math over already-computed
features). The no-heavy-deps grep test (`test_genre_autodetect_imports_no_heavy_deps`)
pins the absence of CLAP/MERT/OpenL3/torch/transformers/tensorflow/librosa.

---

## refresh.py wiring — single-writer + untouched-signal confirmation (PASS)

- **`_stabilize_bpm` is AST-identical** pre/post (verified via `ast.dump`
  comparison of `c5c66a4` vs HEAD). The executor's claim holds.
- **`_classify_active_genre` is AST-identical** pre/post — the coarse
  `active_genre` (house/techno/hard_tek/unknown) renderer signal is untouched;
  `detected_genre` is a *parallel* field, not a replacement.
- The genre detector runs **inside the existing `with state._lock:` batch** in
  `_tick_once` — single-writer contract preserved. It scores over the features
  already computed this tick (stabilized `bpm_cache`, band shares,
  `smoothed_crest`), so no extra audio I/O.
- `_PROFILE_CACHE` is loaded once and reused (no per-tick JSON re-load at 10Hz).
- The `set_active_profile` flip is correctly gated: `is_auto_enabled()` AND
  `committed_genre != "unknown"` AND `committed_genre != profile_name`, wrapped
  in `try/except ValueError` so a non-loadable name can never crash the tick or
  flip to garbage.
- `genre_hysteresis` is loop-local (created once in `state_refresh_loop`,
  threaded through `_tick_once`), with a lazy-default for direct callers/tests —
  matching the established Phase 6 loop-local-state idiom.

## __main__.py env override (PASS)

`env_pinned = "VIBEMIX_GENRE_PROFILE" in os.environ and applied_genre is not None`
— a *defaulted* `techno` (env var absent) is correctly NOT treated as a pin, so
auto-detect still self-corrects in that case; an explicit pin disables the flip
(`set_auto_enabled(False)`) while detection is still surfaced for honesty.
Verified both directions at the `_tick_once` boundary in
`test_genre_autodetect.py` (env-pinned keeps techno active + surfaces psytrance
detection; auto-on flips active profile to detected).

## ws_bus.py bus additions (PASS)

- `detected_genre` + `genre_confidence` are two additive keys inside the
  existing `mascot_frame` dict, written BEFORE the Phase-51 empty-frame guard.
- The guard checks only `("music", "voice", "mic")`, so the new keys cannot
  trip it — pinned by `test_genre_fields_do_not_trip_empty_frame_guard`.
- 30Hz mascot cadence unchanged (`asyncio.sleep(1/30)` untouched); the snapshot
  block (`ipc.session.snapshot` @15Hz) is untouched; `active_genre` still rides
  the wire unchanged.

## psytrance.json (PASS)

Values sane and grounded: `bpm_range [138,150]` (fully inside
`[BPM_VALID_MIN, BPM_VALID_MAX]`), heavy sub `[0.30,0.50]` > mid `[0.08,0.20]`
(the offbeat-rolling-bass discriminator vs techno), `crest [4,7]`,
`vocal_likelihood rare`, RMS thresholds strictly increasing, band-midpoint sum
~0.95 (in [0.85,1.10]). Validates through the hand-written `_parse_profile` (no
pydantic). Pinned by `test_psytrance_profile.py` (7 assertions).

---

## Test realness (PASS — real, not shallow)

- `test_bpm_bus_grounding.py` — replays the **real measured** bimodal psytrance
  distribution (66% @130, 28% @194-200, scatter) through the **actual**
  `_tick_once` chain across 300 ticks with a real `bpm_ring`, monkeypatching
  only the estimator (so the stabilizer + `validate_bpm` are exercised, not
  faked). Asserts BOTH the range bound AND that steady-state median tracks the
  real ~130 (not a wrong-but-in-range clamp). Real.
- `test_sample_rate_guard.py` — asserts the **production** guard
  `assert_device_sample_rate` raises with actionable text, attempts the
  best-effort fix, opens Audio MIDI Setup, and that `open_capture` actually
  calls the guard pre-open (source grep). Real.
- `test_feature_grounding.py` — replays silence→quiet→loud→sweep through
  `_tick_once`, asserts every bus-facing feature finite + in-range. Real.
- `test_genre_autodetect.py` — covers self-scoring, the psy-not-techno
  regression, unknown fallback, no-BPM-lock, tie-margin (via a 2-clone world),
  hysteresis dwell/oscillation/immediate-unknown, env override at the real
  `_tick_once` boundary (both directions), and no-heavy-deps. Real + thorough.
- `test_ws_bus_genre_fields.py` — drives the real `ws_broadcast` through a mock
  socket, captures the actual outbound payload, asserts round-trip values +
  unknown honesty + guard-not-tripped + default. Real.
- `test_audio_macos_live.py` (`macos_audio`) — opt-in real-hardware; documents
  the live-tap recipe. See LOW-3.

---

## LOW notes (no action required)

- **LOW-1 — pre-existing ruff I001/E402/F811/F841/UP037/F541 in touched files.**
  `ruff check` flags 19 errors in `refresh.py` / `ws_bus.py` / `__main__.py`.
  Verified these are **pre-existing** (the `refresh.py` I001 unsorted-import
  block already failed at `c5c66a4`; the ws_bus E402/F811 are in the Phase-11
  WizardBus section; the `__main__` F841/F401/F541 are unrelated). The **new**
  files (`genre_autodetect.py`, `genre/__init__.py`, `music_state.py`) pass ruff
  cleanly. **No CI workflow runs `ruff check`** (CI runs only targeted pytest
  files), so none of this is CI-breaking. Phase 52 introduced no new lint
  regression. Left as-is to avoid sweeping unrelated formatting churn into a
  test-only phase.
- **LOW-2 — `genre/__init__.py` `__all__` ordering** places the two `GENRE_*`
  UPPER-snake constants before `EmaSmoother`. `RUF022` (sorted `__all__`) is in
  the selected ruff set but `ruff check` reports the new files clean (the
  constants-first ordering is accepted by ruff's natural sort), and it is not CI
  enforced. No action.
- **LOW-3 — `macos_audio` test runs in a bare `pytest` on this Mac.** Confirmed
  `addopts = "-ra --strict-markers"` does NOT auto-deselect `macos_audio`, so a
  default run on a Mac-with-BlackHole collects + passes the 3 live tests (a
  stronger outcome than skipping). **Verified no CI job runs the full suite or
  this file** — every workflow runs targeted test files on ubuntu-latest only.
  Zero CI-breakage risk. Acceptable as the executor stated.

---

## Working-tree hygiene

No source/test files were modified by this review (read-only verification). Only
the two review/verification docs are created. Kaan's WIP
(`tauri/src-tauri/src/mascot_window.rs`, `tauri/src-tauri/tauri.conf.json5`, and
the untracked `.planning/phases/54-hype-mode-live/`) was NOT touched or staged.
