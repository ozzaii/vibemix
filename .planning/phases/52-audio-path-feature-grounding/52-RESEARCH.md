# Phase 52: Audio Path + Feature Grounding — Research

**Researched:** 2026-05-21
**Verified against:** HEAD `177ff38` (live `src/vibemix/` tree, this session)
**Mode:** Orchestrator-grounded inline research (autonomous `fully`). Every claim below was read off the live source, not assumed.

> **Scope reminder (from 52-CONTEXT.md):** the BPM median-ring stabilizer **already shipped** in `fd25337` and is live at HEAD. This phase BUILDS ON it — it does **not** re-implement it. Remaining BPM work is gate-confirmation + a real-trace regression only.

---

## Question 1 — Is the audio path (BRINGUP-02) already wired, and what is left to prove?

**Answer: the capture path + the 48 kHz sample-rate guard are already wired. The remaining work is (a) a regression that pins the guard fires on the BlackHole *input* device, and (b) a runnable live-tap recipe doc/test for Kaan's real-hardware sign-off.**

Verified live:
- `src/vibemix/audio/constants.py`: `INPUT_SR_NATIVE = 48000` (BlackHole capture), `INPUT_SR_TARGET = 16000` (feature/LLM rate), `OUTPUT_SR = 24000`. Resample 48k→16k via `scipy.signal.resample_poly` (called in `__main__.py:287/292/365` and in `audio/buffers.py` / `audio/resample.py`).
- `src/vibemix/audio/errors.py::SampleRateMismatchError` documents the BlackHole nominal-SR misconfig trap (Audio MIDI Setup at 44.1k while vibemix expects 48k → stream silently succeeds + resamples wrong). This is the BRINGUP-02 startup-validation hook.
- `src/vibemix/platform/_audio_macos.py::assert_device_sample_rate(device_index, expected)` reads `sd.query_devices(idx)['default_samplerate']` (the only macOS CoreAudio API that reflects the live Audio-MIDI-Setup nominal rate), attempts a best-effort programmatic fix, else opens Audio MIDI Setup and raises `SampleRateMismatchError` with exact fix steps.
- **`assert_device_sample_rate(...)` is already CALLED at every stream open** — `_audio_macos.py:259` (input), `:290` (passthrough), `:440` (mic), each with `sample_rate=INPUT_SR_NATIVE` (=48000). So the moment `__main__.py:903` opens the listening input on the BlackHole index, the 48 kHz guard fires.
- `__main__.py:531` `input_idx = audio_backend.find_device(INPUT_DEVICE, "input")`; `:903` opens the input stream at `INPUT_SR_NATIVE`; `:911` prints `-> listening to {INPUT_DEVICE} @ 48000Hz`.

**Gap to close in this phase:** there is **no test that pins the guard fires for the BlackHole *input* device specifically** (the existing live smoke `tests/test_audio_macos_live.py` is `macos_audio`-marked and proves the guard on a real device, but the default suite has no fast assertion that opening the *listening input* path triggers `assert_device_sample_rate` with `expected=48000`). Add a unit/integration regression that mocks `sd.query_devices` to return a 44100 device and asserts `SampleRateMismatchError` is raised before the wrong-rate stream is used — closing the BRINGUP-02 "audio reaches the co-host at 48 kHz" contract at the source. The real multi-genre live drive (levels move on-screen in time with music) is **Kaan-action** — provide the runnable `macos_audio`-marked live-tap recipe so it is one command.

**Levels-register-in-real-time path (Success Criterion 1 + 4):** `runtime/ws_bus.py::ws_broadcast` emits `{**levels.snapshot(), ...}` at 30 Hz; `Levels.snapshot()` always returns `music/voice/mic`. Phase 51 just added the emit-boundary empty-frame guard (`ws_bus.py:289-298`). The live meters moving = the bus carrying real `music` RMS. The automatable proof is the existing `integration` ws-tap harness; the on-screen confirmation is Kaan-action.

---

## Question 2 — Does the BPM out-of-range gate + stabilizer together guarantee no out-of-range BPM reaches the bus?

**Answer: yes for the stabilizer's own ring output, but there is a residual path through `validate_bpm` that this phase must pin with a regression — and the bus reads `state.bpm` directly, so the contract is "state.bpm never > BPM_VALID_MAX".**

The chain in `state/refresh.py::_tick_once` (verified live):
1. `raw_bpm = estimate_bpm(audio_buf, seconds=6.0)` — golden/pinned, lag 30–60 → BPM ~100–200. **Do not touch** (`audio/features.py`).
2. **`bpm_ring.append(raw_bpm)` → `_stabilize_bpm(bpm_ring)`** (refresh.py:84-97): lower-median of samples in `[BPM_VALID_MIN=100, BPM_VALID_MAX=180]`; drops everything outside that band BEFORE the median. Returns `0.0` if no in-range sample. `if stabilized > 0: bpm_cache = stabilized` — keeps last-good otherwise. **This is the shipped `fd25337` work — leave it alone.**
3. `validate_bpm(bpm_cache, active_profile)` (genre/bpm_validator.py): half/double snap to `profile.bpm_range`. Pass-through when in range; **out-of-range passes through unchanged** (per its own docstring it relies on "the existing `BPM_VALID_MIN/MAX` gate downstream").
4. `state.bpm = bpm_cache` is written (refresh.py:295) inside `with state._lock:`.
5. `ws_bus.py:272` puts `"bpm": state.bpm` on the wire; `_build_session_snapshot` (ws_bus.py:127) maps `raw_bpm = state.bpm`, `bpm = raw_bpm if raw_bpm > 0 else None`.

**The residual concern:** step 3 (`validate_bpm`) can in principle re-introduce an out-of-range value because it "passes through unchanged" when no half/double snap fits. But since `_stabilize_bpm` already clamps the input of step 3 to `[100,180]` (it only ever assigns `bpm_cache` from an in-range median), `validate_bpm`'s pass-through and its `*2` / `/2` corrections all stay bounded by the profile's `bpm_range` (the widest shipped profile range upper bound is dnb 180, ≤ BPM_VALID_MAX). **The phase's job is to PIN this with a real-trace regression**, not to add a new gate. CONTEXT explicitly says: "confirm the gate + stabilizer together guarantee no out-of-range BPM reaches the bus, and add a real-trace regression."

**The real-trace regression shape (from CONTEXT §specifics):** replay the measured bimodal psytrance distribution (≈66% @130, ≈28% @194-200 subdivision-lock, ≈6% scatter) through a rolling ring of 5 driven into `_tick_once` (or `_stabilize_bpm` + `validate_bpm` composed), and assert the value that would reach `state.bpm` / the bus **never exceeds BPM_VALID_MAX (180)**. `tests/state/test_bpm_stabilize.py::test_rolling_ring_replay_never_leaks_out_of_range` already does the `_stabilize_bpm`-only version; the new test must drive it **through `_tick_once`** so the *bus-facing* `state.bpm` is what's asserted (closing the "200 reached the live bus" bug at the integration boundary, not just the unit).

**Edge — the psytrance profile range:** psytrance bpm_range ~[138,150]; with that profile active, `validate_bpm` will half-snap a 200 → still 200 (no fit), but `_stabilize_bpm` already dropped 200 before `bpm_cache` was set, so `validate_bpm` never sees it. A 290 lock → `_stabilize_bpm` drops it (>180); a 145 → passes; a 72 (half-time) → `validate_bpm` doubles to 144 (in [138,150]). All bounded ≤ BPM_VALID_MAX. The regression must include a psytrance-profile-active variant.

---

## Question 3 — How is genre chosen today, and what exactly does the GENRE-01 auto-detector add?

**Answer: today the profile is env-pinned at startup and never auto-detected; there is a *separate* coarse `_classify_active_genre` that writes `state.active_genre` but it is NOT profile-library-aware and only knows house/techno/hard_tek. GENRE-01 adds a NEW profile-library-driven DSP detector that picks the active GenreProfile from real features each tick.**

Two distinct genre surfaces exist live — **do not conflate them**:

| Surface | Where | What it is | Phase 52 action |
|---|---|---|---|
| `apply_genre_env()` | `_main_helpers.py:17` | Reads `VIBEMIX_GENRE_PROFILE` (default `"techno"`), calls `set_active_profile(name)` once at boot. Never reads audio. | Keep as the **override** — when env pins a real genre, auto-detect yields to it. |
| `_classify_active_genre(bpm, feats)` → `state.active_genre` | `refresh.py:100` | Coarse BPM-band (`GENRE_BPM_BANDS`: house 118-128 / techno 128-138 / hard_tek 140-180 / unknown) + a hard_tek centroid gate. Writes `state.active_genre` ("house"/"techno"/"hard_tek"/"unknown"), consumed by the renderer's GenreRouter (`ws_bus.py:276`). | **Leave untouched** — it is a renderer signal, not the profile selector. The new detector is additive. |
| `set_active_profile` / `get_active_profile` | `genre/profile.py:213/227` | Module-level `_ACTIVE_PROFILE` singleton. `_tick_once:221` re-reads it per tick (`get_active_profile()`) so a mid-session flip is honored. | **This is the selector the new detector drives.** The detector calls `set_active_profile(detected_name)` (or leaves it on `unknown`/None) each tick when env did NOT pin a genre. |

**The GENRE-01 detector — grounded, pure-numpy, anti-slop (from CONTEXT §decisions):**
- **Inputs (already computed each tick in `_tick_once`):** `bpm_cache` (stabilized BPM), `feats` bands (`sub_share`/`low_share`/`mid_share`/`high_share` from `snapshot_features`), `smoothed_crest` (the `crest_factor` EMA). No new audio I/O.
- **Scoring:** for each profile in `list_profiles()` (now including psytrance), score nearest-match across three axes: (1) BPM in `profile.bpm_range`, (2) `band_signature` distance — each of sub/low/mid/high inside the profile's `[lo,hi]` band → in-band reward, else distance penalty, (3) `expected_crest_factor` membership. Sum/normalize into a confidence in [0,1].
- **Anti-slop (NON-NEGOTIABLE):**
  - **Confidence gate + `unknown` fallback** — when the best score is below a threshold (or two profiles tie within a margin), emit `unknown`, NOT a guess. Mirror `derive_audible_track`'s `(unsure)`/`unknown` confidence pattern (`track_resolver.py`).
  - **Hysteresis** — debounce profile switches with an N-tick dwell so genre doesn't flip bar-to-bar. Mirror `HysteresisState` + `_apply_hysteresis` in `genre/detector.py` (3-tick dwell, immediate commit to a "silent/unknown-on-death" floor).
  - **Env override wins** — if `apply_genre_env()` pinned a non-None profile (i.e. `VIBEMIX_GENRE_PROFILE` was explicitly set to a real genre), the auto-detector must NOT call `set_active_profile`. CONTEXT: "Env stays as an explicit override — when the user pins a genre, auto-detection yields to it." (Detector needs to know whether env pinned; thread an `env_pinned: bool` flag from `main()` → loop → `_tick_once`, OR have the detector no-op when env is set. Recommended: a module-level `genre_auto_enabled` flag set in `main()` after `apply_genre_env()`.)
  - **No CLAP/MERT/OpenL3, no new heavy deps** — pure numpy on existing features. A Gemini-based confirmation pass is explicitly **out of scope** (v.next).

**The `psytrance.json` profile (mirror the locked schema in `profile.py`):**
- `bpm_range`: ~[138, 150] (psy/full-on; CONTEXT). Within `[BPM_VALID_MIN, BPM_VALID_MAX]` ✓.
- `band_signature`: heavy `sub`/`low` (offbeat rolling bass), modest mid/high. Recommended sub [0.30,0.50], low [0.20,0.35], mid [0.08,0.20], high [0.05,0.15] (shares ~sum to 1).
- `expected_crest_factor`: high (psy masters are punchy but dynamic vs techno) — [4.0, 7.0] recommended.
- `vocal_likelihood`: `"rare"`.
- `absolute_thresholds`: silent/low/peak RMS mirroring techno (0.012 / 0.040 / 0.110) as a sane default.
- build/breakdown/drop thresholds tuned slightly steeper than techno (psy builds are aggressive): build_climb_threshold ~0.028, breakdown_ratio 0.4, drop_jump_threshold 0.065.
- **MUST validate via the hand-written `_parse_profile`** (`profile.py:87`) — no pydantic (Critical Constraint 6). A test loading `load_profile("psytrance")` must return a `GenreProfile` with these values.

**Landmine — test count assertion will break:** `tests/state/test_genre_profile.py::test_list_profiles_returns_all_five` hard-asserts `list_profiles() == ["disco","drum_and_bass","house","pop","techno"]` and `PROFILE_NAMES` is that exact list. Adding `psytrance.json` makes `list_profiles()` return 6 entries (psytrance sorts after pop, before techno). **The plan MUST update this assertion** (rename the test or expand the expected list to include psytrance) or the default suite goes red. Same for any `sensible-values` loop that iterates `PROFILE_NAMES`.

---

## Question 4 — How does GENRE-02 surface detected genre + confidence on the bus without breaking Phase 51's empty-frame guard?

**Answer: add two ADDITIVE static keys (`detected_genre`, `genre_confidence`) to the mascot frame dict in `ws_broadcast`, sourced from two new MusicState fields. The empty-frame guard only checks `music/voice/mic`, so static additive keys cannot trip it.**

Verified live (`ws_bus.py:266-298`):
- The mascot frame is a literal dict: `{**levels.snapshot(), "audible":..., "deck":..., "phase":..., "bpm":..., "mood":..., "bpm_confidence":..., "downbeat_phase":..., "beat_phase":..., "active_genre":..., "emotion":..., "reaction_intent":...}`.
- The emit-boundary guard (`:289-298`): `if not mascot_frame or not all(k in mascot_frame for k in ("music","voice","mic")): skip`. Adding keys never removes the meter keys → guard never trips on the new fields. ✓ (CONTEXT confirms this; the research verifies it at the code line.)

**Plan:**
- Add `detected_genre: str = "unknown"` and `genre_confidence: float = 0.0` to `MusicState` (`music_state.py`) — additive defaults so golden-equivalence holds, written ONLY in `_tick_once` (single-writer rule).
- The GENRE-01 detector writes them inside the existing `with state._lock:` batch in `_tick_once` (alongside `genre_profile_name` / `active_genre`).
- `ws_bus.py` mascot frame gains `"detected_genre": state.detected_genre, "genre_confidence": state.genre_confidence`.
- **Anti-slop on the wire:** when confidence is below the gate, `detected_genre == "unknown"` and `genre_confidence` carries the (low) score — never a hallucinated label. Mirror the `active_genre` "unknown" honesty already on the wire.
- **Do NOT replace `active_genre`** — it has existing renderer subscribers (GenreRouter) and `test_ws_bus_phase22_fields.py` pins it. The new fields are parallel.
- Distinguish `detected_genre` (full profile-library name incl. psytrance/disco/pop/dnb) from `active_genre` (the coarse house/techno/hard_tek/unknown renderer signal). They can disagree; that's fine — they answer different questions.
- A ws-bus test (mirror `test_ws_bus_phase22_fields.py`) must assert the two new keys appear on the captured payload and round-trip the values.

---

## Validation Architecture

> Required section — drives `52-VALIDATION.md` (Nyquist). All commands runnable from repo root.

### Test framework
- **pytest 7.x** (`pyproject.toml [tool.pytest.ini_options]`, `addopts = "-ra --strict-markers"`).
- Quick run: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <files>` (or `uv run pytest -q <files>`).
- Full suite: `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q`.
- Opt-in markers used here: `integration` (real ws-server tap), `macos_audio` (real BlackHole — Kaan-action live tap).

### What is automatable (engineering, default + opt-in suites)
| Behavior | Requirement | Test type | Command |
|---|---|---|---|
| BlackHole 48 kHz guard fires for the listening INPUT device when device is at 44.1k | BRINGUP-02 | unit (mock `sd.query_devices`) | `pytest -q tests/audio/test_sample_rate_guard.py` |
| Stabilizer + validate_bpm chain: bus-facing `state.bpm` never > BPM_VALID_MAX on a real harmonic-leak trace (techno + psytrance profile) | BRINGUP-02 | unit/integration (drive `_tick_once`) | `pytest -q tests/state/test_bpm_bus_grounding.py` |
| Audio-derived features (rms/bands/onset) stay in valid range, no NaN, across a synthetic full-set replay | BRINGUP-02 | unit | `pytest -q tests/state/test_feature_grounding.py` |
| `load_profile("psytrance")` returns a schema-valid GenreProfile with the locked values | GENRE-01 | unit | `pytest -q tests/state/test_psytrance_profile.py` |
| `list_profiles()` includes psytrance; existing 5-list assertion updated | GENRE-01 | unit | `pytest -q tests/state/test_genre_profile.py` |
| DSP detector picks correct profile from synthetic feature vectors per genre; ambiguous/out-of-library → `unknown` (no false-confident pick) | GENRE-01 | unit | `pytest -q tests/state/test_genre_autodetect.py` |
| Detector hysteresis: no bar-to-bar flicker on alternating borderline vectors | GENRE-01 | unit | `pytest -q tests/state/test_genre_autodetect.py` |
| Env override wins: when `VIBEMIX_GENRE_PROFILE` pinned, auto-detector does not flip the active profile | GENRE-01 | unit | `pytest -q tests/state/test_genre_autodetect.py` |
| `detected_genre` + `genre_confidence` on the mascot bus frame; `unknown` when unsure; never trips the empty-frame guard | GENRE-02 | unit (ws payload capture) | `pytest -q tests/runtime/test_ws_bus_genre_fields.py` |
| Full suite still green (no golden-equivalence regression) | all | suite | `PYTHONPATH=src python3 -m pytest -q` |

### What is manual / Kaan-action (real hardware — autonomous carveout)
| Behavior | Requirement | Why manual | Instructions |
|---|---|---|---|
| Real master output through BlackHole reaches co-host @48 kHz; on-screen meters move in time with music | BRINGUP-02 (SC1/SC4) | needs real audio device + eyes on UI | Play a known-BPM track → BlackHole 2ch; run `uv run python -m vibemix`; tap `ws://127.0.0.1:8765`; confirm `music` level tracks the track and `bpm` lands in the track's real band. Runnable recipe shipped as a `macos_audio`-marked live test. |
| Genre auto-detect tracks reality across Kaan's whole library (psytrance no longer misclassifies; never a wrong confident label) | GENRE-01/02 | needs his library + his ear | Drive ≥2 genres live; confirm `detected_genre` matches or is `unknown`, never a wrong confident label. (Per `project_phase_16_kaan_dj_testing`.) |

### Sampling rate
- After every task commit: run that task's quick command.
- After every wave: run the full default suite.
- Before verify: full default suite green; the `macos_audio` live tap is Kaan-action and recorded as deferred.

---

## Pitfalls (verified, must respect)
1. **Do NOT re-implement `_stabilize_bpm`** — it shipped in `fd25337`. Confirm + regress only.
2. **Do NOT touch `estimate_bpm`** (`audio/features.py`) — golden/pinned.
3. **Do NOT replace `active_genre` / `_classify_active_genre`** — it is a live renderer signal with subscribers + a pinned test. New detector + fields are additive/parallel.
4. **`test_list_profiles_returns_all_five` WILL break** when psytrance is added — update it in the same plan/wave that adds the profile or the suite goes red.
5. **Single-writer rule** — only `_tick_once` writes MusicState. New `detected_genre`/`genre_confidence` fields written there, inside `with state._lock:`.
6. **No pydantic / no new heavy deps** — psytrance profile validates through the hand-written `_parse_profile`; detector is pure numpy.
7. **Env override** — auto-detector must yield when `VIBEMIX_GENRE_PROFILE` pins a real genre. Thread the "env pinned" signal explicitly; do not guess from `get_active_profile()` alone (env default is `techno`, so a non-None active profile does NOT by itself mean the user pinned it — need an explicit flag set right after `apply_genre_env()`).
8. **Empty-frame guard** (`ws_bus.py:289`) only checks `music/voice/mic` — additive static keys are safe, but the ws-bus test must still confirm a full frame round-trips.

---

## RESEARCH COMPLETE
