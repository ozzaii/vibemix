---
channel: reddit
subreddit: r/programming (primary) + r/opensource (secondary, ~24h delay)
language: en
hero_beat: A (amber overlay ring on EQ deck synced with Gemini voice) — leads with engineering breakdown angle
media: 30s YouTube unlisted upload linked from body + 720x720 GIF inline
status: draft
tbd_markers:
  - <TBD repo_url> — GitHub repo URL
  - <TBD demo_youtube> — YouTube unlisted video URL
  - <TBD demo_gif> — 720x720 GIF for inline embed
anti_slop_thesis_position: paragraph 2 (under "the problem")
note: r/programming hates self-promo. Frame as engineering breakdown, not launch announcement. Mention Bravoh once, honestly, then move on.
---

# Reddit r/programming — Show & Tell post

## Title

> I built an open-source AI co-host for live DJ sets, and "just prompt better" wasn't enough. Here's how the grounding stack works.

## Body

vibemix is an AI co-host for live DJ sets. It listens to your master output, watches your DJ software, ingests your MIDI controller, and reacts in your headphones — like a friend who actually heard the mix, not a chatbot reading liner notes.

I'm posting because the most interesting engineering problem was a negative result: we couldn't get usable AI reactions out of "better prompting." Every prompt iteration produced more polished generic-AI-assistant slop. The fix wasn't a smarter prompt — it was building a grounding pipeline so the model literally couldn't react to events that didn't happen.

### The architecture

Three input streams feed into the same Gemini Live session:

1. **Master audio** — captured via BlackHole (macOS) or WASAPI loopback (Windows), downsampled 48 kHz → 16 kHz with `scipy.signal.resample_poly`, pushed as continuous PCM frames.
2. **DJ software window** — screen-captured at ~1 fps with `mss`, cropped to the DJ software window bounds via macOS Quartz / Windows DWM, sent as image frames.
3. **MIDI controller** — every CC + note + jog wheel move, parsed by `mido`, decoded against per-controller profile JSON.

The reaction layer never fires from a single source. It fires from typed events derived from cross-source diffs — `TRACK_CHANGE`, `PHASE` (intro/build/drop/breakdown), `LAYER_ARRIVAL` (sub-bass / lead / vocal coming in), `MIX_MOVE` (filter / EQ / fader manipulation), `KAAN_SPOKE` (mic detection). Each event type has its own cooldown so we don't carpet-bomb the user with reactions.

### The anti-slop stack

On top of grounded events, there's a stack to prevent the model from inventing details:

- **Negative dictionary**: phrases like "this track," "the vibe," "feels like" are pre-rejected at the prompt layer because they've all been observed correlating with hallucinated content.
- **Describe-before-infer**: the system prompt requires citing the observed event before any interpretation. "Filter swept ~3s then dropped" *then* "nice tension build" — never the inverse.
- **Past-tense framing**: reactions reference events that already finished. No "this drop is hitting" — only "that drop hit."
- **`<silence/>` short-circuit token**: when the model can't ground a reaction, it emits silence. Silence is a feature, not a failure mode. In demos we explicitly show 3-second gaps where the AI stays quiet.
- **Per-session anti-repetition ring**: last 8 reactions are kept in context to prevent the model repeating itself.

### Tech stack

- **AI**: Gemini 2.5 Flash Native Audio via LiveKit RealtimeModel (persistent WebSocket, audio streamed in real time)
- **Frontend**: Tauri shell + vanilla TS (no React — startup-cost discipline) + WebSocket bus at 30 Hz feeding a Three.js mascot overlay
- **Backend**: Python 3.14 sidecar handling audio I/O, MIDI decode, event detection, screen capture
- **Bravoh proxy**: API key never ships in the binary; client talks to a Bravoh-managed proxy that rate-limits per-client and forwards to Gemini

### Honest caveats

- Mac + Windows only (Linux out of scope — loopback audio stack diverges enough that maintenance triples).
- The Bravoh-managed proxy means there's a server in the loop. The repo is Apache 2.0 and there's an env-var path to point at your own Gemini key if you'd rather BYO.
- Bravoh's main product is closed and Gemini-only. vibemix is Bravoh's first OSS release — the warm-up for the main launch.

### Repo

<TBD repo_url>

Demo: <TBD demo_youtube>

Inline (Beat A — amber overlay ring + grounded reaction):

![demo gif](<TBD demo_gif>)

### What I'd love feedback on

1. **Anti-slop gate design**. The `<silence/>` short-circuit is the most fragile part — happy to discuss alternatives.
2. **Controller library scope**. 10 SKUs out of the box, sniff tool for the rest. Should we curate more aggressively, or push community PRs?
3. **Bravoh-proxy vs BYO-key**. This was a real call — the proxy gives us per-client rate limit + an honest "your key never ships in the binary" story, at the cost of routing your audio through a third party. Curious how others have handled the API-key-in-distributed-binary problem.

Happy to answer questions on any of the above.

## Notes for Kaan

- Post mid-week (Tuesday/Wednesday) at ~9am EST for r/programming peak engagement.
- Stay in the comments for the first 2 hours — Reddit rewards active OP presence.
- Pre-warm with 3-5 honest comments from Bravoh team (acknowledge they're team if asked — don't fake organic).
- Cross-post to r/opensource at 24h delay only if the r/programming post lands.
