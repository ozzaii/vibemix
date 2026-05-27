# SPDX-License-Identifier: Apache-2.0
"""Optional section-vector lookup for transition scoring.

This module is deliberately small and duck-typed. The real section embedding
store can land behind any of these methods without changing the live pill or
agent tool contracts:

* ``section_vector_for_id(section_id)``
* ``section_vector(section_id)``
* ``load_section_vectors([section_id, ...])``
* a ``section_vectors`` / ``_section_vectors`` mapping

When no section vector exists, callers can pass a whole-track fallback vector.
The returned ``basis`` makes that fallback explicit, so downstream payloads do
not accidentally claim section-level audio evidence.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from vibemix.library.cache_paths import SECTION_VECTOR_CACHE_DB_PATH

SectionVectorBasis = Literal["section_vector", "track_vector_fallback", "semantic_unknown"]

SECTION_VECTOR_CACHE_VERSION = "v1-clap-section-window"


@dataclass(frozen=True, slots=True)
class SectionVectorResult:
    vector: np.ndarray | None
    basis: SectionVectorBasis


def open_default_section_vector_db(*, create: bool = True) -> sqlite3.Connection | None:
    """Open the default section-vector DB, optionally without creating it."""
    path = SECTION_VECTOR_CACHE_DB_PATH
    if not create and not path.exists():
        return None
    return open_section_vector_db(path, create=create)


def open_section_vector_db(path: str | Path, *, create: bool = True) -> sqlite3.Connection:
    """Open a section-vector SQLite cache and initialize the schema."""
    db_path = Path(path).expanduser()
    if create:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    init_section_vector_schema(conn)
    return conn


def init_section_vector_schema(conn: sqlite3.Connection) -> None:
    """Create the section-vector table if absent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS section_vector_cache (
            section_id TEXT PRIMARY KEY,
            source_hash TEXT NOT NULL,
            vector BLOB NOT NULL,
            dim INTEGER NOT NULL,
            model_tag TEXT NOT NULL,
            strategy_tag TEXT NOT NULL,
            start_s REAL NOT NULL,
            end_s REAL NOT NULL,
            ts REAL NOT NULL
        )
        """
    )
    conn.commit()


def get_cached_section_vector(conn: sqlite3.Connection, section_id: str) -> np.ndarray | None:
    """Read a section vector by id, returning ``None`` on miss/corruption."""
    row = conn.execute(
        "SELECT vector, dim FROM section_vector_cache WHERE section_id = ?",
        (section_id,),
    ).fetchone()
    if row is None:
        return None
    blob, dim = row
    vector = np.frombuffer(blob, dtype=np.float32)
    if vector.ndim != 1 or vector.shape[0] != int(dim):
        return None
    return vector.copy()


def section_vector_cached(
    conn: sqlite3.Connection,
    section_id: str,
    *,
    source_hash: str | None = None,
) -> bool:
    """Return whether a usable row exists, optionally matching source hash."""
    if source_hash is None:
        row = conn.execute(
            "SELECT dim, length(vector) FROM section_vector_cache WHERE section_id = ?",
            (section_id,),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT dim, length(vector)
            FROM section_vector_cache
            WHERE section_id = ? AND source_hash = ?
            """,
            (section_id, source_hash),
        ).fetchone()
    if row is None:
        return False
    dim, byte_len = row
    return int(dim) > 0 and int(byte_len) == int(dim) * 4


def put_section_vector(
    conn: sqlite3.Connection,
    *,
    section_id: str,
    source_hash: str,
    vector: np.ndarray,
    model_tag: str,
    strategy_tag: str = SECTION_VECTOR_CACHE_VERSION,
    start_s: float,
    end_s: float,
) -> None:
    """Persist one grounded section vector."""
    vec = np.asarray(vector, dtype=np.float32)
    if vec.ndim != 1 or vec.size == 0:
        raise ValueError("section vector must be a non-empty 1-D float32 array")
    conn.execute(
        """
        INSERT OR REPLACE INTO section_vector_cache (
            section_id, source_hash, vector, dim, model_tag, strategy_tag, start_s, end_s, ts
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            section_id,
            source_hash,
            vec.tobytes(),
            int(vec.shape[0]),
            model_tag,
            strategy_tag,
            float(start_s),
            float(end_s),
            time.time(),
        ),
    )
    conn.commit()


def resolve_section_vector(
    provider: Any,
    section_id: str,
    *,
    fallback_vector: np.ndarray | None = None,
) -> SectionVectorResult:
    """Return a section vector when available, else an explicit fallback."""
    vector = _lookup_provider_vector(provider, section_id)
    if vector is not None:
        return SectionVectorResult(vector=vector, basis="section_vector")
    if fallback_vector is not None:
        return SectionVectorResult(
            vector=np.asarray(fallback_vector, dtype=np.float32).copy(),
            basis="track_vector_fallback",
        )
    return SectionVectorResult(vector=None, basis="semantic_unknown")


def semantic_basis_for_pair(source_basis: str | None, destination_basis: str | None) -> str:
    """Collapse source/destination vector provenance into one public label."""
    bases = {source_basis or "semantic_unknown", destination_basis or "semantic_unknown"}
    if bases == {"section_vector"}:
        return "section_vector"
    if "semantic_unknown" in bases:
        return "semantic_unknown"
    if "section_vector" in bases and "track_vector_fallback" in bases:
        return "mixed_section_track"
    return "track_vector_fallback"


def _lookup_provider_vector(provider: Any, section_id: str) -> np.ndarray | None:
    for obj in _provider_objects(provider):
        vector = _lookup_method_vector(obj, section_id)
        if vector is not None:
            return vector
        vector = _lookup_mapping_vector(getattr(obj, "section_vectors", None), section_id)
        if vector is not None:
            return vector
        vector = _lookup_mapping_vector(getattr(obj, "_section_vectors", None), section_id)
        if vector is not None:
            return vector
    return None


def _provider_objects(provider: Any) -> tuple[Any, ...]:
    backend = getattr(provider, "_backend", None)
    if backend is None or backend is provider:
        return (provider,)
    return (provider, backend)


def _lookup_method_vector(obj: Any, section_id: str) -> np.ndarray | None:
    for name in ("section_vector_for_id", "section_vector", "get_section_vector"):
        method = getattr(obj, name, None)
        if callable(method):
            vector = _coerce_vector(_call_or_none(method, section_id))
            if vector is not None:
                return vector
    loader = getattr(obj, "load_section_vectors", None)
    if callable(loader):
        loaded = _call_or_none(loader, [section_id])
        vector = _lookup_mapping_vector(loaded, section_id)
        if vector is not None:
            return vector
        loaded = _call_or_none(loader)
        vector = _lookup_mapping_vector(loaded, section_id)
        if vector is not None:
            return vector
    return None


def _call_or_none(method: Any, *args: Any) -> Any:
    try:
        return method(*args)
    except TypeError:
        return None
    except Exception:
        return None


def _lookup_mapping_vector(raw: Any, section_id: str) -> np.ndarray | None:
    if not isinstance(raw, dict):
        return None
    for key in (section_id, f"vec8:{section_id}", f"vec512:{section_id}"):
        vector = _coerce_vector(raw.get(key))
        if vector is not None:
            return vector
    return None


def _coerce_vector(raw: Any) -> np.ndarray | None:
    if raw is None:
        return None
    try:
        vector = np.asarray(raw, dtype=np.float32)
    except (TypeError, ValueError):
        return None
    if vector.ndim != 1 or vector.size == 0:
        return None
    return vector.copy()


__all__ = [
    "SECTION_VECTOR_CACHE_VERSION",
    "SectionVectorBasis",
    "SectionVectorResult",
    "get_cached_section_vector",
    "init_section_vector_schema",
    "open_default_section_vector_db",
    "open_section_vector_db",
    "put_section_vector",
    "resolve_section_vector",
    "section_vector_cached",
    "semantic_basis_for_pair",
]
