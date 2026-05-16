# Phase 42: Hallucination Gate v3 — Hybrid - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous — gsd-autonomous fully)

<domain>
## Phase Boundary

Adopt the hybrid hallucination gate decided in v3.0 scoping:

- **Phase 27 autonomous proxy = fast lane.** PR / nightly canary uses the v2.1 autonomous-only 2-judge cross-check architecture (Gemini 3 Pro + Gemini 3 Flash, F1≥0.80, substance≥0.65, cited-cosine≥0.40, bypass≤0.15). Already shipped; this phase calibrates thresholds against REAL corpus rather than synthetic fixtures.
- **Kaan-ear release-cut veto = slow lane.** SHIP-CUT gate-2 blocks unless both green: (a) 7 consecutive nightly proxy-green AND (b) signed ear-test within 14-day window.
- **P85 override formally retired.** v2.1 had a one-time autonomous-only override that bypassed Kaan's ear-test for v2.1 ship. The override expires post-v2.1; Phase 42 formally retires it (Decision Log entry + `cut_release.sh` reminder lines removed + retire `test_phase_16_override_expiry.py`).

Engineering scaffolding ships engineering-green. Kaan-action discharges (real corpus WAV upload to LFS, ack-bank quota refresh, first ear-test sessions) are documented in `KAAN-ACTION-LEGAL.md §GATE-*`.

Anti-feature carveouts:
- Do NOT auto-build the 30-session replay harness, LLM scorer, or F1 validator beyond what Phase 27 already shipped (memory: `project_phase_16_kaan_dj_testing`).
- Do NOT replace Kaan's ear-test with a more aggressive autonomous system — the hybrid is the locked design, not "build a better judge".

</domain>

<decisions>
## Implementation Decisions

### Corpus Assembly (GATE-01..03)

- **GATE-01 ack-bank top-up (20/40 → 40/40):** Engineering scaffold = `scripts/eval/generate_ack_audio.py --resume` (already exists from Phase 27-08). Plan 42 verifies the script's idempotent resume path + writes the runbook in `KAAN-ACTION-LEGAL.md §GATE-01`. Actual Gemini TTS call (~$0.10 spend when free-tier resets) is a Kaan-discharge oneliner.
- **GATE-02 VCR cassettes:** Engineering scaffold = `tests/eval/cassettes/` directory + record-mode helper `python -m vibemix.eval.record_cassettes` that scans the existing Phase 27 test suite and replays it with `VCR_RECORD_MODE=new_episodes`. One-time Kaan-discharge: `GEMINI_API_KEY=... python -m vibemix.eval.record_cassettes` after Plan 42 lands. Runbook in `KAAN-ACTION-LEGAL.md §GATE-02`.
- **GATE-03 6×30-min DJ session WAVs in git-LFS:** Engineering scaffold = `eval/corpus/sessions/` directory + `eval/corpus/MANIFEST.md` template + `.gitattributes` entry pointing `eval/corpus/sessions/**/*.wav filter=lfs diff=lfs merge=lfs -text` + LICENSES.md template. The 200MB of public-domain DJ session WAVs is a Kaan-discharge step (Kaan picks 6 sessions across ≥2 genres, ffmpeg-normalizes to 16kHz mono if needed, `git lfs track` + commit). Runbook in `KAAN-ACTION-LEGAL.md §GATE-03`. Phase 42 ships everything except the actual WAV bytes.

### Threshold Calibration (GATE-04)

- **Recalibration script:** `scripts/eval/recalibrate_thresholds.py` runs the 2-judge eval against the real-corpus session(s), measures F1 per session + per-genre, writes an audit trail to `eval/THRESHOLD-RECALIBRATION-LOG.md`.
- **Tolerance band ±0.10:** if measured F1 is within ±0.10 of the locked values (F1≥0.80 etc.), no re-lock needed; just commit the audit-trail entry. If outside, recalibrate + re-sign `THRESHOLD-LOCK.md`.
- **CI gate enforcement:** existing `.github/workflows/eval.yml` (Phase 27-04) consumes `THRESHOLD-LOCK.md`. Phase 42 adds a `--check-real-corpus` mode that fails the workflow if `eval/corpus/sessions/` has fewer than 6 sessions OR the calibration-log lookback shows no entry in the last 30 days.

### Ear-Test Protocol Codification (GATE-05 + GATE-07)

- **Protocol document:** `eval/EAR-TEST-PROTOCOL.md` codifies: 30min minimum per session; ≥2 genres in any 14d ear-test window; structured "what felt slop?" capture template (felt slop / felt scripted / felt late / felt generic checkbox + free-form).
- **Capture surface — Debrief window toggle:** Phase 29's debrief UI gets a new "Rate this session for release-gate" toggle. When opted-in, the debrief save flow writes `eval/ear-test-logs/<session-id>.json` with the structured payload (no audio content — text + checkboxes + timestamp + Kaan's signing identity).
- **Ear-pass calculation:** `scripts/release/check_ear_test.sh` reads `eval/ear-test-logs/` glob, accepts iff ≥2 sessions across ≥2 genres within the last 14 days, AND every captured slop-flag is empty (no "felt slop / scripted / late / generic" reported).
- **Privacy note:** ear-test log content is REDACTED from `eval/README.md` public docs — only the protocol is documented publicly, not Kaan's actual evaluations (per `feedback_privacy_scope_narrow`).

### check_gate.sh Cut-Criteria (GATE-06)

- **Script:** `scripts/release/check_gate.sh` (new) is invoked from `cut_release.sh` as Gate-2 of the 6-gate cut. Logic:
  1. Read last 7 nightly autonomous-proxy scorecards from `eval/proxy-results/` (Phase 27 already writes these).
  2. All 7 must report F1 ≥ locked threshold AND substance ≥ locked AND cited-cosine ≥ locked AND bypass ≤ locked.
  3. AND read `eval/ear-test-logs/` — `check_ear_test.sh` must pass (≥2 sessions ≥2 genres within 14d, zero slop flags).
  4. Exit 0 on both green; exit 1 with structured reason on any failure.
- **Gate-2 placement:** existing `cut_release.sh` already has a Gate-2 slot (Phase 39-01). Wire `check_gate.sh` into that slot; remove any v2.1-era override / reminder lines that referenced the P85 carveout.

### P85 Override Retirement (GATE-08)

- **Decision Log entry:** new file `.planning/decisions/P85-OVERRIDE-RETIRED.md` documents: v2.1 override was time-limited (one-milestone autonomous-only carveout); v3.0 hybrid gate replaces it; cite the audit trail commits + the Phase 27-04 lock.
- **`cut_release.sh` cleanup:** grep for `P85`, `OVERRIDE`, `autonomous-only`, `Kaan-ear bypass` reminder lines from v2.1 cut. Remove. Any logic that branched on the override constant collapses to the hybrid gate.
- **`test_phase_16_override_expiry.py` disposition:** retire — delete the file. The override no longer exists to expire. Replace with a positive assertion test `test_gate_42_hybrid_in_force.py` that pins: (a) `cut_release.sh` invokes `check_gate.sh` as Gate-2; (b) `check_gate.sh` reads both nightly + ear-test inputs; (c) no `OVERRIDE_*` constants remain in the release scripts.

### Public-Facing Eval Documentation (GATE-09)

- **`eval/README.md`:** new file, public-facing. Documents:
  - Hybrid gate regime (autonomous proxy + Kaan ear-test).
  - Threshold values (locked from `THRESHOLD-LOCK.md`) + what they mean for end users.
  - Judge architecture (2-judge cross-check: Gemini 3 Pro + Gemini 3 Flash) at a high level.
  - Protocol for ear-test (REDACTED — no actual ear-test log content, only the protocol shape).
  - How to reproduce the proxy gate locally (`pytest tests/eval/` + `scripts/eval/replay_harness.py`).
  - Anti-slop manifesto link (the "real DJ friend in your ear, no AI slop" north-star).
- **`eval/ear-test-logs/.gitignore`:** ear-test log JSON contents are committed (the metadata, scores, slop-flags) — but per `feedback_privacy_scope_narrow` the LOG CONTENT is fine in repo. What's redacted in `eval/README.md` is descriptive text about specific sessions, not the structured logs themselves. Keep logs in repo (audit trail).

### Claude's Discretion
- Exact module placement of `recalibrate_thresholds.py` (within `scripts/eval/` or new `vibemix.eval` package).
- Debrief UI toggle copy + position (subject to existing Phase 29 UI conventions).
- Whether to bundle Plans 42-01..05 or split further (planner decides).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 27 already shipped the 2-judge cross-check architecture, `THRESHOLD-LOCK.md`, `replay_harness.py`, ack-bank scaffold + 20/40 OPUS files, CI eval workflow.
- Phase 29 shipped the debrief window UI surface — the ear-test toggle slots in there.
- `cut_release.sh` (Phase 39-01) already has a 6-gate scaffold; Gate-2 slot exists.
- `EvidenceRegistry` (Phase 23+) is the load-bearing anti-slop primitive that the eval judges score against.
- `scripts/eval/replay_harness.py` (Phase 27 + 40-04 cooldowns) drives session replays.
- `tests/eval/cassettes/` directory pattern exists from Phase 27; just needs population.

### Established Patterns
- Eval scripts live in `scripts/eval/`; release scripts live in `scripts/release/`.
- LFS-tracked binaries (Phase 27-03 set the precedent for `eval/corpus/`).
- KAAN-ACTION discharges live in `KAAN-ACTION-LEGAL.md` with structured `## §SECTION-ID` sections (Phase 40 established the pattern for §AUDIO-05/06/07).
- Public-facing docs live in repo-root `docs/` or in module-specific `<module>/README.md`. `eval/README.md` is the convention for eval-public-facing.

### Integration Points
- `cut_release.sh` (Phase 39-01) — Gate-2 slot consumes `check_gate.sh`.
- Phase 29 debrief UI — new "rate for release-gate" toggle wires into the debrief save flow.
- `eval/corpus/MANIFEST.md` — Phase 27 already wrote a synthetic version; Phase 42 expands the schema for the 6 real sessions.
- `.github/workflows/eval.yml` — Phase 27 already runs nightly; Phase 42 extends with the `--check-real-corpus` mode.

</code_context>

<specifics>
## Specific Ideas

- Real corpus WAVs source: Kaan picks from public-domain DJ archives (e.g. archive.org, Boiler Room creative-commons sets, Mixcloud CC-BY). ≥2 genres mandatory to satisfy `check_ear_test.sh`. Documented sources in `eval/corpus/LICENSES.md`.
- Ear-test "what felt slop?" UI copy: keep the language casual and Turkish-mix friendly (per CLAUDE.md tone) — "AI yarısı slop'ladı mı?" / "Felt scripted?" etc. Match the project's voice.
- "harikaydı" baseline from Phase 40 — once the GATE-03 corpus lands AND the first ear-test runs, the "harikaydı" session's structured log becomes the gold-standard reference for what "ear-pass" looks like.

</specifics>

<deferred>
## Deferred Ideas

- **3-judge architecture (Pro + Flash + Embedding-2 retrieval check):** considered for the hybrid gate, deferred — Phase 27's 2-judge already meets the locked thresholds. Add the 3rd judge only if real-corpus calibration shows F1 drop > 0.10.
- **Per-DJ-style threshold bands (techno vs house vs hip-hop):** considered but Phase 27 locked per-genre F1 ≥ 0.70 only. Per-style bands defer to v3.x.
- **Ear-test reward gamification (streaks, badges):** out of scope. The toggle is a low-friction signal capture, not a gamified UX.
- **Cross-DJ ear-test (other DJs sign off, not just Kaan):** v3.x. v3.0 ship gate is single-DJ (Kaan) signed.

</deferred>
