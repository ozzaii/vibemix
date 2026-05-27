# SPDX-License-Identifier: Apache-2.0
"""vibemix.llm — Gemini SKU + tier routing seam.

Importing this package is intentionally light; the Google SDK's ``ServiceTier``
enum is imported only when a caller explicitly asks for it or resolves a full
``(model, tier)`` pair.
"""

from __future__ import annotations

from typing import Any

from vibemix.llm.model_router import ROUTER_PATHS, RouterPathError, resolve, resolve_model

__all__ = ["ROUTER_PATHS", "RouterPathError", "resolve", "resolve_model"]


def __getattr__(name: str) -> Any:
    if name == "ServiceTier":
        from google.genai.types import ServiceTier

        return ServiceTier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
