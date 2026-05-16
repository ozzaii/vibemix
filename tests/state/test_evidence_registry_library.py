# SPDX-License-Identifier: Apache-2.0
"""Phase 25 Plan 25-02 — EvidenceRegistry.register_library coverage.

Wires the new ``register_library`` method against both a real
``RekordboxLibrary`` (parsing the synthetic fixture) and a duck-typed
SimpleNamespace so the registry stays decoupled from the library type.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.state.evidence_registry import EvidenceRegistry

FIXTURE = Path(__file__).parent.parent / "library" / "fixtures" / "synthetic_collection.xml"


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Keep the pickle cache out of ``~/.cache`` during this test module."""
    cache = tmp_path / "library.pkl"
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", cache)
    return cache


def test_register_library_writes_one_entry_per_track(isolated_cache):
    """5-track fixture → 5 keys under the ``track`` source after registration."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    registry = EvidenceRegistry()
    n = registry.register_library(lib)
    assert n == 5

    snapshot = registry.snapshot()
    assert set(snapshot["track"].keys()) == {"1", "2", "3", "4", "5"}


def test_registry_has_resolves_track_citations(isolated_cache):
    """``has("track", id, 0.0, tol=0.5)`` returns True for registered IDs."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    registry = EvidenceRegistry()
    registry.register_library(lib)

    assert registry.has("track", "1", 0.0, tol=0.5) is True
    assert registry.has("track", "5", 0.0, tol=0.5) is True
    assert registry.has("track", "999", 0.0, tol=0.5) is False


def test_register_library_with_duck_typed_object():
    """SimpleNamespace with ``.tracks: dict`` is enough — no real library needed."""
    fake = SimpleNamespace(tracks={"a": None, "b": None})
    registry = EvidenceRegistry()
    n = registry.register_library(fake)
    assert n == 2
    assert registry.has("track", "a", 0.0, tol=0.5)
    assert registry.has("track", "b", 0.0, tol=0.5)


def test_register_library_with_missing_tracks_attr_returns_zero():
    """Object without ``.tracks`` mapping → return 0; registry untouched."""
    registry = EvidenceRegistry()
    n = registry.register_library(object())
    assert n == 0
    # The registry's source dict for "track" should NOT have been created.
    snapshot = registry.snapshot()
    assert "track" not in snapshot


def test_register_library_idempotent_on_repeat_calls():
    """Re-registering the same library appends duplicate timestamps but ``has``
    still resolves — the read path is unaffected by duplicates.
    """
    fake = SimpleNamespace(tracks={"42": None})
    registry = EvidenceRegistry()
    registry.register_library(fake)
    registry.register_library(fake)
    assert registry.has("track", "42", 0.0, tol=0.5)
