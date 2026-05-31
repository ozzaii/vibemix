# SPDX-License-Identifier: Apache-2.0
"""Manual smoke test: HEAR the MiniDeck engine on real hardware.

Not a unit test (CI has no audio device) — a hands-on proof that the numpy
resampler + equal-power crossfade ported from Mixxx actually make correct
sound. Synthesizes two pure tones onto the two owned decks and, over ~7
seconds, audibly demonstrates both ported scars:

  0.0-1.5s  deck A only (220 Hz), rate 1.0      -> baseline tone
  1.5-3.5s  deck A rate ramps 1.0 -> 0.5        -> octave pitch DROP (resampler works)
  3.5-6.0s  xfader sweeps A -> B (330 Hz)       -> equal-power crossfade, no loudness dip
  6.0-7.0s  deck B only

Routes to the system default output (Mac speakers / Mac headphone jack) unless
``--device <name-substring>`` is given. The mix is fanned across every output
channel pair, so multi-channel interfaces (e.g. the FLX4 master) also play it.

Run:
    uv run python scripts/miniplayer_smoke.py --device "MacBook Pro Speakers"
    uv run python scripts/miniplayer_smoke.py                       # system default
"""

from __future__ import annotations

import argparse
import time

import numpy as np

from vibemix.audio.miniplayer import MiniDeck

SR = 44_100


def _tone(freq_hz: float, *, seconds: float, amplitude: float = 0.2) -> np.ndarray:
    """A stereo ``(N, 2)`` float32 sine slab — a known oracle the ear can verify."""
    n = int(seconds * SR)
    t = np.arange(n, dtype=np.float64) / SR
    wave = (amplitude * np.sin(2.0 * np.pi * freq_hz * t)).astype(np.float32)
    return np.stack([wave, wave], axis=1)


def _resolve_device(name_hint: str | None) -> tuple[int | None, int]:
    """Return ``(device_index, output_channels)`` — matched device, else default."""
    import sounddevice as sd

    if name_hint is not None:
        for i, dev in enumerate(sd.query_devices()):
            if name_hint.lower() in dev["name"].lower() and dev["max_output_channels"] > 0:
                return i, int(dev["max_output_channels"])
    default = sd.query_devices(kind="output")  # system default output
    return None, min(2, int(default["max_output_channels"]) or 2)


def _automate(deck: MiniDeck, t: float) -> None:
    """Stage the two-scar demo by driving xfader/rate over wall-clock.

    Plain attribute writes from the main thread while the audio callback reads
    them — fine for a smoke test (CPython float assignment is atomic); the real
    practice flow snapshots under a lock.
    """
    if t < 1.5:
        deck.rate_a, deck.xfader = 1.0, 0.0
    elif t < 3.5:
        frac = (t - 1.5) / 2.0  # 0 -> 1 across the window
        deck.rate_a, deck.xfader = 1.0 - 0.5 * frac, 0.0  # 1.0 -> 0.5 = octave drop
    elif t < 6.0:
        frac = (t - 3.5) / 2.5
        deck.rate_a, deck.xfader = 0.5, frac  # sweep A -> B
    else:
        deck.xfader = 1.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=None, help="output device name substring")
    parser.add_argument("--seconds", type=float, default=7.0)
    args = parser.parse_args()

    import sounddevice as sd

    device, out_channels = _resolve_device(args.device)
    info = sd.query_devices(device) if device is not None else sd.query_devices(kind="output")
    print(f"-> output: {info['name']} ({out_channels} ch) @ {SR} Hz")
    print("-> A=220Hz B=330Hz | 0-1.5s A | 1.5-3.5s octave-drop | 3.5-6s crossfade | 6-7s B")

    deck = MiniDeck(
        _tone(220.0, seconds=12.0),
        _tone(330.0, seconds=12.0),
        rate_a=1.0,
        rate_b=1.0,
        xfader=0.0,
    )

    def _callback(outdata, frames, time_info, status):  # runs on the OS audio thread
        if status:
            print(f"   [stream status] {status}")
        mix = deck.render_block(frames)  # (frames, 2)
        outdata.fill(0.0)
        nch = outdata.shape[1]
        for c in range(0, nch, 2):  # fan stereo across every output pair
            outdata[:, c] = mix[:, 0]
            if c + 1 < nch:
                outdata[:, c + 1] = mix[:, 1]

    stream = sd.OutputStream(
        device=device,
        samplerate=SR,
        channels=out_channels,
        dtype="float32",
        blocksize=512,
        callback=_callback,
    )
    with stream:
        start = time.monotonic()
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= args.seconds:
                break
            _automate(deck, elapsed)
            time.sleep(0.02)
    print("-> done.")


if __name__ == "__main__":
    main()
