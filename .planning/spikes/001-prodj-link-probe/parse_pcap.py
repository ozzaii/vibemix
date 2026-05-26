#!/usr/bin/env python3
"""Parse a tcpdump pcap of DJ-Link traffic (spike 001, capture path).

rekordbox holds UDP 50000-50002 on the local machine, so we can't bind those
ports here. Instead capture the wire with:

    sudo tcpdump -i en0 -w /tmp/djlink.pcap 'udp portrange 50000-50002'

(run ~30 s with a deck playing, Ctrl-C to stop) then:

    python3 parse_pcap.py /tmp/djlink.pcap

Pure stdlib: hand-parses the classic pcap container + Ethernet/IPv4/UDP, then
reuses the beat parser from probe.py. Answers the same question as the live
probe — does rekordbox give us BPM + beat-in-bar phase + pitch?
"""
from __future__ import annotations

import struct
import sys

from probe import MAGIC, TYPE_BEAT, device_name, hexdump, parse_beat

PCAP_MAGIC_LE = 0xA1B2C3D4
DLT_EN10MB = 1
DLT_NULL = 0     # loopback / null linktype (4-byte family header)
DLT_RAW = 12     # raw IP


def udp_payloads(path: str):
    """Yield (src_port, dst_port, payload) for every UDP datagram in the pcap."""
    with open(path, "rb") as f:
        gh = f.read(24)
        if len(gh) < 24:
            return
        magic = struct.unpack("<I", gh[:4])[0]
        le = magic == PCAP_MAGIC_LE
        endian = "<" if le else ">"
        linktype = struct.unpack(endian + "I", gh[20:24])[0]

        while True:
            rh = f.read(16)
            if len(rh) < 16:
                break
            _, _, incl, _ = struct.unpack(endian + "IIII", rh)
            data = f.read(incl)
            if len(data) < incl:
                break

            # strip link layer -> IP
            if linktype == DLT_EN10MB:
                if len(data) < 14:
                    continue
                ethertype = struct.unpack(">H", data[12:14])[0]
                if ethertype != 0x0800:  # IPv4 only
                    continue
                ip = data[14:]
            elif linktype == DLT_NULL:
                ip = data[4:]
            elif linktype == DLT_RAW:
                ip = data
            else:
                ip = data  # best effort

            if len(ip) < 20 or (ip[0] >> 4) != 4:
                continue
            ihl = (ip[0] & 0x0F) * 4
            if ip[9] != 17:  # protocol 17 = UDP
                continue
            udp = ip[ihl:]
            if len(udp) < 8:
                continue
            sport, dport, ulen, _ = struct.unpack(">HHHH", udp[:8])
            yield sport, dport, udp[8:ulen if ulen <= len(udp) else len(udp)]


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python3 parse_pcap.py <file.pcap>", file=sys.stderr)
        return 2
    path = sys.argv[1]

    beats = []
    devices = {}
    seen_types = set()
    n_dj = 0

    for sport, dport, payload in udp_payloads(path):
        if not payload.startswith(MAGIC):
            continue
        n_dj += 1
        ptype = payload[0x0A]
        if ptype not in seen_types:
            seen_types.add(ptype)
            print(f"\n=== first DJ-Link packet  dport={dport} type={ptype:#04x} len={len(payload)} ===")
            print(hexdump(payload))
            print()
        if ptype == TYPE_BEAT:
            b = parse_beat(payload)
            if b:
                beats.append(b)
                bar = "".join("●" if i + 1 == b["beat_in_bar"] else "·" for i in range(4))
                print(f"  {b['name'] or '?':<12} {b['bpm']:7.2f} BPM [{bar}] beat {b['beat_in_bar']}/4  pitch {b['pitch_pct']:+.2f}%")
        else:
            name = device_name(payload)
            if name and name not in devices:
                devices[name] = ptype
                print(f"[device] {name}  type={ptype:#04x}")

    print("\n--- SUMMARY ---")
    print(f"DJ-Link packets: {n_dj}")
    print(f"packet types:    {[hex(t) for t in sorted(seen_types)]}")
    print(f"devices:         {list(devices) or '(none)'}")
    print(f"beat packets:    {len(beats)}")
    if beats:
        bpms = [b["bpm"] for b in beats]
        bars = sorted({b["beat_in_bar"] for b in beats})
        pitches = sorted({b["pitch_pct"] for b in beats})
        print(f"bpm range:       {min(bpms):.2f}–{max(bpms):.2f}")
        print(f"beat-in-bar:     saw {bars}  ({'GOOD: full 1-4 phase' if bars == [1, 2, 3, 4] else 'partial — check fidelity'})")
        print(f"pitch values:    {pitches[:8]}{' ...' if len(pitches) > 8 else ''}")
    else:
        print("NO beat packets in capture. If devices appeared but no beats,")
        print("rekordbox may not broadcast beats with no CDJ/peer present —")
        print("then Ableton Link (spike 002) is the path for beat phase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
