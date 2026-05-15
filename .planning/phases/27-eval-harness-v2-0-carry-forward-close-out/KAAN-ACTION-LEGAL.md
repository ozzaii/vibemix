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

**Last updated:** 2026-05-15 by Phase 27 autonomous execution.
