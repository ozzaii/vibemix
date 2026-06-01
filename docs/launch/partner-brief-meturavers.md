# vibemix — One-Page Brief

**The only AI co-host that actually listens to your set.**

vibemix runs locally on a DJ's Mac or PC, listens to the master output, watches the DJ software, reads the MIDI controller, and talks back into the headphones — as a hype-man or a coach — grounded in what the DJ actually just did. Not generic commentary. Not hallucinated track names. Not late reactions.

Apache-licensed client with a Bravoh-managed hosted service. macOS distribution is gated on producing and verifying a signed/notarized DMG; Windows targets v0.1.0 stable.

---

## What it does today

- **Live co-host** — 6 voice modes (3 skill levels × hype/coach), 10 controllers mapped out of the box, app-agnostic across rekordbox / Serato / Traktor / djay Pro / VirtualDJ / Mixxx via audio + screen + MIDI grounding.
- **Vibe Library** — local CLAP-based search across the DJ's own collection ("find me something darker"). 100% on-device, no cloud upload.
- **Set Builder (Viber)** — describe the set, get a sequenced harmonic path with every transition explained, exported straight to Rekordbox XML.
- **Beginner Module (v9.0, in build)** — interactive teaching mode. The user's actual controller renders on screen, the AI highlights the next control to touch, library tracks demonstrate every concept. 36 lessons across 3 courses.

## The moat

Every reaction is cited against real evidence — the audio chunk, the MIDI move, the on-screen track, the cue point in the file. Un-cited commentary is stripped before it leaves the model. That anti-slop discipline is structural, not prompt-engineered, and it is the reason DJs keep vibemix open instead of trying it once and closing it.

## Built by [Bravoh](https://bravoh.ai)

Bravoh is the AI creative team for music artists — currently in closed beta. vibemix is Bravoh's DJ co-host product: the live utility that earns the trust of the DJ community.

## Where Meturavers fits

To be discussed under NDA. Natural shapes of collaboration:

- Curriculum / teaching surface for the Beginner Module
- Controller / hardware co-branding around v9.0
- Community + distribution into the DJ space
- Something else entirely — open to it

---

**Contact** · Kaan Özkan, co-founder · kaan@bravoh.ai
**Repository** · github.com/bravoh-ai/vibemix
**Full capabilities brief** · `vibemix-capabilities.pdf` (attached separately)
