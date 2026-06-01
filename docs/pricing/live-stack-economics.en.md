# vibemix — Live Co-Host Cost Economics

**Status:** source-audited internal cost model, rechecked 2026-05-31. Gemini,
DeepSeek, Hume, Deepgram, and OpenAI rows are grounded in current official pages.
The Cartesia row is still a legacy-derived, unverified sensitivity row, so this
copy is not external pricing copy until that effective rate is confirmed in
billing. Reproduce any figure with `vibemix library budget --stack live`. This
document measures cost. It does not choose the business model, and it does not
rate model quality (Kaan's ear decides that).

## TL;DR

One daily-active DJ costs about **€9.74 per month** to run. The co-host's voice eats roughly three quarters of that. The Gemini brain (thinking plus hearing) takes most of the rest. Set-prep and the LiveKit pipeline round to zero. The text-to-speech vendor is the lever that moves the bill.

Chosen stack: brain `gemini-3.5-flash`, voice **Cartesia Sonic**, listening mic→Gemini (no separate speech-to-text), set-prep **DeepSeek V4 Pro**, LiveKit running **local** (direct mode).

## What one DJ costs

Per active DJ, with the chosen stack (brain `gemini-3.5-flash` + Cartesia voice):

| Usage | €/DJ/month | €/set |
|---|---|---|
| Daily-active (20 sets/month) | **€9.74** | €0.49 |
| Casual (4 sets/month) | **€1.95** | €0.49 |

### Why €9.74

| Leg | €/DJ/month | Share | What you pay for |
|---|---|---|---|
| **TTS (Cartesia voice)** | **7.39** | **76%** | the co-host speaking ~12s per reaction, ~1,600 reactions/month |
| brain (`gemini-3.5-flash`, text) | 1.33 | 14% | reading the evidence, writing the reaction |
| listen (same Gemini, audio in) | 0.99 | 10% | hearing the set (master + mic) as audio tokens |
| Viber set-prep (DeepSeek V4 Pro) | 0.02 | ~0% | crafting sets, answering questions, off-session |
| LiveKit | 0.00 | 0% | local direct mode, no Cloud room |

The Gemini brain hears and thinks in one model call: `listen` is its audio-input half, `brain` is its text half. Together they take 24%. Speaking takes the other 76%. You pay for the co-host to talk.

## The cost bench: brain fixed, voice varied

Brain held at `gemini-3.5-flash`. Fleet at 10,000 daily-active DJs.

| TTS voice | €/DJ/month | Fleet €/month | Note |
|---|---|---|---|
| Gemini 2.5 Flash TTS (value) | 6.79 | €67,887 | cheapest on paper, but **mute live** |
| **Cartesia Sonic (live pick)** | **9.74** | **€97,374** | works live; cost row is legacy-derived/unverified |
| Gemini 3.1 Flash TTS (currently wired) | 11.23 | €112,341 | premium, the bill today |

Cartesia wins the live reliability test because it actually produces audio.
Under the legacy-derived sensitivity row it also runs 13% under the Gemini 3.1
voice the router uses today (€97k vs €112k fleet), but do not present that
Cartesia price externally until the current public-plan/account-billing
conversion is confirmed. Gemini 2.5 TTS is cheaper still, but it returns "No
audio content generated" on the live rig, so it is out.

## The five cost levers, ranked

1. **TTS vendor.** Swings the fleet from €68k (Gemini 2.5) to €147k (ElevenLabs). The decision that matters.
2. **Spoken-reply length + reaction density.** Both feed the TTS leg directly and carry near-zero quality risk. Cutting the spoken reply 12s→9s saves ~18%; throttling 80→60 reactions/set saves ~25%. A real DJ friend is terse and picks moments, so a tighter co-host can read as more authentic, not less.
3. **Usage (sets/month).** Linear. A casual DJ at 4 sets costs one fifth of a daily DJ at 20.
4. **Brain tier.** A real lever, not free. Swapping the premium `gemini-3.5-flash` for the cheapest Flash cuts the fleet ~€13.5k (14%), because the cheaper Flash carries a $1.00/1M audio-input rate against the premium's $1.50/1M, so it trims both the brain and the listen leg. This is the one lever that changes what the co-host says, so it ranks below the zero-risk speech knobs and gates on Kaan's ear.
5. **LiveKit transport.** Local direct mode costs €0. LiveKit Cloud would bill $0.01 per **agent-session-minute**, about €138k/month at 10k DAU, larger than the whole rest of the stack combined. Running local is the biggest cost decision, and it is already made.

## Cache: the load-bearing assumption

The €9.74 figure assumes a 90% implicit input-cache hit. That single number carries the model. A 90% hit cuts the brain's text-input cost ~5x. Drop to a cold cache (0% hit) and the per-DJ bill rises to €12.34 (+38%). The repo never measures the real hit rate, so treat 90% as a hopeful default, not a fact. The `SessionMeter` in `budget.py` already computes the true `cache_hit_rate` from `usage_metadata`. Measure it on a live soak before trusting €9.74. The brain's input token count (modeled at 1,900) is also likely low: a full grounded prompt with the persona block plus the always-appended anti-slop and citation stack runs closer to 3,300-4,600 tokens. At 90% cache that adds about €0.67. At a cold cache it adds €3.53, so the two risks compound.

## Source-audited prices (USD)

| Model | Role | Input /1M | Output /1M | Cached in /1M | Source | Read |
|---|---|---|---|---|---|---|
| `gemini-3.5-flash` | brain | $1.50 | $9.00 | $0.15 | ai.google.dev/gemini-api/docs/pricing | 2026-05-31 |
| `gemini-3.1-flash-tts-preview` | voice | $1.00 text | $20.00 audio | — | same | 2026-05-31 |
| `gemini-2.5-flash-preview-tts` | voice | $0.50 text | $10.00 audio | — | same | 2026-05-31 |
| Cartesia Sonic (`sonic-3`) | voice | legacy-derived ~$29.9/1M char | — | — | cartesia.ai/pricing (UNVERIFIED: current page lists Sonic-3.5 minutes, not a per-character SKU) | 2026-05-31 |
| `deepseek-v4-pro` | Viber | $0.435 | $0.87 | $0.0036 | api-docs.deepseek.com official 1/4-price note | 2026-05-31 |
| Deepgram Nova-3 (alt STT) | listen | — | — | — | $0.0048/min streaming | 2026-05 |
| LiveKit Cloud agent (unused) | transport | — | — | — | $0.01/agent-session-min, livekit.io/pricing | 2026-05 |

Gemini bills TTS audio as 25 tokens per second. `gemini-3.5-flash` lists no
separate audio-input rate, so audio rides its standard $1.50/1M input rate (not
free). DeepSeek's official page says V4 Pro pricing is adjusted to one quarter
of the original price after the 75% promotion ends on 2026-05-31 15:59 UTC, so
$0.435/$0.87 is the current official row. Cartesia is different: the current
public page lists Sonic-3.5 plan minutes and plan prices but no exact
per-character SKU. The repo keeps the old $29.9/1M-character row only as an
unverified sensitivity placeholder until the effective account/billing rate is
confirmed.

## Assumptions behind the numbers

- One reaction: 1,900 input tokens, 40 output tokens (from the Phase-81 bench; likely closer to 3,300-4,600 input in production, see Cache section), ~12s spoken, ~18s audio window into the brain.
- 80 reactions per 75-minute set (~1.07/min, well under the 22s global-floor ceiling of ~205).
- 90% implicit input cache hit (unverified, see Cache section).
- Daily-active DJ runs 20 sets/month (generous, ~5/week); casual runs 4.
- USD to EUR at 0.92.

## Caveats

- Cartesia's per-character rate is legacy-derived, not an official SKU. Do not
  use the €9.74/€97k headline as external pricing copy until the current Sonic
  public-plan or account-billing conversion is confirmed.
- Gemini TTS is the cheapest cloud voice on paper, yet it returns no audio on the live rig. Cartesia is the live pick for reliability, not just cost. The wired fallback chain currently degrades from Cartesia onto the mute Gemini voices, so a working non-Gemini secondary (OpenAI tts-1) belongs in the chain.
- The 12s/30-word reaction is chattier than a true one-liner (5-12 words, ~6s). A tighter reaction drops the per-DJ bill toward €5.6, so spoken length is a real product-and-cost knob.
- This proves cost. Whether `gemini-3.5-flash` sounds like a real DJ friend stays Kaan's ear call.

## Reproduce

```bash
# the chosen stack
vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3
# the three-voice cost bench
vibemix library budget --stack live --dau 10000 --brain live_coach --tts live_coach_tts          # Gemini 3.1 TTS
vibemix library budget --stack live --dau 10000 --brain live_coach --tts live_coach_tts_fallback  # Gemini 2.5 TTS
# the brain-tier lever (cheapest Flash)
vibemix library budget --stack live --dau 10000 --brain live_coach_cand_25flash --tts sonic-3
# the LiveKit Cloud what-if + cold cache + casual DJ
vibemix library budget --stack live --dau 10000 --livekit-per-min 0.01
vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3 --cache-hit 0.0
vibemix library budget --stack live --dau 10000 --brain live_coach --tts sonic-3 --sessions-per-month 4
```
