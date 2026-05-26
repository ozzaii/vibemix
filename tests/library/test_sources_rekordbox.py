# SPDX-License-Identifier: Apache-2.0
"""Phase 89 Plan 89-01 — LibrarySource Protocol + RekordboxSource tests.

Task 1 lands the Protocol pin (Test D, real-green now). The RekordboxSource
detect/iter coverage flips green in Task 2 (marked strict-xfail until then).

Honest-green posture: NO GEMINI_API_KEY, NO network, NO torch/laion_clap —
``import vibemix.library.sources.base`` must succeed with torch absent, and
embedding is never exercised here (this module pins the source contract only).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.sources.base import LibrarySource

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_collection.xml"


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Point ``RekordboxLibrary.CACHE_PATH`` at a tmpdir-isolated location.

    THE library.pkl gotcha: ``load_xml`` writes the pickle cache as a side
    effect, so without this the test would clobber the developer's real
    ``~/.cache/vibemix/library.pkl``. Mirrors ``test_rekordbox.py``.
    """
    cache = tmp_path / "library.pkl"
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", cache)
    return cache


# --------------------------------------------------------------------------- #
# Test D — REAL-GREEN now: the Protocol contract + lazy-import pin.            #
# --------------------------------------------------------------------------- #


def test_library_source_is_runtime_checkable_protocol():
    """A class exposing detect()/default_paths()/iter_tracks()/name satisfies
    isinstance(obj, LibrarySource) via structural typing — no inheritance."""

    class _FakeSource:
        name = "fake"

        def detect(self) -> bool:
            return True

        def default_paths(self):
            return []

        def iter_tracks(self):
            return iter(())

    obj = _FakeSource()
    assert isinstance(obj, LibrarySource)


def test_library_source_rejects_incomplete_shape():
    """An object missing iter_tracks is NOT a LibrarySource (structural)."""

    class _Incomplete:
        name = "broken"

        def detect(self) -> bool:
            return False

        def default_paths(self):
            return []

    assert not isinstance(_Incomplete(), LibrarySource)


def test_sources_base_import_pulls_no_heavy_dep():
    """Importing the source contract in a fresh interpreter must NOT import
    torch / laion_clap (the lazy-import contract clap_engine relies on)."""
    code = (
        "import sys; import vibemix.library.sources.base; "
        "assert 'torch' not in sys.modules, 'torch leaked'; "
        "assert 'laion_clap' not in sys.modules, 'laion_clap leaked'"
    )
    repo_src = str(Path(__file__).resolve().parents[2] / "src")
    env = {**dict(__import__("os").environ), "PYTHONPATH": repo_src}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr


# --------------------------------------------------------------------------- #
# RekordboxSource detect/iter — flips green in Task 2.                         #
# --------------------------------------------------------------------------- #


@pytest.mark.xfail(strict=True, reason="RekordboxSource lands in Task 2")
def test_rekordbox_source_detect_explicit_path(isolated_cache):
    """detect() returns True for an explicit collection.xml path that exists."""
    from vibemix.library.sources.rekordbox import RekordboxSource

    src = RekordboxSource(xml_path=str(FIXTURE))
    assert src.name == "rekordbox"
    assert src.detect() is True
    assert Path(src.resolved_path) == FIXTURE


@pytest.mark.xfail(strict=True, reason="RekordboxSource lands in Task 2")
def test_rekordbox_source_detect_missing_returns_false(isolated_cache, tmp_path):
    """detect() returns False when no collection.xml exists at the given path."""
    from vibemix.library.sources.rekordbox import RekordboxSource

    src = RekordboxSource(xml_path=str(tmp_path / "nope.xml"))
    assert src.detect() is False


@pytest.mark.xfail(strict=True, reason="RekordboxSource lands in Task 2")
def test_rekordbox_source_iter_tracks_yields_entries(isolated_cache):
    """iter_tracks() yields all 5 fixture TrackEntry rows."""
    from vibemix.library.rekordbox import TrackEntry
    from vibemix.library.sources.rekordbox import RekordboxSource

    src = RekordboxSource(xml_path=str(FIXTURE))
    assert src.detect() is True
    entries = list(src.iter_tracks())
    assert len(entries) == 5
    assert all(isinstance(e, TrackEntry) for e in entries)
    assert {e.track_id for e in entries} == {"1", "2", "3", "4", "5"}


@pytest.mark.xfail(strict=True, reason="RekordboxSource lands in Task 2")
def test_rekordbox_source_satisfies_protocol(isolated_cache):
    """RekordboxSource is a structural LibrarySource."""
    from vibemix.library.sources.rekordbox import RekordboxSource

    assert isinstance(RekordboxSource(xml_path=str(FIXTURE)), LibrarySource)


@pytest.mark.xfail(strict=True, reason="RekordboxSource lands in Task 2")
def test_rekordbox_source_no_sqlcipher_import(isolated_cache):
    """Detecting + iterating must never pull a *sqlcipher* module (XML-only)."""
    from vibemix.library.sources.rekordbox import RekordboxSource

    src = RekordboxSource(xml_path=str(FIXTURE))
    src.detect()
    list(src.iter_tracks())
    assert not any("sqlcipher" in m.lower() for m in sys.modules)
