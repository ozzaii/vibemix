# Spike Manifest

## Idea

Ingest **ground-truth live deck state** from the DJ software locally, instead of
inferring it. Today vibemix's co-host infers what the DJ is doing from MIDI moves
+ now-playing title + 6 s audio-autocorrelation BPM — a thin, guessy picture that
caps live-feedback quality (the AI "can't fully get into what the DJ is doing").
DJ software (rekordbox first) broadcasts on the LAN: PRO DJ LINK (loaded track id,
BPM, pitch, beat-in-bar phase) and Ableton Link (shared tempo + beat phase).
Reading those would turn inference into truth — and unlock beat-relative feedback.

## Findings (2026-05-26, Kaan's laptop-only rekordbox rig)

**The clean local-broadcast path to per-deck ground truth does NOT exist for a
laptop-only rekordbox setup.**

- **PRO DJ LINK** broadcasts nothing without Pioneer hardware on the LAN (0 of
  173k packets matched 50000-50002). It IS the right path **when CDJs/DJM are
  present** (club / serious-DJ market) — deferred to a hardware test, not dead.
- **Ableton Link** traffic flows and is easy to read, but rekordbox exposes only a
  single global tempo that's decoupled from the audible decks (saw 123.71 while
  decks played 160.53 / 120.00). No per-deck/track data. Useful only if the DJ
  Link-locks the master deck — not assumable.

→ **Pivot:** for laptop-only DJs (any software), the universal local "API" is what
the screen already renders — track title, BPM, key, pitch %, position, cues are
all on screen. `deck_vision.py` (Gemini screen read) already exists but is gated
off (`vision_enabled=False`). Re-evaluating that path is spike 003 (proposed).

## Requirements

- Passive-first: no packet injection onto a live DJ network until passive signal
  is confirmed.
- Ground-truth must carry per-deck state (loaded track + audible/pitched BPM +
  beat phase), not just a global tempo.
- macOS first (Kaan's rig: arm64, rekordbox). Pure-stdlib probes where possible.
- Cannot assume Pioneer hardware on the LAN; cannot assume the DJ changes workflow
  (e.g. Link-locking decks).

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | prodj-link-probe | standard | UDP 50000-50002 → BPM + beat-in-bar + pitch ground truth | INVALIDATED laptop-only / CONDITIONAL on hardware | prodj-link, beat-phase |
| 002 | ableton-link-probe | standard | Link → tempo + beat phase tracking the audible mix | PARTIAL (flows, but decoupled single tempo, no per-deck) | ableton-link, beat-phase |
| 003 | deck-vision-revisit | standard | Screen read (existing `deck_vision.py`) → per-deck title/BPM/key/pitch, any software | TODO (proposed) | vision, universal, laptop-only |
