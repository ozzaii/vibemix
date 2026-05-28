# SPDX-License-Identifier: Apache-2.0
"""Plan 28-05 — similar_to tests + anti-feature guard verification."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

import vibemix.__main__ as main_mod
from vibemix.library._cosine import EMBEDDING_DIM
from vibemix.library.rekordbox import TrackEntry
from vibemix.library.similar import SimilarResult, similar_to


def _make_track(tid: str, bpm: float = 138.0) -> TrackEntry:
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key="A min",
        duration_s=240.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


@pytest.fixture
def fake_library() -> MagicMock:
    lib = MagicMock()
    lib.tracks = [_make_track(f"t{i:03d}") for i in range(10)]
    return lib


@pytest.fixture
def fake_embedder() -> MagicMock:
    e = MagicMock()
    e.embed_track.return_value = np.ones(EMBEDDING_DIM, dtype=np.float32)
    return e


@pytest.fixture
def fake_store() -> MagicMock:
    s = MagicMock()
    return s


def test_similar_returns_top_k_excluding_seed(
    fake_embedder, fake_store, fake_library
) -> None:
    # similar_to ranks via the mean-centered path (the anisotropy fix).
    fake_store.search_centered.return_value = [
        ("t000", 1.0),  # seed itself
        ("t001", 0.9),
        ("t002", 0.85),
        ("t003", 0.8),
        ("t004", 0.75),
    ]
    results = similar_to(
        fake_embedder, fake_store, fake_library, "t000", k=3
    )
    assert len(results) == 3
    ids = [r.track_id for r in results]
    assert "t000" not in ids  # seed excluded
    assert ids == ["t001", "t002", "t003"]


def test_similar_unknown_seed_returns_empty(
    fake_embedder, fake_store, fake_library
) -> None:
    results = similar_to(
        fake_embedder, fake_store, fake_library, "t-unknown"
    )
    assert results == []
    fake_embedder.embed_track.assert_not_called()


def test_similar_empty_library_returns_empty(
    fake_embedder, fake_store
) -> None:
    lib = MagicMock()
    lib.tracks = []
    results = similar_to(fake_embedder, fake_store, lib, "t000")
    assert results == []
    fake_embedder.embed_track.assert_not_called()


def test_similar_result_to_dict() -> None:
    # 5-field construction still works (S6 enrichment fields default to None).
    r = SimilarResult(
        track_id="t1", similarity=0.85, title="X", artist="Y", bpm=138.0
    )
    d = r.to_dict()
    assert d == {
        "track_id": "t1",
        "similarity": 0.85,
        "title": "X",
        "artist": "Y",
        "bpm": 138.0,
        # One Mind S6 — additive harmonic + tempo enrichment, honest-null here.
        "camelot": None,
        "harmonic_compatible": None,
        "bpm_delta": None,
    }


def test_similar_result_to_dict_with_s6_enrichment() -> None:
    r = SimilarResult(
        track_id="t1",
        similarity=0.85,
        title="X",
        artist="Y",
        bpm=133.0,
        camelot="9A",
        harmonic_compatible=True,
        bpm_delta=5.0,
    )
    d = r.to_dict()
    assert d["camelot"] == "9A"
    assert d["harmonic_compatible"] is True
    assert d["bpm_delta"] == 5.0


def test_similar_skips_unknown_track_ids(
    fake_embedder, fake_store, fake_library
) -> None:
    fake_store.search_centered.return_value = [
        ("t000", 1.0),  # seed
        ("t-ghost", 0.9),  # not in library
        ("t001", 0.8),
    ]
    results = similar_to(
        fake_embedder, fake_store, fake_library, "t000", k=5
    )
    ids = [r.track_id for r in results]
    assert "t-ghost" not in ids
    assert ids == ["t001"]


def test_anti_feature_guard_module_docstring() -> None:
    """Static contract: similar.py docstring MUST mention USER-ASKED."""
    from vibemix.library import similar as similar_module

    assert "USER-ASKED" in (similar_module.__doc__ or "")
    assert "autosurface" in (similar_module.__doc__ or "").lower()


def test_no_background_caller_imports_similar() -> None:
    """Anti-feature enforcement: agent-loop modules MUST NOT import similar.

    This is a structural guard — the only legitimate callers are CLI
    handlers (__main__.py) and IPC dispatchers (ws_bus). Background
    event/coach loops importing similar would constitute autosurface.
    """
    repo_root = Path(__file__).resolve().parents[2]
    forbidden_files = [
        repo_root / "src" / "vibemix" / "agent" / "dj_cohost.py",
        repo_root / "src" / "vibemix" / "runtime" / "coach.py",
        repo_root / "src" / "vibemix" / "runtime" / "session_loop.py",
    ]
    for f in forbidden_files:
        if not f.exists():
            continue
        text = f.read_text()
        # Allow comment mentions like "# Plan 05" — only ban actual import.
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and "library.similar" in stripped:
                pytest.fail(
                    f"{f.name} imports vibemix.library.similar — anti-feature "
                    f"guard violation. similar_to is USER-ASKED only."
                )


def test_library_similar_cli_emits_centering_metadata(monkeypatch) -> None:
    """The desktop bridge reads these fields for the shared results header."""
    import vibemix.library as lib_pkg
    import vibemix.library.similar as similar_mod

    class FakeLibrary:
        def __init__(self) -> None:
            self.tracks = {"t000": _make_track("t000")}

        def try_load_cache(self) -> bool:
            return True

    class FakeStore:
        def row_count(self) -> int:
            return 24

        def close(self) -> None:
            return None

    result = SimilarResult(
        track_id="t001",
        similarity=0.77,
        title="Title t001",
        artist="Artist t001",
        bpm=138.0,
    )
    monkeypatch.setattr(lib_pkg, "RekordboxLibrary", FakeLibrary)
    monkeypatch.setattr(lib_pkg, "build_embedder", lambda: object())
    monkeypatch.setattr(lib_pkg, "open_store", lambda: FakeStore())
    monkeypatch.setattr(
        similar_mod,
        "similar_to",
        lambda embedder, store, library, track_id, k: [result],
    )

    buf = io.StringIO()
    monkeypatch.setattr(main_mod.sys, "stdout", buf)
    rc = main_mod._cmd_library_similar(argparse.Namespace(track_id="t000", k=3))

    assert rc == 0
    payload = json.loads(buf.getvalue())
    assert payload["centered"] is True
    assert payload["corpus_size"] == 24
