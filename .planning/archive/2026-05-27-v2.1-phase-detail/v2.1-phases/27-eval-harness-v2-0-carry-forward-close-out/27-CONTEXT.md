# Phase 27: Eval Harness + v2.0 Carry-Forward Close-Out - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — no grey-area pause; recommended answers locked at Claude's discretion against ROADMAP + REQUIREMENTS + STATE + PITFALLS.md research)

<domain>
## Phase Boundary

Autonomous hallucination-proxy gate satisfies the v2.1 ship bar in place of Phase 16's Kaan-ear-only test; every v2.0 tech-debt carry-forward closed at runtime.

**Mapped REQ-IDs (14):** EVAL-01..EVAL-08, LIBRARY-09, REC-09, LATENCY-14, LATENCY-15, MASCOT-11, MIDI-20.

**In scope:**
- `scripts/eval/replay_harness.py` — deterministic single-binary replay of recorded sessions through shipped P17 detectors + P18 EvidenceRegistry + P19 ack bank + P20 linter + P22 anticipation.
- 2-judge cross-check rubric (Gemini 3 Pro + Gemini 3 Flash, different prompts) computing F1 + `useful_response_ratio` (substance) + cited-but-irrelevant cosine + bypass-rate.
- Corpus assembly: ≥ 3 public-domain DJ sets (archive.org / CCMixter / FMA), ≥ 3 genres, Hard Tek ≤ 70%.
- Threshold lock: `THRESHOLD-LOCK.md` — F1 ≥ 0.80 (both judges), substance ≥ 0.65, cited cosine ≥ 0.4, bypass ≤ 0.15. Kaan co-signature placeholder (autonomous = Kaan-action note in KAAN-ACTION-LEGAL.md, not a pause).
- CI: `.github/workflows/eval.yml` — runs harness on PR merge + nightly canary; fails below threshold; per-run scorecards under `.planning/eval-runs/`.
- v2.0 close-outs:
  - LIBRARY-09: wire `EvidenceRegistry.register_library` from `__main__.py:~698-717` when `~/.cache/vibemix/library.pkl` exists.
  - REC-09: universal2 macOS sidecar (lipo merge of arm64 + x86_64 PyInstaller).
  - LATENCY-14: Windows WASAPI `IMMNotificationClient` device-change subscription.
  - LATENCY-15: 40 Achird-voice OPUS ack recordings via offline Gemini TTS batch render + AIza-key scan re-run.
  - MIDI-20: DDJ-FLX4 Sync note disambiguation via autonomous synthetic MIDI replay against fixture sniff.

**Out of scope:**
- Real-GLB anticipation animations (Phase 35 ASSETS-03 — MASCOT-11 line-item lives here as a tracking pointer).
- New detectors beyond shipped v2.0 set (Hard Tek detectors = Phase 30).
- Apple notarytool / SignPath wiring (Phase 38 — legal-capacity carveout).
- DJ profile injection (Phase 32).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

All implementation choices are at Claude's discretion, grounded in:
- ROADMAP Phase 27 success criteria (verbatim)
- REQUIREMENTS.md EVAL-01..08, LIBRARY-09, REC-09, LATENCY-14, LATENCY-15, MIDI-20
- Pitfalls P42–P46, P48, P63, P69, P70
- POC reference files (cohost_v4.py canonical) for evidence-registry + detector contracts
- STATE.md "Decisions Locked (v2.1)" — autonomous mode, Phase 16 override, 3-process model, no architectural redesign

### Eval harness architecture
- **Recording format:** Existing `recordings/<session>/{events.jsonl, input.wav, voice.wav}` is the canonical replay input. No new recording format.
- **Replay determinism:** Seed Gemini API responses via cassette/snapshot mode (record once, replay deterministically) — Gemini API is non-deterministic but rubric judging happens against canonical recordings. Replay harness reads events.jsonl and re-runs detectors with frozen audio frames.
- **Single-binary:** `scripts/eval/replay_harness.py` is pure Python — no GPU, no Tauri, no sidecar. Imports vibemix package directly.
- **CI runtime:** Eval CI uses `--judge=gemini-3-flash` for speed + `--judge=gemini-3-pro` for accuracy in nightly canary only. PR merge runs Flash-only for cost.

### 2-judge cross-check (Pitfall P42)
- Two rubric files: `eval/rubrics/judge_pro.md` (Gemini 3 Pro, strict structured-JSON output, 6-axis scoring), `eval/rubrics/judge_flash.md` (Gemini 3 Flash, simpler binary pass/fail per axis + freeform justification).
- Both judges score INDEPENDENTLY on the same corpus row. Final score = `min(pro_f1, flash_f1)` to prevent self-bias collusion.
- Substance metric (EVAL-04): `useful_response_ratio = #(responses with ≥1 concrete observation OR specific advice) / total`. Heuristic detector: Gemini-judge tags each response with substance bool; require ≥ 0.65.
- Cited-but-irrelevant filter (EVAL-05): Gemini Embedding 2 (text+text mode) cosine between cited evidence-id payload and response text; threshold ≥ 0.4. Anything below = "cited but empty" → counted against F1.
- Bypass rate (EVAL-06): `% of events where AI silent within 8s` ≤ 0.15.

### Corpus diversity (Pitfall P43)
- **Sources locked:** archive.org (CC0 mixes), CCMixter, Free Music Archive. License txt per source committed to `eval/corpus/LICENSES.md`.
- **Genre coverage:** ≥ 3 distinct genres — Hard Tek + Techno + House (matches v2.0 baseline), optional 4th = Drum & Bass. Hard Tek ≤ 70%.
- **Size:** 6 sessions (2 Hard Tek, 2 Techno, 2 House) ≈ 6 × 30min ≈ 3 hours total. Enough for F1 stat power, small enough for CI nightly.
- **Per-detector-per-genre F1 matrix:** scorecard rows = (detector × genre) so a Hard Tek-overfit issue surfaces.

### Threshold lock (EVAL-06)
- `eval/THRESHOLD-LOCK.md` is a markdown file with frontmatter `kaan_signed: false` + `kaan_signed_at: null`. Auto-discharge writes `kaan_signed: autonomous_phase27` + timestamp — NOT a real signature. Kaan-action surface (`KAAN-ACTION-LEGAL.md`) gets a line "Phase 27 THRESHOLD-LOCK autonomous-signed; review when convenient". This is consistent with `gsd-autonomous fully` mode + memory `feedback_autonomous_no_grey_area_pause`.

### CI gate (EVAL-07)
- `.github/workflows/eval.yml` triggers: `pull_request: [opened, synchronize]` + `schedule: cron '0 5 * * *'` (nightly 5am UTC).
- Caches eval corpus via GitHub Actions cache keyed on corpus manifest hash.
- Posts scorecard comment on PR via `actions/github-script`.
- Failure mode: F1 < threshold → exit 1 → red check. Non-blocking on `[skip-eval]` PR title for docs-only changes.

### v2.0 close-outs
- **LIBRARY-09:** Single edit in `vibemix/__main__.py` around line 698–717 — add `if (cache := Path("~/.cache/vibemix/library.pkl").expanduser()).exists(): registry.register_library(load_library_index(cache))` after EvidenceRegistry init. Test = `test_register_library_invoked_when_cache_exists` + live citation test that asks Gemini to name a track and asserts the response includes a known track name from the test cache.
- **REC-09:** Build script change in `scripts/build_macos.sh` — invoke PyInstaller twice (`--target-arch=arm64` and `--target-arch=x86_64`), then `lipo -create -output vibemix-sidecar arm64/vibemix-sidecar x86_64/vibemix-sidecar`. Verify via `lipo -info` in CI.
- **LATENCY-14:** Windows-only path — `vibemix/audio/wasapi.py` subscribes to `IMMNotificationClient::OnDefaultDeviceChanged` via comtypes; on event, soft-restart audio stream without crashing session. Stub on macOS.
- **LATENCY-15:** Offline Gemini TTS batch render — `scripts/generate_ack_audio.py` reads `assets/ack_bank/manifest.json` (40 lines), calls Gemini 3 Flash TTS Achird voice, writes OPUS. Re-runs `scripts/scan_aiza_keys.py` after to verify zero matches.
- **MIDI-20:** Replay `tests/fixtures/ddj_flx4_sync_capture.jsonl` (real sniff from Kaan's controller during v2.0) through synthetic mido send; assert Sync note maps to expected event. Defensive both-bindings (0x60 + 0x58) confirmed unless one is verified-only.

### Test discipline
- All EVAL-01..08 + close-outs have dedicated tests under `tests/eval/` and `tests/runtime_closeouts/`.
- Gemini API calls in tests use VCR.py cassettes (record-once, replay-many) so CI doesn't burn API quota.
- Nightly canary in CI = real Gemini calls (cassettes refreshed). Cost cap = budget ≤ $5/day per memory "~50 €/month".

</decisions>

<code_context>
## Existing Code Insights

- **Canonical baseline:** `cohost_v4.py` POC — EvidenceRegistry, detector taxonomy, ack bank pattern. v2.1 lifts from v4 (memory `project_v4_canonical_baseline`).
- **EvidenceRegistry slot:** v2.0 Phase 25 reserved `register_library(index)` method — Phase 27 wires its invocation. Pitfall P48 = orphan unwired primitive.
- **Detector chain:** v2.0 Phase 17 GenreRouter + `build_hard_tek_chain` slot — Phase 27 replays through this, Phase 30 fills Hard Tek detectors.
- **Recording format:** v2.0 Phase 15 `recordings/<session>/{events.jsonl, input.wav, voice.wav}` is stable — replay harness reads this.
- **Sidecar build:** v2.0 Phase 21 CI scaffold has PyInstaller; needs arm64 + x86_64 + lipo merge for REC-09.
- **WASAPI:** v2.0 Phase 18 `vibemix/audio/wasapi.py` (Windows-only); needs IMMNotificationClient subscription.
- **POC files untouched rule (G5):** `cohost*.py`, `mascot.html`, `_test_*.py` lockfile in tests — extend allowlist for v2.1 modified files.

Codebase maps under `.planning/codebase/` will feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **Gemini 3 Flash for PR-merge eval, Gemini 3 Pro for nightly canary** — cost-aware. Both judges full-mode for THRESHOLD-LOCK initial sign-off.
- **Achird voice is Gemini-only** — memory `feedback_no_clap_use_gemini_embedding`. No alternative TTS provider.
- **`eval/corpus/` is git-LFS** — 3 hours of 44.1kHz mp3 ≈ 200MB; LFS keeps repo lean.
- **THRESHOLD-LOCK.md autonomous co-signature** — explicit Kaan-action surface line per memory `feedback_autonomous_no_grey_area_pause`. Kaan can review post-hoc.
- **MIDI-20 fixture is real captured data** — not synthesized. From Kaan's v2.0 session.
- **Eval CI cost cap:** $5/day. Nightly canary = ~6 sessions × 2 judges × ~30 calls/session = 360 Gemini calls ≈ $1-2 with prompt caching.

</specifics>

<deferred>
## Deferred Ideas

- **Bravoh-side proxy for API key (CRITICAL-01):** vibemix-distributed binary needs proxy not raw key — deferred to Phase 34 OSS security pass.
- **Hard Tek detectors:** deferred to Phase 30 (per ROADMAP).
- **DJ profile injection:** deferred to Phase 32.
- **Real GLB animations (MASCOT-11 actual execution):** deferred to Phase 35 ASSETS-03 — Phase 27 only carries the REQ-ID forward as a tracking line.
- **Per-detector confidence-weighted F1:** v2.1 ships flat F1. Confidence weighting = v2.2 backlog.
- **OSS-Foundation reviewer signoff on rubrics:** the 2 rubric files are versioned in repo; external review is post-launch concern.

</deferred>
