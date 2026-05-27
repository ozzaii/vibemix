# SPDX-License-Identifier: Apache-2.0
"""Product embedder factory.

The shipped library path is local CLAP ONNX/512. Legacy Gemini embedding code
lives in ``vibemix.library.embed`` for migration probes and compatibility tests,
but this factory intentionally does not import it.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

from vibemix.library.embed_config import DEFAULT_EMBED_STRATEGY

if TYPE_CHECKING:
    from google import genai


def build_embedder(
    client: genai.Client | None = None,
    cache_db: sqlite3.Connection | None = None,
    **kwargs: object,
):
    """Return the product embedder: local CLAP ONNX, 512-dim.

    ``client`` is accepted for old call-site compatibility and ignored.
    """
    _ = client
    embed_strategy = str(kwargs.get("embed_strategy", DEFAULT_EMBED_STRATEGY))

    from vibemix.library.embed_clap import ClapEmbedder

    return ClapEmbedder(cache_db=cache_db, embed_strategy=embed_strategy)


__all__ = ["build_embedder"]
