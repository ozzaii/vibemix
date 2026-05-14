---
channel: twitter
language: en
hero_beat: A (amber overlay ring on EQ deck synced with Gemini voice)
media: 30s MP4 (landscape 16:9, sound-on assumed) + thread embeds 720x720 GIF
status: draft
tbd_markers:
  - <TBD repo_url> — GitHub repo URL (assumes bravoh/vibemix; verify org slug)
  - <TBD demo_mp4> — link to Wave 4 demo film (YouTube unlisted or Twitter native upload)
  - <TBD discord_invite> — Discord invite (Wave 6 Kaan-action)
anti_slop_thesis_position: tweet 1 hook + tweet 2 framing
---

# Twitter / X — launch thread (EN)

## Tweet 1 (hook, 280-char ceiling)

> An open-source AI co-host for DJ sets that actually listens to your music. Not "AI commentary." Not hallucinated track names. It watches your audio, your DJ software's screen, and your controller — then talks to you like a real DJ friend.
>
> [30s demo MP4 — <TBD demo_mp4>]

_(Character count target ~270 with the embed — trim "actually" / "real DJ friend" → "real friend" if over.)_

## Tweet 2 — the anti-slop framing

> Most "AI for music" tools sound like a chatbot reading liner notes. We hit that wall and figured out why: prompting alone can't fix it. The model has to be grounded in what's actually happening — every reaction tied to a real event in the audio, on screen, or on the controller.

## Tweet 3 — the 3-source grounding stack

> So vibemix listens on three channels at once:
>
> 1. Master audio (BlackHole / WASAPI loopback)
> 2. DJ software window (screen capture, ~1 fps)
> 3. MIDI controller (every CC + note + jog move)
>
> If a reaction can't cite at least one of those, the prompt suppresses it. Silence is a feature.

## Tweet 4 — close + community PR call

> Mac + Windows binaries. Apache 2.0. 10 controllers mapped out of the box (Pioneer DDJ family, Hercules Inpulse, Numark Party Mix Live). Bring your controller — there's a sniff tool + new-controller issue template if yours isn't in the box yet.
>
> Repo: <TBD repo_url>
> Discord: <TBD discord_invite>

## Notes for Kaan

- Post the thread when Beat A demo is live on YouTube unlisted (Wave 4 deliverable).
- Pin tweet 1 for ~72h.
- Quote-tweet from the Bravoh account ~30 min after main thread (warm boost, not co-tweet).
- If hashtags: at most `#opensource #dj #aiformusic` on tweet 4 only (Twitter algorithm penalizes hashtag-heavy threads).
