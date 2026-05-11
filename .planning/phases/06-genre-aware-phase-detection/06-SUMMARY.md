---
phase: 06-genre-aware-phase-detection
plan: rollup
type: summary
status: complete
completed_at: 2026-05-11
requirements_covered:
  - SENSE-03  # Percentile-based phase detector (no global RMS thresholds)
  - SENSE-04  # 5 genre profile JSONs (techno / house / D&B / disco / pop)
  - SENSE-06  # Crest factor compression detection
  - SENSE-07  # BPM half/double validator
  - SENSE-08  # Vocal-section detector + LAYER_ARRIVAL gate
  - SENSE-10  # PARTIAL — detector implemented; 30-min per-genre validation harness lives in Phase 16
  - UX-03     # Genre profile selectable via VIBEMIX_GENRE_PROFILE env (Phase 12 UI flips it)
wave_commits:
  - 11d358a  # wave 1 — genre profile system + 5 JSON profiles
  - 1c4e264  # wave 2 — crest factor + BPM half/double validator + vocal detector
  - 01ff963  # wave 3 — percentile phase detector + MusicState extensions + state_refresh_loop wiring
  - 84b6978  # wave 4 — LAYER_ARRIVAL vocal gate + VIBEMIX_GENRE_PROFILE env + state re-exports
test_count: 531  # 385 Phase 5 baseline + 146 Phase 6 new
---

# Phase 6 — Genre-Aware Phase Detection — Summary

**Completed:** 2026-05-11
**Plan:** 06-genre-aware-phase-detection / 5 plans across 5 waves (4 feat + 1 docs gate)
**Verdict:** All 10 acceptance gates PASS. Phase 6 is shipped.

## What Phase 6 Delivered

Five hand-tuned genre profile JSONs (`techno`, `house`, `drum_and_bass`, `disco`, `pop`) drive a **percentile-based phase detector** that adapts to each track's own loudness distribution rather than a fixed RMS scale. Three companion DSP guards land alongside: **crest factor** flags compressed vs dynamic masters; **BPM half/double validator** snaps autocorr's half-time / double-time mis-locks to the active profile's `bpm_range`; **vocal-section detector** (1.5s in / 2.5s out hysteresis) flips `MusicState.vocal_active`, which gates `EventDetector.LAYER_ARRIVAL` so the AI doesn't fire a "new sonic layer" reaction every time a singer enters.

The new classifier preserves v4 byte-equivalence in the fallback path: `VIBEMIX_GENRE_PROFILE=none` (or env unset and Settings UI opts out) keeps the Phase 3 absolute-threshold body running. Pinned via parametric golden-equivalence test across 10 canonical curves — when `profile=None`, the new dispatch entry point returns the SAME string for the SAME inputs as the original v4 `classify_phase`. Critical Constraint 3 honored.

MusicState gains 4 new fields (`crest_factor`, `vocal_active`, `bpm_corrected`, `genre_profile_name`) with backward-compat defaults — Phase 3's existing tests (`test_music_state.py`) pass unchanged. Hysteresis state and the EMA smoother live in `state_refresh_loop`'s LOCAL scope, NOT in MusicState (Critical Constraint 7: MusicState holds consumer-readable evidence; hysteresis machinery is internal detector state).

POC files (`cohost_v4.py`, `run_v4.sh`, `cohost*.py`, `mascot.html`, `fillers/`) are diff-untouched throughout — `v4` still runs unchanged via `./run_v4.sh` on Kaan's rig.

### Wave-by-wave

- **Wave 1** (`11d358a`) — `vibemix.state.genre` subpackage. `GenreProfile` frozen dataclass + 5 hand-tuned JSON profiles + `load_profile` / `list_profiles` / `set_active_profile` / `get_active_profile` singleton + hand-written schema validator (no pydantic — Critical Constraint 6). 46 tests.
- **Wave 2** (`1c4e264`) — Three companion DSP helpers. `crest_factor(pcm_int16)` (peak/RMS, float64-safe squared sum) + `EmaSmoother(alpha=0.3)` (pass-through first update). `validate_bpm(raw, profile)` (half/double snap + defensive zero/negative short-circuit). `VocalDetector` class (2-of-3 heuristic rules + 1.5s in / 2.5s out hysteresis). 41 tests.
- **Wave 3** (`01ff963`) — The heart of Phase 6. `classify_phase_percentile` (30/70/95 percentile mapping + cold-start fallback + build (≥4 climbs, stricter than v4's 3) + breakdown (`< breakdown_ratio * recent_peak`) + drop (p95 + jump > threshold) + 3-tick hysteresis; silent commits immediately). `HysteresisState` dataclass threading through ticks. `classify_phase` becomes a DISPATCH entry point — `profile=None` returns plain `str` (Phase 3 byte-equivalent); `profile=<GenreProfile>` returns `(label, HysteresisState)` tuple. `state_refresh_loop._tick_once` extended to write 4 new fields each tick. 39 tests.
- **Wave 4** (`84b6978`) — Consumer wiring. `EventDetector.LAYER_ARRIVAL` gated on `and not state.vocal_active` (single 1-line code change, plus baseline-still-updates so post-vocal jumps don't false-fire on stale signatures). `apply_genre_env()` helper reads `VIBEMIX_GENRE_PROFILE` (default `'techno'`, case-insensitive + whitespace-stripped; `none`/`unknown`/`''` → Phase 3 fallback; invalid → `sys.exit` listing valid choices). `__main__.py` calls it between Phase 5 mode dispatch and audio primitives setup. `vibemix.state.__init__` re-exports 11 genre symbols at top level. 13 tests.

## Requirements Coverage

| Req | Description | How Phase 6 satisfied it |
|-----|-------------|--------------------------|
| SENSE-03 | Percentile-based phase detector (no global RMS) | `vibemix.state.genre.detector.classify_phase_percentile` — 30/70/95 percentile mapping over `long_arc_curve(120s)`. Dispatched from `vibemix.state.phase.classify_phase` when a profile is active. |
| SENSE-04 | 5 genre profile JSONs | `src/vibemix/state/genre/profiles/{techno,house,drum_and_bass,disco,pop}.json` — hand-tuned per 06-CONTEXT.md §5 Initial Profiles. Ship in wheel via hatchling default package-data inclusion (verified via `uv build --wheel + unzip -l`). |
| SENSE-06 | Crest factor compression detection | `vibemix.state.genre.crest_factor.crest_factor` (peak/RMS) + `EmaSmoother(alpha=0.3)` cross-snapshot smoothing. Written to `MusicState.crest_factor` each tick. |
| SENSE-07 | BPM half/double validator | `vibemix.state.genre.bpm_validator.validate_bpm` — snaps `raw_bpm` to `profile.bpm_range` via half-or-double scan. `state_refresh_loop` overwrites `MusicState.bpm` with the normalized value AND writes `MusicState.bpm_corrected: bool`. |
| SENSE-08 | Vocal-section detector + LAYER_ARRIVAL gate | `vibemix.state.genre.vocal_detector.VocalDetector` (2-of-3 rules + 1.5s/2.5s hysteresis) writes `MusicState.vocal_active`. `EventDetector.LAYER_ARRIVAL` block gated on `and not state.vocal_active`. |
| SENSE-10 | Per-genre F1 ≥85% measurement | **PARTIAL** — Phase 6 ships the detector; Phase 16 (Hallucination Verification Gate) runs the 30-session replay suite and produces the F1 number per CONTEXT out-of-scope clause. Open To-do: collect 30-min recorded sets per genre (Kaan + Francesco's DJ network). |
| UX-03 | Genre profile selectable at runtime | `VIBEMIX_GENRE_PROFILE` env var read at startup via `apply_genre_env()`; valid genres list comes from `list_profiles()`. Phase 12 Settings UI will surface a dropdown reading the same list and invoking `set_active_profile` mid-session — the per-tick `get_active_profile()` re-read in `state_refresh_loop` makes mid-session swaps cheap. |

## Files Created / Modified

### Created

| Path | Purpose | LOC |
|------|---------|-----|
| `src/vibemix/state/genre/__init__.py` | Re-exports all 11 Phase 6 surface symbols | 35 |
| `src/vibemix/state/genre/profile.py` | `GenreProfile` dataclass + JSON loader + active-profile singleton + hand-written schema validator | 230 |
| `src/vibemix/state/genre/crest_factor.py` | `crest_factor` (peak/RMS) + `EmaSmoother(alpha=0.3)` | 70 |
| `src/vibemix/state/genre/bpm_validator.py` | `validate_bpm(raw, profile) -> (normalized, was_corrected)` | 60 |
| `src/vibemix/state/genre/vocal_detector.py` | `VocalDetector` class (2-of-3 rules, 1.5s/2.5s hysteresis) | 115 |
| `src/vibemix/state/genre/detector.py` | `classify_phase_percentile` + `HysteresisState` | 175 |
| `src/vibemix/state/genre/profiles/__init__.py` | Package marker (importlib.resources resolution) | 10 |
| `src/vibemix/state/genre/profiles/techno.json` | 125-175 BPM, crest 3.5-6.5, sub-heavy, rare vocals | 20 |
| `src/vibemix/state/genre/profiles/house.json` | 118-130 BPM, crest 4-7, balanced bands, occasional vocals | 20 |
| `src/vibemix/state/genre/profiles/drum_and_bass.json` | 165-180 BPM, crest 3.5-5.5, sub+high heavy | 20 |
| `src/vibemix/state/genre/profiles/disco.json` | 110-125 BPM, crest 5-9, mid+high heavy, frequent vocals | 20 |
| `src/vibemix/state/genre/profiles/pop.json` | 95-130 BPM, crest 3-5, heavy compression, very frequent vocals | 20 |
| `src/vibemix/_main_helpers.py` | `apply_genre_env()` — extracted from `__main__.py` for testability | 50 |
| `tests/state/test_genre_profile.py` | 46 tests pinning schema, sanity, singleton | 230 |
| `tests/state/test_crest_factor.py` | 13 tests pinning crest math + EMA | 110 |
| `tests/state/test_bpm_validator.py` | 15 tests pinning half/double matrix + defensives | 140 |
| `tests/state/test_vocal_detector.py` | 13 tests pinning 2-of-3 rules + 1.5s/2.5s hysteresis | 175 |
| `tests/state/test_genre_detector.py` | 16 tests pinning percentile mapping + hysteresis + cold-start | 245 |

### Modified

| Path | Change |
|------|--------|
| `src/vibemix/state/music_state.py` | 4 new fields added (crest_factor, vocal_active, bpm_corrected, genre_profile_name) with backward-compat defaults |
| `src/vibemix/state/phase.py` | `classify_phase` becomes a dispatch entry point — Phase 3 v4 body preserved as `_classify_phase_v4`; new keyword-only `profile=` / `features=` / `hysteresis_state=` enables percentile path |
| `src/vibemix/state/refresh.py` | `_tick_once` extended with 4 new loop-local kwargs (crest_smoother / vocal_detector / hysteresis_state / feature_history); writes 4 new MusicState fields; dispatches classify_phase on active profile |
| `src/vibemix/state/event_detector.py` | Single 1-line gate added to LAYER_ARRIVAL: `and not state.vocal_active` |
| `src/vibemix/state/__init__.py` | Re-exports 11 Phase 6 symbols at vibemix.state top level |
| `src/vibemix/__main__.py` | Calls `apply_genre_env()` after Phase 5 mode dispatch |
| `tests/state/test_phase.py` | Adds parametric golden-equivalence test + dispatch-path tests |
| `tests/state/test_refresh.py` | Adds 7 tests pinning 4 new MusicState fields written per tick |
| `tests/state/test_event_detector.py` | Adds 4 tests pinning LAYER_ARRIVAL vocal-active gate + baseline-update invariant |
| `tests/test_main_smoke.py` | Adds 9 tests pinning env-driven genre dispatch matrix + case-insensitivity + sys.exit on bad value |
| `pyproject.toml` | Comment documenting hatchling default behavior ships JSONs as wheel package data |

## Architectural Decisions Locked

- **Percentile thresholds: p30 / p70 / p95.** Drawn from the rolling 120s `long_arc_curve` (already produced by Phase 2). 30-sample minimum for percentile activation — sub-30 falls back to the profile's absolute thresholds.
- **3-tick hysteresis at 10Hz = 300ms minimum dwell.** Tighter than human perception threshold for phase transitions. `silent` is a hard exception — commits immediately on first detection (anti-hallucination — audio death is unambiguous).
- **Cold start uses profile's absolute thresholds.** Not v4's global `SILENT_RMS`/`LOW_RMS`/`PEAK_RMS` constants. Pop and disco, for instance, use a higher `silent_rms=0.014` than techno's 0.012 — heavily-compressed masters have a higher noise floor.
- **JSON profile schema frozen + hand-validated.** No pydantic dependency — Critical Constraint 6 says no new heavy deps. Validator raises `ValueError` with profile-name + field-name on any missing/malformed payload; silent defaults explicitly prohibited (CONTEXT scope_reduction).
- **Active profile singleton at module level.** `vibemix.state.genre.profile._ACTIVE_PROFILE`. `set_active_profile(None)` is a first-class call that disables genre mode — pinned via test. Phase 12 Settings UI will re-call `set_active_profile` mid-session; `state_refresh_loop` re-reads `get_active_profile()` per tick.
- **`VIBEMIX_GENRE_PROFILE` env defaults to `'techno'`.** Kaan's set per CONTEXT D-LOCKED §Settings Integration. `'none'`/`'unknown'`/`''` are first-class aliases for Phase 3 fallback. Invalid name → `sys.exit` with the valid-choices list (NOT silent fallback — same security/clarity stance as Phase 5's mode dispatch).
- **`classify_phase` return-type is conditional on whether `profile` was passed.** `profile=None` (positional or keyword) → plain `str` (Phase 3 contract preserved). `profile=<GenreProfile>` → `(label, HysteresisState)` tuple. Backward-compat trick keeps existing positional callers working without modification.
- **Hysteresis state lives in `state_refresh_loop` local scope.** NOT in MusicState — Critical Constraint 7. MusicState is consumer-readable evidence; hysteresis machinery is internal detector state and must not leak into prompt evidence.
- **BPM validator: half→double order, zero/negative short-circuit.** `raw * 2` checked before `raw / 2`. `raw_bpm <= 0.0` returns `(0.0, False)` immediately — `estimate_bpm` returns 0 as "no signal", doubling it is meaningless.
- **VocalDetector: 2-of-3 heuristic rules.** Mid dominance (sustained), rising onset trend, vocal-above-sub-bass. 1.5s in-dwell + 2.5s out-dwell. `profile` parameter accepted but unused in v1 — reserved for future per-genre threshold tuning (D&B vocals sit at different band ratios than pop choruses).
- **EventDetector LAYER_ARRIVAL is the ONLY event-type change.** Other 5 (KAAN_SPOKE / MANUAL / TRACK_CHANGE / PHASE / MIX_MOVE / HEARTBEAT) byte-identical to v4. The baseline `self.last_band_signature = sig` line still updates inside the gated branch — pinned via test — so a non-vocal post-vocal jump doesn't false-fire against a stale baseline.
- **No new heavy DSP deps.** Critical Constraint 6. Numpy + scipy already in stack. All Phase 6 algorithms are ≤60 LOC each. Zero new top-level imports added to `pyproject.toml dependencies`.
- **Build detection stricter in percentile path.** `>= 4` monotonic positive deltas (all 4 climbs) for the percentile detector; the v4 fallback path retains `>= 3`. Cold-start path inside `classify_phase_percentile` shares the v4 absolute-threshold body via `_cold_start_phase` (uses profile's `peak_rms` instead of `PEAK_RMS` constant). Two thresholds because two paths with different tolerance budgets.

## Deviations from Plan

### Auto-fixed during execution

1. **[Rule 3 — Test calibration] Crest factor test math.**
   - Found during: Wave 2 Task 1.
   - Issue: Initial test expected `crest_factor` of uniform-random int16 to be 3-5 (compressed-dance range). That math is wrong — uniform-random has theoretical crest = √3 ≈ 1.732, not 3-5. Compressed dance crest of 3-5 needs a SPARSE distribution (kick-dominated with body of small samples between).
   - Fix: Replaced one test with `test_uniform_random_crest_close_to_sqrt3` (≈ √3) and added `test_sparse_peaks_synthetic_crest_in_dance_master_range` that uses sparse impulses to actually achieve crest 3-5.
   - Files modified: `tests/state/test_crest_factor.py`.
   - Commit: `1c4e264` (Wave 2).

2. **[Rule 3 — Test calibration] EMA smoother convergence test.**
   - Found during: Wave 2 Task 1.
   - Issue: Initial test fed 15 ticks of 10.0 to a smoother with `initial=0.0`. Because the FIRST update is a pass-through (no synthetic warm-up bias), the value jumped to 10.0 on tick 1 and stayed there.
   - Fix: Warm up the smoother with `update(0.0)` first, then feed 20 ticks of 10.0. With alpha=0.3 from a 0.0 baseline, after 20 ticks: `1 - 0.7^20 ≈ 0.9992` — converges nicely to 9.99.
   - Commit: `1c4e264` (Wave 2).

3. **[Rule 3 — Test calibration] Wave 3 hysteresis-reset-on-same-as-current test.**
   - Found during: Wave 3 Task 1.
   - Issue: Initial test used `curve=[0.04]*35` to classify as 'groove'. But with all 35 samples at 0.04, p30=p70=p95=0.04, so `last >= p95` → 'peak' branch. The curve doesn't actually classify as 'groove'.
   - Fix: Used `linspace(0.01, 0.08, 34) + [0.040]` for a wide distribution where `p30 ≈ 0.031`, `p70 ≈ 0.057`, last=0.040 → falls in groove tier. Added an explicit assert checking `p30 <= last < p70` to document the constraint.
   - Commit: `01ff963` (Wave 3).

### CONTEXT-driven implementation choices (planner-foreseen)

4. **Hand-written schema validator instead of pydantic.** CONTEXT mentioned "pydantic-validated load from JSON" as a possibility but the planner picked the lighter dependency. Wave 1 ships a 70-line hand-written validator covering all 11 required fields + 4 nested keys. No new top-level pyproject dependency.
5. **CONTEXT "62→124 (techno)" boundary case documented as edge.** `validate_bpm(62.0, techno)` returns `(62.0, False)` NOT `(124.0, True)` — 124 falls below techno's `bpm_range` lo of 125. Pinned via `test_techno_62_NOT_corrected_doubled_falls_below_range`. The in-range half-corrected case uses 63→126 in the test suite.
6. **Build detection threshold split.** Percentile path uses `>= 4` monotonic climbs (strict, all 4 deltas positive); v4 fallback path retains `>= 3` (looser). Two different thresholds for two different paths — documented in `detector.py` step 3 comment.
7. **`_main_helpers.apply_genre_env()` extraction.** Not in CONTEXT verbatim — pulled the env-dispatch block out of `__main__.py` for testability. Tests call `apply_genre_env()` directly instead of standing up the full async orchestrator. Matches the Phase 5 pattern.
8. **Defensive zero/negative short-circuit in `validate_bpm`.** Not in CONTEXT text but pinned via test. `estimate_bpm` returns 0.0 as "no signal"; doubling zero is meaningless. Negative input is also short-circuited (defensive against future autocorr math glitches).

## Dependent Phases Unlocked

- **Phase 10 (Prompt Template Matrix)** — `AICoach.evidence_line` can now surface `vocal=on/off`, `crest=N.N`, `bpm=corrected/raw`, `genre=<name>` for prompts. The 4 new MusicState fields are stable consumer-readable surfaces.
- **Phase 12 (Settings UI)** — Genre picker reads `vibemix.state.list_profiles()` for options; writes via `vibemix.state.set_active_profile(name)`. Mid-session profile flips work via the per-tick `get_active_profile()` re-read in `state_refresh_loop`.
- **Phase 16 (Hallucination Verification)** — Per-genre F1 ≥85% gate has its detector to measure. SENSE-10's 30-min recorded-set validation harness lives here.

## Open Items Carried Forward

- **30-min recorded sets per genre.** Kaan + Francesco's DJ network. Phase 16 work; collection can begin now in parallel with Phase 7 (Windows Port). Five genres × 30 min ≈ 2.5 hours of audio total — manageable.
- **Per-deck profile inference** (deck A = techno, deck B = house). Post-v1 per CONTEXT.
- **Auto-detect genre from audio fingerprint.** Post-v1.
- **Genre profile training UI.** Post-v1.
- **Vocal-section confidence (0..1 score).** Conditional on Phase 10 prompt-work needing it; currently boolean only.
- **DDJ-FLX4 tempo CC overriding autocorr.** Phase 9 fix territory — when the controller is connected and reports BPM, prefer that over autocorr's noisy estimate.

## v4-vs-Phase-6 Phase Classification Diff

**What stays the same:** When `VIBEMIX_GENRE_PROFILE=none` (or env unset and Settings opts out via `set_active_profile(None)`), behavior is byte-equivalent to v4. Pinned via parametric golden-equivalence test in `tests/state/test_phase.py::test_profile_none_equals_phase_3_behavior_for_all_existing_inputs` across 10 canonical curves.

**What changes when a profile is active (default `'techno'`):**

- Phase labels become **more sensitive to the track's OWN loudness distribution** rather than global thresholds. A quiet techno track that previously sat in `'low'` for its entire run can now hit `'groove'` / `'peak'` as its dynamics expand against its own p30/p70/p95.
- `'drop'` is **more conservative** — requires a jump > `profile.drop_jump_threshold` (0.060 for techno) ON TOP of being ≥ p95. v4 fired `'drop'` on a single PEAK_RMS crossing if any of the previous 3 samples sat below LOW_RMS — looser. Phase 6 will MISS some sustained-peak "drops" that v4 would have flagged; it surfaces only the true sudden jumps.
- **3-tick hysteresis (300ms at 10Hz) prevents flicker.** v4 had no hysteresis — single-tick transitions allowed. Brief 1-2-tick blips between adjacent labels no longer change `state.phase`.
- **`'silent'` commits immediately** (no hysteresis) when `audible=False` or `last < silent_rms` — anti-hallucination, preserves v4's instinct that silence is unambiguous.
- **Build detection stricter** (4 monotonic climbs required vs 3 in v4) in the percentile path. The cold-start path under 30 samples still uses 3.

### Side-by-side: synthetic curves through both paths

| Curve | v4 label | P6 label (techno profile, after 3-tick hysteresis convergence) |
|-------|----------|----------------------------------------------------------------|
| `[0.005]` — silent | silent | silent |
| `[0.030]` — just under low_rms | low | low |
| `[0.05, 0.05, 0.05, 0.04, 0.045, 0.043, 0.044]` — groove fallback | groove | groove |
| `[0.02, 0.04, 0.06, 0.08, 0.10, 0.12]` — 5-tick climb | build | peak* |
| `[0.05]*10` — sustained mid-energy | peak | groove* |
| `[0.05, 0.05, 0.05, 0.02, 0.05, 0.12]` — drop above PEAK_RMS | drop | drop |
| `[0.10]*5 + [0.07, 0.06, 0.05, 0.045, 0.041]` — crash from peak | breakdown | groove* |
| `[0.090]*40` — sustained-peak warm curve | peak | peak |
| `[0.050]*35 + [0.040, 0.040, 0.040, 0.040, 0.120]` — drop with jump | groove | drop |
| `[0.030]*30 + [0.030, 0.035, 0.040, 0.045, 0.060]` — strict build | build | build |

\* These differences are **expected and intentional** — they reflect the percentile detector's adaptation to the track's own dynamics. Short-warm curves (under 30 samples) follow profile absolute thresholds (different from v4 global constants); long-warm curves follow percentile mapping. The 3-tick hysteresis additionally suppresses single-tick transitions that v4 would have surfaced.

### Side effects on EventDetector

- PHASE events fire on the COMMITTED (post-hysteresis) phase, not the raw classifier output. Brief transient labels (1-2 ticks of 'peak' inside a 'groove' run) no longer fire a PHASE event. This is anti-slop tightening.
- LAYER_ARRIVAL is **suppressed during vocal sections** (state.vocal_active=True). The AI no longer fires a "new layer arrived" reaction every time a singer enters. v4 had no such gate. D&B + pop + disco see the biggest behavioral shift.

### Side effects on AICoach (Phase 10 surface)

- `state.vocal_active` exposed for prompts.
- `state.crest_factor` exposed for prompts ("track is heavily compressed" / "dynamic master").
- `state.bpm_corrected` exposed ("BPM=128 [corrected from autocorr half-detection of 64]").
- `state.genre_profile_name` exposed ("operating in techno mode").

### What to expect in a live session

- **Fewer noisy PHASE flips per minute** — hysteresis kills the 10Hz flutter that v4 occasionally surfaced.
- **LAYER_ARRIVAL silenced during vocals** — biggest qualitative win for non-techno genres.
- **Drop detection more deliberate** — might miss a few sustained-peak drops that v4 would have flagged; will fire on the true sudden jumps Kaan considers "drops".
- **BPM displayed in evidence_line more often correct** — half-detection auto-snaps.
- **The percentile detector's "track adapts to its own dynamics" is the biggest qualitative win** — Kaan should hear AI reactions that follow HIS curve, not a fixed loudness scale.

## Verification Snapshot

| Gate | Description | Status | Notes |
|------|-------------|--------|-------|
| 1 | Import probe (all 11 symbols) | PASS | `from vibemix.state.genre import ...` exits 0 |
| 2 | All 5 profiles loadable | PASS | `list_profiles() == ['disco','drum_and_bass','house','pop','techno']` |
| 3 | Phase 3 golden equivalence preserved | PASS | 11 tests in `test_phase.py::test_profile_none_equals_phase_3_*` + positional |
| 4 | Percentile detector on synthetic curves | PASS | 16 tests in `test_genre_detector.py` |
| 5 | BPM half/double matrix | PASS | 15 tests in `test_bpm_validator.py` — 62/250/200/350 + boundary + zero/negative |
| 6 | Crest factor math | PASS | 13 tests in `test_crest_factor.py` — sine ≈ √2, square ≈ 1, impulse > 20, EMA pass-through |
| 7 | Vocal detector hysteresis | PASS | 13 tests in `test_vocal_detector.py` — 1.5s in / 2.5s out + brief-dip-resilience + rule combos |
| 8 | EventDetector LAYER_ARRIVAL vocal gate | PASS | 4 tests pinning suppression + fires-when-not-vocal + baseline-still-updates |
| 9 | MusicState 4 new fields with defaults | PASS | `MusicState().crest_factor==0.0`, `.vocal_active is False`, `.bpm_corrected is False`, `.genre_profile_name=='unknown'` |
| 10 | Full pytest + ruff hygiene | PASS | 531 tests green; ruff check + format clean across `src/` + `tests/` |

POC-untouched: `git diff --name-only HEAD~4..HEAD -- 'cohost*.py' 'run*.sh' mascot.html fillers/ cohost.streaming.py.bak` empty. `cohost_v4.py` is byte-identical to phase start; `./run_v4.sh` continues to function unchanged.

## Commit History

| SHA | Wave | Title |
|-----|------|-------|
| `11d358a` | 1 | feat(06): wave 1 — genre profile system + 5 JSON profiles |
| `1c4e264` | 2 | feat(06): wave 2 — crest factor + BPM half/double validator + vocal detector |
| `01ff963` | 3 | feat(06): wave 3 — percentile phase detector + MusicState extensions + state_refresh_loop wiring |
| `84b6978` | 4 | feat(06): wave 4 — LAYER_ARRIVAL vocal gate + VIBEMIX_GENRE_PROFILE env + state re-exports |
| (this commit) | 5 | docs(06): Phase 6 complete — genre-aware phase detection shipped |

## Self-Check: PASSED

- All 10 verification gates green.
- POC files diff-untouched (`cohost*.py`, `run*.sh`, `mascot.html`, `fillers/`, `cohost.streaming.py.bak`).
- 4 atomic `feat(06):` wave commits + this `docs(06):` close commit.
- 531 tests green (385 Phase 5 baseline + 146 Phase 6 new). Ruff check + format clean.
- 5 JSON profiles ship in wheel (verified via `uv build --wheel + unzip -l`).
- 4 new MusicState fields with backward-compat defaults — Phase 3 tests pass unchanged.
- Phase 3 golden equivalence pinned across 10 parametric curves.
- `set_active_profile(None)` is a valid call disabling genre mode (Critical Constraint 8).
- Hysteresis state in loop-local scope, NOT in MusicState (Critical Constraint 7).
- No new heavy DSP deps (Critical Constraint 6).
- Every CONTEXT D-LOCKED decision honored; no deferred ideas implemented this phase.
