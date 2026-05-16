# SPDX-License-Identifier: Apache-2.0
"""vibemix.llm — Gemini SKU + ServiceTier routing seam (Plan 41-01).

Single source of truth: every Gemini model literal in `src/vibemix/`
flows through :func:`vibemix.llm.model_router.resolve`. The CI grep
gate fails any PR that re-introduces a hardcoded model literal in
`src/vibemix/` outside the allowlisted ``_router_config.py``.

See :mod:`vibemix.llm.model_router` for the API and
:mod:`vibemix.llm._router_config` for the locked routing table.
"""

from __future__ import annotations

from vibemix.llm.model_router import (
    ROUTER_PATHS,
    RouterPathError,
    ServiceTier,
    resolve,
)

__all__ = ["ROUTER_PATHS", "RouterPathError", "ServiceTier", "resolve"]
