# SPDX-License-Identifier: Apache-2.0
"""Offline auto-cue detection — the foundation of "Viber auto-places your hot cues".

This module runs OFFLINE structure analysis on a fully-decoded track and emits
ordered :class:`CuePoint` markers at the musically meaningful, mixable moments
(intro mix-in, breakdown, drop / re-entry, phrase boundaries). It is the
"Path 2" analysis layer that lets the cue-anchored embedding strategy
(``LibraryEmbedder`` + ``ingest_folder``) embed ~80s regions anchored at the
parts a DJ actually mixes on, instead of arbitrary intro/mid/outro slices.

# Why a fresh offline analyzer (not the live detectors)

The live ``vibemix.state.detectors`` classes (``BreakdownKickKillDetector``,
``ReentryKickLandDetector``, ``PhraseBoundaryDetector``, …) are **stateful
streaming processors**: they read a live ``MusicState`` (sub-band share, RMS,
beat_phase, bpm_confidence) and keep ``now``-keyed trailing-window baselines
that rotate every few seconds. They are tuned to fire ONCE on a live edge with
per-type cooldowns — they cannot be replayed cleanly over a decoded file
without reconstructing the whole state-refresh loop.

What IS reusable offline are their **pure DSP primitives**, which take a bare
numpy array + sample rate and have zero I/O / zero state:

    - ``vibemix.state.detectors._dsp.sub_share`` — fraction of FFT energy in
      the sub band. The SAME math the live ``BreakdownKickKillDetector`` /
      ``ReentryKickLandDetector`` watch via ``state.bands["sub"]``. We compute
      it per-frame here to build a sub-energy curve over the whole track.
    - ``vibemix.state.detectors._phrase_dsp.lock_downbeat_phase`` /
      ``estimate_phrase_length_bars`` — the SAME band-limited downbeat lock +
      self-similarity the live ``PhraseBoundaryDetector`` uses, to snap raw
      energy-edge candidates onto the phrase grid.

So this is NOT a reinvention: the breakdown/re-entry detection reuses the
exact ``sub_share`` primitive the live detectors trust, and the phrase snapping
reuses the exact ``_phrase_dsp`` lock the live ``PhraseBoundaryDetector`` uses.
The only new code is the offline orchestration: a frame loop + edge-finding +
phrase-grid snapping. That is documented inline.

# Anti-hallucination contract (v4 "trust the audio")

Deterministic, pure-DSP, **NO network, NO Gemini call**. On a track with no
detectable structure (silence, no sub-band energy, too short), we emit FEWER
cues — never a fabricated grid. A cue is only emitted when a real energy edge
(or phrase boundary) is present in the audio. We never invent a "drop" that
the sub-energy curve does not support.

# Output

``detect_cues(audio_path, max_cues=N)`` returns up to ``N`` ordered
:class:`CuePoint`s with ascending ``start_s`` and hot-cue ``number`` 1..N. The
``type`` is one of the Rekordbox-compatible values in
``{"cue", "loop", "fadein", "fadeout", "load"}`` (we emit only ``"cue"`` — the
breakdown/re-entry/phrase markers are all hot cues; loop/fade timing is
deferred, see module TODO). ``end_s`` is ``None`` (loops not emitted).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import numpy as np

from vibemix.library.rekordbox import CuePoint

# NOTE: the live-detector DSP primitives (``vibemix.state.detectors._dsp`` /
# ``._phrase_dsp``) are imported LAZILY inside the functions below, NOT at
# module top-level. Importing the ``vibemix.state.detectors`` package runs its
# ``__init__`` which eagerly imports every live detector — and those
# transitively pull in ``vibemix.state.coach`` / ``vibemix.state.refresh``.
# vibemix.library.__init__ imports this module, and vibemix.memory imports
# vibemix.library, so an eager top-level import here would leak the live
# reaction path into the memory storage spine (the no-live-path import-boundary
# gate in tests/memory/test_no_live_path_import.py). Lazy imports keep cue
# detection's DSP reuse honest WITHOUT dragging the coach loop into the library
# import graph. The pure functions themselves are still the exact same math.

logger = logging.getLogger(__name__)


# ─── Analysis constants ────────────────────────────────────────────────────────

# Mono analysis sample rate. 16kHz matches the canonical live-pipeline buffer
# rate (``vibemix.audio`` resamples 48k→16k) so the DSP primitives behave
# bit-for-bit the way they do live. The sub band (20-100Hz) is fully resolved
# well below Nyquist; no reason to decode at 44.1/48k for structure analysis.
ANALYSIS_SR: int = 16000

# Frame hop for the sub-energy curve. 1.0s gives ~1Hz resolution — the same
# hop the live ``energy_curve`` uses and that ``estimate_phrase_length_bars``
# defaults to (``hop_seconds=1.0``). Coarse enough to be cheap over a 6-minute
# track, fine enough to localise a breakdown to within a second.
FRAME_HOP_S: float = 1.0

# Per-frame analysis window. We feed each frame to ``sub_share`` which uses a
# 16384-sample (~1.0s @ 16kHz) Hanning-windowed rfft internally; a 2.0s window
# gives that FFT a comfortable, centred sample without starving short tracks.
FRAME_WIN_S: float = 2.0

# Sub-share thresholds for breakdown / re-entry edge detection. These mirror
# the SHAPE of the live detectors' logic (a "kill" = sub collapses below a
# floor after being high; a "re-entry" = sub recovers above a floor). The
# absolute numbers are looser than the live constants because offline we have
# the WHOLE curve and use a relative-to-track-median comparison rather than a
# rotating 8s baseline — see ``_find_sub_edges``.
SUB_KILL_REL: float = 0.45  # sub frame < 45% of the track's busy-median = a kill
SUB_REENTRY_REL: float = 0.80  # sub recovers to ≥ 80% of busy-median = a re-entry

# A track shorter than this has no meaningful mix structure to cue — emit only
# a single load cue at 0s rather than fabricating a grid.
MIN_TRACK_S: float = 30.0

# ffmpeg decode timeout — guard against a hung / malformed file.
FFMPEG_TIMEOUT_S: int = 60

__all__ = ["detect_cues", "decode_to_mono", "ANALYSIS_SR"]


# ─── Decode ─────────────────────────────────────────────────────────────────────


def _require_ffmpeg() -> str:
    ff = shutil.which("ffmpeg")
    if ff is None:
        raise RuntimeError(
            "ffmpeg is required for offline cue detection. Install via "
            "`brew install ffmpeg` (mac) or `winget install Gyan.FFmpeg` (windows)."
        )
    return ff


def decode_to_mono(audio_path: Path, sample_rate: int = ANALYSIS_SR) -> np.ndarray:
    """Decode ``audio_path`` to a mono float32 array at ``sample_rate``.

    Reuses ffmpeg exactly the way ``library.embed`` does (subprocess, hard
    dep), but pipes raw PCM to stdout instead of writing mp3 tempfiles —
    cue detection needs the samples in memory, not on disk. Output is
    little-endian float32 in [-1, 1], single channel.

    Returns a zero-length array on a decode that yields no audio (the caller
    treats that as "no structure" and emits a single load cue).
    """
    ffmpeg = _require_ffmpeg()
    cmd = [
        ffmpeg,
        "-v",
        "error",
        "-i",
        str(audio_path),
        "-ac",
        "1",  # mono
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",  # raw little-endian float32 PCM
        "-",
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        timeout=FFMPEG_TIMEOUT_S,
        check=True,
    )
    return np.frombuffer(proc.stdout, dtype="<f4").astype(np.float32)


# ─── Sub-energy curve + edge finding ────────────────────────────────────────────


def _sub_energy_curve(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Per-frame sub-band share over the whole track.

    Reuses ``_dsp.sub_share`` — the SAME primitive the live breakdown /
    re-entry detectors watch via ``state.bands["sub"]`` — frame by frame.
    Returns a 1D float32 array, one value per ``FRAME_HOP_S`` of audio.
    """
    from vibemix.state.detectors._dsp import sub_share

    if samples.size == 0:
        return np.zeros(0, dtype=np.float32)
    hop = int(FRAME_HOP_S * sample_rate)
    win = int(FRAME_WIN_S * sample_rate)
    n_frames = max(1, samples.size // hop)
    curve = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        center = i * hop
        lo = max(0, center - win // 2)
        hi = min(samples.size, center + win // 2)
        curve[i] = sub_share(samples[lo:hi], sample_rate)
    return curve


def _rms_curve(samples: np.ndarray, sample_rate: int, n_frames: int) -> np.ndarray:
    """Per-frame RMS, aligned to the same hop grid as the sub-energy curve.

    Used as the "music is still playing" gate (the live ``LOW_RMS`` check) so a
    fade-out / silent tail is not mistaken for a breakdown re-entry.
    """
    if samples.size == 0 or n_frames == 0:
        return np.zeros(0, dtype=np.float32)
    hop = int(FRAME_HOP_S * sample_rate)
    out = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        lo = i * hop
        hi = min(samples.size, lo + hop)
        seg = samples[lo:hi]
        out[i] = float(np.sqrt(np.mean(seg * seg))) if seg.size else 0.0
    return out


def _find_sub_edges(
    sub_curve: np.ndarray, rms_curve: np.ndarray
) -> tuple[list[int], list[int]]:
    """Find breakdown (kill) and re-entry frame indices in the sub-energy curve.

    Mirrors the SHAPE of the live ``BreakdownKickKillDetector`` /
    ``ReentryKickLandDetector`` pair, adapted for offline whole-curve analysis:

        - "busy median" = median sub-share over frames where the track is
          audible (RMS above a small floor). This is the offline analogue of
          the live rotating-8s baseline: it answers "what's a normal kick-busy
          level for THIS track".
        - A KILL edge = a frame whose sub-share falls below
          ``SUB_KILL_REL * busy_median`` while RMS is still up (music playing,
          not the track ending).
        - A RE-ENTRY edge = the first frame AFTER a kill whose sub-share
          recovers to ≥ ``SUB_REENTRY_REL * busy_median``.

    Each kill pairs with at most one re-entry (same contract as the live pair).
    Returns ``(kill_frames, reentry_frames)`` as sorted frame indices.
    """
    n = sub_curve.size
    if n == 0:
        return [], []

    # Music-playing mask — frames with real energy. The RMS floor is relative
    # to the track's own peak so it adapts to quiet vs loud masters (no fixed
    # absolute LOW_RMS, which was tuned for the live 16k buffer's int16 scale).
    rms_peak = float(rms_curve.max()) if rms_curve.size else 0.0
    rms_floor = 0.05 * rms_peak  # below 5% of peak = effectively silent
    playing = rms_curve > rms_floor if rms_curve.size == n else np.ones(n, dtype=bool)

    busy = sub_curve[playing & (sub_curve > 0.0)]
    if busy.size < 4:
        # Not enough busy frames to establish a baseline — no honest edges.
        return [], []
    busy_median = float(np.median(busy))
    if busy_median <= 0.0:
        return [], []

    kill_thr = SUB_KILL_REL * busy_median
    reentry_thr = SUB_REENTRY_REL * busy_median

    kills: list[int] = []
    reentries: list[int] = []
    in_kill = False
    for i in range(n):
        sub = float(sub_curve[i])
        is_playing = bool(playing[i]) if playing.size == n else True
        if not in_kill:
            # Looking for a kill: sub collapses while music still plays.
            if is_playing and sub < kill_thr:
                kills.append(i)
                in_kill = True
        else:
            # Inside a breakdown — looking for the re-entry.
            if is_playing and sub >= reentry_thr:
                reentries.append(i)
                in_kill = False
    return kills, reentries


# ─── Phrase grid ─────────────────────────────────────────────────────────────────


def _estimate_bpm(samples: np.ndarray, sample_rate: int) -> float:
    """Coarse BPM estimate from the band-limited (kick) autocorrelation.

    Reuses ``_phrase_dsp.band_limited_autocorr`` indirectly via a small local
    peak-pick — we only need a rough BPM to feed ``lock_downbeat_phase`` and
    ``estimate_phrase_length_bars``. Returns 0.0 when no convincing periodicity
    exists (the caller then skips phrase snapping — anti-hallucination).
    """
    from vibemix.state.detectors._phrase_dsp import band_limited_autocorr

    # Analyse a representative middle slice (avoid intro/outro dead air).
    if samples.size < sample_rate * 8:
        return 0.0
    mid = samples.size // 2
    half_win = int(8 * sample_rate)
    slice_ = samples[max(0, mid - half_win) : mid + half_win]
    ac = band_limited_autocorr(slice_, sample_rate)
    if ac.size == 0:
        return 0.0
    # Search the lag range corresponding to 70-180 BPM (the dance-music core).
    lo_lag = int(sample_rate * 60.0 / 180.0)
    hi_lag = int(sample_rate * 60.0 / 70.0)
    hi_lag = min(hi_lag, ac.size - 1)
    if hi_lag <= lo_lag:
        return 0.0
    window = ac[lo_lag : hi_lag + 1]
    # A convincing beat peak must clear the local noise floor (mean + 2σ),
    # mirroring estimate_phrase_length_bars' strictness — no fabricated BPM.
    floor = float(window.mean()) + 2.0 * (float(window.std()) or 1e-6)
    peak_local = int(np.argmax(window))
    if float(window[peak_local]) < floor:
        return 0.0
    best_lag = lo_lag + peak_local
    if best_lag <= 0:
        return 0.0
    return 60.0 * sample_rate / best_lag


def _snap_to_phrase_grid(
    candidate_s: float,
    samples: np.ndarray,
    sample_rate: int,
    bpm: float,
) -> float:
    """Snap a raw energy-edge candidate (in seconds) to the nearest bar
    downbeat using the SAME downbeat lock the live PhraseBoundaryDetector uses.

    Reuses ``_phrase_dsp.lock_downbeat_phase``. When the lock is too weak
    (``confidence < 0.5``, the live
    ``BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`` floor) we leave the candidate where it
    is rather than snapping it onto a fabricated grid — anti-hallucination.
    """
    from vibemix.state.detectors._phrase_dsp import lock_downbeat_phase

    if bpm <= 0.0:
        return candidate_s
    # Lock the downbeat phase off an 8s window around the candidate.
    win = int(8 * sample_rate)
    center = int(candidate_s * sample_rate)
    lo = max(0, center - win // 2)
    hi = min(samples.size, lo + win)
    phase, conf = lock_downbeat_phase(samples[lo:hi], bpm, sample_rate)
    if conf < 0.5:
        return candidate_s
    # Snap to the nearest BAR downbeat (one bar = 4 beats). The lock gives us
    # phase within a bar, so the nearest downbeat is candidate - (phase *
    # bar_seconds), adjusted to the closer of the two adjacent downbeats.
    bar_seconds = 4.0 * 60.0 / bpm
    if bar_seconds <= 0:
        return candidate_s
    # phase ∈ [0,1) = how far into the current bar the candidate sits.
    offset_into_bar = phase * bar_seconds
    down_below = candidate_s - offset_into_bar
    down_above = down_below + bar_seconds
    snapped = (
        down_below
        if abs(candidate_s - down_below) <= abs(candidate_s - down_above)
        else down_above
    )
    return max(0.0, snapped)


# ─── Public API ─────────────────────────────────────────────────────────────────


def detect_cues(audio_path: Path, *, max_cues: int = 4) -> list[CuePoint]:
    """Detect up to ``max_cues`` musically meaningful cue points in ``audio_path``.

    Deterministic, pure-DSP, NO network, NO Gemini. Decodes the file to mono
    (``decode_to_mono``), builds a sub-band energy curve (reusing the live
    ``_dsp.sub_share`` primitive), finds breakdown / re-entry edges (reusing the
    live breakdown/re-entry SHAPE), snaps them to the phrase grid (reusing the
    live ``_phrase_dsp`` downbeat lock), and emits ordered hot cues.

    Cue priority (most to least mixable):
        1. Intro mix-in  — first sustained-energy frame (``type="cue"`` #1, the
           load/mix-in point). Always emitted if the track has any energy.
        2. Re-entry / drop — sub recovers after a breakdown (the moment a DJ
           wants the incoming track to land on).
        3. Breakdown      — sub collapses (a mix-out / blend opportunity).
        4. Phrase boundaries — fallback fillers if fewer than ``max_cues``
           structural edges were found, placed on detected phrase downbeats.

    Returns up to ``max_cues`` :class:`CuePoint`s, ascending ``start_s``,
    hot-cue ``number`` 1..``max_cues``, all ``type="cue"`` (loop/fade timing
    deferred). A track with no detectable structure yields a single ``load``
    cue at 0.0s — never a fabricated grid.
    """
    if max_cues < 1:
        max_cues = 1

    samples = decode_to_mono(audio_path)
    duration_s = samples.size / float(ANALYSIS_SR) if samples.size else 0.0

    # No audio / too short — single honest load cue at the start.
    if samples.size == 0 or duration_s < MIN_TRACK_S:
        return [
            CuePoint(name="load", type="load", start_s=0.0, end_s=None, number=1)
        ]

    sub_curve = _sub_energy_curve(samples, ANALYSIS_SR)
    rms_curve = _rms_curve(samples, ANALYSIS_SR, sub_curve.size)
    kills, reentries = _find_sub_edges(sub_curve, rms_curve)
    bpm = _estimate_bpm(samples, ANALYSIS_SR)

    # Build a candidate list of (position_s, label). Dedup + ordering happen
    # after snapping. positions are frame_index * FRAME_HOP_S.
    candidates: list[tuple[float, str]] = []

    # 1. Intro mix-in: first frame whose sub-share clears half the busy median
    #    (the kick groove has started). Falls back to 0.0 on a soft intro.
    busy = sub_curve[sub_curve > 0.0]
    if busy.size:
        busy_median = float(np.median(busy))
        intro_thr = 0.5 * busy_median
        intro_frame = next(
            (i for i, v in enumerate(sub_curve) if float(v) >= intro_thr), 0
        )
        candidates.append((intro_frame * FRAME_HOP_S, "intro"))

    # 2. Re-entries (drops) — the highest-value mix targets.
    for r in reentries:
        candidates.append((r * FRAME_HOP_S, "reentry"))

    # 3. Breakdowns — mix-out opportunities.
    for k in kills:
        candidates.append((k * FRAME_HOP_S, "breakdown"))

    # 4. Phrase-boundary fillers — only if we still need more cues AND have a
    #    BPM lock. Place them on phrase downbeats spread across the track. This
    #    never fabricates structure: a phrase boundary IS a real grid position,
    #    and we only emit them up to max_cues.
    if bpm > 0.0 and len(candidates) < max_cues:
        from vibemix.state.detectors._phrase_dsp import estimate_phrase_length_bars

        phrase_bars = estimate_phrase_length_bars(
            sub_curve.tolist(), bpm, hop_seconds=FRAME_HOP_S
        )
        phrase_s = phrase_bars * 4.0 * 60.0 / bpm
        if phrase_s > 0:
            t = phrase_s
            while t < duration_s and len(candidates) + 0 < max_cues * 3:
                candidates.append((t, "phrase"))
                t += phrase_s

    # Snap every candidate to the phrase grid (no-op when lock is weak).
    snapped: list[tuple[float, str]] = []
    for pos, label in candidates:
        s = _snap_to_phrase_grid(pos, samples, ANALYSIS_SR, bpm)
        s = min(max(0.0, s), duration_s)
        snapped.append((s, label))

    # Dedup positions within 1.5s of each other (keep the first / higher
    # priority by virtue of insertion order: intro→reentry→breakdown→phrase),
    # then order by time and cap at max_cues.
    snapped_sorted = sorted(snapped, key=lambda x: x[0])
    deduped: list[tuple[float, str]] = []
    for pos, label in snapped_sorted:
        if deduped and abs(pos - deduped[-1][0]) < 1.5:
            continue
        deduped.append((pos, label))

    # Priority pick: if we have more than max_cues, keep intro + re-entries +
    # breakdowns first (structural), then phrase fillers.
    priority = {"intro": 0, "reentry": 1, "breakdown": 2, "phrase": 3}
    chosen = sorted(deduped, key=lambda x: priority.get(x[1], 9))[:max_cues]
    chosen.sort(key=lambda x: x[0])

    if not chosen:
        return [
            CuePoint(name="load", type="load", start_s=0.0, end_s=None, number=1)
        ]

    cues: list[CuePoint] = []
    for n, (pos, label) in enumerate(chosen, start=1):
        cues.append(
            CuePoint(
                name=label,
                type="cue",
                start_s=round(float(pos), 3),
                end_s=None,
                number=n,
            )
        )
    return cues
