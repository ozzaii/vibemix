---
spike: 001
name: prodj-link-probe
type: standard
validates: "Given rekordbox broadcasting on the LAN, when we listen passively on UDP 50000+50001, then we decode loaded-deck BPM + beat-in-bar phase + pitch as ground truth"
verdict: PENDING
related: []
tags: [ingest, prodj-link, ground-truth, beat-phase, rekordbox]
---

# Spike 001: PRO DJ LINK passive probe

## What This Validates

Given rekordbox open and broadcasting PRO DJ LINK on the LAN, when we bind UDP
50000 (announce) + 50001 (beats) passively, then we receive beat packets
carrying **real BPM, beat-in-bar (1-4) phase, and pitch fader %** — ground
truth, not the audio-autocorrelation guess the live co-host uses today.

This is the inference-ceiling fix: the AI currently infers deck state from MIDI
moves + now-playing title + 6 s BPM autocorrelation. If this data flows, we can
give **beat-relative** feedback ("you cut the fader off-beat") instead of vague
commentary.

## Research

Protocol = Pioneer PRO DJ LINK, reverse-engineered by Deep Symmetry (dysentery /
beat-link). Every packet starts with magic `Qspt1WmJOL`; byte `0x0a` = type.

| Port | Carries | Needs us to inject? |
|------|---------|---------------------|
| 50000 | device announce / keep-alive (who's on the net) | no — passive |
| 50001 | **beat packets** (BPM, beat-in-bar, pitch), one per beat | no — passive |
| 50002 | rich status (loaded track id, play/cue state, on-air) | **yes** — must announce as a virtual CDJ |

Beat packet offsets used (will be eyeballed against the first real hexdump):
`0x21` device#, `0x54` pitch (uint32 BE, `0x100000`=100%), `0x5a` BPM (uint16 BE
÷100), `0x5c` beat-in-bar 1-4.

Known caveats to test against real data:
- Laptop-only rekordbox advertises as device ~11 with a limited status flag
  (`c0` = "always playing", on-air/master not reliable). Beat packets should
  still carry BPM + beat-in-bar; **that's the load-bearing question**.
- rekordbox emits PRO DJ LINK in **EXPORT mode** (LINK button), not necessarily
  PERFORMANCE — confirm which mode actually broadcasts.
- The Mac must share a broadcast domain with the rig (same Wi-Fi/LAN, no AP
  client-isolation). Loopback-only won't see broadcasts.

Chosen approach: **passive listen first** (zero network injection → cannot
disturb a live set). Virtual-CDJ announce for port 50002 track-id = iteration 2,
only after passive beat data is confirmed.

Refs: <https://djl-analysis.deepsymmetry.org/djl-analysis/beats.html> ·
<https://github.com/Deep-Symmetry/dysentery> ·
<https://github.com/flesniak/python-prodj-link>

## How to Run

1. Open **rekordbox**, load a track on a deck, hit play.
2. Enable PRO DJ LINK (the **LINK** button / EXPORT mode). If you have CDJs on
   the LAN, even better — power them on.
3. Make sure this Mac is on the **same LAN** as the rig.
4. Run:
   ```bash
   python3 probe.py            # live readout, Ctrl-C to stop
   python3 probe.py --seconds 30
   ```

## What to Expect

A live line like:
```
  rekordbox     128.00 BPM [··●·] beat 3/4  pitch +0.00%  (#412)
```
and on the first packet of each type, a hexdump (to verify offsets). On exit, a
SUMMARY with beat count/sec, BPM range, and which beat-in-bar values appeared
(want the full `[1,2,3,4]`). Forensic log → `probe-log.jsonl`.

## Observability

Every beat + device event is appended to `probe-log.jsonl` (ISO-timestamped),
plus first-of-type hexdumps to stdout, plus an exit summary with derived stats.

## Investigation Trail

- **Built v1** — passive UDP listener on 50000+50001, pure stdlib (no pip dep),
  full beat parse + first-of-type hexdump + forensic JSONL. Smoke-tested with no
  rekordbox: binds clean, summary path works, 0 packets as expected.
- **NEXT (needs Kaan):** run with rekordbox broadcasting → confirm beat packets
  arrive and beat-in-bar cycles 1→4. Then decide on iteration 2 (port 50002
  virtual-CDJ announce for loaded track id).

## Results

PENDING — awaiting a live capture against Kaan's rekordbox.
