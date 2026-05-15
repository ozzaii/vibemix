# SPDX-License-Identifier: Apache-2.0
"""Plan 28-05 — similar_to tests + anti-feature guard verification."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

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
    e.embed_track.return_value = np.ones(768, dtype=np.float32)
    return e


@pytest.fixture
def fake_store() -> MagicMock:
    s = MagicMock()
    return s


def test_similar_returns_top_k_excluding_seed(
    fake_embedder, fake_store, fake_library
) -> None:
    fake_store.search.return_value = [
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
    }


def test_similar_skips_unknown_track_ids(
    fake_embedder, fake_store, fake_library
) -> None:
    fake_store.search.return_value = [
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
