# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 06 — EXEMPLAR-01 ``ingest_folder(compute_band_shares=True)``
side-car ``band_shares`` write opt-in.

Verifies the additive write path Plan 93-06 grafts onto the existing CLAP
ingest loop:

    * legacy callers (no kwarg / kwarg=False) → ``band_shares`` table stays
      empty for any track they ingest (byte-identical with pre-Plan-93-06
      ingest behavior).
    * opt-in callers (kwarg=True) → ``band_shares`` table carries one row
      per successfully-CLAP-embedded track; the 5 floats (sub/low/mid/high
      shares + kick_corr) match what ``compute_band_shares()`` returned.
    * a ``compute_band_shares`` raise on one track LOGS ``[band-share err]``
      but does NOT abort the outer ingest loop — best-effort semantics from
      93-RESEARCH.md Pattern 9.

ZERO real audio fixtures: the per-track ``compute_band_shares`` function
is monkeypatched to return a deterministic dict (or raise on demand). The
``band_share_store.DB_PATH`` is pointed at ``tmp_path`` so the test never
touches ``~/.cache/vibemix/library-clap.db``.

REQ-IDs: EXEMPLAR-01.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from vibemix.library import ingest_folder
from vibemix.library._cosine import EMBEDDING_DIM, l2_normalize
from vibemix.library.index_numpy import NumpyStore
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore

# ─── Fixtures (mirror tests/library/test_folder_ingest.py shape) ─────────────


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * 16)
    return path


@pytest.fixture
def numpy_store(tmp_path: Path) -> LibraryStore:
    backend = NumpyStore(
        vectors_path=tmp_path / "vectors.npy",
        ids_path=tmp_path / "ids.json",
    )
    return LibraryStore(backend)


class FakeEmbedder:
    """Records calls; returns a fixed L2-normalized vector. No network."""

    def __init__(self) -> None:
        self.embed_calls: list[str] = []
        self._vec = l2_normalize(np.ones(EMBEDDING_DIM, dtype=np.float32))
        self._embed_strategy = "mean_excerpt"

    def has_cached_embedding(self, track) -> bool:
        return False

    def embed_track(self, track) -> np.ndarray:
        self.embed_calls.append(track.track_id)
        return self._vec.copy()


@pytest.fixture(autouse=True)
def _isolate_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect both the Rekordbox cache AND the band_shares side-car DB
    away from ``~/.cache/vibemix/`` so the test never touches real state."""
    # Mirror tests/library/test_folder_ingest.py — keep library.pkl in tmp.
    monkeypatch.setattr(
        RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl"
    )
    # Point band_share_store.DB_PATH at a tmp sqlite file so the additive
    # write path (Plan 93-06) lands in tmp, not ~/.cache/vibemix/.
    from vibemix.learn import band_share_store
    from vibemix.library import index_sqlite_vec

    bs_db = tmp_path / "library-clap.db"
    monkeypatch.setattr(index_sqlite_vec, "DB_PATH", bs_db)
    monkeypatch.setattr(band_share_store, "DB_PATH", bs_db)


def _const_probe(_dur: float = 120.0):
    return lambda _path: _dur


def _count_band_shares_rows(db_path: Path) -> int:
    """Return the row-count of band_shares table, or 0 when DB/table missing."""
    if not db_path.exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    try:
        try:
            cur = conn.execute("SELECT COUNT(*) FROM band_shares")
        except sqlite3.OperationalError:
            return 0
        return int(cur.fetchone()[0])
    finally:
        conn.close()


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_ingest_default_flag_does_not_write_band_shares(
    tmp_path: Path, numpy_store: LibraryStore
) -> None:
    """Legacy callers (no kwarg → default False) keep the existing
    no-band-share behavior — byte-identical with pre-Plan-93-06 ingest."""
    _touch(tmp_path / "tracks" / "a.mp3")
    _touch(tmp_path / "tracks" / "b.mp3")

    report = ingest_folder(
        tmp_path / "tracks",
        FakeEmbedder(),
        numpy_store,
        probe=_const_probe(120.0),
    )

    assert report.embedded == 2
    # Side-car DB either doesn't exist OR has zero band_shares rows.
    assert _count_band_shares_rows(tmp_path / "library-clap.db") == 0


def test_ingest_with_flag_writes_band_shares(
    tmp_path: Path, numpy_store: LibraryStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """compute_band_shares=True writes one row per successfully-embedded
    track; the 5 floats round-trip from the monkeypatched compute fn."""
    _touch(tmp_path / "tracks" / "a.mp3")
    _touch(tmp_path / "tracks" / "b.mp3")

    captured_paths: list[str] = []

    def _fake_compute(path: str) -> dict[str, float]:
        captured_paths.append(path)
        return {
            "sub_share": 0.25,
            "low_share": 0.35,
            "mid_share": 0.25,
            "high_share": 0.15,
            "kick_corr": 0.12,
        }

    # Patch on the exemplar module — folder_ingest re-imports lazily inside
    # the per-track block. Patching at the source-of-truth means the
    # lazy import receives the patched symbol.
    from vibemix.learn import exemplar as _exemplar_mod

    monkeypatch.setattr(_exemplar_mod, "compute_band_shares", _fake_compute)

    report = ingest_folder(
        tmp_path / "tracks",
        FakeEmbedder(),
        numpy_store,
        probe=_const_probe(120.0),
        compute_band_shares=True,
    )

    assert report.embedded == 2
    assert len(captured_paths) == 2
    # Both rows landed; query back to verify content.
    db_path = tmp_path / "library-clap.db"
    assert _count_band_shares_rows(db_path) == 2
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            "SELECT sub_share, low_share, mid_share, high_share, kick_corr "
            "FROM band_shares ORDER BY track_id"
        ).fetchall()
    finally:
        conn.close()
    # All 2 rows carry the constants we returned.
    for row in rows:
        assert row[0] == pytest.approx(0.25)
        assert row[1] == pytest.approx(0.35)
        assert row[2] == pytest.approx(0.25)
        assert row[3] == pytest.approx(0.15)
        assert row[4] == pytest.approx(0.12)
        # The 4 shares should sum to roughly 1.0 (sanity that we wrote what
        # the monkeypatched compute returned, not some default).
        assert (row[0] + row[1] + row[2] + row[3]) == pytest.approx(1.0, abs=1e-6)


def test_ingest_with_flag_swallows_band_share_errors(
    tmp_path: Path,
    numpy_store: LibraryStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A compute_band_shares raise on one track LOGS [band-share err] but
    does NOT abort the outer ingest loop — best-effort semantics from
    93-RESEARCH.md Pattern 9."""
    import logging

    _touch(tmp_path / "tracks" / "good.mp3")
    _touch(tmp_path / "tracks" / "bad.mp3")

    def _fake_compute(path: str) -> dict[str, float]:
        if path.endswith("bad.mp3"):
            raise RuntimeError("synthetic decode failure")
        return {
            "sub_share": 0.30,
            "low_share": 0.30,
            "mid_share": 0.25,
            "high_share": 0.15,
            "kick_corr": 0.05,
        }

    from vibemix.learn import exemplar as _exemplar_mod

    monkeypatch.setattr(_exemplar_mod, "compute_band_shares", _fake_compute)

    with caplog.at_level(logging.WARNING, logger="vibemix.library.folder_ingest"):
        report = ingest_folder(
            tmp_path / "tracks",
            FakeEmbedder(),
            numpy_store,
            probe=_const_probe(120.0),
            compute_band_shares=True,
        )

    # Outer ingest counters unchanged by the band-share failure — the CLAP
    # vector was still added for BOTH tracks.
    assert report.embedded == 2
    assert report.failed == 0
    # Only the "good" track produced a band_shares row; the "bad" one was
    # logged + skipped.
    assert _count_band_shares_rows(tmp_path / "library-clap.db") == 1
    # The warning was emitted via the [band-share err] marker.
    assert any(
        "[band-share err]" in record.getMessage() for record in caplog.records
    ), f"expected [band-share err] log entry; got {[r.getMessage() for r in caplog.records]}"


def test_embed_folder_cli_enables_band_shares_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The operator fallback path should feed Learn's own-track exemplars too."""
    import vibemix.library as library_mod
    from vibemix import __main__ as main_mod

    folder = tmp_path / "tracks"
    folder.mkdir()
    calls: dict[str, object] = {}

    class FakeStore:
        def close(self) -> None:
            calls["closed"] = True

    def fake_ingest_folder(folder_arg, embedder, store, **kwargs):
        calls["folder"] = folder_arg
        calls["compute_band_shares"] = kwargs.get("compute_band_shares")
        return SimpleNamespace(
            embedded=0,
            skipped_cached=0,
            failed=0,
            total=0,
            cost_estimate_eur=0.0,
            as_dict=lambda: {
                "embedded": 0,
                "skipped_cached": 0,
                "failed": 0,
                "total": 0,
            },
        )

    monkeypatch.setattr(library_mod, "build_embedder", lambda *a, **k: object())
    monkeypatch.setattr(library_mod, "open_store", lambda *a, **k: FakeStore())
    monkeypatch.setattr(library_mod, "ingest_folder", fake_ingest_folder)

    rc = main_mod._cmd_library_embed_folder(
        argparse.Namespace(
            path=str(folder),
            strategy="mean_excerpt",
            compute_key=False,
            compute_bpm=False,
            json=True,
        )
    )

    assert rc == 0
    assert calls["folder"] == folder
    assert calls["compute_band_shares"] is True
    assert calls["closed"] is True


def test_embed_folder_cli_expands_default_music_tilde(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The desktop first-run field defaults to ~/Music; keep that path valid."""
    import vibemix.library as library_mod
    from vibemix import __main__ as main_mod

    home = tmp_path / "home"
    folder = home / "Music"
    folder.mkdir(parents=True)
    calls: dict[str, object] = {}

    class FakeStore:
        def close(self) -> None:
            calls["closed"] = True

    def fake_ingest_folder(folder_arg, embedder, store, **kwargs):
        calls["folder"] = folder_arg
        return SimpleNamespace(
            embedded=0,
            skipped_cached=0,
            failed=0,
            total=0,
            cost_estimate_eur=0.0,
            as_dict=lambda: {
                "embedded": 0,
                "skipped_cached": 0,
                "failed": 0,
                "total": 0,
            },
        )

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setattr(library_mod, "build_embedder", lambda *a, **k: object())
    monkeypatch.setattr(library_mod, "open_store", lambda *a, **k: FakeStore())
    monkeypatch.setattr(library_mod, "ingest_folder", fake_ingest_folder)

    rc = main_mod._cmd_library_embed_folder(
        argparse.Namespace(
            path="~/Music",
            strategy="mean_excerpt",
            compute_key=False,
            compute_bpm=False,
            json=True,
        )
    )

    assert rc == 0
    assert calls["folder"] == folder
    assert calls["closed"] is True
