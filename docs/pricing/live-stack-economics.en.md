# vibemix — Live Co-Host Cost Economics

**Status:** source-audited internal cost model, rechecked 2026-06-01. The
production voice path is **local MOSS-only**: there is no Cartesia, Gemini TTS,
OpenAI TTS, or other paid cloud voice fallback in the live co-host chain. Paid
voice vendors remain in the table only as explicit what-if sensitivity rows.
Reproduce any figure with `vibemix library budget --stack live`. This document
measures cost; it does not decide model quality.

## TL;DR

One daily-active DJ costs about **€0.99 per month** to run with the current
default stack. The voice provider bill is **€0.00** because MOSS runs on-device.
The dominant paid leg is now listening/audio input into the Gemini brain.

Chosen stack: brain `live_coach_cand_25flash`, voice **Local MOSS**, listening
mic→Gemini Part (no separate speech-to-text), set-prep **DeepSeek V4 Pro**,
LiveKit running **local** (direct mode).

## What one DJ costs

Per active DJ, with the chosen stack:

| Usage | €/DJ/month | €/set |
|---|---:|---:|
| Daily-active (20 sets/month) | **€0.99** | **€0.05** |
| Casual (4 sets/month) | **€0.20** | **€0.05** |

### Why €0.99

| Leg | €/DJ/month | Fleet €/month @ 10k DAU | What you pay for |
|---|---:|---:|---|
| listen | **0.66** | **6,624** | Gemini audio-input tokens for the live set window |
| brain | 0.31 | 3,066 | reading evidence and writing the reaction |
| tts | **0.00** | **0** | local MOSS voice; no provider bill |
| Viber set-prep | 0.02 | 227 | off-session set building and library questions |
| LiveKit | 0.00 | 0 | local direct mode; no Cloud room |

The paid center of gravity moved from speech to listening. MOSS removes the old
cloud-TTS bill; it does not remove the need to package/download the MOSS model
or prove the voice on a real release artifact.

## Sensitivity: what paid voice would cost

Brain/listening fixed to the current default. Fleet at 10,000 daily-active DJs.

| TTS voice | Fleet €/month | Note |
|---|---:|---|
| **Local MOSS (production)** | **9,917** | current default; provider TTS bill is zero |
| OpenAI tts-1 | 47,011 | paid what-if only |
| Gemini value TTS | 54,371 | historical paid what-if only |
| Cartesia Sonic | 83,858 | legacy-derived sensitivity row; **UNVERIFIED** |
| Gemini premium TTS | 98,825 | historical paid what-if only |
| ElevenLabs Flash v2.5 | 133,565 | paid what-if only |
| Hume Octave 2 | 133,565 | paid what-if only |

Cartesia is **not** the production voice. Its row stays because the budget model
keeps historical sensitivity comparisons, but the price is legacy-derived and
must not be used as external pricing copy.

## Other cost levers

1. **Listening window and brain tier.** With MOSS local, audio-input tokens are
   the biggest paid leg. Reducing unnecessary audio context is now more valuable
   than swapping voice vendors.
2. **Spoken-reply length + reaction density.** These still matter for product
   feel and CPU/model load, but they no longer add provider TTS spend on the
   production path.
3. **Usage (sets/month).** Linear. A casual DJ at 4 sets costs one fifth of a
   daily DJ at 20.
4. **LiveKit transport.** Local direct mode costs €0. LiveKit Cloud would bill
   per agent-session-minute and is not part of the default product path.

## Cache: the load-bearing assumption

The €0.99 figure assumes a 90% implicit input-cache hit. Drop to a cold cache
(0% hit) and the fleet bill rises from €9,917 to €16,713/month at 10k DAU.
The `SessionMeter` in `budget.py` computes the true `cache_hit_rate` from
`usage_metadata`; measure it on a live soak before trusting the model for
pricing decisions.

## Source-audited prices

| Row | Role | Source | Status |
|---|---|---|---|
| Gemini brain/listening rows | brain + audio input | ai.google.dev/gemini-api/docs/pricing | verified 2026-05-31 |
| Local MOSS | voice | `vibemix.agent.local_tts` | verified as zero provider bill |
| DeepSeek V4 Pro | Viber | api-docs.deepseek.com official pricing note | verified 2026-05-31 |
| Cartesia Sonic | voice what-if | cartesia.ai/pricing | **unverified** legacy-derived sensitivity |
| OpenAI / ElevenLabs / Hume voice rows | voice what-if | vendor pricing pages | comparison rows only |
| LiveKit Cloud agent | transport what-if | livekit.io/pricing | unused in local direct mode |

## Caveats

- This proves source-level cost math, not release readiness. A shippable app must
  still prove MOSS model availability, packaged sidecar behavior, and live audio
  output on a clean machine.
- The 90% cache-hit assumption is not yet a live-measured product fact.
- This proves cost, not taste. Whether the chosen brain and MOSS voice feel like
  a real DJ friend remains a listening pass.

## Reproduce

```bash
# current production-cost stack
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts moss-local

# paid-voice what-if rows
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts live_coach_tts_fallback
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts live_coach_tts
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts sonic-3

# cold-cache and casual-DJ checks
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts moss-local --cache-hit 0.0
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts moss-local --sessions-per-month 4
```
