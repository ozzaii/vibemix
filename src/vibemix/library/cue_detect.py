# SPDX-License-Identifier: Apache-2.0
"""Offline auto-cue engine — the foundation of "Viber auto-places your hot cues".

This module runs OFFLINE structure analysis on a fully-decoded track and emits
ordered :class:`CueAnchor` spans (``source="fallback"``) at the musically meaningful,
mixable regions: ``intro / build / breakdown / drop / outro``. It is the
"Path 2" analysis layer that lets the cue-anchored embedding strategy
(``ClapEmbedder`` + ``ingest_folder``) embed phrase-aligned mixable windows
anchored at the parts a DJ actually mixes on, and (later) feeds the live
co-host's "enter on hot cue 2, exit at the breakdown" suggestions.

# Why a fresh offline analyzer (not the live detectors)

The live ``vibemix.state.detectors`` classes (``BreakdownKickKillDetector``,
``ReentryKickLandDetector``, ``PhraseBoundaryDetector``, …) are **stateful
streaming processors**: they read a live ``MusicState`` and keep ``now``-keyed
trailing-window baselines that rotate every few seconds. They fire ONCE on a
live edge with per-type cooldowns — they cannot be replayed cleanly over a
decoded file without reconstructing the whole state-refresh loop.

What IS reusable offline are their **pure DSP primitives**, which take a bare
numpy array + sample rate and have zero I/O / zero state:

    - ``vibemix.state.detectors._dsp.sub_share`` — fraction of FFT energy in the
      sub band (the SAME math the live breakdown / re-entry detectors watch).
    - ``vibemix.state.detectors._phrase_dsp.band_limited_autocorr`` /
      ``lock_downbeat_phase`` / ``estimate_phrase_length_bars`` — the SAME
      band-limited downbeat lock + self-similarity the live
      ``PhraseBoundaryDetector`` uses, to estimate BPM, snap candidates onto the
      phrase grid, and size phrase-aligned windows.

So this is NOT a reinvention: the breakdown/re-entry detection reuses the exact
``sub_share`` primitive the live detectors trust, and the phrase snapping reuses
the exact ``_phrase_dsp`` lock the live ``PhraseBoundaryDetector`` uses. The new
code is the offline orchestration: a per-frame feature loop, Foote-novelty
boundaries, track-relative segment labeling, the dance-degrade gate, mixable
window sizing, and confidence scoring. That is documented inline.

# What "drop" actually means (the live-ear correction, 2026-05-26)

The original engine ranked segments by ENERGY and called the loudest full-band
segment the drop. On brick-walled hardtechno that is the bug: the master is so
compressed that the intro groove and the "drop" are indistinguishable by loudness
— the percentile-normalized energy spread stretched a uniform groove into fake
structure, and the loudest-segment heuristic dropped the cue in the wrong place.

Live ear-testing fixed the definition for dance/techno:

    drop      = the kick slamming back IN after a sustained breakdown (the
                RE-ENTRY frame — the kick-back, not "the loudest part").
    breakdown = the bass-cut (kill) that starts that breakdown (the KILL frame).

So structure, not energy, drives the labels: the drop/breakdown pair IS the
kill→reentry pair the sub-edge finder already locates. We emit only the MOST
SIGNIFICANT breakdown(s) (top-2) — hardtechno repeats one characteristic
breakdown, and spraying every micro-stutter is redundant noise.

# The engine pipeline (per the 2026-05-26 design spec, breakdown-driven rewrite)

    decode → per-frame feature curves → sub-edge kill/reentry pairs
           → significant-breakdown selection → structural cue building
           → dance-degrade gate → mixable windows → confidence

1. Per-frame features (1Hz hop): sub-band share (the live ``sub_share``) + RMS.
   The four-band split + onset density are still computed for the busy-median
   context but the structure now comes from the sub-edge pairs, not from
   energy-segment ranking.
2. Sub-edge pairs: ``_find_sub_edges`` returns kill (bass-out) / reentry
   (kick-back) frames — the SAME math the live breakdown / re-entry detectors
   trust. ``_significant_breakdowns`` pairs each kill with its NEXT reentry,
   keeps only pairs whose bass-out lasts ≥ ``_MIN_BREAKDOWN_S`` (shorter gaps
   are kick stutters, not structure), dedups near-coincident kills, scores each
   by ``gap_seconds × bass_drop_depth`` and caps at ``_MAX_BREAKDOWNS``.
3. Structural cue building: intro = first sustained-energy frame; for each
   significant breakdown a ``breakdown`` anchor at the kill and a ``drop`` anchor
   at the reentry (the kick-back); outro = last sustained-energy region near EOF;
   an optional ``build`` before a drop when the pre-drop region is rising.
4. Dance-degrade gate (anti-hallucination): dance labels (drop/breakdown/build)
   require G1 beat-presence (valid bpm + ``beat_ratio ≥ 1.0``) AND at least one
   significant breakdown. Beat present but NO significant breakdown (a steady
   groove/tool) → ONLY intro + outro — NEVER a fabricated drop. No beat / too
   short / silent → ``[]`` or intro/outro. This replaces the old percentile
   energy-spread gate (G2'), which was the brick-wall bug.
5. Mixable windows: phrase-aligned mix-region within the section
   (intro/outro target 32 bars, drop/breakdown 16 bars), capped at 80s.
6. Confidence: geometric mean of boundary_salience · label_margin · grid_conf ·
   method_agreement (the ``lock_downbeat_phase`` confidence — previously
   discarded — is captured here as ``grid_conf``).

# Anti-hallucination contract (v4 "trust the audio")

Deterministic, pure-DSP, **NO network, NO Gemini call**. On a track with no
detectable structure (silence, no sub-band energy, too short) we return an
EMPTY list — never a fabricated grid, never a fabricated drop on flat/beatless
material. A dance label (drop/breakdown/build) is only emitted when a real beat
is present AND a real sustained breakdown (kill→reentry ≥ _MIN_BREAKDOWN_S) was
found in the audio. A steady groove with no breakdown gets intro/outro only.

# Output

``detect_cues(audio_path, *, max_cues=N)`` returns up to ``N`` ordered
:class:`CueAnchor`s (``source="fallback"``) with ascending ``start_s``, each carrying
a ≤80s phrase-aligned mixable window (``start_s`` < ``end_s``) and a [0,1]
``confidence``. Empty list on no structure.
"""

from __future__ import annotations

import logging
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np

from vibemix.library.cue_types import CueAnchor

# NOTE: the live-detector DSP primitives (``vibemix.state.detectors._dsp`` /
# ``._phrase_dsp``) are imported LAZILY inside the functions below, NOT at
# module top-level. Importing the ``vibemix.state.detectors`` package runs its
# ``__init__`` which eagerly imports every live detector — and those
# transitively pull in ``vibemix.state.prompt_builder`` / ``vibemix.state.refresh``.
# vibemix.library.__init__ imports this module, and vibemix.memory imports
# vibemix.library, so an eager top-level import here would leak the live
# reaction path into the memory storage spine (the no-live-path import-boundary
# gate in tests/memory/test_no_live_path_import.py). Lazy imports keep cue
# detection's DSP reuse honest WITHOUT dragging the coach loop into the library
# import graph. The pure functions themselves are still the exact same math.

logger = logging.getLogger(__name__)


# ─── Analysis constants ────────────────────────────────────────────────────────

# Mono analysis sample rate. 16kHz matches the canonical live-pipeline buffer
# rate so the DSP primitives behave bit-for-bit the way they do live. The sub
# band (20-100Hz) is fully resolved well below Nyquist.
ANALYSIS_SR: int = 16000

# Frame hop for the per-frame feature curves. 1.0s gives ~1Hz resolution — the
# same hop the live ``energy_curve`` uses and that ``estimate_phrase_length_bars``
# defaults to. Coarse enough to be cheap over a 6-minute track, fine enough to
# localise structure to within a second.
FRAME_HOP_S: float = 1.0

# Per-frame analysis window. ``sub_share`` uses a 16384-sample (~1.0s @ 16kHz)
# Hanning-windowed rfft internally; a 2.0s window gives that FFT a comfortable,
# centred sample without starving short tracks. The direct band-split below
# reuses the same window for numeric alignment.
FRAME_WIN_S: float = 2.0

# Sub-share thresholds for the breakdown / re-entry edge finder. Mirror the
# SHAPE of the live detectors (a "kill" = sub collapses below a floor after
# being high; a "re-entry" = sub recovers). Looser absolute numbers than the
# live constants because offline we have the WHOLE curve and compare to a
# track-relative busy-median rather than a rotating 8s baseline.
SUB_KILL_REL: float = 0.45  # sub frame < 45% of the track's busy-median = a kill
SUB_REENTRY_REL: float = 0.80  # sub recovers to ≥ 80% of busy-median = a re-entry

# A track shorter than this has no meaningful mix structure to cue — return [].
MIN_TRACK_S: float = 30.0

# ffmpeg decode timeout — guard against a hung / malformed file.
FFMPEG_TIMEOUT_S: int = 60

# Final-anchor dedup radius (seconds). Two anchors closer than this collapse to
# one — hysteresis after phrase-snapping.
_DEDUP_S: float = 1.5

# Minimum musical-section length (seconds). Used to dedup near-coincident
# breakdown kills (the same characteristic breakdown caught twice) and to size
# intro/outro snap regions — a real intro/breakdown/drop/outro is ≥ ~16s; closer
# "edges" are per-phrase percussion fluctuation, not separately-cueable structure.
_MIN_SECTION_S: float = 16.0

# Dance-degrade gate (the anti-hallucination core). Tuned on real tracks — the
# original raw-RMS dynamic-range gate false-negatived brick-walled dance masters,
# and its successor (the spread of track-NORMALIZED per-segment energy) WAS the
# brick-wall bug: percentile normalization stretched a uniform compressed groove
# into fake structure and the loudest segment got mislabeled as the drop. The
# dance gate is now STRUCTURAL: dance labels require G1 beat-presence AND at least
# one significant breakdown (a real bass-out → kick-back), not an energy spread.
_GATE_BEAT_AC_K: float = 2.0  # G1: kick autocorr peak must clear mean + 2σ

# A real breakdown's bass-out lasts at least this long. A kill→reentry gap below
# this (at the 1Hz frame hop, frames ≈ seconds) is a kick stutter / fill, not
# structure — we ignore it. (Live ear-test calibration.)
_MIN_BREAKDOWN_S: float = 6.0

# Emit at most this many breakdown→drop pairs. Hardtechno repeats ONE
# characteristic breakdown; spraying every breakdown is redundant noise. We keep
# the top-N most significant pairs by ``gap × bass_drop_depth``.
_MAX_BREAKDOWNS: int = 2

# Mixable-window phrase targets (bars). intro/outro blend over longer regions;
# drop/breakdown are shorter punch-in windows.
_WINDOW_BARS = {
    "intro": 32,
    "outro": 32,
    "drop": 16,
    "breakdown": 16,
    "build": 16,
}
_MAX_WINDOW_S: float = 80.0  # the embed single-call audio cap.

# Downbeat-lock confidence floor for the internal ``snapped`` flag (the live
# ``BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`` floor).
_SNAP_CONF_MIN: float = 0.5

__all__ = ["ANALYSIS_SR", "audible_bounds_s", "decode_to_mono", "detect_cues"]


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

    Reuses ffmpeg exactly the way ``library.embed`` does (subprocess, hard dep),
    but pipes raw PCM to stdout instead of writing mp3 tempfiles — cue detection
    needs the samples in memory. Output is little-endian float32 in [-1, 1],
    single channel. Returns a zero-length array on a decode that yields no audio
    (the caller treats that as "no structure" and returns []).
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


# ─── Per-frame feature curves ─────────────────────────────────────────────────


def _sub_energy_curve(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    """Per-frame sub-band share over the whole track.

    Reuses ``_dsp.sub_share`` — the SAME primitive the live breakdown /
    re-entry detectors watch via ``state.bands["sub"]`` — frame by frame.
    Returns a 1D float32 array, one value per ``FRAME_HOP_S`` of audio. Kept as
    a named primitive (not folded into ``_feature_curves``) because the edge
    finder + its tests depend on the exact ``sub_share`` numerics.
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
    fade-out / silent tail is not mistaken for a breakdown re-entry, and as the
    track-relative energy ``E`` the segment labeler normalizes.
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


# ─── Sub-energy edge finding (breakdown / re-entry) ──────────────────────────────


def _find_sub_edges(
    sub_curve: np.ndarray, rms_curve: np.ndarray
) -> tuple[list[int], list[int]]:
    """Find breakdown (kill) and re-entry frame indices in the sub-energy curve.

    Mirrors the SHAPE of the live ``BreakdownKickKillDetector`` /
    ``ReentryKickLandDetector`` pair, adapted for offline whole-curve analysis:

        - "busy median" = median sub-share over frames where the track is
          audible (RMS above a small floor) — the offline analogue of the live
          rotating-8s baseline ("what's a normal kick-busy level for THIS track").
        - A KILL edge = a frame whose sub-share falls below
          ``SUB_KILL_REL * busy_median`` while RMS is still up (music playing).
        - A RE-ENTRY edge = the first frame AFTER a kill whose sub-share recovers
          to ≥ ``SUB_REENTRY_REL * busy_median``.

    Each kill pairs with at most one re-entry. Returns ``(kills, reentries)`` as
    sorted frame indices.
    """
    n = sub_curve.size
    if n == 0:
        return [], []

    rms_peak = float(rms_curve.max()) if rms_curve.size else 0.0
    rms_floor = 0.05 * rms_peak  # below 5% of peak = effectively silent
    playing = rms_curve > rms_floor if rms_curve.size == n else np.ones(n, dtype=bool)

    busy = sub_curve[playing & (sub_curve > 0.0)]
    if busy.size < 4:
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
            if is_playing and sub < kill_thr:
                kills.append(i)
                in_kill = True
        else:
            if is_playing and sub >= reentry_thr:
                reentries.append(i)
                in_kill = False
    return kills, reentries


# ─── Significant-breakdown selection (the structure source) ──────────────────────


def _significant_breakdowns(
    kills: list[int],
    reentries: list[int],
    sub_curve: np.ndarray,
    rms_curve: np.ndarray,
) -> list[tuple[int, int, float]]:
    """Pick the most significant breakdown→drop (kill→reentry) pairs.

    The live-ear definition of structure for dance/techno: a ``breakdown`` is the
    bass-cut (kill) and the ``drop`` is the kick slamming back in (the next
    reentry). This pairs them, filters out kick stutters, dedups repeats, and
    ranks by significance.

    Steps (pure numpy):

        1. Pair each kill with its NEXT reentry (the bass-out that recovers).
        2. Keep only pairs whose gap (``reentry − kill`` frames; at the 1Hz hop
           frames ≈ seconds) is ≥ ``_MIN_BREAKDOWN_S`` — shorter bass-outs are
           kick stutters / fills, not structure.
        3. Dedup pairs whose KILL frames are within ``_MIN_SECTION_S`` (the same
           characteristic breakdown caught twice); keep the higher-scoring one.
        4. Score each by ``gap_seconds × bass_drop_depth`` where bass_drop_depth
           is how far the sub-share fell below the track's busy-median during the
           breakdown, normalized to [0, 1] by that median.
        5. Return sorted by score DESCENDING, capped to ``_MAX_BREAKDOWNS``.

    Returns a list of ``(kill_frame, reentry_frame, score)`` tuples.
    """
    if not kills or not reentries or sub_curve.size == 0:
        return []

    # Busy-median = the track's normal kick-busy sub level (same context the edge
    # finder used), so bass_drop_depth is measured against it.
    rms_peak = float(rms_curve.max()) if rms_curve.size else 0.0
    rms_floor = 0.05 * rms_peak
    n = sub_curve.size
    if rms_curve.size == n:
        playing = rms_curve > rms_floor
    else:
        playing = np.ones(n, dtype=bool)
    busy = sub_curve[playing & (sub_curve > 0.0)]
    busy_median = float(np.median(busy)) if busy.size else 0.0
    if busy_median <= 0.0:
        return []

    min_gap = _MIN_BREAKDOWN_S / FRAME_HOP_S  # frames ≈ seconds at 1Hz hop
    reentries_sorted = sorted(reentries)

    pairs: list[tuple[int, int, float]] = []
    for kill in sorted(kills):
        # Next reentry strictly after this kill.
        reentry = next((r for r in reentries_sorted if r > kill), None)
        if reentry is None:
            continue
        gap_frames = reentry - kill
        if gap_frames < min_gap:
            continue  # kick stutter, not a real breakdown
        gap_seconds = gap_frames * FRAME_HOP_S
        # bass_drop_depth: mean sub-share during the breakdown vs the busy-median,
        # normalized → how far the bass dropped (1.0 = sub fully gone).
        bd_sub = float(np.mean(sub_curve[kill:reentry])) if reentry > kill else 0.0
        depth = max(0.0, min(1.0, (busy_median - bd_sub) / busy_median))
        score = gap_seconds * depth
        pairs.append((kill, reentry, score))

    if not pairs:
        return []

    # Dedup near-coincident kills (same characteristic breakdown) — keep the
    # higher-scoring pair within a _MIN_SECTION_S kill window.
    dedup_frames = _MIN_SECTION_S / FRAME_HOP_S
    pairs.sort(key=lambda p: p[2], reverse=True)  # best first
    kept: list[tuple[int, int, float]] = []
    for kill, reentry, score in pairs:
        if any(abs(kill - k) < dedup_frames for k, _, _ in kept):
            continue
        kept.append((kill, reentry, score))

    # Already sorted by score descending; cap to the top _MAX_BREAKDOWNS.
    return kept[:_MAX_BREAKDOWNS]


# ─── BPM + phrase grid ────────────────────────────────────────────────────────


def _estimate_bpm(samples: np.ndarray, sample_rate: int) -> tuple[float, float]:
    """Coarse BPM estimate from the band-limited (kick) autocorrelation.

    Reuses ``_phrase_dsp.band_limited_autocorr``. Returns ``(bpm, peak_ratio)``:
    ``bpm`` is 0.0 when no convincing periodicity exists (the caller skips
    phrase snapping AND fails dance-gate G1 — anti-hallucination). ``peak_ratio``
    is the autocorr peak's prominence over the local noise floor (mean + 2σ
    margin, ≥ 1.0 when convincing) — fed to G1 as the "convincing kick autocorr
    peak" signal so a weak periodicity does not pass the beat-presence gate.
    """
    from vibemix.state.detectors._phrase_dsp import band_limited_autocorr

    if samples.size < sample_rate * 8:
        return 0.0, 0.0
    mid = samples.size // 2
    half_win = int(8 * sample_rate)
    slice_ = samples[max(0, mid - half_win) : mid + half_win]
    ac = band_limited_autocorr(slice_, sample_rate)
    if ac.size == 0:
        return 0.0, 0.0
    # Search the lag range corresponding to 70-180 BPM (the dance-music core).
    lo_lag = int(sample_rate * 60.0 / 180.0)
    hi_lag = int(sample_rate * 60.0 / 70.0)
    hi_lag = min(hi_lag, ac.size - 1)
    if hi_lag <= lo_lag:
        return 0.0, 0.0
    window = ac[lo_lag : hi_lag + 1]
    floor = float(window.mean()) + _GATE_BEAT_AC_K * (float(window.std()) or 1e-6)
    peak_local = int(np.argmax(window))
    peak_val = float(window[peak_local])
    if peak_val < floor:
        return 0.0, 0.0
    best_lag = lo_lag + peak_local
    if best_lag <= 0:
        return 0.0, 0.0
    bpm = 60.0 * sample_rate / best_lag
    # Prominence ratio ≥ 1.0 (peak clears the mean+2σ floor) = convincing beat.
    peak_ratio = peak_val / floor if floor > 0.0 else 0.0
    return bpm, peak_ratio


def _snap_to_phrase_grid(
    candidate_s: float,
    samples: np.ndarray,
    sample_rate: int,
    bpm: float,
) -> tuple[float, float]:
    """Snap a raw candidate (seconds) to the nearest bar downbeat.

    Reuses ``_phrase_dsp.lock_downbeat_phase``. Returns ``(snapped_s, grid_conf)``
    where ``grid_conf`` is the lock confidence (captured here — the live snapper
    discarded it; the spec's confidence factor #3 needs it). When the lock is too
    weak (``grid_conf < _SNAP_CONF_MIN``) the candidate is returned unmoved — no
    snapping onto a fabricated grid (anti-hallucination).
    """
    from vibemix.state.detectors._phrase_dsp import lock_downbeat_phase

    if bpm <= 0.0:
        return candidate_s, 0.0
    win = int(8 * sample_rate)
    center = int(candidate_s * sample_rate)
    lo = max(0, center - win // 2)
    hi = min(samples.size, lo + win)
    phase, conf = lock_downbeat_phase(samples[lo:hi], bpm, sample_rate)
    if conf < _SNAP_CONF_MIN:
        return candidate_s, conf
    bar_seconds = 4.0 * 60.0 / bpm
    if bar_seconds <= 0:
        return candidate_s, conf
    offset_into_bar = phase * bar_seconds
    down_below = candidate_s - offset_into_bar
    down_above = down_below + bar_seconds
    snapped = (
        down_below
        if abs(candidate_s - down_below) <= abs(candidate_s - down_above)
        else down_above
    )
    return max(0.0, snapped), conf


# ─── Confidence ─────────────────────────────────────────────────────────────────


def _confidence(
    boundary_salience: float,
    label_margin: float,
    grid_conf: float,
    method_agreement: float,
) -> float:
    """Geometric mean of the four grounded [0,1] factors (spec §6), clamped.

    A geometric mean (not arithmetic) means any single weak factor pulls the
    whole confidence down — a cue is only trusted when boundary depth, label
    separation, grid lock, AND cross-method corroboration all hold.
    """
    factors = [
        max(0.0, min(1.0, boundary_salience)),
        max(0.0, min(1.0, label_margin)),
        max(0.0, min(1.0, grid_conf)),
        max(0.0, min(1.0, method_agreement)),
    ]
    # Avoid a hard zero collapsing everything; floor each factor at a tiny eps so
    # one un-measured factor doesn't zero an otherwise-strong cue.
    prod = 1.0
    for f in factors:
        prod *= max(f, 1e-3)
    conf = prod ** (1.0 / 4.0)
    return max(0.0, min(1.0, conf))


# ─── Public API ─────────────────────────────────────────────────────────────────


def _first_sustained_frame(sub_curve: np.ndarray, rms_curve: np.ndarray) -> int:
    """The intro anchor: first frame whose sub clears ~0.5× the busy-median (the
    track's groove has actually started), else frame 0."""
    rms_peak = float(rms_curve.max()) if rms_curve.size else 0.0
    rms_floor = 0.05 * rms_peak
    n = sub_curve.size
    playing = rms_curve > rms_floor if rms_curve.size == n else np.ones(n, dtype=bool)
    busy = sub_curve[playing & (sub_curve > 0.0)]
    if busy.size < 4:
        return 0
    busy_median = float(np.median(busy))
    if busy_median <= 0.0:
        return 0
    thr = 0.5 * busy_median
    for i in range(n):
        if (not playing.size or playing[i]) and sub_curve[i] >= thr:
            return i
    return 0


def _last_sustained_frame(rms_curve: np.ndarray) -> int:
    """The outro anchor: walk back from EOF to the last frame with RMS > 5% of
    peak (the last frame where music is still playing, ignoring a silent tail)."""
    n = rms_curve.size
    if n == 0:
        return 0
    rms_peak = float(rms_curve.max())
    rms_floor = 0.05 * rms_peak
    for i in range(n - 1, -1, -1):
        if rms_curve[i] > rms_floor:
            return i
    return n - 1


def audible_bounds_s(
    samples: np.ndarray,
    sample_rate: int = ANALYSIS_SR,
) -> tuple[float, float] | None:
    """Return the first/last audible bounds for decoded audio.

    This is a deterministic floor for cue placement: structure anchors may be
    rich and model-produced, but they must not resolve inside the silent lead-in
    or silent tail of the file. Returns ``None`` for empty/all-silent audio.
    """
    if samples.size == 0:
        return None
    rms_peak = float(np.max(np.abs(samples))) if samples.size else 0.0
    if rms_peak <= 1e-9:
        return None
    sub_curve = _sub_energy_curve(samples, sample_rate)
    n_frames = sub_curve.size
    if n_frames < 1:
        return None
    rms_curve = _rms_curve(samples, sample_rate, n_frames)
    if not rms_curve.size or float(rms_curve.max()) <= 1e-9:
        return None
    duration_s = samples.size / float(sample_rate)
    first_frame = _first_sustained_frame(sub_curve, rms_curve)
    last_frame = _last_sustained_frame(rms_curve)
    first_s = min(duration_s, max(0.0, first_frame * FRAME_HOP_S))
    last_s = min(duration_s, max(first_s, (last_frame + 1) * FRAME_HOP_S))
    if last_s <= first_s:
        return None
    return first_s, last_s


def detect_cues(audio_path: Path, *, max_cues: int = 4) -> list[CueAnchor]:
    """Detect up to ``max_cues`` structural :class:`CueAnchor`s in ``audio_path``.

    Deterministic, pure-DSP, NO network, NO Gemini. Runs the breakdown-driven
    engine pipeline (decode → sub-edge kill/reentry pairs → significant-breakdown
    selection → structural cue building → dance-gate → windows → confidence)
    documented at module top. Returns ``source="fallback"`` anchors with ascending
    ``start_s``, each carrying a ≤80s phrase-aligned mixable window and a [0,1]
    confidence.

    Structure, not energy, drives the labels: a ``drop`` is the kick slamming
    back IN after a sustained breakdown (the re-entry frame), and a ``breakdown``
    is the bass-cut that starts it (the kill frame). We emit only the top
    ``_MAX_BREAKDOWNS`` most significant breakdown→drop pairs.

    Anti-hallucination contract: a track with no detectable structure (silence,
    too short, no sub-band energy) returns ``[]``. A beat present but NO
    significant breakdown (a steady groove/tool) yields ONLY ``intro``/``outro``
    — never a fabricated ``drop``/``build``/``breakdown``.
    """
    if max_cues < 1:
        max_cues = 1

    samples = decode_to_mono(audio_path)
    duration_s = samples.size / float(ANALYSIS_SR) if samples.size else 0.0

    # No audio / too short — no honest structure to cue.
    if samples.size == 0 or duration_s < MIN_TRACK_S:
        return []
    audible_bounds = audible_bounds_s(samples, ANALYSIS_SR)
    if audible_bounds is None:
        return []

    # ── 1. Per-frame feature curves ──
    sub_curve = _sub_energy_curve(samples, ANALYSIS_SR)
    n_frames = sub_curve.size
    if n_frames < 2:
        return []
    rms_curve = _rms_curve(samples, ANALYSIS_SR, n_frames)

    # ── 2. Sub-edge kill/reentry pairs → significant breakdowns ──
    kills, reentries = _find_sub_edges(sub_curve, rms_curve)
    breakdowns = _significant_breakdowns(kills, reentries, sub_curve, rms_curve)

    # ── 3. BPM / beat presence (feeds the dance gate + phrase grid) ──
    bpm, beat_ratio = _estimate_bpm(samples, ANALYSIS_SR)

    # ── 4. Dance-degrade gate (STRUCTURAL, anti-hallucination) ──
    # Dance labels (drop/breakdown/build) require G1 beat-presence AND at least
    # one significant breakdown. No fabricated drop on a steady groove.
    beat_present = bpm > 0.0 and beat_ratio >= 1.0
    dance_ok = beat_present and bool(breakdowns)

    # ── 5. Phrase grid sizing ──
    bar_s = (4.0 * 60.0 / bpm) if bpm > 0.0 else 0.0
    phrase_bars = 16
    if bpm > 0.0:
        from vibemix.state.detectors._phrase_dsp import estimate_phrase_length_bars

        phrase_bars = estimate_phrase_length_bars(
            sub_curve.tolist(), bpm, hop_seconds=FRAME_HOP_S
        )

    # ── 6. Build structural candidates: (label, seg_start_frame, weight) ──
    # ``weight`` is the breakdown significance (or 1.0 for position cues) used as
    # the confidence label_margin proxy.
    candidates: list[tuple[str, int, float]] = []

    intro_frame = _first_sustained_frame(sub_curve, rms_curve)
    candidates.append(("intro", intro_frame, 1.0))

    outro_frame = _last_sustained_frame(rms_curve)
    candidates.append(("outro", outro_frame, 1.0))

    if dance_ok:
        # Normalize breakdown scores → [0,1] for label_margin.
        max_score = max((s for _, _, s in breakdowns), default=0.0) or 1e-6
        for kill, reentry, score in breakdowns:
            w = max(0.0, min(1.0, score / max_score))
            candidates.append(("breakdown", kill, w))
            candidates.append(("drop", reentry, w))
            # Optional build: the run right before the drop, if it is rising
            # (sub recovering toward the kick-back). Precision over coverage —
            # skip if unsure. We place a build a phrase before the reentry only
            # when there is room between the kill and the reentry for a lift.
            if bar_s > 0.0:
                build_frame = reentry - round(
                    _WINDOW_BARS["build"] * bar_s / FRAME_HOP_S
                )
                if kill < build_frame < reentry:
                    seg = sub_curve[build_frame:reentry]
                    if seg.size >= 2 and float(seg[-1]) > float(seg[0]) + 1e-4:
                        candidates.append(("build", build_frame, 0.5 * w))

    # ── 7. Mixable windows + confidence per candidate ──
    edge_frames = list(kills) + list(reentries) + [k for k, _, _ in breakdowns] + [
        r for _, r, _ in breakdowns
    ]
    anchors: list[tuple[CueAnchor, float]] = []  # (anchor, priority_score)
    for label, seg_frame, weight in candidates:
        seg_start_s = max(0.0, seg_frame * FRAME_HOP_S)
        if seg_start_s >= duration_s:
            continue

        # start_s = phrase-aligned downbeat at the candidate frame; capture grid_conf.
        start_s, grid_conf = _snap_to_phrase_grid(
            seg_start_s, samples, ANALYSIS_SR, bpm
        )
        start_s = min(max(0.0, start_s), max(0.0, duration_s - 1.0))

        # Window sizing: phrase-aligned target bars, capped by 80s + EOF.
        target_bars = _WINDOW_BARS.get(label, 16)
        if bar_s > 0.0 and phrase_bars > 0:
            max_phrases = math.floor(_MAX_WINDOW_S / bar_s / phrase_bars)
            bars = min(target_bars, max(phrase_bars, max_phrases * phrase_bars))
            window_s = bars * bar_s
        else:
            window_s = _MAX_WINDOW_S
        end_s = min(start_s + window_s, duration_s, start_s + _MAX_WINDOW_S)
        if end_s <= start_s:
            end_s = min(start_s + min(window_s, _MAX_WINDOW_S), duration_s)
        if end_s <= start_s:
            continue
        if (end_s - start_s) > _MAX_WINDOW_S:
            end_s = start_s + _MAX_WINDOW_S

        snapped = grid_conf >= _SNAP_CONF_MIN

        # Confidence factors:
        # boundary_salience — how deep the sub dropped here (breakdown depth) or a
        # baseline for position cues.
        boundary_salience = min(1.0, 0.5 + 0.5 * weight)
        # label_margin — the breakdown's normalized significance (position cues
        # get a fixed mid value).
        label_margin = min(1.0, 0.4 + 0.6 * weight)
        # method_agreement — the candidate frame corroborated by a real sub-edge
        # AND the phrase-grid snap. 1.0 when both corroborate, 0.5 baseline.
        near_edge = any(
            abs(round(start_s / FRAME_HOP_S) - f) <= 2 for f in edge_frames
        )
        method_agreement = 0.5 + (0.25 if near_edge else 0.0) + (
            0.25 if snapped else 0.0
        )
        conf = _confidence(
            boundary_salience, label_margin, grid_conf, method_agreement
        )

        # Priority for the max_cues cut: drop > breakdown > intro > outro > build.
        priority = {
            "drop": 0,
            "breakdown": 1,
            "intro": 2,
            "outro": 3,
            "build": 4,
        }.get(label, 5)
        anchors.append(
            (
                CueAnchor(
                    label=label,  # type: ignore[arg-type]
                    start_s=round(float(start_s), 3),
                    end_s=round(float(end_s), 3),
                    confidence=round(float(conf), 4),
                    source="fallback",
                ),
                float(priority) - conf,  # lower = keep first
            )
        )

    if not anchors:
        return []

    # Cap at max_cues by priority (structural first), then sort by time.
    anchors.sort(key=lambda x: x[1])
    chosen = [a for a, _ in anchors[:max_cues]]
    chosen.sort(key=lambda a: a.start_s)

    # Dedup any anchors that snapped to the same downbeat (within _DEDUP_S).
    deduped: list[CueAnchor] = []
    for anc in chosen:
        if deduped and abs(anc.start_s - deduped[-1].start_s) < _DEDUP_S:
            continue
        deduped.append(anc)
    return deduped
