# Phase 27: Eval Harness + v2.0 Carry-Forward Close-Out — Research

**Researched:** 2026-05-15
**Domain:** Autonomous LLM-as-judge eval gate + v2.0 carry-forward runtime wiring (LIBRARY/REC/LATENCY/MASCOT/MIDI close-outs)
**Confidence:** HIGH on architecture (anchored to v2.0 audit + 1961 passing tests + locked CONTEXT decisions); HIGH on Gemini SDK paths (verified via WebSearch + repo grep); MEDIUM on judge-rubric calibration thresholds (no replay corpus to validate against — first-run tuning required); HIGH on universal2 sidecar pitfall (corrected via PyInstaller upstream guidance — see "Critical Correction" below).

---

## Summary

Phase 27 lands two parallel workstreams under one phase boundary: (1) the **autonomous hallucination-proxy gate** that substitutes for Phase 16's Kaan-ear-only test in v2.1 only, and (2) the **v2.0 carry-forward close-outs** — six discrete runtime patches that close shipped-but-orphaned surfaces from v2.0's ship audit. The gate is ~80% of the engineering load (judge rubric design + corpus assembly + CI wiring + thresholds). The close-outs are ~20% — small surgical patches against named call sites.

The phase is **out-of-band by design**: the eval harness imports `vibemix.*` primitives but runs entirely under `scripts/eval/` and `tests/eval/` — no live runtime touch except a tiny additive helper on `AudioBuffer` (`fill_from_wav()`) and the 5-line `register_library` invocation patch in `__main__.py`. POC files (`cohost*.py`) stay untouched per locked decision.

**Critical correction:** Research surfaced a hard PyInstaller limitation — **lipo-merging two arch-specific PyInstaller bundles will NOT produce a working universal2 binary** (the embedded PKG archive lives only in the last-merged slice). The correct path is `--target-arch universal2` with a universal2 Python + universal2 wheels for every binary extension, OR ship two arch-specific sidecars and let Tauri's externalBin target-triple convention pick the right one at install time. This contradicts the CONTEXT.md "lipo-merge" plan and MUST be addressed in planning.

**Primary recommendation:** Plan REC-09 around Tauri's target-triple sidecar convention (`vibemix-sidecar-aarch64-apple-darwin` + `vibemix-sidecar-x86_64-apple-darwin`), NOT lipo-merge. Build the Gemini judge as two prompts (Pro 6-axis structured-JSON + Flash binary-pass-fail) routed via existing `google-genai` 2.0.1 client. Source the corpus from FMA Electronic + archive.org public-domain DJ mixes with `licenseurl:*publicdomain*` filter. Write THRESHOLD-LOCK.md with `kaan_signed: autonomous_phase27` per autonomous mode — Kaan-action surface gets a review line in `KAAN-ACTION-LEGAL.md`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (Claude's Discretion under `gsd-autonomous fully`)

All implementation choices locked at Claude's discretion, grounded in:
- ROADMAP Phase 27 success criteria (verbatim)
- REQUIREMENTS.md EVAL-01..08, LIBRARY-09, REC-09, LATENCY-14, LATENCY-15, MIDI-20
- Pitfalls P42–P46, P48, P63, P69, P70
- POC reference: `cohost_v4.py` (canonical) for evidence-registry + detector contracts
- STATE.md "Decisions Locked (v2.1)" — autonomous mode, Phase 16 override, 3-process model, no architectural redesign

**Eval harness architecture:**
- Recording format: existing `recordings/<session>/{events.jsonl, input.wav, voice.wav}` is the canonical replay input. No new recording format.
- Replay determinism: cassette/snapshot mode (record once, replay deterministically). Gemini API is non-deterministic but rubric judging happens against canonical recordings.
- Single-binary: `scripts/eval/replay_harness.py` is pure Python — no GPU, no Tauri, no sidecar. Imports vibemix package directly.
- CI runtime: `--judge=gemini-3-flash` for PR speed; `--judge=gemini-3-pro` for nightly canary accuracy. PR merge runs Flash-only for cost.

**2-judge cross-check (P42):**
- Two rubric files: `eval/rubrics/judge_pro.md` (Pro, strict structured-JSON, 6-axis), `eval/rubrics/judge_flash.md` (Flash, binary pass/fail per axis + freeform justification).
- Both judges score INDEPENDENTLY on same corpus row. Final score = `min(pro_f1, flash_f1)` to prevent self-bias collusion.
- Substance metric (EVAL-04): `useful_response_ratio = #(responses with ≥1 concrete observation OR specific advice) / total`. Heuristic: Gemini judge tags each response with substance bool; require ≥ 0.65.
- Cited-but-irrelevant filter (EVAL-05): Gemini Embedding 2 (text+text) cosine between cited evidence-id payload and response text; threshold ≥ 0.4.
- Bypass rate (EVAL-06): `% of events where AI silent within 8s` ≤ 0.15.

**Corpus diversity (P43):**
- Sources: archive.org (CC0 mixes), CCMixter, Free Music Archive. License txt per source committed to `eval/corpus/LICENSES.md`.
- Genre coverage: ≥ 3 genres — Hard Tek + Techno + House (matches v2.0 baseline), optional 4th = D&B. Hard Tek ≤ 70%.
- Size: 6 sessions (2 Hard Tek, 2 Techno, 2 House) × 30min ≈ 3 hours. Stat power for F1, small enough for nightly CI.
- Per-detector-per-genre F1 matrix surfaces Hard Tek-overfit issues.

**Threshold lock (EVAL-06):**
- `eval/THRESHOLD-LOCK.md` — markdown with frontmatter `kaan_signed: false` + `kaan_signed_at: null`. Auto-discharge writes `kaan_signed: autonomous_phase27` + timestamp (NOT a real signature).
- `KAAN-ACTION-LEGAL.md` gets line: "Phase 27 THRESHOLD-LOCK autonomous-signed; review when convenient" — consistent with `gsd-autonomous fully` mode.

**CI gate (EVAL-07):**
- `.github/workflows/eval.yml` triggers: `pull_request: [opened, synchronize]` + `schedule: cron '0 5 * * *'` (nightly 5am UTC).
- Caches eval corpus via GitHub Actions cache keyed on corpus manifest hash.
- Posts scorecard comment on PR via `actions/github-script`.
- Failure mode: F1 < threshold → exit 1 → red check. Non-blocking on `[skip-eval]` PR title for docs-only changes.

**v2.0 close-outs:**
- LIBRARY-09: 5-line edit in `vibemix/__main__.py` around line 696–698 — invocation patch + invocation test + end-to-end live citation test.
- REC-09: ⚠️ **CONTEXT prescribed lipo-merge approach is technically infeasible per PyInstaller upstream** — see Critical Correction in §Architecture Patterns and Pitfall section. Replan around target-triple convention.
- LATENCY-14: `vibemix/audio/wasapi.py` (or `vibemix/platform/_audio_windows.py`) subscribes to `IMMNotificationClient::OnDefaultDeviceChanged` via comtypes; on event, soft-restart audio stream. Stub on macOS.
- LATENCY-15: `scripts/generate_ack_audio.py` reads `assets/ack_bank/manifest.json` (40 lines), calls Gemini 3 Flash TTS Achird voice, writes OPUS. Re-runs `scripts/build_sidecar.py` AIza-key scan after.
- MIDI-20: replay `tests/fixtures/ddj_flx4_sync_capture.jsonl` through synthetic mido send; assert Sync note maps to expected event. Defensive both-bindings (0x60 + 0x58) confirmed unless one verified-only.

**Test discipline:**
- All EVAL-01..08 + close-outs have dedicated tests under `tests/eval/` and `tests/runtime_closeouts/`.
- Gemini API calls in tests use VCR.py cassettes (record-once, replay-many) — CI doesn't burn API quota.
- Nightly canary in CI = real Gemini calls (cassettes refreshed). Cost cap = budget ≤ $5/day per memory "~50 €/month".

### Claude's Discretion
ALL implementation choices fall here under `gsd-autonomous fully`. Research recommends; planner locks; executor builds. Only privacy rule + destructive risk + Apple Dev Agreement + SignPath OSS legal-capacity carveouts pause.

### Deferred Ideas (OUT OF SCOPE)
- Bravoh-side proxy for API key (CRITICAL-01) → Phase 34 OSS security pass.
- Hard Tek detectors → Phase 30.
- DJ profile injection → Phase 32.
- Real GLB animations (MASCOT-11 actual execution) → Phase 35 ASSETS-03. Phase 27 only carries the REQ-ID forward as a tracking line — no engineering work.
- Per-detector confidence-weighted F1 → v2.2 backlog.
- OSS-Foundation reviewer signoff on rubrics → post-launch.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EVAL-01 | Replay harness reads `recordings/<session>/events.jsonl + input.wav + voice.wav`; replays through P17 detectors + P18 EvidenceRegistry + P19 ack bank + P20 linter + P22 anticipation. Single-binary, deterministic, no GPU. | §Architecture Patterns "Replay Harness" + verified primitive paths in `src/vibemix/state/` + existing `scripts/replay_linter.py` scaffold (270 LOC) |
| EVAL-02 | 2-judge cross-check — Gemini 3 Pro + Gemini 3 Flash with different rubric prompts. Both ≥ 0.80 F1 (Pitfall P42). | §Standard Stack "LLM Judge"; verified `client.models.generate_content` is the canonical SDK surface |
| EVAL-03 | Corpus diversity gate — ≥ 3 public-domain DJ sets across ≥ 3 genres; Hard Tek ≤ 70%; per-detector-per-genre F1 matrix (Pitfall P43). | §Architecture Patterns "Corpus Assembly" + WebSearch-verified FMA + archive.org sourcing patterns |
| EVAL-04 | Substance metric — `useful_response_ratio ≥ 0.65`; per-event-class substance check (Pitfall P44). | §Code Examples "Substance metric"; per-event ground truth labels in fixtures |
| EVAL-05 | Cited-but-irrelevant filter — Gemini Embedding 2 cosine ≥ 0.4 between cited evidence and response text (Pitfall P45). | §Code Examples "Cited-relevance"; verified `embed_content` SDK surface |
| EVAL-06 | F1 + substance + bypass-rate-ceiling 0.15 threshold lock in THRESHOLD-LOCK.md (autonomous-signed under autonomous mode). | §Architecture Patterns "Threshold Lock"; autonomous mode policy |
| EVAL-07 | CI gate — `.github/workflows/eval.yml` runs replay harness on PR merge + nightly canary; fails build below threshold. | §Architecture Patterns "CI Workflow"; existing release.yml patterns reusable |
| EVAL-08 | Eval report artifact — per-run scorecard (`eval_report_<hash>.json`) committed to `.planning/eval-runs/`. | §Architecture Patterns "Audit Trail"; markdown + JSON pattern from v2.0 audit |
| LIBRARY-09 | `EvidenceRegistry.register_library` invoked from `__main__.py:~696-698` when `~/.cache/vibemix/library.pkl` exists; invocation test + end-to-end live citation test (Pitfall P48). | Verified: `register_library` defined at `evidence_registry.py:168` but NOT called anywhere; `library.pkl` cache path at `library/rekordbox.py:123` |
| REC-09 | Universal2 sidecar — eliminates Rosetta prompt on Apple Silicon (Pitfall P69). | ⚠️ **CRITICAL CORRECTION** — PyInstaller upstream documents lipo-merge of bundles is infeasible. See §Critical Correction below |
| LATENCY-14 | WASAPI loopback `IMMNotificationClient` subscription — mid-session default-device-change handled without crash (Pitfall P70). | §Code Examples "WASAPI device change"; comtypes is pure-Python COM bridge; verified no `wasapi.py` exists in current `src/vibemix/audio/` — needs creation |
| LATENCY-15 | 40 Achird-voice OPUS ack recordings — replace v2.0 silent placeholders via offline Gemini TTS Achird-voice batch render; re-run AIza scan. | Verified: 40 silent placeholders in `src/vibemix/audio/ack_bank/{drop_hit,track_change,mix_move,silence_break,generic_filler}/01..08.opus`; existing generator at `scripts/generate_placeholder_acks.py` is the template |
| MASCOT-11 | Anticipation-layer real GLBs land — handled in Phase 35 ASSETS-03. Phase 27 carries REQ-ID forward as tracking pointer ONLY. | §Out of Scope — no Phase 27 engineering. ASSETS-03 in Phase 35. |
| MIDI-20 | DDJ-FLX4 Sync note disambiguation locked — autonomous synthetic MIDI replay against fixture sniff; defensive both-bindings (0x60 + 0x58) confirmed or narrowed. | Verified: `controllers/ddj-flx4.json` lines 24-27 ship 4 sync entries (`sync_a/b` + `sync_a/b_alt`) all `pending-verdict`; existing `tests/midi/test_profile_flx4_golden.py` is the golden-fixture pattern |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Replay harness orchestration | Out-of-band CLI / dev tooling | — | Runs in CI + dev shell; never touches production runtime |
| Gemini judge invocation | Out-of-band CLI / `scripts/eval/` | Existing `google-genai` SDK | Same SDK as live runtime; called offline from harness |
| F1 / precision / recall math | Out-of-band CLI (stdlib only) | — | 20 lines of confusion-matrix counting; no scikit-learn |
| Cited-relevance cosine filter | Out-of-band CLI / `scripts/eval/` | Gemini Embedding 2 via `google-genai` | Same SDK as Phase 28 library indexer (anti-coupling — call at eval time, cache embeddings per evidence-id) |
| THRESHOLD-LOCK.md sign-off | Repo doc + KAAN-ACTION-LEGAL.md | — | Markdown with frontmatter; autonomous discharge per `gsd-autonomous fully` |
| CI gate workflow | `.github/workflows/eval.yml` | GitHub Actions cache | Standard GH Actions pattern; PR + nightly cron |
| `register_library` invocation | Python sidecar `__main__.py` | `library/rekordbox.py:try_load_cache` + `EvidenceRegistry.register_library` | 5-line patch at line ~696 between recorder + refresh_task creation; no new module |
| Universal2 sidecar (REC-09) | Build pipeline `scripts/build_sidecar.py` + `release.yml` | Tauri externalBin target-triple convention | NOT lipo-merge (technically infeasible per PyInstaller upstream); see §Critical Correction |
| WASAPI device-change handler (LATENCY-14) | Python sidecar `vibemix/platform/_audio_windows.py` | comtypes COM bridge | Subscribe `IMMNotificationClient::OnDefaultDeviceChanged`; soft-restart stream on event |
| Achird OPUS ack render (LATENCY-15) | Build-time `scripts/generate_ack_audio.py` | google-genai TTS + ffmpeg / pyav OPUS encode | One-shot offline batch; replaces 40 silent placeholders one-for-one |
| MIDI sync sniff fixture replay (MIDI-20) | `tests/midi/test_flx4_sync_disambig.py` | mido virtual port + `tests/fixtures/ddj_flx4_sync_capture.jsonl` | Synthetic replay against real captured fixture; verdict updates `controllers/ddj-flx4.json` status |

---

## Standard Stack

### Core (all already in `pyproject.toml` — zero new runtime adds)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-genai` | `>=2.0.1` (verified in `pyproject.toml:30`) [VERIFIED: repo grep] | Gemini 3 Pro + Flash judge calls; Gemini Embedding 2 cosine; Gemini 3 Flash TTS for Achird ack render | Same SDK already wired in v2.0 live path. No new dep. `client.models.generate_content` + `client.models.embed_content` are the canonical surfaces [VERIFIED: WebSearch ai.google.dev embeddings docs] |
| `numpy` | `>=2.4.4` (verified in `pyproject.toml:39`) [VERIFIED: repo grep] | Cosine similarity math + F1 confusion matrix | 20 lines of stdlib + numpy beats 30MB scikit-learn import |
| `pytest` + `pytest-mock` | `>=8.0` + `>=3.15.1` (verified in `pyproject.toml:140-141`) [VERIFIED: repo grep] | Test runner + Gemini client mocking for offline tests | Existing test infra; no `pytest-asyncio` present (verified absent — async tests use `asyncio.run()` directly per `tests/midi/test_watcher.py` pattern) |
| `mido` + `python-rtmidi` | `>=1.3.3` + `>=1.5.8` [VERIFIED: pyproject.toml:41-42] | MIDI sync sniff fixture replay (MIDI-20) | Existing dep; virtual port pattern documented in `tests/midi/` |
| `av` (PyAV) | `17.0.1` (transitive via livekit-agents) [VERIFIED: STACK.md] | OPUS encode for Achird ack recordings (LATENCY-15) | Already used by `scripts/generate_placeholder_acks.py` — same encoding path |

### Dev/CI-only additions (zero or minimal bundle impact)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `vcrpy` (VCR.py) | `>=8.0` [CITED: vcrpy.readthedocs.io 8.0.0 docs] | Record-once-replay-many cassettes for Gemini API in CI tests | Add to `[dependency-groups] dev` only. Cassettes stored under `tests/eval/cassettes/`. Without this, every CI test burns Gemini quota |
| `pytest-recording` | `>=0.13` [CITED: pypi.org/project/pytest-recording] | pytest plugin wrapping VCR.py for fixture-based cassette mgmt | Optional convenience layer over raw VCR; the `@pytest.mark.vcr` decorator is the canonical pattern |
| `comtypes` | `>=1.4` (Windows-gated) [CITED: pypi.org/project/comtypes] | COM interface bridge for `IMMNotificationClient` (LATENCY-14) | Already a transitive of `pyaudiowpatch`? Verify at planning. Add explicit if absent. Pure-Python; no compile step |

### Alternatives Considered (REJECTED)

| Instead of | Could Use | Tradeoff (why rejected) |
|------------|-----------|-------------------------|
| stdlib + numpy F1 | `scikit-learn` | +30 MB transitive bloat for 20 lines of confusion-matrix math; violates lean-utility memory [CITED: STACK.md "Bucket 1"] |
| `google-genai` direct | `deepeval` / `langchain-evals` / Vertex AI Eval Service | 50-200 MB transitives; multi-provider abstraction tax; violates Gemini-only memory `feedback_no_clap_use_gemini_embedding` [CITED: STACK.md "What NOT to add"] |
| Gemini Pro + Flash judges | `gemini-3.1-flash-preview` (single judge) | Single-judge fails P42 self-bias mitigation; cross-check with two prompts is the protection [CITED: PITFALLS.md P42] |
| numpy cosine | `sqlite-vec` for cited-relevance | Only ~6 sessions × ~30 events × 1 cosine each = ~180 cosines per run. numpy.dot is faster than building an index for this scale |
| VCR.py cassettes | `responses` / `httpx_mock` | google-genai uses httpx but routes through `gapic` transport; VCR.py intercepts at the urllib3/httpx layer, supports both transparently [CITED: vcrpy 8.0.0 docs Usage] |

**Installation:**
```bash
# Add to [dependency-groups] dev in pyproject.toml
uv add --group dev "vcrpy>=8.0" "pytest-recording>=0.13"

# comtypes — verify if pulled transitively first; add only if absent
uv add --group dev 'comtypes>=1.4; sys_platform == "win32"'
```

**Version verification:**
- `google-genai>=2.0.1` is current and stable per repo `pyproject.toml:30`. WebSearch confirms `embed_content` + `generate_content` are the canonical surfaces in 2.0.x [VERIFIED: ai.google.dev/gemini-api/docs/embeddings, May 2026].
- `vcrpy 8.0.0` is the current major version per Read the Docs [CITED: vcrpy.readthedocs.io].
- `comtypes` requires Windows + Python 3.9+ (we're on 3.12); pure-Python COM bridge [CITED: pypi.org/project/comtypes].
- ⚠️ **Verify the Python version:** `pyproject.toml:9` says `requires-python = ">=3.12,<3.13"`, NOT 3.14 as the auto-discovered CLAUDE.md "Tech Stack / Languages" section claims. Plan against 3.12.

---

## Architecture Patterns

### System Architecture Diagram

```
                ┌──────────────────────────────────────────┐
                │  EVAL HARNESS (out-of-band CLI)          │
                │                                          │
   recordings/  │  scripts/eval/replay_harness.py          │
   <session>/   │      ↓                                   │
       │        │  ┌── for each session: ──────────────┐   │
       │        │  │ 1. AudioBuffer.fill_from_wav()    │   │
       ├────────┤  │    (NEW additive helper)          │   │
       │        │  │ 2. drive state_refresh_loop tick  │   │
       │        │  │    via time-warp (manual ticks)   │   │
       │        │  │ 3. EventDetector.detect()         │   │
       │        │  │    → predicted_events.jsonl       │   │
       │        │  │ 4. CitationLinter.lint()          │   │
       │        │  │    → response_acceptance.csv      │   │
       │        │  └───────────────────────────────────┘   │
       │        │      ↓                                   │
       │        │  scripts/eval/judge.py                   │
       │        │      ├─ Gemini 3 Pro (judge_pro.md)      │
       │        │      └─ Gemini 3 Flash (judge_flash.md)  │
       │        │           │  6-axis structured JSON     │
       │        │           ↓                              │
       │        │      verdicts_pro.jsonl                  │
       │        │      verdicts_flash.jsonl                │
       │        │      ↓                                   │
       │        │  scripts/eval/cited_relevance.py         │
       │        │      ├─ Gemini Embedding 2 (text+text)   │
       │        │      ↓                                   │
       │        │      cited_relevance.csv                 │
       │        │      ↓                                   │
       │        │  scripts/eval/f1.py                      │
       │        │      ├─ predicted vs ground-truth events │
       │        │      ├─ ±2s tolerance per GROUND-07      │
       │        │      ├─ per-detector-per-genre matrix    │
       │        │      ↓                                   │
       │        │  scripts/eval/scorecard.py               │
       │        │      ↓                                   │
       │        │  .planning/eval-runs/<hash>/             │
       │        │      ├─ eval_report_<hash>.json          │
       │        │      ├─ scorecard.md                     │
       │        │      ├─ verdicts_pro.jsonl               │
       │        │      ├─ verdicts_flash.jsonl             │
       │        │      └─ regression_diff.md               │
       │        └──────────────────────────────────────────┘
       │
       │       (LIVE RUNTIME — UNTOUCHED except 5-line patch)
       │
       └────────→ vibemix/__main__.py
                     ├── recorder = VoiceRecorder(...)
                     ├── # NEW (LIBRARY-09): try_load_cache + register_library
                     │   if (cache := Path("~/.cache/vibemix/library.pkl").expanduser()).exists():
                     │       lib = RekordboxLibrary()
                     │       if lib.try_load_cache():
                     │           evidence_registry.register_library(lib)
                     │           print(f"-> library: {len(lib.tracks)} tracks registered")
                     ├── refresh_task = asyncio.create_task(state_refresh_loop(...))
                     └── coach_task = asyncio.create_task(coach_loop(...))


                ┌──────────────────────────────────────────┐
                │  CARRY-FORWARD CLOSE-OUTS                │
                │                                          │
                │  REC-09  scripts/build_sidecar.py +       │
                │          release.yml: target-triple       │
                │          convention (NOT lipo-merge)      │
                │                                          │
                │  LATENCY-14 vibemix/platform/             │
                │             _audio_windows.py +           │
                │             IMMNotificationClient via    │
                │             comtypes                     │
                │                                          │
                │  LATENCY-15 scripts/generate_ack_audio.py │
                │             → 40 OPUS files in            │
                │             src/vibemix/audio/ack_bank/   │
                │             → re-run AIza scan in         │
                │             scripts/build_sidecar.py      │
                │                                          │
                │  MIDI-20  tests/midi/                     │
                │           test_flx4_sync_disambig.py      │
                │           replays                         │
                │           tests/fixtures/                 │
                │           ddj_flx4_sync_capture.jsonl     │
                │           → updates                       │
                │           controllers/ddj-flx4.json       │
                │           status from "pending-verdict"   │
                │           to "verified" (one or both)     │
                └──────────────────────────────────────────┘


                ┌──────────────────────────────────────────┐
                │  CI GATE                                 │
                │                                          │
                │  .github/workflows/eval.yml              │
                │     on: pull_request, schedule (5am UTC) │
                │     ├─ checkout                          │
                │     ├─ cache eval/corpus/                │
                │     │   key: corpus-manifest-hash        │
                │     ├─ uv sync --group dev               │
                │     ├─ python -m scripts.eval.replay     │
                │     │   --judge=gemini-3-flash (PR)      │
                │     │   --judge=gemini-3-pro,flash       │
                │     │     (nightly)                      │
                │     ├─ exit 1 if F1 < 0.80 OR            │
                │     │   substance < 0.65 OR              │
                │     │   cited_cosine < 0.4 OR            │
                │     │   bypass > 0.15                    │
                │     ├─ commit eval_report_<hash>.json    │
                │     │   to .planning/eval-runs/          │
                │     └─ post scorecard PR comment via     │
                │         actions/github-script            │
                └──────────────────────────────────────────┘
```

### Recommended Project Structure

```
scripts/
├── eval/                                    # NEW — eval-only CLI tools
│   ├── __init__.py
│   ├── replay_harness.py                    # main orchestrator CLI
│   ├── judge.py                             # 2-judge dispatcher
│   ├── cited_relevance.py                   # embedding-cosine filter
│   ├── f1.py                                # confusion-matrix math
│   ├── scorecard.py                         # markdown + JSON report
│   └── corpus_manifest.py                   # diversity gate validator
├── generate_ack_audio.py                    # NEW — replaces silent placeholders (LATENCY-15)
├── replay_linter.py                         # EXISTING (Phase 20-03 scaffold) — extend for harness
└── tune_detectors.py                        # EXISTING (Phase 17) — reference

eval/                                        # NEW — corpus + rubrics
├── corpus/
│   ├── LICENSES.md                          # per-source license records
│   ├── manifest.json                        # {sessions: [...], hard_tek_pct, genre_distribution}
│   └── sessions/                            # git-LFS tracked
│       ├── hard_tek_01/
│       │   ├── input.wav                    # 30 min mix
│       │   ├── events.jsonl                 # ground-truth labels (Kaan-curated)
│       │   ├── responses/                   # ground-truth Gemini responses (recorded once)
│       │   └── source.txt                   # archive.org / FMA / CCMixter URL + license
│       ├── hard_tek_02/
│       ├── techno_01/, techno_02/
│       └── house_01/, house_02/
├── rubrics/
│   ├── judge_pro.md                         # Gemini 3 Pro 6-axis structured JSON
│   └── judge_flash.md                       # Gemini 3 Flash binary pass/fail
└── THRESHOLD-LOCK.md                        # autonomous-signed threshold doc

tests/eval/                                  # NEW — eval harness tests
├── conftest.py                              # synthetic 5s WAV fixtures
├── cassettes/                               # VCR.py recorded API responses
├── test_replay_harness.py
├── test_judge_pro_rubric.py
├── test_judge_flash_rubric.py
├── test_cited_relevance.py
├── test_f1_math.py
└── test_corpus_diversity_gate.py

tests/runtime_closeouts/                     # NEW — close-out tests
├── test_register_library_invoked.py         # LIBRARY-09 invocation test (mock spy)
├── test_track_citation_end_to_end.py        # LIBRARY-09 full citation lifecycle
├── test_universal2_sidecar.py               # REC-09 lipo -archs assertion
├── test_wasapi_default_device_change.py     # LATENCY-14 device change handler
├── test_ack_bank_real_audio.py              # LATENCY-15 non-silent + AIza-clean
├── test_ack_bank_aiza_scan.py               # LATENCY-15 zero-AIza assertion
└── test_flx4_sync_disambig.py               # MIDI-20 sniff fixture replay

tests/fixtures/                              # EXISTING dir
└── ddj_flx4_sync_capture.jsonl              # NEW — REQUIRES Kaan to capture from controller

.planning/eval-runs/                         # NEW — per-run audit trail
└── (populated by CI; gitignored or LFS — decide at planning)

.github/workflows/eval.yml                   # NEW — CI gate workflow

.planning/phases/27-.../KAAN-ACTION-LEGAL.md # NEW — autonomous-signed surface log
```

### Pattern 1: Replay Harness — Frame-by-Frame Determinism

**What:** Drive the live runtime's primitives offline using recorded WAV + events.jsonl as input. No mocks, no fakes — real `EvidenceRegistry`, real `EventDetector`, real `CitationLinter`. Mock only the Gemini API at the SDK boundary (via VCR cassettes).

**When to use:** Every session in `eval/corpus/sessions/` runs through this. Each event in `events.jsonl` is a ground-truth label; every `predicted_events.jsonl` row is what the harness re-derived from the same audio.

**Example:**
```python
# scripts/eval/replay_harness.py — pseudocode
# Source: extends scripts/replay_linter.py (Phase 20-03 scaffold, 270 LOC)
import asyncio
from pathlib import Path
from vibemix.audio.buffers import AudioBuffer
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.event_detector import EventDetector
from vibemix.coach.citation_linter import CitationLinter

async def replay_session(session_dir: Path, judge: str) -> dict:
    # 1. Load recorded audio (NEW additive helper on AudioBuffer)
    audio_buf = AudioBuffer(sample_rate=16000, window_seconds=7.0)
    audio_buf.fill_from_wav(session_dir / "input.wav")  # NEW method

    # 2. Load ground-truth events (the labels)
    ground_truth = [
        json.loads(line)
        for line in (session_dir / "events.jsonl").open()
        if line.strip()
    ]

    # 3. Construct REAL primitives — not mocks
    evidence_registry = EvidenceRegistry()
    event_detector = EventDetector(evidence_registry=evidence_registry, ...)
    citation_linter = CitationLinter(evidence_registry=evidence_registry)

    # 4. Time-warp tick the state refresh loop
    predicted_events = []
    for t_session in range(0, int(audio_buf.duration_s), 1):  # 1Hz manual tick
        snapshot = audio_buf.snapshot_features(t_session=t_session)
        new_events = event_detector.detect(snapshot)
        predicted_events.extend(new_events)

    # 5. For each ground-truth event, get the recorded Gemini response
    #    and ask the judge to score it
    results = []
    for ev in ground_truth:
        response = (session_dir / "responses" / f"{ev['id']}.txt").read_text()
        verdict = await call_judge(judge, ev, response, audio_buf)
        results.append(verdict)

    return {
        "session": session_dir.name,
        "predicted_events": predicted_events,
        "ground_truth_events": ground_truth,
        "judge_verdicts": results,
    }
```

### Pattern 2: 2-Judge Cross-Check with Different Rubric Prompts (Pitfall P42)

**What:** Two judges, different prompts, independent scoring. Final score = `min(pro_f1, flash_f1)` to prevent same-family self-bias collusion.

**When to use:** Every reaction in the corpus gets scored by both judges. Disagreement is signal — flag in scorecard for human review.

**Example (Pro rubric — `eval/rubrics/judge_pro.md`):**
```markdown
You are evaluating an AI DJ co-host's verbal reaction to a real DJ event.

Score the reaction on 6 axes (0.0 - 1.0 each):
1. groundedness — does it cite real events from the EvidenceRegistry?
2. timing — did it fire within ±2s of the actual event?
3. substance — does it contain ≥1 concrete observation OR specific advice?
4. tone — does it sound like a real DJ friend (not generic AI)?
5. relevance — does the cited evidence semantically anchor to the response text?
6. brevity — is it ≤ 2 sentences?

Output STRICTLY this JSON schema (no prose, no markdown fences):
{
  "groundedness": float,
  "timing": float,
  "substance": float,
  "tone": float,
  "relevance": float,
  "brevity": float,
  "verdict": "pass" | "fail" | "borderline",
  "rationale": "one sentence why"
}
```

**Example (Flash rubric — `eval/rubrics/judge_flash.md`):**
```markdown
Quick binary check on this AI DJ reaction. Pass requires ALL of:
- Cites a real event with [ev:TYPE@time] or [track:id] tag
- Sentence has substance (not just "Yeah" or "I'm listening")
- Fires within ±2s of the event
- Sounds like a friend, not a robot

Output STRICTLY:
{"pass": true|false, "why": "<1 sentence>"}
```

**Why two prompts:** Pro's 6-axis structured JSON gives nuanced scoring. Flash's binary-with-justification provides an orthogonal sanity check. If they disagree, scorecard surfaces the disagreement for review. Per Anthropic's "Demystifying Evals for AI Agents" (cited in FEATURES.md), three-tier eval methodology (rules-based + visual + LLM-as-judge) is the canonical pattern; we adapt the LLM-judge tier to two-judge.

### Pattern 3: Cited-Relevance Cosine Filter (Pitfall P45)

**What:** For each `[ev:TYPE@time]` citation in a response, embed (a) the event description from EvidenceRegistry and (b) the non-citation text around the citation. Cosine < 0.4 = "cited but irrelevant" — counts against `useful_response_ratio`.

**When to use:** Orthogonal third gate, independent of F1 and judge verdicts. Catches `"Yeah. [ev:KICK_SWAP@1:23]"` patterns.

**Example:**
```python
# scripts/eval/cited_relevance.py
from google import genai
from google.genai import types
import numpy as np

def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def relevance_score(response_text: str, evidence_payload: str, client: genai.Client) -> float:
    """Returns cosine similarity between response text (citations stripped) and
    cited evidence payload. Threshold ≥ 0.4 per CONTEXT EVAL-05."""
    stripped = strip_citations(response_text)  # remove [ev:...], [track:...]
    if len(stripped.split()) < 3:
        return 0.0  # degenerate response (P45 minimum-8-words rule)

    result = client.models.embed_content(
        model="gemini-embedding-2-preview",
        contents=[stripped, evidence_payload],
        config=types.EmbedContentConfig(
            task_type=types.TaskType.SEMANTIC_SIMILARITY,
            output_dimensionality=768,  # MRL truncation; 3072 is overkill for ~180 cosines
        ),
    )
    return cosine(np.array(result.embeddings[0].values),
                  np.array(result.embeddings[1].values))
```

[CITED: ai.google.dev/gemini-api/docs/embeddings — `embed_content` SDK surface confirmed for `gemini-embedding-2-preview` with MRL truncation]

### Pattern 4: VCR.py Cassettes for Deterministic Gemini Calls

**What:** Record once against real Gemini API, replay forever in CI. Eliminates flakes + cost.

**When to use:** Every test that hits `client.models.generate_content` or `client.models.embed_content`. Nightly canary refreshes cassettes against real API; PR runs replay only.

**Example:**
```python
# tests/eval/test_judge_pro_rubric.py
import pytest
from scripts.eval.judge import call_pro_judge

@pytest.mark.vcr  # pytest-recording decorator; cassette under tests/eval/cassettes/
def test_pro_judge_scores_grounded_response():
    response = "The mid kicks just dropped [ev:KICK_SWAP@1:23] — clean handoff."
    evidence = {"type": "KICK_SWAP", "t_session": 83.0, "rms_delta": 0.18}
    verdict = call_pro_judge(response, evidence)
    assert verdict["verdict"] in ("pass", "borderline")
    assert verdict["substance"] >= 0.7
    assert verdict["groundedness"] >= 0.8
```

**Cassette refresh policy:** PR CI uses recorded cassettes (`record_mode="none"`). Nightly canary runs with `record_mode="new_episodes"` against real Gemini — refreshes any drift. Cost cap: ~6 sessions × ~30 events × 2 judges + ~180 embedding calls = ~540 Gemini calls/night ≈ $1-2 with prompt caching well under $5/day cap.

[CITED: vcrpy.readthedocs.io 8.0.0 + pypi.org/project/pytest-recording for the canonical pytest pattern]

### Pattern 5: THRESHOLD-LOCK.md Frontmatter (Autonomous Signature)

**What:** Markdown file with YAML frontmatter encoding the threshold values + signature state. Autonomous mode writes `kaan_signed: autonomous_phase27`.

**Example:**
```markdown
---
kaan_signed: autonomous_phase27        # "false" | "autonomous_phase27" | "<kaan-real-sig>"
kaan_signed_at: "2026-05-15T20:00:00Z"
phase: 27
milestone: v2.1
thresholds:
  f1_min: 0.80           # both judges; min(pro_f1, flash_f1)
  substance_min: 0.65    # useful_response_ratio
  cited_cosine_min: 0.4  # cited-but-irrelevant filter
  bypass_max: 0.15       # bypass-rate ceiling
  per_genre_f1_min: 0.70 # per-detector-per-genre cell minimum
---

# vibemix Eval Threshold Lock — v2.1

This file is the autonomous-signed threshold lock for the v2.1 hallucination
proxy gate. It substitutes for Phase 16's Kaan-ear-only test under the
v2.1 milestone override.

## Sign-off

`kaan_signed: autonomous_phase27` — Claude auto-discharged this lock per
`gsd-autonomous fully` mode. A line in `KAAN-ACTION-LEGAL.md` flags this
for Kaan's post-hoc review. This is NOT a real signature.

## Re-tuning protocol

If gate values drift, the threshold lock is re-issued in a new commit.
Both judges must independently re-validate against the same corpus before
the new lock takes effect.
```

### Pattern 6: CI Workflow (`.github/workflows/eval.yml`)

```yaml
# .github/workflows/eval.yml
name: Eval Gate
on:
  pull_request:
    types: [opened, synchronize]
  schedule:
    - cron: '0 5 * * *'  # nightly 5am UTC
  workflow_dispatch:

jobs:
  eval:
    if: "!contains(github.event.pull_request.title, '[skip-eval]')"
    runs-on: ubuntu-latest  # CI-only; no platform-specific deps
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          lfs: true  # corpus is git-LFS

      - name: Cache eval corpus
        uses: actions/cache@v4
        with:
          path: eval/corpus/sessions
          key: corpus-${{ hashFiles('eval/corpus/manifest.json') }}

      - name: Setup uv + Python
        uses: astral-sh/setup-uv@v3
        with:
          python-version: '3.12'

      - name: Install deps
        run: uv sync --group dev

      - name: Run replay harness (PR mode — Flash only)
        if: github.event_name == 'pull_request'
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          uv run python -m scripts.eval.replay_harness \
            --judge=gemini-3-flash \
            --output=.planning/eval-runs/${{ github.sha }}/

      - name: Run replay harness (nightly — both judges)
        if: github.event_name == 'schedule'
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          uv run python -m scripts.eval.replay_harness \
            --judge=gemini-3-pro,gemini-3-flash \
            --output=.planning/eval-runs/${{ github.sha }}/ \
            --vcr-mode=new_episodes  # refresh cassettes nightly

      - name: Post scorecard to PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const card = fs.readFileSync('.planning/eval-runs/${{ github.sha }}/scorecard.md', 'utf8');
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: card
            });

      - name: Commit eval-run artifact
        if: github.event_name == 'schedule'
        run: |
          git config user.name "vibemix-eval-bot"
          git config user.email "noreply@vibemix.dev"
          git add .planning/eval-runs/
          git commit -m "eval: nightly canary $(date +%Y-%m-%d)" || true
          git push
```

### Anti-Patterns to Avoid

- **Mocking the primitives in the harness.** Use real `EvidenceRegistry`, real `EventDetector`. Mock only the Gemini API at the SDK boundary. Otherwise the harness validates mocks, not production code.
- **Single-judge scoring.** Pitfall P42 — Gemini scores its own output 5-15% higher than third-party would. Two judges with different prompts is the protection.
- **Citation-presence as gate.** Pitfall P45 — `"Yeah. [ev:KICK_SWAP@1:23]"` passes citation linter but is degenerate. Cited-relevance cosine + min-8-words is the orthogonal protection.
- **Synthetic adversarial corpus.** FEATURES.md anti-feature watch — "synthetic audio sounds like AI slop, which is what we're trying to *not* be". Real session corpus only.
- **Pretty dashboard for eval results.** Markdown report + CSV is enough. No Langfuse/MLFlow/Streamlit wrappers — engineering ego, not ship-value.
- **Real-time eval-in-prod.** Doubles cost, adds latency, the judge becomes a slop source. Eval is OFFLINE GATE only.
- **Lipo-merging two PyInstaller bundles** — see Critical Correction below; this approach DOES NOT WORK.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| F1 / precision / recall on event timestamps | scikit-learn `f1_score` | 20 lines of stdlib + numpy counting | scikit-learn is +30 MB transitive; F1 math is trivially counted from confusion matrix |
| HTTP recording for Gemini API tests | hand-rolled JSON dump fixtures | `vcrpy` + `pytest-recording` | Cassettes capture full HTTP semantics (headers, query strings, multipart bodies); hand-rolled JSON misses transport details |
| Cosine similarity for cited-relevance | Wrap sentence-transformers | `numpy.dot / norms` + Gemini Embedding 2 | sentence-transformers + torch = +800 MB. Gemini Embedding 2 is the locked-in model per memory `feedback_no_clap_use_gemini_embedding` |
| YAML frontmatter parsing for THRESHOLD-LOCK.md | Regex | `pyyaml` (already in dev deps) | PyYAML is already listed in `pyproject.toml:149` |
| MIDI virtual port for sync replay (MIDI-20) | Mock mido | Real `mido.open_output(virtual=True)` | mido supports virtual ports natively; existing `tests/midi/test_watcher.py` pattern |
| Universal2 macOS sidecar | lipo-merge bundles | Tauri externalBin target-triple convention | **CRITICAL:** lipo-merge of PyInstaller bundles produces broken binaries (PKG archive lives in only one slice). See Critical Correction §Pitfalls |
| WASAPI device-change subscription | Polling default device every 1s | `IMMNotificationClient::OnDefaultDeviceChanged` via comtypes | Polling burns CPU + adds latency; COM event is push-based and standard Windows pattern |

**Key insight:** Phase 27 is a "wire glue + write rubrics + assemble corpus" phase, not a "build novel infrastructure" phase. Every component has a canonical existing tool. Hand-rolling here = scope creep AND quality regression.

---

## Runtime State Inventory

> Phase 27 has limited runtime-state surface (most close-outs are code edits). LIBRARY-09 + LATENCY-15 + MIDI-20 touch on-disk state that needs explicit migration consideration.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | `~/.cache/vibemix/library.pkl` (RekordboxLibrary cache, written by `library/rekordbox.py:save_cache`). Existing v2.0 users have this if they ran the (currently orphaned) library import path | None — invocation patch reads existing format; LIBRARY-09 is a wire-up, not a data migration |
| | `recordings/<session>/{events.jsonl, input.wav, voice.wav}` (existing v2.0 sessions on Kaan's disk) | None for harness — harness READS recordings; corpus uses public-domain replays NOT user recordings (privacy + license) |
| | `eval/corpus/sessions/<source>/` (NEW git-LFS tracked) | NEW DATA — sourced once; manifest hash gates CI cache |
| **Live service config** | None — eval runs in CI offline; no Datadog/n8n/Cloudflare equivalent | None |
| **OS-registered state** | None — no Windows Task Scheduler / launchd / systemd surfaces touched by Phase 27 | None |
| **Secrets/env vars** | `GEMINI_API_KEY` (existing; used by live runtime + judge) — judge calls go through same key | None — code rename only; key unchanged. CI uses `secrets.GEMINI_API_KEY` |
| **Build artifacts / installed packages** | `src/vibemix/audio/ack_bank/{drop_hit,track_change,mix_move,silence_break,generic_filler}/01..08.opus` — 40 silent placeholder OPUS files written by `scripts/generate_placeholder_acks.py` | LATENCY-15 BYTE REPLACEMENT — `scripts/generate_ack_audio.py` overwrites all 40 files with real Achird TTS audio. PyInstaller bundle hash will change → regenerate sidecar build → re-run AIza scan |
| | `src/vibemix/midi/controllers/ddj-flx4.json` — sync entries lines 24-27 ship `pending-verdict` status | MIDI-20 STATUS UPDATE — JSON file edit; `pending-verdict` → `verified` for the binding(s) confirmed by sniff fixture replay |

**Nothing found in OS-registered state and live service config:** verified by grep against the affected modules — Phase 27's surface is pure dev-tool + Python sidecar runtime + ack-bank assets. No external service registrations.

---

## Common Pitfalls

### CRITICAL CORRECTION — Pitfall: REC-09 lipo-merge approach is technically infeasible

**What goes wrong:** CONTEXT.md and PITFALLS.md P69 prescribe `lipo -create -output vibemix-sidecar arm64/vibemix-sidecar x86_64/vibemix-sidecar` to produce a universal2 sidecar. **This does not work for PyInstaller bundles.** PyInstaller upstream documentation explicitly states: *"While tools like lipo allow you to combine two single-arch executables into a universal2 executable, this does not work with PyInstaller-built executables. In a universal2 build, a single PKG archive is created and embedded into the last architecture slice of the universal2 executable. Therefore, when extracting architecture slices using lipo, the last slice will have the PKG archive and will run correctly, while the first slice will raise an error due to lack of the PKG archive."* [CITED: pyinstaller.org/en/stable/feature-notes.html, verified May 2026]

**Why it happens:** PyInstaller's build process embeds a Python interpreter PKG archive into the executable. The two arch-specific bundles each have their own PKG archive at the END of the binary; lipo-merge cannot union them — the result is a binary where one slice (typically arm64, last-merged) works and the other (x86_64) immediately segfaults at app launch trying to read the missing PKG archive.

**Warning signs:**
- `lipo -archs vibemix-sidecar` shows `arm64 x86_64` (looks correct)
- Launching on M1: works
- Launching on Intel Mac: immediate "Bus error: 10" or PyInstaller's "Cannot read PKG archive"
- macOS Console.app shows `dyld_sim` PKG archive errors

**Prevention (RECOMMENDED PATH):**
- **Tauri externalBin target-triple convention:** ship TWO arch-specific PyInstaller bundles named per Tauri's required convention: `vibemix-sidecar-aarch64-apple-darwin` and `vibemix-sidecar-x86_64-apple-darwin`. Tauri's bundler picks the right one at install time per `externalBin` config. [CITED: v2.tauri.app/develop/sidecar/ — "Tauri appends the target triple to the specified path"]
- Build matrix: `release.yml` runs PyInstaller on both `macos-14` (arm64) AND a separately-tagged Intel runner (e.g., `macos-13` or `macos-14-intel-runner-tag`) → produces two binaries → DMG bundles both → Tauri picks correct one per host arch.
- ALTERNATIVELY (more complex): Build a single `--target-arch=universal2` PyInstaller bundle. Requires:
  - Universal2 Python interpreter (build from source OR use `python.org` universal2 installer)
  - Universal2 wheels for EVERY binary extension dep (numpy, scipy, sounddevice, pyobjc, av, livekit, mido) — many wheels do NOT ship universal2 for Python 3.12; manual `delocate-merge` per-package required
  - Significant build complexity vs target-triple split

**Mitigation evidence:**
- Test: `tests/runtime_closeouts/test_universal2_sidecar.py::test_target_triple_files_exist` — assert `vibemix-sidecar-aarch64-apple-darwin` AND `vibemix-sidecar-x86_64-apple-darwin` both exist post-build, AND each has only its own arch (`lipo -archs` returns single arch per file).
- CI: `release.yml` matrix `macos-14` + (intel runner) builds both; assert via `lipo -archs $SIDECAR_BIN | grep -qE "^(arm64|x86_64)$"` per artifact.
- Post-bundle: assert Tauri DMG contains both target-triple binaries via `unzip -l vibemix.app/Contents/MacOS/`.

**Phase 27 planning impact:** REC-09 plan must explicitly choose between target-triple split (recommended, lower risk) or universal2-via-delocate-merge (higher complexity). Default recommendation = **target-triple split**.

### Pitfall: Self-bias collusion when both judges share the same family (P42)

**What goes wrong:** Pro and Flash both being Gemini = same RLHF family → both might inflate Gemini's own outputs by the same 5-15%. Cross-check still catches "wildly different" outputs but misses "consistently inflated" ones.

**Why it happens:** Same-family bias is a documented LLM-as-judge failure mode [CITED: futureagi.com/blog/best-llm-judge-models-2026]. Two-judge cross-check mitigates IF prompts force divergent reasoning paths; it doesn't mitigate IF both prompts let the model anchor on the same priors.

**Prevention:**
- **Different rubric framings:** Pro asks "would this fool a human?"; Flash asks "does the sentence semantically anchor to the citation?" — these surface different failure modes.
- **Min aggregation, not mean:** `min(pro_f1, flash_f1)` not `mean(...)`. Disagreement = caution.
- **Anti-self-praise prompt instructions:** Both rubric files include explicit "If the response is grammatical but vague, score harshly. We test for substance, not politeness."
- **Kaan-veto bookmark (post-RC):** even with autonomous proxy passing, Kaan does a 5-session post-RC ear-listen sample. If he disagrees, v2.1.1 patch re-tunes rubrics.

**Warning signs:**
- F1 ≥ 0.85 from both judges but Kaan flags 3 of 5 sample reactions as slop
- Both judges score borderline responses identically (suggests anchoring on same priors)

### Pitfall: Corpus overfit to Hard Tek (P43)

**What goes wrong:** Most v2.0 recordings are Kaan's Hard Tek + techno sets. If corpus is sourced from Kaan's recordings, gate is "Kaan's-taste regression test." First non-Kaan user (house DJ) hits entirely different audio distribution → detectors mis-fire → "AI is broken" reports.

**Prevention:**
- Corpus = public-domain only (FMA Electronic + archive.org `licenseurl:*publicdomain*`). NO Kaan recordings.
- Genre quotas enforced in `corpus_manifest.py` validator: Hard Tek ≤ 70%, ≥ 3 distinct genres, 6 sessions total.
- Per-detector-per-genre F1 matrix surfaces overfit. Each cell must hit precision ≥ 0.7.

**Warning signs:**
- `eval/corpus/manifest.json` shows `hard_tek_pct > 70`
- F1 matrix shows house genre cells all at 0.0 (detector never fires) or 0.5 (detector spurious-fires)

### Pitfall: F1 too lenient — gate accepts "I'm listening" filler (P44)

**What goes wrong:** Phase 20 shipped `IM_LISTENING_FRAGMENT` fallback for "cannot cite, say I'm listening." Combined with bypass-on-strip-rate, Gemini can degenerate to mostly filler. F1 passes (no false-positive citations), judge passes (grammatical), gate green, user hears AI saying nothing.

**Prevention:**
- `useful_response_ratio ≥ 0.65` substance metric — 35%+ filler fails gate.
- Per-event-class substance: DROP, PHRASE_BOUNDARY, KICK_SWAP MUST get substantive responses (HEARTBEAT exempt).
- Bypass rate ≤ 0.15 — if linter is constantly being overridden, anti-slop contract is paper.

### Pitfall: Citation linter gamed via "Yeah. [ev:...]" (P45)

**What goes wrong:** Linter validates citation presence + validity, not semantic anchoring. `"Yeah. [ev:KICK_SWAP@1:23]"` passes.

**Prevention:**
- Min-8-words-after-strip-citations rule: `len(strip_citations(response).split()) >= 8`.
- Cited-relevance cosine ≥ 0.4 between cited evidence payload and response text.
- Prompt mitigation via Phase 28 system instruction: "Sentence must describe what's happening — don't just emit the tag."

### Pitfall: register_library final-mile orphan AGAIN (P48)

**What goes wrong:** v2.0 audit flagged: "register_library: defined, NOT called." If LIBRARY-09 patch only adds an import test (not invocation test), orphan ships again. Verified via grep — `register_library` is currently NOT referenced anywhere in `__main__.py`.

**Prevention:**
- **Invocation test (not import test):** `tests/runtime_closeouts/test_register_library_invoked.py` boots `__main__.py`'s init path with synthetic `library.pkl`, asserts `evidence_registry.register_library` is invoked via `mocker.spy(evidence_registry, 'register_library')`.
- **End-to-end live citation test:** drag-drop XML → run session → assert events.jsonl contains valid `[track:<id>]` citation passing linter.
- **CI grep gate:** `grep -q "evidence_registry.register_library" src/vibemix/__main__.py` MUST return exit 0.

### Pitfall: Bundle ID accidentally changed during REC-09 work (P63)

**What goes wrong:** Bundle ID `world.bravoh.vibemix` lives in `tauri/src-tauri/tauri.conf.json5` + `Info.plist`. REC-09 PyInstaller spec changes touching `tauri.conf.json5` could accidentally edit `bundleIdentifier`. Result: every v2.0 user → v2.1 upgrade hits TCC permission reset.

**Prevention:**
- Bundle ID lock CI assertion: `tests/install/test_bundle_id_locked.py` reads tauri.conf.json5 + plist, asserts ALL equal `world.bravoh.vibemix`.
- Grep gate: `! grep -rE "(bundleIdentifier|CFBundleIdentifier).*['\"]" tauri/ release.yml | grep -v "world.bravoh.vibemix"` — fails CI if any other identifier appears.

### Pitfall: WASAPI device change handler blocks (P70)

**What goes wrong:** `IMMNotificationClient` callback methods MUST be non-blocking. Microsoft docs: "the methods of the IMMNotificationClient interface must be nonblocking, and the client should never wait on a synchronization object during an event callback" [CITED: learn.microsoft.com IMMNotificationClient]. If LATENCY-14 implementation does a synchronous WASAPI re-init in the callback, Windows kills the audio service.

**Prevention:**
- Callback ONLY sets a `threading.Event` or pushes to a `queue.Queue`; actual stream restart happens on a separate worker thread.
- Pattern: `OnDefaultDeviceChanged` → `self._device_changed_event.set()` → worker thread waits on the event → `assert_wasapi_loopback_rate(...)` then re-opens stream.
- Test: `test_wasapi_default_device_change.py` asserts callback returns within 1ms (mock + time.perf_counter).

### Pitfall: AIza key embedded in Achird OPUS bytes (LATENCY-15)

**What goes wrong:** Gemini TTS responses are audio bytes; theoretically clean. BUT if the generation script logs request/response bodies into a fixture or accidentally writes the API key into a manifest, the AIza scan in `scripts/build_sidecar.py` will catch it and FAIL the build.

**Prevention:**
- `scripts/generate_ack_audio.py` writes ONLY raw OPUS bytes to disk; no JSON manifests with response metadata.
- After generation: re-run `scripts/build_sidecar.py` AIza scan as a separate task assertion.
- Test: `tests/runtime_closeouts/test_ack_bank_aiza_scan.py` greps all 40 OPUS files for `AIza[A-Za-z0-9_-]{35}` pattern; asserts zero matches.

### Pitfall: MIDI sync sniff fixture not yet captured (MIDI-20)

**What goes wrong:** MIDI-20 plan assumes `tests/fixtures/ddj_flx4_sync_capture.jsonl` exists from "Kaan's v2.0 session." Verified — this fixture file does NOT exist in the repo. Phase 27 task either (a) requires Kaan to capture the fixture (Kaan-action) OR (b) generates a synthetic-but-defensible fixture from `cohost_v4.py` POC source code (which has the actual NOTE_MAP from Kaan's real DJ sessions).

**Prevention:**
- **Recommended (autonomous mode):** Extract the FLX4 sync note byte values from `cohost_v4.py` `_NOTE_MAP` (POC-grounded from real sessions per memory `project_v4_canonical_baseline`) and synthesize the fixture programmatically. Document the source provenance in fixture frontmatter.
- If POC source disagrees with the JSON file's `pending-verdict` entries, the discrepancy IS the verdict signal — narrow to the POC-confirmed binding, leave the alt as `tentative`.
- **Alternative:** Defer MIDI-20 to Kaan-action surface if POC source is ambiguous. Per autonomous mode, recommend the autonomous path first.

---

## Code Examples

### Replay harness — minimal session loop

```python
# scripts/eval/replay_harness.py
# Source: extends scripts/replay_linter.py (270 LOC, Phase 20-03)
from __future__ import annotations
import argparse, asyncio, json, sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from vibemix.audio.buffers import AudioBuffer
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.event_detector import EventDetector
from vibemix.coach import CitationLinter
from scripts.eval.judge import call_judges
from scripts.eval.cited_relevance import relevance_score
from scripts.eval.f1 import compute_f1


async def replay_one_session(session_dir: Path, judges: list[str]) -> dict:
    audio_buf = AudioBuffer(sample_rate=16000)
    audio_buf.fill_from_wav(session_dir / "input.wav")  # NEW additive helper

    ground_truth = [json.loads(line) for line in (session_dir / "events.jsonl").read_text().splitlines() if line.strip()]

    evidence_registry = EvidenceRegistry()
    event_detector = EventDetector(evidence_registry=evidence_registry)
    linter = CitationLinter()

    # Time-warp: tick refresh manually at 1Hz
    predicted = []
    for t in range(int(audio_buf.duration_s)):
        snapshot = audio_buf.snapshot_features(t_session=float(t))
        predicted.extend(event_detector.detect(snapshot, t_session=float(t)))

    # Score each ground-truth event with both judges
    verdicts = []
    for ev in ground_truth:
        response_path = session_dir / "responses" / f"{ev['id']}.txt"
        if not response_path.exists():
            verdicts.append({"event_id": ev["id"], "verdict": "no_response", "bypass": True})
            continue
        response = response_path.read_text()
        judge_verdicts = await call_judges(judges, response, ev, audio_buf)
        cosine = await relevance_score(response, ev.get("payload", ""))
        verdicts.append({**judge_verdicts, "cosine": cosine, "event_id": ev["id"]})

    return {
        "session": session_dir.name,
        "f1": compute_f1(predicted, ground_truth, tolerance_s=2.0),
        "verdicts": verdicts,
        "useful_response_ratio": sum(1 for v in verdicts if v.get("substance", 0) > 0.5) / max(len(verdicts), 1),
        "bypass_rate": sum(1 for v in verdicts if v.get("bypass")) / max(len(verdicts), 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("eval/corpus/sessions"))
    parser.add_argument("--judges", default="gemini-3-flash", help="comma-separated")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold-lock", type=Path, default=Path("eval/THRESHOLD-LOCK.md"))
    args = parser.parse_args()

    judges = args.judges.split(",")
    sessions = sorted(args.corpus.glob("*/"))
    results = asyncio.run(asyncio.gather(*(replay_one_session(s, judges) for s in sessions)))

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "eval_report.json").write_text(json.dumps(results, indent=2))

    # Threshold check — exit 1 if any session below
    thresholds = parse_threshold_lock_frontmatter(args.threshold_lock)
    failed = [r for r in results
              if r["f1"] < thresholds["f1_min"]
              or r["useful_response_ratio"] < thresholds["substance_min"]
              or r["bypass_rate"] > thresholds["bypass_max"]]
    if failed:
        print(f"FAIL: {len(failed)} sessions below threshold", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### `register_library` invocation patch (LIBRARY-09)

```python
# vibemix/__main__.py — insert between line 668 (agent construction) and line 689 (refresh_task)
# Source: verified call site at __main__.py:689 + register_library at evidence_registry.py:168
from pathlib import Path
from vibemix.library.rekordbox import RekordboxLibrary

# ... existing code ...
agent = DJCoHostAgent(...)  # line 653-668 in current __main__.py

# ── Plan 25-02 final-mile wiring (closes v2.0 register_library orphan, P48) ──
library_cache = Path.home() / ".cache" / "vibemix" / "library.pkl"
if library_cache.exists():
    lib = RekordboxLibrary()
    if lib.try_load_cache():
        registered = evidence_registry.register_library(lib)
        print(f"-> library: {registered} tracks registered for [track:<id>] citations")
    else:
        print("-> library: cache present but failed to load — skipping registration")
else:
    print("-> library: no cache at ~/.cache/vibemix/library.pkl — citations limited to nowplaying-cli")

session = AgentSession(llm=llm_inst, tts=tts_inst)
# ... rest unchanged ...
```

### LATENCY-14 — IMMNotificationClient stub

```python
# vibemix/platform/_audio_windows.py — extension
# Source: WebSearch IMMNotificationClient docs + comtypes pattern
import threading
from comtypes import CLSCTX_ALL, COMObject
from comtypes.client import CreateObject
# Note: actual IMMDeviceEnumerator binding pattern depends on existing pyaudiowpatch usage.
# Verify pyaudiowpatch already pulls comtypes transitively before adding explicit dep.

class _DeviceChangeListener(COMObject):
    """IMMNotificationClient impl — ALL methods MUST be non-blocking per
    Microsoft docs (https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/
    nn-mmdeviceapi-immnotificationclient).
    """
    _com_interfaces_ = [IMMNotificationClient]  # bound from comtypes typelib

    def __init__(self, restart_event: threading.Event):
        super().__init__()
        self._restart_event = restart_event

    def OnDefaultDeviceChanged(self, flow, role, default_device_id):
        # Non-blocking: just signal worker thread
        self._restart_event.set()
        return 0  # S_OK

    # Other methods (OnDeviceAdded, OnDeviceRemoved, OnPropertyValueChanged) — return 0


class WindowsLoopbackAudio:
    def __init__(self):
        self._restart_event = threading.Event()
        self._listener = _DeviceChangeListener(self._restart_event)
        # Register via IMMDeviceEnumerator::RegisterEndpointNotificationCallback
        # ... existing audio init code ...
        self._restart_thread = threading.Thread(target=self._restart_worker, daemon=True)
        self._restart_thread.start()

    def _restart_worker(self):
        while not self._stop:
            if self._restart_event.wait(timeout=1.0):
                self._restart_event.clear()
                self._restart_stream_safely()
```

### Substance metric (EVAL-04)

```python
# scripts/eval/scorecard.py
def useful_response_ratio(verdicts: list[dict]) -> float:
    """Per CONTEXT EVAL-04 + Pitfall P44.
    A response is 'useful' if EITHER judge tags substance >= 0.5.
    """
    useful = sum(
        1 for v in verdicts
        if v.get("pro", {}).get("substance", 0) >= 0.5
        or v.get("flash", {}).get("pass", False)
    )
    return useful / max(len(verdicts), 1)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 16 Kaan-ear-only test | 2-judge autonomous gate (Pro + Flash, different rubrics) | v2.1 milestone (autonomous mode) | Kaan-ear becomes post-RC validation, not gate |
| BLEU/ROUGE for AI eval | LLM-as-judge with structured JSON output | 2024-2026 industry shift [CITED: futureagi.com 2026 ranking] | BLEU/ROUGE measure text overlap, not "feels like a real DJ friend" |
| Single judge | 2-judge cross-check with different prompts | P42 mitigation (2025-2026 LLM-judge bias research) | Mitigates self-bias inflation 5-15% |
| Hand-rolled HTTP test mocks | VCR.py cassettes (record-once-replay-many) | VCR.py 8.0 (2025) | Captures full HTTP semantics; eliminates flakes |
| `lipo -create` PyInstaller bundle merge | Tauri target-triple convention OR PyInstaller `--target-arch=universal2` with universal2 wheels | PyInstaller 6.x docs (current) | lipo-merge produces broken binaries; target-triple is canonical |

**Deprecated/outdated:**
- **scikit-learn for F1:** unjustified bloat for 20 lines of math
- **deepeval / langchain-evals:** 50-200MB transitives for what's 200 LOC of glue
- **Real-time eval-in-prod:** doubled cost + latency; eval is offline gate only
- **Polling default audio device every 1s for changes:** push-based `IMMNotificationClient` is the standard Windows pattern

---

## Assumptions Log

> Claims tagged `[ASSUMED]` — flag for user confirmation before locking decisions.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Gemini 3 Pro + Flash are both available via `client.models.generate_content` with model IDs `gemini-3-pro` and `gemini-3-flash` (not `-preview` suffix) | Standard Stack, Code Examples | LOW — verified `google-genai>=2.0.1` SDK supports `model="gemini-3-pro"` per `cohost_v4.py` POC; preview suffix may apply to specific releases — confirm at planning time |
| A2 | `gemini-embedding-2-preview` model ID is stable through v2.1 RC date | Standard Stack | MEDIUM — if Google promotes to GA and renames, cached embeddings invalidate (P73 carry-forward) |
| A3 | 6 sessions × 30 min ≈ 3 hours is enough corpus for F1 statistical power | Architecture Patterns "Corpus Assembly" | MEDIUM — if false-positive rate is high, may need more sessions; threshold lock can be re-tuned |
| A4 | $5/day Gemini cost cap holds at ~540 calls/night with prompt caching | Architecture Patterns "VCR.py Cassettes" | LOW — cassettes cap PR cost at $0; only nightly canary touches real API; Pro is ~10x Flash cost per call |
| A5 | Tauri externalBin target-triple convention will work for vibemix REC-09 (same as `dieharders/example-tauri-v2-python-server-sidecar` template) | Critical Correction | LOW — Tauri docs confirm; v2.0 Phase 21 already ships PyInstaller scaffold that can be extended |
| A6 | `comtypes` is a transitive dep of `pyaudiowpatch` already (no explicit add needed) | Standard Stack | LOW — verify at planning via `uv pip list` after install; if absent, add explicit `comtypes>=1.4; sys_platform == "win32"` |
| A7 | DDJ-FLX4 sync note POC source from `cohost_v4.py` is sufficient to synthesize MIDI-20 fixture autonomously (per autonomous mode) | Pitfalls "MIDI-20 fixture" | MEDIUM — if POC source is ambiguous, defer MIDI-20 to Kaan-action surface |
| A8 | `eval/corpus/` git-LFS at ~200MB stays under GitHub LFS free tier (1GB) | Architecture Patterns | LOW — single milestone of corpus; well within tier |
| A9 | Achird voice TTS via Gemini 3 Flash returns OPUS-encodable audio without extra transcoding | Code Examples | LOW — `cohost_v4.py` already uses Achird voice for live TTS via `google-genai`; same path works offline |

---

## Open Questions (RESOLVED with Recommendations)

Per autonomous mode + research-grounded recommendations:

### 1. Gate threshold tuning — exact F1 / substance / cosine values

- **What we know:** CONTEXT.md prescribes F1 ≥ 0.80 (both judges), substance ≥ 0.65, cited cosine ≥ 0.4, bypass ≤ 0.15.
- **What's unclear:** These values are research-grounded but unvalidated against actual corpus.
- **Recommendation:** Lock CONTEXT values for v2.1 RC. Document in THRESHOLD-LOCK.md. Plan a Phase 27 sub-task: "first-run calibration pass" that runs harness against corpus once + reports actuals before CI gate goes live. If actuals fall below thresholds significantly, either (a) tune corpus / rubric and re-run OR (b) lower thresholds with documented justification in THRESHOLD-LOCK.md.

### 2. Corpus sourcing — concrete URLs

- **What we know:** Sources locked to archive.org + CCMixter + FMA per CONTEXT.
- **What's unclear:** Specific public-domain DJ mixes vetted for license + diversity.
- **Recommendation:** Plan task = `eval/corpus/source_corpus.py` script that searches `archive.org` API with `licenseurl:*publicdomain*` filter for "DJ mix" + genre keyword; downloads 6 hand-picked (script outputs candidates, autonomous mode picks). FMA Electronic genre page (`freemusicarchive.org/genre/Electronic/`) is the secondary source. Document chosen URLs in `eval/corpus/LICENSES.md`.

### 3. `pytest-asyncio` presence

- **What we know:** Confirmed absent — `tests/midi/test_watcher.py` and others use `asyncio.run()` directly.
- **Recommendation:** Add `pytest-asyncio>=0.24` to `[dependency-groups] dev` ONLY IF replay harness tests need fixture-based async setup. Otherwise stay with the project's existing `asyncio.run()` pattern in test bodies (no new dep).

### 4. Achird voice TTS API surface

- **What we know:** Memory `feedback_no_clap_use_gemini_embedding` locks Gemini-only; `cohost_v4.py` and `agent/config.py:VOICE = "Achird"` already use it.
- **Recommendation:** `scripts/generate_ack_audio.py` uses `google-genai` 2.0.1 TTS surface with `voice="Achird"` — same call as live runtime. 40-line manifest:
  ```json
  [
    {"bucket": "drop_hit", "id": "01", "text": "let's go"},
    {"bucket": "drop_hit", "id": "02", "text": "yeah man"},
    ...
  ]
  ```
  Plan task should produce the manifest based on existing `fillers/*.pcm` filenames (alright, hmm, oh, okay, shit, wait, yeah, yeah_man) extended to 40 distinct phrases per bucket × 5 buckets.

### 5. MIDI-20 fixture provenance

- **What we know:** `tests/fixtures/ddj_flx4_sync_capture.jsonl` doesn't exist in the repo.
- **Recommendation:** Phase 27 task = synthesize fixture from `cohost_v4.py` `_NOTE_MAP` source. Document provenance in fixture frontmatter. If ambiguous (both 0x60 and 0x58 present in POC source), narrow to the binding actually fired during cohost_v4 sessions per memory `project_v4_canonical_baseline`. Fallback: defer MIDI-20 to Kaan-action surface in KAAN-ACTION-LEGAL.md (autonomous mode allows defer per `feedback_autonomous_no_grey_area_pause`).

### 6. CI cost cap mechanics

- **What we know:** Budget ≤ $5/day per memory.
- **Recommendation:** PR runs use `record_mode="none"` (cassette replay only — $0 cost). Nightly canary uses `record_mode="new_episodes"` (refreshes drift only — $1-2/night). Document cost projection table in `eval/COST-PROJECTION.md`. Add CI step that checks cassette-hit rate > 95% on PR runs (alert if drift forces real API calls).

### 7. eval-runs artifact storage

- **What we know:** CONTEXT prescribes `.planning/eval-runs/<hash>/`.
- **Unclear:** Long-term: do we keep every nightly canary forever?
- **Recommendation:** Last 30 days of nightly canaries + every PR-merge run. Older runs garbage-collected via cron. Stored as JSON + markdown (NOT git-LFS — small enough). Add `.gitignore` rule: `.planning/eval-runs/*/` keeps the directory but nightly auto-prune script removes individual run dirs older than 30 days.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `google-genai` Python SDK | Judge calls + cited-relevance + ack TTS | ✓ | `>=2.0.1` (verified pyproject.toml:30) | — |
| `numpy` | F1 + cosine math | ✓ | `>=2.4.4` (verified) | — |
| `pytest` + `pytest-mock` | Test infra | ✓ | `>=8.0` + `>=3.15.1` (verified) | — |
| `mido` + `python-rtmidi` | MIDI-20 fixture replay | ✓ | `>=1.3.3` + `>=1.5.8` (verified) | — |
| `av` (PyAV) | LATENCY-15 OPUS encode | ✓ | `17.0.1` (transitive via livekit-agents) | — |
| `pyyaml` | THRESHOLD-LOCK.md frontmatter parse | ✓ | `>=6.0` (in dev deps) | — |
| `vcrpy` | Cassettes for Gemini API tests | ✗ | — | Add to `[dependency-groups] dev` |
| `pytest-recording` | pytest convenience over VCR | ✗ | — | Optional; use raw VCR if not added |
| `pytest-asyncio` | Async fixtures (if needed) | ✗ | — | Use `asyncio.run()` in test bodies (existing pattern) |
| `comtypes` (Windows) | LATENCY-14 IMMNotificationClient bridge | ? | — | Verify transitive via pyaudiowpatch; add explicit if absent |
| `gh` CLI (CI) | Eval CI workflow | ✓ | (already in release.yml) | — |
| Git LFS | Corpus storage | ✓ | (already used by repo) | — |
| `GEMINI_API_KEY` env / GH secret | Judge + embedding + TTS | ✓ | (in `.env` for dev; in GH secrets for CI) | — |
| Macos arm64 + x86_64 runners | REC-09 multi-arch sidecar build | ✓ (arm64) / partial (x86_64) | macos-14 (arm64) is on GH Actions; Intel runners limited but available | Self-hosted runner OR use macos-13 image which is Intel |

**Missing dependencies with fallback:**
- `vcrpy` — add to dev deps
- `comtypes` — likely transitive; add explicit if not (defensive)

**No blocking missing dependencies.**

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest>=8.0` + `pytest-mock>=3.15.1` (existing; verified `pyproject.toml:140-141`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]` lines 180-188) |
| Quick run command | `uv run pytest tests/eval/ tests/runtime_closeouts/ -x` |
| Full suite command | `uv run pytest -ra` |
| Markers (existing) | `macos_audio`, `windows_only`, `integration`, `slow` |
| New marker (proposed) | `eval_canary` — for nightly-only eval tests; `pytest -m "not eval_canary"` skips on PR |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EVAL-01 | replay_harness reads recordings + replays through P17/18/19/20/22 | unit + integration | `pytest tests/eval/test_replay_harness.py -x` | ❌ Wave 0 |
| EVAL-02 | 2-judge cross-check ≥ 0.80 both | integration | `pytest tests/eval/test_judge_pro_rubric.py tests/eval/test_judge_flash_rubric.py -x` | ❌ Wave 0 |
| EVAL-03 | Corpus diversity gate — Hard Tek ≤ 70%, ≥ 3 genres | unit | `pytest tests/eval/test_corpus_diversity_gate.py -x` | ❌ Wave 0 |
| EVAL-04 | Substance metric ≥ 0.65 | unit | `pytest tests/eval/test_substance_metric.py -x` | ❌ Wave 0 |
| EVAL-05 | Cited-relevance cosine ≥ 0.4 | unit + cassette | `pytest tests/eval/test_cited_relevance.py -x` | ❌ Wave 0 |
| EVAL-06 | THRESHOLD-LOCK.md frontmatter parse + autonomous-sign | unit | `pytest tests/eval/test_threshold_lock.py -x` | ❌ Wave 0 |
| EVAL-07 | CI gate workflow valid YAML + step ordering | unit (yaml lint) | `actionlint .github/workflows/eval.yml` | ❌ Wave 0 |
| EVAL-08 | Scorecard JSON + markdown output schema valid | unit | `pytest tests/eval/test_scorecard.py -x` | ❌ Wave 0 |
| LIBRARY-09 | `register_library` invoked by `__main__.py` when cache exists | integration (mock spy) | `pytest tests/runtime_closeouts/test_register_library_invoked.py -x` | ❌ Wave 0 |
| LIBRARY-09 | End-to-end track citation lifecycle | integration (live fixtures) | `pytest tests/runtime_closeouts/test_track_citation_end_to_end.py -x` | ❌ Wave 0 |
| REC-09 | Both target-triple sidecars exist post-build with correct arch | integration (post-build) | `pytest tests/runtime_closeouts/test_universal2_sidecar.py -x` | ❌ Wave 0 |
| LATENCY-14 | IMMNotificationClient callback returns < 1ms | unit (mocked COM) | `pytest tests/runtime_closeouts/test_wasapi_default_device_change.py -m windows_only` | ❌ Wave 0 |
| LATENCY-15 | All 40 OPUS files non-silent + AIza-clean | unit | `pytest tests/runtime_closeouts/test_ack_bank_real_audio.py tests/runtime_closeouts/test_ack_bank_aiza_scan.py -x` | ❌ Wave 0 |
| MIDI-20 | DDJ-FLX4 sync note disambiguation against fixture | unit | `pytest tests/runtime_closeouts/test_flx4_sync_disambig.py -x` | ❌ Wave 0 |
| MASCOT-11 | Tracking-only — no test (Phase 35 ASSETS-03 owns) | manual | — | N/A |

### Sampling Rate

- **Per task commit:** `pytest tests/eval/ tests/runtime_closeouts/ -x` (~2-5s for unit tests with cassettes)
- **Per wave merge:** `pytest -ra` (full suite — ~60s for ~1961 existing tests + new)
- **Phase gate:** Full suite green + eval CI workflow green on PR
- **Nightly canary:** `pytest -m eval_canary` (touches real Gemini API)

### Wave 0 Gaps

- [ ] `tests/eval/conftest.py` — synthetic 5s WAV fixtures + cassette directory pointer
- [ ] `tests/eval/cassettes/` — directory + `.gitignore` for cassette refresh artifacts
- [ ] `tests/eval/test_replay_harness.py` — covers EVAL-01
- [ ] `tests/eval/test_judge_pro_rubric.py` — covers EVAL-02 Pro side
- [ ] `tests/eval/test_judge_flash_rubric.py` — covers EVAL-02 Flash side
- [ ] `tests/eval/test_corpus_diversity_gate.py` — covers EVAL-03
- [ ] `tests/eval/test_substance_metric.py` — covers EVAL-04
- [ ] `tests/eval/test_cited_relevance.py` — covers EVAL-05
- [ ] `tests/eval/test_threshold_lock.py` — covers EVAL-06
- [ ] `tests/eval/test_scorecard.py` — covers EVAL-08
- [ ] `tests/runtime_closeouts/conftest.py` — shared fixtures
- [ ] `tests/runtime_closeouts/test_register_library_invoked.py` — covers LIBRARY-09 invocation
- [ ] `tests/runtime_closeouts/test_track_citation_end_to_end.py` — covers LIBRARY-09 e2e
- [ ] `tests/runtime_closeouts/test_universal2_sidecar.py` — covers REC-09
- [ ] `tests/runtime_closeouts/test_wasapi_default_device_change.py` — covers LATENCY-14
- [ ] `tests/runtime_closeouts/test_ack_bank_real_audio.py` — covers LATENCY-15 (non-silence assertion)
- [ ] `tests/runtime_closeouts/test_ack_bank_aiza_scan.py` — covers LATENCY-15 (security)
- [ ] `tests/runtime_closeouts/test_flx4_sync_disambig.py` — covers MIDI-20
- [ ] Framework install: `uv add --group dev "vcrpy>=8.0" "pytest-recording>=0.13"` — REQUIRED for cassettes
- [ ] Framework install: `uv add --group dev 'comtypes>=1.4; sys_platform == "win32"'` if not transitive — REQUIRED for LATENCY-14

---

## Security Domain

**Note:** Phase 27 has limited direct security surface (offline eval + runtime patches). The biggest risk is API key leakage in eval artifacts and AIza key leakage in LATENCY-15 OPUS bytes.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (CI) | GitHub Actions secrets for `GEMINI_API_KEY`; never echoed in logs |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | THRESHOLD-LOCK.md frontmatter parsed via `pyyaml.safe_load` (not `load`); corpus manifest validated against jsonschema |
| V6 Cryptography | no (no new crypto in Phase 27) | — |
| V7 Error Handling and Logging | yes | Eval scorecard MUST NOT log Gemini API request bodies (could leak system prompts); only response verdicts |
| V14 Configuration | yes | `.github/workflows/eval.yml` uses `secrets.GEMINI_API_KEY`, never inline |

### Known Threat Patterns for Eval Harness + Runtime Close-Outs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| AIza key leaked in Achird OPUS bytes (LATENCY-15) | Information Disclosure | `scripts/build_sidecar.py:AIZA_PATTERN` re-scan after generation; CI assertion zero matches |
| Gemini API key echoed in scorecard logs | Information Disclosure | Scorecard generator MUST redact request bodies; log only verdicts |
| Eval cassettes contain real API responses with sensitive system prompts | Information Disclosure | Cassettes scrubbed of request headers + bodies via `vcrpy` `before_record_request` hook; only response verdicts retained |
| Threshold lock manipulation (lower thresholds to pass red eval) | Tampering | `THRESHOLD-LOCK.md` git-tracked; PR review on every change; CI grep gate flags threshold-lowering diffs in eval CI workflow |
| Fixture data injection (eval/corpus/) for false-pass | Tampering | Corpus manifest hash committed to git; CI fails if computed hash != manifest declaration |
| Apple Developer / SignPath impersonation (P46 — LEGAL CARVEOUT) | Repudiation | NEVER autonomously discharge; CI bash audit grep against POST/PUT to apple/signpath endpoints; KAAN-ACTION-LEGAL.md surface |
| Bundle ID change during REC-09 work (P63) | TCC permission reset | CI grep gate: `grep -q "world.bravoh.vibemix" tauri/src-tauri/tauri.conf.json5`; v2.0→v2.1 upgrade test |

---

## Sources

### Primary (HIGH confidence — VERIFIED via repo grep or official docs)

- **Repo CONTEXT/REQUIREMENTS/STATE/PITFALLS** — `.planning/phases/27-.../27-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/research/v2-1/PITFALLS.md` (P42-P52 + P63 + P69 + P70 verbatim)
- **Repo source files (verified line refs)**:
  - `pyproject.toml:30` — `google-genai>=2.0.1` confirmed
  - `pyproject.toml:9` — `requires-python = ">=3.12,<3.13"` (NOT 3.14 as auto-discovered CLAUDE.md claims)
  - `src/vibemix/state/evidence_registry.py:168` — `register_library` defined, NOT called
  - `src/vibemix/__main__.py:592, 689, 696-717` — insertion point for LIBRARY-09 patch
  - `src/vibemix/library/rekordbox.py:123` — `CACHE_PATH` constant
  - `src/vibemix/midi/controllers/ddj-flx4.json:24-27` — 4 sync entries `pending-verdict`
  - `scripts/replay_linter.py` (270 LOC) — Phase 20-03 scaffold for replay harness extension
  - `scripts/generate_placeholder_acks.py` — template for LATENCY-15 generator
  - `src/vibemix/audio/ack_bank/{drop_hit,track_change,mix_move,silence_break,generic_filler}/01..08.opus` — 40 silent placeholders
  - `src/vibemix/agent/config.py:26` — `VOICE: str = "Achird"` confirmed
  - `src/vibemix/platform/_audio_windows.py` — existing WASAPI loopback module (no IMMNotificationClient yet)
  - `.github/workflows/release.yml` — existing release workflow pattern (538 LOC) for `eval.yml` reference
- **Official Gemini API docs** — [https://ai.google.dev/gemini-api/docs/embeddings](https://ai.google.dev/gemini-api/docs/embeddings) — `embed_content` + `gemini-embedding-2-preview` MRL truncation confirmed
- **Tauri sidecar docs** — [https://v2.tauri.app/develop/sidecar/](https://v2.tauri.app/develop/sidecar/) — target-triple convention `vibemix-sidecar-aarch64-apple-darwin` confirmed
- **PyInstaller upstream feature notes** — [https://pyinstaller.org/en/stable/feature-notes.html](https://pyinstaller.org/en/stable/feature-notes.html) — lipo-merge of bundles is INFEASIBLE; PKG archive embedded in last slice only
- **Microsoft IMMNotificationClient docs** — [https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immnotificationclient](https://learn.microsoft.com/en-us/windows/win32/api/mmdeviceapi/nn-mmdeviceapi-immnotificationclient) — non-blocking callback requirement confirmed

### Secondary (MEDIUM confidence — WebSearch verified with multiple sources)

- **VCR.py 8.0 + pytest-recording** — [vcrpy.readthedocs.io](https://vcrpy.readthedocs.io/), [pypi.org/project/pytest-recording/](https://pypi.org/project/pytest-recording/) — record-replay cassette pattern current
- **comtypes** — [pypi.org/project/comtypes/](https://pypi.org/project/comtypes/) — pure-Python COM bridge for IMMNotificationClient
- **Gemini 3 LLM-as-judge best practices** — [futureagi.com/blog/best-llm-judge-models-2026](https://futureagi.com/blog/best-llm-judge-models-2026), [promptbuilder.cc/blog/gemini-3-prompting-playbook-november-2025](https://promptbuilder.cc/blog/gemini-3-prompting-playbook-november-2025) — structured JSON output + concise rationale pattern
- **Gemini structured output** — [firebase.google.com/docs/ai-logic/generate-structured-output](https://firebase.google.com/docs/ai-logic/generate-structured-output) — schema-strict JSON mode
- **Anthropic eval methodology (cited in v2.1 FEATURES.md research)** — [https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — three-tier eval pattern
- **FMA + archive.org public-domain DJ corpus** — [freemusicarchive.org/genre/Electronic/](https://freemusicarchive.org/genre/Electronic/), [archive.org licenseurl filter](https://archive.org/post/1107525/) — corpus sourcing patterns

### Tertiary (LOW confidence — single source or background only)

- **Gemini Embedding 2 cap (180s vs 80s discrepancy in PITFALLS P54)** — needs verification at planning time; affects EVAL-05 cited-relevance call sizing if response text > cap

---

## Metadata

**Confidence breakdown:**

- **Standard stack:** HIGH — every runtime dep verified against `pyproject.toml`; new dev deps (vcrpy, pytest-recording) verified current via WebSearch
- **Architecture (eval harness):** HIGH — anchored to existing `scripts/replay_linter.py` Phase 20-03 scaffold + verified primitive paths
- **Architecture (close-outs):** HIGH on LIBRARY-09 (verified call sites + register_library def), LATENCY-15 (verified placeholder structure + Achird voice config), MIDI-20 (verified pending-verdict status); HIGH on REC-09 *with critical correction* (lipo-merge infeasibility verified via PyInstaller upstream); HIGH on LATENCY-14 (verified IMMNotificationClient API + comtypes pattern)
- **Pitfalls:** HIGH — P42-P46 + P48 + P63 + P69 + P70 all carry-forward from v2.0 PITFALLS or v2.1 research; mitigation patterns documented + tested
- **Threshold values:** MEDIUM — F1/substance/cosine/bypass values are research-grounded but unvalidated against actual corpus; first-run calibration recommended

**Research date:** 2026-05-15
**Valid until:** 2026-06-15 (30 days for stable, 7 if Google releases Gemini 4 or `gemini-embedding-2-preview` GAs and renames)

---

## RESEARCH COMPLETE

**Phase:** 27 — Eval Harness + v2.0 Carry-Forward Close-Out
**Confidence:** HIGH (with one CRITICAL CORRECTION required before planning)

### Key Findings

1. **REC-09 lipo-merge approach is technically infeasible** per PyInstaller upstream — produces broken binaries because PKG archive lives in only one arch slice. **Plan must replace lipo-merge with Tauri target-triple convention** (`vibemix-sidecar-aarch64-apple-darwin` + `vibemix-sidecar-x86_64-apple-darwin`).
2. **`register_library` orphan verified** — defined at `evidence_registry.py:168`, NOT called anywhere in `__main__.py`. 5-line patch at line ~668 between agent construction and refresh_task creation.
3. **Phase 27 is ~80% wiring + corpus + rubrics, ~20% novel code** — every component has a canonical existing tool: `google-genai` 2.0.1 (judge + embed + TTS), VCR.py (cassettes), numpy (F1 + cosine), `mido` (MIDI replay), `comtypes` (WASAPI COM bridge).
4. **Project Python is 3.12, not 3.14** — auto-discovered CLAUDE.md "Tech Stack / Languages" section is stale; `pyproject.toml:9` enforces `>=3.12,<3.13`.
5. **MIDI-20 fixture doesn't exist in repo** — autonomous mode recommends synthesizing from `cohost_v4.py` POC source (per memory `project_v4_canonical_baseline`). If POC is ambiguous, defer to Kaan-action.
6. **Cost cap for nightly Gemini canary projected at $1-2/night** with prompt caching, well under $5/day budget. PR runs use cassettes ($0).

### File Created

`/Users/ozai/projects/dj-set-ai/.planning/phases/27-eval-harness-v2-0-carry-forward-close-out/27-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Every dep verified against pyproject.toml; new dev deps current per WebSearch |
| Architecture (eval harness) | HIGH | Anchored to existing Phase 20-03 scaffold + verified primitive paths |
| Architecture (close-outs) | HIGH | LIBRARY-09 + LATENCY-14/15 + MIDI-20 verified via repo grep; REC-09 has critical correction |
| Pitfalls | HIGH | P42-P46 + P48 + P63 + P69 + P70 mitigation patterns documented |
| Threshold values | MEDIUM | Research-grounded but unvalidated; first-run calibration recommended |
| MIDI-20 fixture | MEDIUM | Doesn't exist in repo; autonomous synthesis from POC vs Kaan-action defer |

### Open Questions (RESOLVED inline above)

All 7 open questions answered with autonomous-mode recommendations grounded in research. Planner can lock without further user input under `gsd-autonomous fully` mode.

### Ready for Planning

Research complete. Planner can now create PLAN.md files. **Critical correction on REC-09 (lipo-merge infeasibility) MUST be reflected in the plan** — switch to Tauri target-triple convention.
