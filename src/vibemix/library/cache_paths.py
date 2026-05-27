# SPDX-License-Identifier: Apache-2.0
"""Shared cache paths for local library state and model assets."""

from __future__ import annotations

import os
from pathlib import Path

VIBEMIX_CACHE_DIR = Path.home() / ".cache" / "vibemix"

# Cache database. NOT library.db (Plan 02 owns that for vec0). NOT
# library.pkl (Phase 25 Rekordbox parsed cache).
EMBED_CACHE_DB_PATH = VIBEMIX_CACHE_DIR / "embeddings.db"

# CLAP 512-d content-hash cache, distinct from legacy cloud embedding rows.
CLAP_EMBED_CACHE_DB_PATH = VIBEMIX_CACHE_DIR / "clap_embeddings.db"

CLAP_ONNX_ENV = "VIBEMIX_CLAP_ONNX_DIR"
DEFAULT_CLAP_ONNX_DIR = VIBEMIX_CACHE_DIR / "clap-onnx"

CUE_ONNX_ENV = "VIBEMIX_CUE_ONNX_PATH"
DEFAULT_CUE_ONNX_PATH = VIBEMIX_CACHE_DIR / "cue-detr-onnx" / "cuedetr.fp32.onnx"


def clap_onnx_dir() -> Path:
    """Resolved CLAP ONNX directory (env override, else vibemix cache)."""
    return Path(os.environ.get(CLAP_ONNX_ENV) or DEFAULT_CLAP_ONNX_DIR).expanduser()


def cue_onnx_path() -> Path:
    """Resolved CUE-DETR ONNX path (env override, else vibemix cache)."""
    return Path(os.environ.get(CUE_ONNX_ENV) or DEFAULT_CUE_ONNX_PATH).expanduser()

__all__ = [
    "CLAP_EMBED_CACHE_DB_PATH",
    "CLAP_ONNX_ENV",
    "CUE_ONNX_ENV",
    "DEFAULT_CLAP_ONNX_DIR",
    "DEFAULT_CUE_ONNX_PATH",
    "EMBED_CACHE_DB_PATH",
    "VIBEMIX_CACHE_DIR",
    "clap_onnx_dir",
    "cue_onnx_path",
]
