# SPDX-License-Identifier: Apache-2.0
"""Backend-neutral embedder protocols used by library product modules."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from vibemix.library.rekordbox import TrackEntry


class QueryEmbedder(Protocol):
    """Embeds natural-language library queries."""

    def embed_query(self, query: str) -> np.ndarray: ...


class TrackEmbedder(Protocol):
    """Embeds Rekordbox tracks into the library vector space."""

    def embed_track(self, track: TrackEntry) -> np.ndarray: ...


class CachedTrackEmbedder(TrackEmbedder, Protocol):
    """Embeds tracks and exposes cache-hit probes for importer telemetry."""

    def has_cached_embedding(self, track: TrackEntry) -> bool: ...


class AudioBytesEmbedder(Protocol):
    """Embeds short audio buffers for grounding."""

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray: ...


class LibraryEmbedderLike(
    QueryEmbedder,
    CachedTrackEmbedder,
    AudioBytesEmbedder,
    Protocol,
):
    """Full product embedder surface shared by CLAP and legacy tests."""


__all__ = [
    "AudioBytesEmbedder",
    "CachedTrackEmbedder",
    "LibraryEmbedderLike",
    "QueryEmbedder",
    "TrackEmbedder",
]
