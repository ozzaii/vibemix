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

from google.genai.types import ServiceTier

from vibemix.llm._router_config import _ROUTES

__all__ = ["resolve", "ROUTER_PATHS", "RouterPathError", "ServiceTier"]


# Frozen tuple of valid router-path keys. Defensive against accidental
# mutation by callers (a list would let `ROUTER_PATHS.append(...)` succeed).
ROUTER_PATHS: tuple[str, ...] = tuple(sorted(_ROUTES.keys()))


class RouterPathError(KeyError):
    """Raised when ``resolve(path)`` is called with an unknown path.

    Inherits from ``KeyError`` so callers that wrap the resolve call in
    ``except KeyError`` keep working (backward-compat for any future
    consumer that catches the parent class).
    """


def resolve(path: str) -> tuple[str, ServiceTier | None]:
    """Return ``(model_id, tier)`` for ``path``.

    Args:
        path: A router-path key. Must be one of :data:`ROUTER_PATHS`.

    Returns:
        ``(model_id, ServiceTier | None)``. The tier is ``None`` for the
        ``live_coach_tts_openrouter`` path (not a Gemini-API call —
        consume the model_id only).

    Raises:
        RouterPathError: If ``path`` is not a valid router-path key. The
            error message lists every valid path.
    """
    try:
        return _ROUTES[path]
    except KeyError:
        valid = ", ".join(ROUTER_PATHS)
        raise RouterPathError(
            f"unknown router path {path!r}; valid paths: {valid}"
        ) from None
