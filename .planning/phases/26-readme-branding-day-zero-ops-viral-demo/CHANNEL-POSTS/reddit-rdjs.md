---
channel: reddit
subreddits:
  - r/Beatmatch (primary)
  - r/DJs (secondary, ~12h delay, slightly adjusted body)
  - r/DJSetups (tertiary)
language: en
hero_beat: C (3 seconds of deliberate silence — "watch what it doesn't say")
media: 30s YouTube unlisted upload linked from body + 720x720 GIF inline
status: draft
tbd_markers:
  - <TBD repo_url> — GitHub repo URL
  - <TBD demo_youtube> — YouTube unlisted video URL
  - <TBD demo_gif> — 720x720 GIF for inline embed
anti_slop_thesis_position: title + first line of body
note: DJ community hates AI-generated commentary. Frame defensively first ("we built this because every other AI music tool sounds like a chatbot"), then show the silence beat as proof.
---

# Reddit r/Beatmatch + r/DJs — community launch

## Title (r/Beatmatch)

> Free open-source AI co-host that actually listens to your mix — and shuts up when it doesn't have anything to say

## Title (r/DJs — slight variant)

> Built a free AI co-host for live sets (Mac+Win) — the trick was getting it to stay silent

## Body (r/Beatmatch version)

Every AI tool I've tried for live mixing has the same problem: it sounds like a chatbot reading liner notes. Generic commentary, hallucinated track names, late reactions to moves you finished 15 seconds ago. Useless.

I'm a DJ. I wanted an actual co-host — like a friend on the couch behind me — that's grounded in what I'm actually doing.

So vibemix listens to three things at once:

- My master output (whatever's coming out of djay Pro / Serato / VirtualDJ)
- My DJ software's screen (so it knows which deck is loud, what BPM, where the markers are)
- My MIDI controller (every EQ knob, every filter sweep, every cue trigger)

It reacts in two modes:

- **Hype-man** during the set (party energy, present tense, kept brief)
- **Coach** after the cue (past-tense critique — "that cut was a beat off, try the downbeat next time")

And three skill levels (Beginner / Intermediate / Pro) with prompt vocabularies tuned to each.

### The thing I'm most proud of

It stays silent when it doesn't have anything to say. The whole anti-slop layer is built around the model emitting silence rather than generic AI commentary. Watch the last 5 seconds of the demo:

[demo: <TBD demo_youtube>]

That 3-second pause is on purpose. The model couldn't ground a reaction. It stayed quiet.

### Setup

- Free, Apache 2.0
- Mac (DMG) + Windows (MSI) signed binaries
- 10 controllers mapped out of the box: full Pioneer DDJ family (FLX4, FLX6, FLX10, 400, 1000, SX3), Pioneer XDJ-RX3, Numark Party Mix Live, Hercules Inpulse 300 + 500
- Don't see yours? There's a sniff tool that captures any controller's MIDI shape in 30 seconds, and a PR template for adding it to the library
- Tested on djay Pro 5 — Serato + VirtualDJ + Rekordbox support is planned

### Honest disclaimers

- Free for v1. The Gemini API cost is absorbed by Bravoh as part of our launch. Might revisit if usage scales — we'll announce before changing anything.
- Linux is not supported (the loopback audio stack is different enough that it triples our maintenance — sorry).
- This is the first OSS release from Bravoh, the AI artist platform. The main product (closed, paid) is unrelated to vibemix. vibemix is its own thing.

### Repo

<TBD repo_url>

### Question for the community

Which controllers should we add to the library next? Drop a comment with what you're running. The current 10 covers the biggest SKUs we could verify with the actual hardware in hand.

## Body adjustments for r/DJs

- Open with the "built this because every AI music tool sounds like a chatbot" line as the first sentence (r/DJs leans more cynical than r/Beatmatch).
- Drop the "Hype-man / Coach" mode breakdown into a TL;DR at the top — r/DJs prefers compact posts.
- Keep the silence-beat demo as the hero.

## Notes for Kaan

- Post r/Beatmatch first (more beginner-friendly audience, anti-slop framing resonates).
- 12h gap before r/DJs (DJ subreddit overlap is high — don't burn karma with same-day dupes).
- Stay in the comments. r/Beatmatch in particular rewards OP responsiveness.
- If anyone asks "why not Linux?" — be honest: "loopback stack maintenance, not philosophy."
