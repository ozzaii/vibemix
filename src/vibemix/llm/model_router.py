# SPDX-License-Identifier: Apache-2.0
"""ModelRouter — `path -> (model_id, ServiceTier | None)` resolver.

If you find yourself adding a model literal anywhere in `src/vibemix/`,
you are off-pattern — add the path to ``_router_config._ROUTES`` instead
and call ``resolve(<new_path>)``. The CI grep gate
(`scripts/release/check_no_hardcoded_model.sh`) fails any PR that
re-introduces a Gemini model literal in `src/vibemix/` outside the
allowlisted ``_router_config.py``.

Resolution rules:

- ``resolve(path)`` returns ``(model_id, ServiceTier | None)``.
- Unknown paths raise :class:`RouterPathError` (a ``KeyError`` subclass).
  The error message lists every valid path so the caller can self-diagnose.
- ``ROUTER_PATHS`` is a frozen tuple of valid keys.

Plan 41-01 ships this seam; Plans 41-02..06 consume ``resolve()``.
"""

from __future__ import annotations

from typing import Any

from vibemix.llm._router_config import _ROUTES

__all__ = [
    "ROUTER_PATHS",
    "RouterPathError",
    "resolve",
    "resolve_model",
]


# Frozen tuple of valid router-path keys. Defensive against accidental
# mutation by callers (a list would let `ROUTER_PATHS.append(...)` succeed).
ROUTER_PATHS: tuple[str, ...] = tuple(sorted(_ROUTES.keys()))


class RouterPathError(KeyError):
    """Raised when ``resolve(path)`` is called with an unknown path.

    Inherits from ``KeyError`` so callers that wrap the resolve call in
    ``except KeyError`` keep working (backward-compat for any future
    consumer that catches the parent class).
    """


def _to_service_tier(tier_name: str | None) -> Any | None:
    """Return the real Gemini SDK enum only when a caller needs the tier."""
    if tier_name is None:
        return None
    from google.genai.types import ServiceTier

    return getattr(ServiceTier, tier_name)


def resolve_model(path: str) -> str:
    """Return only the model id for ``path`` without importing the Gemini SDK."""
    try:
        return _ROUTES[path][0]
    except KeyError:
        valid = ", ".join(ROUTER_PATHS)
        raise RouterPathError(
            f"unknown router path {path!r}; valid paths: {valid}"
        ) from None


def resolve(path: str) -> tuple[str, Any | None]:
    """Return ``(model_id, tier)`` for ``path``.

    Args:
        path: A router-path key. Must be one of :data:`ROUTER_PATHS`.

    Returns:
        ``(model_id, ServiceTier | None)``. The tier is ``None`` for the
        non-Gemini API paths such as ``live_coach_openrouter`` (consume the
        model_id only).

    Raises:
        RouterPathError: If ``path`` is not a valid router-path key. The
            error message lists every valid path.
    """
    try:
        model, tier_name = _ROUTES[path]
    except KeyError:
        valid = ", ".join(ROUTER_PATHS)
        raise RouterPathError(
            f"unknown router path {path!r}; valid paths: {valid}"
        ) from None
    return model, _to_service_tier(tier_name)


def __getattr__(name: str) -> Any:
    if name == "ServiceTier":
        from google.genai.types import ServiceTier

        return ServiceTier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
