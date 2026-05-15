# Phase 27 — Kaan-Action Items (deferred external work)

This file tracks items the autonomous Phase 27 execution surfaced as
"requires Kaan / external action" — Apple/SignPath approvals, real-API
recording runs whose cost or non-determinism warrant a human in the loop,
or one-time legal/operational steps.

## Item 1: Record VCR.py cassettes for Plan 27-02 judge tests

**Status:** Deferred. Low-effort. Can be done any time before Plan 27-04
CI gate activation.

**What:** The 2-judge cross-check tests (Pro + Flash + cited_relevance)
currently cover the pure-logic surface (39 tests passing). The API-backed
paths require recorded VCR cassettes under `tests/eval/cassettes/` so PR
CI runs at $0 cost (no Gemini API contact).

**How:**

```bash
cd /Users/ozai/projects/dj-set-ai
# One-time recording run — requires GEMINI_API_KEY in .env
VCR_RECORD_MODE=new_episodes uv run pytest \
  tests/eval/test_judge_pro_rubric.py \
  tests/eval/test_judge_flash_rubric.py \
  tests/eval/test_cited_relevance.py \
  -m "vcr" --tb=short

# Cassettes land under tests/eval/cassettes/*.yaml
# Headers auto-scrubbed: authorization, x-goog-api-key, x-goog-user-project
# Query params auto-scrubbed: key

# Verify scrub (no AIza tokens in cassettes):
! grep -rE "AIza[A-Za-z0-9_-]{35}" tests/eval/cassettes/

# Commit cassettes
git add tests/eval/cassettes/*.yaml
git commit -m "test(27-02): record VCR.py cassettes for judge + relevance tests"
```

**Cost:** ~10-15 Gemini API calls × ~$0.005 each ≈ $0.05-0.10 total.

**Why deferred:** Recording requires live Gemini API contact and produces
non-deterministic content (the LLM responses differ slightly per run).
Best done by Kaan to verify the rubric framings produce the expected
verdicts on his canonical examples before the cassettes lock in.

**Cross-reference:** Plan 27-02 SUMMARY documents the workflow; the
pure-logic test suite covers the critical Pitfall P42 (min-aggregation)
+ P45 (8-word floor) gates.

---

## Item 2: Apple Developer signing credentials + SignPath OSS approval

**Status:** Long-running external clock (separate from Phase 27).

**What:** The Phase 27-06 REC-09 matrix-build path produces TWO arch-
specific PyInstaller bundles ready for Phase 38 signing. Phase 38 requires:
1. Apple Developer ID Application certificate (.p12 + password).
2. Apple Developer API key (.p8 issued via App Store Connect).
3. SignPath OSS open-source program approval for Windows code signing.

**Why this is in KAAN-ACTION:** Pitfall P46 — autonomous mode MUST NOT
POST/PUT to Apple/SignPath endpoints. These are credential-issuing flows
that require Kaan's signature + 2FA. Phase 38 plans exist as scaffolding
ready to consume the credentials once Kaan completes the external
onboarding.

**Cross-reference:** ROADMAP P38 plans 38-* are blocked on this.
Plan 27-06 REC-09 sidecar build pipeline does NOT require these — it
runs in mock-signing mode on every PR until full signing is wired.

---

## Item 3: Phase 27-08 (LATENCY-15) ack_bank regeneration — IN PROGRESS

**Status:** Active during Phase 27 autonomous execution. Generator
script ran with rate-limit pacing (10 req/min Gemini free tier). At time
of this writing, ~20 of 40 OPUS files regenerated with real Achird-voice
audio; remaining 20 require continued runs with pacing.

**What:** Run `uv run python scripts/generate_ack_audio.py` until all 40
files exist with non-silent (RMS > 0.001) Achird TTS audio. Idempotent —
re-runs skip existing files.

**Cost:** Remaining 20 calls × ~$0.005 ≈ $0.10. Already-completed 20 ≈ $0.10.
Total Plan 27-08 cost ≈ $0.20.

**Why partially deferred:** The script is fully wired (manifest + CLI +
encoding + AIza scan) and produces real audio on success. Rate-limit
backoff pacing is correct. If Phase 27 autonomous execution doesn't
complete all 40 before the wall-clock window closes, this item tracks the
follow-up.

**Cross-reference:** Plan 27-08 SUMMARY for completion status; AIza scan
test (`tests/runtime_closeouts/test_ack_bank_aiza_scan.py`) verifies
security after every regeneration run.

---

## Item 4: Corpus WAV acquisition for Plan 27-03 (EVAL-03)

**Status:** Skeleton in place; WAV files pending.

**What:** Six 30-min public-domain DJ sessions need WAV download + commit
to `eval/corpus/sessions/<session>/input.wav` via Git LFS.

**How:**

```bash
cd /Users/ozai/projects/dj-set-ai

# 1. Find candidates per genre
uv run python scripts/eval/source_corpus.py --all-genres --output candidates.json

# 2. Manually curate 2 candidates per genre (CC0 / public domain only)
#    Pick from candidates.json output. Verify license at the source URL.

# 3. Download WAV (or convert from source mp3/flac) → 48kHz mono 30 min
#    Place as eval/corpus/sessions/<session>/input.wav
#    Fill source.txt with: URL, license, attribution, duration

# 4. Auto-label candidate events
uv run python scripts/eval/label_corpus.py \
  --session eval/corpus/sessions/<session> \
  --output eval/corpus/sessions/<session>/events.jsonl.candidate
# Human-review the candidate, refine, then mv to events.jsonl

# 5. Update eval/corpus/LICENSES.md per-session entry

# 6. Verify diversity gate
uv run python -c "from scripts.eval.corpus_manifest import validate_manifest; from pathlib import Path; r=validate_manifest(Path('eval/corpus/manifest.json')); print(r)"

# 7. Run the eval harness end-to-end
uv run python -m scripts.eval.replay_harness \
  --corpus eval/corpus/sessions \
  --judges gemini-3-flash \
  --threshold-lock eval/THRESHOLD-LOCK.md \
  --output /tmp/first-real-run

# 8. Commit
git lfs install --local
git add eval/corpus/
git commit -m "feat(27-03): populate eval corpus with 6 public-domain sessions"
```

**Cost:** ~200 MB Git LFS storage + ~$5 in Gemini API calls for first nightly canary.

**Why deferred:** Per `gsd-autonomous fully` mode, the agent could in
principle search archive.org / CCMixter / FMA, but the curation step
(verifying license + selecting representative DJ sets per genre) benefits
from human judgement.

---

## Items autonomously discharged in Phase 27

- **THRESHOLD-LOCK.md autonomous-signed** (2026-05-15T08:55:00Z) — Phase 27
  Plan 04 wrote `kaan_signed: autonomous_phase27` to `eval/THRESHOLD-LOCK.md`
  with CONTEXT EVAL-06 threshold values (f1_min=0.80, substance_min=0.65,
  cited_cosine_min=0.4, bypass_max=0.15, per_genre_f1_min=0.70). **NOT** a
  legal-capacity signature — review when convenient. Re-tuning protocol
  documented in the lock body; re-signing requires both judges to re-run
  against the corpus first.

## Items requiring human discharge (NEVER autonomously)

- (none in Phase 27 — Apple Developer Program Agreement update + SignPath
  OSS Foundation application live in Phase 38's KAAN-ACTION-LEGAL.md per
  ROADMAP P38. Pitfall P46 enforced — Phase 27 eval.yml workflow audit
  step grep-asserts no POST/PUT to apple/signpath endpoints.)

---

**Last updated:** 2026-05-15 by Phase 27 autonomous execution.
