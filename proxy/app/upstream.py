# SPDX-License-Identifier: Apache-2.0
"""Module-level upstream HTTP and Gemini clients + per-route circuit breakers.

Per RESEARCH Q6: the proxy holds ONE genai.Client (with the real
GEMINI_API_KEY) globally and reuses it across requests. Same for
httpx.AsyncClient (OpenRouter upstream). Circuit breaker pattern
verbatim from RESEARCH Common Patterns section.
"""

from __future__ import annotations

import time
from typing import Optional

import httpx
from google import genai

from app.config import Settings, get_settings


# ---------------------------------------------------------------------
# Singletons (module-level state, lazy-init, test-resettable)
# ---------------------------------------------------------------------

_gemini_client: Optional[genai.Client] = None
_http_client: Optional[httpx.AsyncClient] = None


def get_gemini_client(settings: Optional[Settings] = None) -> genai.Client:
    """Return the module-level genai.Client singleton (lazy-init)."""
    global _gemini_client
    if _gemini_client is None:
        s = settings or get_settings()
        _gemini_client = genai.Client(api_key=s.GEMINI_API_KEY)
    return _gemini_client


def get_http_client() -> httpx.AsyncClient:
    """Return the module-level httpx.AsyncClient singleton (lazy-init)."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=120.0)
    return _http_client


async def close_http_client() -> None:
    """Test/shutdown helper. Closes and clears the singleton."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def reset_gemini_client() -> None:
    """Test helper. Clears the singleton so the next call rebuilds it."""
    global _gemini_client
    _gemini_client = None


def set_http_client(client: httpx.AsyncClient) -> None:
    """Test helper. Inject a pre-built (mocked) AsyncClient."""
    global _http_client
    _http_client = client


# ---------------------------------------------------------------------
# CircuitBreaker — per-route open/closed/cooldown state machine
# ---------------------------------------------------------------------


class CircuitBreaker:
    """Open after `threshold` consecutive failures; close after cooldown."""

    def __init__(self, threshold: int = 10, cooldown_sec: int = 60):
        self.threshold = threshold
        self.cooldown_sec = cooldown_sec
        self._fail_streak = 0
        self._open_until: Optional[float] = None

    def allow(self) -> bool:
        if self._open_until is None:
            return True
        if time.time() >= self._open_until:
            # Cooldown elapsed — close breaker
            self._open_until = None
            self._fail_streak = 0
            return True
        return False

    def record_success(self) -> None:
        self._fail_streak = 0
        self._open_until = None

    def record_failure(self) -> None:
        self._fail_streak += 1
        if self._fail_streak >= self.threshold and self._open_until is None:
            self._open_until = time.time() + self.cooldown_sec

    def retry_after(self) -> int:
        if self._open_until is None:
            return 0
        return max(1, int(self._open_until - time.time()))

    def reset(self) -> None:
        """Test helper. Reset state."""
        self._fail_streak = 0
        self._open_until = None


# Module-level per-route breakers (created at first use)
gemini_breaker = CircuitBreaker(threshold=10, cooldown_sec=60)
openrouter_breaker = CircuitBreaker(threshold=10, cooldown_sec=60)
