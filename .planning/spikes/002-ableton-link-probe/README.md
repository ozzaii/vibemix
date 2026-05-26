---
spike: 002
name: ableton-link-probe
type: standard
validates: "Given rekordbox with Ableton Link on, when we observe Link traffic, then we get a usable shared tempo + beat phase that tracks the audible mix"
verdict: PARTIAL
related: [001]
tags: [ingest, ableton-link, beat-phase, rekordbox]
---

# Spike 002: Ableton Link probe

## What This Validates

Given rekordbox with Ableton Link enabled, when we join/observe the Link session,
then we receive a shared tempo + beat-phase timeline usable as a ground-truth beat
clock for beat-relative feedback.

## Research

Ableton Link = LAN clock-sync, UDP multicast on `224.76.78.75:20808`. Designed for
**many peers on one machine** (Live + apps), so unlike PRO DJ LINK it uses
reuse-friendly sockets — a vibemix peer can co-exist without stealing ports or
needing sudo. Python binding: `aalink` / `LinkPython-extern` (C++ core, builds via
cmake — present on this Mac). The wire protocol (ALPC) is custom binary; full
tempo/phase decode realistically needs the Link lib, not hand-parsing.

## How to Run (capture used)

```bash
sudo tcpdump -i en0 -c 20 -nn 'udp port 20808'
```
(Full decode would require building `aalink` and joining as a peer — deferred,
see Results.)

## Investigation Trail

- Confirmed via tcpdump that Link traffic flows the moment rekordbox Link is on.
- Read the rekordbox UI state alongside the capture (screenshot) to check whether
  the broadcast tempo reflects the *audible* mix. It does not — see Results.

## Results

**PARTIAL — traffic flows and is trivially observable, but the semantic value is
low for a manually-mixing DJ.**

Live evidence (2026-05-26, Kaan's rig):
- Link traffic confirmed: `192.168.1.46.57554 > 224.76.78.75.20808 UDP len 107`
  every ~250 ms (~4 Hz). Joinable, no sudo, no port contention.
- **But the shared tempo is decoupled from the audible mix.** The Ableton Link
  window showed master tempo **123.71** while deck A played at **160.53 BPM**
  (DATSKO, native 158, +1.6% pitch) and deck B at **120.00** (AZYR, native 165.8,
  −27.6%). The decks' per-deck LINK buttons were off, so Link broadcast an idle
  master tempo unrelated to anything playing.
- rekordbox's Link only ever exposes **one global tempo**, never per-deck BPM /
  loaded track / play state. And a DJ beat-matching by hand won't Link-lock decks
  (it would override their pitch faders and defeat manual mixing).

So Link is only a useful clock **if the DJ opts into Link-locking the master
deck** — a workflow change we can't assume. As a passive ground-truth source for
"what the DJ is doing right now," it does not deliver per-deck/track data and its
tempo can be meaningless. Useful at best as an *optional* precise beat-phase
source for DJs who already run Link-locked; not a general solution.

**Not built:** the `aalink` peer (would only confirm we can read the same single
tempo we already saw decoupled — low marginal value given the semantic gap).
