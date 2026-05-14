#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""tune_detectors.py — Phase 17 reference-WAV detector tuning harness (SENSE-16).

Reads one or more reference WAV files, drives them through the FULL Phase 17
detector pipeline (``GenreRouter`` + baseline ``EventDetector`` + 6 Wave-2
detectors), and emits a per-fire CSV consumable by Kaan's Phase 16 ear-audit:

    python scripts/tune_detectors.py track1.wav [track2.wav ...] --csv out.csv

CSV schema (CONTEXT D-locked — Plan 17-06):
    track, t_seconds, bar_index, detector_name, score, threshold, fired

Purpose: Phase 16 (Hallucination Verification Gate) needs a feedback loop —
Kaan plays a real DJ session, hears a misfire, wants to know "what did the
detector think it heard". This harness lets him replay any track through the
same detector chain in a deterministic, offline way and compare CSV → ear
truth. It's also the regression net: when Plan 17-02-04 thresholds get tuned,
the same WAV → same CSV proves the change.

KAAN-ACTION (STATE.md outstanding to-do):
    "Collect Hard Tek + 9 SKU reference tracks for P17 detector tuning
     harness. Hard Tek 7-10 anchor tracks especially — Kaan-owned."

Anchor tracks expected at (Kaan-supplied):
    .planning/phases/17-hard-tek-detectors-v1-genrerouter-musicstate-extension/anchor_tracks/

Architecture:
    - Imports detector classes via the public package surface
      (``from vibemix.state import EventDetector, GenreRouter, MusicState``,
      ``from vibemix.state.refresh import _tick_once``,
      ``from vibemix.audio.buffers import AudioBuffer``,
      ``from vibemix.state.detectors._phrase_dsp import lock_downbeat_phase``)
      — exercises the same import surface a community contributor would use
      to build their own harness variant.
    - Drives the SYNCHRONOUS ``_tick_once`` (NOT the asyncio
      ``state_refresh_loop``) — this is a pure offline harness; no
      sounddevice / LiveKit / Tauri / asyncio runtime.
    - Tick cadence is 100ms per simulated step (matches the live runtime's
      ``state_refresh_loop`` cadence — keeps detector behaviour comparable).
    - Synthetic time is INJECTED via a single-source ``_clock`` callable that
      replaces ``time.time`` inside ``vibemix.state.event_detector`` for the
      duration of the run. EventDetector's internal cooldowns + chain
      detectors' baseline-window math both consume the synthetic clock so
      a 16s WAV takes 16s of "synthetic" detector time, NOT 1.6s of real
      wall clock. Without this the trailing-window detectors (KILL with
      8s baseline, etc.) would never observe their windows aging.

Anti-patterns (do NOT regress these):
    - DO NOT touch any cohost_*.py POC file (per CLAUDE.md "POC =
      reference, devour it"). Port-from only.
    - DO NOT call the asyncio ``state_refresh_loop`` — call ``_tick_once``.
    - DO NOT instantiate sounddevice / LiveKit / Tauri.
    - DO NOT silently degrade if anchor tracks are missing — log loud,
      exit 2 (UNIX usage-error convention).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import sys
import time as _wall_time
import wave
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
from scipy.signal import resample_poly

from vibemix.audio.buffers import AudioBuffer
from vibemix.audio.constants import (
    INPUT_SR_TARGET,
    KICK_KILL_SUB_DROP_MIN,
    KICK_REENTRY_BAR_TOLERANCE,
    KICK_SWAP_CENTROID_DELTA_HZ,
    PHRASE_BOUNDARY_BAR_TOLERANCE,
    SUB_JUMP_THRESHOLD,
)
from vibemix.state import EventDetector, GenreRouter, MusicState  # noqa: F401  (GenreRouter is reexported public surface)
from vibemix.state.refresh import _tick_once

logger = logging.getLogger(__name__)

# Per-detector "threshold" lookup for the CSV `threshold` column. Best-effort
# semantic — for compound detectors (multi-gate) the most representative
# single threshold is logged. Plan 17-06 first-feedback-pass may extend this
# table per CONTEXT D's "threshold-as-evidence" intent.
_DETECTOR_THRESHOLDS: dict[str, float] = {
    "KICK_SWAP": KICK_SWAP_CENTROID_DELTA_HZ,
    "SUB_LAYER_ARRIVAL": SUB_JUMP_THRESHOLD,
    "BREAKDOWN_KICK_KILL": KICK_KILL_SUB_DROP_MIN,
    "REENTRY_KICK_LAND": KICK_REENTRY_BAR_TOLERANCE,
    "PHRASE_BOUNDARY": PHRASE_BOUNDARY_BAR_TOLERANCE,
    # KICK_DENSITY_SHIFT, baseline events (TRACK_CHANGE/PHASE/LAYER_ARRIVAL/
    # MIX_MOVE/HEARTBEAT) — best-effort 0.0 placeholder; the per-fire `score`
    # column carries the actual evidence payload.
}

# 100ms tick — matches state_refresh_loop cadence so detector behaviour is
# comparable to live runtime. WAV is walked in `_TICK_HOP_SAMPLES` chunks at
# 16kHz target rate.
_TICK_HOP_SECONDS: float = 0.1
_TICK_HOP_SAMPLES: int = int(_TICK_HOP_SECONDS * INPUT_SR_TARGET)  # 1600


@dataclass
class _ControllerStateStub:
    """Stub matching ``vibemix.midi.state.ControllerState`` public surface
    (``deck_snapshot()`` + ``moves_since(t)``). No MIDI input in offline mode.
    """

    def deck_snapshot(self) -> dict:
        return {"A": {}, "B": {}, "xfader": 64, "connected": False}

    def moves_since(self, t: float) -> list[tuple[float, str]]:  # noqa: ARG002
        return []


@dataclass
class _TrackInfoStub:
    """Stub matching ``vibemix.platform._track_macos.TrackInfo.snapshot()``.

    No nowplaying-cli poll in offline mode — title is None so the audible-
    track resolver won't fabricate a TRACK_CHANGE event mid-WAV.
    """

    def snapshot(self) -> dict:
        return {"title": None, "prev_title": None, "title_changed_at": 0.0}


def _read_wav_to_int16_16k(path: Path) -> np.ndarray:
    """Read a WAV file and return int16 mono samples at INPUT_SR_TARGET (16kHz).

    - Decodes via stdlib ``wave`` (no soundfile dep — see CLAUDE.md tech-stack).
    - Mixes stereo → mono by averaging channels.
    - Resamples to 16kHz via ``scipy.signal.resample_poly`` (project dep).
    """
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sampwidth == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        # int32 PCM (rare but supported). Normalise to ±1.0.
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sampwidth == 1:
        # uint8 PCM (8-bit). Normalise to ±1.0.
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported sampwidth {sampwidth} (bytes/sample) in {path}")

    if n_channels > 1:
        # De-interleave + average to mono.
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    if sr != INPUT_SR_TARGET:
        # resample_poly with up=target / gcd, down=src / gcd.
        from math import gcd

        g = gcd(sr, INPUT_SR_TARGET)
        up = INPUT_SR_TARGET // g
        down = sr // g
        samples = resample_poly(samples, up=up, down=down).astype(np.float32)

    # Convert back to int16 for AudioBuffer.push (which expects int16).
    return (np.clip(samples, -1.0, 1.0) * 32767.0).astype(np.int16)


def _process_wav(
    wav_path: Path,
    *,
    bpm_override: float | None,
    genre_override: str | None,
    csv_writer: csv.writer,  # type: ignore[type-arg]
) -> int:
    """Walk a single WAV through the full detector pipeline; write per-fire
    rows to ``csv_writer``. Returns the number of rows written.

    Synthetic time starts at 0.0 and advances by ``_TICK_HOP_SECONDS`` per
    simulated tick. The wall-clock ``time.time`` is monkeypatched inside
    ``vibemix.state.event_detector`` so EventDetector's cooldown gates +
    chain detectors' baseline-window math both consume the synthetic clock.
    """
    rows_written = 0
    track_basename = wav_path.name

    samples_int16 = _read_wav_to_int16_16k(wav_path)
    if samples_int16.size == 0:
        logger.warning("tune_detectors: %s decoded to 0 samples — skipping", wav_path)
        return 0

    # Construct fresh per-WAV state. Each WAV gets its own router + detectors
    # so cross-track baselines don't leak.
    state = MusicState()
    audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    detector = EventDetector(audio_buf=audio_buf)

    # Synthetic clock that EventDetector + chain detectors will read via
    # the patched time.time inside vibemix.state.event_detector.
    current_t: list[float] = [0.0]  # mutable cell so the closure can advance it

    def _synthetic_clock() -> float:
        return current_t[0]

    # Refresh-loop-local helpers (matches the asyncio loop's locals).
    last_audible_high = 0.0
    last_audible_low = 0.0
    bpm_cache = 0.0
    last_bpm_at = 0.0
    feature_history: deque[dict] = deque(maxlen=5)

    controller_stub = _ControllerStateStub()
    track_stub = _TrackInfoStub()

    n_total = samples_int16.size
    n_hops = n_total // _TICK_HOP_SAMPLES

    # Patch time.time inside event_detector for the duration of this WAV
    # walk. Chain detectors receive `now` from EventDetector — same patched
    # clock — so trailing-window math (KILL 8s baseline, etc.) ages naturally
    # against synthetic time without burning real wall-clock seconds per tick.
    with patch("vibemix.state.event_detector.time.time", _synthetic_clock):
        for hop_idx in range(n_hops):
            hop = samples_int16[
                hop_idx * _TICK_HOP_SAMPLES : (hop_idx + 1) * _TICK_HOP_SAMPLES
            ]
            audio_buf.push(hop)
            current_t[0] = (hop_idx + 1) * _TICK_HOP_SECONDS

            try:
                last_audible_high, last_audible_low, bpm_cache, last_bpm_at = _tick_once(
                    state,
                    audio_buf,
                    controller_stub,
                    track_stub,
                    now=current_t[0],
                    last_audible_high=last_audible_high,
                    last_audible_low=last_audible_low,
                    bpm_cache=bpm_cache,
                    last_bpm_at=last_bpm_at,
                    feature_history=feature_history,
                )
            except Exception as e:  # pragma: no cover — defensive; refresh loop is wrapped in production too
                logger.warning(
                    "tune_detectors: tick %d (%s @ t=%.2f) raised %s: %s",
                    hop_idx,
                    track_basename,
                    current_t[0],
                    type(e).__name__,
                    e,
                )
                continue

            # CLI overrides applied AFTER the writer tick but BEFORE the
            # detector dispatch — they shouldn't influence the writer's
            # truth (audio is canonical), but they should influence which
            # genre chain runs + what BPM the chain detectors see.
            if bpm_override is not None:
                state.bpm = bpm_override
            if genre_override is not None:
                state.active_genre = genre_override

            event = detector.detect(state, kaan_just_spoke=False, manual=False)
            if event is None:
                continue

            t_now = current_t[0]
            bar_index = 0
            if state.bpm > 0:
                # Same formula PhraseBoundaryDetector uses internally:
                # beats = t * bpm / 60; bars = beats / 4.
                bar_index = int(t_now * state.bpm / 60.0 / 4.0)

            score_payload: dict[str, Any] = dict(event.extra) if event.extra else {}
            score_str = json.dumps(score_payload, sort_keys=True)

            threshold = _DETECTOR_THRESHOLDS.get(event.type, 0.0)

            csv_writer.writerow(
                [
                    track_basename,
                    f"{t_now:.3f}",
                    bar_index,
                    event.type,
                    score_str,
                    threshold,
                    1,
                ]
            )
            rows_written += 1

    return rows_written


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tune_detectors.py",
        description=(
            "Phase 17 reference-WAV detector tuning harness. Drives one or more "
            "WAV files through the full GenreRouter + EventDetector + 6 Wave-2 "
            "detector pipeline and emits a per-fire CSV (track, t_seconds, "
            "bar_index, detector_name, score, threshold, fired) for Phase 16 "
            "ear-audit + Plan 17-02..04 threshold validation."
        ),
        epilog=(
            "Hard Tek anchor tracks expected at "
            ".planning/phases/17-hard-tek-detectors-v1-genrerouter-musicstate-extension/"
            "anchor_tracks/. STATE.md outstanding to-do — Kaan-owned. See Phase 16 "
            "ear-audit for the consumer side of this harness."
        ),
    )
    parser.add_argument(
        "wavs",
        metavar="WAV",
        nargs="*",
        type=str,
        help="One or more reference WAV files to walk through the detector chain.",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        type=str,
        default=None,
        help=(
            "Output CSV path. Default: tuning_runs/<UTC-iso>.csv under repo root. "
            "Schema: track, t_seconds, bar_index, detector_name, score, threshold, fired."
        ),
    )
    parser.add_argument(
        "--bpm-override",
        dest="bpm_override",
        type=float,
        default=None,
        help="Force state.bpm to this value (default: derive via estimate_bpm).",
    )
    parser.add_argument(
        "--genre-override",
        dest="genre_override",
        type=str,
        default=None,
        help=(
            "Force state.active_genre to this value (one of: house, techno, "
            "hard_tek, unknown). Default: derive via the same heuristic "
            "state_refresh_loop uses."
        ),
    )
    return parser


def _default_csv_path() -> Path:
    """Default output: ``tuning_runs/<UTC-iso>.csv`` under repo root.

    ``tuning_runs/`` is gitignored — see scripts/README.md for rationale
    (per Plan 17-06 threat register T-17-06-04 mitigation).
    """
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return Path("tuning_runs") / f"{ts}.csv"


def main(argv: list[str] | None = None) -> int:
    """Harness entry point. Returns UNIX exit code.

    Returns:
        0 — Success (CSV written, all WAVs processed).
        2 — Usage error (no input WAVs supplied — Kaan-action surface).
    """
    if argv is None:
        argv = sys.argv[1:]

    # Configure logger (idempotent). Stderr-only so stdout stays clean for
    # any future pipeline use.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    if not args.wavs:
        msg = (
            "tune_detectors: no input WAV files. Hard Tek anchor tracks "
            "Kaan-action — see Phase 16 ear-audit + STATE.md outstanding "
            "to-do `Collect Hard Tek + 9 SKU reference tracks`. Suggested "
            "anchor location: .planning/phases/"
            "17-hard-tek-detectors-v1-genrerouter-musicstate-extension/"
            "anchor_tracks/"
        )
        print(msg, file=sys.stderr)
        return 2

    csv_path = Path(args.csv_path) if args.csv_path else _default_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    started = _wall_time.perf_counter()
    total_rows = 0
    n_wavs = len(args.wavs)

    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["track", "t_seconds", "bar_index", "detector_name", "score", "threshold", "fired"]
        )

        for wav_str in args.wavs:
            wav_path = Path(wav_str)
            if not wav_path.exists():
                logger.warning("tune_detectors: input %s does not exist — skipping", wav_path)
                continue
            try:
                rows = _process_wav(
                    wav_path,
                    bpm_override=args.bpm_override,
                    genre_override=args.genre_override,
                    csv_writer=writer,
                )
                total_rows += rows
                logger.info(
                    "tune_detectors: %s → %d rows", wav_path.name, rows
                )
            except Exception as e:
                logger.error(
                    "tune_detectors: %s raised %s: %s",
                    wav_path,
                    type(e).__name__,
                    e,
                )
                continue

    elapsed = _wall_time.perf_counter() - started
    logger.info(
        "tune_detectors: processed %d WAV(s) in %.2fs → %s (%d rows)",
        n_wavs,
        elapsed,
        csv_path,
        total_rows,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
