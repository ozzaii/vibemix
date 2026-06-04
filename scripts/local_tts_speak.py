#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Speak one line through the local Chatterbox engine on real speakers.

A dry, deterministic proof that the on-device voice works — no LiveKit chain,
no heartbeat co-host, no cloud fallback. Reuses the production provider
(`ChatterboxLocalTTS`) + its engine seam; just collects PCM and plays it out.

Run (mlx-audio lives in the ai-local extra on Apple Silicon):
    uv run --extra ai-local python scripts/local_tts_speak.py
    uv run --extra ai-local python scripts/local_tts_speak.py \
        --text "that's the drop" --device "MacBook Pro Speakers"
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np
import sounddevice as sd

from vibemix.agent.chatterbox_tts import ChatterboxLocalTTS, resolve_ref_path


def _output_device_index(name_substr: str | None) -> int | None:
    """First output device whose name contains ``name_substr`` (case-insensitive)."""
    if not name_substr:
        return None
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0 and name_substr.lower() in dev["name"].lower():
            return i
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default="Yo — this is your local voice now. No keys, no cloud, running straight off your Mac. Let's ride.")
    ap.add_argument("--device", default="MacBook Pro Speakers")
    args = ap.parse_args()

    if resolve_ref_path() is None:
        print("Chatterbox reference clip missing; set VIBEMIX_CHATTERBOX_REF.", file=sys.stderr)
        return 2

    tts = ChatterboxLocalTTS()
    print("[chatterbox] loading engine", flush=True)
    t0 = time.perf_counter()
    engine = tts._get_engine()  # synchronous load (the path prewarm() backgrounds)
    print(
        f"[chatterbox] warm in {time.perf_counter() - t0:.1f}s "
        f"- native sr={engine.sample_rate}",
        flush=True,
    )

    chunks: list[bytes] = []
    first = {"t": None}
    t1 = time.perf_counter()

    def on_pcm(pcm: bytes) -> None:
        if first["t"] is None:
            first["t"] = time.perf_counter() - t1
        chunks.append(pcm)

    tts.synthesize_pcm(args.text, on_pcm)
    synth_dt = time.perf_counter() - t1

    sample_rate = tts.sample_rate
    audio = np.frombuffer(b"".join(chunks), dtype="<i2").astype(np.float32) / 32768.0
    dur = len(audio) / sample_rate if sample_rate else 0.0
    ttft_ms = (first["t"] or 0.0) * 1000.0
    rtf = synth_dt / dur if dur else float("nan")
    print(
        f"[chatterbox] TTFT {ttft_ms:.0f}ms - synth {synth_dt:.2f}s "
        f"- audio {dur:.2f}s - RTF {rtf:.2f}",
        flush=True,
    )

    dev = _output_device_index(args.device)
    print(f"[chatterbox] playing on device {dev} ({args.device}) - listen", flush=True)
    sd.play(audio, samplerate=sample_rate, device=dev)
    sd.wait()
    print("[chatterbox] done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
