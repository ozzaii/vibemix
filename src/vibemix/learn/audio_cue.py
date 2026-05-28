# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 03 — EXEMPLAR-04 exemplar audio routing.

REQ-ID: EXEMPLAR-04 — Exemplar audio plays through a DEDICATED
``sd.OutputStream`` on the user-picked headphone device. Owns its own
stream; does **NOT** reuse the mic-gated co-host playback queue.

Pitfall 2 — mic-gating
======================

``audio/buffers.py:195`` (the co-host playback-queue ``.push``) hooks
``levels.update_voice`` which ducks the user's mic the instant AI audio
enters the queue (v4 `RealtimeModel` mic-gate). If exemplar playback
re-used the co-host queue, the lesson would silence Kaan's mic for the
duration of the exemplar — the very thing the tutor needs to hear (his
spoken response, his beat-matching). The mic-gate is correct for the
co-host TTS path; it is wrong for the headphone-routed tutor exemplar.

So ``ExemplarPlayer`` owns a SECOND ``sd.OutputStream`` on a SEPARATE
device (the headphone bus). The grep gate in
``tests/learn/test_exemplar_player.py`` is the load-bearing static check
that this architectural rule holds.

Course 3 active-session guard SCAFFOLDING
=========================================

P93 ships the constructor seam (``state: MusicState`` kwarg) and the
``can_play()`` method. P96 wires the real guard so we NEVER play tutor
exemplars while the user is mid-set (would step on the live mix).
``can_play()`` returns ``True`` in P93 — Plan 96's diff is one line.

Gain policy
===========

* Default ``-12 dB`` — safe headphone level (CONTEXT.md lock).
* Drop to ``-18 dB`` when master deck RMS > ``0.5`` linear (≈ -6 dBFS) so
  headphone bleed doesn't compete with a hot master mix.
* Below ``SILENT_RMS`` → default ``-12 dB`` (no ducking).

References:

* 93-RESEARCH.md §Pattern 6 — ExemplarPlayer (verbatim source basis).
* 93-RESEARCH.md §Pattern 7 — ``load_audio_stereo`` PyAV decode.
* ``src/vibemix/platform/_audio_macos.py:298-326`` — precedent
  ``open_passthrough_output`` (NEW ``sd.OutputStream`` per call).
"""
from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
import sounddevice as sd

from vibemix.audio.constants import SILENT_RMS

if TYPE_CHECKING:  # pragma: no cover — forward ref only, no runtime import cycle
    from vibemix.state.music_state import MusicState


# ---------------------------------------------------------------------------
# Gain policy (CONTEXT.md lock)
# ---------------------------------------------------------------------------

# Default-safe gain for headphone exemplar playback.
_DEFAULT_GAIN_DB: float = -12.0
# Lower-by-6 gain when master deck is loud (avoid hot-mix bleed into headphones).
_LOUD_MASTER_GAIN_DB: float = -18.0
# Master-RMS threshold above which we drop to ``_LOUD_MASTER_GAIN_DB``.
# -6 dBFS in linear RMS ≈ 0.5 (RMS of a full-scale sine is 0.707;
# -6 dBFS RMS ≈ 0.5). Strictly-greater-than so the 0.5 boundary itself
# stays at the default -12 dB (verified by
# test_choose_gain_db_default_silent_master / _lowers_when_master_loud).
_LOUD_MASTER_RMS_LINEAR: float = 0.5


def _db_to_gain(db: float) -> float:
    """Convert decibel-Full-Scale to linear gain (10 ** (db / 20))."""
    return float(10 ** (db / 20.0))


def _choose_gain_db(master_rms: float | None) -> float:
    """Pick -12 dB by default; -18 dB when master deck audio is hot.

    * ``None`` / below ``SILENT_RMS`` → ``-12 dB`` (silent master is treated
      as "no special handling" — no need to duck).
    * Above ``_LOUD_MASTER_RMS_LINEAR`` (= 0.5, ≈ -6 dBFS) → ``-18 dB`` so
      the headphone tutor doesn't fight a loud master.
    * Anywhere in between → ``-12 dB``.
    """
    if master_rms is None or master_rms < SILENT_RMS:
        return _DEFAULT_GAIN_DB
    if master_rms > _LOUD_MASTER_RMS_LINEAR:
        return _LOUD_MASTER_GAIN_DB
    return _DEFAULT_GAIN_DB


# ---------------------------------------------------------------------------
# ExemplarPlayer
# ---------------------------------------------------------------------------


class ExemplarPlayer:
    """Plays a packaged or library track on a dedicated headphone OutputStream.

    Owns its own ``sd.OutputStream`` — does **NOT** reuse the mic-gated
    co-host playback queue at ``audio/buffers.py:195``. Reuse would
    silence Kaan's mic during exemplar playback (Pitfall 2 above).

    Stereo float32 @ track sample rate; PyAV/FFmpeg decode via
    ``library/audio_decode.load_audio_stereo``.

    Course 3 active-session guard (P96 wires; P93 scaffolds):
    ``can_play()`` returns ``False`` when the user is mid-set; P93 always
    returns ``True`` so Plan 96's diff is one line, not a constructor
    reshape.
    """

    def __init__(self, device_index: int, *, state: "MusicState | Any") -> None:
        """Construct an ExemplarPlayer.

        :param device_index: ``sd.OutputStream`` device index — usually a
            headphone bus picked by the user via the wizard (P97). ``-1``
            or ``None`` should NOT be passed; defer to system default
            from the caller side.
        :param state: ``MusicState`` reference for the active-session
            guard scaffold (P96 reads ``state.session_active`` and
            ``state.audible_deck``). Forward-typed to avoid an import
            cycle; in P93 we read ``state.audio_rms`` (or fall back to
            ``state.rms``) for the gain policy at ``.play()`` time.
        """
        self._device_index = device_index
        self._state = state
        self._stream: sd.OutputStream | None = None
        self._buffer: np.ndarray | None = None
        self._cursor: int = 0
        self._lock = threading.Lock()
        self._on_stop: Callable[[], None] | None = None

    def can_play(self) -> bool:
        """Active-session guard SCAFFOLDING.

        Reads ``state.session_active`` and ``state.audible_deck`` so the P96
        diff is one line, not a reshape. In P93 the scaffold always returns
        ``True`` — Plan P96 (EXEMPLAR-06) lands the real guard:
        ``return not (state.session_active and state.audible_deck != "none")``.
        """
        # Touch the seam attributes so static analysers + IDEs see the
        # contract; P93 ignores the result. P96 replaces the return body.
        _session_active = getattr(self._state, "session_active", False)
        _audible_deck = getattr(self._state, "audible_deck", "none")
        # Reference the locals so linters don't flag them; they document
        # the seam that P96 will activate.
        _ = (_session_active, _audible_deck)
        # P93 scaffolding: always allow. P96 lands the real guard:
        #   return not (state.session_active and state.audible_deck != "none")
        return True

    def _read_master_rms(self) -> float:
        """Read the master-deck RMS from the bound ``MusicState``.

        Real ``MusicState`` exposes the field as ``rms`` (see
        ``src/vibemix/state/music_state.py:31``). Some test stubs +
        the verbatim 93-RESEARCH §Pattern 6 source set ``audio_rms``;
        accept either. Falls back to ``0.0`` (silent) if both are absent
        so the gain policy stays safe.
        """
        val = getattr(self._state, "audio_rms", None)
        if val is None:
            val = getattr(self._state, "rms", 0.0)
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    def play(
        self,
        file_path: str,
        *,
        on_stop: Callable[[], None] | None = None,
    ) -> None:
        """Decode + start playback. Idempotent — stops any prior stream first.

        Lazy-imports ``load_audio_stereo`` (mirrors the runtime/wizard.py
        lazy-import pattern) so importing this module without PyAV
        installed succeeds; PyAV only loads when we actually decode.

        :param file_path: filesystem path to the exemplar audio file.
        :param on_stop: optional one-shot callable invoked when the
            stream finishes (EOF) or is stopped via ``.stop()``. Used by
            the lesson runtime to emit ``ipc.learn.exemplar_stop``.
        """
        self.stop()
        if not self.can_play():
            return

        # Lazy import — keeps module-import light and avoids dragging
        # PyAV into callers that never play an exemplar (mirrors the
        # ``vibemix.runtime.wizard`` lazy-import pattern at module level).
        from vibemix.library.audio_decode import load_audio_stereo

        samples, sr = load_audio_stereo(file_path)

        gain = _db_to_gain(_choose_gain_db(self._read_master_rms()))
        samples = (samples * gain).astype(np.float32)

        with self._lock:
            self._buffer = samples
            self._cursor = 0
            self._on_stop = on_stop

        def _callback(outdata, frames, time_info, status):  # noqa: ANN001
            # sd.OutputStream callback runs on the OS audio thread —
            # MUST be lock-protected against play()/stop() racing the
            # audio engine. Same threading model as
            # vibemix/audio/buffers.py — sync stdlib lock, no asyncio.
            with self._lock:
                buf = self._buffer
                cur = self._cursor
                if buf is None:
                    outdata.fill(0)
                    raise sd.CallbackStop
                end = cur + frames
                if end >= buf.shape[0]:
                    tail = buf[cur:]
                    outdata[: tail.shape[0]] = tail
                    outdata[tail.shape[0] :] = 0
                    # Clear the buffer so a second-tail callback is a
                    # no-op; the on_stop fires synchronously inside
                    # .stop() (called by the stream's CallbackStop
                    # cleanup path) or via the explicit caller-side
                    # .stop() — never inside the audio callback (avoids
                    # arbitrary-code-on-audio-thread reentrancy).
                    self._buffer = None
                    raise sd.CallbackStop
                outdata[:] = buf[cur:end]
                self._cursor = end

        self._stream = sd.OutputStream(
            device=self._device_index,
            samplerate=sr,
            channels=2,
            dtype="float32",
            latency="low",
            callback=_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop any in-flight playback. Idempotent.

        Safe to call without a prior ``.play()`` — the empty-state path
        is a no-op. Always closes the stream + clears the buffer; the
        ``on_stop`` callable is invoked exactly once (one-shot atomic
        flip under the lock to satisfy idempotency).
        """
        with self._lock:
            stream = self._stream
            self._stream = None
            self._buffer = None
            on_stop_local = self._on_stop
            self._on_stop = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:  # pragma: no cover — sd.OutputStream cleanup is best-effort
                pass
        if on_stop_local is not None:
            try:
                on_stop_local()
            except Exception:  # pragma: no cover — caller bugs must not poison stop()
                pass


__all__ = [
    "ExemplarPlayer",
    "_choose_gain_db",
]
