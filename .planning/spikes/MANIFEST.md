# Spike Manifest

## Idea

Ingest **ground-truth live deck state** from the DJ software locally, instead of
inferring it. Today vibemix's co-host infers what the DJ is doing from MIDI moves
+ now-playing title + 6 s audio-autocorrelation BPM — a thin, guessy picture that
caps live-feedback quality (the AI "can't fully get into what the DJ is doing").
DJ software (rekordbox first) actually broadcasts far more on the LAN: PRO DJ LINK
(loaded track id, BPM, pitch, beat-in-bar phase) and Ableton Link (shared tempo +
beat phase). Reading those turns inference into truth — and unlocks beat-relative
feedback ("you cut the fader off-beat", "you came in on the downbeat, in key").

## Requirements

- Passive-first: probes must not inject packets onto a live DJ network until the
  passive signal is confirmed (a wrong virtual-CDJ announce can disturb real CDJs).
- Ground-truth must carry **beat phase** (beat-in-bar), not just tempo — that's
  the load-bearing field for beat-relative feedback.
- macOS first (Kaan's rig: arm64, rekordbox). Pure-stdlib probes where possible.

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | prodj-link-probe | standard | Passive UDP 50000+50001 → BPM + beat-in-bar + pitch ground truth | PENDING (built, awaiting live capture) | ingest, prodj-link, beat-phase |
| 002 | ableton-link-probe | standard | Join as passive Link peer → tempo + beat phase, cross-app | TODO | ingest, ableton-link, beat-phase |
