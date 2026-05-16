# SPDX-License-Identifier: Apache-2.0
"""Plan 41-05 Task 1 — GA-rename probe + auto-bump tests for LibraryEmbedder.

Covers LAT-06's GA-probe behaviour: on construction, LibraryEmbedder
tries the GA-renamed model id ``gemini-embedding-002`` first; on 404 /
NOT_FOUND it falls back to the v2.1 shipped id ``gemini-embedding-2``.
If both fail the probe raises so the caller can surface the outage.

When the probe surfaces a GA rename, ``EXCERPT_STRATEGY_VERSION`` bumps
from ``v1-3excerpt-mean`` → ``v2-3excerpt-mean-emb2-ga`` so the cache
invalidates and the corpus is re-embedded lazily on first read.

All tests use a mock ``genai.Client`` — zero real network traffic.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from vibemix.library.embed import (
    EMBEDDING_DIM,
    EXCERPT_STRATEGY_VERSION,
    EXCERPT_STRATEGY_VERSION_GA_RENAME,
    GEMINI_EMBEDDING_MODEL,
    GEMINI_EMBEDDING_MODEL_GA_CANDIDATES,
    LibraryEmbedder,
    _probe_ga_model_id,
)
from vibemix.library.rekordbox import TrackEntry


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _make_embedding_response(values: list[float] | None = None) -> SimpleNamespace:
    if values is None:
        values = [0.1] * EMBEDDING_DIM
    return SimpleNamespace(embeddings=[SimpleNamespace(values=values)])


@pytest.fixture
def cache_db(tmp_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(tmp_path / "embeddings.db"))


@pytest.fixture
def short_track(tmp_path: Path) -> TrackEntry:
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


# ─── Constants integrity ─────────────────────────────────────────────────────


def test_ga_candidates_order_locked() -> None:
    """The probe order MUST try the GA-renamed id first.

    Pinned per Plan 41-05 probe_design block: ('gemini-embedding-002',
    'gemini-embedding-2'). Bumping order requires explicit Plan change.
    """
    assert GEMINI_EMBEDDING_MODEL_GA_CANDIDATES == (
        "gemini-embedding-002",
        "gemini-embedding-2",
    )
    assert EXCERPT_STRATEGY_VERSION_GA_RENAME == "v2-3excerpt-mean-emb2-ga"
    assert EXCERPT_STRATEGY_VERSION == "v1-3excerpt-mean"


# ─── _probe_ga_model_id direct unit tests ────────────────────────────────────


def test_probe_002_succeeds_returns_002_and_v2_version() -> None:
    """Probe finds gemini-embedding-002 first → (-002, v2-...-emb2-ga)."""
    client = MagicMock()
    client.models.embed_content.return_value = _make_embedding_response()

    model_id, version = _probe_ga_model_id(client)

    assert model_id == "gemini-embedding-002"
    assert version == "v2-3excerpt-mean-emb2-ga"
    # Only one probe call needed — first candidate succeeded.
    assert client.models.embed_content.call_count == 1
    call = client.models.embed_content.call_args
    assert call.kwargs["model"] == "gemini-embedding-002"


def test_probe_002_fails_falls_back_to_2() -> None:
    """First candidate raises 404 → falls back to gemini-embedding-2.

    On fallback, version is the v1 default (NO cache invalidation).
    """
    client = MagicMock()
    not_found = Exception("404 NOT_FOUND: model gemini-embedding-002 not available")
    client.models.embed_content.side_effect = [
        not_found,
        _make_embedding_response(),
    ]

    model_id, version = _probe_ga_model_id(client)

    assert model_id == "gemini-embedding-2"
    assert version == "v1-3excerpt-mean"
    assert client.models.embed_content.call_count == 2
    second_call = client.models.embed_content.call_args_list[1]
    assert second_call.kwargs["model"] == "gemini-embedding-2"


def test_probe_all_fail_raises() -> None:
    """Both candidates raise → RuntimeError surfaces outage."""
    client = MagicMock()
    client.models.embed_content.side_effect = [
        Exception("404 NOT_FOUND"),
        Exception("503 UNAVAILABLE"),
    ]

    with pytest.raises(RuntimeError) as excinfo:
        _probe_ga_model_id(client)

    assert "GEMINI_EMBEDDING_MODEL_GA_CANDIDATES" in str(excinfo.value)
    assert client.models.embed_content.call_count == 2


def test_probe_event_logged_on_success() -> None:
    """Probe surfaces an ``embedding_model_probe`` event to recorder."""
    client = MagicMock()
    client.models.embed_content.return_value = _make_embedding_response()
    recorder = MagicMock()

    _probe_ga_model_id(client, recorder=recorder)

    # Exactly one log_event call with the probe payload.
    assert recorder.log_event.call_count == 1
    call = recorder.log_event.call_args
    assert call.args[0] == "embedding_model_probe"
    kwargs = call.kwargs
    assert kwargs["chosen"] == "gemini-embedding-002"
    assert kwargs["version"] == "v2-3excerpt-mean-emb2-ga"
    # Candidate list pinned so observability can show what was tried.
    assert kwargs["candidates_tried"] == ["gemini-embedding-002"]
    assert "duration_ms" in kwargs


def test_probe_event_logged_on_fallback() -> None:
    """Recorder receives the fallback chain on 404."""
    client = MagicMock()
    not_found = Exception("404 NOT_FOUND")
    client.models.embed_content.side_effect = [
        not_found,
        _make_embedding_response(),
    ]
    recorder = MagicMock()

    _probe_ga_model_id(client, recorder=recorder)

    call = recorder.log_event.call_args
    kwargs = call.kwargs
    assert kwargs["chosen"] == "gemini-embedding-2"
    assert kwargs["version"] == "v1-3excerpt-mean"
    assert kwargs["candidates_tried"] == [
        "gemini-embedding-002",
        "gemini-embedding-2",
    ]


# ─── LibraryEmbedder integration ─────────────────────────────────────────────


def test_probe_runs_once_per_embedder(
    cache_db: sqlite3.Connection,
    short_track: TrackEntry,
) -> None:
    """Probe is invoked exactly once on construction, then never again.

    Per-call embed_track must NOT re-probe; that would burn quota.
    """
    client = MagicMock()
    client.models.embed_content.return_value = _make_embedding_response()

    embedder = LibraryEmbedder(client, cache_db=cache_db)

    # 1 probe call so far.
    assert client.models.embed_content.call_count == 1

    # Embed the same track 5 times — cache hits after first.
    for _ in range(5):
        embedder.embed_track(short_track)

    # 1 probe + 1 real embed = 2 (subsequent 4 are cache hits).
    assert client.models.embed_content.call_count == 2


def test_probe_overrides_module_default_for_calls(
    cache_db: sqlite3.Connection,
    short_track: TrackEntry,
) -> None:
    """When probe finds GA-renamed model, embed_track uses the new id.

    Embedder calls embed_content with the probed model, NOT the module
    default constant.
    """
    client = MagicMock()
    client.models.embed_content.return_value = _make_embedding_response()

    embedder = LibraryEmbedder(client, cache_db=cache_db)
    embedder.embed_track(short_track)

    # All calls (probe + audio embed) should use gemini-embedding-002.
    for call in client.models.embed_content.call_args_list:
        assert call.kwargs["model"] == "gemini-embedding-002"


def test_probe_fallback_preserves_legacy_model_in_calls(
    cache_db: sqlite3.Connection,
    short_track: TrackEntry,
) -> None:
    """Probe falls back to legacy → embed_track uses legacy id."""
    client = MagicMock()
    client.models.embed_content.side_effect = [
        Exception("404 NOT_FOUND"),  # -002 probe fails
        _make_embedding_response(),  # -2 probe succeeds
        _make_embedding_response(),  # real audio embed
    ]

    embedder = LibraryEmbedder(client, cache_db=cache_db)
    embedder.embed_track(short_track)

    # Probe issued 2 calls (002 fail, 2 success); embed issued 1 call.
    assert client.models.embed_content.call_count == 3
    final_call = client.models.embed_content.call_args_list[-1]
    assert final_call.kwargs["model"] == "gemini-embedding-2"


def test_probe_failure_falls_back_to_module_defaults(
    cache_db: sqlite3.Connection,
) -> None:
    """If both candidates fail, embedder construction still succeeds.

    The instance falls back to module-default model + version so the
    library can attempt subsequent calls (which will surface their own
    errors). This avoids hard-crashing the app on a transient probe outage.
    """
    client = MagicMock()
    client.models.embed_content.side_effect = [
        Exception("503 UNAVAILABLE"),
        Exception("503 UNAVAILABLE"),
    ]

    embedder = LibraryEmbedder(client, cache_db=cache_db)

    assert embedder._model == GEMINI_EMBEDDING_MODEL
    assert embedder._excerpt_strategy_version == EXCERPT_STRATEGY_VERSION


def test_probe_can_be_disabled(
    cache_db: sqlite3.Connection,
    short_track: TrackEntry,
) -> None:
    """probe_on_init=False skips the probe entirely.

    Used by unit tests that need deterministic call counts (the existing
    test_embed.py suite asserts call_count == 1 for short_track and would
    break if a probe call was prepended).
    """
    client = MagicMock()
    client.models.embed_content.return_value = _make_embedding_response()

    embedder = LibraryEmbedder(client, cache_db=cache_db, probe_on_init=False)

    # No probe call issued.
    assert client.models.embed_content.call_count == 0
    # Module defaults are in effect.
    assert embedder._model == GEMINI_EMBEDDING_MODEL
    assert embedder._excerpt_strategy_version == EXCERPT_STRATEGY_VERSION

    embedder.embed_track(short_track)
    # Now exactly 1 call — the real embed.
    assert client.models.embed_content.call_count == 1


# ─── Cache-key stability goldens ─────────────────────────────────────────────


def _cache_key_for(
    file_bytes_marker: bytes,
    model: str,
    version: str,
) -> str:
    """Recompute the exact hash structure used in LibraryEmbedder._track_hash."""
    h = hashlib.sha256()
    h.update(file_bytes_marker)
    h.update(b"||")
    h.update(model.encode())
    h.update(b"||")
    h.update(version.encode())
    return h.hexdigest()


def test_cache_key_stable_when_probe_falls_back_to_legacy(
    cache_db: sqlite3.Connection,
    short_track: TrackEntry,
) -> None:
    """Pre-Phase-41 cache rows MUST keep cache-hitting after the probe lands.

    Golden invariant: when the probe falls back to ``gemini-embedding-2``
    + ``v1-3excerpt-mean``, the SHA256 cache key is byte-identical to the
    v2.1-shipped value. This is the primary safety property of the probe.
    """
    client = MagicMock()
    client.models.embed_content.side_effect = [
        Exception("404 NOT_FOUND"),
        _make_embedding_response(),
    ]
    embedder = LibraryEmbedder(client, cache_db=cache_db, probe_on_init=False)
    embedder_with_probe = LibraryEmbedder(client, cache_db=cache_db)

    # Direct golden compute: cache key against the same file should match
    # the pre-Phase-41 key (legacy model + v1 version).
    file_bytes = Path(short_track.filepath).read_bytes()
    file_hash = hashlib.sha256()
    file_hash.update(file_bytes)
    # _track_hash streams the file content first, then '||model||version'.
    # We replicate via private call for the golden.
    legacy_key = embedder._track_hash(short_track)
    probed_key = embedder_with_probe._track_hash(short_track)

    assert legacy_key == probed_key, (
        "Cache key drifted after probe fallback — v2.1 caches will miss!"
    )


def test_cache_key_changes_on_ga_rename(
    cache_db: sqlite3.Connection,
    short_track: TrackEntry,
    tmp_path: Path,
) -> None:
    """When probe finds GA rename, cache key MUST change.

    Forces lazy re-embed on next read (the documented migration UX).
    """
    legacy_client = MagicMock()
    legacy_client.models.embed_content.side_effect = [
        Exception("404 NOT_FOUND"),
        _make_embedding_response(),
    ]
    legacy_db = sqlite3.connect(str(tmp_path / "legacy.db"))
    legacy = LibraryEmbedder(legacy_client, cache_db=legacy_db)

    ga_client = MagicMock()
    ga_client.models.embed_content.return_value = _make_embedding_response()
    ga_db = sqlite3.connect(str(tmp_path / "ga.db"))
    ga = LibraryEmbedder(ga_client, cache_db=ga_db)

    legacy_key = legacy._track_hash(short_track)
    ga_key = ga._track_hash(short_track)

    assert legacy_key != ga_key, (
        "Cache key did not change after GA rename — corpus will serve "
        "stale legacy vectors!"
    )
