---
phase: 52
slug: audio-path-feature-grounding
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-21
---

# Phase 52 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Verified against HEAD `177ff38`. The BPM median-ring stabilizer is already
> shipped (`fd25337`) — this phase confirms the gate + regresses it, it does
> NOT re-implement it.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (`[tool.pytest.ini_options]`, `--strict-markers`) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <file>` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~60-90 seconds (default suite); +real-hw live tap is `macos_audio`, Kaan-action |

---

## Sampling Rate

- **After every task commit:** Run the task's quick command (single test file).
- **After every plan wave:** Run the full default suite.
- **Before `/gsd:verify-work`:** Full default suite must be green. The `macos_audio` live tap is Kaan-action and recorded as deferred — not a default-suite gate.
- **Max feedback latency:** ~90 seconds (full suite).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 52-01-01 | 01 | 1 | BRINGUP-02 | — | Listening-input stream open rejects a 44.1k BlackHole with `SampleRateMismatchError` before audio is consumed | unit | `pytest -q tests/audio/test_sample_rate_guard.py` | ❌ W0 | ⬜ pending |
| 52-01-02 | 01 | 1 | BRINGUP-02 | — | Bus-facing `state.bpm` never exceeds BPM_VALID_MAX on a real harmonic-leak trace (techno + psytrance profile) | unit/integration | `pytest -q tests/state/test_bpm_bus_grounding.py` | ❌ W0 | ⬜ pending |
| 52-01-03 | 01 | 1 | BRINGUP-02 | — | rms/bands/onset_density stay finite + in-range across a synthetic full-set replay (no NaN, no spike leak) | unit | `pytest -q tests/state/test_feature_grounding.py` | ❌ W0 | ⬜ pending |
| 52-01-04 | 01 | 1 | BRINGUP-02 | — | Runnable live-tap recipe (`macos_audio`) — meters move + bpm in-band on real BlackHole | manual/opt-in | `pytest -m macos_audio -q tests/test_audio_macos_live.py` | ✅ (extends existing) | ⬜ pending |
| 52-02-01 | 02 | 1 | GENRE-01 | — | `psytrance.json` loads via hand-written `_parse_profile` into a valid GenreProfile with locked values | unit | `pytest -q tests/state/test_psytrance_profile.py` | ❌ W0 | ⬜ pending |
| 52-02-02 | 02 | 1 | GENRE-01 | — | `list_profiles()` includes psytrance; the existing 5-list assertion is updated (suite stays green) | unit | `pytest -q tests/state/test_genre_profile.py` | ✅ (edit) | ⬜ pending |
| 52-03-01 | 03 | 2 | GENRE-01 | — | DSP detector picks the correct profile from synthetic per-genre vectors | unit | `pytest -q tests/state/test_genre_autodetect.py` | ❌ W0 | ⬜ pending |
| 52-03-02 | 03 | 2 | GENRE-01 | — | Ambiguous / out-of-library vector → `unknown` (no false-confident pick); hysteresis stops bar-to-bar flicker | unit | `pytest -q tests/state/test_genre_autodetect.py` | ❌ W0 | ⬜ pending |
| 52-03-03 | 03 | 2 | GENRE-01 | — | Env override wins: with `VIBEMIX_GENRE_PROFILE` pinned, auto-detector does not flip the active profile | unit | `pytest -q tests/state/test_genre_autodetect.py` | ❌ W0 | ⬜ pending |
| 52-03-04 | 03 | 2 | GENRE-01 | — | Detector wired into `_tick_once`, writes `detected_genre`/`genre_confidence`; existing refresh tests stay green | unit | `pytest -q tests/state/test_refresh.py` | ✅ (edit) | ⬜ pending |
| 52-04-01 | 04 | 3 | GENRE-02 | — | `detected_genre`+`genre_confidence` on the mascot bus frame; round-trip values; `unknown` honesty | unit | `pytest -q tests/runtime/test_ws_bus_genre_fields.py` | ❌ W0 | ⬜ pending |
| 52-04-02 | 04 | 3 | GENRE-02 | — | New keys never trip the Phase-51 empty-frame guard; existing ws_bus tests stay green | unit | `pytest -q tests/runtime/test_ws_bus.py tests/runtime/test_ws_bus_empty_frames.py tests/runtime/test_ws_bus_phase22_fields.py` | ✅ (existing) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/audio/test_sample_rate_guard.py` — new, BRINGUP-02 input-device guard
- [ ] `tests/state/test_bpm_bus_grounding.py` — new, BRINGUP-02 BPM-to-bus regression
- [ ] `tests/state/test_feature_grounding.py` — new, BRINGUP-02 feature-range regression
- [ ] `tests/state/test_psytrance_profile.py` — new, GENRE-01 profile load
- [ ] `tests/state/test_genre_autodetect.py` — new, GENRE-01 detector
- [ ] `tests/runtime/test_ws_bus_genre_fields.py` — new, GENRE-02 bus fields
- [ ] `src/vibemix/state/genre/profiles/psytrance.json` — new profile (data, not test)
- [ ] `src/vibemix/state/genre/genre_autodetect.py` (or equivalent module) — new detector

*Existing infrastructure (conftest `int16_sine`, `_tick_once` test harness, ws-payload capture harness) covers fixtures — no new framework install.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real master output → BlackHole reaches co-host @48 kHz; on-screen meters move in time with music | BRINGUP-02 (SC1/SC4) | needs real audio device + eyes on UI | Play a known-BPM track into BlackHole 2ch; `uv run python -m vibemix`; tap `ws://127.0.0.1:8765`; confirm `music` tracks the track + `bpm` lands in the real band. Runnable as the `macos_audio` live recipe (52-01-04). |
| Genre auto-detect tracks reality across Kaan's whole library; psytrance no longer misclassifies; never a wrong confident label | GENRE-01/GENRE-02 (SC5/SC6) | needs his library + his ear | Drive ≥2 genres live; confirm `detected_genre` matches the played genre or is `unknown`, never a wrong confident label (`project_phase_16_kaan_dj_testing`). |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-21
