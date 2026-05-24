# SPDX-License-Identifier: Apache-2.0
"""Process-global debug-log verbosity switch (v8.0 LOG-04).

OFF by default. When off, the live runtime's stderr + ``events.jsonl`` output is
byte-identical to the pre-v8.0 baseline — no behavioural or perf change. The
discrete reaction events (``citation_count`` / ``citation_strip`` /
``citation_bypass`` / ``ai_text``) are always logged; this switch only gates the
*verbose* additions (the per-turn consolidated ``reaction_evidence`` digest and
any future trace-level lines), so turning it on never *removes* anything.

Turned on by, in precedence order:
  1. ``vibemix --debug-log`` (CLI flag — calls :func:`set_debug_log`).
  2. ``VIBEMIX_DEBUG_LOG`` env var truthy (read once at import — the path the
     bundled binary + CI use, since they can't always pass argv).

Read it anywhere via :func:`debug_log_enabled`. This module depends only on the
stdlib so it can be imported from the audio / state / agent layers without any
import cycle.
"""

from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on", "debug", "verbose"}


def _env_default() -> bool:
    return os.environ.get("VIBEMIX_DEBUG_LOG", "").strip().lower() in _TRUTHY


_enabled: bool = _env_default()


def debug_log_enabled() -> bool:
    """True when verbose debug logging is active for this process."""
    return _enabled


def set_debug_log(enabled: bool) -> None:
    """Set the process-global debug-log flag (called from the CLI flag handler).

    A ``True`` from the CLI flag wins over a falsy env default; passing
    ``False`` here does NOT override a truthy ``VIBEMIX_DEBUG_LOG`` env (the env
    is the floor, the flag can only raise verbosity), so an operator who set the
    env to debug a bundled install still gets logs even on a default launch.
    """
    global _enabled
    _enabled = bool(enabled) or _env_default()
