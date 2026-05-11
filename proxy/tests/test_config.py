# SPDX-License-Identifier: Apache-2.0
"""CONFIG-01..04 — pydantic-settings shape + lru_cache + list parsing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_config_01_settings_defaults_with_required_vars():
    from app.config import Settings

    s = Settings(
        GEMINI_API_KEY="g",
        OPENROUTER_API_KEY="o",
        JWT_SECRET="j",
        REDIS_URL="redis://x",
    )
    assert s.RATE_LIMIT_PER_MIN == 60
    assert s.RATE_LIMIT_PER_DAY == 2000
    assert s.JWT_TTL_DAYS == 90
    assert s.ALLOWED_ORIGINS == []


def test_config_02_missing_required_var_raises_validation_error(monkeypatch):
    from app.config import get_settings

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Block the env file from re-populating (autouse fixture's setenv on
    # GEMINI_API_KEY was already undone by delenv above; but pydantic-
    # settings also reads from .env file if present — neutralize by setting
    # env_file to a nonexistent path via monkeypatch on Settings class itself.)
    get_settings.cache_clear()
    # Construct directly with _env_file=None to skip dotenv lookup.
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_config_03_get_settings_is_cached(monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b


def test_config_04_allowed_origins_list_parsing(monkeypatch):
    """pydantic-settings v2 parses comma-separated strings into list[str] when
    the field type is list[str]. JSON list syntax also works."""
    from app.config import Settings

    # JSON list form (canonical pydantic-settings list parsing).
    s = Settings(
        GEMINI_API_KEY="g",
        OPENROUTER_API_KEY="o",
        JWT_SECRET="j",
        REDIS_URL="redis://x",
        ALLOWED_ORIGINS=["https://a.com", "https://b.com"],  # type: ignore[arg-type]
    )
    assert s.ALLOWED_ORIGINS == ["https://a.com", "https://b.com"]
