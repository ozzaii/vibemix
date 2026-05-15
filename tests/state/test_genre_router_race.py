# SPDX-License-Identifier: Apache-2.0
"""GenreRouter MappingProxyType + 1000-cycle threaded race regression
(Phase 30 SENSE-19 / Pitfall P49).

P49 was: an early refactor allowed runtime ``GENRE_REGISTRY[g] = builder``
registration, which broke the atomic-swap contract — a swap mid-detect-call
could observe a half-mutated registry. The fix: ``GENRE_REGISTRY`` is now a
``types.MappingProxyType`` (immutable view of a module-private dict). The
1000-cycle race test below pins the atomic-swap guarantee under heavy
concurrent read pressure.

Anti-flake budget: 8 reader threads × 1000 swaps completes in ~50ms on a
modern laptop. The join timeout (5s) is generous against the worst CI box
we've seen.
"""

from __future__ import annotations

import threading

import pytest

from vibemix.events.genres import GENRE_REGISTRY
from vibemix.state.genre_router import GenreRouter


def test_genre_registry_is_immutable_mapping():
    """P49 mitigation pinning — runtime mutation of GENRE_REGISTRY raises
    TypeError. The only legitimate way to add a genre is to edit
    ``vibemix/events/genres/__init__.py`` + release."""
    with pytest.raises(TypeError):
        GENRE_REGISTRY["dubstep"] = lambda: []  # type: ignore[index]

    # Same for deletion + clear.
    with pytest.raises(TypeError):
        del GENRE_REGISTRY["unknown"]  # type: ignore[attr-defined]


def test_genre_registry_has_known_keys():
    """Sanity: MappingProxyType doesn't drop entries. The 4 known genres
    must remain accessible after the immutability refactor."""
    assert set(GENRE_REGISTRY.keys()) == {"unknown", "house", "techno", "hard_tek"}


def test_genre_router_1000_cycle_concurrent_swap_no_race():
    """8 reader threads iterate ``active_chain()`` while the main thread
    swaps between hard_tek and techno 1000 times. Neither the reads nor
    the swaps must raise, and the final state must be one of the swapped
    genres.

    Atomicity contract (T-17-05-02): ``router._chain`` rebinds to a fresh
    list on every swap. Concurrent readers keep their local reference to
    the old list (now garbage-collectable). No half-iterated chain is
    ever observable.
    """
    router = GenreRouter()
    router.swap("hard_tek")

    stop = threading.Event()
    errors: list[BaseException] = []
    read_count = [0]
    read_lock = threading.Lock()

    def reader() -> None:
        try:
            local_count = 0
            while not stop.is_set():
                chain = router.active_chain()
                # Iterate it the way EventDetector.detect does — touching
                # every detector forces the reference to live across the
                # loop body (anti-optimisation guard).
                for _ in chain:
                    pass
                local_count += 1
            with read_lock:
                read_count[0] += local_count
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=reader, daemon=True) for _ in range(8)]
    for t in threads:
        t.start()

    try:
        for i in range(1000):
            router.swap("techno" if i % 2 else "hard_tek")
    finally:
        stop.set()
        for t in threads:
            t.join(timeout=5.0)

    assert not errors, f"Race test surfaced errors: {errors!r}"
    # Final state must be one of the two genres we swapped to.
    assert router.current_genre in ("techno", "hard_tek")
    # Sanity: readers actually ran (caught early no-op deadlock).
    assert read_count[0] > 0


def test_genre_router_chain_immutable_during_iteration():
    """A swap mid-iteration must not mutate the list the iterator is
    holding. Captures the same atomic-rebind contract from a single-
    threaded vantage point."""
    router = GenreRouter()
    router.swap("hard_tek")
    chain_before = router.active_chain()
    n_before = len(chain_before)

    # Simulate "mid-iteration" by taking the reference, then swapping,
    # then continuing to inspect what we held.
    router.swap("house")
    assert len(chain_before) == n_before, "old chain reference was mutated by swap"
    # The router's *new* chain is the house chain, distinct list object.
    assert router.active_chain() is not chain_before
