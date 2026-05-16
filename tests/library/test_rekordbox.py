# SPDX-License-Identifier: Apache-2.0
"""Phase 25 Plan 25-02 — RekordboxLibrary parse + cache + dormancy tests.

All tests use the synthetic 5-track fixture at
``tests/library/fixtures/synthetic_collection.xml``. The cache path is
isolated to a pytest ``tmp_path`` via monkeypatching the class attribute,
so the developer's actual ``~/.cache/vibemix/library.pkl`` is never
touched.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TrackEntry

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_collection.xml"


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Point ``RekordboxLibrary.CACHE_PATH`` at a tmpdir-isolated location."""
    cache = tmp_path / "library.pkl"
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", cache)
    return cache


def test_load_xml_round_trip(isolated_cache):
    """Parse the synthetic 5-track fixture; check core field round-trip."""
    lib = RekordboxLibrary()
    n = lib.load_xml(FIXTURE)
    assert n == 5
    assert len(lib) == 5

    track1 = lib.lookup_by_id("1")
    assert isinstance(track1, TrackEntry)
    assert track1.title == "Test Track One"
    assert track1.artist == "Artist A"
    assert track1.album == "Album X"
    assert track1.bpm == 124.0
    assert track1.key == "Am"
    assert track1.duration_s == 240.0
    assert len(track1.cues) >= 2
    # urllib.parse.unquote on the pre-stripped path is a no-op for our
    # synthetic fixture (no encoded characters); just confirm we surface a
    # non-empty filepath so Phase 26 prompt grounding has something to bind.
    assert track1.filepath.endswith("track-1.mp3")


def test_cuepoint_loop_shape(isolated_cache):
    """Track 3 has at least one loop cue with end_s > start_s."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    track3 = lib.lookup_by_id("3")
    assert track3 is not None
    loops = [c for c in track3.cues if c.type == "loop"]
    assert len(loops) >= 1
    loop = loops[0]
    assert loop.end_s is not None
    assert loop.end_s > loop.start_s


def test_lookup_by_id_returns_track_entry(isolated_cache):
    """Known + unknown id lookups both behave."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    assert lib.lookup_by_id("1") is not None
    assert lib.lookup_by_id("999") is None


def test_lookup_by_id_returns_none_when_unloaded():
    """Fresh library has no tracks — lookup returns None."""
    lib = RekordboxLibrary()
    assert lib.lookup_by_id("1") is None
    assert lib.lookup_by_id("anything") is None


def test_staleness_nudge_logs_when_xml_older_than_30d(
    isolated_cache, tmp_path, caplog
):
    """31-day-old XML mtime fires the LIBRARY-06 logger.info nudge."""
    # Copy the fixture so we can mtime-bump without polluting the repo.
    dst = tmp_path / "stale_collection.xml"
    dst.write_bytes(FIXTURE.read_bytes())
    stale = time.time() - 31 * 86400
    os.utime(dst, (stale, stale))

    with caplog.at_level(logging.INFO, logger="vibemix.library"):
        lib = RekordboxLibrary()
        lib.load_xml(dst)
    nudges = [r for r in caplog.records if "collection.xml is" in r.getMessage()]
    assert len(nudges) == 1, (
        f"expected exactly one staleness nudge; got {[r.getMessage() for r in caplog.records]}"
    )
    assert "days old" in nudges[0].getMessage()


def test_no_sqlcipher_module_imported_after_load(isolated_cache):
    """SQLCipher path stays dormant even after a full XML load.

    We allow ``pyrekordbox.db6`` to land in ``sys.modules`` because the
    package ``__init__.py`` imports ``Rekordbox6Database`` eagerly — that's
    by-design upstream. What MUST stay zero is any module matching
    ``*sqlcipher*``. A fresh interpreter (subprocess) is the cleanest way
    to assert this independent of the test runner's pre-existing imports.
    """
    script = (
        f"import sys\n"
        f"from vibemix.library.rekordbox import RekordboxLibrary\n"
        f"lib = RekordboxLibrary()\n"
        f"lib.load_xml({str(FIXTURE)!r})\n"
        f"assert len(lib) == 5, f'expected 5 tracks, got {{len(lib)}}'\n"
        f"leaks = sorted(m for m in sys.modules if 'sqlcipher' in m.lower())\n"
        f"print('LEAKED:' + ','.join(leaks) if leaks else 'DORMANT')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "DORMANT", (
        f"SQLCipher path leaked during load_xml — stdout: {result.stdout!r}; "
        f"stderr: {result.stderr!r}"
    )


def test_cache_warm_start_round_trip(isolated_cache):
    """First load_xml writes the cache; a fresh instance hits it via try_load_cache."""
    lib1 = RekordboxLibrary()
    lib1.load_xml(FIXTURE)
    assert isolated_cache.exists()

    lib2 = RekordboxLibrary()
    assert lib2.try_load_cache() is True
    assert len(lib2) == 5
    track1 = lib2.lookup_by_id("1")
    assert track1 is not None
    assert track1.title == "Test Track One"
    assert track1.bpm == 124.0


def test_cache_invalidated_when_xml_path_differs(
    isolated_cache, tmp_path
):
    """A different on-disk fixture replaces the cached source; cache is bypassed
    on path mismatch — try_load_cache returns True because the cache is keyed
    on the original ``xml_path`` recorded at write time, and the cache hit
    populates from THAT recorded path, not the caller's expectation. The
    real invalidation gate is the source-mtime > cached-mtime check, which
    we cover here by bumping mtime on the recorded source after caching.
    """
    # Initial load populates the cache for FIXTURE.
    lib1 = RekordboxLibrary()
    lib1.load_xml(FIXTURE)
    assert isolated_cache.exists()

    # Bump source mtime forward by 10s; the cache should now be considered stale.
    future = time.time() + 10.0
    os.utime(FIXTURE, (future, future))
    try:
        lib2 = RekordboxLibrary()
        assert lib2.try_load_cache() is False, (
            "cache should be invalidated when source mtime moved forward"
        )
    finally:
        # Restore mtime to roughly current to avoid polluting other tests.
        now = time.time()
        os.utime(FIXTURE, (now, now))


def test_cache_miss_when_file_absent(isolated_cache):
    """Fresh library + no pre-existing cache file → try_load_cache returns False."""
    lib = RekordboxLibrary()
    assert lib.try_load_cache() is False


def test_cache_miss_on_corrupted_blob(isolated_cache):
    """Garbage cache file → silent False (no exception bubble)."""
    isolated_cache.parent.mkdir(parents=True, exist_ok=True)
    isolated_cache.write_bytes(b"not a pickle")
    lib = RekordboxLibrary()
    assert lib.try_load_cache() is False
