---
channel: hacker_news
post_type: Show HN
language: en
hero_beat: A (amber overlay ring on EQ deck synced with Gemini voice) — engineering audience leads with grounding architecture
media: 30s YouTube unlisted linked from author first comment + repo link in title
status: draft
tbd_markers:
  - <TBD repo_url> — GitHub repo URL (this IS the HN submission URL)
  - <TBD demo_youtube> — YouTube unlisted (in author first comment)
anti_slop_thesis_position: title (implied) + author first comment paragraph 2
note: HN rewards specificity + author-comment-first context. No marketing language. Engineering claims are testable or they get torn apart.
---

# Hacker News — Show HN post

## URL submitted

<TBD repo_url>

## Title

> Show HN: vibemix – open-source AI co-host for DJ sets, grounded in audio/screen/MIDI

_(80 char limit. Current draft: 79 chars including "Show HN: " prefix. If trimming: "Show HN: vibemix – AI co-host for DJ sets, grounded in audio + screen + MIDI" → 80 exact.)_

## Author first comment (post immediately after submission)

> Author here. Some context HN might find interesting:
>
> The original goal was a generic "AI commentary for DJ sets" tool. Early prototypes were unusable — every iteration of better prompting produced more polished generic-AI-assistant slop. The actual fix was a grounding pipeline: every reaction has to cite at least one real event observed in the audio, on the DJ software's screen, or on the MIDI controller. If the model can't ground, it emits a `<silence/>` short-circuit token and stays quiet.
>
> **Three input streams feed the same Gemini Live session:**
>
> 1. Master audio (BlackHole on macOS, WASAPI loopback on Windows), downsampled 48 → 16 kHz via `scipy.signal.resample_poly`
> 2. DJ software window captured at ~1 fps, cropped via Quartz / DWM to the app window bounds
> 3. MIDI controller — every CC, note, jog wheel — parsed by `mido`, decoded against per-controller profile JSON (10 SKUs curated, sniff tool for the rest)
>
> Reactions fire from typed events derived from cross-source diffs: `TRACK_CHANGE`, `PHASE` (intro/build/drop/breakdown), `LAYER_ARRIVAL` (sub-bass / lead / vocal coming in), `MIX_MOVE`, `KAAN_SPOKE` (mic detection). Each event type has its own cooldown. No single source can trigger a reaction alone.
>
> **Anti-slop layer on top:**
>
> - Negative dictionary at the prompt layer ("this track," "the vibe," "feels like" — all phrases that correlate with hallucinated content in our test sessions)
> - Describe-before-infer rule (cite observed event before any interpretation)
> - Past-tense framing (no live commentary — only critique of moves already finished)
> - Per-session anti-repetition ring (last 8 reactions kept in context)
> - `<silence/>` token short-circuits any reaction the model can't ground
>
> **Tech stack:**
>
> - Gemini 2.5 Flash Native Audio via LiveKit RealtimeModel (persistent WebSocket)
> - Tauri shell + vanilla TS (no React — startup-cost discipline) + Three.js mascot overlay
> - Python 3.14 sidecar for audio I/O, MIDI decode, event detection, screen capture
> - Bravoh-managed proxy with per-client rate limit so the API key doesn't ship in the binary
>
> **Caveats:**
>
> - Mac + Windows only. Linux out of scope — loopback audio stack divergence triples maintenance.
> - The Bravoh proxy means a server is in the loop. Apache 2.0 client, BYO-key env var path supported.
> - First OSS release from Bravoh (AI artist platform). The main Bravoh product is closed and unrelated to vibemix.
>
> **Demo:** <TBD demo_youtube> (30s — three signature beats: amber overlay ring on EQ deck synced with reaction, mascot anticipation 200ms before voice, deliberate 3s silence as anti-slop made viewable)
>
> **What I'd most appreciate feedback on:**
>
> 1. **Anti-slop gate design.** The `<silence/>` short-circuit is the most fragile part — happy to discuss alternatives or related literature.
> 2. **Controller library scope.** 10 SKUs out of the box + sniff tool for the rest. Aggressive curation vs community PRs — where's the line?
> 3. **API-key-in-distributed-binary problem.** We chose the proxy route over BYO-key for UX reasons. Curious how others have handled this for tools targeting non-developer end users.

## Notes for Kaan

- Submit Tuesday/Wednesday 9-11am EST (HN peak).
- Post the author first comment within 60 seconds of submission. HN penalizes Show HNs that don't have author context up top.
- Stay in the thread for the first 4 hours. HN rewards substantive author replies; downvotes the rest.
- Pre-warm: do NOT have Bravoh team upvote or comment. HN's vote-ring detection is aggressive and a Show HN flag from us would tank the post permanently.
- If anyone asks about the closed-source Bravoh proxy, link to the env-var BYO-key path in the README. Don't get defensive.
