# Voiceover Policy — Anti-Slop Doctrine

**Pitfall P58** mandate. This file is a policy AND a contract — its
existence + content is verified by
`tests/scripts/test_demo_film_no_ai_vo.py`.

---

## Policy

For the 30s demo film + any future vibemix promotional content:

1. **Default is NO voiceover.** Music + ambient session audio + on-screen
   captions carry the narrative.
2. If a VO is added, it MUST be written by Kaan or Francesco AND
   recorded by Kaan or Francesco (or another human collaborator).
3. NO AI-generated voiceover. NO AI TTS. NO synthesized narration.

---

## Why

The product bar is "real DJ friend in your ear, no AI slop". A demo
with AI-generated VO immediately contradicts the bar — viewers can hear
the cadence, the over-articulated transitions, the lack of breath
control. The first comment on the post will be "is this AI?" — and the
answer "yes, the demo IS AI, but the product isn't!" is a losing
argument.

A human-recorded VO with imperfections beats a clean AI VO every time
for this product.

---

## Forbidden services / endpoints (enforced by grep gate)

The following tokens MUST NOT appear in `scripts/demo_film/` source
files (.sh, .py, .json, .ts, .js):

- `elevenlabs` (ElevenLabs TTS)
- `openai` (OpenAI TTS)
- `gemini-tts` (Gemini TTS — even though Gemini is our LLM, TTS is
  forbidden for the demo film)
- `tts.googleapis` (Google Cloud TTS REST endpoint)
- `synth.voice` (any "synth voice" service signature)
- `ai-voiceover` (catch-all token)
- `synthesize_speech` (Google / AWS Polly API method name)

This doc itself is exempt from the grep gate — it lists the tokens
EXACTLY so the policy is unambiguous. The test reads only source files
(.sh / .py / .json / .ts / .js), not .md docs.

---

## What IS allowed

- Kaan/Francesco's real voice, recorded via any mic (phone, USB mic,
  Shure SM7 — doesn't matter).
- Voice processing (compression, EQ, noise gate) — these are mixing
  tools, not synthesis.
- Captions / on-screen text — preferred over VO for the v0.1 demo.
- Music — though see `recording_protocol.md` about rights.

---

## Decision protocol (for the v0.1 demo)

1. Cut the 30s film WITHOUT VO first (no-VO default).
2. Watch it back. If a beat feels unclear without narration → ask
   "would a caption fix this?".
3. Caption: yes → add caption, do not add VO.
4. Caption: no → consider human VO. Write 3 sentences max. Record in
   one take. No re-do for "polish" — the imperfection is the feature.
5. If at any point the temptation is "let me just have Gemini draft
   the line and I'll record it" → STOP. Kaan/Francesco writes the
   line. Gemini may critique a Kaan-written draft, but the first
   pass is human.

---

## Tracked Kaan-action

- `KAAN-ACTION-LEGAL.md` entry `ASSETS-VO` — final decision (no-VO OR
  human-VO) + asset commitment.

