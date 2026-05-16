# SPDX-License-Identifier: Apache-2.0
"""GenreRouter — atomic per-genre detector-chain dispatch (SENSE-11).

The router holds the active detector chain (a flat list returned by one of
the builders in ``vibemix.events.genres``) and swaps it atomically when
``state.active_genre`` changes mid-session. ``EventDetector`` consults the
router on every tick; the swap is a single attribute reassign, so a swap
mid-detect-call cannot leave a half-iterated chain (T-17-05-02 mitigation —
the swap happens at the TOP of ``EventDetector.detect`` BEFORE iteration).

Construct ONCE per session — chain detectors carry baseline state across
ticks (e.g. ``KickSwapDetector.prev_centroid_hz``,
``BreakdownKickKillDetector.last_kill_at``). Re-instantiation discards
those seeded baselines (T-17-05-04 mitigation). Plan 06's tuning harness
uses one router for the entire WAV scan.

Threat mitigations:
    - T-17-05-01 (Tampering): unknown genre string → fallback to "unknown"
      baseline + WARN log. No code execution path from the string value
      (registry is a dict lookup only).
    - T-17-05-02 (Repudiation): swap is a single attribute write. Any
      reader currently iterating ``self._chain`` keeps its local list
      reference — the next swap simply rebinds ``self._chain`` to a new
      list without mutating the old one.
    - T-17-05-04 (Denial of Service): idempotent swap (same genre = no-op,
      no chain re-instantiation). Document in this docstring + Test 4.
"""

from __future__ import annotations

import logging

# NOTE: GENRE_REGISTRY is imported LAZILY inside ``swap()`` rather than at
# module load. The registry's per-genre chain builders pull from
# ``vibemix.state.detectors`` — and the state package's ``__init__`` itself
# imports ``GenreRouter`` from this module. Importing the registry eagerly
# would create a circular import chain when an entry point starts at
# ``vibemix.events.genres`` (the partially-initialised state package would
# come back through ``hard_tek.build_hard_tek_chain``'s detectors import).
# Phase 30 SENSE-19 — see the lazy import inside ``swap()``.

logger = logging.getLogger(__name__)


class GenreRouter:
    """Atomically swappable per-genre detector chain.

    Construct ONCE per session. EventDetector calls ``swap(state.active_genre)``
    at the TOP of every ``.detect()`` call when the active_genre has changed,
    then iterates ``active_chain()``.

    Public attributes:
        current_genre: str — the genre name the active chain was built for.
            Always one of the keys in ``GENRE_REGISTRY``. An unknown
            ``swap(x)`` argument forces this back to ``"unknown"`` (NOT to
            ``x`` — refusing to register a chain we don't have).
    """

    def __init__(self, initial_genre: str = "unknown") -> None:
        self.current_genre: str = "unknown"
        self._chain: list = []
        # Seed the initial chain via swap() so the unknown-genre fallback
        # path is exercised on construction too.
        self.swap(initial_genre)

    def swap(self, new_genre: str) -> bool:
        """Swap the active detector chain to the one registered for
        ``new_genre``. Returns True if a swap actually happened, False if
        idempotent no-op (same genre, chain already built).

        Unknown ``new_genre`` (not in ``GENRE_REGISTRY``) → fallback to
        ``"unknown"`` baseline + WARN log. We refuse to register a chain
        we don't have rather than silently leave the old chain in place
        (which would be confusing — caller would see ``current_genre ==
        "dubstep"`` while still running the techno chain).

        Atomicity: two attribute writes (``self._chain`` then
        ``self.current_genre``). Python's GIL makes this effectively atomic
        from the point of view of any single ``.detect()`` reader (single-
        threaded asyncio runner — there's no concurrent swap anyway).
        """
        # Idempotent no-op — same genre AND chain is already built. Skip
        # re-instantiation so detector baselines stay seeded across "swap"
        # calls that aren't actually changing anything (T-17-05-04).
        if new_genre == self.current_genre and self._chain is not None:
            # Need to also handle the very-first swap from __init__: when
            # __init__ has not yet called swap, current_genre == "unknown"
            # and self._chain == []. Calling swap("unknown") needs to build
            # the (empty) chain. Detect this case via "first swap" — when
            # _chain has not been built yet for current_genre, we must run.
            # The simplest signal: check the registry. If the chain wasn't
            # seeded by a previous successful swap, we need to seed it now.
            # We track this with a simple sentinel — the _initialized flag.
            if getattr(self, "_initialized", False):
                return False

        # Lazy import — see module-level note. By the time swap() is called
        # the events.genres package is fully initialised so the import is
        # a cheap cached module lookup.
        from vibemix.events.genres import GENRE_REGISTRY

        builder = GENRE_REGISTRY.get(new_genre)
        if builder is None:
            logger.warning(
                "GenreRouter: unknown genre %r — falling back to 'unknown' baseline",
                new_genre,
            )
            new_genre = "unknown"
            builder = GENRE_REGISTRY["unknown"]

        # Atomic swap — two attribute writes, GIL-protected. _chain rebinds
        # to a new list; any concurrent reader keeps its local reference to
        # the old list (which is now garbage-collectable once they release).
        self._chain = builder()
        self.current_genre = new_genre
        self._initialized = True
        return True

    def active_chain(self) -> list:
        """Return the current detector chain. SHARED reference — callers
        MUST NOT mutate. EventDetector iterates it read-only."""
        return self._chain
