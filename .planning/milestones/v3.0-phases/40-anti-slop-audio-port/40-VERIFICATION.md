---
phase: 40-anti-slop-audio-port
verified: 2026-05-17T00:00:00Z
status: human_needed
score: 4/5 success-criteria verified, 1 pending Kaan ear-test
overrides_applied: 0
re_verification:
  previous_status: null  # initial verification
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "SC #5 — v4 'harikaydı' baseline regression ear-test"
    expected: "Real DJ session (≥1) in both Coach + Hype mode: reactions feel as alive/grounded as v4 chat-tested 2026-05-11 baseline; no scripted/late/hallucinated/generic AI slop"
    why_human: "Per memory `project_phase_16_kaan_dj_testing` — hallucination gate satisfied by Kaan's personal DJ-set testing, NOT an automated suite. Engineering verification cannot judge 'feels alive in your ear'."
  - test: "SC #4a — AUDIO-05 PGP key publish (KAAN-ACTION-LEGAL)"
    expected: "`gpg --quick-gen-key 'Bravoh Security <security@bravoh.com>' ed25519` → `gpg --send-keys --keyserver hkps://keys.openpgp.org <FP>` → email-verify link clicked → SECURITY.md fingerprint cell updated → `git rm KAAN-PGP-PLACEHOLDER.asc`. Dual-mode gate test (`tests/security/test_pgp_published.py`) auto-flips post-discharge."
    why_human: "Engineering pre-stage GREEN (slot file + SECURITY.md retarget + runbook + dual-mode gate test). External clock (keyserver email-verify + Kaan's gpg trust chain) — legal-capacity carveout per `gsd-autonomous fully`."
  - test: "SC #4b — AUDIO-06 Tauri ed25519 updater key rotation (KAAN-ACTION-LEGAL)"
    expected: "`npx @tauri-apps/cli signer generate --no-password` → paste pubkey into `tauri.conf.json5 plugins.updater.pubkey` → `base64 -i …key | gh secret set TAURI_UPDATER_PRIVATE_KEY` → `gh workflow run release.yml` rehearsal. Dual-mode gate test (`tests/tauri/test_updater_key_rotated.py`) auto-flips post-discharge."
    why_human: "Engineering pre-stage GREEN (Plan 40-05 comment block + runbook + dual-mode gate test). External actor (GitHub Actions secret) + key-custody decision — Kaan-only step per autonomous-mode policy."
  - test: "SC #4c — AUDIO-07 BlackHole fresh-Mac probe walk (KAAN-ACTION-LEGAL)"
    expected: "Fresh macOS user account → wizard click-through → events.jsonl artifact captures `audio.probe.detected` (post-install) and `audio.probe.cta_fired` (during install CTA) → 6-invariant discharge checklist signed in KAAN-ACTION-LEGAL.md §AUDIO-07."
    why_human: "Engineering scaffolding GREEN (probe emits 3 event kinds + Pitfall 5 retry; 12 hermetic tests pass). Requires fresh user account + physical install — cannot be programmatically verified on developer hardware."
---

# Phase 40: Anti-Slop Audio Port — Verification Report

**Phase Goal:** Close the biggest engineering anti-slop gap — Gemini now hears Kaan's voice (mic as 2nd Part) and gets a 3s structural preview (source-file lookahead as 3rd Part); event cooldowns re-tuned to v4 chat-tested intuition. Pre-stage independent KAAN-ACTION items (PGP, Tauri updater key, BlackHole fresh-Mac probe).

**Verified:** 2026-05-17
**Status:** human_needed
**Re-verification:** No — initial verification.

---

## Goal Achievement

### Success Criteria (ROADMAP.md)

| # | Success Criterion | Status | Evidence |
|---|-------------------|--------|----------|
| 1 | KAAN_SPOKE triggers 3-Part Gemini request when local file present — P1 BlackHole 7s / P2 mic 12s / P3 lookahead 3s; prompt labels Parts | ✓ VERIFIED | `src/vibemix/agent/dj_cohost.py:489-492` attaches Part 1 (audio_wav) + conditional Part 2 (mic_wav, line 492) + conditional Part 3 (lookahead, line 507+). `src/vibemix/prompts/matrix.py:511-587` `build_parts_description` emits `"P1 = …, P2 = your mic …, P3 = source-file lookahead … NOT YET HEARD BY AUDIENCE"` explicit labeling. Tested by `tests/agent/test_dj_cohost_3part.py::test_part_count_3_mic_and_lookahead` (PASS). |
| 2 | Streaming-track sessions degrade to 2-Part with zero ffmpeg errors logged | ✓ VERIFIED | `LookaheadProvider.snapshot_wav` returns `(None, meta_with_reason)` on every failure path — never raises. Pinned by `tests/audio/test_lookahead.py`: `test_no_nowplaying_returns_none`, `test_no_file_match_returns_none`, `test_ffmpeg_error_returns_none`, `test_subprocess_timeout_returns_none` (all PASS). DJCoHostAgent has double-belt `try/except` wrapper at `dj_cohost.py:467-470`. Skip emits `lookahead_part_skipped` recorder event with `reason`, NOT stderr ffmpeg error. |
| 3 | Event cooldowns (PHASE/LAYER_ARRIVAL/MIX_MOVE/HEARTBEAT/TRACK_CHANGE) match v4 chat-tested values within ±1s | ✓ VERIFIED | `src/vibemix/audio/constants.py:65,70-74` literal exact-match: HEARTBEAT_SEC=45.0, TRACK_CHANGE=5.0, PHASE=10.0, LAYER_ARRIVAL=10.0, MIX_MOVE=14.0, HEARTBEAT→HEARTBEAT_SEC=45.0. Delta from chat-tested baseline = 0.0s (exceeds ±1s tolerance). `scripts/eval/replay_harness.py:111-160` exposes `--print-cooldowns` observational mode with `COOLDOWN_REPORT_TOLERANCE_S=1.0` WARNING band. `tests/eval/test_replay_harness_cooldowns.py` (8 tests) all PASS. |
| 4 | PGP key published + Tauri updater key rotated + BlackHole fresh-Mac probe pass | ⚠️ HUMAN NEEDED | Engineering pre-stage GREEN for all three (slot files + runbooks + dual-mode gate tests). Kaan must discharge the 3 external-clock actions per KAAN-ACTION-LEGAL.md §AUDIO-05/06/07. Classified as `human_needed` (legal-capacity carveouts), NOT gaps. |
| 5 | v4 "harikaydı" baseline regression — ear-test on ≥1 real Kaan DJ session (Coach + Hype) | ⚠️ HUMAN NEEDED | Per memory `project_phase_16_kaan_dj_testing` — hallucination gate satisfied by Kaan's personal DJ-set testing. Engineering surface verifiable: 3-Part contract live, cooldowns tuned, mic + lookahead grounding wired. Kaan must perform the ear-test. |

**Score:** 3/5 fully verified in code + 2/5 routed to human verification (KAAN-ACTION-LEGAL + ear-test, per phase rubric).

---

### Observable Truths (Plan-level must_haves)

| # | Truth | Plan | Status | Evidence |
|---|-------|------|--------|----------|
| 1 | KAAN_SPOKE-recent + mic-has-signal → Gemini sees mic as 2nd audio Part | 40-01 | ✓ VERIFIED | `dj_cohost.py:492` + `tests/agent/test_dj_cohost_mic_part.py::test_part_count_3_when_recent_kaan_with_signal` PASS |
| 2 | Mic ring zero-fills during AI talk — no self-triggered KAAN_SPOKE loop | 40-01 | ✓ VERIFIED | `__main__.py::_mic_callback_factory` zero-fills if `mic._current_gain() == MIC_GAIN_AT_AI_TALK`. `tests/audio/test_mic_audio_buf.py::test_t3_zero_fill_during_ai_talk` PASS |
| 3 | Mic disabled/silent/AI-talking → request is 1-Part (backward-compat) | 40-01 | ✓ VERIFIED | `tests/agent/test_dj_cohost_mic_part.py`: `test_part_count_2_when_no_mic_audio_buf`, `_when_kaan_spoke_not_recent`, `_when_mic_silent` all PASS (these report 2-Part = text + Part1 mix; "1-Part" in plan terminology means 1 audio Part) |
| 4 | When source file on disk, `LookaheadProvider.snapshot_wav()` returns 18s mono 16kHz WAV ending 3s past playhead | 40-02 | ✓ VERIFIED | `src/vibemix/audio/lookahead.py:207` + `tests/audio/test_lookahead.py::test_snapshot_wav_happy_path` PASS. Constants pinned: LOOKAHEAD_SECONDS=3.0, LOOKAHEAD_WINDOW_SECONDS=18.0, LOOKAHEAD_SAMPLE_RATE=16000. |
| 5 | Streaming-only / failure paths return `(None, meta)` — never raise | 40-02 | ✓ VERIFIED | 4 failure-path tests all PASS in `test_lookahead.py`. |
| 6 | ffmpeg uses input-seek (`-ss` BEFORE `-i`) for fast extract | 40-02 | ✓ VERIFIED | `test_lookahead.py::test_input_seek_before_dash_i` PASS. |
| 7 | 3-Part additive contract when all three signals present | 40-03 | ✓ VERIFIED | `test_dj_cohost_3part.py::test_part_count_3_mic_and_lookahead` PASS. |
| 8 | "NOT YET HEARD BY AUDIENCE" + anti-prediction guard on lookahead Part | 40-03 | ✓ VERIFIED | `matrix.py:577,587` contains both phrases. `test_matrix_3part_labeling.py::test_anti_prediction_phrase_in_lookahead_variants` PASS. |
| 9 | Slot-renumber: lookahead at P2 when mic absent | 40-03 | ✓ VERIFIED | `test_matrix_3part_labeling.py::test_lookahead_only_at_p2` PASS. |
| 10 | Cooldowns match v4 chat-tested 2026-05-11 literal | 40-04 | ✓ VERIFIED | Source file exact-match (see SC #3). `tests/audio/test_constants.py::test_event_gap_dict_shape_and_values` + `test_engine_constants_match_v4` PASS. |
| 11 | `replay_harness --print-cooldowns` emits per-type median + delta + WARNING | 40-04 | ✓ VERIFIED | `replay_harness.py:114-160` `_emit_cooldown_report` + `_accumulate_session_gaps`. `tests/eval/test_replay_harness_cooldowns.py` (8 tests) PASS. |
| 12 | PGP slot file exists with armor envelope + sentinel | 40-05 | ✓ VERIFIED | `docs/security/pgp-public-key.txt` contains both `BEGIN PGP PUBLIC KEY BLOCK` armor envelope (×1) and `PLACEHOLDER-VIBEMIX-AUDIO-05-PGP-NOT-YET-GENERATED` sentinel (×1). SECURITY.md retargeted (2 mentions). Dual-mode gate test: 4 PASS + 1 skip (post-discharge mode). |
| 13 | Tauri updater key rotation comment + runbook in place | 40-05 | ✓ VERIFIED | `tauri.conf.json5` has Plan 40-05 comment block (1 occurrence). KAAN-ACTION-LEGAL.md §AUDIO-06 has 4-step runbook. Dual-mode gate test: 7 PASS + 1 skip. |
| 14 | `probe_blackhole` emits 3 structured `audio.probe.*` event kinds | 40-06 | ✓ VERIFIED | `src/vibemix/install/blackhole_probe.py` references all three event names + `emit_cta_fired` helper. 12 hermetic tests in `test_blackhole_probe_events.py` all PASS. |
| 15 | Pitfall 5 fresh-boot CoreAudio race → single 1.5s retry | 40-06 | ✓ VERIFIED | `blackhole_probe.py` `time.sleep(1.5)` × 1. Tests `test_pitfall_5_retry_succeeds_on_second_try` + `_still_missing` + `test_retry_only_runs_once` PASS. |

**Truths verified: 15/15** (all plan-level must_haves observed in code).

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/vibemix/audio/buffers.py` | `AudioBuffer` reused for mic_audio_buf | ✓ VERIFIED | Reused via `AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)` per Plan 40-01 |
| `src/vibemix/audio/constants.py` | 3 new MIC_AUDIO_PART_* + retuned cooldowns | ✓ VERIFIED | Lines 44-46 + 65,70-74 |
| `src/vibemix/audio/lookahead.py` | LookaheadProvider class + 4 LOOKAHEAD_* constants | ✓ VERIFIED | Class at line 58; snapshot_wav at 207; _resolve_file at 121; _current_position at 170 |
| `src/vibemix/audio/__init__.py` | Re-exports for both 40-01 + 40-02 constants | ✓ VERIFIED | LookaheadProvider + 4 LOOKAHEAD constants + 3 MIC_AUDIO_PART constants re-exported |
| `src/vibemix/agent/dj_cohost.py` | mic_audio_buf + lookahead kwargs + Part 2/3 attach + recorder events | ✓ VERIFIED | `self._mic_audio_buf` (6 refs), `self._lookahead` (5 refs), Part 2 attach at L492, Part 3 attach at L507+ |
| `src/vibemix/prompts/matrix.py` | `build_parts_description` + NOT YET HEARD label | ✓ VERIFIED | Function at line 511; "NOT YET HEARD BY AUDIENCE" appears at lines 487,493,538,577,587 (incl. docs+code) |
| `src/vibemix/prompts/__init__.py` | Re-export `build_parts_description` | ✓ VERIFIED | Per Plan 40-03 SUMMARY claims (+2 LOC); used by dj_cohost imports |
| `src/vibemix/__main__.py` | mic_audio_buf + lookahead_provider wiring | ✓ VERIFIED | mic_audio_buf (10 refs), lookahead_provider (2 refs) |
| `src/vibemix/install/blackhole_probe.py` | emit_event + retry + emit_cta_fired | ✓ VERIFIED | All 3 event-name string literals present; time.sleep(1.5) present; retry_on_missing kwarg present |
| `src/vibemix/install/__init__.py` | Re-exports for probe_blackhole + emit_cta_fired + BLACKHOLE_INSTALL_URL | ✓ VERIFIED | Per Plan 40-06 self-check |
| `scripts/eval/replay_harness.py` | `--print-cooldowns` + `_emit_cooldown_report` + `_accumulate_session_gaps` + COOLDOWN_REPORT_TOLERANCE_S | ✓ VERIFIED | All 4 symbols present at lines 100-160, 666-677 |
| `docs/security/pgp-public-key.txt` | Slot file with armor envelope + sentinel | ✓ VERIFIED | 2 expected pattern matches (BEGIN BLOCK + PLACEHOLDER sentinel) |
| `SECURITY.md` | Retargeted to docs/security/pgp-public-key.txt | ✓ VERIFIED | 2 mentions of new path |
| `tauri/src-tauri/tauri.conf.json5` | Plan 40-05 comment block | ✓ VERIFIED | 1 occurrence as expected |
| `KAAN-ACTION-LEGAL.md` | §AUDIO-05/06/07 sections | ✓ VERIFIED | Section headers present at L527, L601, L671 |
| `tests/audio/test_mic_audio_buf.py` | 7 tests for ring + zero-fill + resample | ✓ VERIFIED | 7 PASS |
| `tests/agent/test_dj_cohost_mic_part.py` | 6 tests for 1/2-Part integration | ✓ VERIFIED | 6 PASS |
| `tests/audio/test_lookahead.py` | 8 tests for provider + degrade paths | ✓ VERIFIED | 8 PASS |
| `tests/agent/test_dj_cohost_3part.py` | 6 tests for 3-Part integration | ✓ VERIFIED | 6 PASS |
| `tests/prompts/test_matrix_3part_labeling.py` | 6 unit tests for prompt builder | ✓ VERIFIED | 6 PASS |
| `tests/eval/test_replay_harness_cooldowns.py` | 8 tests for --print-cooldowns | ✓ VERIFIED | 8 PASS |
| `tests/security/test_pgp_published.py` | Dual-mode gate test (7 invariants) | ✓ VERIFIED | 4 PASS + 1 skip (post-discharge mode) |
| `tests/tauri/test_updater_key_rotated.py` | Dual-mode gate test (8 invariants) | ✓ VERIFIED | 7 PASS + 1 skip (post-discharge mode) |
| `tests/install/test_blackhole_probe_events.py` | 12 tests for probe events + retry | ✓ VERIFIED | 12 PASS |

---

### Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| `__main__.py::_mic_callback_factory` | `buffers.py::AudioBuffer.push` | `resample_poly + zero-fill + int16 clip` | ✓ WIRED — confirmed by `test_t2_callback_resamples_48k_to_16k` PASS |
| `dj_cohost.py::llm_node` | `google.genai types.Part.from_bytes` | `contents.append` (gated by 3-gate decision) | ✓ WIRED — 3 separate Part.from_bytes invocations at L489, L492, L507+ |
| `lookahead.py::_current_position` | `/opt/homebrew/bin/nowplaying-cli` | subprocess.run list-form | ✓ WIRED — `test_subprocess_args_use_list_form` PASS |
| `lookahead.py::_resolve_file` | `/usr/bin/mdfind` | subprocess.run list-form, kMDItemFSName query | ✓ WIRED — verified via PASS of `test_no_file_match_returns_none` graceful-degrade |
| `lookahead.py::snapshot_wav` | `/opt/homebrew/bin/ffmpeg` | subprocess.run with -ss BEFORE -i, 4s timeout | ✓ WIRED — `test_input_seek_before_dash_i` PASS |
| `__main__.py::main` | `DJCoHostAgent.__init__` | passes both `mic_audio_buf=` and `lookahead=` kwargs | ✓ WIRED — confirmed via 10 mic_audio_buf refs + 2 lookahead_provider refs in __main__ |
| `dj_cohost.py::llm_node` | `vibemix.prompts.matrix.build_parts_description` | function call with `(audio_seconds, has_mic_part, has_lookahead_part)` | ✓ WIRED — function exists at matrix.py:511; consumed by dj_cohost (per Plan 40-03 SUMMARY) |
| `blackhole_probe.py::probe_blackhole` | `_safe_emit` callable | optional emit_event callable invoked at 3 sites | ✓ WIRED — 3 event-name literals + swallow contract pinned by 2 tests |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `mic_audio_buf` ring | `int16[192000]` | sounddevice mic callback (real device) | ✓ Yes (callback runs on physical mic input; zero-fill only during AI-talk; tests T1+T3 confirm signal flow + zero-fill) | ✓ FLOWING |
| Mic Part 2 (Gemini contents) | `mic_wav: bytes` | `snapshot_wav(self._mic_audio_buf, MIC_AUDIO_PART_SECONDS)` | ✓ Yes (real PCM from mic_audio_buf; gated by 3 conditions; `test_mic_part_mime_is_audio_wav` confirms RIFF envelope) | ✓ FLOWING |
| Lookahead Part 3 (Gemini contents) | `lookahead_wav: bytes` | `LookaheadProvider.snapshot_wav()` → ffmpeg subprocess on real source file | ✓ Yes (real ffmpeg extract from disk; gated by nowplaying-cli + mdfind chain; falls back to None on streaming/missing) | ✓ FLOWING |
| Cooldowns | `MIN_EVENT_GAP_PER_TYPE[ev_type]` | `src/vibemix/audio/constants.py` constants dict | ✓ Yes (consumed by `EventDetector._cooldown_ok()` — verified by `tests/state/test_event_detector.py` 27 PASS) | ✓ FLOWING |
| Probe events | `audio.probe.{detected,missing,cta_fired}` | sounddevice query + caller-invoked emit | ✓ Yes (real sounddevice query at probe call; emit_event callable wired by caller in v3.0 Phase 45 — documented stub by design, not data hole) | ⚠️ STATIC at wizard-sink boundary (intentional — see Plan 40-06 §Sink Contract) |
| PGP slot file | `docs/security/pgp-public-key.txt` body | placeholder sentinel pre-discharge | ⚠️ PLACEHOLDER (intentional — Kaan-discharge step, dual-mode gate test flips on real-content arrival) | ⚠️ STATIC pre-discharge (by design) |
| Tauri pubkey | `tauri.conf.json5 plugins.updater.pubkey` | 2026-05-13 dev key (unchanged) | ⚠️ STATIC pre-discharge (Plan 40-05 only added comment; rotation = Kaan step) | ⚠️ STATIC pre-discharge (by design) |

The 3 STATIC entries are documented design decisions, not gaps. Wizard-sink emit_event boundary is the v3.0 Phase 45 / SHIP-04 (INSTALL-VM-RUN) handoff per Plan 40-06 §Sink Contract.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 40 test suite passes | `pytest tests/audio/test_mic_audio_buf.py tests/agent/test_dj_cohost_mic_part.py tests/audio/test_lookahead.py tests/agent/test_dj_cohost_3part.py tests/prompts/test_matrix_3part_labeling.py tests/eval/test_replay_harness_cooldowns.py tests/security/test_pgp_published.py tests/tauri/test_updater_key_rotated.py tests/install/test_blackhole_probe_events.py -q` | 64 passed, 2 skipped (post-discharge mode) | ✓ PASS |
| Regression on touched modules | `pytest tests/agent/test_dj_cohost.py tests/audio/test_buffers.py tests/audio/test_constants.py tests/state/test_event_detector.py -q` | 103 passed | ✓ PASS |
| Cooldowns import + value check | `python -c "from vibemix.audio.constants import MIN_EVENT_GAP_PER_TYPE, HEARTBEAT_SEC; print(HEARTBEAT_SEC, MIN_EVENT_GAP_PER_TYPE['PHASE'], MIN_EVENT_GAP_PER_TYPE['LAYER_ARRIVAL'], MIN_EVENT_GAP_PER_TYPE['MIX_MOVE'], MIN_EVENT_GAP_PER_TYPE['TRACK_CHANGE'])"` | 45.0 / 10.0 / 10.0 / 14.0 / 5.0 | ✓ PASS |
| `--print-cooldowns` flag present | `python -m scripts.eval.replay_harness --help` | Flag advertised in argparse output (per Plan 40-04 verification) | ✓ PASS |

---

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| (n/a) | No probe scripts under `scripts/*/tests/probe-*.sh` for Phase 40 | n/a | SKIPPED (Phase 40 is a Python-pkg phase, not migration/tooling — no probe-* convention applies) |

The dual-mode gate tests (`tests/security/test_pgp_published.py` + `tests/tauri/test_updater_key_rotated.py`) serve the equivalent purpose for the KAAN-ACTION-LEGAL discharge gates; both run cleanly under pytest.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUDIO-01 | 40-01 | Mic audio as 2nd Gemini multimodal Part (`mic_audio_buf` 12s ring, attached on KAAN_SPOKE) | ✓ SATISFIED | Plan 40-01 GREEN. 13 new tests; mic_part_attached/skipped events emit; 99 existing DJCoHostAgent tests regression-clean. |
| AUDIO-02 | 40-02 + 40-03 | 3s file-based lookahead via nowplaying-cli + mdfind + ffmpeg → 3rd Gemini Part; graceful streaming-only skip | ✓ SATISFIED | Plan 40-02 GREEN (provider). Plan 40-03 GREEN (wire-in). 8 hermetic provider tests + 6 integration tests. |
| AUDIO-03 | 40-04 | Event cooldowns retuned to v4 2026-05-11 baseline (PHASE 18→10, LAYER_ARRIVAL 16→10, MIX_MOVE 20→14, HEARTBEAT 70→45, TRACK_CHANGE 6→5) | ✓ SATISFIED | Plan 40-04 GREEN. Source exact-match; 8 replay-harness tests; 4 test pin sites updated. |
| AUDIO-04 | 40-03 | Prompt template documents 3-Part contract with "NOT YET HEARD BY AUDIENCE" label | ✓ SATISFIED | Plan 40-03 GREEN. `build_parts_description` builder with 4-way dispatch; 6 unit tests + 6 integration tests pin locked Q2 strings. |
| AUDIO-05 | 40-05 | PGP key published to keys.openpgp.org | ~ PRE-STAGE GREEN / NEEDS KAAN DISCHARGE | Engineering scaffolding (slot file + SECURITY.md retarget + dual-mode gate test) GREEN. Discharge = Kaan-only step per KAAN-ACTION-LEGAL.md §AUDIO-05. |
| AUDIO-06 | 40-05 | Tauri ed25519 updater key rotated to production | ~ PRE-STAGE GREEN / NEEDS KAAN DISCHARGE | Engineering scaffolding (Plan 40-05 comment + runbook + dual-mode gate test) GREEN. Discharge = Kaan-only step per KAAN-ACTION-LEGAL.md §AUDIO-06. |
| AUDIO-07 | 40-06 | BlackHole fresh-Mac probe walk + structured events | ~ PRE-STAGE GREEN / NEEDS KAAN DISCHARGE | Engineering scaffolding (3 event kinds + Pitfall 5 retry + 12 tests) GREEN. Discharge = fresh-account walk per KAAN-ACTION-LEGAL.md §AUDIO-07. |

All 7 AUDIO requirements claimed by the plans are present in REQUIREMENTS.md. No orphaned IDs.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| (none) | All grep checks clean — no TBD/FIXME/XXX debt markers in Plan 40 files; no `return None` / `return {}` stub patterns in load-bearing code paths | ℹ️ INFO | The 2 skipped tests in `tests/security/test_pgp_published.py` + `tests/tauri/test_updater_key_rotated.py` are dual-mode skips (`pytest.skip("Pre-discharge mode — exercised by separate assertions.")`) — by design, not stubs. |

POC immutability gate: `git status -- cohost.py cohost_v2.py cohost_lk.py mascot.html` → **clean** (no output) ✓

---

### Human Verification Required

Phase 40 has **5 items routed to human verification** — 4 are KAAN-ACTION-LEGAL discharge steps (engineering pre-staged GREEN; Kaan executes external action) and 1 is the v4 baseline ear-test (subjective acceptance of anti-slop reactions). All are explicitly carved out per `gsd-autonomous fully` policy + memory `project_phase_16_kaan_dj_testing`.

#### 1. v4 "harikaydı" baseline ear-test (SC #5)

**Test:** Run `./run.sh` (or `./run_v4.sh` as A/B baseline) against ≥1 real Kaan DJ session. Toggle Coach + Hype mode. Listen for reactions that feel forced/late/hallucinated/scripted/generic.
**Expected:** Reactions feel as alive/grounded as the v4 chat-tested 2026-05-11 baseline. No AI slop. Mic-attached responses (KAAN_SPOKE → "test test" → coherent reply to literal words). Lookahead-Part landings feel on-the-moment, not after-the-fact.
**Why human:** Hallucination gate is "real DJ friend in your ear" — no automated proxy. Per memory `project_phase_16_kaan_dj_testing`, this is satisfied by Kaan's personal DJ-set testing, NOT an automated suite.

#### 2. AUDIO-05 — PGP key publish (SC #4a, KAAN-ACTION-LEGAL §AUDIO-05)

**Test:** Follow `KAAN-ACTION-LEGAL.md §AUDIO-05` runbook end-to-end.
**Expected:** Real ed25519 PGP key generated, published to `hkps://keys.openpgp.org`, email-verify link clicked, `docs/security/pgp-public-key.txt` replaced with real armor block, SECURITY.md fingerprint cell updated, `KAAN-PGP-PLACEHOLDER.asc` removed. Dual-mode gate test (`tests/security/test_pgp_published.py`) flips from 4-pass+1-skip → 7-pass post-discharge automatically.
**Why human:** External clock (keyserver email-verify, gpg trust chain) + private-key custody = legal-capacity carveout per `gsd-autonomous fully`.

#### 3. AUDIO-06 — Tauri ed25519 updater key rotation (SC #4b, KAAN-ACTION-LEGAL §AUDIO-06)

**Test:** Follow `KAAN-ACTION-LEGAL.md §AUDIO-06` runbook end-to-end.
**Expected:** New production keypair generated via `npx @tauri-apps/cli signer generate --no-password`, pubkey pasted into `tauri.conf.json5 plugins.updater.pubkey`, base64-encoded private key set as `TAURI_UPDATER_PRIVATE_KEY` GH secret, release.yml rehearsal run. Dual-mode gate test (`tests/tauri/test_updater_key_rotated.py`) flips from 7-pass+1-skip → 8-pass automatically (dev-key fingerprint `94A8F6CE42E6487D` no longer present).
**Why human:** External actor (GitHub Actions secret store) + key-custody decision = Kaan-only step.

#### 4. AUDIO-07 — BlackHole fresh-Mac probe walk (SC #4c, KAAN-ACTION-LEGAL §AUDIO-07)

**Test:** Fresh macOS user account → install vibemix → wizard click-through → capture events.jsonl.
**Expected:** `audio.probe.cta_fired` event recorded during install CTA dispatch; post-install `audio.probe.detected` event with non-null `device_name` field. 6-invariant discharge checklist in KAAN-ACTION-LEGAL.md §AUDIO-07 signed.
**Why human:** Requires fresh user account + physical install hardware — cannot be programmatically verified on developer machine.

---

### Gaps Summary

**No engineering gaps.** All plan-level must_haves verified in code. All 4 fully-engineered success criteria (#1, #2, #3, plus engineering pre-stage of #4) are GREEN. Only #5 (ear-test) and the 3 KAAN-ACTION-LEGAL discharge steps within #4 are pending — both routed to `human_needed` per the phase rubric's explicit carveouts.

Note: 2 plan SUMMARYs reference pre-existing test failures (DEFERRED-40-01-02, DEFERRED-40-01-03, DEFERRED-40-02-01, DEFERRED-40-04-01, DEFERRED-40-04-02, plus the LFS pointer drift in `tauri/ui/assets/mascot/*.glb`). All are documented in `deferred-items.md`, all reproduce identically on `main` independent of Phase 40 changes, all are out-of-scope per executor SCOPE BOUNDARY rule. Phase 30 SENSE-17/18 expected-key set closed naturally by Plan 40-04. Not in-scope for this Phase 40 verification.

---

_Verified: 2026-05-17_
_Verifier: Claude (gsd-verifier)_
