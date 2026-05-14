# SPDX-License-Identifier: Apache-2.0
"""vibemix.events — composition tier for per-genre event detection.

Two distinct tiers per SENSE-15:

- ``vibemix/state/detectors/`` — the IMPLEMENTATION tier. Detector classes
  + shared band-limited DSP primitives (``_dsp.py`` for kick-side centroid +
  sub-share; ``_phrase_dsp.py`` for band-limited autocorr + downbeat lock +
  phrase-length self-similarity). Each detector is a stateful, single-tick
  class with a ``.detect(state, audio_buf, now) -> Event | None`` signature.

- ``vibemix/events/genres/`` — the COMPOSITION tier (this package). One
  builder function per genre that instantiates the right detectors with the
  right pair-wiring (``ReentryKickLandDetector(kill_detector=...)``,
  ``PhraseBoundaryDetector(kill_detector=...)``) and returns a flat list
  the GenreRouter iterates per ``.detect()`` call.

The ``GenreRouter`` (lives in ``vibemix.state.genre_router`` so it can stay
co-located with ``EventDetector``) wires them together at runtime. When
``state.active_genre`` flips, the router does an atomic chain swap — no
session restart, no in-flight detection interruption.

Why two tiers? The detectors are reusable building blocks (a Hard Tek track
slipped into a techno set still benefits from KickSwap). The composition
tier is where per-genre tuning lives — Plan 06 will land per-genre cooldown
overrides + threshold deltas in the chain builders without touching the
detector classes themselves.
"""
