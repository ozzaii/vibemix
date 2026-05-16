# SPDX-License-Identifier: Apache-2.0
"""Plan 28-01 Task 3 — Unit tests for LibraryEmbedder.

All ``client.models.embed_content`` calls are mocked — zero real network
traffic, no Gemini API key needed. ffmpeg subprocess is mocked so the
3-excerpt path is exercised without needing real audio decoding.

Test plan:
    - test_short_track_single_call
    - test_long_track_split_into_3_excerpts
    - test_audio_cap_error_handled
    - test_streaming_track_text_only_path
    - test_content_hash_skip_on_reimport
    - test_text_query_embed
    - test_model_id_locked
    - test_no_task_type_param
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from vibemix.library.embed import (
    EMBEDDING_DIM,
    EXCERPT_STRATEGY_VERSION,
    GEMINI_EMBEDDING_MODEL,
    LibraryEmbedder,
)
from vibemix.library.rekordbox import TrackEntry


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_embedding_response(values: list[float] | None = None) -> MagicMock:
    """Build a mock response object shaped like the Gemini SDK return."""
    if values is None:
        values = [0.1] * EMBEDDING_DIM
    return SimpleNamespace(
        embeddings=[SimpleNamespace(values=values)]
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock ``genai.Client`` with mocked ``models.embed_content``."""
    client = MagicMock()
    client.models.embed_content.return_value = _make_embedding_response()
    return client


@pytest.fixture
def cache_db(tmp_path: Path) -> sqlite3.Connection:
    """Per-test in-tmpdir sqlite cache, schema initialised by Embedder."""
    return sqlite3.connect(str(tmp_path / "embeddings.db"))


@pytest.fixture
def embedder(
    mock_client: MagicMock, cache_db: sqlite3.Connection
) -> LibraryEmbedder:
    # ``probe_on_init=False`` keeps these Plan 28 tests deterministic.
    # The Plan 41-05 GA-rename probe path is covered in
    # tests/library/test_embedding_ga_probe.py.
    return LibraryEmbedder(mock_client, cache_db=cache_db, probe_on_init=False)


@pytest.fixture
def short_track(tmp_path: Path) -> TrackEntry:
    """60s track on disk — single-call audio path."""
    audio = tmp_path / "short.mp3"
    audio.write_bytes(b"fakeid3" + b"\x00" * 1024)
    return TrackEntry(
        track_id="t-short",
        title="Short Track",
        artist="Tester",
        album="Album A",
        bpm=128.0,
        key="A min",
        duration_s=60.0,
        cues=(),
        filepath=str(audio),
    )


@pytest.fixture
def long_track(tmp_path: Path) -> TrackEntry:
    """480s track on disk — 3-excerpt path."""
    audio = tmp_path / "long.mp3"
    audio.write_bytes(b"fakeid3" + b"\x00" * 1024)
    return TrackEntry(
        track_id="t-long",
        title="Long Track",
        artist="Tester",
        album="Album L",
        bpm=140.0,
        key="C maj",
        duration_s=480.0,
        cues=(),
        filepath=str(audio),
    )


@pytest.fixture
def streaming_track() -> TrackEntry:
    """No on-disk file — text-only path."""
    return TrackEntry(
        track_id="t-stream",
        title="Streaming Only",
        artist="Spotify Artist",
        album="Streaming Album",
        bpm=125.0,
        key="F# min",
        duration_s=200.0,
        cues=(),
        filepath="/does/not/exist.mp3",
    )


@pytest.fixture
def fake_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch shutil.which + subprocess.run so ffmpeg subprocess is mocked.

    The mocked subprocess writes 1KB of audio-like bytes to its output
    path so the embedder's ``read_bytes`` call returns realistic data.
    """
    monkeypatch.setattr(
        "vibemix.library.embed.shutil.which",
        lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None,
    )

    def fake_run(cmd, **kwargs):
        # The last positional arg of our ffmpeg invocation is the output path.
        out_path = Path(cmd[-1])
        out_path.write_bytes(b"\xff\xfb\x90\x44" + b"\x00" * 1020)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(
        "vibemix.library.embed.subprocess.run", fake_run
    )


# ─── Tests ───────────────────────────────────────────────────────────────────


def test_short_track_single_call(
    embedder: LibraryEmbedder,
    mock_client: MagicMock,
    short_track: TrackEntry,
) -> None:
    """60s track → 1 audio embed call, float32 (768,), L2-normalized."""
    vec = embedder.embed_track(short_track)

    assert vec.dtype == np.float32
    assert vec.shape == (EMBEDDING_DIM,)
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-3
    assert mock_client.models.embed_content.call_count == 1

    # Verify model id used.
    call = mock_client.models.embed_content.call_args
    assert call.kwargs["model"] == GEMINI_EMBEDDING_MODEL


def test_long_track_split_into_3_excerpts(
    embedder: LibraryEmbedder,
    mock_client: MagicMock,
    long_track: TrackEntry,
    fake_ffmpeg: None,
) -> None:
    """480s track → exactly 3 audio embed calls; result = mean of 3."""
    # Configure each call to return a distinct vector so mean is non-trivial.
    vectors = [
        [0.1] * EMBEDDING_DIM,
        [0.2] * EMBEDDING_DIM,
        [0.3] * EMBEDDING_DIM,
    ]
    mock_client.models.embed_content.side_effect = [
        _make_embedding_response(v) for v in vectors
    ]

    vec = embedder.embed_track(long_track)

    assert mock_client.models.embed_content.call_count == 3
    assert vec.dtype == np.float32
    assert vec.shape == (EMBEDDING_DIM,)
    # L2-normalized so we lose absolute scale; verify length.
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-3


def test_audio_cap_error_handled(
    embedder: LibraryEmbedder,
    mock_client: MagicMock,
    short_track: TrackEntry,
    fake_ffmpeg: None,
) -> None:
    """First call fails with audio-too-long → falls back to 3-excerpt path.

    Track is short but server says it's over cap. We expect 1 failed
    full-file call + 3 successful excerpt calls = 4 total.
    """
    # Track reports 60s (single-call branch) but the API rejects with
    # cap error — verify fallback to 3-excerpt path.
    cap_error = Exception("audio too long: exceeds 180s cap")
    mock_client.models.embed_content.side_effect = [
        cap_error,
        _make_embedding_response([0.1] * EMBEDDING_DIM),
        _make_embedding_response([0.2] * EMBEDDING_DIM),
        _make_embedding_response([0.3] * EMBEDDING_DIM),
    ]

    vec = embedder.embed_track(short_track)
    assert mock_client.models.embed_content.call_count == 4
    assert vec.shape == (EMBEDDING_DIM,)


def test_streaming_track_text_only_path(
    embedder: LibraryEmbedder,
    mock_client: MagicMock,
    streaming_track: TrackEntry,
) -> None:
    """Track with missing file → text-only embed; 0 audio calls."""
    vec = embedder.embed_track(streaming_track)

    assert mock_client.models.embed_content.call_count == 1
    call = mock_client.models.embed_content.call_args
    # Text mode: contents is a string, not a list.
    assert isinstance(call.kwargs["contents"], str)
    sig = call.kwargs["contents"]
    assert "Streaming Only" in sig
    assert "Spotify Artist" in sig
    assert "125 BPM" in sig
    assert "F# min" in sig
    assert vec.shape == (EMBEDDING_DIM,)


def test_content_hash_skip_on_reimport(
    embedder: LibraryEmbedder,
    mock_client: MagicMock,
    short_track: TrackEntry,
) -> None:
    """Second embed_track on identical TrackEntry → cache hit, 0 new calls."""
    vec1 = embedder.embed_track(short_track)
    assert mock_client.models.embed_content.call_count == 1

    vec2 = embedder.embed_track(short_track)
    assert mock_client.models.embed_content.call_count == 1
    np.testing.assert_array_equal(vec1, vec2)

    # Cache row count is 1.
    rows = embedder._cache.execute(
        "SELECT COUNT(*) FROM embed_cache"
    ).fetchone()[0]
    assert rows == 1


def test_text_query_embed(
    embedder: LibraryEmbedder, mock_client: MagicMock
) -> None:
    """embed_query → 1 text embed call, float32 (768,), L2-normalized."""
    vec = embedder.embed_query("driving acid techno around 138 BPM")

    assert vec.dtype == np.float32
    assert vec.shape == (EMBEDDING_DIM,)
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-3

    assert mock_client.models.embed_content.call_count == 1
    call = mock_client.models.embed_content.call_args
    assert isinstance(call.kwargs["contents"], str)
    assert call.kwargs["model"] == GEMINI_EMBEDDING_MODEL


def test_model_id_locked() -> None:
    """Regression guard: model id must stay 'gemini-embedding-2'.

    Documented in CONTEXT correction (Open Q9). If this test fails, a
    contributor accidentally reverted to the older text-only series.
    """
    assert GEMINI_EMBEDDING_MODEL == "gemini-embedding-2"
    assert EXCERPT_STRATEGY_VERSION == "v1-3excerpt-mean"
    assert EMBEDDING_DIM == 768


def test_no_task_type_param(
    embedder: LibraryEmbedder,
    mock_client: MagicMock,
    streaming_track: TrackEntry,
) -> None:
    """Open Q8: the legacy task-routing kwarg is NOT valid for Embedding 2.

    Verify no call uses it as a kwarg.
    """
    embedder.embed_track(streaming_track)
    for call in mock_client.models.embed_content.call_args_list:
        assert "task_type" not in call.kwargs
