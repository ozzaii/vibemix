# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / Task 2 — library/embed.py routes via ModelRouter.

The CRITICAL test here is :func:`test_library_embed_cache_key_unchanged`:
the SHA256 cache-key invariant for LibraryEmbedder must stay byte-identical
across the migration. If the resolved ``GEMINI_EMBEDDING_MODEL`` ever drifts
from ``"gemini-embedding-2"``, every existing user's
``~/.cache/vibemix/embeddings.db`` would silently invalidate. Plan 41-05
owns the version bump if a GA model-ID rename surfaces.
"""

from __future__ import annotations

import hashlib

from vibemix.library.embed import (
    EXCERPT_STRATEGY_VERSION,
    GEMINI_EMBEDDING_MODEL,
)
from vibemix.llm.model_router import resolve


def test_library_embed_model_matches_router() -> None:
    """GEMINI_EMBEDDING_MODEL is router-derived (embedding path)."""
    assert GEMINI_EMBEDDING_MODEL == resolve("embedding")[0]


def test_library_embed_model_is_gemini_embedding_2() -> None:
    """Smoke: resolved id is still the Phase 28 Open-Q9 id."""
    assert GEMINI_EMBEDDING_MODEL == "gemini-embedding-2"


def test_library_embed_cache_key_unchanged() -> None:
    """Plan-41-01 A1 invariant — cache-key SHA256 byte-identical to golden.

    LibraryEmbedder keys its on-disk cache by
    ``SHA256(file_bytes || model_id || strategy_version)``. The migration
    from inline literal → router-derived constant MUST NOT shift this hash,
    or every cached embedding silently invalidates and the user re-pays
    €27/month worth of API calls.

    The golden hash below was computed on the pre-migration tree
    (model_id == "gemini-embedding-2", strategy_version == "v1-3excerpt-mean").
    """
    canary = b"canary-bytes-41-01-task-2"
    h = hashlib.sha256()
    h.update(canary)
    h.update(GEMINI_EMBEDDING_MODEL.encode())
    h.update(EXCERPT_STRATEGY_VERSION.encode())
    expected = "26f69c902942762c0fc7e14ada0e439cae4af6f0b24d9b3c3786b9399d6ead42"
    assert h.hexdigest() == expected, (
        "cache-key SHA256 drifted; either GEMINI_EMBEDDING_MODEL or "
        "EXCERPT_STRATEGY_VERSION changed across the 41-01 migration"
    )


def test_excerpt_strategy_version_unchanged() -> None:
    """Belt-and-braces: EXCERPT_STRATEGY_VERSION is the Phase-28-locked
    string. Plan 41-05 owns any bump.
    """
    assert EXCERPT_STRATEGY_VERSION == "v1-3excerpt-mean"
