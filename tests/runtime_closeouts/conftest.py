# SPDX-License-Identifier: Apache-2.0
"""Phase 27 runtime close-out shared fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from vibemix.library.rekordbox import RekordboxLibrary
    from vibemix.state.evidence_registry import EvidenceRegistry


@pytest.fixture
def synthetic_library_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a synthetic library.pkl at a tmp_path-rooted ~/.cache/vibemix/.

    monkeypatches ``pathlib.Path.home`` to return ``tmp_path`` so the
    27-05 wire-in's ``Path.home() / ".cache" / "vibemix" / "library.pkl"``
    resolves under tmp_path. Returns the cache file path.
    """
    cache_dir = tmp_path / ".cache" / "vibemix"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "library.pkl"
    cache_path.write_bytes(b"placeholder pickle bytes - try_load_cache mocked in tests")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return cache_path


@pytest.fixture
def synthetic_library() -> "RekordboxLibrary":
    """A RekordboxLibrary with one synthetic TrackEntry preloaded.

    Uses the ACTUAL Track API (per src/vibemix/library/rekordbox.py:70):
    TrackEntry(track_id, title, artist, album, bpm, key, duration_s, cues, filepath).
    Tracks dict keyed by track_id.
    """
    from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry

    lib = RekordboxLibrary()
    entry = TrackEntry(
        track_id="test_track_001",
        title="Test Track",
        artist="Test Artist",
        album="Test Album",
        bpm=128.0,
        key="A min",
        duration_s=320.0,
        cues=(),
        filepath="/tmp/test_track_001.mp3",
    )
    lib.tracks = {entry.track_id: entry}
    return lib


@pytest.fixture
def evidence_registry_with_library(
    synthetic_library: "RekordboxLibrary",
) -> "EvidenceRegistry":
    """An EvidenceRegistry with the synthetic library already registered."""
    from vibemix.state.evidence_registry import EvidenceRegistry

    reg = EvidenceRegistry()
    reg.register_library(synthetic_library)
    return reg
