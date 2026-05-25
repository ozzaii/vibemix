# Gemini Audio Truth Test — BLOCKED (billing), harness ready

**Date:** 2026-05-25
**Goal:** Empirically measure Gemini's raw audio understanding on Kaan's real
tracks to ground a product milestone. No theory, no fabrication.

## VERDICT (one line)

**BLOCKED — could not collect a single real Gemini output.** The configured
`GEMINI_API_KEY` authenticates correctly but the account's **prepay credits are
depleted**, so every call (audio *and* trivial text) returns
`429 RESOURCE_EXHAUSTED`. Per the truth-test rule, no results are invented. The
full harness is built and validated and will produce real data the moment the
account is funded.

## The blocker, verbatim

Every request — across `gemini-3-flash-preview`, `gemini-2.5-flash`,
`gemini-flash-latest`, with audio parts and with a 3-word text-only prompt —
returned:

```
ClientError("429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message':
'Your prepayment credits are depleted. Please go to AI Studio at
https://ai.studio/projects to manage your project and billing. Learn more at
https://ai.google.dev/gemini-api/docs/billing#prepay. ', 'status':
'RESOURCE_EXHAUSTED'}}")
```

### Why this is a billing block, not a transient rate limit or a code bug

- The key loads fine via `python-dotenv` (39 chars, `AIzaSy` prefix — valid
  direct-key format). No `401`/`403` → auth is fine.
- A **text-only 3-word prompt** ("say ok") also 429s → not audio-specific, not
  payload-size related.
- All three model names 429 identically → not a model-availability (`404`) issue.
- The message is literally "prepayment credits are depleted" with a billing
  link — this is account funding, not a per-minute quota that resets. There is
  no retry-after window to wait out.

**This requires Kaan to top up the Gemini/AI Studio project's prepay balance
(or swap in a funded key).** It is outside what the harness can fix.

## What WAS done (so the run is one command away once funded)

### Model resolution (no hardcoded literal)

Resolved via `vibemix.llm.model_router.resolve("library_auto_tag")`
→ `gemini-3-flash-preview` (ServiceTier.FLEX). This is the library
auto-tag path — the closest existing "describe this audio" route. (The live
co-host path `live_coach` → `gemini-3.5-flash` is the other candidate; for a
pure audio-understanding probe the Flash tag model is the right surface.)

### Track selection + ground truth (8 tracks, genre spread)

Excerpts: 75 s, **mono 16 kHz MP3**, pulled from the **middle** of each track
(the groove, not the intro). Ground truth is filename + folder + embedded
`genre` tag (no BPM/key tags were embedded — typical for free-DL pool tracks,
so BPM/key correctness can only be judged by ear/DSP later, not from metadata).

| id | file | folder genre tag | ground-truth read |
|----|------|------------------|-------------------|
| t1 | `hardtechno/PYREZ - DARK SIDE (Original Mix) Free DL.mp3` | Hard Techno | hard techno, ~150 BPM, dark |
| t2 | `hardtechno/Lil Texas - Rip City (Simtec HT Remix) [FREE DL].mp3` | Techno | hard techno remix, fast (~155-160) |
| t3 | `hardtechno/IGDA - Run The Hill (Original Mix).mp3` | (none) | hard techno, ~150 BPM |
| t4 | `hardtechno/Mitro - 90s.mp3` | Techno | hard techno / 90s-rave flavor |
| t5 | `PSYMIND/Miquiztli - Om Namah Shivaya.mp3` | Psycore | psytrance/psycore, fast (~180+), mantra vocal |
| t6 | `TEK JOURNEY/AcidVars - Free Tekno!.mp3` | **Ambient (mislabeled)** | acid tekno/freetekno, 303 acid, ~150-170 |
| t7 | `GROOVEY140/Patrick Prins - Le Voie Le Soleil (Solardo Remix).mp3` | "Solardo" (label, not genre) | tech-house / 140 groove |
| t8 | `francorella/Go Bang (96kbit_AAC).m4a` | (PNAU) | nu-disco / indie-dance, ~120 |

Note the **t6 metadata trap**: tagged "Ambient" but it is freetekno/acid — a
good adversarial case for whether Gemini trusts the audio over a (would-be) label.

### Excerpts (extracted, on disk)

All 8 confirmed written to `/tmp/truthtest/*.mp3` (290-394 KB each, 75 s, mono
16 kHz). ffmpeg extraction succeeded for every track.

### Consistency probe (designed, not yet run)

Harness sends **t1 twice** (run A in the main loop + an explicit run B) and
relies on the 8 distinct tracks to test per-track adaptation vs templated slop.
Cannot evaluate without outputs.

## Honest evaluation against the 5 axes

All five — **correctness, generalization, hallucination, sharpness, bottom-line**
— are **UNDETERMINED**. Zero real model outputs were obtained, and fabricating
plausible-looking Gemini text to fill them would defeat the entire purpose of a
truth test. No verdict on "good enough as a grounding source" can be honestly
given yet.

## Cost

**€0 spent** — all 9 intended calls (8 tracks + 1 probe) were rejected at the
billing gate before any tokens were processed. For the eventual real run:
9 calls x (~75 s audio ≈ ~2k audio tokens in + ~400 text out) on Flash FLEX is
on the order of **single-digit euro-cents total** — trivially cheap. The cost
story for *this experiment* is a non-issue; the milestone-scale cost concern
(per the existing memory note on Gemini audio embedding at ~€897/mo naive) is a
separate question about the embedding/similarity engine, not this understanding probe.

## To run it (after funding the key)

```bash
cd /Users/ozai/projects/dj-set-ai
uv run python /tmp/truthtest/run_test.py    # writes /tmp/truthtest/results.json
```

The harness (`/tmp/truthtest/run_test.py`) resolves the model via
`model_router`, loads `.env`, sends each excerpt as an `audio/mp3` Part with the
exact DJ-grade prompt from the task, captures raw text + latency + token usage
verbatim to JSON, and runs the t1-twice consistency probe. Excerpts persist at
`/tmp/truthtest/t1..t8.mp3`. Re-running this report's data section is then a
copy-paste of `results.json`.

## Nothing committed to git (per instruction).
