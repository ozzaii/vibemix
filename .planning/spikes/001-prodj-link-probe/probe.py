#!/usr/bin/env python3
"""PRO DJ LINK passive probe (spike 001).

THROWAWAY. Listens for the broadcasts rekordbox / CDJs emit on the LAN and
dumps exactly what fields arrive — to answer: does laptop-only rekordbox give
us usable ground-truth deck state (BPM, beat-in-bar phase, pitch)?

Passive only: binds UDP 50000 (device announce) + 50001 (beat packets).
It does NOT inject any packets onto the network, so it cannot disturb a live
rig. The richer status stream (port 50002: loaded track id, play state) needs
us to announce as a virtual CDJ — deferred to iteration 2 (see README).

Run with rekordbox open:
    python3 probe.py                 # passive listen, live readout
    python3 probe.py --seconds 30    # auto-stop after 30s
Ctrl-C to stop. A forensic JSONL log + summary are written on exit.

Protocol offsets from Deep Symmetry's dysentery analysis:
  https://djl-analysis.deepsymmetry.org/djl-analysis/beats.html
"""
from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time
from datetime import datetime, timezone

MAGIC = b"Qspt1WmJOL"  # every DJ-Link packet starts with these 10 bytes

PORT_ANNOUNCE = 50000  # device keep-alive / "I exist" broadcasts
PORT_BEAT = 50001      # beat packets — one per beat, carries BPM + beat-in-bar

# packet type byte (index 0x0a)
TYPE_BEAT = 0x28
TYPE_KEEPALIVE = 0x06  # one of several announce subtypes; we hexdump the rest

# beat-packet field offsets (these are what the spike is *testing*, so we also
# hexdump the first beat packet to eyeball them against real bytes)
OFF_DEVICE_NUM = 0x21   # player number (1-4 CDJ, 33 mixer, other = rekordbox)
OFF_PITCH = 0x54        # uint32 BE, 0x100000 == 100% (no tempo change)
OFF_BPM = 0x5a          # uint16 BE, value / 100 == track BPM
OFF_BEAT_IN_BAR = 0x5c  # 1..4 — THE phase signal
PITCH_BASE = 0x100000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def device_name(pkt: bytes) -> str:
    raw = pkt[0x0B:0x1F]
    return raw.split(b"\x00")[0].decode("ascii", "replace").strip()


def parse_beat(pkt: bytes) -> dict | None:
    if len(pkt) < OFF_BEAT_IN_BAR + 1:
        return None
    pitch_raw = struct.unpack_from(">I", pkt, OFF_PITCH)[0]
    bpm_raw = struct.unpack_from(">H", pkt, OFF_BPM)[0]
    return {
        "device": pkt[OFF_DEVICE_NUM],
        "name": device_name(pkt),
        "bpm": bpm_raw / 100.0,
        "beat_in_bar": pkt[OFF_BEAT_IN_BAR],
        "pitch_pct": round((pitch_raw - PITCH_BASE) / PITCH_BASE * 100.0, 3),
        "len": len(pkt),
    }


def hexdump(pkt: bytes, width: int = 16) -> str:
    out = []
    for i in range(0, len(pkt), width):
        chunk = pkt[i : i + width]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        out.append(f"  {i:#06x}  {hexs}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=0, help="auto-stop after N seconds (0 = until Ctrl-C)")
    ap.add_argument("--log", default="probe-log.jsonl")
    args = ap.parse_args()

    socks = {}
    for port in (PORT_ANNOUNCE, PORT_BEAT):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # rekordbox itself holds 50000-50002 when PRO DJ LINK is on. On macOS,
        # SO_REUSEPORT lets us co-bind; broadcast/multicast packets are delivered
        # to *all* sockets in the reuseport group, so we listen without stealing
        # them from rekordbox (unicast would load-balance — beats are broadcast).
        if hasattr(socket, "SO_REUSEPORT"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        try:
            s.bind(("0.0.0.0", port))
        except OSError as e:
            print(f"[!] could not bind UDP {port}: {e}", file=sys.stderr)
            print("    (is rekordbox or another DJ-Link tool already holding it?)", file=sys.stderr)
            return 2
        s.setblocking(False)
        socks[port] = s

    print(f"-> listening on UDP {PORT_ANNOUNCE} (announce) + {PORT_BEAT} (beats)")
    print("-> open rekordbox; enable PRO DJ LINK / put a deck playing. Ctrl-C to stop.\n")

    log = open(args.log, "w")
    events = []
    seen_types: dict[int, bool] = {}     # first-of-each-type hexdump guard
    seen_devices: dict[str, dict] = {}   # who's on the net
    beat_count = 0
    started = time.time()

    def record(ev: dict) -> None:
        ev["t"] = now_iso()
        events.append(ev)
        log.write(json.dumps(ev) + "\n")
        log.flush()

    try:
        import select

        while True:
            if args.seconds and (time.time() - started) >= args.seconds:
                break
            ready, _, _ = select.select(list(socks.values()), [], [], 0.5)
            for s in ready:
                try:
                    data, addr = s.recvfrom(2048)
                except BlockingIOError:
                    continue
                if not data.startswith(MAGIC):
                    continue
                ptype = data[0x0A]
                port = s.getsockname()[1]

                # hexdump the first packet of each (port,type) so we can verify
                # the offsets against ground truth, not trust them blindly.
                key = ptype
                if key not in seen_types:
                    seen_types[key] = True
                    print(f"\n=== first packet  port={port} type={ptype:#04x} len={len(data)} from={addr[0]} ===")
                    print(hexdump(data))
                    print()

                if port == PORT_BEAT and ptype == TYPE_BEAT:
                    b = parse_beat(data)
                    if b:
                        beat_count += 1
                        record({"kind": "beat", "src": addr[0], **b})
                        bar = "".join("●" if i + 1 == b["beat_in_bar"] else "·" for i in range(4))
                        sys.stdout.write(
                            f"\r  {b['name'] or '?':<12} {b['bpm']:7.2f} BPM "
                            f"[{bar}] beat {b['beat_in_bar']}/4  pitch {b['pitch_pct']:+.2f}%  "
                            f"(#{beat_count})   "
                        )
                        sys.stdout.flush()
                else:
                    name = device_name(data)
                    if name and name not in seen_devices:
                        seen_devices[name] = {"src": addr[0], "dev": data[OFF_DEVICE_NUM] if len(data) > OFF_DEVICE_NUM else None}
                        record({"kind": "device", "name": name, "src": addr[0], "ptype": ptype})
                        print(f"\n[device seen] {name}  ip={addr[0]}  type={ptype:#04x}")
    except KeyboardInterrupt:
        pass
    finally:
        log.close()
        for s in socks.values():
            s.close()

    dur = time.time() - started
    print("\n\n--- SUMMARY ---")
    print(f"duration:      {dur:.1f}s")
    print(f"beat packets:  {beat_count}  ({beat_count / dur:.1f}/s)" if dur else f"beat packets: {beat_count}")
    print(f"devices seen:  {list(seen_devices.keys()) or '(none)'}")
    print(f"packet types:  {[hex(t) for t in sorted(seen_types)]}")
    if beat_count:
        bpms = [e["bpm"] for e in events if e["kind"] == "beat"]
        bars = sorted({e["beat_in_bar"] for e in events if e["kind"] == "beat"})
        print(f"bpm range:     {min(bpms):.2f}–{max(bpms):.2f}")
        print(f"beat-in-bar:   saw values {bars}  ({'GOOD: full 1-4 phase' if bars == [1,2,3,4] else 'partial — check fidelity'})")
    else:
        print("NO BEAT PACKETS. Either rekordbox PRO DJ LINK is off, no deck is")
        print("playing, or this Mac isn't on the same broadcast domain as the rig.")
    print(f"\nforensic log: {args.log}  ({len(events)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
