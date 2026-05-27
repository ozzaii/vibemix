---
plan: 30-03
phase: 30-2-hard-tek-detectors-distortion-climb-acid-line-entry
status: complete
wave: 2
requirements: [SENSE-19, P49]
commits:
  - f0bb581 # feat(30-03): GenreRouter MappingProxyType + 1000-cycle race test (SENSE-19)
tasks_completed: 1/1
tests_added: 4
tests_passing: 4/4
regression_check: pytest tests/state/test_genre_router_race.py → 4/4 in ~0.6s; full Phase-30 suite → 45/45
hard_gate: 1000-cycle race test → PASSED
---

# Plan 30-03 Summary — GenreRouter MappingProxyType + race test

## What was built

`GENRE_REGISTRY` is now an immutable `types.MappingProxyType` view over the private `_GENRE_REGISTRY_RAW` dict. No runtime `register_detector()` exists (confirmed in research) — and now no caller can mutate `GENRE_REGISTRY[...]` either. Closes P49 (atomic-swap break risk).

### Refactor (`src/vibemix/events/genres/__init__.py`)

```python
from types import MappingProxyType

_GENRE_REGISTRY_RAW: dict[str, Callable[[], list]] = {
    "unknown":  build_baseline_chain,
    "house":    build_house_chain,
    "techno":   build_techno_chain,
    "hard_tek": build_hard_tek_chain,
}
GENRE_REGISTRY: MappingProxyType[str, Callable[[], list]] = MappingProxyType(_GENRE_REGISTRY_RAW)
```

`_GENRE_REGISTRY_RAW` is module-private — the only place mutation could happen. Public `GENRE_REGISTRY` is read-only at the type-system level.

### Hard gate — 1000-cycle race test (`tests/state/test_genre_router_race.py`)

`test_genre_router_1000_cycle_concurrent_swap_no_race`:
- 8 reader threads iterate `active_chain()` continuously.
- Main thread swaps `hard_tek <-> techno` 1000 times.
- Assertion surface: zero raised exceptions, zero half-state observable, final genre is one of the two swapped to, all reader iterations completed without `RuntimeError: dictionary changed size during iteration` (the textbook race).

**Mechanism:** `router._chain` is *rebound* (atomic CPython attribute swap), never *mutated*. Readers holding the old list reference iterate it safely; new readers see the new chain. Together with the immutable registry, this gives the lock-free atomic-swap pattern P49 required.

`test_genre_router_chain_immutable_during_iteration`: single-threaded confirmation that swap mid-iteration doesn't mutate the list the iterator is holding.

## Test surface

| File | Tests | Coverage |
|------|-------|----------|
| test_genre_router_race.py | 4 | `MappingProxyType` immutability assertion; known-keys check; 1000-cycle threaded race; single-threaded mid-iteration swap safety |

**Total: 4 tests, 4 pass (~0.6s incl. 1000-cycle race).**

## Self-Check: PASSED

- [x] `GENRE_REGISTRY` is `MappingProxyType` — `TypeError` on item assignment.
- [x] 1000-cycle threaded race never raises; final state is consistent.
- [x] No call sites broke (read access through `MappingProxyType` is dict-compatible).
- [x] Atomic-swap pattern P49 closed.

## What this unblocks

- Hard Tek + future genre chains can be safely re-bound at runtime without lock contention.
- Phase 31+ can rely on `GENRE_REGISTRY` as a frozen registry surface.
