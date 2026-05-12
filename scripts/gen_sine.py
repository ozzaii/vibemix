"""Generates tauri/ui/public/audio/sine-1khz-1500ms.wav.

Spec (per .planning/phases/11-tauri-shell-calibration-wizard/11-UI-SPEC.md
§Asset Pipeline): 48 kHz mono int16, 1.5 s duration, -6 dBFS peak, 100 ms
fade-in / fade-out.

Used by Step 2 (Output Device) of the calibration wizard: the audible 1 kHz
test tone proves the user's headphones + BlackHole + macOS output path is
audible. Programmatic guard runs in parallel via sounddevice.

Reproducible build-time artifact — run once, commit the resulting WAV so
executors don't need numpy on the build host. Re-run only when the spec
changes (and update the SHA-256 in tauri/ui/LICENSE-3RD-PARTY.md).
"""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


SAMPLE_RATE = 48000
DURATION_S = 1.5
FREQ_HZ = 1000.0
PEAK_DBFS = -6.0
FADE_MS = 100


def main() -> int:
    n = int(SAMPLE_RATE * DURATION_S)
    t = np.arange(n) / SAMPLE_RATE
    peak = 10 ** (PEAK_DBFS / 20.0)
    sine = peak * np.sin(2 * np.pi * FREQ_HZ * t)
    f = int(SAMPLE_RATE * FADE_MS / 1000)
    sine[:f] *= np.linspace(0, 1, f)
    sine[-f:] *= np.linspace(1, 0, f)
    int16 = (sine * 32767).astype(np.int16)
    out = Path("tauri/ui/public/audio/sine-1khz-1500ms.wav")
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(int16.tobytes())
    print(f"wrote {out} ({n} samples, {DURATION_S}s, {SAMPLE_RATE} Hz)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
