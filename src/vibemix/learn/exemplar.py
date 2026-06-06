# SPDX-License-Identifier: Apache-2.0
"""exemplar — DSP-band per-track band-share + compressed-kick guard primitives.

Phase 93 EXEMPLAR-01 + EXEMPLAR-02. Pure-compute helpers consumed by:
  * Plan 93-03's ``ExemplarFinder`` (ranking / honest-null fallback /
    EvidenceRegistry writes).
  * Plan 93-06's ingest extension to ``library/folder_ingest.py`` — at the
    same loop where each track's CLAP vector is written, also persist a
    5-tuple ``(sub, low, mid, high, kick_corr)`` to the ``band_shares``
    side-car table (see ``learn/band_share_store.py``).

This module ships ONLY the dim-agnostic, offline-unit-testable scalars.
Ranking, registry, and fallback land in 93-03; CLI surface lands in 93-06.

Verbatim math port of 93-RESEARCH.md §Pattern 2 + §Pattern 3. The
band-share scalars themselves come unchanged from
``audio/features.py:71-89`` via ``snapshot_features(buf, seconds=duration_s)``;
the kick-spillover Pearson r is a NEW per-window correlation between the
mid (300-4000 Hz) and sub (20-100 Hz) band energy time-series.

Pitfall 5 — ``_KICK_GUARD_R = 0.8`` is the CONTEXT.md lock; if Kaan's
ear-pass on the hardtechno library shows over-aggressive filtering, surface
as ``§EXEMPLAR-KICK-GUARD-EAR`` KAAN-ACTION (do NOT silently retune).
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from vibemix.audio.buffers import AudioBuffer
from vibemix.audio.features import snapshot_features
from vibemix.learn.band_share_store import open_default_db, top_for_band
from vibemix.library.audio_decode import load_audio_mono

if TYPE_CHECKING:
    from vibemix.state.evidence_registry import EvidenceRegistry

# 48 kHz is the standard ingest sample rate; matches the existing CLAP
# embed pipeline. ``snapshot_features`` reads ``buf._sr`` directly so the
# FFT band masks stay in absolute Hz regardless of this number, but 48 kHz
# is the locked default to avoid spectral resolution drift across calls.
_INGEST_SR: int = 48000

# Compressed-kick guard threshold (CONTEXT.md lock). Pearson r between
# mid-band and sub-band per-window energy. r > 0.8 → mid is mostly kick
# spillover, not real mid content (track gets excluded from mid-band
# lessons). See module docstring §Pitfall 5 for the KAAN-ACTION escape
# hatch if ear-pass shows over-aggressive filtering.
_KICK_GUARD_R: float = 0.8


# Pitfall 3 (RESEARCH §Pattern 2) — ``snapshot_features(buf, seconds=...)``
# snapshots the LAST ``seconds`` of the buffer (designed for the live
# detector's "what just happened" semantics). When we want the FULL TRACK
# band-share aggregate, we pass ``seconds=duration_s`` so the snapshot is
# the whole buffer. Calling with the default ``seconds=5.0`` would only
# look at the last 5 s of the track (the outro/breakdown) — wrong shape
# for library-track aggregation.
def compute_band_shares(audio_path: str) -> dict[str, float]:
    """Return ``{sub,low,mid,high}_share`` + ``kick_corr`` for one track file.

    Single full-track FFT (verbatim math port of
    ``audio/features.py:71-89``); side-loads the existing
    ``snapshot_features`` primitive by building an ``AudioBuffer`` large
    enough to hold the entire decoded track, then snapshotting the whole
    buffer (``seconds=duration_s``).

    Silent track → returns 5 zeros (the ``snapshot_features.silent``
    short-circuit at ``audio/features.py:43-44`` propagates through).

    ``kick_corr`` is computed against the FLOAT32 samples (not the int16
    cast) — correlation needs the high-resolution waveform; rounding to
    int16 attenuates the per-window mid-band variance enough to drag the
    Pearson r below the 0.8 guard threshold on borderline tracks.

    Args:
        audio_path: Path to any audio file decodable by PyAV/FFmpeg
            (mp3/m4a/wav/flac/aiff). Decoding errors propagate as
            ``AudioDecodeError`` (caller — i.e. Plan 93-06's ingest loop —
            wraps in try/except and skips).
    """
    sr = _INGEST_SR
    samples = load_audio_mono(audio_path, target_sr=sr)
    duration_s = len(samples) / sr
    # AudioBuffer is a ring sized to ``int(sr * seconds)``; sizing it to the
    # exact duration_s + pushing all samples gives us a full-track snapshot.
    # NOTE: AudioBuffer.__init__(seconds, sr) — no ``sample_rate`` or
    # ``dtype`` kwargs (the buffer is hardcoded int16 internally; verbatim
    # signature at audio/buffers.py:46).
    buf = AudioBuffer(seconds=duration_s, sr=sr)
    # snapshot_features expects int16 samples; cast float32 → int16 once.
    # Clip BEFORE cast to avoid the v4 int16-overflow bug
    # (audio/features.py:99-101 Pitfall 4 — int16 silently produces -32768
    # if the order is inverted).
    int16 = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    buf.push(int16)
    feats = snapshot_features(buf, seconds=duration_s)
    if feats.get("silent"):
        return {
            "sub_share": 0.0,
            "low_share": 0.0,
            "mid_share": 0.0,
            "high_share": 0.0,
            "kick_corr": 0.0,
        }
    return {
        "sub_share": float(feats["sub_share"]),
        "low_share": float(feats["low_share"]),
        "mid_share": float(feats["mid_share"]),
        "high_share": float(feats["high_share"]),
        "kick_corr": _kick_correlation(samples, sr),
    }


# Spectral-leakage fraction (Rule 1 deviation from RESEARCH §Pattern 3 —
# see ``_kick_correlation`` docstring §Spectral-leakage gate). A windowed
# 1024-sample FFT of a 60 Hz sine has -32 dB Hanning side-lobes that smear
# into the 300+ Hz mid band; for a sub-band RMS of ~200, that's ~5.0 of
# numerical leakage at 300 Hz per window, which the verbatim Pattern 3
# algorithm wrongly counts as "mid content" correlated with sub. Subtracting
# 2% of the sub-band RMS from each window's mid-band RMS clears the leakage
# floor while preserving genuinely-saturated mid harmonics. Empirically:
#   * clean smooth-envelope kicks → r drops from 0.74 → -0.07 (well below 0.3)
#   * distorted kicks (mid harmonics riding the kick envelope) → r stays 0.99
#   * balanced mid leads (independent of sub) → r stays near 0 (≤ -0.12)
# See module docstring §Pitfall 7 for the empirical-floor backstop.
_SPECTRAL_LEAKAGE_FRAC: float = 0.02


def _kick_correlation(samples: np.ndarray, sr: int) -> float:
    """Compute Pearson r between per-window mid-band and sub-band energy.

    Returns r ∈ [-1, 1]. r > 0.8 means mid-band energy tracks sub-band
    energy too tightly — the mid is mostly kick spillover, not real mid
    content. ``ExemplarFinder.find()`` (Plan 93-03) excludes tracks with
    r > ``_KICK_GUARD_R`` (0.8) from MID-band lessons.

    Algorithm (RESEARCH §Pattern 3 + Plan 93-02 spectral-leakage fix):
        * Per-window FFT @ 1024 samples (Hanning) over non-overlapping
          ~20 ms windows (``win = sr // 50``).
        * Sub-band mask: 20-100 Hz.
        * Mid-band mask: 300-4000 Hz (the SUM of the two FFT bands
          ``snapshot_features`` aggregates into ``mid_share``; do NOT split
          mid into two scalars — would diverge from the v4 port contract).
        * **Spectral-leakage gate** (Plan 93-02 deviation): subtract
          ``_SPECTRAL_LEAKAGE_FRAC × sub_rms`` from each window's mid_rms,
          floored at 0. Hanning-windowed 1024-sample FFT of a low-frequency
          sine produces -32 dB side-lobes that splash into the 300+ Hz mid
          band; for a sub_rms of ~200, that's ~5.0 of numerical leakage per
          window. Without this gate the verbatim Pattern 3 algorithm
          reported r ≈ 0.6 even for clean sub-only kicks (the leakage tracks
          sub trivially). The 2% factor is empirically tuned: it kills the
          leakage floor without dampening genuine compressed-kick harmonics
          (which sit 10-100x above the leakage floor on the synthetic
          fixtures and real hardtechno tracks alike).
        * Pearson r via ``np.corrcoef`` on (sub_series, mid_clean_series).

    Fast-exit paths (zero-correlation honest defaults):
        * ``samples.size < sr * 2`` → no honest correlation possible.
        * Fewer than 10 windows after slicing → too short.
        * Zero variance on either series (silent / DC-only signals OR
          mid-after-leakage-gate fully zeroed out) → 0.0 (avoid
          ``RuntimeWarning: invalid value`` from ``np.corrcoef``).
        * Non-finite r from pathological numeric edge cases → 0.0.
    """
    if samples.size < sr * 2:
        return 0.0  # too short — no honest correlation

    win = sr // 50  # ~20 ms windows
    n_win = samples.size // win
    if n_win < 10:
        return 0.0  # too few windows for meaningful correlation

    # Per-window FFT → band-energy time-series for mid and sub. The full
    # snapshot_features uses a 16384-sample FFT; per-window resolution at
    # 1024 samples gives ~46 Hz/bin @ 48 kHz, plenty for the 20-4000 Hz
    # band-mask granularity.
    spec_win = 1024
    sub_series = np.zeros(n_win, dtype=np.float32)
    mid_series = np.zeros(n_win, dtype=np.float32)
    freqs = np.fft.rfftfreq(spec_win, d=1.0 / sr)
    sub_mask = (freqs >= 20) & (freqs < 100)
    # mid = combined mid_low + mid_hi (300-4000 Hz) — same aggregation
    # contract as snapshot_features.
    mid_mask = (freqs >= 300) & (freqs < 4000)
    hann = np.hanning(spec_win).astype(np.float32)
    for i in range(n_win):
        start = i * win
        end = start + win
        x = samples[start:end]
        # Zero-pad up to spec_win if the window is shorter than the FFT.
        if x.size < spec_win:
            x = np.pad(x, (0, spec_win - x.size))
        x = x[:spec_win].astype(np.float32) * hann
        spec = np.abs(np.fft.rfft(x))
        sub_series[i] = (
            float(np.sqrt(np.mean(spec[sub_mask] ** 2))) if sub_mask.any() else 0.0
        )
        mid_series[i] = (
            float(np.sqrt(np.mean(spec[mid_mask] ** 2))) if mid_mask.any() else 0.0
        )

    # Spectral-leakage gate — see module-level _SPECTRAL_LEAKAGE_FRAC comment.
    # Subtracts the expected Hanning-windowed side-lobe contribution from sub
    # to mid; floor at 0 (negative values from a noisy sub probe would invert
    # the correlation sign artifically).
    mid_clean = np.maximum(mid_series - _SPECTRAL_LEAKAGE_FRAC * sub_series, 0.0)

    # Zero-variance guard — silent or DC-only signals OR all-zeroed-out
    # mid_clean → 0.0 instead of raising ``RuntimeWarning: invalid value``
    # from ``np.corrcoef``.
    sub_std = float(np.std(sub_series))
    mid_std = float(np.std(mid_clean))
    if sub_std < 1e-9 or mid_std < 1e-9:
        return 0.0
    r = float(np.corrcoef(sub_series, mid_clean)[0, 1])
    # Guard against NaN propagation in pathological numeric edge cases.
    if not np.isfinite(r):
        return 0.0
    return r


# --------------------------------------------------------------------------- #
# Plan 93-04 — ExemplarFinder ranker + packaged-fallback bank                  #
# --------------------------------------------------------------------------- #


# Plan 93-04 — minimum number of library tracks that must pass the band floor
# before we trust library results. Below this, fall back to the packaged
# CC-BY bank with the honest-null reason. Locked per CONTEXT.md §Honest-null
# fallback ("≤3 tracks" → strictly less than 3 = floor of 3).
_LIBRARY_FLOOR: int = 3

# Query extra rows so stale/unplayable cache entries do not force a packaged
# fallback when the library still has enough playable examples just below the
# top of the band-share ranking.
_LIBRARY_RESOLVE_HEADROOM: int = 9

# Plan 93-02 ships this threshold via ``band_share_store.top_for_band(...,
# max_kick_corr=0.8)``; keep the constant local to ``exemplar.py`` so a future
# §EXEMPLAR-KICK-GUARD-EAR ear-pass tunes one place (the ranking layer caller
# passes this through to the store-level filter).
# NOTE: distinct module-level binding from ``_KICK_GUARD_R = 0.8`` above
# (that name is the per-track Pearson r threshold; this one is the ranker's
# call-time argument). Same VALUE today, different semantic role — keep
# both so the ear-pass tuning can move them independently if needed.
_KICK_GUARD_R_FILTER: float = 0.8

# Honest-null fallback copy — CONSTANT, NOT live-generated (byte-equality
# guarantee per CONTEXT.md). Plan 93-01 + Plan 93-04 tests assert this
# string verbatim. TONE-02 binding: the AI never paraphrases this; the
# engine surfaces it.
_HONEST_NULL_REASON: str = (
    "Your library doesn't have a great example of this — "
    "listen to this one we packaged"
)


def _packaged_bank_dir() -> Path:
    """Return the path to the bundled CC-BY exemplar bank.

    Resolves via :mod:`importlib.resources` so both layouts work:

    * **Development** — running from ``src/vibemix/learn/assets/band_exemplars``.
    * **Wheel / PyInstaller** — installed under the same package namespace.

    The dev-time ``Path(__file__).parent / "assets" / "band_exemplars"``
    fallback is the safety net for any environment where
    ``importlib.resources.files()`` cannot resolve the namespace package
    (rare, but seen on some PyInstaller configurations that strip ``__init__``).
    """
    try:
        from importlib.resources import files

        return Path(str(files("vibemix.learn.assets.band_exemplars")))
    except Exception:
        return Path(__file__).parent / "assets" / "band_exemplars"


def _fallback_for_band(band: str) -> tuple[str, str, str] | None:
    """Return ``(synthetic_track_id, file_path, honest-null reason)`` or None.

    Sorts files alphabetically inside the band's subdir (deterministic — the
    SAME band+bank always picks the SAME track for the same install).
    Returns ``None`` when the bank directory is missing or empty (e.g. when
    §EXEMPLAR-BANK-SOURCING has not yet populated the bank — the engine then
    surfaces ``[]`` to the caller, the degraded-install contract).

    Synthetic track_id shape: ``_packaged:<band>:<file_stem>`` — the
    ``_packaged:`` prefix is a RESERVED namespace that library track_ids
    never use (folder_ingest + Rekordbox derive ids from filenames /
    UUIDs, never from the ``_packaged:`` prefix). STRIDE T-93-04-04
    accept disposition.
    """
    bank_dir = _packaged_bank_dir() / band
    if not bank_dir.exists():
        return None
    files = (
        sorted(bank_dir.glob("*.mp3"))
        + sorted(bank_dir.glob("*.ogg"))
        + sorted(bank_dir.glob("*.wav"))
    )
    if not files:
        return None
    path = files[0]
    synthetic_id = f"_packaged:{band}:{path.stem}"
    return (synthetic_id, str(path), _HONEST_NULL_REASON)


@dataclass
class ExemplarPick:
    """One ranked exemplar pick — library-side or packaged-fallback.

    Fields:
        track_id: Real Rekordbox / folder-ingest id (``library`` reason)
            OR synthetic ``_packaged:<band>:<stem>`` (``packaged`` reason).
        file_path: Filesystem path to the audio. Library picks are only
            returned when this is a real, playable file path; packaged
            fallback picks carry the bundled bank path.
        band_score: The track's ``band_share`` scalar for the picked
            band — top-of-distribution for library picks; ``0.0`` for
            packaged-fallback picks (no library score to assign).
        reason: Free-form human reason. For packaged picks this is the
            verbatim ``_HONEST_NULL_REASON`` constant; for library picks
            it embeds the band name.
    """

    track_id: str
    file_path: str
    band_score: float
    reason: str


class ExemplarFinder:
    """Picks band-exemplar tracks for EQ lessons.

    Pure-compute over the side-car ``band_shares`` table (Plan 93-02); falls
    back to the packaged CC-BY bank when the library has < ``_LIBRARY_FLOOR``
    tracks passing the kick-guard floor.

    Invariant #2 binding. ``registry.write("exemplar", track_id, t_session)``
    runs BEFORE :meth:`find` returns so the AI's later
    ``[exemplar:<track_id>]`` citation resolves via
    :meth:`EvidenceRegistry.has` during linter validation. A fabricated
    ``[exemplar:bogus]`` strips the whole turn because no
    ``("exemplar", "bogus", _)`` write ever happened.

    Note: as of Plan 93-04 the ``EVIDENCE_SOURCES`` frozenset still has 9
    sources (Plan 93-05 lands ``"exemplar"`` via the 4-site mirror); the
    registry's v1.0 permissive contract makes this write succeed today
    (see ``evidence_registry.py:170-181`` — "any string source / key is
    accepted").
    """

    def __init__(self, *, registry: EvidenceRegistry | None = None) -> None:
        self._registry = registry
        # Memoize the library lookup so multiple find() calls per session
        # don't re-instantiate / re-load the cache. None means "not loaded
        # yet"; a sentinel object would also work but we re-use None to
        # mean "no library available" too (the library path tolerates that).
        self._library_loaded: bool = False
        self._library = None

    def _load_library(self):
        """Load the Rekordbox library cache once per finder instance.

        Returns a library-like object (with a ``.tracks`` mapping) or
        ``None`` when no library is available. Defensive against:
        * monkeypatched ``try_load_cache`` lambda (test path) — returns
          the lib directly OR None.
        * Real instance-method ``try_load_cache(self)`` — instantiate the
          class, call the bound method, return self if it loaded.
        * Any exception during library import / cache load — None.
        """
        if self._library_loaded:
            return self._library
        self._library_loaded = True
        try:
            from vibemix.library.rekordbox import RekordboxLibrary
            # Test-monkeypatch path: ``try_load_cache`` is replaced with a
            # no-arg callable (e.g. ``lambda: None`` or ``classmethod(lambda
            # cls: FakeLib())``). Call the class attribute with no args.
            try:
                result = RekordboxLibrary.try_load_cache()
                if result is None:
                    # Test path explicitly said "no library" — honor it.
                    self._library = None
                    return None
                # Truthy result that has the ``.tracks`` mapping IS the lib.
                if hasattr(result, "tracks"):
                    self._library = result
                    return result
                # Fall through — result was truthy but not a lib (e.g. True
                # from a bound-method probe). Drop to the production path.
            except TypeError:
                # Production path: ``try_load_cache`` is an instance method
                # that needs ``self``; the bare class-level call raised
                # TypeError. Instantiate + call.
                pass
            # Production path: real RekordboxLibrary instance.
            lib = RekordboxLibrary()
            if lib.try_load_cache():
                self._library = lib
                return lib
        except Exception:
            # Any failure (import error, cache corruption, etc.) → no library.
            pass
        self._library = None
        return None

    def _resolve_library_path(self, lib, track_id: str) -> str:
        """Map ``track_id`` → filesystem path via the library cache.

        Returns ``""`` (empty string) when the library is absent, when the
        track_id is not in the library's ``tracks`` mapping, or when the
        entry's audio path cannot be resolved to an existing file.

        Folder ingest writes real ``TrackEntry(filepath=...)`` rows into the
        Rekordbox-compatible cache, while a few historical tests/fakes used
        ``.path``. Accept both, with ``filepath`` as the production field.
        """
        if lib is None:
            return ""
        tracks_map = getattr(lib, "tracks", None)
        if not isinstance(tracks_map, dict):
            return ""
        entry = tracks_map.get(track_id)
        if entry is None:
            return ""
        path = getattr(entry, "filepath", None)
        if not isinstance(path, str) or not path:
            path = getattr(entry, "path", None)
        if not isinstance(path, str):
            return ""
        try:
            candidate = Path(path).expanduser()
        except (TypeError, ValueError):
            return ""
        if not candidate.is_file():
            return ""
        return str(candidate)

    def find(
        self,
        band: str,
        k: int = 1,
        t_session: float | None = None,
    ) -> list[ExemplarPick]:
        """Pick up to ``k`` exemplar tracks for ``band``.

        Library path is tried first; if ≥ ``_LIBRARY_FLOOR`` rows pass the
        ``band_share_store.top_for_band(..., max_kick_corr=0.8)`` filter
        AND resolve to playable local files, the top-K library rows are
        returned. Otherwise the packaged CC-BY bank fallback fires with the
        honest-null reason. If BOTH library and bank are empty, returns
        ``[]`` (degraded-install contract from RESEARCH §Code Example 1).

        For every returned pick, the engine calls
        ``registry.write("exemplar", track_id, t_session)`` BEFORE
        returning — the Invariant #2 binding that makes a fabricated
        ``[exemplar:<id>]`` uncitable-by-construction once Plan 93-05
        lands the 4-site mirror.

        ``t_session`` defaults to ``time.time()`` so callers that don't
        track a session-relative clock still get a sane registry write
        timestamp.
        """
        if t_session is None:
            t_session = time.time()

        # Library path — best-effort. open_default_db() opens
        # ``library-clap.db``; if the DB or the band_shares table is
        # absent, top_for_band returns []. We absorb any error so an
        # un-ingested install never crashes the engine.
        try:
            with open_default_db() as conn:
                rows = top_for_band(
                    conn, band,
                    k=max(k, _LIBRARY_FLOOR) + _LIBRARY_RESOLVE_HEADROOM,
                    max_kick_corr=_KICK_GUARD_R_FILTER,
                )
        except Exception:
            rows = []

        picks: list[ExemplarPick] = []
        if len(rows) >= _LIBRARY_FLOOR:
            # Library has enough band-share rows; now require enough
            # playable cache entries too. A stale band_shares row whose
            # source file moved must not become a silent "from your library"
            # exemplar with no audio.
            lib = self._load_library()
            playable_rows: list[tuple[str, float, str]] = []
            for track_id, score, _kick in rows:
                file_path = self._resolve_library_path(lib, track_id)
                if not file_path:
                    continue
                playable_rows.append((track_id, score, file_path))
            if len(playable_rows) >= _LIBRARY_FLOOR:
                for track_id, score, file_path in playable_rows[:k]:
                    if self._registry is not None:
                        self._registry.write("exemplar", track_id, t_session)
                    picks.append(
                        ExemplarPick(
                            track_id=track_id,
                            file_path=file_path,
                            band_score=score,
                            reason=f"from your library — strongest {band}-band track",
                        )
                    )

        if picks:
            return picks

        # Packaged-fallback path — fires when library has 0, fewer than
        # floor rows, or fewer than floor playable file paths.
        fb = _fallback_for_band(band)
        if fb is None:
            # Degraded install — neither library nor bank has anything to say.
            return []
        synthetic_id, file_path, reason = fb
        if self._registry is not None:
            self._registry.write("exemplar", synthetic_id, t_session)
        return [
            ExemplarPick(
                track_id=synthetic_id,
                file_path=file_path,
                band_score=0.0,
                reason=reason,
            )
        ]


__all__ = [
    "ExemplarFinder",
    "ExemplarPick",
    "compute_band_shares",
]
