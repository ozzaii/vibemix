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


def _write_minimal_track_xml(tmp_path, *, track_attrs: str, body: str = "") -> Path:
    """Emit a 1-track collection.xml so a single edge case can be asserted in
    isolation without perturbing the canonical 5-track fixture's counts."""
    dst = tmp_path / "edge_collection.xml"
    dst.write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<DJ_PLAYLISTS Version="1.0.0">\n'
        '  <PRODUCT Name="vibemix" Version="1.0.0" Company="vibemix-test" />\n'
        '  <COLLECTION Entries="1">\n'
        f'    <TRACK Location="file://localhost//Users/test/Music/edge.mp3" '
        f'TrackID="9001" Name="Edge" {track_attrs}>\n'
        f"{body}"
        "    </TRACK>\n"
        "  </COLLECTION>\n"
        '  <PLAYLISTS><NODE Name="ROOT" Type="0" Count="0" /></PLAYLISTS>\n'
        "</DJ_PLAYLISTS>",
        encoding="utf-8",
    )
    return dst


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


def test_no_sqlcipher_module_imported_after_load(isolated_cache, tmp_path):
    """SQLCipher path stays dormant even after a full XML load.

    We allow ``pyrekordbox.db6`` to land in ``sys.modules`` because the
    package ``__init__.py`` imports ``Rekordbox6Database`` eagerly — that's
    by-design upstream. What MUST stay zero is any module matching
    ``*sqlcipher*``. A fresh interpreter (subprocess) is the cleanest way
    to assert this independent of the test runner's pre-existing imports.

    ISOLATION: the ``isolated_cache`` fixture monkeypatches
    ``RekordboxLibrary.CACHE_PATH`` IN-PROCESS only — it does NOT cross the
    subprocess boundary. ``load_xml`` writes the pickle cache as a side
    effect, so without an explicit override the child would clobber the
    developer's real ``~/.cache/vibemix/library.pkl`` (this happened during
    a live embed run). We therefore repoint CACHE_PATH inside the child to a
    tmp_path-rooted file so the spawned interpreter never touches real cache.
    """
    child_cache = tmp_path / "subproc_library.pkl"
    script = (
        f"import sys\n"
        f"from vibemix.library.rekordbox import RekordboxLibrary\n"
        f"RekordboxLibrary.CACHE_PATH = __import__('pathlib').Path({str(child_cache)!r})\n"
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


# ===================================================================== #
# Plan 89-02 — enriched metadata / Camelot-at-parse / beatgrid / cue    #
# Type fidelity. These pin the enriched parse contract; RED until the   #
# parser lands in Task 2 (strict-xfail, flipped green there).           #
# ===================================================================== #


def test_enriched_metadata_fields(isolated_cache):
    """Track 1 surfaces genre / label / rating(stars) / play_count / comments."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    track1 = lib.lookup_by_id("1")
    assert track1 is not None
    assert track1.genre == "Techno"
    assert track1.label == "Drumcode"
    assert track1.rating == 4  # Rekordbox byte 204 -> 4 stars
    assert track1.play_count == 42
    assert track1.comments == "/* 8A - Energy 8 */"


def test_enriched_metadata_honest_empty_when_absent(isolated_cache):
    """Tracks with no genre/label/comments coerce to typed empties (Invariant #3)."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    track2 = lib.lookup_by_id("2")
    assert track2 is not None
    assert track2.genre == ""
    assert track2.label == ""
    assert track2.comments == ""
    assert track2.rating == 0
    assert track2.play_count == 0


def test_camelot_computed_at_parse_raw_key_preserved(isolated_cache):
    """track1.camelot is the deterministic Camelot; raw classical key untouched."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    track1 = lib.lookup_by_id("1")
    assert track1 is not None
    assert track1.camelot == "8A"  # Am -> 8A via harmonics.to_camelot
    assert track1.key == "Am"  # raw classical preserved
    # Track 2: Cm -> 5A
    track2 = lib.lookup_by_id("2")
    assert track2 is not None
    assert track2.camelot == "5A"
    assert track2.key == "Cm"


def test_camelot_honest_none_on_empty_key(isolated_cache, tmp_path):
    """An empty Tonality -> camelot is None, key is "" (honest, never guessed)."""
    edge = _write_minimal_track_xml(
        tmp_path, track_attrs='AverageBpm="120.0" Tonality="" TotalTime="180"'
    )
    lib = RekordboxLibrary()
    lib.load_xml(edge)
    track = lib.lookup_by_id("9001")
    assert track is not None
    assert track.key == ""
    assert track.camelot is None


def test_beatgrid_tempo_nodes_variable_grid(isolated_cache):
    """track1 carries a >=2-node TempoNode beatgrid (variable grid)."""
    from vibemix.library.rekordbox import TempoNode

    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    track1 = lib.lookup_by_id("1")
    assert track1 is not None
    assert isinstance(track1.beatgrid, tuple)
    assert len(track1.beatgrid) >= 2
    first = track1.beatgrid[0]
    assert isinstance(first, TempoNode)
    assert first.inizio_s == 0.12
    assert first.bpm == 124.0
    assert first.metro == "4/4"
    assert first.battito == 1


def test_beatgrid_empty_when_absent(isolated_cache):
    """A track with NO TEMPO children -> beatgrid == () (honest empty)."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    track2 = lib.lookup_by_id("2")
    assert track2 is not None
    assert track2.beatgrid == ()


def test_cue_type_fidelity_load(isolated_cache):
    """track1 carries a load mark (Type=3 -> "load"), not a default "cue".

    pyrekordbox 0.4.4 already maps PositionMark.Type int -> label string via
    its GETTERS, so this contract holds today; Task 2 hardens _mark_to_cue to
    int-coerce defensively (handles a raw int Type without regressing this).
    """
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    track1 = lib.lookup_by_id("1")
    assert track1 is not None
    loads = [c for c in track1.cues if c.type == "load"]
    assert len(loads) == 1


def test_cue_type_fidelity_loop_and_plain(isolated_cache):
    """track3 loop cue is "loop" (Type=4); plain hot cues stay "cue" (Type=0)."""
    lib = RekordboxLibrary()
    lib.load_xml(FIXTURE)
    track3 = lib.lookup_by_id("3")
    assert track3 is not None
    loops = [c for c in track3.cues if c.type == "loop"]
    assert len(loops) == 1
    plain = [c for c in track3.cues if c.type == "cue"]
    assert len(plain) == 3  # intro/drop/breakdown all Type=0
