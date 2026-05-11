# SPDX-License-Identifier: Apache-2.0
"""QUOTA-01..06 — Redis INCR + EXPIRE NX semantics via fakeredis.

Plus DOCKER-01..02 — Dockerfile + docker-compose shape checks.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

import app.quota as quota_mod
from app.quota import QuotaClient, QuotaExceeded


_PROXY = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# QUOTA-01..06
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_quota_01_first_consume_returns_1_with_ttl(redis_client):
    q = QuotaClient.from_redis(redis_client)
    count = await q.consume("uuid-a")
    assert count == 1
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    keys = await redis_client.keys("vibemix:quota:*")
    assert keys == [f"vibemix:quota:uuid-a:{today}"]
    ttl = await redis_client.ttl(keys[0])
    assert 86398 <= ttl <= 86400  # ±2s slop


@pytest.mark.asyncio
async def test_quota_02_second_consume_preserves_ttl_via_nx(redis_client):
    q = QuotaClient.from_redis(redis_client)
    await q.consume("uuid-b")
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    key = f"vibemix:quota:uuid-b:{today}"
    ttl1 = await redis_client.ttl(key)
    await asyncio.sleep(1.05)
    count = await q.consume("uuid-b")
    ttl2 = await redis_client.ttl(key)
    assert count == 2
    # NX preserved original TTL — ttl2 should be ~1s less than ttl1, NOT reset to 86400.
    assert ttl2 < ttl1, f"NX flag did not prevent TTL reset: ttl1={ttl1} ttl2={ttl2}"
    assert ttl1 - 3 <= ttl2 <= ttl1 - 1


@pytest.mark.asyncio
async def test_quota_03_exceeds_raises_with_retry_after(redis_client):
    q = QuotaClient.from_redis(redis_client, daily_quota=3)
    # 3 calls succeed
    for _ in range(3):
        await q.consume("uuid-c")
    # 4th raises
    with pytest.raises(QuotaExceeded) as exc:
        await q.consume("uuid-c")
    assert 1 <= exc.value.retry_after_seconds <= 86400


@pytest.mark.asyncio
async def test_quota_04_retry_after_computed_to_midnight_utc(monkeypatch, redis_client):
    class _FrozenDT:
        _now = datetime(2026, 5, 11, 14, 30, 0, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls._now.astimezone(tz) if tz else cls._now

    monkeypatch.setattr(quota_mod, "datetime", _FrozenDT)

    q = QuotaClient.from_redis(redis_client, daily_quota=1)
    await q.consume("uuid-d")
    with pytest.raises(QuotaExceeded) as exc:
        await q.consume("uuid-d")
    # 14:30 UTC → midnight is 9h30m away = 34200s
    expected = (24 * 3600) - (14 * 3600) - (30 * 60)
    assert exc.value.retry_after_seconds == expected


@pytest.mark.asyncio
async def test_quota_05_independent_uuid_counters(redis_client):
    q = QuotaClient.from_redis(redis_client)
    a = await q.consume("uuid-e")
    b = await q.consume("uuid-f")
    assert a == 1 and b == 1


@pytest.mark.asyncio
async def test_quota_06_independent_day_counters(monkeypatch, redis_client):
    """Different YYYYMMDD keys yield independent counters."""

    class _FrozenDT:
        _now = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):
            return cls._now.astimezone(tz) if tz else cls._now

    monkeypatch.setattr(quota_mod, "datetime", _FrozenDT)
    q = QuotaClient.from_redis(redis_client)
    a = await q.consume("uuid-g")

    _FrozenDT._now = datetime(2026, 5, 12, 12, 0, 0, tzinfo=timezone.utc)
    b = await q.consume("uuid-g")

    assert a == 1 and b == 1
    keys = await redis_client.keys("vibemix:quota:*")
    assert sorted(keys) == [
        "vibemix:quota:uuid-g:20260511",
        "vibemix:quota:uuid-g:20260512",
    ]


# ---------------------------------------------------------------------------
# DOCKER-01..02
# ---------------------------------------------------------------------------


def test_docker_01_dockerfile_shape():
    text = (_PROXY / "Dockerfile").read_text()
    assert "FROM python:3.12-slim" in text
    assert "WORKDIR /app" in text
    assert "COPY pyproject.toml" in text
    assert "COPY" in text and "app/" in text  # COPY ... app/ somewhere
    assert "EXPOSE 8788" in text
    assert "uvicorn" in text and "app.main:app" in text


def test_docker_02_compose_shape():
    data = yaml.safe_load((_PROXY / "docker-compose.yml").read_text())
    services = data["services"]
    assert "proxy" in services and "redis" in services
    assert services["redis"]["image"] == "redis:7-alpine"
    depends = services["proxy"]["depends_on"]
    # depends_on can be dict (with condition) or list
    if isinstance(depends, dict):
        assert "redis" in depends
    else:
        assert "redis" in depends
