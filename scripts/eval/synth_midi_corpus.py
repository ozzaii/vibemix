# SPDX-License-Identifier: Apache-2.0
"""Synthesize a MIDI+nowplaying replay corpus from an audio-only recording.

The replay lane (``vibemix.platform._audio_replay``) already plays back a
``midi.jsonl`` tape (``ReplayMidiBackend._run_tape`` → ``ControllerState.
handle_msg``) and a ``nowplaying.jsonl`` script (``ReplayTrackBackend``) when
those files exist in the session dir — but every real capture in the corpus is
audio-only (no controller was attached, no nowplaying client). That leaves the
move-coaching axis (``move_grade_voice_line``, MIX_MOVE reactions) and the
track-identity register UNMEASURABLE by the bench loop: the judged friend
ceiling on an audio-only corpus is the energy-read register alone.

This tool builds a sibling corpus session that symlinks the original capture
(audio + metadata untouched) and adds a deterministic, humanly-plausible DJ
move script in the DDJ-FLX4 profile's CC space plus synthetic track
identities. The macOS MIDI backend constructs ``ControllerState`` with the
FLX4 profile statically (``_midi_macos.py``), and in replay mode the port
watcher is idle (no rebind), so FLX4-schema CCs decode semantically without
any port-name games.

CC values are 0..127. Ramps are emitted as multiple rows so the decoder sees
real move dynamics (magnitude labels like "killed"/"big twist" derive from
deltas, not single jumps).

Usage:
  python scripts/eval/synth_midi_corpus.py \
    --session "/path/to/recordings/20260603-112321" \
    --out /tmp/replay-corpus-midi
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# FLX4 profile bindings (mirrors src/vibemix/midi/profiles/pioneer_ddj_flx4.json;
# kept literal here so the generated tape is self-describing in review).
_CH_DECK_A = 0
_CH_DECK_B = 1
_CH_MIXER = 6
_CC_VOL = 19
_CC_EQ_HI = 7
_CC_EQ_MID = 11
_CC_EQ_LOW = 15
_CC_FILTER_A = 23
_CC_FILTER_B = 24
_CC_XFADER = 31

_TRACKS = [
    (0.0, "Synthcorp - Obsidian Drive", 312.0),
    (240.0, "Velvet Mirage - Neon Tide", 358.0),
    (436.0, "Iron Bloom - Static Garden", 295.0),
]


def _cc(ts: float, channel: int, control: int, value: int) -> dict:
    return {
        "ts": round(ts, 3),
        "type": "cc",
        "channel": channel,
        "data1": control,
        "data2": max(0, min(127, int(value))),
    }


def _ramp(
    rows: list[dict],
    *,
    t0: float,
    t1: float,
    channel: int,
    control: int,
    v0: int,
    v1: int,
    steps: int = 8,
) -> None:
    """Emit a linear CC ramp as discrete rows (inclusive of both endpoints)."""
    steps = max(2, steps)
    for i in range(steps):
        frac = i / (steps - 1)
        rows.append(
            _cc(t0 + (t1 - t0) * frac, channel, control, round(v0 + (v1 - v0) * frac))
        )


def build_move_script() -> list[dict]:
    """A plausible two-transition set script timed against the 444s corpus
    audio (PHASE landmarks measured from prior replays of 20260603-112321:
    peak ~58s, low ~162s, groove ~231s/292s, low ~428s, groove ~451s+)."""
    rows: list[dict] = []

    # Opening state: deck A live, deck B silent, xfader on A.
    rows.append(_cc(2.0, _CH_DECK_A, _CC_VOL, 110))
    rows.append(_cc(2.2, _CH_DECK_B, _CC_VOL, 0))
    rows.append(_cc(2.4, _CH_MIXER, _CC_XFADER, 18))

    # ~76s (post-peak): deck A low-EQ kill, hold through the phrase, restore.
    _ramp(rows, t0=76.0, t1=77.2, channel=_CH_DECK_A, control=_CC_EQ_LOW, v0=64, v1=6)
    _ramp(rows, t0=81.5, t1=82.4, channel=_CH_DECK_A, control=_CC_EQ_LOW, v0=6, v1=64, steps=6)

    # ~112s: filter sweep on A (bipolar around 64) riding into the breakdown.
    _ramp(rows, t0=110.0, t1=113.0, channel=_CH_MIXER, control=_CC_FILTER_A, v0=64, v1=104, steps=10)
    _ramp(rows, t0=113.0, t1=116.0, channel=_CH_MIXER, control=_CC_FILTER_A, v0=104, v1=64, steps=10)

    # ~225-245s: full transition A→B across the groove re-entry.
    _ramp(rows, t0=225.0, t1=235.0, channel=_CH_DECK_B, control=_CC_VOL, v0=0, v1=112, steps=12)
    _ramp(rows, t0=228.0, t1=236.0, channel=_CH_MIXER, control=_CC_XFADER, v0=18, v1=108, steps=10)
    _ramp(rows, t0=236.0, t1=244.0, channel=_CH_DECK_A, control=_CC_VOL, v0=110, v1=6, steps=10)
    # Bass swap: B lows in as A lows go.
    _ramp(rows, t0=233.0, t1=234.5, channel=_CH_DECK_A, control=_CC_EQ_LOW, v0=64, v1=10, steps=6)
    _ramp(rows, t0=233.5, t1=235.0, channel=_CH_DECK_B, control=_CC_EQ_LOW, v0=20, v1=64, steps=6)

    # ~300s: deck B mid dip + restore (carve space under the vocal).
    _ramp(rows, t0=300.0, t1=301.2, channel=_CH_DECK_B, control=_CC_EQ_MID, v0=64, v1=30, steps=6)
    _ramp(rows, t0=305.0, t1=306.0, channel=_CH_DECK_B, control=_CC_EQ_MID, v0=30, v1=64, steps=6)

    # ~362s: deck B brightness lift into the next phrase.
    _ramp(rows, t0=361.0, t1=363.0, channel=_CH_DECK_B, control=_CC_EQ_HI, v0=64, v1=92, steps=8)
    _ramp(rows, t0=366.0, t1=367.5, channel=_CH_DECK_B, control=_CC_EQ_HI, v0=92, v1=70, steps=6)

    # ~420-440s: transition back B→A over the low section.
    _ramp(rows, t0=420.0, t1=430.0, channel=_CH_DECK_A, control=_CC_VOL, v0=6, v1=108, steps=12)
    _ramp(rows, t0=424.0, t1=432.0, channel=_CH_MIXER, control=_CC_XFADER, v0=108, v1=20, steps=10)
    _ramp(rows, t0=432.0, t1=440.0, channel=_CH_DECK_B, control=_CC_VOL, v0=112, v1=4, steps=10)

    rows.sort(key=lambda r: r["ts"])
    return rows


def build_nowplaying_script() -> list[dict]:
    rows = []
    for ts, title, duration in _TRACKS:
        rows.append(
            {
                "ts": ts,
                "title": title,
                "duration_sec": duration,
                "position_sec": 0.0,
                "playback_rate": 1.0,
            }
        )
    return rows


def synthesize(session_dir: Path, out_root: Path, *, suffix: str = "FLX4") -> Path:
    session_dir = session_dir.expanduser().resolve()
    if not (session_dir / "input.wav").exists():
        raise SystemExit(f"not a replayable session (no input.wav): {session_dir}")
    out_session = out_root.expanduser() / f"{session_dir.name}-{suffix}"
    out_session.mkdir(parents=True, exist_ok=True)

    for entry in session_dir.iterdir():
        link = out_session / entry.name
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(entry)

    midi_rows = build_move_script()
    with (out_session / "midi.jsonl").open("w", encoding="utf-8") as fh:
        for row in midi_rows:
            fh.write(json.dumps(row) + "\n")

    np_rows = build_nowplaying_script()
    with (out_session / "nowplaying.jsonl").open("w", encoding="utf-8") as fh:
        for row in np_rows:
            fh.write(json.dumps(row) + "\n")

    print(f"-> synthesized corpus session: {out_session}")
    print(f"   midi.jsonl: {len(midi_rows)} rows | nowplaying.jsonl: {len(np_rows)} tracks")
    return out_session


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--suffix", default="FLX4")
    args = parser.parse_args()
    synthesize(args.session, args.out, suffix=args.suffix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
