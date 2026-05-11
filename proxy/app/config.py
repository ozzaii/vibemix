# SPDX-License-Identifier: Apache-2.0
"""Proxy-side settings via pydantic-settings. All secrets via env vars."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Required — proxy refuses to start without these.
    GEMINI_API_KEY: str
    OPENROUTER_API_KEY: str
    JWT_SECRET: str
    REDIS_URL: str

    # Optional with defaults.
    ALLOWED_ORIGINS: list[str] = []
    RATE_LIMIT_PER_MIN: int = 60
    RATE_LIMIT_PER_DAY: int = 2000
    JWT_TTL_DAYS: int = 90


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
